from django.urls import path
from django.views.generic import RedirectView
from . import views

urlpatterns = [
	path('', views.home, name='home'),

	path(
        'terms-and-conditions/',
        views.terms_and_conditions,
        name='terms_and_conditions'
    ),

    path(
        'privacy-policy/',
        views.privacy_policy,
        name='privacy_policy'
    ),
	
	path('home/', RedirectView.as_view(url='/', permanent=True)),
]