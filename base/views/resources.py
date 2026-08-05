from django.shortcuts import render, get_object_or_404

from base.models import Resource, InteractionEventType
from base.analytics import log_event


def resource_list(request):
    resources = Resource.objects.filter(is_published=True)
    return render(request, "base/resources/resource_list.html", {
        "resources": resources,
    })


def resource_detail(request, slug: str):
    resource = get_object_or_404(Resource, slug=slug, is_published=True)
    log_event(
        InteractionEventType.RESOURCE_VIEW, request=request,
        resource_id=resource.id, resource_slug=resource.slug,
    )
    return render(request, "base/resources/resource_detail.html", {
        "resource": resource,
    })
