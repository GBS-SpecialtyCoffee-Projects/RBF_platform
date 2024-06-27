from django.shortcuts import render, redirect
from base.views.forms import FarmerPhotoForm, RoasterForm, RoasterPhotoForm


def roaster_dashboard(request):
    return render(request, 'base/roaster_dashboard.html')

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
            return redirect('add_roaster_photo_success')
    else:
        form = RoasterPhotoForm()
    return render(request, 'base/add_roaster_photo.html', {'form': form})

def add_roaster_photo_success(request):
    return render(request, 'base/add_roaster_photo_success.html')

def language_select(request):
    return render(request, 'base/language_select.html')
