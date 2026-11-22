# Interactive tables

A table definition declares which columns and controls a page offers. Its view supplies an async loader for the current user's records. Both ordinary navigation and live refresh call that loader, so a bookmarked URL describes the same dataset the user saw while typing.

## A searchable directory

Add `django_tables2` and `django_tings.interactive_table` to `INSTALLED_APPS`, enable app template discovery, and include Django's request context processor. This example assumes a `Contact` model with `owner`, `name` and `city` fields. Point `path("contacts/", contacts, name="contacts")` at the following view.

```python
import django_tables2 as tables
from asgiref.sync import sync_to_async
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils.translation import gettext_lazy as _

from django_tings.interactive_table import (
    InteractiveTable,
    TableDisplay,
    TablePage,
    TableQuery,
    table_sse_response_async,
)

from .models import Contact


class ContactsTable(InteractiveTable):
    name = tables.Column(verbose_name=_("Name"))
    city = tables.Column(verbose_name=_("City"))
    filterable_columns = ["name"]
    sortable_columns = ["name", "city"]
    default_sort_column = "name"
    column_filters = {"city": "select"}
    display = TableDisplay(caption=_("Contacts"), search_label=_("Search contacts"))


@login_required
async def contacts(request):
    owner = await request.auser()

    async def load_page(query: TableQuery) -> TablePage:
        allowed = Contact.objects.filter(owner_id=owner.pk)
        cities = allowed.order_by("city").values_list("city", flat=True).distinct()
        matches = allowed.filter(name__icontains=query.search)
        if selected := query.filters.get("city"):
            matches = matches.filter(city__in=selected)
        total = await matches.acount()
        records = matches.order_by(query.sort or "name", "pk").values("name", "city")
        return TablePage(
            rows=[row async for row in records[query.page_slice(total)]],
            total=total,
            choices={"city": [city async for city in cities]},
        )

    if request.headers.get("Datastar-Request"):
        return await table_sse_response_async(
            ContactsTable, request, load_page=load_page
        )
    table = await ContactsTable.for_request(request, load_page=load_page)
    return await sync_to_async(render)(request, "contacts.html", {"table": table})
```

Apply the application's access policy before loading the table. The loader's authorized dataset determines what a user can search, count or select. Check that same scope when processing submitted record keys.

```django
{% load django_tables2 %}
{% include "django_tings/interactive_table/assets.html" %}
{% render_table table %}
```

Include the assets once per page. Pass `host_datastar=True` to the include when the shell already supplies its Datastar runtime. The default stylesheet and packaged German translations need no frontend build.

## Queries and loaders

The request uses `q`, `page`, `sort`, `direction` and `filter_<column>`. Declare sortable names and handle their values in the loader. `query.sort` is a signed ORM order such as `-name`. `query.sort_column` and `query.sort_direction` are also available. The same loader works with a list by sorting and filtering it, counting the matches and returning `TablePage(matches[query.page_slice(total)], total)`. Compute the count before slicing so a request beyond the last page can display that page immediately.

| Control | Declaration | Loader input and result |
| --- | --- | --- |
| Select | `column_filters = {"city": "select"}` | Read a tuple of selected values from `query.filters`. Supply available values in `TablePage.choices`. |
| Date interval | `column_filters = {"created": "daterange"}` | Read the supplied `start` and `end` string bounds from `query.filters.get("created", {})`. Parse dates according to the host's data policy. The GET names are `filter_created_start` and `filter_created_end`. |
| Quick-filter chips | `column_filters = {"status": "chips"}`, `quick_filter_column = "status"` | Read the selected values from `query.filters`. Supply counts in `TablePage.facets`, keyed by column then status, or supply a sequence of `QuickFilterFacet` objects with labels, tones and icons. Set `quick_filter_default` for the initial selection. |

Compute facet counts over the appropriate authorized dataset, independently of the filtered match count. For staged records, discover the columns within the authorized session and pass `extra_columns=[("field_name", tables.Column(...))]` and, as needed, `exclude=(... ,)` to `for_request`. Use the same options when handling the refresh.

## More than one table

Give every independently navigable table on a page a stable slug in `instance_name`, including tables in separate tab panels. It scopes the DOM ID and URL parameter names. For example, `?clients-q=steel&suppliers-page=4&tab=review` restores the clients search, the fourth supplier page and the host's active tab. Use ordinary GET for the containing page. Use the same view or a dedicated refresh `endpoint=` for each instance. With a shared endpoint, dispatch using an allowlist of permitted instances from the route and the `X-Table-Instance` header. Reapply authentication and dataset scope before loading.

`page_url=` supplies the containing page when its path differs from the refresh path. `fixed_query=` adds server-chosen endpoint parameters, for example an import category. A `TablePageTarget` on the display can resolve a Django route with its fixed page parameters. Validate route identifiers against the current user every time.

Typing pauses for 300 ms before the table searches. Search replaces the current history entry. Page, sort, chip and Clear clicks add entries when the refresh succeeds. The input stays editable after a failed request and Retry repeats the attempted operation. The GET form and navigation links remain usable with JavaScript disabled.

## Configure a table

| Need | Configuration |
| --- | --- |
| Search, size and paging | Set `TableDisplay.search_mode` to visible, collapsed or hidden. Set `default_page_size` or pass `page_size=` per instance. Use `pagination_position`, `pagination_alignment_above`, `pagination_alignment_below`, and `static_height` on the class. |
| Desktop and mobile presentation | Set `density`, `sticky_headers`, `wide_table`, `comparison_scroll`, `identity_column` and `pin_identity_column` on the display. Set `column_kinds` and `column_sublabels` for numeric fields and units. Supply a `TableMobileLayout` to choose each card's heading, badge, summary and details. |
| Navigate or act on a record | Configure `row_target`, `cell_targets`, `row_details` or `row_action`. Targets resolve Django routes from declared record fields. Row actions can supply a disabled reason from the record or omit an action if its value is missing. |
| Selection and review | Set `TableDisplay.selection` to a `TableRowSelection` with record fields for the key and label, an action URL and optional form fields. The scoped selection persists across live paging and filtering. Configure status labels, per-row and per-cell styles and cell differences on the display. |
| Empty and filtered results | Set `TableEmptyState` with separate headings and descriptions for an empty dataset and an empty search. A `TableEmptyAction` can declare a Django permission and route. |
| Project branding | Supply a project-wide theme with `DJANGO_TINGS_TABLE_THEME`, or pass `theme=` for a single instance. Use `display=` to supply request-specific presentation metadata. See the [theme reference](table-theme.md) for CSS variables and template contexts. |
