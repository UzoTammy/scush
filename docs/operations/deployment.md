# Deployment

Scush runs on Heroku.

- `Procfile`: `web: gunicorn ozone.wsgi`
- `django-on-heroku` is applied in `settings.py` whenever `DEBUG=False`
  (`django_on_heroku.settings(locals())`) — it wires up the production database URL
  parsing and other Heroku-specific config on top of the base settings.
- **Static files** are served by Whitenoise
  (`CompressedManifestStaticFilesStorage`) — no separate static host needed.
- **Media uploads** go to S3 via `django-storages`/`boto3`
  (`AWS_STORAGE_BUCKET_NAME`, etc.).
- **Outgoing email** switches from file-based (dev) to real SMTP (Gmail,
  `EMAIL_HOST_USER`/`EMAIL_HOST_PASSWORD`) once `DEBUG=False`.

## Releasing a change

```
git push heroku main
heroku run python manage.py migrate
```

Set any new environment variable with `heroku config:set KEY=value` before deploying
code that depends on it — see [Setup](../getting-started/setup.md) for the full list
`settings.py` reads.

## Docs site

If you changed anything under `docs/`, rebuild and commit the generated site before
deploying, otherwise the live `/static/docs/` pages won't reflect your edits:

```
mkdocs build
```
