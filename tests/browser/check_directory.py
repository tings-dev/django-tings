"""Run with the wheel and Playwright installed, from outside the source tree."""

import os
import threading
from contextlib import contextmanager
from socketserver import ThreadingMixIn
from tempfile import TemporaryDirectory
from wsgiref.simple_server import WSGIServer, make_server

from django.core.management import call_command
from django.core.wsgi import get_wsgi_application
from django.test.utils import override_settings
from playwright.sync_api import expect, sync_playwright


class Server(ThreadingMixIn, WSGIServer):
    daemon_threads = True


@contextmanager
def directory_url():
    os.environ["DJANGO_SETTINGS_MODULE"] = "directory_settings"
    application = get_wsgi_application()
    with (
        TemporaryDirectory() as static_root,
        override_settings(STATIC_ROOT=static_root),
    ):
        call_command("collectstatic", interactive=False, verbosity=0)
        with make_server("127.0.0.1", 0, application, server_class=Server) as server:
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                yield f"http://127.0.0.1:{server.server_port}/directory/"
            finally:
                server.shutdown()
                thread.join()


def check_search(browser, url):
    page = browser.new_page()
    page.goto(
        url
        + "?tab=review&clients-page=2&suppliers-page=2&clients-sort=name&clients-direction=desc&clients-filter_group=A"
    )
    clients = page.locator('[data-table-instance="clients"]')
    suppliers = page.locator("#suppliers")
    search = clients.get_by_role("searchbox", name="Search contacts")
    names = clients.locator("tbody td:first-child")
    expect(clients.get_by_text("Page 2 of 3")).to_be_visible()
    expect(suppliers.get_by_text("Page 2 of 4")).to_be_visible()
    assert page.locator('script[src*="datastar-1.0.2"]').count() == 1
    with page.expect_request(
        lambda request: (
            request.headers.get("datastar-request") and "clients-q=Clark" in request.url
        )
    ):
        search.fill("Clark")
    expect(clients.get_by_text("Page 1 of 1")).to_be_visible()
    expect(names).to_have_text(["Clarkson", "Clark"])
    expect(clients.get_by_text("2 records", exact=True)).to_be_visible()
    expect(search).to_be_focused()
    assert search.evaluate("el => el.selectionStart") == 5
    assert "clients-q=Clark" in page.url
    assert "clients-filter_group=A" in page.url and "clients-direction=desc" in page.url
    assert "suppliers-page=2" in page.url and "tab=review" in page.url
    page.reload()
    expect(names).to_have_text(["Clarkson", "Clark"])
    expect(suppliers.get_by_text("Page 2 of 4")).to_be_visible()
    expect(page.get_by_role("link", name="Review")).to_have_attribute(
        "aria-current", "page"
    )
    search.fill("")
    expect(clients.get_by_text("6 records", exact=True)).to_be_visible()
    assert "clients-q=" not in page.url and "clients-filter_group=A" in page.url
    clients.get_by_role("link", name="Clear search and filters").click()
    expect(clients.get_by_text("7 records", exact=True)).to_be_visible()
    assert (
        "clients-filter_group" not in page.url and "clients-direction=desc" in page.url
    )
    page.close()


