from django.db import models
from django.utils.text import slugify

# Create your models here.


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True)
    description = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
    

class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=60, unique=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Project(models.Model):

    title = models.CharField(max_length=200)
    slug = models.SlugField(
        max_length=220, unique=True, blank=True, editable=False
        )

    short_description = models.CharField(max_length=300)
    description = models.TextField()

    categories = models.ManyToManyField(Category, related_name='projects')
    tags = models.ManyToManyField(Tag, related_name='projects', blank=True)

    PROJECT_TYPE_CHOICES = [
        ('web', 'Web Application'),
        ('mobile', 'Mobile Application'),
        ('game', 'Game'),
        ('tool', 'Tool / Utility'),
        ('other', 'Other'),
    ]

    project_type = models.CharField(
        max_length=20,
        choices=PROJECT_TYPE_CHOICES,
    )

    price = models.DecimalField(max_digits=8, decimal_places=2)

    thumbnail = models.ImageField(
        upload_to='project_thumbnails/',
        null=True,
        blank=True
        )

    views_count = models.PositiveIntegerField(default=0)
    purchases_count = models.PositiveIntegerField(default=0)
    saves_count = models.PositiveIntegerField(default=0)

    CLOUD_STORAGE_CHOICES = [
        ('gdrive', 'Google Drive'),
        ('dropbox', 'Dropbox'),
        ('onedrive', 'OneDrive'),
        ('other', 'Other'),
    ]

    cloud_storage_type = models.CharField(
        max_length=20,
        choices=CLOUD_STORAGE_CHOICES
    )


    cloud_file_id = models.CharField(
        max_length=255,
        help_text="Internal cloud file/folder ID (NOT a public link)"
        )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            slug =base_slug
            counter = 1

            while Project.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1

            self.slug = slug

        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class ProjectMedia(models.Model):

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='additional_media'
    )

    image = models.ImageField(
        upload_to='project_media/'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.image.name