# Tasks with Django-Q2

## Django-Q2

We're using [Django-Q2](https://django-q2.readthedocs.io/) for handling scheduled tasks.
This is a fork of the now-inactive Django-Q project.

This was chosen because it allows us to schedule, run and monitor tasks with limited additional infrastructure, as well as being a project that is relatively popular and well-maintained.

The selected message broker is the Postgres database, which enables us to schedule, manage and monitor tasks from Django Admin.

In the longer term, if we end up with many more tasks, we might want to go for a different broker or even task runner, but this will involve setting up more infrastructure.

## Scheduling tasks

Tasks can be scheduled, managed and monitored from Django Admin at: `/admin/django_q/`.

Task functions can be from anywhere in the django codebase; to organise them, there is a `tasks` directory inside `redbox_core`.

To schedule a new task, visit `/admin/django_q/schedule/` and 'Add Scheduled Task'.
In the form:

| Field   | Details | Example |
| -------- | ------- | ------- |
| Name *(optional)* | Human-friendly task name | Delete expired data |
| Func | Reference to the task function   | redbox_app.redbox_core.tasks.delete_expired_data.task     |
| Schedule Type    | How frequently to run the task    | Daily     |
| Repeats    | -1 for an infinite task, or set a specific number    | 5     |
| Next Run    | Choose the time and date, watching out for timezones    |      |
| *Cron*  | *Not currently implemented*    |      |

Once a task has been run, the outcome can be seen in either the 'Successful tasks' or 'Failed tasks' screen.
