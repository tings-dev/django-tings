"""Template helpers for the server-rendered controls and rows."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any
from urllib.parse import urlencode

from django import template
from django.utils.translation import gettext

from django_tings.interactive_table.display import record_value

if TYPE_CHECKING:
    from django_tings.interactive_table import InteractiveTable

register = template.Library()


@register.filter
def get_item(dictionary: dict[str, Any] | None, key: str) -> Any:
    """Get an item from a dictionary by key.

    Usage: {{ mydict|get_item:key }}
    """
    if dictionary is None:
        return None
    return dictionary.get(key)


@register.simple_tag
def table_sort_url(table: InteractiveTable, column_name: str) -> str:
    """Return a conventional GET URL for sorting a table column."""
    return table.sort_url(column_name)


@register.simple_tag
def table_page_url(table: InteractiveTable, page: int) -> str:
    """Return a conventional GET URL for a result page."""
    return table.page_url(page)


@register.simple_tag
def table_aria_sort(table: InteractiveTable, column_name: str) -> str:
    """Return the ARIA sort state for a table column."""
    return table.aria_sort(column_name)


@register.simple_tag
def table_column_kind(table: InteractiveTable, column_name: str) -> str:
    """Return a table column's semantic display kind."""
    return table.column_kind(column_name)


@register.simple_tag
def table_column_sublabel(table: InteractiveTable, column_name: str) -> str:
    """Return a table column's measurement unit, for the header sub-label."""
    return table.column_sublabel(column_name)


@register.simple_tag
def table_column_label(table: InteractiveTable, column_name: str) -> str:
    """Return the declared, human-facing label for a table column."""
    try:
        return str(table.columns[column_name].header)
    except KeyError:
        return column_name.replace("_", " ").capitalize()


@register.simple_tag
def table_filter_value(
    table: InteractiveTable,
    column_name: str,
    bound: str = "",
) -> str:
    """Return a current simple or range filter value."""
    value = table.column_filter_values.get(column_name, "")
    if bound:
        if not isinstance(value, Mapping):
            return ""
        value = value.get(bound, "")
    return str(value)


@register.simple_tag
def table_status_style(table: InteractiveTable, value: Any) -> Any:
    """Return the declared badge style for a STATUS-kind cell value."""
    return table.display.status_styles.get(str(value))


@register.simple_tag
def table_cell_tone(
    table: InteractiveTable,
    column_name: str,
    record: Mapping[str, Any],
) -> str:
    """Return the record's semantic tone for a cell, or "" when none applies."""
    tone_column = table.display.cell_tone_columns.get(column_name)
    if not tone_column:
        return ""
    return str(record_value(record, tone_column) or "")


@register.simple_tag
def table_row_tone(table: InteractiveTable, record: Mapping[str, Any]) -> str:
    """Return the record's row background tone, or "" when none applies."""
    return table.row_tone(record)


@register.simple_tag
def table_status_icon_only(table: InteractiveTable, column_name: str) -> bool:
    """Whether a STATUS column renders as an icon without its word."""
    return table.status_is_icon_only(column_name)


@register.simple_tag
def table_cell_diff(
    table: InteractiveTable,
    column_name: str,
    record: Mapping[str, Any],
) -> Any:
    """Return the previous value for a changed cell, or None when unchanged."""
    if not table.display.show_cell_diffs:
        return None
    diffs = record_value(record, "_cell_diffs")
    if not isinstance(diffs, Mapping) or column_name not in diffs:
        return None
    value = diffs[column_name]
    return "—" if value in (None, "") else value


@register.simple_tag
def table_row_url(table: InteractiveTable, record: Mapping[str, Any]) -> str:
    """Return a real identifying-cell destination for a table record."""
    target = table.display.row_target
    if target is None:
        return ""
    base = target.url_for(record)
    if not base or not target.preserve_return:
        return base or ""
    return f"{base}?{urlencode({'next': table._state_url()})}"


@register.simple_tag
def table_row_details_url(table: InteractiveTable, record: Mapping[str, Any]) -> str:
    """Return the same-page details destination for a record, or "" when none."""
    target = table.display.row_details
    if target is None:
        return ""
    value = target.value_for(record)
    if value is None:
        return ""
    return table._state_url(**{target.query_param: value})


@register.simple_tag
def table_row_action_value(table: InteractiveTable, record: Mapping[str, Any]) -> str:
    """Return the row action button's record value, or "" when none."""
    action = table.display.row_action
    if action is None:
        return ""
    return action.value_for(record) or ""


@register.simple_tag
def table_row_action_disabled(
    table: InteractiveTable, record: Mapping[str, Any]
) -> bool:
    """Whether the record renders its row action button disabled."""
    action = table.display.row_action
    if action is None:
        return False
    return action.disabled_for(record)


@register.simple_tag
def table_row_action_disabled_reason(
    table: InteractiveTable, record: Mapping[str, Any]
) -> str:
    """The record's row-action disabling explanation, or ""."""
    action = table.display.row_action
    if action is None:
        return ""
    return action.disabled_reason_for(record)


@register.simple_tag
def table_row_action_url(table: InteractiveTable, record: Mapping[str, Any]) -> str:
    """Destination for an enabled linked row action, or ""."""
    action = table.display.row_action
    if action is None or action.disabled_for(record):
        return ""
    if action.route_name:
        base = action.url_for(record)
        if not base:
            return ""
        if not action.preserve_return:
            return base or ""
        return f"{base}?{urlencode({'next': table._state_url()})}"
    if not action.query_param:
        return ""
    value = action.value_for(record)
    if value is None:
        return ""
    return table._state_url(**{action.query_param: value})


@register.simple_tag
def table_selection_value(table: InteractiveTable, record: Mapping[str, Any]) -> str:
    """Return the selection checkbox value for a record, or "" when none."""
    selection = table.display.selection
    if selection is None:
        return ""
    value = record_value(record, selection.value_column)
    return "" if value in (None, "") else str(value)


@register.simple_tag
def table_selection_label(table: InteractiveTable, record: Mapping[str, Any]) -> str:
    """Return the accessible name for a record's selection checkbox."""
    selection = table.display.selection
    if selection is None:
        return ""
    label = record_value(record, selection.label_column)
    if label in (None, ""):
        label = record_value(record, selection.value_column, "")
    return gettext("Select %(record)s") % {"record": label}


@register.simple_tag
def table_cell_url(
    table: InteractiveTable,
    column_name: str,
    record: Mapping[str, Any],
) -> str:
    """Return a per-column destination for a table record, or "" when none applies."""
    target = table.display.cell_targets.get(column_name)
    if target is None:
        return ""
    base = target.url_for(record)
    if not base:
        return ""
    if not base or not target.preserve_return:
        return base or ""
    return f"{base}?{urlencode({'next': table._state_url()})}"
