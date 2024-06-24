# user_management/views.py
from django.shortcuts import render, redirect
from django.conf import settings
from .forms import FarmerPhotoForm, RoasterForm, RoasterPhotoForm

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
