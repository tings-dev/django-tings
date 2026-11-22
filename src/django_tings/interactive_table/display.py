# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Markus Binsteiner

"""Translated display metadata for interactive tables."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from enum import StrEnum
from typing import Any, Self

from django.conf import settings
from django.urls import reverse
from django.utils.functional import Promise
from django.utils.translation import gettext_lazy as _


class ColumnKind(StrEnum):
    """Semantic display kind for a table column."""

    TEXT = "text"
    IDENTIFIER = "identifier"
    NUMBER = "number"
    DATE = "date"
    STATUS = "status"


class TableSearchMode(StrEnum):
    """Developer-defined search-control presentation."""

    VISIBLE = "visible"
    COLLAPSED = "collapsed"
    HIDDEN = "hidden"


class TableDensity(StrEnum):
    """Developer-defined desktop table density."""

    COMPACT = "compact"
    COMFORTABLE = "comfortable"


@dataclass(frozen=True, slots=True)
class TablePageTarget:
    """Named route and fixed query state for a table's containing page."""

    route_name: str
    route_kwargs: Mapping[str, str] = field(default_factory=dict)
    fixed_query: Mapping[str, str] = field(default_factory=dict)


def record_value(record: object, key: str, default: Any = None) -> Any:
    """Read a presentation field from a projected mapping or a record object."""
    if isinstance(record, Mapping):
        return record.get(key, default)
    return getattr(record, key, default)


def _record_url(route: str, fields: Mapping[str, str], record: object) -> str | None:
    if not route:
        return None
    kwargs: dict[str, str] = {}
    for argument, field_name in fields.items():
        value = record_value(record, field_name)
        if value in (None, ""):
            return None
        kwargs[argument] = str(value)
    return reverse(route, kwargs=kwargs)


@dataclass(frozen=True, slots=True)
class TableRowTarget:
    """Named detail route resolved from fields in a table record."""

    label_column: str
    route_name: str
    route_fields: Mapping[str, str]
    preserve_return: bool = True

    def url_for(self, record: object) -> str | None:
        """Return the row route when all required record fields are present."""
        return _record_url(self.route_name, self.route_fields, record)


@dataclass(frozen=True, slots=True)
class TableCellTarget:
    """Named route resolved from a single record's fields, for one column's cell."""

    route_name: str
    route_fields: Mapping[str, str]
    preserve_return: bool = True

    def url_for(self, record: object) -> str | None:
        """Reverse the cell's route, or return None when required fields are empty."""
        return _record_url(self.route_name, self.route_fields, record)


@dataclass(frozen=True, slots=True)
class TableRowDetails:
    """Same-page details link for a row, carried in a query parameter.

    The identity cell links to the table's own page with its canonical request
    state preserved and ``query_param`` set to the record's ``value_column``,
    so the containing view can render a details surface for that row.
    """

    label_column: str
    query_param: str = "details"
    value_column: str = "_index"

    def value_for(self, record: object) -> str | None:
        """Return the record's details value, or None when it has none."""
        value = record_value(record, self.value_column)
        if value in (None, ""):
            return None
        return str(value)


@dataclass(frozen=True, slots=True)
class TableRowSelection:
    """Opt-in selection checkboxes feeding bulk actions on table rows.

    With ``action_url`` set, the selection bar renders a POST form whose
    button submits the collected values as repeated ``selected`` fields
    (progressively enhanced; it stays disabled without JavaScript).
    """

    value_column: str
    label_column: str
    action_label: Any = ""
    action_url: str = ""
    action_fields: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True, slots=True)
