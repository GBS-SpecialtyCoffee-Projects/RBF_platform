# user_management/urls.py
from django.urls import path
from .views import account, farmer,roaster
from django.conf import settings
from django.conf.urls.static import static
urlpatterns = [
    path('', account.landing_page, name='landing_page'),
    path('onboarding/', account.farmer_onboarding, name='onboarding'),
    path('farmer_dashboard/', farmer.farmer_dashboard, name='farmer_dashboard'),
    path('roaster_dashboard/', roaster.roaster_dashboard, name='roaster_dashboard'),
    path('request_meeting/<int:user_id>/', roaster.request_meeting, name='request_meeting'),
    path('manage_meeting_request/<int:meeting_id>/<str:action>/', roaster.manage_meeting_request,name='manage_meeting_request'),
    path('email_verify/', account.email_verify, name='email_verify'),
    path('verify_email/', account.verify_email, name='verify_email'),
    path('activate/<uidb64>/<token>', account.activate, name='activate'),
    path('upload/', farmer.upload_photo, name='upload_photo'),
    path('upload/success/', farmer.upload_success, name='upload_success'),
    path('add_roaster/', roaster.add_roaster, name='add_roaster'),
    path('add_roaster/success/', roaster.add_roaster_success, name='add_roaster_success'),
    path('add_roaster_photo/', roaster.add_roaster_photo, name='add_roaster_photo'),
    path('add_roaster_photo/success/', roaster.add_roaster_photo_success, name='add_roaster_photo_success'),
    path('check_user/', account.check_user, name='check_user'),
    path('signup/', account.signup_view, name='signup'),
    path('signin/', account.signin_view, name='signin'),
    path('signout/', account.signout_view, name='signout'),
    #path('reset_password/', account.password_reset_view, name='reset_password'),
    #path('reset_password/<str:email>/', account.password_reset_view, name='reset_password'),
    path('reset_password/<uidb64>/<token>/', account.password_reset_view, name='reset_password'),
    path('language_select/', account.language_select, name='language_select'),
    path('enter_email/', account.enter_email, name='enter_email'),
    path('translation-test/', account.translation_test_view, name='translation_test'),
    path('test/',account.test,name='test'),
    path('farmer/details/', account.farmer_details, name='farmer_details'),
    path('roaster/details/', account.roaster_details, name='roaster_details'),
    path('reset_password/', account.password_reset_view, name='reset_password'),
    path('language_select/', account.language_select, name='language_select'),
    path('farmer_orientation/', farmer.farmer_orientation, name='farmer_orientation'),
    #    path('signout/', account.signout_view, name='signout'),
    path('update_profile/', farmer.update_profile, name='update_profile'),
    path('delete_roaster_photo/<int:photo_id>/', roaster.delete_roaster_photo, name='delete_roaster_photo'),
    path('connections/', roaster.connections, name='connections'),
    path('farmer/<int:user_id>/', roaster.farmer_view, name='farmer_profile'),
    path('delete_farmer_photo/<int:photo_id>/', farmer.delete_farmer_photo, name='delete_farmer_photo'),
    path('farmer_details_edit/', farmer.edit_farmer_details, name='edit_farmer_details'),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
