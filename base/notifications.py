import logging
from datetime import timezone as dt_timezone

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone, translation
from django.utils.html import strip_tags
from django.utils.translation import gettext

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


def _user_language(user):
    """The locale to render this user's email in, falling back to the default."""
    return getattr(user, 'preferred_language', None) or settings.LANGUAGE_CODE


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


def notify_signup(user):
    """Welcome a newly registered user and point them at their next step."""
    with translation.override(_user_language(user)):
        _send(
            user,
            subject=gettext("Welcome to Coffee Circuit"),
            template='base/emails/welcome.html',
            context={'recipient_name': _display_name(user), 'group': user.group},
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
        with translation.override(_user_language(recipient)):
            _send(
                recipient,
                subject=gettext("%(name)s wants to connect with you") % {
                    'name': initiator_name,
                },
                template='base/emails/connection_request_created.html',
                context=base_context,
            )
    elif event in ('accepted', 'declined'):
        with translation.override(_user_language(initiator)):
            _send(
                initiator,
                subject=(
                    gettext("%(name)s accepted your connection request")
                    if event == 'accepted'
                    else gettext("%(name)s declined your connection request")
                ) % {'name': recipient_name},
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
        with translation.override(_user_language(invitee)):
            _send(
                invitee,
                # The forum is named in the subject because the Spanish copy
                # requires it, and gettext will not accept a translation that
                # introduces a placeholder the source string lacks.
                subject=gettext("%(name)s proposed a meeting time for %(forum)s") % {
                    'name': proposer_name, 'forum': meeting.forum.title,
                },
                template='base/emails/forum_meeting_proposed.html',
                context={
                    **base_context,
                    'invitee_needs_signup': meeting.invitee_needs_signup(),
                },
            )
    elif event in ('confirmed', 'declined'):
        with translation.override(_user_language(proposer)):
            _send(
                proposer,
                subject=(
                    gettext("%(name)s confirmed your meeting time for %(forum)s")
                    if event == 'confirmed'
                    else gettext("%(name)s declined your meeting time for %(forum)s")
                ) % {'name': invitee_name, 'forum': meeting.forum.title},
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
        with translation.override(_user_language(meeting_request.requestee)):
            _send(
                meeting_request.requestee,
                subject=gettext("%(name)s wants to connect with you") % {
                    'name': requester_name,
                },
                template='base/emails/meeting_request_created.html',
                context=base_context,
            )
    elif event in ('accepted', 'rejected'):
        with translation.override(_user_language(meeting_request.requester)):
            _send(
                meeting_request.requester,
                subject=(
                    gettext("%(name)s accepted your meeting request")
                    if event == 'accepted'
                    else gettext("%(name)s declined your meeting request")
                ) % {'name': requestee_name},
                template='base/emails/meeting_request_decision.html',
                context={**base_context, 'event': event},
            )
    else:
        logger.warning("Unknown meeting event: %r", event)


def notify_admin_message(admin_email):
    """Send an admin-composed message to a single user.

    Records the outcome on the ``AdminEmail`` row and returns whether the
    send succeeded, so the caller can report a real result to the admin.
    """
    recipient = admin_email.recipient
    if not recipient.email:
        admin_email.error = 'Recipient has no email address.'
        admin_email.save(update_fields=['delivered', 'error'])
        logger.warning("Skipping admin email for user %s: no email", recipient.pk)
        return False

    try:
        # The greeting and sign-off follow the recipient's language, but the
        # subject and body an admin typed are passed through verbatim -- we do
        # not machine-translate a human's message.
        with translation.override(_user_language(recipient)):
            html_body = render_to_string(
                'base/emails/admin_message.html',
                {
                    'admin_email': admin_email,
                    'recipient_name': _display_name(recipient),
                },
            )
        text_body = strip_tags(html_body)
        message = EmailMultiAlternatives(
            subject=admin_email.subject,
            body=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[recipient.email],
            # Replies reach the admin who wrote it, not the no-reply address.
            reply_to=(
                [admin_email.sent_by.email]
                if admin_email.sent_by and admin_email.sent_by.email
                else None
            ),
        )
        message.attach_alternative(html_body, "text/html")
        message.send()
    except Exception as exc:
        admin_email.error = str(exc)
        admin_email.save(update_fields=['delivered', 'error'])
        logger.exception("Failed to send admin email to %s", recipient.email)
        return False

    admin_email.delivered = True
    admin_email.save(update_fields=['delivered', 'error'])
    return True


def notify_meeting_calendar_invite(meeting):
    """Email both participants of a confirmed ForumMeeting a calendar invite
    (.ics attachment) for their agreed time."""
    roaster = meeting.conversation.roaster
    farmer = meeting.conversation.farmer
    # One shared .ics: both attendees must see the same calendar event, so it
    # stays in the default language rather than being rendered per recipient.
    ics = _build_ics(meeting)

    for user in (roaster, farmer):
        if not user.email:
            logger.warning(
                "Skipping calendar invite for user %s: no email", user.pk
            )
            continue
        try:
            # The two participants may have different preferred languages.
            with translation.override(_user_language(user)):
                subject = gettext(
                    "Calendar invite: your %(forum)s meeting"
                ) % {'forum': meeting.forum.title}
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
