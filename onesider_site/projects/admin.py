from django.contrib import admin
from .models import Category, Tag, Project

# Register your models here.

admin.site.register(Category)
admin.site.register(Tag)
admin.site.register(Project)