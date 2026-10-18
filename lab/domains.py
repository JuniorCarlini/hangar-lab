"""Hangar's domain check: before issuing a certificate for an unknown
domain, Hangar asks the app whether it belongs to an active store.

GET /.well-known/hangar/domain-check?domain=<host>
X-Hangar-Timestamp: unix seconds
X-Hangar-Signature: hex(HMAC-SHA256(HANGAR_DOMAIN_CHECK_SECRET, "<host>|<ts>"))

200 = issue, 404 = not a store, 403 = bad signature (secret out of date)."""

import hashlib
import hmac
import os
import time

from django.http import HttpResponse

from .models import Store

MAX_SKEW = 300  # seconds


def domain_check(request):
    secret = os.environ.get("HANGAR_DOMAIN_CHECK_SECRET", "")
    host = request.GET.get("domain", "").strip().lower()
    ts = request.headers.get("X-Hangar-Timestamp", "")
    sig = request.headers.get("X-Hangar-Signature", "")
    if not secret or not host or not ts.isdigit() or abs(time.time() - int(ts)) > MAX_SKEW:
        return HttpResponse(status=403)
    want = hmac.new(secret.encode(), f"{host}|{ts}".encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(want, sig):
        return HttpResponse(status=403)
    if Store.objects.filter(domain=host, active=True).exists():
        return HttpResponse("ok")
    return HttpResponse(status=404)


def store_for(request):
    """The store whose domain this request came in on, if any."""
    host = request.get_host().split(":")[0].lower()
    return Store.objects.filter(domain=host).first()
