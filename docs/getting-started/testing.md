# Testing

Tests run under `pytest` with `pytest-django`.

```
pytest
```

## Conventions

- Test files are named `tests.py` (one per app, e.g. `stock/tests.py`,
  `trade/tests.py`) — see `pytest.ini`'s `python_files=tests.py`. This differs from
  pytest's default `test_*.py` discovery, so a new `test_foo.py` file will silently
  **not** be collected; put tests in `tests.py`.
- Shared fixtures (`new_user`, `superuser`, `user_in_group_factory`,
  `balance_tolerance_setting`, etc.) live in the root `conftest.py` (repo root, not
  under `docs/`) rather than being redefined per app.
- Coverage is tracked via `pytest-cov` / `coverage` (`.coverage` at repo root).

```
pytest --cov
```

## Where coverage currently exists

`stock` and `trade` have the most complete test suites. Newer or in-progress apps
(`jobs`, `comms`, `delivery`) are lighter on tests — check an app's `tests.py` before
assuming behavior is covered.
