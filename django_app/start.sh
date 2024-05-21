#!/bin/sh

venv/bin/django-admin migrate
venv/bin/django-admin collectstatic --noinput
venv/bin/django-admin compress --force --engine jinja2

exec venv/bin/gunicorn -c ./redbox_app/gunicorn.py redbox_app.wsgi