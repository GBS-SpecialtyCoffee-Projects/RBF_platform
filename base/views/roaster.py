from django.shortcuts import render, redirect,get_object_or_404
from base.views.forms import FarmerPhotoForm, RoasterForm, RoasterPhotoForm, MeetingRequestForm,RoasterProfileForm, RoasterInfoForm, RoasterBioForm,RoasterSourcingForm
from base.models import Farmer, MeetingRequest, RoasterPhoto,Roaster
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.contrib import messages
import os

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
    total_meetings_used = 0

    # Check the number of pending or accepted meetings
    active_meetings_count = MeetingRequest.objects.filter(
        requester=request.user, status__in=['pending', 'accepted']
    ).count()

    can_request_meetings = active_meetings_count < 5

    for meeting_request in meeting_requests_as_requester:
        # Example of extracting time if necessary
        meeting_request.proposed_time = meeting_request.proposed_date.time() if hasattr(meeting_request.proposed_date,
                                                                                                    'time') else None
        # Calculate the number of used meeting requests
        pending_meetings_count = MeetingRequest.objects.filter(
            requester=request.user, status='pending'
        ).count()

        accepted_meetings_count = MeetingRequest.objects.filter(
            requester=request.user, status='accepted'
        ).count()

        total_meetings_used = pending_meetings_count + accepted_meetings_count

    if request.method == 'POST' and 'roaster_info_form' in request.POST:
        roaster_info_form = RoasterInfoForm(request.POST, request.FILES, instance=roaster_profile)
        if roaster_info_form.is_valid():
            roaster_info_form.save()
            return redirect('roaster_dashboard')
    else:
        roaster_info_form = RoasterInfoForm(instance=roaster_profile)

    # Handle the bio form
    if request.method == 'POST' and 'roaster_bio_form' in request.POST:
        roaster_bio_form = RoasterBioForm(request.POST, instance=roaster_profile)
        if roaster_bio_form.is_valid():
            roaster_bio_form.save()
            return redirect('roaster_dashboard')
    else:
        roaster_bio_form = RoasterBioForm(instance=roaster_profile)

    # Handle the photo form
    if request.method == 'POST' and 'roaster_photo_form' in request.POST:
        roaster_photo_form = RoasterPhotoForm(request.POST, request.FILES)
        if roaster_photo_form.is_valid():
            photo_instance = roaster_photo_form.save(commit=False)
            photo_instance.user = request.user  # Assuming you have a ForeignKey to the user
            photo_instance.save()
            return redirect('roaster_dashboard')
    else:
        roaster_photo_form = RoasterPhotoForm()

    # Handle the sourcing form
    if request.method == 'POST' and 'roaster_sourcing_form' in request.POST:
        roaster_sourcing_form = RoasterSourcingForm(request.POST, instance=roaster_profile)
        if roaster_sourcing_form.is_valid():
            roaster_sourcing_form.save()
            return redirect('roaster_dashboard')
    else:
        roaster_sourcing_form = RoasterSourcingForm(instance=roaster_profile)

    return render(request, 'base/roaster_dashboard.html', {
        'farmers': farmers,
        'meeting_requests_as_requestee': meeting_requests_as_requestee,
        'meeting_requests_as_requester': meeting_requests_as_requester,
        'roaster_profile': roaster_profile,
        'roaster_photos': roaster_photos,
        'pending_meetings': pending_meetings,
        'can_request_meetings': can_request_meetings,
        'total_meetings_used': total_meetings_used,
        'roaster_info_form': roaster_info_form,
        'roaster_bio_form': roaster_bio_form,
        'roaster_photo_form': roaster_photo_form,
        'roaster_sourcing_form': roaster_sourcing_form,

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

def delete_roaster_photo(request, photo_id):
    photo = get_object_or_404(RoasterPhoto, id=photo_id, user=request.user)
    if request.method == 'POST':
        # Delete the file from the filesystem
        if photo.photo and os.path.isfile(photo.photo.path):
            os.remove(photo.photo.path)

        # Delete the record from the database
        photo.delete()

        return redirect('roaster_dashboard')