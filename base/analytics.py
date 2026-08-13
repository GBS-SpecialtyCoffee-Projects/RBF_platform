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
