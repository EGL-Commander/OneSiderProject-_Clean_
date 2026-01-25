from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .forms import ProfileUpdateForm

# Create your views here.

@login_required
def edit_profile(request):
    profile = request.user.profile
    saved_projects = profile.saved_projects.all()
    
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            return redirect('profile_edit')
    else:
        form = ProfileUpdateForm(instance=profile)

    return render(
        request,
        'accounts/edit_profile.html',
        {
            'form' : form,
            'saved_projects': saved_projects
            }
        )