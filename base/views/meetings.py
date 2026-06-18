from django.contrib import messages
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST

from base.models import Conversation, ForumMeeting, User
from base.notifications import notify_forum_meeting_event
from base.views.chat import _accepted_connection_exists, _resolve_pair


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
        ForumMeeting.proposable_windows(conversation)
        .filter(id=request.POST.get('window_id'))
        .first()
    )
    if window is None:
        messages.error(request, "That time isn't available to propose.")
        return redirect('chat_thread', user_id=user_id)

    meeting = ForumMeeting.objects.create(
        conversation=conversation, window=window, proposed_by=request.user,
    )
    notify_forum_meeting_event(meeting, 'proposed')
    messages.success(request, "Meeting time proposed.")
    return redirect('chat_thread', user_id=user_id)


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
            meeting.confirm()
            notify_forum_meeting_event(meeting, 'confirmed')
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

    return redirect('chat_thread', user_id=other.id)
