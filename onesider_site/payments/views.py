from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db import transaction
from django.conf import settings

from projects.models import Project
from purchases.models import Purchase

from .services import client


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

        "description": project.title,

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
            'status': 'failed',
            'razorpay_payment_link_id': payment_link['id']
        }
    )

    return JsonResponse({

        "payment_url": payment_link["short_url"]

    })

@login_required
@require_POST
def verify_payment(request):

    razorpay_payment_id = request.POST.get(
        'razorpay_payment_id'
    )

    razorpay_order_id = request.POST.get(
        'razorpay_order_id'
    )

    razorpay_signature = request.POST.get(
        'razorpay_signature'
    )

    purchase_id = request.POST.get(
        'purchase_id'
    )

    if not all([
        razorpay_payment_id,
        razorpay_order_id,
        razorpay_signature,
        purchase_id
    ]):

        return JsonResponse(
            {
                'error':
                    'Missing payment information.'
            },
            status=400
        )

    purchase = get_object_or_404(
        Purchase,
        id=purchase_id,
        user=request.user
    )

    # Make sure this payment belongs
    # to the order we created
    if purchase.razorpay_order_id != (
        razorpay_order_id
    ):

        return JsonResponse(
            {
                'error':
                    'Order mismatch.'
            },
            status=400
        )

    try:

        client.utility.verify_payment_signature({

            'razorpay_order_id':
                razorpay_order_id,

            'razorpay_payment_id':
                razorpay_payment_id,

            'razorpay_signature':
                razorpay_signature

        })

    except Exception:

        return JsonResponse(
            {
                'error':
                    'Payment verification failed.'
            },
            status=400
        )

    purchase.status = 'success'

    purchase.razorpay_payment_id = (
        razorpay_payment_id
    )

    purchase.save()

    return JsonResponse({

        'success': True,

        'download_url':
            f'/projects/download/'
            f'{purchase.project.slug}/'

    })

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

    # Payment failed
    if payment_status != "paid":

        return JsonResponse(
            {
                "error": "Payment failed."
            },
            status=400
        )

    purchase = get_object_or_404(

        Purchase,

        razorpay_payment_link_id=payment_link_id,

        user=request.user

    )

    # Verify from Razorpay API
    try:

        payment = client.payment.fetch(
            payment_id
        )

        if payment["status"] != "captured":

            return JsonResponse(
                {
                    "error": "Payment not captured."
                },
                status=400
            )

    except Exception as e:

        return JsonResponse(
            {
                "error": str(e)
            },
            status=400
        )

    purchase.status = "success"

    purchase.razorpay_payment_id = payment_id

    purchase.save()

    return redirect(
        "project_detail",
        slug=purchase.project.slug
    )