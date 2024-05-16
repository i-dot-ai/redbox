#!/bin/sh

venv/bin/django-admin migrate
venv/bin/django-admin collectstatic --noinput
venv/bin/django-admin compress --force --engine jinja2
venv/bin/django-admin assign_superuser_status

exec venv/bin/daphne -p 8090 redbox_app.asgi:application