import json
import logging

import razorpay

from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse, HttpResponseBadRequest
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.conf import settings
from django.db.models import F
from django.core.mail import send_mail

from projects.models import Project
from purchases.models import Purchase

from .services import client

logger = logging.getLogger(__name__)


@login_required
@require_POST
def create_order(request, slug):

    project = get_object_or_404(
        Project,
        slug=slug,
        is_active=True
    )

    # Prevent buying the same project again
    existing_purchase = Purchase.objects.filter(
        user=request.user,
        project=project,
        status='success'
    ).first()

    if existing_purchase:
        return JsonResponse(
            {
                'error': 'You already own this project.'
            },
            status=400
        )

    amount = int(project.price * 100)

    payment_link = client.payment_link.create({

        "amount": amount,

        "currency": "INR",

        "description": "OneSider Project Purchase",

        "customer": {

            "name": request.user.get_full_name() or request.user.username,

            "email": request.user.email

        },

        "notify": {

            "sms": False,

            "email": False

        },

        "callback_url": request.build_absolute_uri("/payments/success/"),

        "callback_method": "get",

        "notes": {

            "project_id": str(project.id),

            "user_id": str(request.user.id)

        }

    })

    purchase, created = Purchase.objects.update_or_create(
        user=request.user,
        project=project,
        defaults={
            'status': 'pending',
            'razorpay_payment_link_id': payment_link['id']
        }
    )

    return JsonResponse({

        "payment_url": payment_link["short_url"]

    })


def _confirm_purchase(purchase_id, payment_id):
    """
    Idempotently mark a purchase as successful and bump the project's
    purchase counter exactly once.

    Both the browser callback (payment_success) and the server-to-server
    webhook (razorpay_webhook) can end up calling this for the same
    payment - whichever one arrives first should "win" and the other
    should be a safe no-op. select_for_update() plus the status check
    inside the transaction is what makes that safe even if both requests
    land at nearly the same instant.
    """
    with transaction.atomic():
        purchase = (
            Purchase.objects
            .select_for_update()
            .get(pk=purchase_id)
        )

        if purchase.status == "success":
            # Already confirmed by an earlier call - nothing to do.
            return purchase

        purchase.status = "success"
        purchase.razorpay_payment_id = payment_id
        purchase.save(update_fields=["status", "razorpay_payment_id"])

        Project.objects.filter(pk=purchase.project_id).update(
            purchases_count=F("purchases_count") + 1
        )

        transaction.on_commit(
            lambda: _send_purchase_receipt(purchase_id)
        )

        # Customer receipt is a best-effort side effect, not part of
        # what makes this purchase successful. transaction.on_commit
        # means it only fires after the status='success' row above has
        # actually been committed. It only runs on this branch, guarded
        # by select_for_update + the status check above, so it cannot
        # be triggered twice for the same purchase.

        return purchase

