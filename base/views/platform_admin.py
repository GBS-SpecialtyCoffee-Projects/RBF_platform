# base/views/platform_admin.py

from functools import wraps
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login
from django.core.paginator import Paginator
from django.db.models import Q, Count, Value
from django.db.models.functions import Concat
from django.utils.text import slugify
from django.views.decorators.http import require_POST

from base.models import (
    User, Farmer, Roaster, MeetingRequest, FarmerPhoto, RoasterPhoto,
    Language, Story, AuditLog, AuditAction, Resource,
)
from .forms import FarmerForm, RoasterForm, SigninForm, AdminCreateForm, ResourceForm


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


@admin_required
def admin_farmer_detail(request, user_id):
    farmer = get_object_or_404(Farmer, user__id=user_id)
    photos = FarmerPhoto.objects.filter(user=farmer.user)

    if request.method == 'POST':
        if request.POST.get('form_type') == 'status':
            farmer.is_details_filled = 'is_details_filled' in request.POST
            farmer.is_profile_published = 'is_profile_published' in request.POST
            farmer.save(update_fields=['is_details_filled', 'is_profile_published'])
            messages.success(request, 'Account status updated.')
            return redirect('admin_farmer_detail', user_id=user_id)

        if request.POST.get('form_type') == 'story':
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
