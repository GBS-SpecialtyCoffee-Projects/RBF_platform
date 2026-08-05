"""Recording of farmer profile changes for the admin history page.

Capture happens through ``ModelForm.changed_data`` at each call site rather
than through model signals: signals also fire for fixtures and data
migrations, miss ``.update()`` and bulk writes, and hide the behaviour from
the view that triggers it.

Recording must never cost a farmer their edit, so :func:`record_form_change`
and :func:`record_photo_change` swallow and log any error instead of
propagating it.
"""

import logging
from typing import Optional

from django.db import transaction
from django.db.models import Model
from django.db.models.query import QuerySet

from base.models import ProfileChange, User

logger = logging.getLogger(__name__)

# Longest value stored per field; longer values are cut and flagged.
MAX_VALUE_LENGTH = 10_000

# Profile fields worth keeping history for. Deliberately an allowlist so a
# future field is never captured by accident.
TRACKED_FIELDS = frozenset({
    'firstname', 'middlename', 'lastname', 'farm_name',
    'country', 'state', 'city',
    'farm_size', 'farm_size_unit', 'annual_production', 'annual_production_unit',
    'cultivars', 'harvest_season', 'cup_scores_received', 'source_of_cup_scores',
    'quality_report_link', 'processing_method', 'processing_description',
    'main_roles', 'affiliation', 'bio', 'preferred_communication_method',
    'is_member_organization', 'member_organization_name', 'is_profile_published',
    'phone_number', 'country_code',
    # Story fields.
    'story_text', 'language',
})

# Fields whose content is never stored — only whether they changed.
FILE_FIELDS = frozenset({'profile_picture', 'header_image', 'photo'})


def _format(value):
    """Render a field value as something JSON-serialisable and readable."""
    if value is None or value == '':
        return ''
    if isinstance(value, QuerySet):
        return sorted(str(item) for item in value)
    if isinstance(value, (list, tuple, set)):
        return sorted(str(item) for item in value)
    if isinstance(value, Model):
        return str(value)
    if isinstance(value, bool):
        return value
    text = str(value)
    if len(text) > MAX_VALUE_LENGTH:
        return text[:MAX_VALUE_LENGTH] + '…[truncated]'
    return text


def _diff(form):
    """Build ``{field: {"old": ..., "new": ...}}`` from a bound ModelForm."""
    changes = {}
    for field in form.changed_data:
        if field in FILE_FIELDS:
            changes[field] = {'old': None, 'new': 'changed'}
        elif field in TRACKED_FIELDS:
            changes[field] = {
                'old': _format(form.initial.get(field)),
                'new': _format(form.cleaned_data.get(field)),
            }
    return changes


def record_form_change(
    form,
    *,
    user: User,
    source: str,
    changed_by: Optional[User] = None,
) -> None:
    """Record the fields a bound ModelForm changed. No-ops when nothing did.

    Call after ``save()`` (and after ``save_m2m()`` where the view uses
    ``commit=False``) so many-to-many values reflect what was stored.
    """
    try:
        changes = _diff(form)
        if not changes:
            return
        with transaction.atomic():
            ProfileChange.objects.create(
                user=user,
                changed_by=changed_by or user,
                source=source,
                changes=changes,
            )
    except Exception:
        logger.exception("Failed to record profile change for user %s", user.pk)


def record_field_change(
    user: User,
    *,
    source: str,
    field: str,
    old,
    new,
    changed_by: Optional[User] = None,
) -> None:
    """Record a single field edited outside a ModelForm (e.g. admin views)."""
    try:
        if old == new:
            return
        with transaction.atomic():
            ProfileChange.objects.create(
                user=user,
                changed_by=changed_by or user,
                source=source,
                changes={field: {'old': _format(old), 'new': _format(new)}},
            )
    except Exception:
        logger.exception("Failed to record field change for user %s", user.pk)


def record_photo_change(
    user: User,
    *,
    old_count: int,
    new_count: int,
    changed_by: Optional[User] = None,
) -> None:
    """Record a photo count moving up or down. Files are never stored."""
    try:
        if old_count == new_count:
            return
        with transaction.atomic():
            ProfileChange.objects.create(
                user=user,
                changed_by=changed_by or user,
                source='photo',
                changes={'photos': {'old': old_count, 'new': new_count}},
            )
    except Exception:
        logger.exception("Failed to record photo change for user %s", user.pk)
