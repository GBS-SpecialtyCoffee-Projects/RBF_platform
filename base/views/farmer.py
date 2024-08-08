from django.shortcuts import render, redirect,get_object_or_404
from base.views.forms import FarmerPhotoForm, RoasterForm, RoasterPhotoForm, FarmerProfileForm, RoasterProfileForm
from base.models import Roaster, MeetingRequest, Farmer,FarmerPhoto
from django.contrib import messages

def farmer_dashboard(request):
    return(render(request, 'base/farmer_dashboard.html'))
# def farmer_dashboard(request):
#     if request.user.group != 'farmer':
#         return redirect('roaster_dashboard')

#     roasters = Roaster.objects.all()
#     meeting_requests_as_requestee = MeetingRequest.objects.filter(requestee=request.user)
#     meeting_requests_as_requester = MeetingRequest.objects.filter(requester=request.user)
#     farmer_profile = Farmer.objects.filter(user=request.user).first()
#     farmer_photos = FarmerPhoto.objects.filter(user=request.user)
#     pending_meetings = MeetingRequest.objects.filter(
#         requester=request.user, status='accepted'
#     ) | MeetingRequest.objects.filter(
#         requestee=request.user, status='accepted'
#     )

#     # Check the number of pending or accepted meetings
#     active_meetings_count = MeetingRequest.objects.filter(
#         requester=request.user, status__in=['pending', 'accepted']
#     ).count()

#     can_request_meetings = active_meetings_count < 5

#     if request.method == 'POST':
#         form = FarmerProfileForm(request.POST, instance=farmer_profile)
#         if form.is_valid():
#             form.save()
#             return redirect('farmer_dashboard')
#     else:
#         form = FarmerProfileForm(instance=farmer_profile)
#     return render(request, 'base/farmer_dashboard.html', {
#         'roasters': roasters,
#         'meeting_requests_as_requestee': meeting_requests_as_requestee,
#         'meeting_requests_as_requester': meeting_requests_as_requester,
#         'farmer_profile': farmer_profile,
#         'farmer_photos': farmer_photos,
#         'pending_meetings': pending_meetings,
#         'can_request_meetings': can_request_meetings,
#         'form': form,
#     })


def upload_photo(request):
    if request.method == 'POST':
        form = FarmerPhotoForm(request.POST, request.FILES)
        if form.is_valid():
            farmer_photo = form.save(commit=False)
            farmer_photo.user = request.user  # Set the user to the currently logged-in user
            farmer_photo.clean()  # Validate the roaster_photo instance
            farmer_photo.save()
            return redirect('add_roaster_photo_success')
    else:
        form = FarmerPhotoForm()
    return render(request, 'base/upload_photo.html', {'form': form})

def upload_success(request):
    return render(request, 'base/upload_success.html')
