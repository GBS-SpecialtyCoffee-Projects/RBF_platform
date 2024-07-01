from django.shortcuts import render, redirect
from base.views.forms import FarmerPhotoForm, RoasterForm, RoasterPhotoForm
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from .forms import SignupForm, SigninForm, PasswordResetForm
from django.http import HttpResponse
from django.contrib.auth import get_user_model


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
