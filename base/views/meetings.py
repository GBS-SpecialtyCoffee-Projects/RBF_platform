from collections import defaultdict

from django.contrib import messages
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from base.analytics import log_event
from base.models import Conversation, ForumMeeting, InteractionEventType, User
from base.notifications import notify_forum_meeting_event
from base.views.chat import _accepted_connection_exists, _resolve_pair


def _redirect_back(request, user_id):
    """Redirect to the referring page if it is safe, else the chat thread.

    Meetings can be proposed and answered from the connections pages as well as
    from chat, so send the user back where they started.
    """
    referer = request.META.get('HTTP_REFERER', '')
    if referer and url_has_allowed_host_and_scheme(
        referer, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return redirect(referer)
    return redirect('chat_thread', user_id=user_id)


def annotate_connection_meetings(user, connections):
    """Attach live meetings and proposable windows to accepted Connection rows.

    Lets the connections pages offer the same propose/confirm actions as the
    chat thread without an extra query per row.
    """
    # Ids only: the rows are keyed by the other participant, so pulling the
    # User objects back out would cost a query per conversation.
    conversation_ids = {}
    for conv_id, roaster_id, farmer_id in (
        Conversation.objects
        .filter(Q(roaster=user) | Q(farmer=user))
        .values_list('id', 'roaster_id', 'farmer_id')
    ):
        other_id = farmer_id if roaster_id == user.id else roaster_id
        conversation_ids[other_id] = conv_id

    meetings_by_conversation = defaultdict(list)
    if conversation_ids:
        live = (
            ForumMeeting.objects
            .filter(
                conversation_id__in=conversation_ids.values(),
                status__in=ForumMeeting.LIVE_STATUSES,
                window__starts_at__gt=timezone.now(),
            )
            .select_related(
                'window', 'window__forum', 'proposed_by',
                # invitee_needs_signup() walks conversation -> both participants.
                'conversation', 'conversation__roaster', 'conversation__farmer',
            )
        )
        for meeting in live:
            meetings_by_conversation[meeting.conversation_id].append(meeting)

    candidates = list(ForumMeeting.candidate_windows(user))

    for conn in connections:
        meetings = meetings_by_conversation.get(
            conversation_ids.get(conn.other_user.id), []
        )
        taken = {meeting.window_id for meeting in meetings}
        conn.live_meetings = meetings
        conn.proposable_windows = [w for w in candidates if w.id not in taken]
    return connections


@require_POST
def propose_meeting(request, user_id):
    other = get_object_or_404(User, id=user_id)
    roaster, farmer = _resolve_pair(request.user, other)
    if not roaster or not farmer or not _accepted_connection_exists(roaster, farmer):
        return HttpResponseForbidden(
            "You can only schedule meetings with accepted connections."
        )

    conversation, _ = Conversation.objects.get_or_create(roaster=roaster, farmer=farmer)
    window = (
        ForumMeeting.proposable_windows(conversation, request.user)
        .filter(id=request.POST.get('window_id'))
        .first()
    )
    if window is None:
        messages.error(request, "That time isn't available to propose.")
        return _redirect_back(request, user_id)

    meeting = ForumMeeting.objects.create(
        conversation=conversation, window=window, proposed_by=request.user,
    )
    notify_forum_meeting_event(meeting, 'proposed')
    log_event(
        InteractionEventType.MEETING_PROPOSED, request=request,
        target_user=other, meeting_id=meeting.id,
    )
    messages.success(request, "Meeting time proposed.")
    return _redirect_back(request, user_id)


@require_POST
def respond_meeting(request, meeting_id, action):
    meeting = get_object_or_404(ForumMeeting, id=meeting_id)
    conversation = meeting.conversation
    if not conversation.has_participant(request.user):
        return HttpResponseForbidden("Not your meeting.")

    other = conversation.other_participant(request.user)
    is_proposer = meeting.proposed_by_id == request.user.id
    is_live = meeting.status in ForumMeeting.LIVE_STATUSES

    if action in ('confirm', 'decline') and not is_proposer \
            and meeting.status == ForumMeeting.PROPOSED:
        if action == 'confirm':
            # Confirming a meeting in a forum they had not joined signs them
            # up for it, which is what the button promises.
            joined = meeting.accept_signup(request.user)
            if meeting.invitee_needs_signup():
                # The forum closed between proposal and response, so we cannot
                # honour the signup half of the promise.
                messages.error(
                    request,
                    f"{meeting.forum.title} is no longer open for signups, so "
                    "this meeting can't be confirmed.",
                )
                return _redirect_back(request, other.id)
            meeting.confirm()
            notify_forum_meeting_event(meeting, 'confirmed')
            if joined:
                messages.success(
                    request,
                    f"Meeting confirmed. You are now signed up for "
                    f"{meeting.forum.title}.",
                )
            else:
                messages.success(request, "Meeting confirmed.")
        else:
            meeting.decline()
            notify_forum_meeting_event(meeting, 'declined')
            messages.info(request, "Meeting declined.")
    elif action == 'cancel' and is_proposer and is_live:
        meeting.cancel()
        messages.info(request, "Meeting cancelled.")
    else:
        messages.error(request, "That action isn't allowed.")

    return _redirect_back(request, other.id)
