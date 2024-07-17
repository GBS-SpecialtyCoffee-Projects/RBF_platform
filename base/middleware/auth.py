from django.shortcuts import redirect, resolve_url
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings


class AuthMiddleware(MiddlewareMixin):

    def process_request(self, request):
        # Exclude certain paths from requiring authentication
        excluded_paths = [
            resolve_url('onboarding'),
            resolve_url('farmer_dashboard'),
            resolve_url('signin'),
            resolve_url('signup'),
            resolve_url('reset_password'),
            resolve_url('email_verify'),
            resolve_url('verify_email'),
            settings.STATIC_URL,  # Exclude static files
            settings.MEDIA_URL,  # Exclude media files if you serve them in development
        ]

        # Add other paths you want to exclude
        for path in excluded_paths:
            if request.path.startswith(path):
                return
        if request.path == resolve_url('landing_page'):
            return
        # Check if the user is authenticated
        if not request.user.is_authenticated:
            return redirect('signin')
