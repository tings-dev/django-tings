# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Markus Binsteiner

"""Base class for interactive tables with Datastar integration."""

import inspect
import json
import re
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import replace
from functools import partial
from typing import Any, ClassVar, Self
from urllib.parse import urlencode, urlsplit

import django_tables2 as tables
from asgiref.sync import sync_to_async
from django.http import HttpRequest, QueryDict
from django.urls import reverse
from django.utils.functional import Promise
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext_lazy as _
from django_tables2.tables import TableOptions

from django_tings.interactive_table.display import (
    DEFAULT_TABLE_DISPLAY,
    ColumnKind,
    QuickFilterFacet,
    TableDisplay,
    TableSearchMode,
    TableTheme,
    record_value,
)
from django_tings.interactive_table.state import (
    LoaderFilter,
    TablePage,
    TableQuery,
    TableRequestState,
    canonical_filter_kind,
)


class InteractiveTable(tables.Table):
    """Declare columns and display options, then bind a loader with for_request()."""

    # Class attributes to be overridden by subclasses
    table_key: ClassVar[str] = ""
    table_id: ClassVar[str] = "interactive-table"
    filterable_columns: ClassVar[list[str]] = []
    sortable_columns: ClassVar[list[str]] = []
    column_filters: ClassVar[dict[str, str]] = {}  # e.g., {"status": "select"}
    # A "chips"-type column filter rendered as count chips above the toolbar.
    quick_filter_column: ClassVar[str | None] = None
    # Values selected when the request carries no explicit quick-filter state.
    quick_filter_default: ClassVar[tuple[str, ...]] = ()
    sse_endpoint: ClassVar[str | Promise] = ""
    sse_fixed_query: ClassVar[Mapping[str, str]] = {}
    default_page_size: ClassVar[int] = 25
    static_height: ClassVar[bool] = True
    display: ClassVar[TableDisplay] = DEFAULT_TABLE_DISPLAY
    _meta: ClassVar[TableOptions]
    base_columns: ClassVar[Mapping[str, tables.Column]]
    _truncate_cells: ClassVar[bool] = (
        True  # Whether to truncate cell content to a single line
    )

    # Pagination configuration
    # Position: tuple of "above", "below", or both
    pagination_position: ClassVar[tuple[str, ...]] = ("below",)
    # Alignment for each position: "left", "center", or "right"
    pagination_alignment_above: ClassVar[str] = "center"
    pagination_alignment_below: ClassVar[str] = "center"

    # Instance attributes resolved by the table factory.
    available_sort_columns: Sequence[str]
    theme: TableTheme
    query: TableQuery
    page_data: TablePage
    instance_name: str
    query_prefix: str
    current_page: int
    total_pages: int
    total_count: int
    filter_text: str
    sort_column: str | None
    sort_direction: str
    column_filter_values: dict[str, Any]
    page_size: int
    current_row_count: int
    _config: dict[str, Any]  # Resolved config values (class defaults + overrides)
    _column_filter_options: dict[str, list[str]]
    request_state: TableRequestState
    empty_action_url: str | None
    quick_filter_facets: list[QuickFilterFacet]

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        cls.column_filters = {
            name: canonical_filter_kind(kind)
            for name, kind in cls.column_filters.items()
        }

    class Meta:
        template_name = "django_tings/interactive_table/table.html"

    @classmethod
    async def _fetch_data(
        cls,
        *,
        filter_text: str = "",
        sort_column: str | None = None,
        sort_direction: str = "asc",
        page: int = 1,
        page_size: int = 25,
        column_filters: dict[str, Any] | None = None,
        user: Any | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """Fetch filtered, sorted, paginated data from the database asynchronously.

        Subclasses must implement this to perform filtering, sorting, and pagination
        at the database level rather than in Python memory.

        Args:
            filter_text: Text to filter by (searches filterable_columns)
            sort_column: Column to sort by (None for default sorting)
            sort_direction: 'asc' or 'desc'
            page: 1-indexed page number
            page_size: Number of rows per page
            column_filters: Dict of column-specific filters
            user: Authenticated user used by authorization-aware tables

        Returns:
            Tuple of (rows for current page, total count matching filters)
        """
        raise NotImplementedError

    @classmethod
    async def _fetch_distinct_values(
        cls,
        column: str,
        *,
        user: Any | None = None,
    ) -> list[str]:
        """Fetch distinct values for a column from the database asynchronously.

        Override this method to provide efficient database-level distinct queries
        for select-type column filters.

        Args:
            column: The column name to get distinct values for
            user: The actor whose visible rows supply the choices

        Returns:
            Sorted list of unique string values for the column
        """
        # Default implementation fetches a page of data and extracts values
        # Subclasses should override for better efficiency
        rows, _ = await cls._call_fetch_data(page_size=1000, user=user)
        values = set()
        for row in rows:
            value = row.get(column)
            if value is not None:
                values.add(str(value))
        return sorted(values)

    @classmethod
    async def get_filter_options(
        cls,
        column: str,
        *,
        user: Any | None = None,
    ) -> list[str]:
        """Get unique values for a select-type filter column asynchronously.

        Args:
            column: The column name to get options for
            user: The actor whose visible rows supply the choices

        Returns:
            Sorted list of unique string values for the column
        """
        return await cls._fetch_distinct_values(column, user=user)

    @classmethod
    async def _fetch_column_filter_options(
        cls,
        *,
        user: Any | None = None,
    ) -> dict[str, list[str]]:
        """Fetch options for all select-type column filters."""
        options = {}
        for column, filter_type in cls.column_filters.items():
            if filter_type == "select":
                options[column] = await cls.get_filter_options(column, user=user)
        return options

    @classmethod
    async def _fetch_quick_filter_facets(
        cls,
        *,
        user: Any | None = None,
    ) -> list[QuickFilterFacet]:
        """Fetch value/label/count facets for the quick-filter chip strip.

        Tables declaring ``quick_filter_column`` override this; counts are
        expected to ignore search text so the chips stay at-a-glance numbers.
        """
        _ = user
        return []

    @classmethod
    def quick_filter_selection(
        cls, column_filters: Mapping[str, Any] | None
    ) -> tuple[str, ...]:
        """Resolve the active quick-filter values, falling back to the default."""
        if not cls.quick_filter_column:
            return ()
        raw = (column_filters or {}).get(cls.quick_filter_column)
        if isinstance(raw, str):
            values = tuple(part.strip() for part in raw.split(",") if part.strip())
            if values:
                return values
        return tuple(cls.quick_filter_default)

    @classmethod
    async def _call_fetch_data(cls, **kwargs: Any) -> tuple[list[dict[str, Any]], int]:
        """Call subclass fetchers while tolerating older test helper signatures."""
        signature = inspect.signature(cls._fetch_data)
        if "user" not in signature.parameters and not any(
            parameter.kind is inspect.Parameter.VAR_KEYWORD
            for parameter in signature.parameters.values()
        ):
            kwargs.pop("user", None)
        return await cls._fetch_data(**kwargs)

    @classmethod
    async def load_page(
        cls, query: TableQuery, *, user: Any | None = None
    ) -> TablePage:
        """Adapt class-based data sources to the view-supplied loader interface."""
        kwargs = dict(
            filter_text=query.search,
            sort_column=query.sort_column,
            sort_direction=query.sort_direction,
            page_size=query.page_size,
            column_filters=dict(query.column_filters),
            user=user,
        )
        rows, total = await cls._call_fetch_data(page=query.page, **kwargs)
        effective = query.page_number(total)
        if effective != query.page and not rows and total:
            rows, total = await cls._call_fetch_data(page=effective, **kwargs)
        choices = await cls._fetch_column_filter_options(user=user)
        facets = {}
        if cls.quick_filter_column:
            facets[cls.quick_filter_column] = await cls._fetch_quick_filter_facets(
                user=user
            )
        return TablePage(rows, total, choices, facets)

    @classmethod
    def _sortable_fields(
        cls,
        hidden: Sequence[str],
        extra_columns: Sequence[tuple[str, tables.Column]] = (),
    ) -> tuple[str, ...]:
        columns = {**cls.base_columns, **dict(extra_columns)}
        return tuple(
            name
            for name in cls.sortable_columns
            if name not in hidden
            and (column := columns.get(name)) is not None
            and (cls._meta.orderable if column.orderable is None else column.orderable)
        )

    @classmethod
    async def for_request(
        cls,
        request: HttpRequest,
        *,
        load_page: Callable[[TableQuery], Awaitable[TablePage]],
        instance_name: str = "",
        display: TableDisplay | None = None,
        theme: TableTheme | Mapping[str, str] | None = None,
        extra_columns: Sequence[tuple[str, tables.Column]] = (),
        exclude: Sequence[str] = (),
        fixed_query: Mapping[str, str] | None = None,
        endpoint: str | Promise | None = None,
        page_url: str | Promise | None = None,
        page_size: int | None = None,
        config: Mapping[str, Any] | None = None,
        user: Any | None = None,
    ) -> Self:
        """Load an instance scoped to this request and its host-provided data source."""
        if instance_name and not re.fullmatch(r"[a-zA-Z0-9_-]+", instance_name):
            raise ValueError("instance_name must be a slug")
        hidden = tuple(
            dict.fromkeys((*cls.hidden_column_names(), *exclude, *cls._meta.exclude))
        )
        sortable = cls._sortable_fields(hidden, extra_columns)
        state = TableRequestState.from_querydict(
            request.GET,
            sortable_columns=sortable,
            column_filter_names=cls.column_filters,
            prefix=f"{instance_name}-" if instance_name else "",
        )
        return await cls._from_state(
            state,
            load_page=load_page,
            request=request,
            instance_name=instance_name,
            display=display,
            theme=theme,
            extra_columns=extra_columns,
            exclude=hidden,
            fixed_query=fixed_query,
            endpoint=endpoint,
            page_url=page_url,
            page_size=page_size,
            config=config,
            user=user,
            sortable=sortable,
        )

    @classmethod
    async def create_for_request(
        cls,
        request: HttpRequest,
        *,
        user: Any | None = None,
        config: Mapping[str, Any] | None = None,
        **options: Any,
    ) -> Self:
        """Bind a class-based data source to the authorized request user."""
        if user is None:
            user = (
                await request.auser()
                if hasattr(request, "auser")
                else getattr(request, "user", None)
            )
        return await cls.for_request(
            request,
            load_page=partial(cls.load_page, user=user),
            user=user,
            config=config,
            **options,
        )

    @classmethod
    async def create_current(
        cls,
        filter_text: str = "",
        page: int = 1,
        page_size: int | None = None,
        sort_column: str | None = None,
        sort_direction: str = "asc",
        column_filters: dict[str, Any] | None = None,
        config: dict[str, Any] | None = None,
        user: Any | None = None,
    ) -> Self:
        """Construct a class-based table for callers providing already parsed state."""
        hidden = cls.hidden_column_names()
        sortable = cls._sortable_fields(hidden)
        state = TableRequestState(
            filter_text,
            max(1, page),
            sort_column if sort_column in sortable else None,
            "desc" if sort_direction == "desc" else "asc",
            {
                k: v
                for k, v in (column_filters or {}).items()
                if k in cls.column_filters
            },
        )
        return await cls._from_state(
            state,
            load_page=partial(cls.load_page, user=user),
            request=None,
            config=config,
            page_size=page_size,
            user=user,
            exclude=hidden,
            sortable=sortable,
        )

    @classmethod
    async def _from_state(
        cls,
        state: TableRequestState,
        *,
        load_page: Callable[[TableQuery], Awaitable[TablePage]],
        request: HttpRequest | None,
        sortable: Sequence[str],
        exclude: Sequence[str],
        instance_name: str = "",
        display: TableDisplay | None = None,
        theme: TableTheme | Mapping[str, str] | None = None,
        extra_columns: Sequence[tuple[str, tables.Column]] = (),
        fixed_query: Mapping[str, str] | None = None,
        endpoint: str | Promise | None = None,
        page_url: str | Promise | None = None,
        page_size: int | None = None,
        config: Mapping[str, Any] | None = None,
        user: Any | None = None,
    ) -> Self:
        config = config or {}
        size = (
            page_size
            if page_size is not None
            else config.get("page_size", cls.default_page_size)
        )
        if not isinstance(size, int) or size < 1:
            raise ValueError("page_size must be a positive integer")
        if not state.sort_column and sortable:
            default = getattr(cls, "default_sort_column", sortable[0])
            state = replace(
                state,
                sort_column=default if default in sortable else None,
                sort_direction=getattr(
                    cls, "default_sort_direction", state.sort_direction
                ),
            )
        filters: dict[str, LoaderFilter] = {}
        for name, kind in cls.column_filters.items():
            value = state.column_filters.get(name)
            if kind == "chips":
                filters[name] = cls.quick_filter_selection(state.column_filters)
            elif isinstance(value, str):
                filters[name] = (value,)
            elif kind == "daterange":
                filters[name] = value or {}
            elif value is not None:
                filters[name] = value
            else:
                filters[name] = ()
        query = TableQuery(
            state.filter_text,
            state.page,
            state.sort_column,
            state.sort_direction,
            state.column_filters,
            size,
            filters,
        )
        result = await load_page(query)
        if result.total < 0:
            raise ValueError("TablePage.total must be nonnegative")
        # django-tables2 2.x resets Meta defaults for subclasses without Meta.
        template = getattr(
            cls.Meta, "template_name", InteractiveTable.Meta.template_name
        )
        table = cls(
            result.rows,
            exclude=exclude,
            extra_columns=extra_columns,
            template_name=template,
        )
        table.available_sort_columns = sortable
        # Host subclasses declare the default once. A request may shadow it on
        # this instance without changing the declaration used by another user.
        if display is not None:
            table.display = display  # pyrefly: ignore[read-only]  # ty: ignore[invalid-attribute-access]
        table.theme = TableTheme.resolve(theme)
        table._validate_display()
        table.query, table.page_data = query, result
        table.current_page = query.page_number(result.total)
        table.total_pages = query.total_pages(result.total)
        table.total_count = result.total
        table.current_row_count = len(result.rows)
        table.page_size = size
        table.filter_text, table.sort_column, table.sort_direction = (
            state.filter_text,
            state.sort_column,
            state.sort_direction,
        )
        table.column_filter_values = dict(state.column_filters)
        table._column_filter_options = {
            name: list(options) for name, options in result.choices.items()
        }
        facets = result.facets.get(cls.quick_filter_column or "", ())
        table.quick_filter_facets = (
            [QuickFilterFacet(key, key, count) for key, count in facets.items()]
            if isinstance(facets, Mapping)
            else list(facets)
        )
        table.request_state = replace(state, page=table.current_page)
        table.instance_name = instance_name
        table.query_prefix = f"{instance_name}-" if instance_name else ""
        table._config = {
            "table_id": instance_name or config.get("table_id") or cls.table_id,
            "page_size": size,
            "static_height": config.get("static_height", cls.static_height),
            "pagination_position": config.get(
                "pagination_position", cls.pagination_position
            ),
            "pagination_alignment_above": config.get(
                "pagination_alignment_above", cls.pagination_alignment_above
            ),
            "pagination_alignment_below": config.get(
                "pagination_alignment_below", cls.pagination_alignment_below
            ),
            "truncate_cells": config.get("truncate_cells", cls._truncate_cells),
        }
        table._set_navigation(request, page_url, endpoint, fixed_query)
        if user is None and request is not None and table.display.empty.action:
            user = (
                await request.auser()
                if hasattr(request, "auser")
                else getattr(request, "user", None)
            )
        table.empty_action_url = await table._resolve_empty_action_url(user)
        return table

    @classmethod
    def hidden_column_names(cls) -> tuple[str, ...]:
        """Columns excluded from this deployment's rendering."""
        return ()

    @classmethod
    def effective_filterable_columns(cls) -> tuple[str, ...]:
        """The free-text search columns, minus any hidden ones."""
        hidden = set(cls.hidden_column_names())
        return tuple(
            column for column in cls.filterable_columns if column not in hidden
        )

    @classmethod
    def identity_column_name(cls) -> str:
        """The column that identifies a row, whether or not it is a link."""
        if cls.display.identity_column:
            return cls.display.identity_column
        target = cls.display.row_target
        return target.label_column if target is not None else ""

    def get_identity_column(self) -> str:
        """Template accessor for :meth:`identity_column_name`."""
        return self.display.identity_column or (
            self.display.row_target.label_column if self.display.row_target else ""
        )

    def _validate_display(self) -> None:
        if not self.display.pin_identity_column:
            return
        if self.get_identity_column() not in self.columns.names():
            raise ValueError(
                "pin_identity_column requires display.identity_column (or "
                "row_target.label_column) to name a declared table column"
            )

    async def _resolve_empty_action_url(self, user: Any | None) -> str | None:
        """Resolve the empty-state action after its permission check."""
        action = self.display.empty.action
        if action is None:
            return None
        if action.permission:
            if user is None:
                return None
            allowed = False
            async_checker = getattr(user, "ahas_perm", None)
            if callable(async_checker):
                # `async_checker` is resolved dynamically and typed `object`; it is
                # always the async permission checker.
                # pyrefly: ignore [not-async]
                allowed = await async_checker(action.permission)

            # Rules supplies a synchronous backend, which Django's native
            # async permission loop does not consult.
            if not allowed:
                checker = getattr(user, "has_perm", None)
                if not callable(checker):
                    return None
                allowed = await sync_to_async(checker, thread_sensitive=True)(
                    action.permission
                )
            if not allowed:
                return None

        base = reverse(action.route_name, kwargs=dict(action.route_kwargs))
        query = dict(action.query)
        if action.preserve_return:
            query["next"] = self._state_url()
        return f"{base}?{urlencode(query)}" if query else base

    def _set_navigation(
        self,
        request: HttpRequest | None,
        page_url: str | Promise | None,
        endpoint: str | Promise | None,
        fixed_query: Mapping[str, str] | None,
    ) -> None:
        # A separate refresh endpoint carries its own routing parameters. The
        # initiating page supplies its local URL to reconstruct sibling state.
        location = request.get_full_path() if request else ""
        page_header = request.headers.get("X-Table-Path", "") if request else ""
        if page_header.startswith("/") and url_has_allowed_host_and_scheme(
            page_header, allowed_hosts=set()
        ):
            location = page_header
        source = urlsplit(location)
        page_target = self.display.page
        target = page_url or (
            reverse(page_target.route_name, kwargs=dict(page_target.route_kwargs))
            if page_target
            else source.path
        )
        base = urlsplit(str(target))
        self._page_path = base.path
        self._endpoint = str(endpoint or self.sse_endpoint or self._page_path)
        self.fixed_query = {**self.endpoint_query(), **(fixed_query or {})}
        context = QueryDict(source.query, mutable=True)
        for name in self.query_keys.split():
            context.pop(name, None)
        context.pop("datastar", None)
        if not page_header and source.path == urlsplit(self._endpoint).path:
            for name in self.fixed_query:
                context.pop(name, None)
        if page_target:
            for key, val in page_target.fixed_query.items():
                context[key] = val
        for key, values in QueryDict(base.query).lists():
            context.setlist(key, values)
        self._page_context = context

    @property
    def query_keys(self) -> str:
        keys = ["q", "page", "sort", "direction"]
        for name, kind in self.column_filters.items():
            if kind == "daterange":
                keys.extend((f"filter_{name}_start", f"filter_{name}_end"))
            else:
                keys.append(f"filter_{name}")
        return " ".join(self.query_prefix + key for key in keys)

    @property
    def form_context_fields(self) -> list[tuple[str, str]]:
        pairs = [
            (key, value)
            for key, values in self._page_context.lists()
            for value in values
        ]
        if self.sort_column:
            pairs += [
                (self.query_prefix + "sort", self.sort_column),
                (self.query_prefix + "direction", self.sort_direction),
            ]
        return pairs

    def get_page_url(self) -> str:
        return self._url(self._page_context)

    def _url(self, params: QueryDict) -> str:
        query = params.urlencode()
        return f"{self._page_path}?{query}" if query else self._page_path

    def _navigation_url(self, state: TableRequestState, **overrides: object) -> str:
        params = self._page_context.copy()
        owned = set(self.query_keys.split())
        for name, value in {**state.parameters(), **overrides}.items():
            key = (
                self.query_prefix + name if self.query_prefix + name in owned else name
            )
            if value not in ("", None):
                params[key] = str(value)
            else:
                params.pop(key, None)
        return self._url(params)

    def get_clear_url(self) -> str:
        cleared = TableRequestState(
            sort_column=self.request_state.sort_column,
            sort_direction=self.request_state.sort_direction,
        )
        return self._navigation_url(cleared, page="")

    def _state_url(self, **overrides: object) -> str:
        return self._navigation_url(self.request_state, **overrides)

    def get_current_url(self) -> str:
        return self._state_url()

    def sort_url(self, column_name: str) -> str:
        """Return the canonical URL for the next direction of a sortable column."""
        current = self.request_state
        next_direction = (
            "desc"
            if current.sort_column == column_name and current.sort_direction == "asc"
            else "asc"
        )
        return self._state_url(
            page=1,
            sort=column_name,
            direction=next_direction,
        )

    def page_url(self, page: int) -> str:
        """Return the canonical URL for a clamped result page."""
        return self._state_url(page=max(1, min(page, self.total_pages)))

    def aria_sort(self, column_name: str) -> str:
        """Return the ARIA sort state for a column header."""
        if self.request_state.sort_column != column_name:
            return "none"
        return (
            "descending" if self.request_state.sort_direction == "desc" else "ascending"
        )

    def column_kind(self, column_name: str) -> str:
        """Return the declared semantic display kind for a column."""
        kind = self.display.column_kinds.get(column_name, ColumnKind.TEXT)
        return kind.value if isinstance(kind, ColumnKind) else str(kind)

    def column_sublabel(self, column_name: str) -> str:
        """Return the declared measurement unit for a column, or ``""``."""
        return str(self.display.column_sublabels.get(column_name, ""))

    def row_tone(self, record: object) -> str:
        """Return the row's background tone, or ``""`` when none applies.

        Derived from the tone-carrying status column's own style rather than a
        value on the record, so a row can never be tinted one rung and badged
        another.
        """
        column = self.display.row_tone_status_column
        if not column:
            return ""
        style = self.display.status_styles.get(str(record_value(record, column, "")))
        return style.tone if style else ""

    def status_is_icon_only(self, column_name: str) -> bool:
        """Whether a STATUS column renders as an icon without its word."""
        return column_name in self.display.icon_only_status_columns

    @property
    def column_span(self) -> int:
        """Rendered desktop column count, including selection and action cells."""
        return (
            len(self.columns)
            + (1 if self.display.selection else 0)
            + (1 if self.display.row_action else 0)
        )

    def get_table_id(self) -> str:
        """Return the table's unique ID for DOM targeting."""
        return self._config.get("table_id", self.table_id)

    def get_table_key(self) -> str:
        """Return the stable key used by the generic SSE endpoint."""
        return self.table_key

    @classmethod
    def endpoint_query(cls) -> Mapping[str, str]:
        """Fixed, host-owned parameters for routing a table refresh."""
        return cls.sse_fixed_query

    def get_sse_endpoint(self) -> str:
        """Return the SSE endpoint URL for this table."""
        return self._endpoint

    def get_sse_url(self) -> str:
        """Return the SSE endpoint with table-specific fixed request context."""
        endpoint = self.get_sse_endpoint()
        parts = urlsplit(endpoint)
        query = QueryDict(parts.query, mutable=True)
        for name, value in self.fixed_query.items():
            query[name] = value
        return parts._replace(query=query.urlencode()).geturl()

    def get_column_filter_options(self) -> dict[str, list[str]]:
        """Get filter options for all select-type column filters.

        Returns:
            Dict mapping column names to lists of options
        """
        return getattr(self, "_column_filter_options", {})

    @property
    def empty_rows_count(self) -> int:
        """Calculate number of empty rows needed to maintain static height."""
        static_height = self._config.get("static_height", self.static_height)
        if not static_height:
            return 0
        visible_rows = self.current_row_count if self.current_row_count else 1
        return max(0, self.page_size - visible_rows)

    @property
    def empty_rows_range(self) -> range:
        """Return a range object for iterating empty rows in templates."""
        return range(self.empty_rows_count)

    def get_pagination_position(self) -> tuple[str, ...]:
        """Return pagination position configuration for template access."""
        return self._config.get(
            "pagination_position", self.__class__.pagination_position
        )

    def get_pagination_alignment_above(self) -> str:
        """Return pagination alignment for above position."""
        return self._config.get(
            "pagination_alignment_above", self.__class__.pagination_alignment_above
        )

    def get_pagination_alignment_below(self) -> str:
        """Return pagination alignment for below position."""
        return self._config.get(
            "pagination_alignment_below", self.__class__.pagination_alignment_below
        )

    def get_search_mode(self) -> str:
        return self.display.search_mode.value

    def get_density(self) -> str:
        return self.display.density.value

    def get_has_toolbar_controls(self) -> bool:
        return (
            self.display.search_mode is not TableSearchMode.HIDDEN
            or self.get_column_filter_count() > 0
            or self.request_state.has_active_filters
        )

    def get_has_configured_toolbar_controls(self) -> bool:
        """Return whether the toolbar has controls independent of request state."""
        return (
            self.display.search_mode is not TableSearchMode.HIDDEN
            or self.get_column_filter_count() > 0
        )

    def get_column_filter_count(self) -> int:
        """Count column filters rendered inside the toolbar disclosure."""
        return sum(
            1 for filter_type in self.column_filters.values() if filter_type != "chips"
        )

    def get_active_column_filter_count(self) -> int:
        return sum(
            bool(value) if not isinstance(value, Mapping) else any(value.values())
            for name, value in self.request_state.column_filters.items()
            if self.column_filters.get(name) != "chips"
        )

    def get_quick_filter_label(self) -> str | Promise:
        """Accessible name for the quick-filter chip group."""
        return self.display.quick_filter_label or _("Filter rows")

    def get_quick_filter_value(self) -> str:
        """Return the raw quick-filter request value ('' when at the default)."""
        if not self.quick_filter_column:
            return ""
        raw = self.request_state.column_filters.get(self.quick_filter_column)
        return raw if isinstance(raw, str) else ""

    def quick_filter_chips(self) -> list[dict[str, Any]]:
        """Chip rendering state: each facet with its toggled next selection.

        Toggling never empties the selection — the last active chip keeps
        itself — so the table always has a defined, linkable filter state.
        """
        column = self.quick_filter_column
        if not column or not self.quick_filter_facets:
            return []
        order = [facet.value for facet in self.quick_filter_facets]
        active = {
            value
            for value in self.quick_filter_selection(self.request_state.column_filters)
            if value in order
        }
        chips: list[dict[str, Any]] = []
        for facet in self.quick_filter_facets:
            next_values = [
                value for value in order if (value in active) != (value == facet.value)
            ]
            if not next_values:
                next_values = [facet.value]
            next_value = ",".join(next_values)
            chips.append(
                {
                    "facet": facet,
                    "active": facet.value in active,
                    "next_value": next_value,
                    "url": self._state_url(page=1, **{f"filter_{column}": next_value}),
                }
            )
        return chips

    @property
    def truncate_cells(self) -> bool:
        """Return whether to truncate cell content to a single line."""
        # Use getattr to safely check for _config (e.g. if accessed before create_current finishes)
        config = getattr(self, "_config", {})
        return config.get("truncate_cells", self.__class__._truncate_cells)

    def get_config_json(self) -> str:
        """Return config as JSON for embedding in Datastar signals.

        Uses single quotes for strings to be compatible with Datastar's
        signal syntax inside HTML attributes (which use double quotes).
        Keys are sorted for consistent ordering (important for caching).
        """
        # sort_keys=True ensures consistent ordering for cache-friendly URLs
        json_str = json.dumps(self._config, sort_keys=True)
        # Replace double quotes with single quotes for Datastar compatibility
        return json_str.replace('"', "'")
