from django.shortcuts import render, get_object_or_404, redirect
from .models import Project, Category, Project
from django.db.models import Q, F
from django.contrib.auth.decorators import login_required
from purchases.models import Purchase, DownloadToken
from projects.models import Project
from django.http import HttpResponse, HttpResponseForbidden
from django.utils import timezone

# Create your views here.

def project_list(request):
    projects = Project.objects.filter(is_active=True).order_by('?')
    return render(request, 'projects/project_list.html', {'projects': projects})

def project_detail(request, slug):
    project = get_object_or_404(Project, slug=slug, is_active=True)

    Project.objects.filter(pk=project.pk).update(views_count=F('views_count') + 1)
    project.refresh_from_db(fields=['views_count', 'purchases_count', 'saves_count'])

    has_purchased = False
    if request.user.is_authenticated:
        has_purchased = Purchase.objects.filter(
            user=request.user,
            project=project,
            status='success'
        ).exists()

    return render(request, 'projects/project_detail.html', {
        'project': project,
        'has_purchased': has_purchased
        })

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

@login_required
def toggle_save(request, slug):
    project = get_object_or_404(Project, slug=slug, is_active=True)
    profile = request.user.profile

    if profile.saved_projects.filter(pk=project.pk).exists():
        profile.saved_projects.remove(project)
    else:
        profile.saved_projects.add(project)

    true_count = project.saved_by.count()
    Project.objects.filter(pk=project.pk).update(saves_count=true_count)

    return redirect('project_detail', slug=project.slug)

@login_required
def buy_project(request, slug):
    project = get_object_or_404(Project, slug=slug, is_active=True)
    user = request.user

    purchase, created = Purchase.objects.get_or_create(
        user=user,
        project=project,
        defaults={'status': 'success'}
    )

    if not created and purchase.status != 'success':
        purchase.status = 'success'
        purchase.save(update_fields=['status'])

    true_count = project.purchases.filter(status='success').count()
    Project.objects.filter(pk=project.pk).update(purchases_count=true_count)

    return redirect('project_detail', slug=project.slug)

@login_required
def download_project(request, slug):
    project = get_object_or_404(Project, slug=slug, is_active=True)

    has_access = Purchase.objects.filter(
        user=request.user,
        project=project,
        status='success'
    ).exists()

    if not has_access:
        return HttpResponseForbidden("You have not purchased this project.")

    token = DownloadToken.objects.create(
        user = request.user,
        project=project
    )

    return redirect('download_token', token=token.token)

@login_required
def download_with_token(request, token):
    token_obj = get_object_or_404(DownloadToken, token=token)

    if token_obj.user != request.user:
        return HttpResponseForbidden("Invalid token.")

    if not token_obj.is_valid():
        return HttpResponseForbidden("Token expired or already used.")

    token_obj.is_used = True
    token_obj.save(update_fields=['is_used'])

    return HttpResponse(
        f"✅ Authorized download\n\n"
        f"Project: {token_obj.project.title}\n"
        f"Storage: {token_obj.project.get_cloud_storage_type_display()}\n"
        f"File ID: {token_obj.project.cloud_file_id}\n\n"
        f"(Cloud delivery comes next)"
    )