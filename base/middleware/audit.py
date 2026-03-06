from django.urls import resolve
from django.utils.deprecation import MiddlewareMixin

from base.models import AuditAction, AuditLog

URL_ACTIONS = {
    'update_profile': AuditAction.UPDATE_PROFILE,
    'update_header_image': AuditAction.UPDATE_HEADER,
    'upload_photo': AuditAction.UPLOAD_PHOTO,
    'delete_farmer_photo': AuditAction.DELETE_PHOTO,
    'delete_roaster_photo': AuditAction.DELETE_PHOTO,
    'edit_farmer_details': AuditAction.UPDATE_PROFILE,
    'add_roaster_photo': AuditAction.UPLOAD_PHOTO,
    'add_story': AuditAction.ADD_STORY,
    'update_story': AuditAction.UPDATE_STORY,
    'publish_profile': AuditAction.PUBLISH_PROFILE,
    'request_meeting': AuditAction.REQUEST_MEETING,
    'manage_meeting_request': AuditAction.MANAGE_MEETING,
    'signup': AuditAction.CREATE_ACCOUNT,
    'farmer_details': AuditAction.COMPLETE_DETAILS,
    'roaster_details': AuditAction.COMPLETE_DETAILS,
    'admin_farmer_detail': AuditAction.UPDATE_PROFILE,
    'admin_roaster_detail': AuditAction.UPDATE_PROFILE,
    'admin_create': AuditAction.CREATE_ADMIN,
    'admin_toggle': AuditAction.TOGGLE_ADMIN,
}


class AuditMiddleware(MiddlewareMixin):

    def process_response(self, request, response):
        if request.method != 'POST':
            return response
        if response.status_code != 302:
            return response
        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return response

        try:
            url_name = resolve(request.path_info).url_name
        except Exception:
            return response

        action = URL_ACTIONS.get(url_name)
        if action:
            AuditLog.objects.create(user=request.user, action=action)

        return response
