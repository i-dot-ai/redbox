#!/bin/sh

set -o errexit
set -o nounset

python django_app/manage.py migrate
python django_app/manage.py collectstatic --noinput
python django_app/manage.py runserver 0.0.0.0:8090
