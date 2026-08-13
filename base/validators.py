"""Shared constraints for user-uploaded images.

Single source of truth for the image upload rules. The validator wired onto
every image model field and the help text rendered next to every upload
control both read from here, so what users are told always matches what is
actually enforced.
"""

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.template.defaultfilters import filesizeformat
from django.utils.translation import gettext_lazy as _
from PIL import Image

MAX_IMAGE_SIZE_MB = 5
MAX_IMAGE_SIZE = MAX_IMAGE_SIZE_MB * 1024 * 1024

# Pillow format names mapped to the labels users recognise.
ALLOWED_IMAGE_FORMATS = {'JPEG': 'JPG', 'PNG': 'PNG', 'WEBP': 'WebP'}

# Value for the `accept` attribute on file inputs.
IMAGE_ACCEPT = 'image/jpeg,image/png,image/webp'

# Reusable widget attrs for image file inputs. `data-max-size` lets the
# browser-side guard reject a file without matching the limit by hand.
IMAGE_INPUT_ATTRS = {
    'class': 'form-control',
    'accept': IMAGE_ACCEPT,
    'data-max-size': MAX_IMAGE_SIZE,
}

# Guidance only - not enforced, since cropping happens via CSS object-fit.
RECOMMENDED_DIMENSIONS = {
    'profile': '400 x 400 px (square)',
    'header': '1200 x 300 px (wide banner)',
    'gallery': '1200 px on the longest side',
    'cover': '1200 x 630 px',
}


def _is_new_upload(image):
    """True if this value is a file the user just submitted.

    Model validators run against whatever is on the instance, which by then is
    a ``FieldFile`` wrapping the upload rather than the ``UploadedFile``
    itself. An uncommitted ``FieldFile`` is one that has been assigned but not
    yet saved - i.e. a fresh upload.
    """
    if isinstance(image, UploadedFile):
        return True
    return getattr(image, '_committed', True) is False


def _detect_format(image):
    """Return the Pillow format name of an upload, or None if unreadable."""
    # forms.ImageField already opened the upload; reuse that result.
    opened = getattr(image, 'image', None)
    if getattr(opened, 'format', None):
        return opened.format
    try:
        image.seek(0)
        with Image.open(image) as probe:
            return probe.format
    except Exception:
        # Anything Pillow cannot read is "not an allowed format" as far as the
        # user is concerned - including decompression-bomb guards, which raise
        # their own exception type rather than OSError.
        return None
    finally:
        image.seek(0)


def validate_uploaded_image(image):
    """Reject uploads that are too large or not in an allowed format.

    Only freshly uploaded files are checked. Already-stored files are left
    alone, so re-saving a profile does not re-download every image from remote
    storage just to re-validate it.
    """
    if not _is_new_upload(image):
        return

    if image.size > MAX_IMAGE_SIZE:
        raise ValidationError(
            _(
                'That image is %(size)s, which is over the %(limit)s limit. '
                'Please resize it or upload a smaller image.'
            ),
            code='image_too_large',
            params={
                'size': filesizeformat(image.size),
                'limit': filesizeformat(MAX_IMAGE_SIZE),
            },
        )

    image_format = _detect_format(image)
    if image_format not in ALLOWED_IMAGE_FORMATS:
        raise ValidationError(
            _('Please upload a %(formats)s image.'),
            code='image_format_not_allowed',
            params={'formats': allowed_formats_label()},
        )


def allowed_formats_label():
    """e.g. "JPG, PNG or WebP" - for use in messages and help text."""
    labels = list(ALLOWED_IMAGE_FORMATS.values())
    return f'{", ".join(labels[:-1])} or {labels[-1]}'


def image_help_text(role=''):
    """Upload rules for an image role, as a single line of user-facing text."""
    parts = [f'{allowed_formats_label()} - max {MAX_IMAGE_SIZE_MB} MB']
    recommended = RECOMMENDED_DIMENSIONS.get(role)
    if recommended:
        parts.append(f'recommended {recommended}')
    return ' - '.join(parts)
