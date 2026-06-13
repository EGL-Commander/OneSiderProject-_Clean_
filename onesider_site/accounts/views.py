from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .forms import ProfileUpdateForm
from projects.models import Project

# Create your views here.

@login_required
def profile_view(request):
    profile = request.user.profile

    saved_projects = (
        profile.saved_projects
        .select_related()
        .prefetch_related('categories')
    )

    purchased_projects = (
        Project.objects.filter(
            purchases__user=request.user,
            purchases__status='success'
        )
        .prefetch_related('categories')
        .distinct()
    )

    return render(
        request,
        "accounts/Profile (Latest).html",
        {
            "profile": profile,
            "saved_projects": saved_projects,
            "purchased_projects": purchased_projects,
        }
    )

@login_required
def edit_profile(request):
    profile = request.user.profile
    
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            return redirect('profile')
    else:
        form = ProfileUpdateForm(instance=profile)    

    return render(request,'accounts/Edit Profile.html',{'form' : form})