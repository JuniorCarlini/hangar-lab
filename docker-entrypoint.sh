#!/bin/sh
# Migrations run once per start of the web service (RUN_MIGRATIONS=1, the
# default); the worker sets RUN_MIGRATIONS=0. The database may still be
# starting (first deploy): try for up to 60 s. Then the command runs.
set -e
if [ "${RUN_MIGRATIONS:-1}" = "1" ]; then
  tries=0
  until python manage.py migrate --noinput; do
    tries=$((tries + 1))
    if [ "$tries" -ge 30 ]; then
      echo "banco indisponível depois de 60 s" >&2
      exit 1
    fi
    echo "banco ainda subindo; nova tentativa em 2 s" >&2
    sleep 2
  done
fi
exec "$@"