def check_failure_and_ordering(browser, url):
    page = browser.new_page()
    # Let an already-sent older response arrive despite its cancellation.
    page.add_init_script("""const originalFetch = window.fetch;
        window.fetch = (input, init) => originalFetch(input, {...init, signal: undefined});""")
    page.goto(url + "?tab=review&suppliers-page=2")
    clients = page.locator("#clients")
    suppliers = page.locator("#suppliers")
    search = clients.get_by_role("searchbox")
    old = []

    def hold(route):
        if route.request.headers.get("datastar-request"):
            old.append((route, route.fetch()))
        else:
            route.continue_()

    page.route("**/*clients-q=Axel*", hold)
    with page.expect_request(lambda request: "clients-q=Axel" in request.url):
        search.fill("Axel")
    suppliers.get_by_role("link", name="Next page").click()
    expect(suppliers.get_by_text("Page 3 of 4")).to_be_visible()
    search.fill("Daria")
    expect(clients.get_by_text("1 record", exact=True)).to_be_visible()
    assert "clients-q=Daria" in page.url and "suppliers-page=3" in page.url
    with page.expect_event(
        "requestfinished", predicate=lambda request: "clients-q=Axel" in request.url
    ):
        old[0][0].fulfill(response=old[0][1])
    expect(clients.locator("tbody")).to_contain_text("Daria")
    expect(search).to_have_value("Daria")
    assert "clients-q=Daria" in page.url and "suppliers-page=3" in page.url
    before_failure = page.url
    mask = "**/*clients-q=Clark*"
    page.route(mask, lambda route: route.fulfill(status=503))
    search.fill("Clark")
    retry = clients.get_by_role("button", name="Retry")
    expect(retry).to_be_visible()
    expect(suppliers.get_by_role("button", name="Retry")).to_have_count(0)
    expect(clients.locator("tbody")).to_contain_text("Daria")
    expect(search).to_have_value("Clark")
    assert page.url == before_failure
    page.unroute(mask)
    retry.click()
    expect(clients.get_by_text("3 records", exact=True)).to_be_visible()
    assert "clients-q=Clark" in page.url
    clients.get_by_role("link", name="Clear search and filters").click()
    expect(clients.get_by_text("7 records", exact=True)).to_be_visible()
    assert "clients-q" not in page.url
    page.go_back()
    expect(clients.get_by_text("3 records", exact=True)).to_be_visible()
    expect(search).to_have_value("Clark")
    expect(suppliers.get_by_text("Page 3 of 4")).to_be_visible()
    page.go_forward()
    expect(clients.get_by_text("7 records", exact=True)).to_be_visible()
    expect(page.get_by_role("link", name="Review")).to_have_attribute(
        "aria-current", "page"
    )
    assert "tab=review" in page.url and "suppliers-page=3" in page.url
    page.close()


def check_get_form(browser, url):
    page = browser.new_page(java_script_enabled=False)
    page.goto(
        url
        + "?tab=review&clients-page=2&suppliers-page=2&clients-sort=name&clients-direction=desc&clients-filter_group=A"
    )
    clients = page.locator("#clients")
    clients.get_by_role("searchbox").fill("Clark")
    clients.get_by_role("button", name="Search", exact=True).click()
    expect(clients.get_by_text("2 records", exact=True)).to_be_visible()
    names = clients.locator("tbody td:first-child")
    expect(names).to_have_text(["Clarkson", "Clark"])
    assert "clients-filter_group=A" in page.url and "clients-direction=desc" in page.url
    assert "suppliers-page=2" in page.url and "tab=review" in page.url
    clients.get_by_role("link", name="Name").click()
    expect(names).to_have_text(["Clark", "Clarkson"])
    page.close()


def check_review(browser, url):
    for width in (360, 768, 1440):
        page = browser.new_page(
            viewport={"width": width, "height": 900}, reduced_motion="reduce"
        )
        errors = []
        page.on("pageerror", lambda error, errors=errors: errors.append(error))
        page.goto(url + "?review=yes&host_runtime=yes")
        root = page.locator("#clients")
        check = root.get_by_role("checkbox", name="Select Atlas")
        check.check()
        root.get_by_role("link", name="Next page").click()
        expect(root.get_by_text("1 selected")).to_be_visible()
        expect(root.get_by_text("Page 2 of 4")).to_be_visible()
        root.get_by_role("checkbox", name="Select Clara").check()
        expect(root.get_by_text("2 selected")).to_be_visible()
        expect(
            page.locator("#suppliers").get_by_text("Nothing selected")
        ).to_be_visible()
        active = root.locator(
            "[data-table-mobile-records]" if width == 360 else "tbody"
        )
        expect(active.locator(".host-badge").first).to_contain_text("Active")
        if width == 360:
            detail = root.get_by_text("More details").first
            detail.focus()
            detail.press("Enter")
            expect(root.locator("article details[open] dd").first).to_be_visible()
        else:
            expect(root.locator("[data-table-sticky-header]")).to_be_visible()
        root.get_by_role("button", name="Apply selection").click()
        expect(page.get_by_text("Atlas,Clara (approved)")).to_be_visible()
        page.go_back()
        page.evaluate("document.documentElement.style.zoom='200%'")
        assert page.evaluate(
            "document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1"
        )
        assert not errors, errors
        assert page.locator('script[src*="datastar-1.0.2"]').count() == 1
        page.close()


if __name__ == "__main__":
    with directory_url() as start, sync_playwright() as driver:
        browser = driver.chromium.launch(executable_path=os.environ.get("CHROME_BIN"))
        try:
            check_search(browser, start)
            check_failure_and_ordering(browser, start)
            check_get_form(browser, start)
            check_review(browser, start)
        finally:
            browser.close()
