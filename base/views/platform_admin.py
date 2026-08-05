# base/views/platform_admin.py

import csv
from datetime import timedelta
from functools import wraps
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login
from django.core.paginator import Paginator
from django.db.models import Q, Count, F, Value, IntegerField, OuterRef, Subquery
from django.db.models.functions import Coalesce, Concat
from django.http import HttpResponse
from django.utils.text import slugify
from django.views.decorators.http import require_POST

from django.utils import timezone

from base.models import (
    User, Farmer, Roaster, MeetingRequest, Connection, FarmerPhoto, RoasterPhoto,
    Language, Story, AuditLog, AuditAction, Resource, Forum, ForumMeeting,
    InteractionEvent, InteractionEventType, ProfileChange, ProfileChangeSource,
)
from base.notifications import notify_meeting_calendar_invite
from base.profile_history import record_field_change, record_form_change
from .forms import (
    FarmerForm, RoasterForm, SigninForm, AdminCreateForm, ResourceForm,
    ForumForm, ForumWindowFormSet,
)


def admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_staff:
            return redirect('admin_login')
        return view_func(request, *args, **kwargs)
    return wrapper


def admin_login(request):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect('admin_dashboard')

    error = None
    if request.method == 'POST':
        form = SigninForm(request.POST)
        if form.is_valid():
            user = form.get_user()
            if user and user.is_staff:
                login(request, user)
                return redirect('admin_dashboard')
            else:
                error = 'Invalid credentials.'
        else:
            error = 'Invalid credentials.'

    return render(request, 'base/platform_admin/login.html', {'error': error})


@admin_required
def admin_dashboard(request):
    total_farmers = Farmer.objects.count()
    total_roasters = Roaster.objects.count()
    recent_farmers = Farmer.objects.select_related('user').order_by('-created_at')[:5]
    recent_roasters = Roaster.objects.select_related('user').order_by('-created_at')[:5]

    meeting_requests = MeetingRequest.objects.values('status').annotate(count=Count('status'))
    meeting_counts = {item['status']: item['count'] for item in meeting_requests}

    context = {
        'total_farmers': total_farmers,
        'total_roasters': total_roasters,
        'recent_farmers': recent_farmers,
        'recent_roasters': recent_roasters,
        'meeting_counts': meeting_counts,
    }
    return render(request, 'base/platform_admin/dashboard.html', context)


@admin_required
def admin_farmers(request):
    query = request.GET.get('q', '')
    farmers = Farmer.objects.select_related('user').order_by('-created_at')
    if query:
        farmers = farmers.annotate(
            full_name=Concat('firstname', Value(' '), 'lastname'),
        ).filter(
            Q(full_name__icontains=query) |
            Q(farm_name__icontains=query) |
            Q(user__email__icontains=query) |
            Q(country__icontains=query)
        )
    paginator = Paginator(farmers, 20)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'base/platform_admin/farmers.html', {'farmers': page, 'query': query})


@admin_required
def admin_roasters(request):
    query = request.GET.get('q', '')
    roasters = Roaster.objects.select_related('user').order_by('-created_at')
    if query:
        roasters = roasters.annotate(
            full_name=Concat('firstname', Value(' '), 'lastname'),
        ).filter(
            Q(full_name__icontains=query) |
            Q(company_name__icontains=query) |
            Q(user__email__icontains=query) |
            Q(country__icontains=query)
        )
    paginator = Paginator(roasters, 20)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'base/platform_admin/roasters.html', {'roasters': page, 'query': query})


