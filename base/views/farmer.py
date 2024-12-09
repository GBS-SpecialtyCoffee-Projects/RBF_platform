from django.shortcuts import render, redirect,get_object_or_404
from base.views.forms import FarmerBioForm, FarmerForm, FarmerPhotoForm, RoasterForm, RoasterPhotoForm, FarmerProfileForm,FarmerProfilePhotoForm, RoasterProfileForm, OrientationTasksForm, StoryTellingCheck, VideoCommTipsCheck, VideoIntlCheck, VideoPerceptionsCheck, VideoPricingCheck, VideoRelationshipsCheck
from base.models import Roaster, MeetingRequest, Farmer,FarmerPhoto
from django.contrib import messages
import os

def farmer_dashboard(request):
    if request.user.group != 'farmer':
        return redirect('roaster_dashboard')

    # roasters = Roaster.objects.all()
    # meeting_requests = MeetingRequest.objects.filter(requestee=request.user)
    # meeting_requests_as_requester = MeetingRequest.objects.filter(requester=request.user)
    farmer_profile = Farmer.objects.filter(user=request.user).first()
    farmer_photos = FarmerPhoto.objects.filter(user=request.user)
    farmer_photos_unadded = 6 - farmer_photos.count()
    pending_meetings = MeetingRequest.objects.filter(
        requestee=request.user, status='pending'
    )[:2]
    # pending_meetings = MeetingRequest.objects.filter(
    #     requester=request.user, status='accepted'
    # ) | MeetingRequest.objects.filter(
    #     requestee=request.user, status='accepted'
    # )

    # Check the number of pending or accepted meetings
    active_meetings_count = MeetingRequest.objects.filter(
        requester=request.user, status__in=['pending', 'accepted']
    ).count()

    can_request_meetings = active_meetings_count < 5

    if request.method == 'POST' and 'main_form' in request.POST:
        form = FarmerProfileForm(request.POST, instance=farmer_profile)
        if form.is_valid():
            form.save()
            return redirect('farmer_dashboard')
    elif request.method == 'POST' and 'story_form' in request.POST:
        form = FarmerBioForm(request.POST, instance=farmer_profile)
        if form.is_valid():
            form.save()
            return redirect('farmer_dashboard')
    else:
        main_form = FarmerProfileForm(instance=farmer_profile)
        dp_form = FarmerProfilePhotoForm(instance=farmer_profile)
        story_form = FarmerBioForm(instance=farmer_profile)
        photo_form = FarmerPhotoForm()

    return render(request, 'base/farmer_dashboard.html', {
        # 'roasters': roasters,
        # 'meeting_requests_as_requestee': meeting_requests_as_requestee,
        'pending_requests': pending_meetings,
        'farmer_profile': farmer_profile,
        'farmer_photos': farmer_photos,
        'unused_count': farmer_photos_unadded,
        'pending_meetings': pending_meetings,
        'can_request_meetings': can_request_meetings,
        'main_form': main_form, 
        'story_form': story_form,
        'photo_form': photo_form,
        'dp_form': dp_form
    })

def edit_farmer_details(request):
    if request.user.group != 'farmer':
        return redirect('roaster_dashboard')
    
    farmer_profile = Farmer.objects.filter(user=request.user).first()
    
    if request.method == 'POST' and 'main_form' in request.POST:
        form = FarmerProfileForm(request.POST, instance=farmer_profile)
        if form.is_valid():
            form.save()
            return redirect('farmer_dashboard')
    else:
        main_form = FarmerProfileForm(instance=farmer_profile)
    
    
    return render(request, 'base/farmer_details_edit.html',{
        'main_form': main_form
    })

def upload_photo(request):
    if request.method == 'POST':
        form = FarmerPhotoForm(request.POST, request.FILES)
        if form.is_valid():
            farmer_photo = form.save(commit=False)
            farmer_photo.user = request.user  # Set the user to the currently logged-in user
            farmer_photo.clean()  # Validate the roaster_photo instance
            farmer_photo.save()
            return redirect('farmer_dashboard')
    else:
        form = FarmerPhotoForm()
    return render(request, 'base/upload_photo.html', {'form': form})

def update_profile(request):
    if request.method == 'POST':
        farmer_profile = Farmer.objects.filter(user=request.user).first()
        form = FarmerProfilePhotoForm(request.POST, request.FILES, instance=farmer_profile)
        if form.is_valid():
            print('in valid')
            form.save()
            return redirect('farmer_dashboard')  # Redirect to a profile page or any other page
    else:
        return redirect('farmer_dashboard')  # If not a POST request, redirect to profile page

    # return render(request, 'base/farmer_dashboard.html.html', {'form': form})
    return redirect('farmer_dashboard')

