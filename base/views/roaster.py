from django.shortcuts import render, redirect,get_object_or_404
from base.views.forms import FarmerPhotoForm, RoasterForm, RoasterPhotoForm, MeetingRequestForm,RoasterProfileForm, RoasterInfoForm, RoasterBioForm,RoasterSourcingForm, RoasterHeaderImageForm
from base.models import Farmer, Language, MeetingRequest, Connection, RoasterPhoto,Roaster, FarmerPhoto, BuyerFunctions,Story,Season,ProcessingMethod,CupScore,Forum
from base.notifications import notify_meeting_event, notify_connection_event
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.contrib import messages
import logging
import os
import random

logger = logging.getLogger(__name__)
from django.urls import reverse
from django.http import HttpResponseNotAllowed, HttpResponseForbidden, HttpResponseRedirect, JsonResponse
from django.core.paginator import Paginator
from django.db.models import Prefetch, Q
from django.utils.http import url_has_allowed_host_and_scheme


def roaster_dashboard(request):
    if request.user.group != 'roaster':
        return redirect('farmer_dashboard')
    
    roaster_profile = Roaster.objects.filter(user=request.user).first()
    if roaster_profile and roaster_profile.is_details_filled == False:
        return redirect('roaster_details')

    farmers = Farmer.objects.all()
    roaster_photos = RoasterPhoto.objects.filter(user=request.user)
    roaster_functions = BuyerFunctions.objects.filter(roaster=roaster_profile)

    # Connections (new model): split into incoming / sent / active.
    incoming_connections, sent_connections, active_connections = connection_buckets(request.user)
    can_request_meetings = Connection.pending_sent_count(request.user) < Connection.MAX_PENDING_SENT
    total_meetings_used = len(sent_connections)

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
        'incoming_connections': incoming_connections,
        'sent_connections': sent_connections,
        'active_connections': active_connections,
        'roaster_profile': roaster_profile,
        'roaster_photos': roaster_photos,
        'can_request_meetings': can_request_meetings,
        'total_meetings_used': total_meetings_used,
        'roaster_info_form': roaster_info_form,
        'roaster_bio_form': roaster_bio_form,
        'roaster_photo_form': roaster_photo_form,
        'roaster_sourcing_form': roaster_sourcing_form,
        'functions': roaster_functions

    })


def update_roaster_header_image(request):
    if request.method == 'POST':
        roaster_profile = Roaster.objects.filter(user=request.user).first()
        form = RoasterHeaderImageForm(request.POST, request.FILES, instance=roaster_profile)
        if form.is_valid():
            form.save()
    return redirect('roaster_dashboard')


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
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    recipient = get_object_or_404(User, id=user_id)
    create_connection_request(request, recipient)
    return _redirect_back(request)


