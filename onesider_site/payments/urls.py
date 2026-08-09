from django.urls import path
from . import views

urlpatterns = [
    
    path(
        'create-order/<slug:slug>/',
        views.create_order,
        name='create_order'
    ),

    path(
        "success/",
        views.payment_success,
        name="payment_success"
    ),

]