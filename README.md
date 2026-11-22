# django-tings

Reusable Django components. `django_tings.interactive_table` renders django-tables2 tables and adds live search, sorting, and pagination with Datastar.

## Install

The package requires Python 3.12 or later and supports Django 6.0 and 6.1, django-tables2 2.8 through 3.x, and datastar-py 1.x from 1.0.2.

Build and install the local wheel with `uv build --wheel` and `uv pip install dist/django_tings-*.whl`. Add `django_tables2` and `django_tings.interactive_table` to `INSTALLED_APPS`. Enable `APP_DIRS` in the Django template backend and include the `django.template.context_processors.request` context processor.

Declare columns on an `InteractiveTable` subclass and use its async `for_request(request, load_page=...)` method in a view. The loader receives a `TableQuery` and returns a `TablePage` with the requested rows and the total number of matches. Render the result and include its assets once per page.

```django
{% load django_tables2 %}
{% include "django_tings/interactive_table/assets.html" %}
{% render_table table %}
```

Use `{% include "django_tings/interactive_table/assets.html" with host_datastar=True %}` if the host already loads Datastar. The default stylesheet, browser enhancement, local Datastar runtime, and German translation catalog are included in the wheel.

## Development

Run `uv sync --locked --dev` and `uv run pytest`. Use `uv run ruff check` and `uv run ruff format --check` for linting and formatting.

To smoke-test a wheel in a clean Django consumer at the dependency floor, run from the repository root.

```sh
consumer_dir=$(mktemp -d)
uv build --wheel --out-dir "$consumer_dir"
sha256sum "$consumer_dir"/*.whl
cp tests/installed_wheel.py "$consumer_dir/"
uv venv --python 3.12 "$consumer_dir/.venv"
uv pip install --python "$consumer_dir/.venv/bin/python" "$consumer_dir"/*.whl \
  'Django==6.0' 'django-tables2==2.8.0' 'datastar-py==1.0.2'
(cd "$consumer_dir" && .venv/bin/python -I installed_wheel.py)
```

See [the MIT license](LICENSES/MIT.txt) for terms. The bundled Datastar runtime ships with its upstream license.