def _redirect_back(request):
    """Redirect to the referring page if it is safe, else the dashboard."""
    referer = request.META.get('HTTP_REFERER', '')
    if referer and url_has_allowed_host_and_scheme(
        referer, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return redirect(referer)
    return redirect('farmer_dashboard' if request.user.group == 'farmer' else 'roaster_dashboard')


def create_connection_request(request, recipient):
    """Shared validation + creation of an outgoing Connection request.

    Sets a user-facing message and returns the Connection (or None on failure).
    Used by both profile pages and the discovery listings.
    """
    if recipient.group == request.user.group:
        messages.error(request, "Connections must be between a farmer and a roaster.")
        return None

    existing = Connection.between(request.user, recipient)
    if existing and existing.status in Connection.LIVE_STATUSES:
        messages.error(request, "You already have a pending request or connection with this user.")
        return None

    if Connection.pending_sent_count(request.user) >= Connection.MAX_PENDING_SENT:
        messages.error(
            request,
            f"You have too many pending requests (max {Connection.MAX_PENDING_SENT}). "
            "Wait for some to be answered before sending more.",
        )
        return None

    conn = Connection.request(request.user, recipient, message=request.POST.get('message', ''))
    notify_connection_event(conn, 'created')
    messages.success(request, "Connection request sent!")
    return conn


def apply_connection_action(request, connection, action):
    """Shared accept / reject / withdraw / disconnect handling with guards."""
    user = request.user
    is_recipient = connection.recipient.id == user.id
    is_initiator = connection.initiator_id == user.id

    if action == 'accept' and connection.status == Connection.PENDING and is_recipient:
        connection.accept()
        notify_connection_event(connection, 'accepted')
        messages.success(request, "Connection accepted.")
    elif action == 'reject' and connection.status == Connection.PENDING and is_recipient:
        connection.decline()
        notify_connection_event(connection, 'declined')
        messages.info(request, "Request declined.")
    elif action == 'withdraw' and connection.status == Connection.PENDING and is_initiator:
        connection.withdraw()
        messages.info(request, "Request withdrawn.")
    elif action == 'disconnect' and connection.status == Connection.ACTIVE:
        connection.disconnect()
        messages.info(request, "Disconnected.")
    else:
        messages.error(request, "That action isn't available for this connection.")
    return _redirect_back(request)


def manage_meeting_request(request, meeting_id, action):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])
    connection = get_object_or_404(
        Connection,
        Q(pk=meeting_id) & (Q(user_a=request.user) | Q(user_b=request.user)),
    )
    return apply_connection_action(request, connection, action)

def delete_roaster_photo(request, photo_id):
    photo = get_object_or_404(RoasterPhoto, id=photo_id, user=request.user)
    if request.method == 'POST':
        # Delete the file from the filesystem
        if photo.photo and os.path.isfile(photo.photo.path):
            os.remove(photo.photo.path)

        # Delete the record from the database
        photo.delete()

        return redirect('roaster_dashboard')

