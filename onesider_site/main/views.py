from django.shortcuts import render
from projects.models import Category, Project

# Create your views here.

def home(request):

	categories = Category.objects.order_by('name')
	random_projects = Project.objects.filter(is_active=True).order_by('?')[:4]

	latest_projects = Project.objects.filter(is_active=True).order_by('-created_at')[:6]

	context = {
		'categories': categories,
		'random_projects': random_projects,
		'latest_projects': latest_projects,
	}

	return render(request, 'main/Home (Latest).html', context)