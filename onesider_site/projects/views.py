from django.shortcuts import render, get_object_or_404
from .models import Project, Category
from django.db.models import Q

# Create your views here.

def project_list(request):
    projects = Project.objects.filter(is_active=True).order_by('?')
    return render(request, 'projects/project_list.html', {'projects': projects})

def project_detail(request, slug):
    project = get_object_or_404(Project, slug=slug, is_active=True)
    return render(request, 'projects/project_detail.html', {'project': project})

def category_projects(request, category_slug):
    category = get_object_or_404(Category, slug = category_slug)
    projects = Project.objects.filter(
        categories = category,
        is_active = True,
    ).order_by('?')

    return render(
        request,
        'projects/category_projects.html',
        {
            'category' : category,
            'projects' : projects
        }
    )

def project_search(request):
    q = request.GET.get('q', '').strip()

    projects = Project.objects.filter(is_active=True)

    if q:
        projects = projects.filter(
            Q(title__icontains=q) |
            Q(short_description__icontains=q) |
            Q(description__icontains=q) |
            Q(tags__name__icontains=q) |
            Q(categories__name__icontains=q)
        ).distinct()

    return render(request, 'projects/project_search.html', {'projects': projects, 'q': q})