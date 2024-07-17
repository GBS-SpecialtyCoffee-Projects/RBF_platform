from django.shortcuts import render, redirect,get_object_or_404
from base.views.forms import FarmerPhotoForm, RoasterForm, RoasterPhotoForm, MeetingRequestForm,RoasterProfileForm
from base.models import Farmer, MeetingRequest, RoasterPhoto,Roaster
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.contrib import messages


def roaster_dashboard(request):
    if request.user.group != 'roaster':
        return redirect('farmer_dashboard')

    farmers = Farmer.objects.all()
    meeting_requests_as_requestee = MeetingRequest.objects.filter(requestee=request.user)
    meeting_requests_as_requester = MeetingRequest.objects.filter(requester=request.user)
    roaster_profile = Roaster.objects.filter(user=request.user).first()
    roaster_photos = RoasterPhoto.objects.filter(user=request.user)
    pending_meetings = MeetingRequest.objects.filter(
        requester=request.user, status='accepted'
    ) | MeetingRequest.objects.filter(
        requestee=request.user, status='accepted'
    )

    # Check the number of pending or accepted meetings
    active_meetings_count = MeetingRequest.objects.filter(
        requester=request.user, status__in=['pending', 'accepted']
    ).count()

    can_request_meetings = active_meetings_count < 5

    if request.method == 'POST':
        form = RoasterProfileForm(request.POST, instance=roaster_profile)
        if form.is_valid():
            form.save()
            return redirect('roaster_dashboard')
    else:
        form = RoasterProfileForm(instance=roaster_profile)

    return render(request, 'base/roaster_dashboard.html', {
        'farmers': farmers,
        'meeting_requests_as_requestee': meeting_requests_as_requestee,
        'meeting_requests_as_requester': meeting_requests_as_requester,
        'roaster_profile': roaster_profile,
        'roaster_photos': roaster_photos,
        'pending_meetings': pending_meetings,
        'can_request_meetings': can_request_meetings,
        'form': form,
    })


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
            roaster_photo = form.save(commit=False)
            roaster_photo.user = request.user  # Set the user to the currently logged-in user
            try:
                roaster_photo.clean()  # Validate the roaster_photo instance
                roaster_photo.save()
                return redirect('add_roaster_photo_success')
            except ValidationError as e:
                form.add_error(None, e)  # Add the validation error to the form
    else:
        form = RoasterPhotoForm()
    return render(request, 'base/add_roaster_photo.html', {'form': form})

def add_roaster_photo_success(request):
    return render(request, 'base/add_roaster_photo_success.html')

User = get_user_model()


def request_meeting(request, user_id):
    # Check the number of pending or accepted meetings the user has requested
    active_meetings_count = MeetingRequest.objects.filter(
        requester=request.user, status__in=['pending', 'accepted']
    ).count()

    if active_meetings_count >= 5:
        return redirect('farmer_dashboard' if request.user.group == 'farmer' else 'roaster_dashboard')

    if request.method == 'POST':
        form = MeetingRequestForm(request.POST)
        if form.is_valid():
            meeting_request = form.save(commit=False)
            meeting_request.requester = request.user
            meeting_request.requestee = get_object_or_404(User, id=user_id)

            if meeting_request.requester.group == meeting_request.requestee.group:
                form.add_error(None, ValidationError('Meeting requests must be between a farmer and a roaster.'))
            else:
                meeting_request.save()
                return redirect('farmer_dashboard' if request.user.group == 'farmer' else 'roaster_dashboard')
        else:
            messages.error(request, "Form is not valid. Errors: " + str(form.errors.as_json()))
    else:
        form = MeetingRequestForm()

    return render(request, 'base/request_meeting.html', {'form': form})


def manage_meeting_request(request, meeting_id, action):
    meeting_request = get_object_or_404(MeetingRequest, id=meeting_id, requestee=request.user)

    if action == 'accept':
        meeting_request.status = 'accepted'
    elif action == 'reject':
        meeting_request.status = 'rejected'

    meeting_request.save()
    return redirect('farmer_dashboard' if request.user.group == 'farmer' else 'roaster_dashboard')
