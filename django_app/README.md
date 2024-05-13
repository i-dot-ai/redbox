# How to run and test the django app

## running and testing the django app locally

1. copy `.env.test` to `django_app/.env`
2. (re)start postgres and minio `docker-compose up -d db minio` 
3. open you IDE at `django_app` and run the tests here, or navigate to `cd django_app`
4. the server can be run locally using `poetry run python manage.py runserver`
5. test can be run .locally using `poetry run python pytest`

## running admin commands in docker
1. copy `.env.django` to `django_app/.env`
2. (re)start postgres and minio `docker-compose up -d db minio` 
3. run `docker-compose run django-app venv/bin/django-admin <your-management-command>`

## running tests in docker
1. copy `.env.django` to `django_app/.env`
2. (re)start postgres and minio `docker-compose up -d db minio` 
3. `make test-django`
