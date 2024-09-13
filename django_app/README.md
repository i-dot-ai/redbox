# How to run and test the django app

## running and testing the django app locally

1. copy `.env.test` to `django_app/.env`
2. (re)start postgres and minio `docker-compose up -d db minio` 
3. open you IDE at `django_app` and run the tests here, or navigate to `cd django_app`
4. the server can be run locally using `poetry run python manage.py runserver`
5. test can be run .locally using `poetry run pytest`

## running admin commands in docker
1. copy `.env.test` to `.env`
2. (re)start postgres and minio `docker-compose up -d db minio` 
3. run `docker-compose run django-app venv/bin/django-admin <your-management-command>`

## running tests in docker
1. copy `.env.test` to `.env`
2. (re)start postgres and minio `docker-compose up -d db minio` 
3. `make test-django`

## Tasks with Django-Q2

We're using [Django-Q2](https://django-q2.readthedocs.io/) for handling scheduled tasks.
This is a fork of the now-inactive Django-Q project.

This was chosen because it allows us to schedule, run and monitor tasks with limited additional infrastructure, as well as being a project that is relatively popular and well-maintained.

The selected [message broker](https://django-q2.readthedocs.io/) is the DjangoORM, which stores tasks in the Postgres database, enabling us to schedule, manage and monitor tasks from Django Admin.

In the longer term, if we end up with many more tasks, we might want to go for a different broker or even task runner, but this will involve setting up more infrastructure.

## Enqueueing tasks

Tasks can be scheduled, managed and monitored from Django Admin at: `/admin/django_q/`.

Task functions can be from anywhere in the django codebase; to organise them, there is a `tasks` directory inside `redbox_core`.

To schedule a new task, visit `/admin/django_q/schedule/` and 'Add Scheduled Task'.
In the form:

| Field   | Details | Example |
| -------- | ------- | ------- |
| Name *(optional)* | Human-friendly task name | Delete expired data |
| Func | Reference to the task function   | django.core.management.call_command     |
| Args | Function args   | 'delete_expired_data' *note the quotation marks for string inputs*   |
| Schedule Type    | How frequently to run the task    | Daily     |
| Repeats    | -1 for an infinite task, or set a specific number    | 5     |
| Next Run    | Choose the time and date, watching out for timezones    |      |

Once a task has been run, the outcome can be seen in either the 'Successful tasks' or 'Failed tasks' screen.

## Viewing task status

To see a summary of task statuses, run
`poetry run python manage.py qinfo` while in the `redbox/django_app` directory.

## Other schedulers considered

### AWS Lambda

We have tried this recently, however there were problems with connections to the Django DB that failed without notification, requiring a manual fix of failed tasks.

### Celery

Widely popular and actively maintained, but has a number of issues: https://steve.dignam.xyz/2023/05/20/many-problems-with-celery/ . Does not make use of our existing infrastructure, so would incur greater additional complexity and costs.

### RQ

Also popular and well-maintained. Has the advantage of using Redis as a message broker, which we are already using and is reportedly more reliable for longer-term tasks than Celery. However, this would require us to set up three new services:

* a scheduler
* a worker
* a dashboard service to allow us to monitor tasks

In the future, if we have the need of a task scheduler that is more robust at greater volumes, this would be a good option to consider.

### TaskTiger, Dramatiq, Huey

Similar options to RQ, though less well-known. Again, needs to run several services.

### WorkQ, Django Carrot

No longer actively maintained.
