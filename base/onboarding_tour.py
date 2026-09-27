"""Step content for the dashboard onboarding tour (rendered by Driver.js).

Each step targets an element marked with a matching ``data-tour`` attribute
in ``navbar_app.html`` or the farmer/roaster dashboard templates.
"""


def _step(anchor: str, title: str, description: str) -> dict:
    return {
        'element': f'[data-tour="{anchor}"]',
        'popover': {'title': title, 'description': description},
    }


def _intro(counterpart: str) -> dict:
    return {
        'popover': {
            'title': 'Welcome to Coffee Circuit',
            'description': (
                f'This quick tour shows you around. Coffee Circuit helps you '
                f'meet {counterpart}, build relationships and trade directly. '
                f'You can replay it any time with the "Take the tour" button.'
            ),
        },
    }


FARMER_ORIENTATION = _step(
    'onboarding', 'Onboarding tasks',
    'Short tasks and videos to finish before your profile is published. '
    'The red number shows how many are left.',
)
FARMER_BROWSE = _step(
    'browse', 'Find roasters',
    'Browse roasters looking for coffee and send them a connection request.',
)
ROASTER_BROWSE = _step(
    'browse', 'Find farmers',
    'Browse producers and their coffee, then send a connection request to '
    'the ones you would like to work with.',
)
BROWSE_LOCKED = {
    'popover': {
        'title': 'Browsing unlocks soon',
        'description': (
            'Once your profile is complete and published, a new menu item '
            'appears here so you can browse and contact other members.'
        ),
    },
}
CONNECTIONS = _step(
    'connections', 'Connections',
    'Requests you have sent and received. Accept a request to start '
    'chatting. The red number shows requests waiting for your answer.',
)
MESSAGES = _step(
    'messages', 'Messages',
    'Chat with your connections and propose a meeting time from the chat.',
)
TRANSLATE = _step(
    'translate', 'Language',
    'Pick a language here to translate the whole site.',
)
PROFILE = _step(
    'profile', 'Your profile',
    'Edit your name, photo, phone number and email language here.',
)
DASHBOARD_CONNECTIONS = _step(
    'dashboard-connections', 'Latest connections',
    'New connection requests appear here so you can accept or decline them '
    'right away.',
)
PHOTOS = _step(
    'photos', 'Photos',
    'Add up to 6 photos. Profiles with photos get more attention.',
)

FARMER_STEPS = [
    PROFILE,
    _step(
        'story', 'Your story',
        'Tell roasters about your farm and family. You can write it in more '
        'than one language.',
    ),
    _step(
        'details', 'Farm details',
        'Varieties, harvest seasons, processing methods and cup scores. '
        'Roasters use these to find coffee that fits them.',
    ),
    PHOTOS,
    DASHBOARD_CONNECTIONS,
]

ROASTER_STEPS = [
    PROFILE,
    _step(
        'details', 'Company profile',
        'Describe your company and what you look for when you source coffee, '
        'so farmers know what you buy.',
    ),
    DASHBOARD_CONNECTIONS,
    PHOTOS,
]


def steps_for(user) -> list[dict]:
    """The tour steps for ``user``: navbar items first, then the dashboard."""
    is_farmer = user.group == 'farmer'
    if user.is_discoverable:
        browse = FARMER_BROWSE if is_farmer else ROASTER_BROWSE
    else:
        browse = BROWSE_LOCKED
    navbar = [browse, CONNECTIONS, MESSAGES, TRANSLATE]
    if is_farmer:
        return [_intro('roasters'), FARMER_ORIENTATION, *navbar, *FARMER_STEPS]
    return [_intro('farmers'), *navbar, *ROASTER_STEPS]
