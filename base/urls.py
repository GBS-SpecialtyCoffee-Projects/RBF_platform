# user_management/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.landing_page, name='landing_page'),
    path('farmers/', views.farmers, name='farmers'),
    path('roasters/', views.roasters, name='roasters'),
    path('create_account/', views.create_account, name='create_account'),
    path('farmer_dashboard/', views.farmer_dashboard, name='farmer_dashboard'),
    path('upload/', views.upload_photo, name='upload_photo'),
    path('upload/success/', views.upload_success, name='upload_success'),
    path('add_roaster/', views.add_roaster, name='add_roaster'),
    path('add_roaster/success/', views.add_roaster_success, name='add_roaster_success'),
    path('add_roaster_photo/', views.add_roaster_photo, name='add_roaster_photo'),
    path('add_roaster_photo/success/', views.add_roaster_photo_success, name='add_roaster_photo_success'),
]

