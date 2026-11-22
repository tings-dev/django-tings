# Table presentation

Include the assets once on the page, then render each instance with the regular django-tables2 tag.

```django
{% load django_tables2 %}
{% include "django_tings/interactive_table/assets.html" %}
{% render_table clients %}
{% render_table suppliers %}
```

The include serves the stylesheet, browser enhancement and Datastar 1.0.2 from Django staticfiles. A host that already loads Datastar can use `{% include "django_tings/interactive_table/assets.html" with host_datastar=True %}`. Search forms, sort links and pagination work through ordinary GET navigation with JavaScript disabled.

## Display options

Declare a `TableDisplay` on the table class, or pass an instance as `display=` to `for_request`. For example, the following configuration keeps a status word on mobile cards while giving desktop users a compact status badge.

```python
from django.utils.translation import gettext_lazy as _
from django_tings.interactive_table import (
    ColumnKind,
    TableDisplay,
    TableMobileLayout,
    TableStatusStyle,
)

display = TableDisplay(
    caption=_("Contacts"),
    search_label=_("Search contacts"),
    column_kinds={"status": ColumnKind.STATUS},
    status_styles={
        "active": TableStatusStyle(_("Active"), tone="success", icon="check")
    },
    icon_only_status_columns=("status",),
    mobile=TableMobileLayout(
        heading_column="name",
        summary_columns=("email",),
        detail_columns=("team",),
        badge_column="status",
    ),
)
```

Use icon-only desktop badges alongside a visible legend. Screen readers receive the full status name. A table with no mobile layout keeps the semantic table inside a labeled, keyboard-focusable scroll region. The card layout starts below 48rem.

`search_mode` accepts `visible`, `collapsed` and `hidden`. Use `density` for compact or comfortable rows, `column_sublabels` for units, `sticky_headers` for the desktop header, and `comparison_scroll`, `wide_table` or `pin_identity_column` for comparison views. Set `identity_column` to pin an identifier independently of a row link. The `pagination_position` class setting accepts a tuple containing `"above"`, `"below"`, or both. `pagination_alignment_above` and `pagination_alignment_below` each accept `left`, `center` or `right`.

When `show_cell_diffs` is enabled, supply a `_cell_diffs` mapping on each changed record, keyed by column name with the previous display value. `row_tone_status_column` colors a row according to its status. `cell_tone_columns` maps a column name to the field holding that cell’s tone.

## CSS properties

The stylesheet scopes its rules to `.it-table` in the CSS cascade layer `tings`. Set properties on a table or a host selector that matches the table. Host stylesheets using cascade layers can declare `@layer tings, theme, base, components, utilities;` before either stylesheet loads.

| Property | Applies to | Default |
| --- | --- | --- |
| `--it-accent` | Links, focus rings and active chips | `#25537a` |
| `--it-surface`, `--it-header` | Body and heading surfaces | `#fff`, `#f1f5f7` |
| `--it-text`, `--it-muted` | Body and secondary text | `#192933`, `#4c606c` |
| `--it-line` | Dividers and control borders | `#bac8cf` |
| `--it-success`, `--it-info`, `--it-warning`, `--it-error` | Status text and row tones | `#185737`, `#204e75`, `#694613`, `#912f32` |
| `--it-font` | Font shorthand | Inherited |
| `--it-space`, `--it-radius` | Cell spacing and corner radius | `.75rem`, `.4rem` |
| `--it-sticky-offset` | Top offset for the sticky header | `0px` |
| `--it-cell-max` | Maximum width of a truncated cell | `32ch` |
| `--it-wide-width` | Width of an opted-in wide table at 80rem and above | `100%` |

```css
.review-panel .it-table {
  --it-accent: #16645d;
  --it-sticky-offset: var(--app-toolbar-height);
  --it-space: .65rem;
}
```

## Component templates

Set project defaults in Django settings. A per-instance `theme=` mapping overlays individual project defaults. A `TableTheme` instance supplies a complete theme.

```python
DJANGO_TINGS_TABLE_THEME = {
    "status_badge": "directory/components/status.html",
}
```

Each template receives the same context on the initial page and on refresh. All three receive `table` and `mobile` (true for a card).

| Slot | Context and responsibility |
| --- | --- |
| `status_badge` | `row`, `record`, bound `column`, rendered cell `value`, matched `style` (or None), and `icon_only`. Render the visible or accessible status name. |
| `empty` | `table.request_state.has_active_filters` selects the filtered or initial message on `table.display.empty`. `table.empty_action_url` contains the resolved action when permitted. Render empty content and its optional link. |
| `action` | `row`, `record`, configured `action`, `action_url`, `action_value`, `action_disabled` and `action_disabled_reason`. Supply the link or button’s content, including its accessible name. The table renders the control, disabled state and explanation. |

For example, a host status template can supply a branded shape while keeping the translated status label.

```django
{% if style %}
  <span class="directory-status" data-tone="{{ style.tone }}">{{ style.label }}</span>
{% else %}
  {{ value }}
{% endif %}
```

Use django-tables2 custom columns for domain-specific cell rendering. Use Django translation primitives for application labels and template copy. The distribution includes English defaults and a compiled German catalog for its controls, counts and feedback.

## Running the installed-package browser checks

Build the wheel in the checkout and install it alongside Playwright in a separate environment. Run the browser checks from a directory outside the checkout. The test script serves its own Django directory on a temporary localhost port.

```sh
uv build --wheel
work=$(mktemp -d)
uv venv --python 3.12 "$work/venv"
uv pip install --python "$work/venv/bin/python" dist/*.whl playwright
"$work/venv/bin/python" -m playwright install chromium
checkout=$PWD
(cd "$work" && "$work/venv/bin/python" "$checkout/tests/browser/check_directory.py")
```

If Chromium is already installed, set `CHROME_BIN` to its executable path. The checks exercise the packaged and host-supplied runtime, interleaved requests, retry, ordinary GET, keyboard focus, mobile details, alternate badge content and cross-page bulk POST.
