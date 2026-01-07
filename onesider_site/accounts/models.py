from django.db import models
from django.contrib.auth.models import User
from projects.models import Project

# Create your models here.

class Profile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE
    )

    purchased_projects = models.ManyToManyField(
        Project,
        related_name='buyers',
        blank=True
    )

    saved_projects = models.ManyToManyField(
        Project,
        related_name='saved_by',
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user.username