class TableRowAction:
    """Trailing per-row action button rendered after the data columns.

    With ``route_name`` set, enabled actions render as links to that named
    route, reversed from the record fields in ``route_fields`` (skipped when
    a required field is empty) and carrying a ``next`` return path unless
    ``preserve_return`` is off. With ``query_param`` set instead, they link
    to the table's own page with that parameter set to the record's value.
    Without either the button is inert markup: ``name`` and ``value_column``
    surface as ``data-table-row-action`` / ``data-table-row-action-value``
    attributes for page scripts to bind behavior to. A truthy
    ``disabled_column`` record value renders the button disabled, with
    ``disabled_reason`` (or the record's ``disabled_reason_column`` value)
    explaining why to both pointer and screen-reader users.
    """

    label: str | Promise
    header_label: str | Promise = ""
    value_column: str = ""
    name: str = ""
    query_param: str = ""
    route_name: str = ""
    route_fields: Mapping[str, str] = field(default_factory=dict)
    preserve_return: bool = True
    disabled_column: str = ""
    disabled_reason: str | Promise = ""
    disabled_reason_column: str = ""
    #: Desktop cells render this status icon with the label visually hidden,
    #: keeping the action column narrow; mobile record cards keep the text.
    icon: str = ""
    #: Render nothing (instead of an inert button) for records without an
    #: action value — for actions that only apply to some rows.
    hide_without_value: bool = False

    def url_for(self, record: object) -> str | None:
        """Reverse the action's route, or None without one or on empty fields."""
        return _record_url(self.route_name, self.route_fields, record)

    def value_for(self, record: object) -> str | None:
        """Return the record's action value, or None when it has none."""
        if not self.value_column:
            return None
        value = record_value(record, self.value_column)
        if value in (None, ""):
            return None
        return str(value)

    def disabled_for(self, record: object) -> bool:
        """Whether the record renders its action button disabled."""
        return bool(self.disabled_column) and bool(
            record_value(record, self.disabled_column)
        )

    def disabled_reason_for(self, record: object) -> str:
        """The record's disabling explanation, falling back to the static one."""
        if self.disabled_reason_column:
            reason = record_value(record, self.disabled_reason_column)
            if reason:
                return str(reason)
        return str(self.disabled_reason)


@dataclass(frozen=True, slots=True)
class TableEmptyAction:
    """Optional permitted navigation from a table empty state."""

    label: str | Promise
    route_name: str
    permission: str | None = None
    route_kwargs: Mapping[str, str] = field(default_factory=dict)
    query: Mapping[str, str] = field(default_factory=dict)
    preserve_return: bool = True


@dataclass(frozen=True, slots=True)
class TableEmptyState:
    """Base and filtered empty-state guidance for a table."""

    title: str | Promise
    description: str | Promise
    filtered_title: str | Promise
    filtered_description: str | Promise
    action: TableEmptyAction | None = None


@dataclass(frozen=True, slots=True)
class TableStatusStyle:
    """Presentation of one value in a STATUS-kind column.

    ``tone`` names a semantic status color (``success``, ``info``, ``warning``,
    ``error``, or ``neutral``); the badge always pairs it with the translated
    label and an icon so color never carries the meaning alone.
    """

    label: str | Promise
    tone: str = "neutral"
    icon: str = ""


@dataclass(frozen=True, slots=True)
class QuickFilterFacet:
    """One value of a quick-filter column with its unfiltered row count."""

    value: str
    label: str | Promise
    count: int
    tone: str = "neutral"
    icon: str = ""


@dataclass(frozen=True, slots=True)
class TableMobileLayout:
    """Columns used by the narrow record-summary view."""

    heading_column: str
    summary_columns: tuple[str, ...]
    detail_columns: tuple[str, ...] = ()
    badge_column: str | None = None


DEFAULT_EMPTY = TableEmptyState(
    title=_("No data available"),
    description=_("There is no data to display yet."),
    filtered_title=_("No matching data"),
    filtered_description=_("Try changing or clearing the search and filters."),
)


