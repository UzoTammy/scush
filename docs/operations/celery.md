# Background jobs (Celery)

Celery is wired into the project (`ozone/celery.py`), and `CLOUDAMQP_URL` is
configured as the broker in production (`ozone/settings.py`, only read when
`DEBUG=False`).

Currently the only task defined is `core.tasks.send_email`, which renders an email
template and sends it (used in place of sending mail synchronously from a view).

## Known gap

There is **no worker dyno running on Heroku**. The broker (CloudAMQP) and app config
are in place, but nothing is consuming the queue — a call to `send_email.delay(...)`
gets queued and never processed. Until a worker dyno is added (`Procfile` needs a
`worker: celery -A ozone worker` line, and it needs to actually be scaled on
Heroku), treat any `.delay()` call as **not actually running in production**.

If you're debugging "the email never arrived" in production, check this first before
assuming the bug is in the email content or SMTP credentials.

## Running a worker locally

`CELERY_BROKER_URL` is only set from `CLOUDAMQP_URL` when `DEBUG=False`, so in a
normal local dev run it's unset and Celery falls back to its default (a local
RabbitMQ on `localhost`). To actually exercise a task locally, either run a broker
locally or point `CELERY_BROKER_URL` at a broker yourself, then:

```
celery -A ozone worker -l info
```
