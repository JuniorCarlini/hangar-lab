"""Endpoints of the lab app: one page that shows every service working, and
small JSON routes to put load on each one (database, cache, CPU, worker)."""

import os
import socket
import time

import redis
from django.conf import settings
from django.db import connection
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render

from .models import Job, Visit
from .tasks import finish_job

_redis = redis.Redis.from_url(settings.REDIS_URL, socket_timeout=2, socket_connect_timeout=2)


def _check_db() -> tuple[bool, str]:
    try:
        with connection.cursor() as cur:
            cur.execute("select version()")
            return True, cur.fetchone()[0].split(" on ")[0]
    except Exception as e:  # noqa: BLE001 - shown on the page
        return False, str(e)[:200]


def _check_redis() -> tuple[bool, str]:
    try:
        info = _redis.info("server")
        return True, "Redis " + info.get("redis_version", "?")
    except Exception as e:  # noqa: BLE001
        return False, str(e)[:200]


def home(request):
    db_ok, db_info = _check_db()
    redis_ok, redis_info = _check_redis()
    visits = hits = None
    if db_ok:
        Visit.objects.create(path="/")
        visits = Visit.objects.count()
    if redis_ok:
        hits = _redis.incr("lab:home")
    jobs_done = Job.objects.exclude(done_at=None).count() if db_ok else None
    last = Job.objects.exclude(done_at=None).order_by("-done_at").first() if db_ok else None
    return render(
        request,
        "lab/home.html",
        {
            "db_ok": db_ok, "db_info": db_info, "redis_ok": redis_ok, "redis_info": redis_info,
            "visits": visits, "hits": hits, "jobs_done": jobs_done, "last_job": last,
            "host": socket.gethostname(), "version": os.environ.get("APP_VERSION", "dev"),
        },
    )


def healthz(request):
    db_ok, _ = _check_db()
    redis_ok, _ = _check_redis()
    ok = db_ok and redis_ok
    return HttpResponse("ok\n" if ok else "unhealthy\n", status=200 if ok else 503, content_type="text/plain")


def write(request):
    """Database load: one insert and one count."""
    Visit.objects.create(path="/api/write")
    return JsonResponse({"visits": Visit.objects.count()})


def cache(request):
    """Cache load: one write and one read in Redis."""
    n = _redis.incr("lab:cache")
    _redis.set("lab:last", n, ex=300)
    return JsonResponse({"hits": n, "last": int(_redis.get("lab:last") or 0)})


def cpu(request):
    """CPU load: spin for ?ms= milliseconds (at most 500)."""
    ms = min(max(int(request.GET.get("ms", "20")), 0), 500)
    end = time.perf_counter() + ms / 1000
    x = 0
    while time.perf_counter() < end:
        x += 1
    return JsonResponse({"ms": ms, "loops": x})


def job(request):
    """Worker load: queue a job the Celery worker finishes (?work=ms)."""
    work = min(max(int(request.GET.get("work", "100")), 0), 5000)
    j = Job.objects.create()
    finish_job.delay(j.id, work)
    return JsonResponse({"queued": j.id})


def stats(request):
    """Counters, to watch a load test from outside."""
    return JsonResponse({
        "visits": Visit.objects.count(),
        "jobs_queued": Job.objects.count(),
        "jobs_done": Job.objects.exclude(done_at=None).count(),
        "cache_hits": int(_redis.get("lab:cache") or 0),
        "host": socket.gethostname(),
        "version": os.environ.get("APP_VERSION", "dev"),
    })
