# user_management/urls.py
from django.urls import path
from .views import account, farmer,roaster

urlpatterns = [
    path('', account.landing_page, name='landing_page'),
    path('farmer_dashboard/', farmer.farmer_dashboard, name='farmer_dashboard'),
    path('roaster_dashboard/', roaster.roaster_dashboard, name='roaster_dashboard'),
    path('upload/', farmer.upload_photo, name='upload_photo'),
    path('upload/success/', farmer.upload_success, name='upload_success'),
    path('add_roaster/', roaster.add_roaster, name='add_roaster'),
    path('add_roaster/success/', roaster.add_roaster_success, name='add_roaster_success'),
    path('add_roaster_photo/', roaster.add_roaster_photo, name='add_roaster_photo'),
    path('add_roaster_photo/success/', roaster.add_roaster_photo_success, name='add_roaster_photo_success'),
    path('signup/', account.signup_view, name='signup'),
    path('signin/', account.signin_view, name='signin'),
    path('signout/', account.signout_view, name='signout'),
    path('reset_password/', account.password_reset_view, name='reset_password'),
    #    path('signout/', account.signout_view, name='signout'),
]

