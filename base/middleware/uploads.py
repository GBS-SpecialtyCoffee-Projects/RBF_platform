"""Turn an oversized upload into a readable message instead of an error page."""

from django.contrib import messages
from django.core.exceptions import RequestDataTooBig, TooManyFieldsSent
from django.http import HttpResponseRedirect
from django.template.defaultfilters import filesizeformat
from django.utils.deprecation import MiddlewareMixin
from django.utils.http import url_has_allowed_host_and_scheme

from base.validators import MAX_IMAGE_SIZE, MAX_IMAGE_SIZE_MB

# Headroom for the rest of a multipart body - other fields, boundaries - on
# top of the largest single image we accept.
REQUEST_BODY_HEADROOM = 1024 * 1024
MAX_REQUEST_BODY_SIZE = MAX_IMAGE_SIZE + REQUEST_BODY_HEADROOM


class OversizedUploadMiddleware(MiddlewareMixin):
    """Reject too-large uploads before the request body is parsed.

    Per-image limits are enforced by ``validate_uploaded_image``, but that
    runs only once the whole body has been streamed in and parsed. A big
    enough upload never gets that far: it exhausts the worker or trips
    Django's own body limits, and the user is shown the 500 page with no clue
    what went wrong. Checking Content-Length up front turns that into the same
    message they would have got from form validation.
    """

    def process_request(self, request):
        if request.method != 'POST':
            return None
        if not request.content_type.startswith('multipart/form-data'):
            return None
        try:
            content_length = int(request.META.get('CONTENT_LENGTH') or 0)
        except (TypeError, ValueError):
            return None
        if content_length <= MAX_REQUEST_BODY_SIZE:
            return None
        return self._reject(request, content_length)

    def process_exception(self, request, exception):
        # Raised lazily, the first time a view touches request.POST, so it
        # cannot be caught in process_request.
        if isinstance(exception, (RequestDataTooBig, TooManyFieldsSent)):
            return self._reject(request)
        return None

    def _reject(self, request, content_length=None):
        size = f'That upload is {filesizeformat(content_length)}. ' if content_length else ''
        messages.error(
            request,
            f'{size}Images must be {MAX_IMAGE_SIZE_MB} MB or smaller. '
            'Please resize your image and try again.',
        )
        return HttpResponseRedirect(self._back(request))

    @staticmethod
    def _back(request):
        referer = request.META.get('HTTP_REFERER', '')
        if referer and url_has_allowed_host_and_scheme(
            referer,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            return referer
        return '/'
