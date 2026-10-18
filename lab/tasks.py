import socket
import time

from celery import shared_task
from django.utils import timezone

from .models import Job


@shared_task
def finish_job(job_id: int, work_ms: int = 100) -> None:
    """Pretend to work for a while, then mark the job done."""
    time.sleep(work_ms / 1000)
    Job.objects.filter(id=job_id).update(done_at=timezone.now(), worker=socket.gethostname())
