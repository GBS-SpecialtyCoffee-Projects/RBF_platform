# user_management/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.landing_page, name='landing_page'),
    path('farmers/', views.farmers, name='farmers'),
    path('roasters/', views.roasters, name='roasters'),
    path('create_account/', views.create_account, name='create_account'),
    path('farmer_dashboard/', views.farmer_dashboard, name='farmer_dashboard'),
]
