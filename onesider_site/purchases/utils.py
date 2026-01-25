from django.utils import timezone
from .models import DownloadToken

def cleanup_expired_tokens():
    DownloadToken.objects.filter(
        expires_at__lt=timezone.now()
    ).delete()