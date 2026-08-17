from django.contrib import admin
from .models import Category, Tag, Project, ProjectMedia

# Register your models here.

admin.site.register(Category)
admin.site.register(Tag)

class ProjectMediaInline(admin.TabularInline):
    model = ProjectMedia
    extra = 1

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug', 'price', 'is_active', 'is_featured')
    list_editable = ('is_featured',)
    readonly_fields = ('slug',)
    inlines = [ProjectMediaInline]