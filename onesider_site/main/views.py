from django.shortcuts import render
from projects.models import Category, Project

# Create your views here.

def home(request):

	categories = Category.objects.order_by('name')
	random_projects = Project.objects.filter(is_active=True).order_by('?')[:4]

	context = {
		'categories': categories,
		'random_projects': random_projects,
	}

	return render(request, 'main/home.html', context)