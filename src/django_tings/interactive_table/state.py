# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Markus Binsteiner

"""Canonical table state shared by ordinary navigation and live refreshes."""

from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal, Self
from urllib.parse import urlencode

from django.http import QueryDict

from .display import QuickFilterFacet

type FilterValue = str | Mapping[str, str]
type LoaderFilter = tuple[str, ...] | Mapping[str, str]


@dataclass(frozen=True, slots=True)
class TableRequestState:
    """Allowlisted filter, sorting, and pagination state from a query string."""

    filter_text: str = ""
    page: int = 1
    sort_column: str | None = None
    sort_direction: Literal["asc", "desc"] = "asc"
    column_filters: Mapping[str, FilterValue] = field(default_factory=dict)

    @classmethod
    def from_querydict(
        cls,
        query: QueryDict,
        *,
        sortable_columns: Collection[str],
        column_filter_names: Collection[str],
        prefix: str = "",
    ) -> Self:
        try:
            page = max(1, int(query.get(prefix + "page", "1")))
        except (TypeError, ValueError):
            page = 1
        sort = query.get(prefix + "sort")
        filters: dict[str, FilterValue] = {}
        for name in column_filter_names:
            key = f"{prefix}filter_{name}"
            kind = (
                column_filter_names.get(name)
                if isinstance(column_filter_names, Mapping)
                else None
            )
            is_range = kind in ("daterange", "date_range", "date-range")
            if not is_range:
                values = [v.strip() for v in query.getlist(key) if v.strip()]
                if values:
                    filters[name] = ",".join(values) if kind == "chips" else values[-1]
                    continue
            if is_range or kind is None:
                bounds = {
                    bound: value
                    for bound in ("start", "end")
                    if (value := query.get(f"{key}_{bound}", "").strip())
                }
                if bounds:
                    filters[name] = bounds
        return cls(
            filter_text=query.get(prefix + "q", "").strip(),
            page=page,
            sort_column=sort if sort in sortable_columns else None,
            sort_direction="desc"
            if query.get(prefix + "direction") == "desc"
            else "asc",
            column_filters=filters,
        )

    def parameters(self) -> dict[str, str]:
        values = {
            "q": self.filter_text,
            "page": str(self.page),
            "sort": self.sort_column or "",
            "direction": self.sort_direction if self.sort_column else "",
        }
        for key, value in self.column_filters.items():
            if isinstance(value, Mapping):
                values.update(
                    {f"filter_{key}_{bound}": item for bound, item in value.items()}
                )
            else:
                values[f"filter_{key}"] = value
        return values

    def query_string(self, **overrides: object) -> str:
        values = {**self.parameters(), **overrides}
        return urlencode(
            [(key, value) for key, value in values.items() if value not in ("", None)]
        )

    @property
    def has_active_filters(self) -> bool:
        return bool(self.filter_text or self.column_filters)


@dataclass(frozen=True, slots=True)
class TableQuery(TableRequestState):
    """Arguments supplied to the host's authorized loader."""

    page_size: int = 25
    filters: Mapping[str, LoaderFilter] = field(default_factory=dict)

    @property
    def search(self) -> str:
        return self.filter_text

    @property
    def sort(self) -> str:
        if self.sort_column and self.sort_direction == "desc":
            return f"-{self.sort_column}"
        return self.sort_column or ""

    def total_pages(self, total: int) -> int:
        return max(1, (total + self.page_size - 1) // self.page_size)

    def page_number(self, total: int) -> int:
        return min(max(1, self.page), self.total_pages(total))

    def page_slice(self, total: int) -> slice:
        """Slice the matches in their sorted order, including out-of-range requests."""
        start = (self.page_number(total) - 1) * self.page_size
        return slice(start, start + self.page_size)


@dataclass(frozen=True, slots=True)
class TablePage:
    """Authorized rows on the effective page and the full matching count."""

    rows: Sequence[Any]
    total: int
    choices: Mapping[str, Sequence[str]] = field(default_factory=dict)
    facets: Mapping[str, Mapping[str, int] | Sequence[QuickFilterFacet]] = field(
        default_factory=dict
    )
