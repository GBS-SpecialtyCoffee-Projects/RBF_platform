from django.db.models import Max, Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from base.models import Conversation, MeetingRequest, User


def _accepted_connection_exists(roaster, farmer):
    return MeetingRequest.objects.filter(
        requester=roaster, requestee=farmer, status='accepted'
    ).exists()


def _resolve_pair(current_user, other_user):
    if current_user.group == 'roaster' and other_user.group == 'farmer':
        return current_user, other_user
    if current_user.group == 'farmer' and other_user.group == 'roaster':
        return other_user, current_user
    return None, None


def chat_list(request):
    user = request.user
    conversations = (
        Conversation.objects
        .filter(Q(roaster=user) | Q(farmer=user))
        .select_related('roaster', 'farmer')
        .annotate(last_message_at=Max('messages__created_at'))
        .order_by('-last_message_at', '-updated_at')
    )

    items = []
    for conv in conversations:
        other = conv.other_participant(user)
        last = conv.messages.order_by('-created_at').first()
        unread_count = conv.messages.filter(read_at__isnull=True).exclude(sender=user).count()
        items.append({
            'conversation': conv,
            'other': other,
            'last_message': last,
            'unread_count': unread_count,
        })

    return render(request, 'base/chat_list.html', {'items': items})


def chat_thread(request, user_id):
    other = get_object_or_404(User, id=user_id)
    roaster, farmer = _resolve_pair(request.user, other)
    if not roaster or not farmer:
        return HttpResponseForbidden("Chat is only available between a roaster and a farmer.")

    if not _accepted_connection_exists(roaster, farmer):
        return HttpResponseForbidden("You can only chat with accepted connections.")

    conversation, _ = Conversation.objects.get_or_create(roaster=roaster, farmer=farmer)

    conversation.messages.filter(read_at__isnull=True).exclude(sender=request.user).update(
        read_at=timezone.now()
    )

    messages_qs = conversation.messages.select_related('sender').all()
    return render(request, 'base/chat_thread.html', {
        'conversation': conversation,
        'other': other,
        'messages_list': messages_qs,
    })
