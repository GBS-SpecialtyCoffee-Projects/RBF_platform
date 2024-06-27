from django.shortcuts import render, redirect
from base.views.forms import FarmerPhotoForm, RoasterForm, RoasterPhotoForm


def farmer_dashboard(request):
    return render(request, 'base/farmer_dashboard.html')

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

def language_select(request):
    return render(request, 'base/language_select.html')
