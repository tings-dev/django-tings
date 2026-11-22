"""Smoke-test a wheel in an isolated Django consumer."""

from importlib import import_module
from importlib.metadata import distribution
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from unittest import TestCase, main

from django import conf, setup
from django.core.management import call_command
from django.http import HttpResponse
from django.template import engines
from django.template.loader import get_template
from django.test import Client
from django.test.utils import override_settings
from django.urls import path
from django.utils.translation import gettext, ngettext, override

ASSETS = "django_tings/interactive_table"


async def directory(request):
    import django_tables2 as tables
    from asgiref.sync import sync_to_async

    from django_tings.interactive_table import (
        InteractiveTable,
        TablePage,
        render_table_fragment,
        table_sse_response_async,
    )

    class Directory(InteractiveTable):
        name = tables.Column()
        filterable_columns = ["name"]

    async def load_page(query):
        matches = [
            {"name": name}
            for name in ("Ada", "Grace")
            if query.search.casefold() in name.casefold()
        ]
        return TablePage(matches[query.page_slice(len(matches))], len(matches))

    if request.headers.get("Datastar-Request"):
        return await table_sse_response_async(Directory, request, load_page=load_page)
    table = await Directory.for_request(request, load_page=load_page)
    return HttpResponse(await sync_to_async(render_table_fragment)(table, request))


urlpatterns = [path("directory/", directory)]


class DistributionSmokeTest(TestCase):
    def test_package_imports_from_an_installed_wheel(self):
        package = import_module("django_tings")
        installed = distribution("django-tings")
        assert package.__file__ is not None
        self.assertEqual(
            Path(package.__file__).resolve(),
            Path(str(installed.locate_file("django_tings/__init__.py"))).resolve(),
        )
        self.assertEqual(installed.metadata["License-Expression"], "MIT")
        self.assertTrue(
            any(
                file.name == "MIT.txt" and Path(file.locate()).is_file()
                for file in installed.files or ()
            )
        )


class DjangoSmokeTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        conf.settings.configure(
            SECRET_KEY="installed-wheel-smoke-test",
            ALLOWED_HOSTS=["testserver"],
            ROOT_URLCONF=__name__,
            INSTALLED_APPS=[
                "django.contrib.staticfiles",
                "django_tables2",
                "django_tings.interactive_table",
            ],
            TEMPLATES=[
                {
                    "BACKEND": "django.template.backends.django.DjangoTemplates",
                    "APP_DIRS": True,
                }
            ],
            STATIC_URL="/static/",
        )
        setup()

    def test_django_discovers_installed_templates_and_tags(self):
        get_template(f"{ASSETS}/table.html")
        engines["django"].from_string("{% load django_tables2 interactive_table %}")

    def test_assets_include_works_with_the_packaged_and_host_runtime(self):
        template = get_template(f"{ASSETS}/assets.html")
        default_page = template.render()
        host_page = template.render({"host_datastar": True})
        runtime = f"/static/{ASSETS}/datastar-1.0.2.js"
        self.assertEqual(default_page.count(runtime), 1)
        self.assertNotIn(runtime, host_page)
        for page in (default_page, host_page):
            self.assertIn(f"/static/{ASSETS}/table.css", page)
            self.assertIn(f"/static/{ASSETS}/interactive-table.js", page)

    def test_collectstatic_includes_the_runtime_and_its_license(self):
        with (
            TemporaryDirectory() as static_dir,
            override_settings(STATIC_ROOT=static_dir),
        ):
            call_command("collectstatic", interactive=False, verbosity=0)
            for filename in (
                "table.css",
                "interactive-table.js",
                "selection.js",
                "sticky-header.js",
                "datastar-1.0.2.js",
                "DATASTAR-LICENSE.txt",
            ):
                with self.subTest(filename=filename):
                    self.assertTrue((Path(static_dir) / ASSETS / filename).is_file())

    def test_django_uses_the_installed_german_catalog(self):
        with override("de"):
            self.assertEqual(gettext("Search"), "Suchen")
            for count, expected in ((1, "1 Datensatz"), (2, "2 Datensätze")):
                with self.subTest(count=count):
                    result = ngettext(
                        "%(counter)s record", "%(counter)s records", count
                    )
                    self.assertEqual(result % {"counter": count}, expected)

    def test_public_get_and_refresh_render_german_controls_and_counts(self):
        client: Any = Client()
        with override("de"):
            first = client.get("/directory/")
            self.assertEqual(first.status_code, 200)
            self.assertIn("Daten durchsuchen", first.text)
            self.assertIn("2 Datensätze", first.text)
            self.assertIn("Erneut versuchen", first.text)

            refresh = client.get(
                "/directory/", {"q": "Ada"}, headers={"Datastar-Request": "true"}
            )
            self.assertEqual(refresh.status_code, 200)
            self.assertEqual(refresh.headers["Content-Type"], "text/event-stream")
            body = b"".join(refresh.streaming_content).decode()

        self.assertIn("Tabelle aktualisiert. 1 Datensatz", body)
        self.assertIn("Ada", body)
        self.assertNotIn("Grace", body)


if __name__ == "__main__":
    main()
