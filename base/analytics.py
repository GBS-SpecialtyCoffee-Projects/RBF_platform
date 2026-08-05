"""Lightweight helper for recording raw interaction events.

Logging must never break a user request, so :func:`log_event` swallows and
logs any error instead of propagating it.
"""

import logging
from typing import Optional

from django.db import transaction
from django.http import HttpRequest

from base.models import InteractionEvent, User

logger = logging.getLogger(__name__)


def log_event(
    event_type: str,
    *,
    request: Optional[HttpRequest] = None,
    user: Optional[User] = None,
    target_user: Optional[User] = None,
    path: str = "",
    **metadata,
) -> None:
    """Record a single raw interaction event.

    ``user``, ``path`` and ``session_key`` are derived from ``request`` when
    given, but explicit arguments take precedence (e.g. websocket handlers
    that have no request). Extra keyword args are stored in ``metadata``.
    """
    try:
        session_key = ""
        if request is not None:
            if user is None and request.user.is_authenticated:
                user = request.user
            if not path:
                path = request.path
            if request.session.session_key:
                session_key = request.session.session_key

        # Use a savepoint so a logging failure never poisons the caller's
        # transaction.
        with transaction.atomic():
            InteractionEvent.objects.create(
                event_type=event_type,
                user=user if user and user.is_authenticated else None,
                target_user=target_user,
                path=path[:255],
                metadata=metadata,
                session_key=session_key,
            )
    except Exception:
        logger.exception("Failed to log interaction event: %s", event_type)
"""Interaction analytics capture.

``record_event`` and ``record_view`` write :class:`~base.models.InteractionEvent`
rows without ever breaking the caller: analytics must not take down a
user-facing action. Every write is wrapped defensively and only logs on failure.
"""
import logging

from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

from base.models import InteractionEvent

logger = logging.getLogger(__name__)


def _role(user):
    """Return 'farmer' / 'roaster' for a user, or None."""
    return getattr(user, 'group', None)


def _clean_actor(actor):
    """Only store real, authenticated users as the actor."""
    return actor if getattr(actor, 'is_authenticated', False) else None


def record_event(actor, event_type, *, target=None, target_user=None, **metadata):
    """Record a single interaction event.

    actor:       the acting ``User`` (anonymous users are stored as null).
    event_type:  an ``InteractionEvent.EventType`` value.
    target:      optional model instance the event points at (Story, Connection,
                 Message...). Stored via a generic relation.
    target_user: the ``User`` the action is directed at; inferred from the
                 target's ``user`` / ``recipient`` attribute when omitted.
    metadata:    extra context stored as JSON. Actor/target roles are added
                 automatically.
    """
    try:
        if target_user is None and target is not None:
            target_user = (
                getattr(target, 'user', None) or getattr(target, 'recipient', None)
            )

        meta = {'actor_role': _role(actor)}
        if target_user is not None:
            meta['target_role'] = _role(target_user)
        meta.update(metadata)

        kwargs = {
            'actor': _clean_actor(actor),
            'target_user': target_user,
            'event_type': event_type,
            'metadata': meta,
        }
        if target is not None:
            kwargs['content_type'] = ContentType.objects.get_for_model(target.__class__)
            kwargs['object_id'] = target.pk

        return InteractionEvent.objects.create(**kwargs)
    except Exception:
        logger.exception("Failed to record interaction event %s", event_type)
        return None


def record_view(actor, event_type, target_user, *, target=None, **metadata):
    """Record a view event at most once per actor/target/type/day.

    Excludes self-views and deduplicates high-volume page loads so the funnel
    isn't dominated by repeat visits.
    """
    try:
        actor = _clean_actor(actor)
        if actor is None:
            return None
        if target_user is not None and actor.id == target_user.id:
            return None  # don't count viewing your own profile

        already = InteractionEvent.objects.filter(
            actor=actor,
            target_user=target_user,
            event_type=event_type,
            created_at__date=timezone.now().date(),
        ).exists()
        if already:
            return None

        return record_event(
            actor, event_type, target=target, target_user=target_user, **metadata
        )
    except Exception:
        logger.exception("Failed to record view event %s", event_type)
        return None
