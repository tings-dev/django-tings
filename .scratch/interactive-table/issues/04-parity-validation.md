# What demonstrates standalone reuse and a complete Carbonsheet replacement?

Type: grilling
Label: wayfinder:grilling
Status: open
Blocked by: 01, 02, 03

This decision uses the outcomes of [How does an application supply rows and request context?](01-table-data-interface.md), [How does a project configure and theme the table?](02-display-and-theme.md) and [What state belongs to one table instance?](03-table-state.md).

## Question

Which use cases and tests establish that both consumers use the packaged implementation? Include installation from a built wheel with its templates and static assets, the supported Python and Django versions, and a minimal Django project with the standalone default. In the Carbonsheet worktree, trace existing table callers through the library and identify tests for state, permissions, rendering, SSE and browser behavior, including no-JavaScript navigation and the responsive UI contract. Decide which app-specific code stays and what evidence allows the old shared implementation to be removed.

Include the cutover order and any temporary compatibility imports in the migration decision. Inventory callers of signal-only refreshes to determine whether Carbonsheet needs an adapter.

## Required live-search scenario

Run this browser scenario in both the minimal Django project using the installed wheel and the migrated Carbonsheet worktree. The standalone project supplies its own searchable records and loader and uses the library’s templates and JavaScript.

Start on page two with a sort and a column filter applied. Type a search term and pause for Carbonsheet’s current 300 ms debounce. Without pressing Enter, verify that the loader receives the search, the table returns to page one, and matching rows, count and pagination update in place. Keep focus and the caret in the search box, retain the sort and filter, and verify that reopening the resulting URL reproduces the rows. Delay an earlier search response until after a later one and verify that the latest search stays visible. Clear the text and verify that results return for the remaining filters. With JavaScript disabled, submit the same GET form and compare its results.

In the standalone project, render two named instances of the same table class on one URL. Search one while the other is on a later page. Verify both instances after reload and Back/Forward, including the active host tab and each table’s filters and page.
