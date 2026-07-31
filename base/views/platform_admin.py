# base/views/platform_admin.py

from datetime import timedelta
from functools import wraps
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login
from django.core.paginator import Paginator
from django.db.models import Q, Count, Value
from django.db.models.functions import Concat
from django.utils.text import slugify
from django.views.decorators.http import require_POST

from django.utils import timezone

from base.models import (
    User, Farmer, Roaster, MeetingRequest, FarmerPhoto, RoasterPhoto,
    Language, Story, AuditLog, AuditAction, Resource, Forum, ForumMeeting,
    AdminEmail,
)
from base import analytics_reports
from base.notifications import notify_admin_message, notify_meeting_calendar_invite
from .forms import (
    FarmerForm, RoasterForm, SigninForm, AdminCreateForm, ResourceForm,
    ForumForm, ForumWindowFormSet, AdminEmailForm,
)


def admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_staff:
            return redirect('admin_login')
        return view_func(request, *args, **kwargs)
    return wrapper


def superadmin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_superuser:
            return redirect('admin_dashboard')
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


def _send_admin_email(request, recipient, form):
    """Persist and send a composed admin email, flashing the real outcome."""
    admin_email = form.save(commit=False)
    admin_email.recipient = recipient
    admin_email.sent_by = request.user
    admin_email.save()
    if notify_admin_message(admin_email):
        messages.success(request, f'Email sent to {recipient.email}.')
    else:
        messages.error(
            request,
            f'Could not send the email to {recipient.email}: {admin_email.error}',
        )


@admin_required
def admin_farmer_detail(request, user_id):
    farmer = get_object_or_404(Farmer, user__id=user_id)
    photos = FarmerPhoto.objects.filter(user=farmer.user).exclude(photo='').exclude(photo__isnull=True)
    email_form = AdminEmailForm()

    if request.method == 'POST':
        if request.POST.get('form_type') == 'email':
            email_form = AdminEmailForm(request.POST)
            if email_form.is_valid():
                _send_admin_email(request, farmer.user, email_form)
                return redirect('admin_farmer_detail', user_id=user_id)
            # Fall through to render so the compose errors are shown, but
            # never let this POST reach the profile form below.
            form = FarmerForm(instance=farmer)

        elif request.POST.get('form_type') == 'status':
            farmer.is_details_filled = 'is_details_filled' in request.POST
            farmer.is_profile_published = 'is_profile_published' in request.POST
            farmer.save(update_fields=['is_details_filled', 'is_profile_published'])
            messages.success(request, 'Account status updated.')
            return redirect('admin_farmer_detail', user_id=user_id)

        elif request.POST.get('form_type') == 'story':
            language = get_object_or_404(Language, id=request.POST.get('language_id'))
            story_text = request.POST.get('story_text', '').strip()
            story = Story.objects.filter(user=farmer.user, language=language).first()
            if story:
                story.story_text = story_text
                story.save(update_fields=['story_text'])
                messages.success(request, f'Story ({language.name}) updated.')
            else:
                Story.objects.create(
                    user=farmer.user, farmer=farmer,
                    language=language, story_text=story_text,
                )
                messages.success(request, f'Story ({language.name}) added.')
            return redirect('admin_farmer_detail', user_id=user_id)

        else:
            form = FarmerForm(request.POST, request.FILES, instance=farmer)
            if form.is_valid():
                form.save()
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
        'email_form': email_form,
        'sent_emails': AdminEmail.objects.filter(recipient=farmer.user)[:5],
    })


@admin_required
def admin_roaster_detail(request, user_id):
    roaster = get_object_or_404(Roaster, user__id=user_id)
    photos = RoasterPhoto.objects.filter(user=roaster.user)
    email_form = AdminEmailForm()

    if request.method == 'POST':
        if request.POST.get('form_type') == 'email':
            email_form = AdminEmailForm(request.POST)
            if email_form.is_valid():
                _send_admin_email(request, roaster.user, email_form)
                return redirect('admin_roaster_detail', user_id=user_id)
            # Fall through to render so the compose errors are shown, but
            # never let this POST reach the profile form below.
            form = RoasterForm(instance=roaster)

        elif request.POST.get('form_type') == 'status':
            roaster.is_details_filled = 'is_details_filled' in request.POST
            roaster.save(update_fields=['is_details_filled'])
            messages.success(request, 'Account status updated.')
            return redirect('admin_roaster_detail', user_id=user_id)

        else:
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
        'email_form': email_form,
        'sent_emails': AdminEmail.objects.filter(recipient=roaster.user)[:5],
    })


@superadmin_required
def admin_users(request):
    admins = User.objects.filter(is_staff=True).order_by('-date_joined')
    return render(request, 'base/platform_admin/admins.html', {'admins': admins})


@superadmin_required
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


@superadmin_required
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
def admin_emails(request):
    """Compose a one-off email to any platform user, with a send history."""
    email_form = AdminEmailForm()

    if request.method == 'POST':
        recipient = get_object_or_404(
            User, id=request.POST.get('recipient'), is_staff=False,
        )
        email_form = AdminEmailForm(request.POST)
        if email_form.is_valid():
            _send_admin_email(request, recipient, email_form)
            return redirect('admin_emails')

    sent = AdminEmail.objects.select_related('recipient', 'sent_by')
    paginator = Paginator(sent, 20)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'base/platform_admin/emails.html', {
        'email_form': email_form,
        'recipients': User.objects.filter(is_staff=False).order_by('email'),
        'sent_emails': page,
    })


@superadmin_required
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


RANGE_OPTIONS = [('7', 'Last 7 days'), ('30', 'Last 30 days'),
                 ('90', 'Last 90 days'), ('all', 'All time')]


@admin_required
def admin_analytics(request):
    """Staff dashboard: how roasters and farmers interact (funnel, story
    impact, match quality, engagement volume)."""
    days = request.GET.get('days', '30')
    valid = {value for value, _ in RANGE_OPTIONS}
    if days not in valid:
        days = '30'
    start = None if days == 'all' else timezone.now() - timedelta(days=int(days))

    funnel = analytics_reports.funnel(start=start)
    story = analytics_reports.story_impact(start=start)
    match = analytics_reports.match_quality(start=start)
    volume = analytics_reports.engagement_volume(start=start)

    charts = {
        'funnel': {
            'labels': [s['label'] for s in funnel['stages']],
            'counts': [s['count'] for s in funnel['stages']],
        },
        'timeseries': {
            'labels': [row['day'] for row in volume['timeseries']],
            'counts': [row['n'] for row in volume['timeseries']],
        },
        'story': {
            'labels': ['With stories', 'Without stories'],
            'avg_views': [story['with_stories']['avg_views_per_farmer'],
                          story['without_stories']['avg_views_per_farmer']],
            'avg_active': [story['with_stories']['avg_active_per_farmer'],
                           story['without_stories']['avg_active_per_farmer']],
        },
        'farmer_country': {
            'labels': [c for c, _ in match['by_farmer_country'][:10]],
            'counts': [n for _, n in match['by_farmer_country'][:10]],
        },
    }

    return render(request, 'base/platform_admin/analytics.html', {
        'days': days,
        'range_options': RANGE_OPTIONS,
        'funnel': funnel,
        'story': story,
        'match': match,
        'volume': volume,
        'charts': charts,
    })
