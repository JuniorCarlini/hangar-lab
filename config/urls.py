from django.urls import path

from lab import domains, views

urlpatterns = [
    path("", views.home),
    path("healthz", views.healthz),
    path("api/write", views.write),
    path("api/cache", views.cache),
    path("api/cpu", views.cpu),
    path("api/job", views.job),
    path("api/stats", views.stats),
    path(".well-known/hangar/domain-check", domains.domain_check),
]