def connection_farmers(request):
    if request.user.group != 'roaster':
        return redirect('farmer_dashboard')

    farmers = Farmer.objects.prefetch_related(
        'cup_scores_received', 'processing_method', 'farmer_stories',
        'main_roles',
    ).filter(farmer_stories__isnull=False).distinct()
    form = MeetingRequestForm()
    show_modal = False  # Initially, the modal should not be shown

    # Get filter parameters from GET request
    annual_production = request.GET.get('annual_production')
    farm_size = request.GET.get('farm_size')
    country = request.GET.get('country')
    season = request.GET.get('season')
    cup_score = request.GET.get('cup_score')

    # Filter the farmers queryset accordingly
    if annual_production:
        farmers = farmers.filter(annual_production__isnull=False)
        if annual_production == '0-500':
            farmers = farmers.filter(annual_production__gte=0, annual_production__lte=500)
        elif annual_production == '500-2000':
            farmers = farmers.filter(annual_production__gte=500, annual_production__lte=2000)
        elif annual_production == '2000-5000':
            farmers = farmers.filter(annual_production__gte=2000, annual_production__lte=5000)
        elif annual_production == '5000+':
            farmers = farmers.filter(annual_production__gte=5000)

    if farm_size:
        farmers = farmers.filter(farm_size__isnull=False)
        if farm_size == '0.1-2':
            farmers = farmers.filter(farm_size__gte=0.1, farm_size__lte=2)
        elif farm_size == '2-10':
            farmers = farmers.filter(farm_size__gte=2, farm_size__lte=10)
        elif farm_size == '10-50':
            farmers = farmers.filter(farm_size__gte=10, farm_size__lte=50)
        elif farm_size == '50+':
            farmers = farmers.filter(farm_size__gte=50)

    if country:
        farmers = farmers.filter(country=country)

    if season:
        farmers = farmers.filter(harvest_season__id=season)

    if cup_score:
        farmers = farmers.filter(cup_scores_received__id=cup_score)

    if request.method == 'POST':
        # Handle connection request submission
        recipient = get_object_or_404(User, id=request.POST.get('user_id'))
        create_connection_request(request, recipient)
        query_params = request.GET.urlencode()
        redirect_url = reverse('connection_farmers')
        if query_params:
            redirect_url += '?' + query_params
        return HttpResponseRedirect(redirect_url)

    # Connection state for the current user
    can_request_meetings = Connection.pending_sent_count(request.user) < Connection.MAX_PENDING_SENT
    connected_user_ids, sent_user_ids, incoming_user_ids = Connection.status_sets_for(request.user)
    active_meetings_count = len(sent_user_ids)

    # Available countries for filter dropdown
    available_countries = (
        Farmer.objects.filter(farmer_stories__isnull=False)
        .values_list('country', flat=True)
        .distinct()
        .order_by('country')
    )

    # Randomize result order, kept stable across pages via a per-search seed
    try:
        seed = int(request.GET.get('seed'))
    except (TypeError, ValueError):
        seed = random.randint(1, 2_000_000_000)
    farmers_list = list(farmers)
    random.Random(seed).shuffle(farmers_list)

    # Pagination
    paginator = Paginator(farmers_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Build filter query string (without 'page') for template links
    filter_params = request.GET.copy()
    filter_params.pop('page', None)
    filter_params['seed'] = seed
    filter_query_string = filter_params.urlencode()

    return render(request, 'base/connection_farmers.html', {
        'farmers': page_obj,
        'page_obj': page_obj,
        'form': form,
        'show_modal': show_modal,
        'can_request_meetings': can_request_meetings,
        'connected_user_ids': connected_user_ids,
        'sent_user_ids': sent_user_ids,
        'incoming_user_ids': incoming_user_ids,
        'total_meetings_used': active_meetings_count,
        'selected_annual_production': annual_production,
        'selected_farm_size': farm_size,
        'selected_country': country,
        'selected_season': season,
        'available_seasons': Season.objects.all(),
        'selected_cup_score': cup_score,
        'available_cup_scores': CupScore.objects.all(),
        'available_countries': available_countries,
        'filter_query_string': filter_query_string,
    })


def connection_buckets(user):
    """Split a user's connections into (incoming, sent, active) lists.

    Each connection is annotated with ``other_user`` for convenient templating.
    """
    qs = (
        Connection.objects
        .filter(Q(user_a=user) | Q(user_b=user))
        .select_related('user_a', 'user_b', 'initiator')
    )
    incoming, sent, active = [], [], []
    for conn in qs:
        conn.other_user = conn.other(user)
        if conn.status == Connection.ACTIVE:
            active.append(conn)
        elif conn.status == Connection.PENDING:
            if conn.initiator_id == user.id:
                sent.append(conn)
            else:
                incoming.append(conn)
    return incoming, sent, active


def connections(request):
    if request.user.group != 'roaster':
        return redirect('farmer_dashboard')

    incoming, sent, active = connection_buckets(request.user)
    return render(request, 'base/connections.html', {
        'incoming_connections': incoming,
        'sent_connections': sent,
        'active_connections': active,
        'upcoming_forum': Forum.next_upcoming(),
    })


def farmer_view(request, user_id):
    if request.user.group != 'roaster' and request.user.id != user_id:
        return redirect('farmer_dashboard')

    farmer_profile = get_object_or_404(Farmer, user__id=user_id)

    try:
        farmer_photos = FarmerPhoto.objects.filter(user=farmer_profile.user)
        farmer_stories = Story.objects.filter(user=farmer_profile.user)
        farmer_harvest_seasons = Season.objects.filter(farmer=farmer_profile)
        farmer_processing_methods = ProcessingMethod.objects.filter(farmer=farmer_profile)
        farmer_cup_scores = CupScore.objects.filter(farmer=farmer_profile)
        variety = farmer_profile.cultivars.split(',') if farmer_profile.cultivars else []
        is_own_profile = request.user == farmer_profile.user
        active_request = None
        connection_status = 'none'
        if not is_own_profile:
            active_request = Connection.between(request.user, farmer_profile.user)
            if active_request:
                connection_status = active_request.status_for(request.user)
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
        'connection_status': connection_status,
        'active_request': active_request,
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