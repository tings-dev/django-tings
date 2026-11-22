"""A small standalone consumer used by the installed-wheel browser checks."""

from dataclasses import replace

import django_tables2 as tables
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse
from django.template import engines
from django.urls import path

from django_tings.interactive_table import (
    ColumnKind,
    InteractiveTable,
    TableDisplay,
    TableMobileLayout,
    TablePage,
    TableRowDetails,
    TableRowSelection,
    TableStatusStyle,
    successful_table_response,
)


class Contacts(InteractiveTable):
    name = tables.Column()
    group = tables.Column()
    sortable_columns = ["name"]
    column_filters = {"group": "select"}
    default_page_size = 2
    display = TableDisplay(caption="Contacts", search_label="Search contacts")


async def directory(request):
    async def load_page(query):
        names = ["Atlas", "Axel", "Clark", "Clara", "Clarkson", "Daria"]
        records = [{"name": name, "group": "A"} for name in names] + [
            {"name": "Clark B", "group": "B"}
        ]
        matches = [
            row
            for row in records
            if query.search.casefold() in row["name"].casefold()
            and (
                not query.filters.get("group") or row["group"] in query.filters["group"]
            )
        ]
        matches.sort(key=lambda row: row["name"], reverse=query.sort == "-name")
        return TablePage(
            matches[query.page_slice(len(matches))],
            len(matches),
            choices={"group": ["A", "B"]},
        )

    review = request.GET.get("review") == "yes"
    display = (
        replace(
            Contacts.display,
            search_label="Search all active directory contacts by name",
            mobile=TableMobileLayout(
                "name", (), detail_columns=("group",), badge_column="group"
            ),
            column_kinds={"group": ColumnKind.STATUS},
            status_styles={
                "A": TableStatusStyle("Active", tone="success", icon="check")
            },
            row_details=TableRowDetails("name", value_column="name"),
            selection=TableRowSelection(
                "name",
                "name",
                action_label="Apply selection",
                action_url="/apply/",
                action_fields=(("scope", "approved"),),
            ),
        )
        if review
        else Contacts.display
    )

    async def create(instance):
        return await Contacts.for_request(
            request,
            load_page=load_page,
            instance_name=instance,
            display=display,
            config={"pagination_position": ("above", "below")}
            if "both" in request.GET
            else {},
            theme={"status_badge": "directory/badge.html"} if review else None,
        )

    if request.headers.get("Datastar-Request"):
        instance = request.headers.get("X-Table-Instance")
        if instance not in {"clients", "suppliers"}:
            return HttpResponse(status=404)
        table = await create(instance)
        return successful_table_response(table, request)

    page = engines["django"].from_string(
        """{% load django_tables2 i18n %}{% get_current_language as language %}<!doctype html><html lang="{{ language }}">
        <head><meta name="viewport" content="width=device-width,initial-scale=1">
        {% load static %}{% if host_runtime %}<script type="module" src="{% static 'django_tings/interactive_table/datastar-1.0.2.js' %}"></script>{% endif %}
        {% include 'django_tings/interactive_table/assets.html' with host_datastar=host_runtime %}</head>
        <body>
        <nav aria-label="Directory section">
          <a href="?tab=directory"{% if active_tab == "directory" %} aria-current="page"{% endif %}>Directory</a>
          <a href="?tab=review"{% if active_tab == "review" %} aria-current="page"{% endif %}>Review</a>
        </nav>
        {% render_table clients %}{% render_table suppliers %}
        </body></html>"""
    )
    return HttpResponse(
        page.render(
            {
                "clients": await create("clients"),
                "suppliers": await create("suppliers"),
                "active_tab": request.GET.get("tab", "directory"),
                "host_runtime": request.GET.get("host_runtime") == "yes",
            },
            request,
        )
    )


def bulk_action(request):
    keys = request.POST.getlist("selected")
    allowed = {"Atlas", "Axel", "Clark", "Clara", "Clarkson", "Daria", "Clark B"}
    if (
        request.method != "POST"
        or set(keys) - allowed
        or request.POST.get("scope") != "approved"
    ):
        return HttpResponse(status=403)
    return HttpResponse(",".join(keys) + " (approved)")


urlpatterns = [path("directory/", directory), path("apply/", bulk_action)]
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
