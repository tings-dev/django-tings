# How does an application supply rows and request context?

Type: prototype
Label: wayfinder:prototype
Status: resolved
Assignee: Codex

## Question

What is the smallest public interface for declaring columns and supplying a page of rows and its total count? Try the same API against a basic directory, a permissions-scoped detail view, an in-memory inspection table and an import preview with dynamic columns. Show how an application supplies filter options, quick-filter counts and defaults, hidden columns and fixed endpoint parameters. Preserve application control over row visibility and actions. Review concrete call sites with the maintainer.

## Prototype

Open the [interactive walkthrough](../prototype/data-api-prototype.html) or run the [Python prototype](../prototype/data_api.py) with `uv run --script data_api.py`. The examples exercise actual Django requests, SQLite queries and django-tables2 column binding. The walkthrough replays their results. The URL parser is illustrative pending [What state belongs to one table instance?](03-table-state.md).

The reviewed files are preserved on the local branch `prototype/table-data-api` at `699ba73`. Its 15 fixture requests cover Carbonsheet’s [directory](../../../../carbonsheet-django-tings/src/carbonsheet/base/tables/clients.py), [client detail](../../../../carbonsheet-django-tings/src/carbonsheet/base/tables/client_detail.py), [workspace inspection](../../../../carbonsheet-django-tings/src/carbonsheet/inspection/tables.py) and [import preview](../../../../carbonsheet-django-tings/src/carbonsheet/data_import/tables.py).

## Answer

The maintainer approved `await ContactsTable.for_request(request, load_page=load_page)`. The table declares its columns. The view supplies an async callable scoped to the authorized records for this request. That scope applies on initial render and refresh. The application enforces permissions on actions.

The loader receives a normalized `TableQuery` and returns `TablePage(rows, total)`. The total counts all matching rows before pagination. Given that total, `query.page_slice(total)` clamps the requested page so the rows and displayed page agree. The loader can also supply filter choices and facet counts from the authorized dataset. In the import preview, searching narrows the rows while preserving the status counts for the whole import.

The view may supply extra django-tables2 columns, excluded columns and fixed URL parameters per instance.
