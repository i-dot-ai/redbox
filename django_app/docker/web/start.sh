#!/bin/sh

set -o errexit
set -o nounset

poetry run python django_app/manage.py migrate
poetry run python django_app/manage.py collectstatic --noinput
poetry run python django_app/manage.py runserver 0.0.0.0:8090