@admin_required
def admin_farmer_detail(request, user_id):
    farmer = get_object_or_404(Farmer, user__id=user_id)
    photos = FarmerPhoto.objects.filter(user=farmer.user).exclude(photo='').exclude(photo__isnull=True)

    if request.method == 'POST':
        if request.POST.get('form_type') == 'status':
            was_published = farmer.is_profile_published
            farmer.is_details_filled = 'is_details_filled' in request.POST
            farmer.is_profile_published = 'is_profile_published' in request.POST
            farmer.save(update_fields=['is_details_filled', 'is_profile_published'])
            record_field_change(
                farmer.user, source=ProfileChangeSource.ADMIN,
                field='is_profile_published', old=was_published,
                new=farmer.is_profile_published, changed_by=request.user,
            )
            messages.success(request, 'Account status updated.')
            return redirect('admin_farmer_detail', user_id=user_id)

        if request.POST.get('form_type') == 'story':
            language = get_object_or_404(Language, id=request.POST.get('language_id'))
            story_text = request.POST.get('story_text', '').strip()
            story = Story.objects.filter(user=farmer.user, language=language).first()
            if story:
                previous = story.story_text
                story.story_text = story_text
                story.save(update_fields=['story_text'])
                record_field_change(
                    farmer.user, source=ProfileChangeSource.ADMIN,
                    field='story_text', old=previous, new=story_text,
                    changed_by=request.user,
                )
                messages.success(request, f'Story ({language.name}) updated.')
            else:
                Story.objects.create(
                    user=farmer.user, farmer=farmer,
                    language=language, story_text=story_text,
                )
                messages.success(request, f'Story ({language.name}) added.')
            return redirect('admin_farmer_detail', user_id=user_id)

        form = FarmerForm(request.POST, request.FILES, instance=farmer)
        if form.is_valid():
            form.save()
            record_form_change(
                form, user=farmer.user, source=ProfileChangeSource.ADMIN,
                changed_by=request.user,
            )
            messages.success(request, f'Profile for {farmer.user.email} updated.')
            return redirect('admin_farmer_detail', user_id=user_id)
    else:
        form = FarmerForm(instance=farmer)

    languages = Language.objects.all()
    stories = {s.language_id: s for s in Story.objects.filter(user=farmer.user)}
    language_stories = [(lang, stories.get(lang.id)) for lang in languages]

    return render(request, 'base/platform_admin/farmer_detail.html', {
        'farmer': farmer,
        'form': form,
        'photos': photos,
        'language_stories': language_stories,
    })


@admin_required
def admin_roaster_detail(request, user_id):
    roaster = get_object_or_404(Roaster, user__id=user_id)
    photos = RoasterPhoto.objects.filter(user=roaster.user)

    if request.method == 'POST':
        if request.POST.get('form_type') == 'status':
            roaster.is_details_filled = 'is_details_filled' in request.POST
            roaster.save(update_fields=['is_details_filled'])
            messages.success(request, 'Account status updated.')
            return redirect('admin_roaster_detail', user_id=user_id)

        form = RoasterForm(request.POST, request.FILES, instance=roaster)
        if form.is_valid():
            form.save()
            messages.success(request, f'Profile for {roaster.user.email} updated.')
            return redirect('admin_roaster_detail', user_id=user_id)
    else:
        form = RoasterForm(instance=roaster)

    return render(request, 'base/platform_admin/roaster_detail.html', {
        'roaster': roaster,
        'form': form,
        'photos': photos,
    })


@admin_required
def admin_users(request):
    admins = User.objects.filter(is_staff=True).order_by('-date_joined')
    return render(request, 'base/platform_admin/admins.html', {'admins': admins})


@admin_required
def admin_create(request):
    if request.method == 'POST':
        form = AdminCreateForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            user = User.objects.create_user(
                email=email,
                password=form.cleaned_data['password'],
                username=email,
            )
            user.is_staff = True
            user.save(update_fields=['is_staff'])
            messages.success(request, f'Admin account created for {user.email}.')
            return redirect('admin_users')
    else:
        form = AdminCreateForm()
    return render(request, 'base/platform_admin/admin_create.html', {'form': form})


@admin_required
def admin_toggle(request, user_id):
    if request.method == 'POST':
        user = get_object_or_404(User, id=user_id)
        if user == request.user:
            messages.error(request, 'You cannot change your own admin status.')
        elif user.is_superuser:
            messages.error(request, 'Cannot modify a super admin.')
        else:
            user.is_staff = not user.is_staff
            user.save(update_fields=['is_staff'])
            status = 'granted' if user.is_staff else 'revoked'
            messages.success(request, f'Admin access {status} for {user.email}.')
    return redirect('admin_users')


@admin_required
def admin_resources(request):
    query = request.GET.get('q', '')
    resources = Resource.objects.all()
    if query:
        resources = resources.filter(
            Q(title__icontains=query) | Q(summary__icontains=query)
        )
    paginator = Paginator(resources, 20)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'base/platform_admin/resources.html', {
        'resources': page,
        'query': query,
    })


