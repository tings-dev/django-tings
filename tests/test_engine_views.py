"""A host uses one request-scoped loader for ordinary GETs and refreshes."""

from dataclasses import dataclass
from urllib.parse import parse_qs, urlsplit

import django_tables2 as tables
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, JsonResponse
from django.template import RequestContext, Template
from django.test import SimpleTestCase, override_settings
from django.urls import path, reverse_lazy

from django_tings.interactive_table import (
    InteractiveTable,
    TableDisplay,
    TableMobileLayout,
    TablePage,
    TableRowTarget,
)


class Directory(InteractiveTable):
    name = tables.Column()
    sortable_columns = ["name"]
    default_page_size = 2
    display = TableDisplay(caption="Directory")


async def directory(request):
    async def load_page(query):
        names = (
            ["Ada", "Alma", "Carl", "Dora"]
            if request.headers.get("Member")
            else ["Ada"]
        )
        matches = sorted(
            (name for name in names if query.search in name),
            reverse=query.sort == "-name",
        )
        return TablePage(
            [{"name": n} for n in matches[query.page_slice(len(matches))]], len(matches)
        )

    table = await Directory.for_request(request, load_page=load_page)
    return JsonResponse(
        {
            "names": [row.record["name"] for row in table.rows],
            "page": table.current_page,
            "total": table.total_count,
        }
    )


class MembersTable(Directory):
    sse_endpoint = reverse_lazy("members-refresh")
    office = tables.Column(orderable=False)
    handle = tables.Column(orderable=True)
    sortable_columns = ["name", "office"]


class Review(Directory):
    column_filters = {"status": "chips", "region": "select", "dated": "date_range"}
    quick_filter_column = "status"
    quick_filter_default = ("new",)


async def review(request, instance_name):
    async def load_page(query):
        return TablePage(
            [{"name": query.search, "extra": "kg"}],
            1,
            choices={"region": ["EU"]},
            facets={"status": {"new": 8, "old": 2}},
        )

    table = await Review.for_request(
        request,
        load_page=load_page,
        instance_name=instance_name,
        extra_columns=[("extra", tables.Column())],
        exclude=["name"],
        fixed_query={"source": "directory"},
        endpoint="/refresh/",
    )
    return JsonResponse(
        {
            "id": table.get_table_id(),
            "url": table.get_current_url(),
            "clear": table.get_clear_url(),
            "fields": table.form_context_fields,
            "columns": list(table.columns.names()),
            "filters": table.query.filters,
            "choices": table.get_column_filter_options(),
            "chips": [
                (chip["facet"].count, chip["active"])
                for chip in table.quick_filter_chips()
            ],
            "endpoint": table.get_sse_url(),
        }
    )


@dataclass
class Member:
    name: str
    slug: str | None = None


async def institution(request):
    from django_tings.interactive_table import table_sse_response_async

    async def load_page(query):
        if not request.headers.get("Member"):
            raise PermissionDenied
        if query.search == "fail":
            raise RuntimeError("private error")
        return TablePage(
            [Member(query.search or "Ada", "ada" if query.search == "Ada" else None)], 1
        )

    display = TableDisplay(
        caption="Members",
        mobile=TableMobileLayout(heading_column="name", summary_columns=("office",)),
        row_target=TableRowTarget(
            label_column="name", route_name="profile", route_fields={"slug": "slug"}
        ),
    )
    if request.headers.get("Datastar-Request"):
        return await table_sse_response_async(
            MembersTable,
            request,
            load_page=load_page,
            instance_name="staff",
            display=display,
        )
    table = await MembersTable.for_request(
        request, load_page=load_page, instance_name="staff", display=display
    )
    html = Template("{% load django_tables2 %}{% render_table table %}").render(
        RequestContext(request, {"table": table})
    )
    return HttpResponse(html)


urlpatterns = [
    path("directory/", directory),
    path("members/refresh/", institution, name="members-refresh"),
    path("profiles/<slug:slug>/", institution, name="profile"),
    path("institution/", institution),
    path("review/<slug:instance_name>/", review),
]


