from django.shortcuts import render, redirect
from base.views.forms import FarmerPhotoForm, RoasterForm, RoasterPhotoForm
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from .forms import SignupForm, SigninForm, PasswordResetForm
from django.http import HttpResponse
from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.contrib.sites.shortcuts import get_current_site
from base.tokens import account_activation_token
from django.core.mail import EmailMessage
from django.utils.encoding import force_bytes, force_str
from base.models import User


def landing_page(request):
    return render(request, 'base/landing_page.html')


User = get_user_model()

def signup_view(request):
    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            request.session['username'] = user.username
            return redirect('signin')
    else:
        form = SignupForm()
    return render(request, 'base/signup.html', {'form': form})

def signin_view(request):
    if request.method == 'POST':
        form = SigninForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('email')
            password = form.cleaned_data.get('password')
            try:
                user = User.objects.get(email=email)
                if user.check_password(password):
                    login(request, user)
                    request.session['username'] = user.username
                    if user.group == 'farmer':
                        return redirect('farmer_dashboard')
                    else:
                        return redirect('roaster_dashboard')
                else:
                    messages.error(request, 'Invalid email or password.')
            except User.DoesNotExist:
                messages.error(request, 'Invalid email or password.')
        else:
            messages.error(request, 'Invalid email or password.')
    else:
        form = SigninForm()
    return render(request, 'base/signin.html', {'form': form})


def signout_view(request):
    logout(request)  # This destroys the session
    return redirect('signin')


def password_reset_view(request):
    if request.method == 'POST':
        form = PasswordResetForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('email')
            password = form.cleaned_data.get('password')

            try:
                user = User.objects.get(email=email)

                user.set_password(password)
                user.save()
                messages.success(request, 'Your password has been successfully reset.')
                return redirect('signin')
            except User.DoesNotExist:
                messages.error(request, 'No user found with this username or email address.')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = PasswordResetForm()

    return render(request, 'base/password_reset.html', {'form': form})

def email_verify(request):
    return render(request, 'base/email_verify.html')

def verify_email(request):
    try:
        # get the user 
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
        return redirect('landing_page')
    else:
        messages.error(request, "Activation link is invalid!")

    return redirect('email_verify')

def farmer_onboarding(request):
    return render(request, 'base/onboarding.html')
