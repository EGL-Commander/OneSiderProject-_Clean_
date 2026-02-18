import uuid
from django.db import models
from django.conf import settings
from projects.models import Project
from django.utils import timezone
from datetime import timedelta

# Create your models here.

class Purchase(models.Model):
    STATUS_CHOICES = (
        ('success', 'Success'),
        ('failed', 'Failed')
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='purchases'
    )

    project = models.ForeignKey(
        Project,
        on_delete=models.PROTECT,
        related_name='purchases'
    )

    status = models.CharField(
        max_length=10,
        choices = STATUS_CHOICES,
        default='failed'
    )

    purchased_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'project')

    def __str__(self):
        return f"{self.user} → {self.project} ({self.status})"
   
class DownloadToken(models.Model):
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='download_tokens'
    )

    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='download_tokens'
    )

    is_used = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(minutes=10)
        super().save(*args, **kwargs)

    def is_valid(self):
        return (
            not self.is_used and
            timezone.now() < self.expires_at
        )

    def __str__(self):
        return f"{self.project.title} | {self.user.username}"