@override_settings(ROOT_URLCONF=__name__)
class DirectoryTests(SimpleTestCase):
    def test_last_matching_page_uses_only_visible_records(self):
        params = {"q": "a", "sort": "name", "direction": "desc", "page": 999}
        response = self.client.get("/directory/", params, headers={"Member": "yes"})
        self.assertEqual(
            response.json(), {"names": ["Alma", "Ada"], "page": 2, "total": 4}
        )
        public = self.client.get("/directory/", params)
        self.assertEqual(public.json(), {"names": ["Ada"], "page": 1, "total": 1})

    def test_instance_links_and_form_retain_other_tables_and_repeated_host_fields(self):
        response = self.client.get(
            "/review/a/?a-filter_status=new,old&a-filter_dated_start=2025-01-01"
            "&a-page=99&a-q=steel&b-page=3&tab=review&tag=x&tag=y"
        )
        page = response.json()
        self.assertEqual(page["id"], "a")
        self.assertEqual(page["columns"], ["extra"])
        self.assertEqual(page["filters"]["status"], ["new", "old"])
        self.assertEqual(page["filters"]["dated"], {"start": "2025-01-01"})
        self.assertEqual(page["choices"], {"region": ["EU"]})
        self.assertEqual(page["chips"], [[8, True], [2, True]])
        self.assertEqual(page["endpoint"], "/refresh/?source=directory")
        query = parse_qs(urlsplit(page["url"]).query)
        self.assertEqual(query["a-page"], ["1"])
        self.assertEqual(query["a-q"], ["steel"])
        self.assertEqual(
            parse_qs(urlsplit(page["clear"]).query),
            {"b-page": ["3"], "tab": ["review"], "tag": ["x", "y"]},
        )
        self.assertEqual(
            page["fields"],
            [["b-page", "3"], ["tab", "review"], ["tag", "x"], ["tag", "y"]],
        )

    def test_refresh_uses_the_same_table_context_as_normal_render(self):
        headers = {"Member": "yes"}
        initial = self.client.get("/institution/?staff-q=Ada", headers=headers)
        self.assertContains(initial, 'id="staff"')
        self.assertContains(initial, "Ada")
        live = self.client.get(
            "/institution/?staff-q=Alma&staff-page=99",
            headers={
                **headers,
                "Datastar-Request": "true",
                "X-Table-Path": "/institution/?tab=review",
            },
        )
        body = b"".join(live.streaming_content).decode()
        self.assertEqual(live.status_code, 200)
        self.assertIn("text/event-stream", live.headers["Content-Type"])
        self.assertEqual(body.count("event: datastar-patch-elements"), 1)
        self.assertIn('id="staff"', body)
        self.assertIn("Alma", body)
        self.assertIn("staff-page=1", body)
        self.assertIn("tab=review", body)

    def test_refresh_requires_host_authorization_and_hides_internal_error_details(self):
        denied = self.client.get("/institution/", headers={"Datastar-Request": "true"})
        self.assertEqual(denied.status_code, 403)
        failed = self.client.get(
            "/institution/?staff-q=fail",
            headers={"Member": "yes", "Datastar-Request": "true"},
        )
        self.assertEqual(failed.status_code, 500)
        body = b"".join(failed.streaming_content).decode()
        self.assertIn('id="staff-status"', body)
        self.assertNotIn("private error", body)

    def test_missing_row_target_renders_the_label_as_plain_text(self):
        response = self.client.get("/institution/", headers={"Member": "yes"})
        self.assertContains(response, "Ada")
        self.assertNotContains(response, "/profiles/")

    def test_object_record_links_return_to_the_named_table_and_host_tab(self):
        response = self.client.get(
            "/institution/?tab=one&staff-q=Ada", headers={"Member": "yes"}
        )
        self.assertContains(response, "/profiles/ada/?next=")
        self.assertContains(response, "staff-q%3DAda")
        self.assertContains(response, "tab%3Done")

    async def test_asgi_refresh_streams_the_result_to_async_consumers(self):
        response = await self.async_client.get(
            "/institution/?staff-q=Alma",
            headers={"Member": "yes", "Datastar-Request": "true"},
        )
        body = b"".join([part async for part in response.streaming_content])
        self.assertIn(b"Alma", body)

    def test_sort_links_match_column_declarations_on_desktop_and_mobile(self):
        response = self.client.get(
            "/institution/?staff-sort=office", headers={"Member": "yes"}
        )
        for layout in ("desktop", "mobile"):
            self.assertContains(response, f'data-table-focus-key="sort-{layout}-name"')
            self.assertNotContains(
                response, f'data-table-focus-key="sort-{layout}-office"'
            )
            self.assertNotContains(
                response, f'data-table-focus-key="sort-{layout}-handle"'
            )
        self.assertContains(response, 'aria-sort="ascending"')
        self.assertContains(response, "staff-sort=name&amp;staff-direction=desc")
        self.assertNotContains(response, "staff-sort=office")

    def test_named_refresh_endpoint_resolves_when_the_page_is_rendered(self):
        response = self.client.get("/institution/", headers={"Member": "yes"})
        self.assertContains(response, 'data-table-endpoint="/members/refresh/"')
