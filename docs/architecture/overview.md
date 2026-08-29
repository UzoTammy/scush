# Project Structure

Scush is a single Django project (`ozone/`) made up of many focused apps, one per
business domain, rather than one monolithic app.

```
ozone/            project package: settings.py, urls.py, wsgi/asgi, celery.py
core/             cross-cutting: Setting, CompanyProfile, JsonDataset, static docs site
<app>/            one directory per business domain — see Apps
docs/             this documentation site (source for MkDocs)
process-documentation/   internal planning/design notes (not part of this site)
```

## Settings (`ozone/settings.py`)

- Config values come from a local `.env` file via `python-decouple` — see
  [Setup](../getting-started/setup.md) for the variable list.
- `DEBUG=False` switches several things at once: SMTP email instead of file-based,
  the Celery broker URL is read from `CLOUDAMQP_URL`, and `django_on_heroku.settings()`
  is applied (Heroku-friendly DB/static config).
- Static files are served by **Whitenoise** (`CompressedManifestStaticFilesStorage`);
  media uploads go to **S3** via `django-storages`.
- `django_session_timeout` enforces an inactivity timeout (20 min in `DEBUG`, 10 min
  in production).

## URL routing (`ozone/urls.py`)

Each app owns a URL prefix and its own `urls.py`, included from the project root:

```python
path('customer/', include('customer.urls')),
path('apply/', include('apply.urls')),
path('product/', include('stock.urls')),
path('store/', include('warehouse.urls')),
path('staff/', include('staff.urls')),
path('trade/', include('trade.urls')),
...
```

Note the prefixes don't always match the app's directory name (`stock` → `product/`,
`warehouse` → `store/`) — check `ozone/urls.py` rather than assuming.

`core.urls` is mounted at `/` and handles the site's home/shared routes.

## Background jobs

See [Celery](../operations/celery.md) — a broker is configured but there's a known gap
in how it's run. Don't assume a task queued with `.delay()` is actually being
processed; check that page first.

## This documentation site

Source lives in `docs/`, is built by `mkdocs build` into `core/static/docs/`, and is
served as a static asset by Django — this replaced an older S3-hosted docs site.
Rebuild and commit the generated output whenever you add or edit a page — see
[the home page](../index.md#adding-a-page).
