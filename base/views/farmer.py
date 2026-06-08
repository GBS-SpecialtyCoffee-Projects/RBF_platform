from django.shortcuts import render, redirect,get_object_or_404
from base.views.forms import FarmerAddStoryForm, FarmerStoryForm, FarmerForm, FarmerPhotoForm, RoasterForm, RoasterPhotoForm, FarmerProfileForm,FarmerProfilePhotoForm, RoasterProfileForm, OrientationTasksForm, StoryTellingCheck, VideoCommTipsCheck, VideoIntlCheck, VideoPerceptionsCheck, VideoPricingCheck, VideoRelationshipsCheck, FarmerHeaderImageForm, MeetingRequestForm
from base.models import Roaster, RoasterPhoto, MeetingRequest, Farmer,FarmerPhoto,Story,Language,Season,ProcessingMethod,CupScore
from base.notifications import notify_meeting_event
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import HttpResponseBadRequest, HttpResponseNotAllowed, HttpResponseRedirect, JsonResponse
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
import logging
import os

logger = logging.getLogger(__name__)

User = get_user_model()

def farmer_dashboard(request):
    if request.user.group != 'farmer':
        return redirect('roaster_dashboard')

    # roasters = Roaster.objects.all()
    # meeting_requests = MeetingRequest.objects.filter(requestee=request.user)
    # meeting_requests_as_requester = MeetingRequest.objects.filter(requester=request.user)
    farmer_profile = Farmer.objects.filter(user=request.user).first()

    if farmer_profile and farmer_profile.is_details_filled == False:
        return redirect('farmer_details')
    
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

def connections(request):
    if request.user.group != 'farmer':
        return redirect('roaster_dashboard')

    meeting_requests = MeetingRequest.objects.filter(
        requestee=request.user
    ).select_related('requester')

    return render(request, 'base/farmer_connections.html', {
        'meeting_requests': meeting_requests,
    })


