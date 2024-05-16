# How to run and test the django app

## running and testing the django app locally

1. (re)start postgres and minio `docker-compose up -d db minio` 
2. run `docker exec minio rm -rf data/redbox-storage-dev/Cabinet_Office_-_Wikipedia.pdf/` to remove any existing test files
3. open you IDE at `django_app` and run the tests here, or navigate to `cd django_app`
4. the server can be run locally using `export POSTGRES_HOST=localhost && poetry run python manage.py runserver`
    1. If you change your local `.env` you can skip the export step
5. test can be run .locally using `poetry run pytest`

## running admin commands in docker
1. copy `.env.django` to `django_app/.env`
2. (re)start postgres and minio `docker-compose up -d db minio` 
3. run `docker-compose run django-app venv/bin/django-admin <your-management-command>`

## running tests in docker 
1. `make test-django`
