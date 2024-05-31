# How to run and test the django app

## running and testing the django app locally

1. copy `.env.test` to `django_app/.env`
2. (re)start postgres and minio `docker-compose up -d db minio` 
3. open you IDE at `django_app` and run the tests here, or navigate to `cd django_app`
4. the server can be run locally using `poetry run python manage.py runserver`
5. test can be run .locally using `poetry run pytest`

## running admin commands in docker
1. copy `.env.django` to `django_app/.env`
2. (re)start postgres and minio `docker-compose up -d db minio` 
3. run `docker-compose run django-app venv/bin/django-admin <your-management-command>`

## running tests in docker
1. copy `.env.django` to `django_app/.env`
2. (re)start postgres and minio `docker-compose up -d db minio` 
3. `make test-django`

---

# Changes to integrate Staff SSO 

These changes captured here to documents the steps taken to integrate the django-staff-sso-client into redbox.

You need to be in the django_app folder.
1. `poetry remove django-gov-notify`
2. Open `pyproject.toml` and downgrade the Django dependency (e.g. 4.2.2)
3. `poetry add django-staff-sso-client`
4. Follow the remainder of the instructions at <https://github.com/uktrade/django-staff-sso-client>
5. Update 'sign-in-view' in `auth_views.py` to redirect to '/auth/login'

Currently, users will only be able to authenticate if they already exist in the local db.  To do so, login to admin as a superuser & manually add users.

## Common errors

If unable to create a superuser 
`docker exec -it <container name> poetry run python manage.py createsuperuser`

Exec into the django-app container and run the following: 
`source venv/bin/activate`
`pip install poetry`
`poetry install`
`venv/bin/django-admin migrate`
`venv/bin/django-admin createsuperuser`

^ Some of these steps may be superfluous, further testing to be done.
