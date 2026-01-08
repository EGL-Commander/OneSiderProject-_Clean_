from django.contrib import admin
from .models import Category, Tag, Project

# Register your models here.

admin.site.register(Category)
admin.site.register(Tag)
# admin.site.register(Project)

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug', 'price', 'is_active')
    readonly_fields = ('slug',)