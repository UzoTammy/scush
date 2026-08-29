# Setup

## Requirements

- Python 3.14 (see `.python-version` / `Pipfile`)
- PostgreSQL (local dev defaults to a `scush_local` database; SQLite is used as a
  fallback if `DATABASE_URL` isn't set)
- [pipenv](https://pipenv.pypa.io/) for dependency management

## Install dependencies

```
pipenv install --dev
pipenv shell
```

## Environment variables

Settings are read via `python-decouple` from a `.env` file at the repo root
(gitignored — never commit it). Required/used keys, from `ozone/settings.py`:

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | Django secret key |
| `DEBUG` | `True`/`False`, defaults to `False` |
| `DATABASE_URL` | Postgres connection string (`sqlite:///db.sqlite3` if unset) |
| `ALLOWED_HOSTS` | Comma-separated allowed hosts |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` / `AWS_STORAGE_BUCKET_NAME` | S3 bucket used for media file storage (`django-storages`) |
| `EMAIL_USER` / `EMAIL_PASS` | SMTP credentials (Gmail) used for outgoing mail in production |
| `CLOUDAMQP_URL` | Celery broker URL, only read when `DEBUG=False` |

In `DEBUG` mode, outgoing email is written to files under `mail/sample/` instead of
being sent (`EMAIL_BACKEND` is file-based), so you don't need real SMTP credentials
to develop locally — the AWS and email keys still need *some* value for settings to
load without raising, even if a placeholder.

## Database

```
python manage.py migrate
python manage.py createsuperuser
```

## Run the dev server

```
python manage.py runserver
```

The app is served at `http://127.0.0.1:8000/`. See [Project Structure](../architecture/overview.md)
for how URLs are routed to each app.
