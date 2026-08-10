from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from .forms import ProfileUpdateForm
from projects.models import Project
from .forms import RegisterForm

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

    owned_project_ids = set(
        purchased_projects.values_list('id', flat=True)
    )

    return render(
        request,
        "accounts/Profile (Latest).html",
        {
            "profile": profile,
            "saved_projects": saved_projects,
            "purchased_projects": purchased_projects,
            "owned_project_ids": owned_project_ids,
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

def register_view(request):

    if request.method == "POST":

        form = RegisterForm(request.POST)

        if form.is_valid():

            user = form.save()

            login(request, user)

            return redirect("project_list")

    else:

        form = RegisterForm()

    return render(
        request,
        "accounts/Register.html",
        {
            "form": form
        }
    )

@login_required
def library_view(request):

    purchased_projects = (
        Project.objects.filter(
            purchases__user=request.user,
            purchases__status="success"
        )
        .prefetch_related("categories")
        .distinct()
    )

    return render(
        request,
        "accounts/Library.html",
        {
            "purchased_projects": purchased_projects,
        }
    )