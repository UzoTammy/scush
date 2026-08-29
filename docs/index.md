# Scush Developer Documentation

Scush is the Django-based internal system for Ozone — covering staff/HR, stock and
warehouse management, trade and cashflow reporting, customer records, recruitment,
and internal comms.

This site is built with [MkDocs](https://www.mkdocs.org/) (Material theme) and served
directly by the Django app as static files, replacing the previous S3-hosted
documentation site.

## Where to start

- **New to the project?** Start with [Setup](getting-started/setup.md) to get a local
  environment running.
- **Want the lay of the land?** See [Project Structure](architecture/overview.md) for
  how the codebase is organized, and [Apps](architecture/apps.md) for what each
  Django app owns.
- **Shipping a change?** See [Testing](getting-started/testing.md) before you open a PR,
  and [Deployment](operations/deployment.md) for how it gets to production.

## Adding a page

1. Add a new Markdown file under `docs/`.
2. List it in the `nav:` section of `mkdocs.yml` at the repo root.
3. Rebuild the site:

   ```
   mkdocs build
   ```

4. Commit the regenerated files in `core/static/docs/` along with your Markdown source.

!!! note
    This site documents the codebase for developers. End-user help pages (how to use
    the app) live inside the app itself, not here.
