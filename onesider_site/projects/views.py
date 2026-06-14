from django.shortcuts import render, get_object_or_404, redirect
from .models import Project, Category
from django.db.models import Q, F
from django.contrib.auth.decorators import login_required
from purchases.models import Purchase, DownloadToken
from django.http import HttpResponseForbidden, FileResponse
from django.utils import timezone
from purchases.utils import cleanup_expired_tokens
from purchases.gdrive import download_file_bytes
from django.views.decorators.http import require_http_methods, require_POST
from django.conf import settings
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.urls import reverse

# Create your views here.

def project_list(request):
    categories = Category.objects.all()

    return render(request, 'projects/Gallery Project List (Latest).html', {'categories' : categories})

def project_list_api(request):

    projects = Project.objects.filter(
        is_active=True
    ).order_by('-created_at')

    category = request.GET.get('category')
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')

    if category:
        projects = projects.filter(
            categories__slug=category
        )

    if min_price:
        projects = projects.filter(
            price__gte=min_price
        )

    if max_price:
        projects = projects.filter(
            price__lte=max_price
        )

    projects = projects.distinct()

    paginator = Paginator(projects, 12)

    page_number = request.GET.get('page', 1)

    page_obj = paginator.get_page(page_number)

    data = []

    for project in page_obj:
        data.append({
            "title": project.title,
            "slug": project.slug,
            "price": str(project.price),
            "short_description": project.short_description,
            "thumbnail_url": (
                project.thumbnail.url
                if project.thumbnail
                else None
            )
        })

    return JsonResponse({
        "projects": data,
        "has_more": page_obj.has_next()
    })

def project_detail(request, slug):
    project = get_object_or_404(
        Project.objects.prefetch_related(
            'categories', 'tags'),
        slug=slug,
        is_active=True
    )

    viewed_projects = request.session.get('viewed_projects', [])

    if project.pk not in viewed_projects:
        Project.objects.filter(pk=project.pk).update(
            views_count=F('views_count') + 1
        )

        viewed_projects.append(project.pk)

        request.session['viewed_projects'] = viewed_projects[-100:]
    
    project.refresh_from_db(fields=['views_count', 'purchases_count', 'saves_count'])

    has_purchased = False
    is_saved = False
    if request.user.is_authenticated:
        has_purchased = Purchase.objects.filter(
            user=request.user,
            project=project,
            status='success'
        ).exists()

        is_saved = request.user.profile.saved_projects.filter(
            pk=project.pk
        ).exists()

    tags = project.tags.all()

    return render(request, 'projects/Project Detail (Latest).html', {
        'project': project,
        'has_purchased': has_purchased,
        'is_saved' : is_saved,
        'tags' : tags
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

    categories = Category.objects.all()

    category = request.GET.get('category')
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')

    projects = Project.objects.filter(is_active=True)

    if q:
        projects = projects.filter(
            Q(title__icontains=q) |
            Q(short_description__icontains=q) |
            Q(description__icontains=q) |
            Q(tags__name__icontains=q) |
            Q(categories__name__icontains=q)
        ).distinct()
    
    if category:
        projects = projects.filter(categories__slug=category)

    if min_price:
        projects = projects.filter(price__gte=min_price)

    if max_price:
        projects = projects.filter(price__lte=max_price)

    return render(request, 'projects/project_search.html', {
        'projects': projects,
        'q' : q,
        'selected_category' : category,
        'categories' : categories,
        })

@login_required
@require_POST
def toggle_save(request, slug):
    project = get_object_or_404(Project, slug=slug, is_active=True)
    profile = request.user.profile

    if profile.saved_projects.filter(pk=project.pk).exists():
        profile.saved_projects.remove(project)
    else:
        profile.saved_projects.add(project)

    true_count = project.saved_by.count()
    Project.objects.filter(pk=project.pk).update(saves_count=true_count)

    saved = profile.saved_projects.filter(pk=project.pk).exists()

    return JsonResponse({
        'saved' : saved,
        'saves_count' : true_count
    })

@login_required
@require_POST
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

    return JsonResponse({
        "success" : True,
        "purchases_count" : true_count,
        "download_url" : reverse(
            "download_project", 
            args=[project.slug]
        )
    })

@login_required
@require_http_methods(['GET', 'POST'])
def download_project(request, slug):
    project = get_object_or_404(Project, slug=slug, is_active=True)

    has_access = Purchase.objects.filter(
        user=request.user,
        project=project,
        status='success'
    ).exists()

    if not has_access:
        return HttpResponseForbidden("You have not purchased this project.")
    
    if request.method == 'GET':
        return render(request, 'projects/download_warning.html', {'project': project})
    
    cleanup_expired_tokens()

    recent_tokens = DownloadToken.objects.filter(
        user=request.user,
        project=project,
        created_at__gte=timezone.now() - timezone.timedelta(seconds=60)
    )

    if recent_tokens.exists():
        return HttpResponseForbidden("Please wait 60 Seconds before requesting another download.")


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
    
    try:
        filename, mimetype, fh = download_file_bytes(token_obj.project.cloud_file_id)
    except Exception as e:
        if settings.DEBUG:
            return HttpResponseForbidden(f"Drive fetch failed: {type(e).__name__} — {e}")
        return HttpResponseForbidden('Could not fetch file from Drive. Please try again later.')

    token_obj.is_used = True
    token_obj.save(update_fields=['is_used'])

    return FileResponse(
        fh,
        as_attachment=True,
        filename=filename,
        content_type=mimetype
    )