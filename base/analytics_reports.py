"""Interaction analytics reporting.

Read-only aggregation functions that answer the platform's core questions about
how roasters and farmers interact. Each returns dashboard-ready primitives
(dicts / lists) and accepts an optional ``start`` / ``end`` datetime window.

Authoritative tables (``Connection``, ``Message``, ``ForumMeeting``) are used
where they carry full history; :class:`~base.models.InteractionEvent` supplies
the view/engagement signals that aren't recorded anywhere else. View-based
stages therefore only reflect activity from when capture went live.
"""
from collections import Counter

from django.db.models import Count, Q
from django.db.models.functions import TruncDate

from base.models import (
    Connection, Farmer, ForumMeeting, InteractionEvent, Message,
)


# --- helpers ---------------------------------------------------------------
def _apply_range(qs, field, start, end):
    if start is not None:
        qs = qs.filter(**{f'{field}__gte': start})
    if end is not None:
        qs = qs.filter(**{f'{field}__lte': end})
    return qs


def _rate(numerator, denominator):
    """Percentage (0–100, rounded) guarding against division by zero."""
    if not denominator:
        return 0.0
    return round(100.0 * numerator / denominator, 1)


def _avg(numerator, denominator):
    if not denominator:
        return 0.0
    return round(numerator / denominator, 2)


def _events(event_type, start, end):
    return _apply_range(
        InteractionEvent.objects.filter(event_type=event_type),
        'created_at', start, end,
    )


# --- 1. funnel / conversion -----------------------------------------------
def funnel(start=None, end=None):
    """Stage counts and step-to-step conversion for the engagement funnel.

    Stages mix distinct *unordered pairs* (views/messages) with authoritative
    relationship rows so each stage is a meaningful "how many got this far".
    """
    def distinct_pairs(event_type):
        rows = _events(event_type, start, end).values_list('actor_id', 'target_user_id')
        return len({frozenset(r) for r in rows if all(r)})

    profile_views = distinct_pairs(InteractionEvent.EventType.VIEW_PROFILE)
    story_views = distinct_pairs(InteractionEvent.EventType.VIEW_STORY)

    msg_pairs = _apply_range(Message.objects.all(), 'created_at', start, end)\
        .values('conversation_id').distinct().count()

    conns = _apply_range(Connection.objects.all(), 'created_at', start, end)
    requests = conns.count()
    active = conns.filter(status=Connection.ACTIVE).count()

    meetings = _apply_range(ForumMeeting.objects.all(), 'created_at', start, end)
    proposed = meetings.values('conversation_id').distinct().count()
    confirmed = meetings.filter(status=ForumMeeting.CONFIRMED)\
        .values('conversation_id').distinct().count()

    stages = [
        {'key': 'profile_views', 'label': 'Profiles viewed', 'count': profile_views},
        {'key': 'story_views', 'label': 'Stories viewed', 'count': story_views},
        {'key': 'messages', 'label': 'Conversations started', 'count': msg_pairs},
        {'key': 'requests', 'label': 'Connection requests', 'count': requests},
        {'key': 'active', 'label': 'Active connections', 'count': active},
        {'key': 'meetings_proposed', 'label': 'Meetings proposed', 'count': proposed},
        {'key': 'meetings_confirmed', 'label': 'Meetings confirmed', 'count': confirmed},
    ]
    for i, stage in enumerate(stages):
        prev = stages[i - 1]['count'] if i else stage['count']
        stage['step_conversion'] = _rate(stage['count'], prev) if i else 100.0
    return {'stages': stages}


