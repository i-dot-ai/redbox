# Tasks with Django-Q2

## Django-Q2

We're using [Django-Q2](https://django-q2.readthedocs.io/) for handling scheduled tasks.
This is a fork of the now-inactive Django-Q project.

This was chosen because it allows us to schedule, run and monitor tasks with limited additional infrastructure, as well as being a project that is relatively popular and well-maintained.

The selected [message broker](https://django-q2.readthedocs.io/) is the the standard Redis.

In the longer term, if we end up with many more tasks, we might want to go for a different task runner, but this will involve setting up more infrastructure.

## Enqueueing tasks

Tasks can either be triggered as a one-off or scheduled task. There is an example command to schedule a task to run the `delete expired data` management command here on a cron schedule here: `django_app/redbox_app/redbox_core/management/commands/enqueue_delete_expired_data.py` .

Task schedules are stored as a `Schedule` object the database. They can be inspected (and if necessary, deleted) in the Django ORM shell via: `from django_q.models import Schedule`.

For information on enqueueing a one-off task (e.g. in response to a file upload), see https://django-q2.readthedocs.io/en/master/tasks.html .

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