def _unique_slug(base, exclude_pk=None):
    slug = base or 'resource'
    candidate = slug
    i = 2
    qs = Resource.objects.all()
    if exclude_pk is not None:
        qs = qs.exclude(pk=exclude_pk)
    while qs.filter(slug=candidate).exists():
        candidate = f'{slug}-{i}'
        i += 1
    return candidate


@admin_required
def admin_resource_create(request):
    if request.method == 'POST':
        form = ResourceForm(request.POST, request.FILES)
        if form.is_valid():
            resource = form.save(commit=False)
            slug = form.cleaned_data.get('slug') or slugify(resource.title)
            resource.slug = _unique_slug(slug)
            resource.author = request.user
            resource.save()
            messages.success(request, 'Resource created.')
            return redirect('admin_resources')
    else:
        form = ResourceForm()
    return render(request, 'base/platform_admin/resource_form.html', {
        'form': form,
        'resource': None,
    })


@admin_required
def admin_resource_edit(request, resource_id):
    resource = get_object_or_404(Resource, id=resource_id)
    if request.method == 'POST':
        form = ResourceForm(request.POST, request.FILES, instance=resource)
        if form.is_valid():
            updated = form.save(commit=False)
            slug = form.cleaned_data.get('slug') or slugify(updated.title)
            if slug != resource.slug:
                updated.slug = _unique_slug(slug, exclude_pk=resource.pk)
            updated.save()
            messages.success(request, 'Resource updated.')
            return redirect('admin_resources')
    else:
        form = ResourceForm(instance=resource)
    return render(request, 'base/platform_admin/resource_form.html', {
        'form': form,
        'resource': resource,
    })


@admin_required
@require_POST
def admin_resource_delete(request, resource_id):
    resource = get_object_or_404(Resource, id=resource_id)
    resource.delete()
    messages.success(request, 'Resource deleted.')
    return redirect('admin_resources')


@admin_required
def admin_forums(request):
    query = request.GET.get('q', '')
    forums = Forum.objects.all()
    if query:
        forums = forums.filter(Q(title__icontains=query))
    paginator = Paginator(forums, 20)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'base/platform_admin/forums.html', {
        'forums': page,
        'query': query,
    })


@admin_required
def admin_forum_create(request):
    if request.method == 'POST':
        form = ForumForm(request.POST)
        formset = ForumWindowFormSet(request.POST, prefix='windows')
        if form.is_valid() and formset.is_valid():
            forum = form.save(commit=False)
            forum.created_by = request.user
            forum.save()
            formset.instance = forum
            formset.save()
            messages.success(request, 'Forum created.')
            return redirect('admin_forums')
    else:
        form = ForumForm()
        formset = ForumWindowFormSet(prefix='windows')
    return render(request, 'base/platform_admin/forum_form.html', {
        'form': form,
        'formset': formset,
        'forum': None,
    })


@admin_required
def admin_forum_edit(request, forum_id):
    forum = get_object_or_404(Forum, id=forum_id)
    if request.method == 'POST':
        form = ForumForm(request.POST, instance=forum)
        formset = ForumWindowFormSet(request.POST, instance=forum, prefix='windows')
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            messages.success(request, 'Forum updated.')
            return redirect('admin_forums')
    else:
        form = ForumForm(instance=forum)
        formset = ForumWindowFormSet(instance=forum, prefix='windows')
    return render(request, 'base/platform_admin/forum_form.html', {
        'form': form,
        'formset': formset,
        'forum': forum,
    })


@admin_required
@require_POST
def admin_forum_delete(request, forum_id):
    forum = get_object_or_404(Forum, id=forum_id)
    forum.delete()
    messages.success(request, 'Forum deleted.')
    return redirect('admin_forums')


@admin_required
def admin_meetings(request):
    meetings = ForumMeeting.confirmed_upcoming()
    paginator = Paginator(meetings, 20)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'base/platform_admin/meetings.html', {
        'meetings': page,
    })


@admin_required
@require_POST
def admin_meeting_send_invite(request, meeting_id):
    meeting = get_object_or_404(ForumMeeting, id=meeting_id)
    meeting.meeting_link = request.POST.get('meeting_link', '').strip()
    meeting.invite_sent_at = timezone.now()
    meeting.save(update_fields=['meeting_link', 'invite_sent_at', 'updated_at'])
    notify_meeting_calendar_invite(meeting)
    messages.success(request, 'Calendar invite sent to both participants.')
    return redirect('admin_meetings')


