import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)


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
            from_email=settings.EMAIL_FROM,
            to=[user.email],
        )
        message.attach_alternative(html_body, "text/html")
        message.send()
    except Exception:
        logger.exception(
            "Failed to send notification to %s (subject=%r)", user.email, subject
        )


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