def connection_roasters(request):
    if request.user.group != 'farmer':
        return redirect('roaster_dashboard')

    roasters = Roaster.objects.filter(is_details_filled=True)
    form = MeetingRequestForm()
    show_modal = False

    # Get filter parameters from GET request
    country = request.GET.get('country')
    purchase_volume = request.GET.get('purchase_volume')

    # Filter the roasters queryset accordingly
    if country:
        roasters = roasters.filter(country=country)

    if purchase_volume:
        roasters = roasters.filter(purchase_volume__isnull=False)
        if purchase_volume == '0-500':
            roasters = roasters.filter(purchase_volume__gte=0, purchase_volume__lte=500)
        elif purchase_volume == '500-2000':
            roasters = roasters.filter(purchase_volume__gte=500, purchase_volume__lte=2000)
        elif purchase_volume == '2000-5000':
            roasters = roasters.filter(purchase_volume__gte=2000, purchase_volume__lte=5000)
        elif purchase_volume == '5000+':
            roasters = roasters.filter(purchase_volume__gte=5000)

    if request.method == 'POST':
        # Handle meeting request form submission
        form = MeetingRequestForm(request.POST)
        if form.is_valid():
            active_meetings_count = MeetingRequest.objects.filter(
                requester=request.user, status__in=['pending', 'accepted']
            ).count()

            if active_meetings_count >= 5:
                messages.error(request, "You cannot have more than 5 pending or accepted meetings.")
                return _redirect_with_filters(request)

            requestee_id = request.POST.get('user_id')
            if MeetingRequest.objects.filter(
                requester=request.user, requestee_id=requestee_id, status__in=['pending', 'accepted']
            ).exists():
                messages.error(request, "You already have an active request with this roaster.")
                return _redirect_with_filters(request)

            meeting_request = form.save(commit=False)
            meeting_request.requester = request.user
            meeting_request.requestee = get_object_or_404(User, id=requestee_id)
            meeting_request.save()
            notify_meeting_event(meeting_request, 'created')
            return _redirect_with_filters(request)
        else:
            show_modal = True  # Show modal if the form is invalid

    # Fetch the user's meeting requests
    meeting_requests = MeetingRequest.objects.filter(requester=request.user)
    active_meeting_requests = meeting_requests.filter(status__in=['pending', 'accepted'])
    active_meetings_count = active_meeting_requests.count()
    can_request_meetings = active_meetings_count < 5
    connected_user_ids, sent_user_ids, incoming_user_ids = MeetingRequest.status_sets_for(request.user)

    # Available countries for filter dropdown
    available_countries = (
        Roaster.objects.filter(is_details_filled=True)
        .values_list('country', flat=True)
        .distinct()
        .order_by('country')
    )

    # Pagination
    paginator = Paginator(roasters, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Build filter query string (without 'page') for template links
    filter_params = request.GET.copy()
    filter_params.pop('page', None)
    filter_query_string = filter_params.urlencode()

    return render(request, 'base/connection_roasters.html', {
        'roasters': page_obj,
        'page_obj': page_obj,
        'form': form,
        'show_modal': show_modal,
        'can_request_meetings': can_request_meetings,
        'connected_user_ids': connected_user_ids,
        'sent_user_ids': sent_user_ids,
        'incoming_user_ids': incoming_user_ids,
        'meeting_requests': meeting_requests,
        'total_meetings_used': active_meetings_count,
        'selected_country': country,
        'selected_purchase_volume': purchase_volume,
        'available_countries': available_countries,
        'filter_query_string': filter_query_string,
    })


def _redirect_with_filters(request):
    """Redirect back to the roaster search page preserving GET filters."""
    redirect_url = reverse('connection_roasters')
    query_params = request.GET.urlencode()
    if query_params:
        redirect_url += '?' + query_params
    return HttpResponseRedirect(redirect_url)


def manage_connection_request(request, meeting_id, action):
    if request.user.group != 'farmer':
        return redirect('roaster_dashboard')

    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    if action not in ('accept', 'reject'):
        return HttpResponseBadRequest('Invalid action')

    meeting_request = get_object_or_404(
        MeetingRequest, id=meeting_id, requestee=request.user
    )
    meeting_request.status = 'accepted' if action == 'accept' else 'rejected'
    meeting_request.save()
    notify_meeting_event(meeting_request, meeting_request.status)

    referer = request.META.get('HTTP_REFERER', '')
    if referer and url_has_allowed_host_and_scheme(
        referer, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return redirect(referer)
    return redirect('farmer_connections')


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
            form.save()
            referer = request.META.get('HTTP_REFERER', '')
            if 'farmer/' in referer:
                return redirect('farmer_profile', user_id=request.user.id)
            return redirect('farmer_dashboard')
    else:
        return redirect('farmer_dashboard')

    return redirect('farmer_dashboard')

def update_header_image(request):
    if request.method == 'POST':
        farmer_profile = Farmer.objects.filter(user=request.user).first()
        form = FarmerHeaderImageForm(request.POST, request.FILES, instance=farmer_profile)
        if form.is_valid():
            form.save()
            referer = request.META.get('HTTP_REFERER', '')
            if 'farmer/' in referer:
                return redirect('farmer_profile', user_id=request.user.id)
            return redirect('farmer_dashboard')
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

def roaster_view(request, user_id):
    if request.user.group != 'farmer' and request.user.id != user_id:
        return redirect('roaster_dashboard')

    roaster_profile = get_object_or_404(Roaster, user__id=user_id)

    try:
        roaster_photos = RoasterPhoto.objects.filter(user=roaster_profile.user)
        roaster_functions = roaster_profile.company_functions.all()
        is_own_profile = request.user == roaster_profile.user
        active_request = None
        connection_status = 'none'
        if not is_own_profile:
            active_request = MeetingRequest.active_between(request.user, roaster_profile.user)
            if active_request:
                connection_status = active_request.status_for(request.user)
    except Exception:
        logger.exception("Error loading roaster profile data for user_id=%s", user_id)
        messages.error(request, "Something went wrong loading this profile. Please try again later.")
        return redirect('farmer_dashboard')

    return render(request, 'base/roaster_view.html', {
        'roaster_profile': roaster_profile,
        'roaster_photos': roaster_photos,
        'functions': roaster_functions,
        'is_own_profile': is_own_profile,
        'connection_status': connection_status,
        'active_request': active_request,
    })


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

    profile_completed = farmer.profile_completed

    
    if not profile_completed:
        profile_completed = check_is_complete(farmer)
        if profile_completed:
            farmer.profile_completed = True
            farmer.save()
        
    print(profile_completed)

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

def check_is_complete(farmer):
     
      if  farmer.firstname and farmer.lastname and farmer.profile_picture and farmer.country_code and farmer.phone_number and farmer.farm_name and farmer.country and farmer.state and farmer.city and farmer.farm_size and farmer.annual_production:
          return True
      else:
          return False
      
def publish_profile(request):
     farmer = request.user.farmer_profile
     
     farmer.is_profile_published = True
     farmer.save()
     return redirect('farmer_dashboard')
     
     

