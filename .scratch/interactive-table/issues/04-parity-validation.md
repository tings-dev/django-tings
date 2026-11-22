# What demonstrates standalone reuse and a complete Carbonsheet replacement?

Type: grilling
Label: wayfinder:grilling
Status: resolved
Assignee: Codex
Blocked by: 01, 02, 03

This decision uses the outcomes of [How does an application supply rows and request context?](01-table-data-interface.md), [How does a project configure and theme the table?](02-display-and-theme.md) and [What state belongs to one table instance?](03-table-state.md).

## Question

Which use cases and tests establish that both consumers use the packaged implementation? Include installation from a built wheel with its templates and static assets, the supported Python and Django versions, and a minimal Django project with the standalone default. In the Carbonsheet worktree, trace existing table callers through the library and identify tests for state, permissions, rendering, SSE and browser behavior, including no-JavaScript navigation and the responsive UI contract. Decide which app-specific code stays and what evidence allows the old shared implementation to be removed.

Include the cutover order and any temporary compatibility imports in the migration decision. Inventory callers of signal-only refreshes to determine whether Carbonsheet needs an adapter.

## Required live-search scenario

Run this browser scenario in both the minimal Django project using the installed wheel and the migrated Carbonsheet worktree. The standalone project supplies its own searchable records and loader and uses the library’s templates and JavaScript.

Start on page two with a sort and a column filter applied. Type a search term and pause for Carbonsheet’s current 300 ms debounce. Without pressing Enter, verify that the loader receives the search, the table returns to page one, and matching rows, count and pagination update in place. Keep focus and the caret in the search box, retain the sort and filter, and verify that reopening the resulting URL reproduces the rows. Delay an earlier search response until after a later one and verify that the latest search stays visible. Clear the text and verify that results return for the remaining filters. With JavaScript disabled, submit the same GET form and compare its results.

In the standalone project, render two named instances of the same table class on one URL. Search one while the other is on a later page. Verify both instances after reload and Back/Forward, including the active host tab and each table’s filters and page.

## Answer

The maintainer approved the first-release compatibility targets and test coverage below. The implementation is ready for sign-off when the same built wheel passes the standalone and Carbonsheet checks, including the live-search scenario above.

### Prove reuse from an installed wheel

Build one MIT-licensed wheel and record its version and checksum. Install it non-editably in a clean minimal Django project outside the source checkout, then use the same wheel in the Carbonsheet worktree for final sign-off. A sibling editable dependency is useful during development. Run final validation with the wheel actually imported by both consumers. A local wheel suffices for this check.

The minimal project owns its URL, view, columns and data loader. Render through Django’s normal app-template loader, serve the assets collected by `collectstatic`, and exercise live search with the packaged Datastar runtime and standalone CSS. Check that an included German label renders under a language override, and verify the wheel contains the compiled catalog, templates, table JS/CSS, and licenses. Also exercise a project that already supplies Datastar, as Carbonsheet does. Use the feature and state examples in the three resolved tickets as the library’s regression cases.

### Demonstrate the Carbonsheet cutover

1. In the integration worktree, record the current results of the focused suites and identify each table's initial GET, refresh endpoint, data source, and authorization scope. Keep a before/after record so any existing failures and migration regressions are distinguishable.
2. Move one searchable directory end to end, then the scoped factories, import review, workspace directory, and historical auction prices. For each, move the initial view, controls and refresh endpoint together. Preserve host-owned query parameters, data projections, routes, permission checks, translations and theme overrides. Verify that unauthorized users cannot obtain rows, option labels or facet counts through either render path.
3. Audit consumers of the existing `tableKey` routing signal as well as search/filter signals. Dashboard and auction endpoints read the key even for requests with explicit paging parameters. The migration must give those endpoints a server-validated way to select the correct table. Retain an application adapter only for an identified caller that still needs one. Trace any temporary import aliases to their final callers.
4. Remove the replaced shared base, parsing, refresh, rendering and browser code after all production callers use the package. Verify imports, template resolution and loaded assets, including one Datastar runtime. Keep the host’s concrete table definitions, authorized loaders, route/return handling, actions and styling. Check feature parity against the display ticket, including dynamic columns, select/date filters, chip counts, per-row actions, bulk selection across pages, diffs, sticky headers and narrow-screen details.
5. Run focused table suites, the full Carbonsheet suite (`just tests all`), `just check`, `just i18n verify` and `just i18n compile`. Run the sticky-header and ephemeral-toolbar Node scripts explicitly while they remain outside the Python suite. Port assertions tied to old filesystem paths so they check the installed assets and the behavior users rely on. Use the repository browser helper for real interactions at 360, 768 and 1440 px, keyboard/focus, zoom, reduced motion, expanded copy and overflow. Use a Playwright context with JavaScript disabled for the ordinary form. Record commands, package versions, representative routes, and any unresolved failures before calling the replacement complete.

### Approved versions and coverage

- **Compatibility target.** Target Python 3.12+ and Django 6.0.x and 6.1.x for the first release. Validate the library on Python 3.12 with Django 6.0 and its minimum supported dependencies, including the django-tables2 2.x line used in the prototypes. Also validate the application with its lockfile, which specifies Django 6.1.1, django-tables2 3.0.1 and datastar-py 1.0.3 on Python 3.14+. Record the exact versions exercised.
- **Coverage.** Require automated initial GET and refresh checks for every Carbonsheet table entry point, including historical auctions. Require real-browser coverage for four workflows. A directory exercises live search. Scoped detail covers fixed context, authorization and Back/Forward. Import review covers dynamic columns, facets, selection and actions. Workspaces exercise an in-memory source and same-page refresh.

[Carbonsheet lockfile](../../../../carbonsheet-django-tings/uv.lock) · [Dashboard endpoints](../../../../carbonsheet-django-tings/src/carbonsheet/dashboard/views.py) · [Import refresh](../../../../carbonsheet-django-tings/src/carbonsheet/data_import/views.py) · [Workspace host](../../../../carbonsheet-django-tings/src/carbonsheet/inspection/host.py) · [Auction views](../../../../carbonsheet-django-tings/src/carbonsheet/auction_prices/views.py) · [Test recipes](../../../../carbonsheet-django-tings/justfile)
