import logging
from datetime import timezone as dt_timezone

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)


def _ics_escape(text):
    """Escape a value for an iCalendar text field."""
    return (
        str(text)
        .replace('\\', '\\\\')
        .replace(';', '\\;')
        .replace(',', '\\,')
        .replace('\n', '\\n')
    )


def _build_ics(meeting):
    """Build an iCalendar (VEVENT) invite for a confirmed ForumMeeting."""
    window = meeting.window
    roaster = meeting.conversation.roaster
    farmer = meeting.conversation.farmer
    fmt = '%Y%m%dT%H%M%SZ'
    summary = (
        f"Coffee meeting: {_display_name(roaster)} × {_display_name(farmer)}"
    )
    description = f"{meeting.forum.title} meeting."
    if meeting.meeting_link:
        description = f"{description}\nJoin: {meeting.meeting_link}"

    lines = [
        'BEGIN:VCALENDAR',
        'VERSION:2.0',
        'PRODID:-//RBF Platform//Forum Meeting//EN',
        'METHOD:REQUEST',
        'BEGIN:VEVENT',
        f'UID:forum-meeting-{meeting.id}@rbf-platform',
        f'DTSTAMP:{timezone.now().strftime(fmt)}',
        f'DTSTART:{window.starts_at.astimezone(dt_timezone.utc).strftime(fmt)}',
        f'DTEND:{window.ends_at.astimezone(dt_timezone.utc).strftime(fmt)}',
        f'SUMMARY:{_ics_escape(summary)}',
        f'DESCRIPTION:{_ics_escape(description)}',
        f'ORGANIZER:mailto:{settings.DEFAULT_FROM_EMAIL}',
        f'ATTENDEE;ROLE=REQ-PARTICIPANT;RSVP=TRUE:mailto:{roaster.email}',
        f'ATTENDEE;ROLE=REQ-PARTICIPANT;RSVP=TRUE:mailto:{farmer.email}',
    ]
    if meeting.meeting_link:
        lines.append(f'LOCATION:{_ics_escape(meeting.meeting_link)}')
        lines.append(f'URL:{_ics_escape(meeting.meeting_link)}')
    lines += ['STATUS:CONFIRMED', 'END:VEVENT', 'END:VCALENDAR']
    return '\r\n'.join(lines)


def _display_name(user):
    profile = getattr(user, 'farmer_profile', None) or getattr(
        user, 'roaster_profile', None
    )
    if profile and (profile.firstname or profile.lastname):
        return f"{profile.firstname or ''} {profile.lastname or ''}".strip()
    return user.email


def _send(user, subject, template, context):
    # Single dispatch seam. Today: email only.
    # Future: switch on user.preferred_channel to route to WhatsApp etc.
    if not user.email:
        logger.warning("Skipping notification for user %s: no email", user.pk)
        return
    try:
        html_body = render_to_string(template, context)
        text_body = strip_tags(html_body)
        message = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email],
        )
        message.attach_alternative(html_body, "text/html")
        message.send()
    except Exception:
        logger.exception(
            "Failed to send notification to %s (subject=%r)", user.email, subject
        )


def notify_connection_event(connection, event):
    """Email notifications for the Connection lifecycle (created/accepted/declined)."""
    initiator = connection.initiator
    recipient = connection.recipient
    initiator_name = _display_name(initiator)
    recipient_name = _display_name(recipient)
    base_context = {
        'connection': connection,
        'initiator_name': initiator_name,
        'recipient_name': recipient_name,
    }

    if event == 'created':
        _send(
            recipient,
            subject=f"{initiator_name} wants to connect with you",
            template='base/emails/connection_request_created.html',
            context=base_context,
        )
    elif event in ('accepted', 'declined'):
        _send(
            initiator,
            subject=(
                f"{recipient_name} accepted your connection request"
                if event == 'accepted'
                else f"{recipient_name} declined your connection request"
            ),
            template='base/emails/connection_request_decision.html',
            context={**base_context, 'event': event},
        )
    else:
        logger.warning("Unknown connection event: %r", event)


def notify_forum_meeting_event(meeting, event):
    """Email notifications for the ForumMeeting lifecycle.

    proposed → email the invitee; confirmed/declined → email the proposer.
    """
    proposer = meeting.proposed_by
    invitee = meeting.invitee
    proposer_name = _display_name(proposer)
    invitee_name = _display_name(invitee)
    base_context = {
        'meeting': meeting,
        'window': meeting.window,
        'forum': meeting.forum,
        'proposer_name': proposer_name,
        'invitee_name': invitee_name,
    }

    if event == 'proposed':
        _send(
            invitee,
            subject=f"{proposer_name} proposed a meeting time",
            template='base/emails/forum_meeting_proposed.html',
            context=base_context,
        )
    elif event in ('confirmed', 'declined'):
        _send(
            proposer,
            subject=(
                f"{invitee_name} confirmed your meeting time"
                if event == 'confirmed'
                else f"{invitee_name} declined your meeting time"
            ),
            template='base/emails/forum_meeting_decision.html',
            context={**base_context, 'event': event},
        )
    else:
        logger.warning("Unknown forum meeting event: %r", event)


def notify_meeting_event(meeting_request, event):
    requester_name = _display_name(meeting_request.requester)
    requestee_name = _display_name(meeting_request.requestee)
    base_context = {
        'meeting_request': meeting_request,
        'requester_name': requester_name,
        'requestee_name': requestee_name,
    }

    if event == 'created':
        _send(
            meeting_request.requestee,
            subject=f"{requester_name} wants to connect with you",
            template='base/emails/meeting_request_created.html',
            context=base_context,
        )
    elif event in ('accepted', 'rejected'):
        _send(
            meeting_request.requester,
            subject=(
                f"{requestee_name} accepted your meeting request"
                if event == 'accepted'
                else f"{requestee_name} declined your meeting request"
            ),
            template='base/emails/meeting_request_decision.html',
            context={**base_context, 'event': event},
        )
    else:
        logger.warning("Unknown meeting event: %r", event)


def notify_meeting_calendar_invite(meeting):
    """Email both participants of a confirmed ForumMeeting a calendar invite
    (.ics attachment) for their agreed time."""
    roaster = meeting.conversation.roaster
    farmer = meeting.conversation.farmer
    ics = _build_ics(meeting)
    subject = f"Calendar invite: your {meeting.forum.title} meeting"

    for user in (roaster, farmer):
        if not user.email:
            logger.warning(
                "Skipping calendar invite for user %s: no email", user.pk
            )
            continue
        try:
            context = {
                'meeting': meeting,
                'window': meeting.window,
                'forum': meeting.forum,
                'recipient_name': _display_name(user),
                'other_name': _display_name(
                    meeting.conversation.other_participant(user)
                ),
            }
            html_body = render_to_string(
                'base/emails/meeting_calendar_invite.html', context
            )
            text_body = strip_tags(html_body)
            message = EmailMultiAlternatives(
                subject=subject,
                body=text_body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user.email],
            )
            message.attach_alternative(html_body, "text/html")
            message.attach('meeting.ics', ics, 'text/calendar; method=REQUEST')
            message.send()
        except Exception:
            logger.exception(
                "Failed to send calendar invite to %s", user.email
            )
