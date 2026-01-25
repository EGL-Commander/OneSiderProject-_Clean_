from django.urls import path
from . import views

urlpatterns = [
    path('', views.project_list, name='project_list'),
    path('search/', views.project_search, name='project_search'),
    path('category/<slug:category_slug>/', views.category_projects, name='category_projects'),
    path('<slug:slug>/save/', views.toggle_save, name='toggle_save'),
    path('<slug:slug>/buy/', views.buy_project, name='buy_project'),
    path('<slug:slug>/download/', views.download_project, name='download_project'),
    path('<slug:slug>/', views.project_detail, name='project_detail'),
]