import json
import logging

from django.shortcuts import render, redirect
from django.urls import reverse
from django.conf import settings
from django.core.mail import send_mail
from django.db.models import F
from django.utils import timezone

from projects.models import Project
from .forms import ContactForm

from django.core.cache import cache

logger = logging.getLogger(__name__)

# Create your views here.

TRAY_SIZE = 8

CONTACT_RATE_LIMIT = 2
CONTACT_RATE_WINDOW = 60 * 60  # 15 minutes


def _serialize_tray_card(project):
    """
    Same shape the Home page's tray-rendering JS expects, and the same
    field set/pattern already used by projects.views.project_list_api,
    reused here for consistency rather than inventing a new shape.
    """
    return {
        "title": project.title,
        "slug": project.slug,
        "price": str(project.price),
        "short_description": project.short_description,
        "thumbnail_url": (
            project.thumbnail.url
            if project.thumbnail
            else None
        ),
    }


def home(request):

    base_qs = Project.objects.filter(is_active=True)

    most_purchased = base_qs.filter(
        purchases_count__gt=0
    ).order_by('-purchases_count', '-created_at')[:TRAY_SIZE]

    newly_added = base_qs.order_by('-created_at')[:TRAY_SIZE]

    commanders_choice = base_qs.filter(
        is_featured=True
    ).order_by('-created_at')[:TRAY_SIZE]

    # "Rising" = projects created recently that are already getting
    # traction, not just whatever's newest (that's "Newly Added") and
    # not all-time purchase leaders (that's "Most Purchased"). Reuses
    # the same engagement fields already tracked on Project - no new
    # model, no separate scoring system.
    rising_cutoff = timezone.now() - timezone.timedelta(days=60)
    rising = (
        base_qs
        .filter(created_at__gte=rising_cutoff)
        .annotate(
            engagement=(
                F('views_count')
                + F('purchases_count') * 5
                + F('saves_count') * 2
            )
        )
        .filter(engagement__gt=0)
        .order_by('-engagement')[:TRAY_SIZE]
    )

    tray_data = {
        "tray-most-purchased": [_serialize_tray_card(p) for p in most_purchased],
        "tray-newly-added": [_serialize_tray_card(p) for p in newly_added],
        "tray-commanders-choice": [_serialize_tray_card(p) for p in commanders_choice],
        "tray-rising": [_serialize_tray_card(p) for p in rising],
    }

    context = {
        'tray_data': json.dumps(tray_data),
    }

    return render(request, 'main/Home (Latest).html', context)


def terms_and_conditions(request):
    return render(
        request,
        'main/Terms and Conditions.html'
    )


def privacy_policy(request):
    return render(
        request,
        'main/Privacy Policy.html'
    )


def about(request):
    return render(request, 'main/About.html')


def contact(request):

    if request.method == 'POST':

        form = ContactForm(request.POST)

        if form.is_valid():

            if form.is_spam():
                # Pretend it worked - never reveal the honeypot to a bot.
                return redirect(f"{reverse('contact')}?sent=1")

            client_ip = request.META.get('REMOTE_ADDR', 'unknown')
            rate_limit_key = f"contact-rate:{client_ip}"

            submission_count = cache.get(rate_limit_key, 0)

            if submission_count >= CONTACT_RATE_LIMIT:
                return redirect(f"{reverse('contact')}?rate_limited=1")

            cache.set(
                rate_limit_key,
                submission_count + 1,
                CONTACT_RATE_WINDOW,
            )

            contact_message = form.save()

            notify_to = getattr(settings, 'CONTACT_NOTIFICATION_EMAIL', '')

            if notify_to:
                try:
                    send_mail(
                        subject=(
                            f"OneSider — Contact Notification — "
                            f"{contact_message.name}"
                        ),
                        message=(
                            f"From: {contact_message.name} "
                            f"<{contact_message.email}>\n\n"
                            f"{contact_message.message}"
                        ),
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[notify_to],
                        fail_silently=False,
                    )
                except Exception:
                    # The message is already saved and reviewable in
                    # admin regardless - a failed notification email
                    # must not turn into a broken/error response for
                    # the person who just submitted the form, and must
                    # never leak SMTP internals to them.
                    logger.exception(
                        "Failed to send contact notification email"
                    )

            return redirect(f"{reverse('contact')}?sent=1")

    else:
        form = ContactForm()

    sent = request.GET.get('sent') == '1'
    rate_limited = request.GET.get('rate_limited') == '1'

    return render(request, 'main/Contact.html', {
        'form': form,
        'sent': sent,
        'rate_limited': rate_limited,
    })