def delete_farmer_photo(request, photo_id):
    photo = get_object_or_404(FarmerPhoto, id=photo_id, user=request.user)
    if request.method == 'GET':
        # Delete the file from the filesystem
        if photo.photo and os.path.isfile(photo.photo.path):
            os.remove(photo.photo.path)

        # Delete the record from the database
        photo.delete()

        return redirect('farmer_dashboard')

def upload_success(request):
    return render(request, 'base/upload_success.html')

def language_select(request):
    return render(request, 'base/language_select.html')


def farmer_orientation(request):

    """
    View to handle orientation tasks
    """

    if request.user.group != 'farmer':
        return redirect('roaster_dashboard')
    
    farmer = request.user.farmer_profile

    tasks_completed = [
        farmer.profile_completed,
        farmer.storytelling_workshop,
        farmer.video_pricing,
        farmer.video_intl,
        farmer.video_comm_tips,
        farmer.video_relationships,
        farmer.video_perceptions,
    ]
    # Calculate the percentage of tasks completed for progress bar
    completed_count = sum(tasks_completed)
    total_tasks = len(tasks_completed)
    progress_percentage = (completed_count / total_tasks) * 100
    remaining = total_tasks - completed_count


    if request.method == 'POST':

        if 'story' in request.POST:
            form = StoryTellingCheck(request.POST, instance=farmer)
            if form.is_valid():
                form.save()
                return redirect('farmer_orientation')
            
        elif 'pricing' in request.POST:
                    form = VideoPricingCheck(request.POST, instance=farmer)
                    if form.is_valid():
                        form.save()
                        return redirect('farmer_orientation')
                    
        elif 'intl' in request.POST:
                    form = VideoIntlCheck(request.POST, instance=farmer)
                    if form.is_valid():
                        form.save()
                        return redirect('farmer_orientation')
                    
        elif 'comms' in request.POST:
                    form = VideoCommTipsCheck(request.POST, instance=farmer)
                    if form.is_valid():
                        form.save()
                        return redirect('farmer_orientation')
                    
        elif 'relat' in request.POST:
                    form = VideoRelationshipsCheck(request.POST, instance=farmer)
                    if form.is_valid():
                        form.save()
                        return redirect('farmer_orientation')
                    
        elif 'percep' in request.POST:
                    form = VideoPerceptionsCheck(request.POST, instance=farmer)
                    if form.is_valid():
                        form.save()
                        return redirect('farmer_orientation')

        else:
            
            form = OrientationTasksForm(request.POST, instance=farmer)
            
            if form.is_valid():
                form.save()

                tasks_completed = [
                    farmer.profile_completed,
                    farmer.storytelling_workshop,
                    farmer.video_pricing,
                    farmer.video_intl,
                    farmer.video_comm_tips,
                    farmer.video_relationships,
                    farmer.video_perceptions,
                ]
                completed_count = sum(tasks_completed)
                progress_percentage = (completed_count / total_tasks) * 100
                remaining = total_tasks - completed_count

                return redirect('farmer_orientation')
    else:
        form = OrientationTasksForm(instance=farmer)
        
    context = {
        'user': farmer,
        'form': form,
        'progress_percentage': progress_percentage,
        'completed': completed_count,
        'total': total_tasks,
        'remaining': remaining
    }

    return render(request, 'base/farmer_orientation.html', context)


def storytelling_check(request):
    """
    View method to handle storytelling task completion
    individually outside of OrientationTasksForm

    Implemented as a bug fix for checkbox form
    submission within modals unselecting all other fields
    in OrientationTasksForm
    """
    if request.method == 'POST':
        print(request.POST)
        farmer = request.user.farmer_profile
        form = StoryTellingCheck(request.POST, instance=farmer)
        if form.is_valid():
            form.save()
            return redirect('farmer_orientation')

def vid_x_check(request):
    """
    View method to handle storytelling task completion
    individually outside of OrientationTasksForm

    Implemented as a bug fix for checkbox form
    submission within modals unselecting all other fields
    in OrientationTasksForm
    """
    if request.method == 'POST':
        farmer = request.user.farmer_profile
        form = VideoPricingCheck(request.POST, instance=farmer)
        if form.is_valid():
            form.save()
            return redirect('farmer_orientation')