# --- 2. story impact -------------------------------------------------------
def story_impact(start=None, end=None):
    """Compare farmers who have stories against those who don't, on the
    engagement they receive. Answers: do stories drive roaster interest?"""
    with_ids = set(
        Farmer.objects.filter(farmer_stories__isnull=False)
        .values_list('user_id', flat=True).distinct()
    )
    all_ids = set(Farmer.objects.values_list('user_id', flat=True))
    without_ids = all_ids - with_ids

    def group(ids):
        ids = list(ids)
        n = len(ids)
        if not ids:
            return {'farmers': 0, 'profile_views': 0, 'requests_received': 0,
                    'active_connections': 0, 'avg_views_per_farmer': 0.0,
                    'avg_active_per_farmer': 0.0, 'accept_rate': 0.0}

        views = _events(InteractionEvent.EventType.VIEW_PROFILE, start, end)\
            .filter(target_user_id__in=ids).count()

        involving = _apply_range(Connection.objects.all(), 'created_at', start, end)\
            .filter(Q(user_a_id__in=ids) | Q(user_b_id__in=ids))
        # Requests the farmer *received* (roaster initiated, so initiator not a farmer).
        received = involving.exclude(initiator_id__in=ids).count()
        active = involving.filter(status=Connection.ACTIVE).count()

        return {
            'farmers': n,
            'profile_views': views,
            'requests_received': received,
            'active_connections': active,
            'avg_views_per_farmer': _avg(views, n),
            'avg_active_per_farmer': _avg(active, n),
            'accept_rate': _rate(active, received),
        }

    return {'with_stories': group(with_ids), 'without_stories': group(without_ids)}


# --- 3. match quality ------------------------------------------------------
def _profile(user, attr):
    prof = getattr(user, attr, None)
    return prof


def match_quality(start=None, end=None):
    """Which segments produce successful (active) connections. Buckets active
    connections by the farmer's and roaster's country, and records who tends to
    initiate (roaster-led vs farmer-led)."""
    conns = _apply_range(
        Connection.objects.filter(status=Connection.ACTIVE),
        'created_at', start, end,
    ).select_related(
        'user_a__farmer_profile', 'user_b__farmer_profile',
        'user_a__roaster_profile', 'user_b__roaster_profile',
    )

    by_farmer_country = Counter()
    by_roaster_country = Counter()
    initiation = Counter()  # 'roaster' / 'farmer'

    for c in conns:
        farmer = _profile(c.user_a, 'farmer_profile') or _profile(c.user_b, 'farmer_profile')
        roaster = _profile(c.user_a, 'roaster_profile') or _profile(c.user_b, 'roaster_profile')
        if farmer:
            by_farmer_country[farmer.country or 'Unknown'] += 1
        if roaster:
            by_roaster_country[roaster.country or 'Unknown'] += 1
        initiation[getattr(c.initiator, 'group', None) or 'unknown'] += 1

    return {
        'active_total': sum(initiation.values()),
        'by_farmer_country': by_farmer_country.most_common(),
        'by_roaster_country': by_roaster_country.most_common(),
        'initiation': dict(initiation),
    }


# --- 4. engagement volume --------------------------------------------------
def engagement_volume(start=None, end=None):
    """Overall activity: event totals by type, a daily time series, and
    authoritative relationship/message counts."""
    events = _apply_range(InteractionEvent.objects.all(), 'created_at', start, end)

    by_type = {
        row['event_type']: row['n']
        for row in events.values('event_type').annotate(n=Count('id'))
    }
    timeseries = list(
        events.annotate(day=TruncDate('created_at'))
        .values('day').annotate(n=Count('id')).order_by('day')
    )

    conns = _apply_range(Connection.objects.all(), 'created_at', start, end)
    return {
        'events_by_type': by_type,
        'events_total': sum(by_type.values()),
        'timeseries': timeseries,
        'messages': _apply_range(Message.objects.all(), 'created_at', start, end).count(),
        'connection_requests': conns.count(),
        'active_connections': conns.filter(status=Connection.ACTIVE).count(),
        'meetings_confirmed': _apply_range(
            ForumMeeting.objects.filter(status=ForumMeeting.CONFIRMED),
            'created_at', start, end,
        ).count(),
    }
