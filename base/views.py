# user_management/views.py
from django.shortcuts import render, redirect
from django.conf import settings
from .forms import FarmerPhotoForm, RoasterForm, RoasterPhotoForm
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import EmailMessage
from django.contrib.sites.shortcuts import get_current_site
from django.contrib import messages
from django.contrib.auth import get_user_model
from .tokens import account_activation_token
from .models import User

def landing_page(request):
    return render(request, 'base/landing_page.html')

def farmers(request):
    return render(request, 'base/farmers.html')

def roasters(request):
    return render(request, 'base/roasters.html')

def create_account(request):
    return render(request, 'base/create_account.html')

def farmer_dashboard(request):
    return render(request, 'base/farmer_dashboard.html')

# views.py

def upload_photo(request):
    if request.method == 'POST':
        form = FarmerPhotoForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('upload_success')
    else:
        form = FarmerPhotoForm()
    return render(request, 'base/upload_photo.html', {'form': form})

def upload_success(request):
    return render(request, 'base/upload_success.html')

def add_roaster(request):
    if request.method == 'POST':
        form = RoasterForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('base/add_roaster_success')
    else:
        form = RoasterForm()
    return render(request, 'base/add_roaster.html', {'form': form})

def add_roaster_success(request):
    return render(request, 'base/add_roaster_success.html')

def add_roaster_photo(request):
    if request.method == 'POST':
        form = RoasterPhotoForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('base/add_roaster_photo_success')
    else:
        form = RoasterPhotoForm()
    return render(request, 'base/add_roaster_photo.html', {'form': form})

def add_roaster_photo_success(request):
    return render(request, 'base/add_roaster_photo_success.html')

def email_verify(request):
    return render(request, 'base/email_verify.html')

def verify_email(request):
    try:
        user = User.objects.get(email='israelwhiz@gmail.com')
    except User.DoesNotExist:
        messages.error(request, 'User does not exist')
    mail_subject = 'Verify your email'
    message = render_to_string('base/template_verify_email.html', {
        'user': user.username,
        'domain': get_current_site(request).domain,
        'uid': urlsafe_base64_encode(force_bytes(user.pk)),
        'token': account_activation_token.make_token(user),
        'protocol': 'https' if request.is_secure() else 'http'
    })
    email = EmailMessage(
        mail_subject, message, to=[user.email]
    )
    if email.send(): 
       messages.success(request, f'Dear {user.username}, please check your email to confirm your registration.')
    else:
       messages.error(request, 'Something went wrong. Please try again.')
    return render(request, 'base/email_verify.html')

def activate(request, uidb64, token):
    User = get_user_model()
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except:
        user = None

    if user is not None and account_activation_token.check_token(user, token):
        user.is_active = True
        user.save()

        messages.success(request, "Thank you for your email confirmation. Now you can login your account.")
        return redirect('login')
    else:
        messages.error(request, "Activation link is invalid!")

    return redirect('email_verify')
    