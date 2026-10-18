from django.db import models


class Visit(models.Model):
    """One write per request to /api/write and to the home page."""

    path = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)


class Job(models.Model):
    """A background job: queued by the web, finished by the Celery worker."""

    queued_at = models.DateTimeField(auto_now_add=True)
    done_at = models.DateTimeField(null=True)
    worker = models.CharField(max_length=64, blank=True)
