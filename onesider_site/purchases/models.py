from django.db import models
from django.conf import settings
from projects.models import Project

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
        choices = STATUS_CHOICES
    )

    purchased_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'project')

    def __str__(self):
        return f"{self.user} → {self.project} ({self.status})"