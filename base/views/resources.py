from django.shortcuts import render, get_object_or_404

from base.models import Resource


def resource_list(request):
    resources = Resource.objects.filter(is_published=True)
    return render(request, "base/resources/resource_list.html", {
        "resources": resources,
    })


def resource_detail(request, slug: str):
    resource = get_object_or_404(Resource, slug=slug, is_published=True)
    return render(request, "base/resources/resource_detail.html", {
        "resource": resource,
    })