@admin_required
def admin_pending_requests(request):
    """Connection requests still awaiting a response, longest-waiting first."""
    connections = (
        Connection.objects.filter(status=Connection.PENDING)
        .select_related('initiator', 'user_a', 'user_b')
        .order_by('created_at')
    )
    paginator = Paginator(connections, 20)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'base/platform_admin/pending_requests.html', {
        'connections': page,
    })


def _filtered_interactions(request):
    """Apply the raw-interaction filters shared by the table and CSV export."""
    events = InteractionEvent.objects.select_related('user', 'target_user')
    event_type = request.GET.get('event_type', '')
    if event_type:
        events = events.filter(event_type=event_type)
    date_from = request.GET.get('from', '')
    if date_from:
        events = events.filter(created_at__date__gte=date_from)
    date_to = request.GET.get('to', '')
    if date_to:
        events = events.filter(created_at__date__lte=date_to)
    user_query = request.GET.get('user', '')
    if user_query:
        events = events.filter(user__email__icontains=user_query)
    return events


@admin_required
def admin_interactions(request):
    events = _filtered_interactions(request)

    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = (
            'attachment; filename="interaction_events.csv"'
        )
        writer = csv.writer(response)
        writer.writerow([
            'id', 'created_at', 'event_type', 'user', 'target_user',
            'path', 'session_key', 'metadata',
        ])
        for event in events.iterator():
            writer.writerow([
                event.id,
                event.created_at.isoformat(),
                event.event_type,
                event.user.email if event.user else '',
                event.target_user.email if event.target_user else '',
                event.path,
                event.session_key,
                event.metadata,
            ])
        return response

    paginator = Paginator(events, 50)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'base/platform_admin/interactions.html', {
        'events': page,
        'event_type_choices': InteractionEventType.choices,
        'filters': {
            'event_type': request.GET.get('event_type', ''),
            'from': request.GET.get('from', ''),
            'to': request.GET.get('to', ''),
            'user': request.GET.get('user', ''),
        },
    })


def _count_subquery(queryset):
    """Wrap a correlated queryset as a COUNT subquery, yielding 0 when empty.

    Grouping on a constant collapses the rows to a single count, so the
    subquery stays scalar and never inflates the outer query.
    """
    counted = (
        queryset.order_by()
        .values(_group=Value(1))
        .annotate(total=Count('id'))
        .values('total')
    )
    return Coalesce(Subquery(counted, output_field=IntegerField()), 0)


def _connections_involving(**filters):
    """Connections the outer user is a participant of (either side)."""
    return Connection.objects.filter(
        Q(user_a=OuterRef('pk')) | Q(user_b=OuterRef('pk')), **filters
    )


def _meetings_involving(**filters):
    """Forum meetings the outer user is a participant of (either side)."""
    return ForumMeeting.objects.filter(
        Q(conversation__roaster=OuterRef('pk'))
        | Q(conversation__farmer=OuterRef('pk')),
        **filters,
    )


# Sortable columns, mapped to the annotation they order by.
ENGAGEMENT_SORTS = {
    'received': '-connections_received',
    'unaccepted': '-connections_unaccepted',
    'sent': '-requests_sent',
    'scheduled': '-meetings_scheduled',
    'pending': '-meetings_pending',
    'last_login': F('last_login').desc(nulls_last=True),
    # Default: longest-idle first, never-active users at the very top.
    'idle': F('last_activity').asc(nulls_first=True),
}


def _engagement_queryset(request):
    """Per-user engagement counts, filtered by the request's query string."""
    users = (
        User.objects.filter(is_staff=False)
        .select_related('farmer_profile', 'roaster_profile')
        .annotate(
            connections_received=_count_subquery(
                _connections_involving().exclude(initiator=OuterRef('pk'))
            ),
            connections_unaccepted=_count_subquery(
                _connections_involving(status=Connection.PENDING)
                .exclude(initiator=OuterRef('pk'))
            ),
            requests_sent=_count_subquery(
                Connection.objects.filter(initiator=OuterRef('pk'))
            ),
            meetings_scheduled=_count_subquery(
                _meetings_involving(status=ForumMeeting.CONFIRMED)
            ),
            meetings_pending=_count_subquery(
                _meetings_involving(status=ForumMeeting.PROPOSED)
            ),
            last_activity=Subquery(
                InteractionEvent.objects.filter(user=OuterRef('pk'))
                .order_by('-created_at')
                .values('created_at')[:1]
            ),
        )
    )

    group = request.GET.get('group', '')
    if group in dict(User.GROUP_CHOICES):
        users = users.filter(group=group)

    user_query = request.GET.get('user', '')
    if user_query:
        users = users.filter(email__icontains=user_query)

    idle_days = request.GET.get('idle', '')
    if idle_days.isdigit():
        cutoff = timezone.now() - timedelta(days=int(idle_days))
        users = users.filter(
            Q(last_activity__lt=cutoff) | Q(last_activity__isnull=True)
        )

    if request.GET.get('blocking'):
        users = users.filter(connections_unaccepted__gt=0)

    sort = request.GET.get('sort', 'idle')
    return users.order_by(ENGAGEMENT_SORTS.get(sort, ENGAGEMENT_SORTS['idle']))