@dataclass(frozen=True, slots=True)
class TableDisplay:
    """Complete presentation metadata for an interactive table."""

    caption: str | Promise = _("Data")
    search_label: str | Promise = _("Search data")
    page: TablePageTarget | None = None
    empty: TableEmptyState = DEFAULT_EMPTY
    mobile: TableMobileLayout | None = None
    column_kinds: Mapping[str, ColumnKind] = field(default_factory=dict)
    #: Per-column second line, set in small muted type under the column name.
    #: Two uses, both of which buy width back:
    #:
    #: - a measurement unit, which suffixed onto the values instead would set
    #:   the column's width on every row where the header states it once;
    #: - the less distinguishing half of a two-word name, so the column is only
    #:   as wide as the half that identifies it ("Year" over "Production",
    #:   rather than "Production year" on one line).
    #:
    #: Splitting the name also survives translation, where wrapping does not:
    #: German compounds like "Produktionsjahr" are a single unbreakable word.
    #: Unlisted columns render no second line.
    column_sublabels: Mapping[str, str | Promise] = field(default_factory=dict)
    row_target: TableRowTarget | None = None
    row_details: TableRowDetails | None = None
    selection: TableRowSelection | None = None
    row_action: TableRowAction | None = None
    cell_targets: Mapping[str, TableCellTarget] = field(default_factory=dict)
    comparison_scroll: bool = False
    #: Column that identifies a row, for pinning. Defaults to the row target's
    #: label column; set it explicitly when a table has an identity column that
    #: is not a link (a comparison table keyed by date, say).
    identity_column: str = ""
    #: Accessible name of the quick-filter chip group. Names what the chips
    #: filter by, so the group is not described as "status" on tables that
    #: filter by something else.
    quick_filter_label: str | Promise = ""
    search_mode: TableSearchMode = TableSearchMode.VISIBLE
    density: TableDensity = TableDensity.COMPACT
    wide_table: bool = False
    pin_identity_column: bool = False
    status_styles: Mapping[str, TableStatusStyle] = field(default_factory=dict)
    sticky_headers: bool = True
    show_cell_diffs: bool = False
    #: Per-column semantic tone, read per record: maps a column name to the
    #: record key holding a tone (``warning``, ``error``, …). A non-empty tone
    #: renders that cell's value in a status badge with an alert icon, so
    #: color never carries the meaning alone. Unlisted columns are unaffected.
    cell_tone_columns: Mapping[str, str] = field(default_factory=dict)
    #: STATUS column whose style supplies the row's background tone. The tone is
    #: read back out of ``status_styles``, never stored per row, so the tint and
    #: the row's own badge can never disagree. Empty disables row tinting.
    #:
    #: Keep the tone-carrying status column visible so its text or icon also
    #: communicates the meaning of the row color.
    row_tone_status_column: str = ""
    #: STATUS columns rendered as a bare icon with an accessible name instead of
    #: an icon plus its word. Only safe where the page carries a visible legend
    #: naming every value; without one the column cannot be decoded.
    icon_only_status_columns: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class TableTheme:
    """Presentation slots rendered inside the table's interactive controls."""

    status_badge: str = "django_tings/interactive_table/_status_badge.html"
    empty: str = "django_tings/interactive_table/_empty_state.html"
    action: str = "django_tings/interactive_table/_action.html"

    @classmethod
    def resolve(cls, override: Self | Mapping[str, str] | None) -> Self:
        if override is not None and not isinstance(override, Mapping):
            return override
        default = getattr(settings, "DJANGO_TINGS_TABLE_THEME", {})
        base = default if isinstance(default, cls) else cls(**default)
        return replace(base, **(override or {}))


DEFAULT_TABLE_DISPLAY = TableDisplay()


__all__ = [
    "DEFAULT_TABLE_DISPLAY",
    "ColumnKind",
    "QuickFilterFacet",
    "TableCellTarget",
    "TableDensity",
    "TableDisplay",
    "TableEmptyAction",
    "TableEmptyState",
    "TableMobileLayout",
    "TablePageTarget",
    "TableRowAction",
    "TableRowDetails",
    "TableRowSelection",
    "TableRowTarget",
    "TableSearchMode",
    "TableStatusStyle",
    "TableTheme",
    "record_value",
]
