import zlib

from django import template

register = template.Library()

# Circle fills for the monogram. Each is dark enough to carry white text, and
# they stay in the site's earth-tone range so a list of them still reads calmly.
AVATAR_COLORS = (
    '#4e6e5d', '#8c5e3c', '#2f6f8f', '#a2673f', '#6b5b95', '#3f7d6e',
)

# Used when there is no name to build a monogram from.
AVATAR_NEUTRAL = '#8a8f98'


def _name(profile):
    """The profile's display name, or '' when it has not been filled in."""
    parts = (getattr(profile, 'firstname', ''), getattr(profile, 'lastname', ''))
    return ' '.join(part for part in parts if part).strip()


@register.inclusion_tag('base/partials/avatar.html')
def avatar(profile, size=90, border=False, style=''):
    """Render a profile's picture, or a stand-in when it has none.

    ``profile`` is a Farmer or a Roaster - both carry ``firstname``,
    ``lastname`` and ``profile_picture``, which is all this needs.
    """
    name = _name(profile)
    initials = ''.join(word[0].upper() for word in name.split()[:2])

    # A profile with no name yet still needs a stable colour, so fall back to
    # the account email. crc32 rather than hash(): hash() is salted per
    # process, which would repaint everyone's avatar on each restart.
    identity = name or getattr(getattr(profile, 'user', None), 'email', '') or ''
    color = (
        AVATAR_COLORS[zlib.crc32(identity.encode()) % len(AVATAR_COLORS)]
        if initials else AVATAR_NEUTRAL
    )

    return {
        'image': getattr(profile, 'profile_picture', None),
        'initials': initials,
        'color': color,
        'size': size,
        'font_size': round(size * 0.38),
        'border': border,
        'style': style,
    }
