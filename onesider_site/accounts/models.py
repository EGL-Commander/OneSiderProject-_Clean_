from django.db import models
from django.contrib.auth.models import User
from projects.models import Project

# Create your models here.

class AvatarChoices(models.IntegerChoices):
    AVATAR_1 = 1, 'Avatar One'
    AVATAR_2 = 2, 'Avatar Two'
    AVATAR_3 = 3, 'Avatar Three'
    AVATAR_4 = 4, 'Avatar Four'
    AVATAR_5 = 5, 'Avatar Five'
    AVATAR_6 = 6, 'Avatar Six'
    AVATAR_7 = 7, 'Avatar Seven'

class Profile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE
    )
    display_name = models.CharField(max_length=50)

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

    avatar = models.PositiveSmallIntegerField(
        choices = AvatarChoices.choices,
        default = AvatarChoices.AVATAR_1
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user.username