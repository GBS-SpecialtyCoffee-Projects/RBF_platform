from django.contrib import messages
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from base.models import Forum, ForumSignup


def forum_list(request):
    forums = (
        Forum.objects.filter(status=Forum.PUBLISHED)
        .filter(Q(windows__isnull=True) | Q(windows__ends_at__gt=timezone.now()))
        .distinct()
        .prefetch_related('windows')
    )
    signed_up_ids = set(
        ForumSignup.objects.filter(user=request.user, forum__in=forums)
        .values_list('forum_id', flat=True)
    )
    return render(request, 'base/forums/forum_list.html', {
        'forums': forums,
        'signed_up_ids': signed_up_ids,
    })


def forum_detail(request, forum_id):
    forum = get_object_or_404(Forum, id=forum_id, status=Forum.PUBLISHED)
    if forum.is_over:
        raise Http404('This forum has ended.')
    return render(request, 'base/forums/forum_detail.html', {
        'forum': forum,
        'is_signed_up': forum.is_signed_up(request.user),
    })


@require_POST
def forum_signup(request, forum_id):
    forum = get_object_or_404(Forum, id=forum_id)
    if not forum.is_open:
        messages.error(request, 'This forum is not open for signups.')
    else:
        _, created = ForumSignup.objects.get_or_create(forum=forum, user=request.user)
        if created:
            messages.success(request, f'You signed up for {forum.title}.')
        else:
            messages.info(request, 'You are already signed up for this forum.')
    return _redirect_back(request, forum)


@require_POST
def forum_cancel_signup(request, forum_id):
    forum = get_object_or_404(Forum, id=forum_id)
    deleted, _ = ForumSignup.objects.filter(forum=forum, user=request.user).delete()
    if deleted:
        messages.success(request, f'Your signup for {forum.title} was cancelled.')
    return _redirect_back(request, forum)


def _redirect_back(request, forum):
    """Redirect to the referring page if it is safe, else the forum detail."""
    referer = request.META.get('HTTP_REFERER', '')
    if referer and url_has_allowed_host_and_scheme(
        referer, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return redirect(referer)
    return redirect('forum_detail', forum_id=forum.id)
