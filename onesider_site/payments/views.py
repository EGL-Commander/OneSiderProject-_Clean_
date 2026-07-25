from django.shortcuts import get_object_or_404
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

    razorpay_order = client.order.create({
        'amount': amount,
        'currency': 'INR',
        'receipt': f'project_{project.id}_user_{request.user.id}',
        'notes': {
            'project_id': str(project.id),
            'user_id': str(request.user.id),
        }
    })

    purchase, created = Purchase.objects.update_or_create(
        user=request.user,
        project=project,
        defaults={
            'status': 'failed',
            'razorpay_order_id': razorpay_order['id']
        }
    )

    return JsonResponse({
        'order_id': razorpay_order['id'],
        'amount': amount,
        'currency': 'INR',
        'key_id': settings.RAZORPAY_KEY_ID,
        'project_title': project.title,
        'purchase_id': purchase.id,
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