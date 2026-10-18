#!/usr/bin/env python3
"""Load test for the Hangar Lab app, with the standard library only.

    python3 loadtest/carga.py https://lab-web.<ip>.sslip.io --rota misto --usuarios 50 --segundos 60

Routes: write (PostgreSQL), cache (Redis), cpu (processing), job (Celery
worker), misto (all of them) and home (the page). Each simulated user keeps
one connection open and fires requests back to back. At the end: requests
per second, times (p50/p95/p99), status codes and errors.
"""

import argparse
import http.client
import random
import ssl
import statistics
import threading
import time
import urllib.parse
from collections import Counter

ROUTES = {
    "write": ["/api/write"],
    "cache": ["/api/cache"],
    "cpu": ["/api/cpu?ms=20"],
    "job": ["/api/job?work=50"],
    "home": ["/"],
    "misto": ["/api/write", "/api/cache", "/api/cpu?ms=10", "/api/job?work=50", "/"],
}


def worker(url, paths, stop_at, out, lock):
    u = urllib.parse.urlsplit(url)
    ctx = ssl.create_default_context()

    def connect():
        if u.scheme == "https":
            return http.client.HTTPSConnection(u.hostname, u.port or 443, timeout=15, context=ctx)
        return http.client.HTTPConnection(u.hostname, u.port or 80, timeout=15)

    conn = connect()
    times, codes, errors = [], Counter(), Counter()
    while time.monotonic() < stop_at:
        path = random.choice(paths)
        t0 = time.perf_counter()
        try:
            conn.request("GET", path, headers={"User-Agent": "hangar-lab-carga"})
            r = conn.getresponse()
            r.read()
            codes[r.status] += 1
            times.append(time.perf_counter() - t0)
        except Exception as e:  # noqa: BLE001 - counted, then reconnect
            errors[type(e).__name__] += 1
            conn.close()
            conn = connect()
    conn.close()
    with lock:
        out["times"] += times
        out["codes"].update(codes)
        out["errors"].update(errors)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("url")
    ap.add_argument("--rota", choices=sorted(ROUTES), default="misto")
    ap.add_argument("--usuarios", type=int, default=20)
    ap.add_argument("--segundos", type=int, default=30)
    a = ap.parse_args()

    out = {"times": [], "codes": Counter(), "errors": Counter()}
    lock = threading.Lock()
    stop_at = time.monotonic() + a.segundos
    print(f"Carga: {a.usuarios} usuários, {a.segundos} s, rota '{a.rota}' em {a.url}")
    threads = [threading.Thread(target=worker, args=(a.url, ROUTES[a.rota], stop_at, out, lock)) for _ in range(a.usuarios)]
    t0 = time.monotonic()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    elapsed = time.monotonic() - t0

    ts = sorted(out["times"])
    total = len(ts) + sum(out["errors"].values())
    print(f"\nRequisições: {total} em {elapsed:.1f} s  ->  {len(ts) / elapsed:.0f} req/s")
    if ts:
        q = statistics.quantiles(ts, n=100)
        print(f"Tempo: p50 {q[49] * 1000:.0f} ms · p95 {q[94] * 1000:.0f} ms · p99 {q[98] * 1000:.0f} ms · máx {ts[-1] * 1000:.0f} ms")
    print("Respostas:", dict(sorted(out["codes"].items())))
    ok = sum(n for c, n in out["codes"].items() if 200 <= c < 300)
    print(f"Sucesso: {100 * ok / max(total, 1):.2f}%")
    if out["errors"]:
        print("Erros de conexão:", dict(out["errors"]))


if __name__ == "__main__":
    main()
