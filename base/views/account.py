from django.shortcuts import render, redirect
from base.views.forms import FarmerPhotoForm, RoasterForm, RoasterPhotoForm
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from .forms import SignupForm, SigninForm, PasswordResetForm
from django.http import HttpResponse
from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import EmailMessage
from django.contrib.sites.shortcuts import get_current_site
from django.contrib import messages
from django.contrib.auth import get_user_model
from .tokens import account_activation_token
from base.models import User
from django.utils import translation
from django.conf import settings
from django.http import JsonResponse
from django.urls import reverse
from django.contrib.auth.tokens import default_token_generator






def landing_page(request):
    return render(request, 'base/landing_page.html')

def language_select(request):
    return render(request, 'base/language_select.html')


User = get_user_model()

def check_user(request):
    username = request.GET.get('username', None)
    email = request.GET.get('email', None)
    data = {
        'username_exists': User.objects.filter(username=username).exists() if username else False,
        'email_exists': User.objects.filter(email=email).exists() if email else False
    }
    return JsonResponse(data)

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
            user = form.authenticate_user()
            if user:
                login(request, user)
                request.session['username'] = user.username
                if user.group == 'farmer':
                    redirect_url = reverse('farmer_dashboard')
                else:
                    redirect_url = reverse('roaster_dashboard')

                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({'success': True, 'redirect_url': redirect_url})
                else:
                    return redirect(redirect_url)
            else:
                message = 'Invalid email or password.'
        else:
            message = 'Invalid email or password.'

        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': message})
        else:
            messages.error(request, message)
    else:
        form = SigninForm()

    return render(request, 'base/signin.html', {'form': form})

def signout_view(request):
    logout(request)  # This destroys the session
    return redirect('signin')




def password_reset_view(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        if request.method == 'POST':
            form = PasswordResetForm(request.POST)
            if form.is_valid():
                password = form.cleaned_data.get('password')
                user.set_password(password)
                user.save()
                #messages.success(request, 'Your password has been successfully reset.')
                return redirect('signin')
            else:
                messages.error(request, 'Please correct the errors below.')
        else:
            form = PasswordResetForm()
        return render(request, 'base/password_reset.html', {'form': form})
    else:
        messages.error(request, "Password reset link is invalid!")
        return redirect('email_verify')


def email_verify(request):
    return render(request, 'base/email_verify.html')


def verify_email(request, email):
    try:
        user = User.objects.get(email=email)
        mail_subject = 'Password reset verification'
        message = render_to_string('base/template_verify_email.html', {
            'user': user,
            'domain': get_current_site(request).domain,
            'uid': urlsafe_base64_encode(force_bytes(user.pk)),
            'token': default_token_generator.make_token(user),
            'protocol': 'https' if request.is_secure() else 'http'
        })
        email_message = EmailMessage(mail_subject, message, to=[user.email])
        if email_message.send():
            messages.success(request, 'Please check your email to reset your password.')
        else:
            messages.error(request, 'Failed to send the email. Please try again.')
    except User.DoesNotExist:
        messages.error(request, 'No user is associated with this email address.')
    return redirect('email_verify')


def activate(request, uidb64, token):
    User = get_user_model()
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        #messages.success(request, "Your email has been verified. You can now reset your password.")
        return redirect('reset_password', uidb64=uidb64, token=token)
    else:
        messages.error(request, "Activation link is invalid!")
        return redirect('email_verify')


def enter_email(request):
    if request.method == 'POST':
        email = request.POST['email']
        return redirect('verify_email', email=email)
    return render(request, 'base/enter_email.html')











def translation_test_view(request):
    user_language = 'zh-hans'  # Change this dynamically based on user preference if needed
    translation.activate(user_language)
    request.session[settings.LANGUAGE_COOKIE_NAME] = user_language
    return render(request, 'base/translation_test.html')

def test(request):
    return render(request,'base/test.html')
