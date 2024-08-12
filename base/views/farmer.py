from django.shortcuts import render, redirect,get_object_or_404
from base.views.forms import FarmerPhotoForm, RoasterForm, RoasterPhotoForm, FarmerProfileForm, RoasterProfileForm, OrientationTasksForm, StoryTellingCheck, VideoCommTipsCheck, VideoIntlCheck, VideoPerceptionsCheck, VideoPricingCheck, VideoRelationshipsCheck
from base.models import Roaster, MeetingRequest, Farmer,FarmerPhoto
from django.contrib import messages

def farmer_dashboard(request):
    if request.user.group != 'farmer':
        return redirect('roaster_dashboard')

    roasters = Roaster.objects.all()
    meeting_requests_as_requestee = MeetingRequest.objects.filter(requestee=request.user)
    meeting_requests_as_requester = MeetingRequest.objects.filter(requester=request.user)
    farmer_profile = Farmer.objects.filter(user=request.user).first()
    farmer_photos = FarmerPhoto.objects.filter(user=request.user)
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
        form = FarmerProfileForm(request.POST, instance=farmer_profile)
        if form.is_valid():
            form.save()
            return redirect('farmer_dashboard')
    else:
        form = FarmerProfileForm(instance=farmer_profile)

    return render(request, 'base/farmer_dashboard.html', {
        'roasters': roasters,
        'meeting_requests_as_requestee': meeting_requests_as_requestee,
        'meeting_requests_as_requester': meeting_requests_as_requester,
        'farmer_profile': farmer_profile,
        'farmer_photos': farmer_photos,
        'pending_meetings': pending_meetings,
        'can_request_meetings': can_request_meetings,
        'form': form,
    })

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

