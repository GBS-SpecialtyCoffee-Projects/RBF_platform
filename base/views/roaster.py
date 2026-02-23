from django.shortcuts import render, redirect,get_object_or_404
from base.views.forms import FarmerPhotoForm, RoasterForm, RoasterPhotoForm, MeetingRequestForm,RoasterProfileForm, RoasterInfoForm, RoasterBioForm,RoasterSourcingForm
from base.models import Farmer, Language, MeetingRequest, RoasterPhoto,Roaster, FarmerPhoto, BuyerFunctions,Story,Season,ProcessingMethod,CupScore
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.contrib import messages
import logging
import os

logger = logging.getLogger(__name__)
from django.urls import reverse
from django.http import HttpResponseRedirect, JsonResponse
from django.db.models import Prefetch


def roaster_dashboard(request):
    if request.user.group != 'roaster':
        return redirect('farmer_dashboard')
    
    roaster_profile = Roaster.objects.filter(user=request.user).first()
    if roaster_profile and roaster_profile.is_details_filled == False:
        return redirect('roaster_details')

    farmers = Farmer.objects.all()
    meeting_requests_as_requestee = MeetingRequest.objects.filter(requestee=request.user)
    meeting_requests_as_requester = MeetingRequest.objects.filter(requester=request.user)
    roaster_profile = Roaster.objects.filter(user=request.user).first()
    roaster_photos = RoasterPhoto.objects.filter(user=request.user)
    roaster_functions = BuyerFunctions.objects.filter(roaster=roaster_profile)
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

    # Limit the number of photos to 6
    if roaster_photos.count() >= 6:
        roaster_photo_form = None  # Disable the photo form if the limit is reached
        messages.warning(request, 'You have reached the maximum limit of 6 photos.')
    else:
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
        'functions': roaster_functions

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
                messages.success(request, "Meeting request sent successfully!")
                return redirect('farmer_dashboard' if request.user.group == 'farmer' else 'roaster_dashboard')
        else:
            messages.error(request, "Form is not valid. Please correct the errors.")
            return render(request, 'base/connections.html', {'form': form, 'show_modal': True})
    else:
        form = MeetingRequestForm()

    return render(request, 'base/connections.html', {'form': form, 'show_modal': False})


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

