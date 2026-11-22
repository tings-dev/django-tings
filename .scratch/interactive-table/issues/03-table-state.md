# What state belongs to one table instance?

Type: grilling
Label: wayfinder:grilling
Status: resolved
Assignee: Codex

## Question

Which query parameters, Datastar signals and patch targets belong to an instance on initial render, ordinary GET navigation and SSE refresh? Decide how existing Carbonsheet links and legacy requests will behave, and whether two independently filtered instances must work on one page. Current DOM IDs include a table identifier, while signals such as `tablePage` and query parameters such as `page` are shared. Cover sorting, filtering, pagination, history, stale updates, error feedback and existing query context.

## Current Carbonsheet behavior

- Ordinary GETs read `q`, `page`, `sort`, `direction` and declared `filter_*` fields, including date bounds. In a Datastar request, the presence of any of the first four keys selects the canonical parser for the entire table state. A request containing only `filter_country=DE` can therefore fall through to legacy signals. This matters when migrating existing forms. [State parser](../../../../carbonsheet-django-tings/src/carbonsheet/base/tables/state.py) · [SSE adapter](../../../../carbonsheet-django-tings/src/carbonsheet/base/tables/sse.py)
- Typing or changing a form field replaces the current history entry after a debounce. A sort, pager, chip or clear link pushes its destination before the response arrives. Typing edits the current URL, whereas generated links rebuild it from the configured page target, fixed query and table fields. Carbonsheet’s details sheet also handles its own Back/Forward transitions. [Browser behavior](../../../../carbonsheet-django-tings/src/carbonsheet/static/js/interactive-table.js) · [Link generation](../../../../carbonsheet-django-tings/src/carbonsheet/base/tables/base.py) · [Details sheet](../../../../carbonsheet-django-tings/src/carbonsheet/static/js/record-details-sheet.js)
- The server patches result and status elements by ID. Page, loading and filter signals are shared names. Bulk selection already keeps record IDs in a set per table region, including selected records on other pages or hidden by the current filter. A shareable URL does not include those IDs. [Table template](../../../../carbonsheet-django-tings/src/carbonsheet/base/templates/base/components/tables/interactive_table.html) · [Selection behavior](../../../../carbonsheet-django-tings/src/carbonsheet/static/js/table-row-selection.js)

## Answer

- A page with one table may use plain `q`, `page`, `sort`, `direction` and declared filter parameters. When multiple tables share a URL, the consuming view assigns each a stable instance name. Searching, sorting or paging one instance updates only its own state. Links and forms preserve sibling state and host page context, including the active tab. The same rule applies to tab panels that share a URL. Each instance owns its live signals, result and error targets, pending request, focus and selection.
- After a successful live search, replace the current history entry. Successful page, sort, chip and clear clicks add an entry. Back and Forward restore the view described by the URL. Ignore superseded responses. On a failed refresh, keep the last successful rows and URL, and keep the typed text available to retry.
- The generic live Datastar request and ordinary GET form use the same explicit query parameters. Migrate Carbonsheet's templates and endpoints together. Add a Carbonsheet adapter only if a remaining caller sends table state exclusively through legacy signals.

## Acceptance examples

1. A dashboard at `?clients-q=steel&suppliers-page=4&imports-page=2` keeps independent state for three tables. Clearing the clients search leaves the other two on their current pages. The names come from the consuming view. The same rule would apply to independent tables in tab panels sharing one URL. Separate pages with one table each can use ordinary `q` and `page` parameters. Ordinary links, GET forms and links opened in another browser tab should reproduce the same view.
2. An older search for `st` returns after a newer search for `steel`. Only the latest request for that instance may change rows, signals, status, focus, busy state or history. A successful refresh of a sibling should merge its change into the latest page URL even when its request began earlier.
3. A failing refresh should leave successful rows visible and offer retry in the initiating instance. A server-clamped page should produce a shareable URL consistent with the rows. Back/Forward for a host-owned details sheet should still work.
4. A shared Carbonsheet URL such as `?q=steel&page=2`, a filter-only URL, a deliberate clear, and an old signal-only request should each resolve unambiguously. Fixed routing parameters belong to the host. A view checks authorization on each request.
