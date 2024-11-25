#!/bin/sh

venv/bin/django-admin migrate
venv/bin/django-admin collectstatic --noinput
venv/bin/django-admin create_admin_user

venv/bin/django-admin qcluster &

venv/bin/daphne -b 0.0.0.0 -p 8080 redbox_app.asgi:application