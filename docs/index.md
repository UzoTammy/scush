# Scush Documentation

Welcome to the Scush system documentation.

This site is built with [MkDocs](https://www.mkdocs.org/) and served directly by the Django app,
replacing the previous S3-hosted documentation site.

## Adding a page

1. Add a new Markdown file under `docs/`.
2. List it in the `nav:` section of `mkdocs.yml` at the repo root.
3. Rebuild the site:

   ```
   mkdocs build
   ```

4. Commit the regenerated files in `core/static/docs/` along with your Markdown source.