@admin_required
def admin_engagement(request):
    """Per-user connection and meeting counts, for spotting inactive users."""
    users = _engagement_queryset(request)

    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = (
            'attachment; filename="user_engagement.csv"'
        )
        writer = csv.writer(response)
        writer.writerow([
            'email', 'group', 'connections_received', 'connections_unaccepted',
            'requests_sent', 'meetings_scheduled', 'meetings_pending',
            'last_login', 'last_activity',
        ])
        for user in users.iterator():
            writer.writerow([
                user.email,
                user.group,
                user.connections_received,
                user.connections_unaccepted,
                user.requests_sent,
                user.meetings_scheduled,
                user.meetings_pending,
                user.last_login.isoformat() if user.last_login else '',
                user.last_activity.isoformat() if user.last_activity else '',
            ])
        return response

    paginator = Paginator(users, 50)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'base/platform_admin/engagement.html', {
        'users': page,
        'group_choices': User.GROUP_CHOICES,
        'filters': {
            'group': request.GET.get('group', ''),
            'user': request.GET.get('user', ''),
            'idle': request.GET.get('idle', ''),
            'blocking': request.GET.get('blocking', ''),
            'sort': request.GET.get('sort', 'idle'),
        },
    })


def _filtered_profile_changes(request):
    """Apply the filters shared by the history table and its CSV export."""
    changes = (
        ProfileChange.objects.select_related('user', 'changed_by')
        .filter(user__group='farmer')
    )
    source = request.GET.get('source', '')
    if source:
        changes = changes.filter(source=source)
    date_from = request.GET.get('from', '')
    if date_from:
        changes = changes.filter(created_at__date__gte=date_from)
    date_to = request.GET.get('to', '')
    if date_to:
        changes = changes.filter(created_at__date__lte=date_to)
    user_query = request.GET.get('user', '')
    if user_query:
        changes = changes.filter(user__email__icontains=user_query)
    return changes


@admin_required
def admin_profile_history(request):
    """History of farmer profile edits: what changed, when, and by whom."""
    changes = _filtered_profile_changes(request)

    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = (
            'attachment; filename="profile_changes.csv"'
        )
        writer = csv.writer(response)
        writer.writerow([
            'created_at', 'user', 'changed_by', 'source',
            'field', 'old_value', 'new_value',
        ])
        # One row per changed field, so the export is analysable as a table
        # rather than as JSON blobs.
        for change in changes.iterator():
            for field, values in sorted(change.changes.items()):
                writer.writerow([
                    change.created_at.isoformat(),
                    change.user.email if change.user else '',
                    change.changed_by.email if change.changed_by else '',
                    change.source,
                    field,
                    values.get('old', ''),
                    values.get('new', ''),
                ])
        return response

    paginator = Paginator(changes, 50)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'base/platform_admin/profile_history.html', {
        'changes': page,
        'source_choices': ProfileChangeSource.choices,
        'filters': {
            'source': request.GET.get('source', ''),
            'from': request.GET.get('from', ''),
            'to': request.GET.get('to', ''),
            'user': request.GET.get('user', ''),
        },
    })


@admin_required
def admin_audit_log(request):
    logs = AuditLog.objects.select_related('user').all()
    action_filter = request.GET.get('action', '')
    if action_filter:
        logs = logs.filter(action=action_filter)
    paginator = Paginator(logs, 50)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'base/platform_admin/audit_log.html', {
        'logs': page,
        'action_choices': AuditAction.choices,
        'current_filter': action_filter,
    })
