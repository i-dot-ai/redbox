#!/bin/sh

set -o errexit
set -o nounset

poetry run python manage.py migrate
poetry run python manage.py collectstatic --noinput
poetry run python manage.py runserver 0.0.0.0:8090
