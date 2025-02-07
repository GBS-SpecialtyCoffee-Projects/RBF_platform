from django.shortcuts import render, redirect,get_object_or_404
from base.views.forms import FarmerAddStoryForm, FarmerStoryForm, FarmerForm, FarmerPhotoForm, RoasterForm, RoasterPhotoForm, FarmerProfileForm,FarmerProfilePhotoForm, RoasterProfileForm, OrientationTasksForm, StoryTellingCheck, VideoCommTipsCheck, VideoIntlCheck, VideoPerceptionsCheck, VideoPricingCheck, VideoRelationshipsCheck
from base.models import Roaster, MeetingRequest, Farmer,FarmerPhoto,Story,Language,Season,ProcessingMethod,CupScore
from django.contrib import messages
from django.http import JsonResponse
import os

def farmer_dashboard(request):
    if request.user.group != 'farmer':
        return redirect('roaster_dashboard')

    # roasters = Roaster.objects.all()
    # meeting_requests = MeetingRequest.objects.filter(requestee=request.user)
    # meeting_requests_as_requester = MeetingRequest.objects.filter(requester=request.user)
    farmer_profile = Farmer.objects.filter(user=request.user).first()
    farmer_photos = FarmerPhoto.objects.filter(user=request.user)
    farmer_stories  = Story.objects.filter(user=request.user)
    farmer_harvest_seasons = Season.objects.filter(farmer=farmer_profile)
    farmer_processing_methods = ProcessingMethod.objects.filter(farmer=farmer_profile)
    farmer_cup_scores = CupScore.objects.filter(farmer=farmer_profile)
    farmer_story = farmer_stories.first()
    farmer_photos_unadded = 6 - farmer_photos.count()
    pending_meetings = MeetingRequest.objects.filter(
        requestee=request.user, status='pending'
    )[:2]
    languages = Language.objects.all()
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
        form = FarmerStoryForm(request.POST, instance=farmer_profile)
        if form.is_valid():
            form.save()
            return redirect('farmer_dashboard')
    else:
        print('in else')
        main_form = FarmerProfileForm(instance=farmer_profile)
        dp_form = FarmerProfilePhotoForm(instance=farmer_profile)
        story_form = FarmerStoryForm(instance=farmer_story)
        add_story_form = FarmerAddStoryForm()
        photo_form = FarmerPhotoForm()

    return render(request, 'base/farmer_dashboard.html', {
        # 'roasters': roasters,
        # 'meeting_requests_as_requestee': meeting_requests_as_requestee,
        'pending_requests': pending_meetings,
        'farmer_profile': farmer_profile,
        'farmer_stories': farmer_stories,
        'harvest_seasons': farmer_harvest_seasons,
        'processing_methods': farmer_processing_methods,
        'cup_scores': farmer_cup_scores,
        'farmer_photos': farmer_photos,
        'unused_count': farmer_photos_unadded,
        'pending_meetings': pending_meetings,
        'can_request_meetings': can_request_meetings,
        'main_form': main_form, 
        'story_form': story_form,
        'add_story_form': add_story_form,
        'photo_form': photo_form,
        'dp_form': dp_form,
        'languages': languages
    })

def edit_farmer_details(request):
    if request.user.group != 'farmer':
        return redirect('roaster_dashboard')
    
    farmer_profile = Farmer.objects.filter(user=request.user).first()
    print(request.method)
    
    if request.method == 'POST' and 'main_form' in request.POST:
        form = FarmerProfileForm(request.POST, instance=farmer_profile)
        if form.is_valid():
            print('in valid')
            form.save()
            return redirect('farmer_dashboard')
        else:
            print(form.errors)
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
            farmer_photo.clean()  
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
            # print('in valid')
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
        # if photo.photo and os.path.isfile(photo.photo.path):
        #     os.remove(photo.photo.path)

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

def switch_story(request,language_id):
     try:
        #get current farmer
        farmer = request.user
        #get the id of the story i am meant to return 
        language= Language.objects.get(id=language_id)
        #get story with that id 
        story = Story.objects.get(language=language, user=farmer)
        #get all stories excluding story in the language
        # languages = [ (story.language.id,story.language.name) for story in Story.objects.filter(user=farmer).exclude(language=language)]
        languages = [ (language.id,language.name) for language in Language.objects.all()]

        # print(languages)
        # print(story.story_text)
     except:
         return JsonResponse({'error': 'Language not found',}, status=404)
    
     #return response to page with story 
     return JsonResponse({'story': story.story_text,'languages':languages, 'success': 'success'}, status=200)

def update_story(request):
    if request.method == 'POST':
        farmer = request.user
        language= Language.objects.get(id=request.POST.get('language'))
        story = Story.objects.get(language=language, user=farmer)
        form = FarmerStoryForm(request.POST,instance=story)
        if form.is_valid():
            # print('in valid')
            instance =form.save()
            return JsonResponse({'success': 'success', 'story': instance.story_text}, status=200)
            # return redirect('farmer_dashboard')  # Redirect to a profile page or any other page
    else:
        return JsonResponse({'error': 'Method not allowed'}, status=405)
        # return redirect('farmer_dashboard')  # If not a POST request, redirect to profile page

    # return render(request, 'base/farmer_dashboard.html.html', {'form': form})
    # return redirect('farmer_dashboard')
    return JsonResponse({'success': 'success'}, status=200)

def add_story(request):
    if request.method == 'POST':
        farmer = request.user
        # language= Language.objects.get(id=request.POST.get('language'))
        # story = Story.objects.get(language=language, user=farmer)
        form = FarmerAddStoryForm(request.POST)
        if form.is_valid():
            # print('in valid')
            instance =form.save(commit=False)
            instance.user = farmer
            instance.save()
            return JsonResponse({'success': 'success', 'story': instance.story_text}, status=200)
            # return redirect('farmer_dashboard')  # Redirect to a profile page or any other page
    else:
        return JsonResponse({'error': 'Method not allowed'}, status=405)
        # return redirect('farmer_dashboard')  # If not a POST request, redirect to profile page

    # return render(request, 'base/farmer_dashboard.html.html', {'form': form})
    # return redirect('farmer_dashboard')
    return JsonResponse({'success': 'success'}, status=200)

