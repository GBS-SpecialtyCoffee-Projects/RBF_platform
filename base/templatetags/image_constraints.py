from django import template
from django.utils.html import format_html

from base.validators import IMAGE_ACCEPT, MAX_IMAGE_SIZE, image_help_text

register = template.Library()


@register.inclusion_tag('base/partials/image_upload_help.html')
def image_upload_help(role=''):
    """Render the upload rules for an image role next to its file input.

    Roles are the keys of ``RECOMMENDED_DIMENSIONS``: 'profile', 'header',
    'gallery', 'cover'. An unknown or omitted role prints format and size
    only.
    """
    return {'help_text': image_help_text(role)}


@register.simple_tag
def image_file_attrs():
    """Attributes for a hand-written image file input.

    Mirrors ``IMAGE_INPUT_ATTRS``, which form-rendered widgets already carry.
    """
    return format_html(
        'accept="{}" data-max-size="{}"', IMAGE_ACCEPT, MAX_IMAGE_SIZE,
    )