def _send_purchase_receipt(purchase_id):
    try:
        purchase = (
            Purchase.objects
            .select_related("user", "project")
            .get(pk=purchase_id)
        )

        if not purchase.user.email:
            logger.warning(
                "Purchase %s has no customer email; receipt not sent.",
                purchase_id,
            )
            return

        send_mail(
            subject=f"OneSider — Purchase Confirmed — {purchase.project.title}",
            message=(
                "Your OneSider Purchase has been Confirmed.\n\n"
                "Purchase Details:\n\n"
                f"Project: {purchase.project.title}\n"
                f"Amount Paid: ₹{purchase.project.price}\n"
                f"Purchase ID: {purchase.id}\n"
                f"Purchased On: {purchase.purchased_at}\n\n"

                "Your Purchase is Now Available in Your OneSider Account.\n\n"

                "Keep this E-mail as Your Purchase Confirmation and Reference it"
                " if You Ever Need Support Regarding this Purchase.\n\n\n"

                "Forged in Silence\n\n"

                "OneSider"

            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[purchase.user.email],
            fail_silently=True,
        )

    except Purchase.DoesNotExist:
        logger.warning(
            "Purchase %s not found while sending receipt.",
            purchase_id,
        )

@login_required
def payment_success(request):

    payment_link_id = request.GET.get(
        "razorpay_payment_link_id"
    )

    payment_id = request.GET.get(
        "razorpay_payment_id"
    )

    payment_status = request.GET.get(
        "razorpay_payment_link_status"
    )

    razorpay_signature = request.GET.get(
        "razorpay_signature"
    )

    payment_link_reference_id = request.GET.get(
        "razorpay_payment_link_reference_id", ""
    )

    purchase = get_object_or_404(
        Purchase,
        razorpay_payment_link_id=payment_link_id,
        user=request.user
    )

    # If the webhook already confirmed this purchase (it can arrive before
    # the buyer's browser gets redirected back), there's nothing left to
    # verify - just send them on to their project.
    if purchase.status == "success":
        return redirect("project_detail", slug=purchase.project.slug)

    if payment_status != "paid":
        return redirect("project_detail", slug=purchase.project.slug)

    # Confirm these query params genuinely came from Razorpay and weren't
    # tampered with or replayed with someone else's payment id.
    try:
        client.utility.verify_payment_link_signature({
            "payment_link_id": payment_link_id,
            "payment_link_reference_id": payment_link_reference_id,
            "payment_link_status": payment_status,
            "razorpay_payment_id": payment_id,
            "razorpay_signature": razorpay_signature,
        })
    except razorpay.errors.SignatureVerificationError:
        logger.warning(
            "Razorpay callback signature mismatch for payment_link_id=%s",
            payment_link_id
        )
        return redirect("project_detail", slug=purchase.project.slug)

    # Belt-and-braces: confirm directly with Razorpay's API that the
    # payment is genuinely captured before we grant access.
    try:
        payment = client.payment.fetch(payment_id)

        if payment["status"] != "captured":
            return redirect("project_detail", slug=purchase.project.slug)

    except Exception:
        logger.exception(
            "Failed to verify Razorpay payment %s via API", payment_id
        )
        return redirect("project_detail", slug=purchase.project.slug)

    _confirm_purchase(purchase.id, payment_id)

    return redirect(
        "project_detail",
        slug=purchase.project.slug
    )


@csrf_exempt
@require_POST
def razorpay_webhook(request):
    """
    Server-to-server confirmation from Razorpay's own servers.

    This is what actually guarantees a paid purchase never gets
    permanently stuck as 'failed': payment_success only fires if the
    buyer's browser makes it back to the callback_url, which isn't
    guaranteed (closed tab, dropped connection, etc). Razorpay retries
    this webhook on its own until it gets a 2xx response, independent of
    the buyer's browser.

    Set this up in the Razorpay Dashboard under Settings -> Webhooks:
      - URL: https://<your-domain>/payments/webhook/
      - Active events: payment_link.paid
      - Secret: any strong random string - put the same value in your
        .env as RAZORPAY_WEBHOOK_SECRET.
    """
    signature = request.headers.get("X-Razorpay-Signature", "")
    body = request.body

    if not settings.RAZORPAY_WEBHOOK_SECRET:
        logger.error(
            "RAZORPAY_WEBHOOK_SECRET is not configured - rejecting webhook."
        )
        return HttpResponse(status=500)

    try:
        client.utility.verify_webhook_signature(
            body.decode("utf-8"),
            signature,
            settings.RAZORPAY_WEBHOOK_SECRET,
        )
    except razorpay.errors.SignatureVerificationError:
        logger.warning("Razorpay webhook signature mismatch.")
        return HttpResponseBadRequest("Invalid signature.")

    try:
        payload = json.loads(body)
    except ValueError:
        return HttpResponseBadRequest("Invalid JSON body.")

    event = payload.get("event")

    # We only act on payment_link.paid - other events (refunds, disputes,
    # etc.) are simply acknowledged for now so Razorpay stops retrying.
    if event != "payment_link.paid":
        return HttpResponse(status=200)

    payment_entity = (
        payload.get("payload", {})
        .get("payment", {})
        .get("entity", {})
    )

    payment_link_entity = (
        payload.get("payload", {})
        .get("payment_link", {})
        .get("entity", {})
    )

    payment_id = payment_entity.get("id")
    payment_link_id = payment_link_entity.get("id")

    if not payment_id or not payment_link_id:
        logger.warning("Webhook payload missing payment/payment_link id.")
        return HttpResponse(status=200)

    try:
        purchase = Purchase.objects.get(
            razorpay_payment_link_id=payment_link_id
        )
    except Purchase.DoesNotExist:
        logger.warning(
            "Webhook for unknown payment_link_id=%s", payment_link_id
        )
        return HttpResponse(status=200)

    _confirm_purchase(purchase.id, payment_id)

    return HttpResponse(status=200)