def connections(request):
    # farmers = Farmer.objects.all()
    farmers = Story.objects.select_related('farmer').prefetch_related('farmer__cup_scores_received', 'farmer__processing_method').filter(farmer__isnull=False)
    for farmer in farmers:
        farmer.cup_scores_received = farmer.farmer.cup_scores_received.all()
        farmer.processing_method = farmer.farmer.processing_method.all()
    form = MeetingRequestForm()
    show_modal = False  # Initially, the modal should not be shown

    # Get filter parameters from GET request
    annual_production = request.GET.get('annual_production')
    farm_size = request.GET.get('farm_size')

    # Filter the farmers queryset accordingly
    if annual_production:
        farmers = farmers.filter(farmer__annual_production__isnull=False)
        if annual_production == '0.1-5':
            farmers = farmers.filter(farmer__annual_production__gte=0.1, farmer__annual_production__lte=5)
        elif annual_production == '5-20':
            farmers = farmers.filter(farmer__annual_production__gte=5, farmer__annual_production__lte=20)
        elif annual_production == '20-50':
            farmers = farmers.filter(famrer__annual_production__gte=20, farmer__annual_production__lte=50)
        elif annual_production == '50+':
            farmers = farmers.filter(farmer__annual_production__gte=50)

    if farm_size:
        farmers = farmers.filter(farmer__farm_size__isnull=False)
        if farm_size == '0.1-2':
            farmers = farmers.filter(farmer__farm_size__gte=0.1, farmer__farm_size__lte=2)
        elif farm_size == '2-10':
            farmers = farmers.filter(farmer__farm_size__gte=2, farmer__farm_size__lte=10)
        elif farm_size == '10-50':
            farmers = farmers.filter(farmer__farm_size__gte=10, farmer__farm_size__lte=50)
        elif farm_size == '50+':
            farmers = farmers.filter(farmer__farm_size__gte=50)

    if request.method == 'POST':
        # Handle retrieval or deletion of meeting requests
        if 'retrieve_meeting_request' in request.POST:
            meeting_request = get_object_or_404(MeetingRequest, id=request.POST.get('meeting_id'))
            if meeting_request.status == 'pending':
                meeting_request.delete()
            # Redirect back to the same page with GET parameters
            query_params = request.GET.urlencode()
            redirect_url = reverse('connections')
            if query_params:
                redirect_url += '?' + query_params
            return HttpResponseRedirect(redirect_url)
        elif 'delete_meeting_request' in request.POST:
            meeting_request = get_object_or_404(MeetingRequest, id=request.POST.get('meeting_id'))
            if meeting_request.status == 'rejected':
                meeting_request.delete()
            query_params = request.GET.urlencode()
            redirect_url = reverse('connections')
            if query_params:
                redirect_url += '?' + query_params
            return HttpResponseRedirect(redirect_url)

        # Handle meeting request form submission
        form = MeetingRequestForm(request.POST)
        if form.is_valid():
            # Check the number of pending or accepted meetings before saving the new request
            active_meetings_count = MeetingRequest.objects.filter(
                requester=request.user, status__in=['pending', 'accepted']
            ).count()

            if active_meetings_count >= 5:
                messages.error(request, "You cannot have more than 5 pending or accepted meetings.")
                query_params = request.GET.urlencode()
                redirect_url = reverse('connections')
                if query_params:
                    redirect_url += '?' + query_params
                return HttpResponseRedirect(redirect_url)

            meeting_request = form.save(commit=False)
            meeting_request.requester = request.user
            meeting_request.requestee = get_object_or_404(User, id=request.POST.get('user_id'))
            meeting_request.save()
            query_params = request.GET.urlencode()
            redirect_url = reverse('connections')
            if query_params:
                redirect_url += '?' + query_params
            return HttpResponseRedirect(redirect_url)
        else:
            show_modal = True  # Show modal if the form is invalid

    # Fetch the user's meeting requests
    meeting_requests = MeetingRequest.objects.filter(requester=request.user)

    # Check the number of pending or accepted meetings
    active_meetings_count = meeting_requests.filter(status__in=['pending', 'accepted']).count()
    can_request_meetings = active_meetings_count < 5

    return render(request, 'base/connections.html', {
        'farmers': farmers,
        'form': form,
        'show_modal': show_modal,
        'can_request_meetings': can_request_meetings,
        'meeting_requests': meeting_requests,
        'total_meetings_used': active_meetings_count,
        'selected_annual_production': annual_production,
        'selected_farm_size': farm_size,
    })

def farmer_view(request, user_id):
    farmer_profile = get_object_or_404(Farmer, user__id=user_id)

    try:
        farmer_photos = FarmerPhoto.objects.filter(user=farmer_profile.user)
        farmer_stories = Story.objects.filter(user=farmer_profile.user)
        farmer_harvest_seasons = Season.objects.filter(farmer=farmer_profile)
        farmer_processing_methods = ProcessingMethod.objects.filter(farmer=farmer_profile)
        farmer_cup_scores = CupScore.objects.filter(farmer=farmer_profile)
        variety = farmer_profile.cultivars.split(',') if farmer_profile.cultivars else []
        is_own_profile = request.user == farmer_profile.user
    except Exception:
        logger.exception("Error loading farmer profile data for user_id=%s", user_id)
        messages.error(request, "Something went wrong loading this profile. Please try again later.")
        return redirect('connections')

    return render(request, 'base/farmer_view.html', {
        'farmer_profile': farmer_profile,
        'farmer_photos': farmer_photos,
        'farmer_stories': farmer_stories,
        'harvest_seasons': farmer_harvest_seasons,
        'processing_methods': farmer_processing_methods,
        'cup_scores': farmer_cup_scores,
        'variety': variety,
        'is_own_profile': is_own_profile,
    })

def switch_story(request,language_id,user_id):
     try:
        #get current farmer
        # farmer = request.user
        #get the id of the story i am meant to return 
        language= Language.objects.get(id=language_id)
        #get story with that id 
        story = Story.objects.get(language=language,user_id=user_id)
        #get all stories excluding story in the language
        # languages = [ (story.language.id,story.language.name) for story in Story.objects.filter(user=farmer).exclude(language=language)]
        languages = [ (language.id,language.name) for language in Language.objects.all()]

        # print(languages)
        # print(story.story_text)
     except:
         return JsonResponse({'error': 'Language not found',}, status=404)
    
     #return response to page with story 
     return JsonResponse({'story': story.story_text,'languages':languages, 'success': 'success'}, status=200)