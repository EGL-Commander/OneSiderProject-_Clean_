from django.urls import path
from . import views

urlpatterns = [
    path('', views.project_list, name='project_list'),
    path('category/<slug:category_slug>/', views.category_projects, name='category_projects'),
    path('<slug:slug>/', views.project_detail, name='project_detail'),
]