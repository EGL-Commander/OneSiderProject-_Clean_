from django.urls import path
from . import views

urlpatterns = [
    path('', views.project_list, name='project_list'),
    path('api/', views.project_list_api, name='project_list_api'),
    path('<slug:slug>/save/', views.toggle_save, name='toggle_save'),
    path('<slug:slug>/buy/', views.buy_project, name='buy_project'),
    path('<slug:slug>/download/', views.download_project, name='download_project'),
    path('download/token/<uuid:token>/', views.download_with_token, name='download_token'),
    path('<slug:slug>/', views.project_detail, name='project_detail'),
]