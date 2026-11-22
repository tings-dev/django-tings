# How does a project configure and theme the table?

Type: prototype
Label: wayfinder:prototype
Status: resolved
Assignee: Codex

## Question

What does a minimal table declaration look like with the standalone default, and which overrides let Carbonsheet achieve its existing appearance and behavior? Compare a minimal declaration with a feature-rich import preview. Account for mobile cards and details, density, search modes, column kinds and sublabels, sticky headers, pinned identity, comparison scrolling, status icons and tones, cell diffs, selection, row and cell targets, actions, empty states and pagination controls. Identify the template, CSS, JavaScript and translation assets an installed app must supply and how a host overrides them. Review both examples with the maintainer.

## Prototype

Open the [portable walkthrough](../prototype/display-theme.html). The arrows switch between a two-column contacts directory, an import preview using the library defaults, and the same import with a Carbonsheet theme. Select **New** and **Errors**, then narrow the window and open **Row details**. The table declaration and host overrides are expandable beneath each example. The file replays fixtures rendered by Django. The [live prototype](../prototype/display-theme/preview.py) serves the same templates and handles real Datastar requests. Run it with `uv run --script preview.py` from its directory.

The reviewed source and portable walkthrough are preserved on the local branch `prototype/table-theme` at `fe7b423`.

## Answer

The maintainer approved three customization points for the standalone table and Carbonsheet integration. Use `TableDisplay` for features, scoped CSS variables for styling, and named Django templates for custom markup. The library owns Datastar patch targets and keyboard behavior across themes.

Keep the approved view-supplied data loader. Declare columns with django-tables2. Supply an optional `TableDisplay` on the table class, with a per-instance `display=` override for request-specific values. A directory can supply just its caption. A rich table declares its behavior once and can render in either theme. Subclasses and factory views can use `dataclasses.replace` to change a single option. For import sessions, for example, the view can bind the session's columns, mobile heading and bulk action without changing class-wide defaults.

Use plain, scoped CSS for the shipped default. A host stylesheet loaded afterward can set documented `--it-*` properties for colors, borders, typography and spacing. Allow a project-wide theme default and a `theme=` override on an instance. A theme names any Django presentation templates it needs to replace. In the prototype the only host template is a [status badge](../prototype/display-theme/templates/host/import_status.html). The library owns the wrapper, patch target IDs, live regions, focus handling and event bindings. Themes receive the same presentation context during the initial render, mobile rendering and SSE updates. Use django-tables2's normal custom columns for application-specific cell content.

### Existing options to preserve in the library

| Concern | Application declaration and behavior |
| --- | --- |
| Search, filters and paging | Declare searchable and sortable fields, default sort, select/date-range filters, chip values/defaults and page size alongside the data configuration. Display options set the search label and visible/collapsed/hidden mode, chip group label, pager placement above/below and alignment at each position. |
| Table layout | Choose compact or comfortable density, static height with placeholder rows, cell truncation, sticky headers, wide layout, comparison scrolling and a pinned identity column. Pinning and comparison scrolling are opt-in. The host can map the sticky offset to its shell. |
| Columns and mobile | Specify column kinds and header sublabels, mobile heading, summary, detail and badge columns. Preserve accessible labels, units, ordinary sort links, and a narrow-screen fallback when cards are unconfigured. |
| Status and change indicators | Map raw values to translated labels, tones and icons. Choose row tones, per-cell tones, icon-only desktop status with an accessible name, and cell diffs with previous values. Keep full labels on mobile. |
| Navigation and actions | Declare row and cell route targets, return links, same-page row details, and per-row actions with disabled reasons or missing-value behavior. Preserve row selection keyed by a record field, named bulk POST actions, extra form fields and CSRF protection. The host authorizes the receiving view. |
| Empty and refresh states | Provide distinct empty and filtered-empty copy and optional permitted actions. The library preserves rows and focus on refresh, announces results and failures, and offers retry. Host slots can control the appearance of status badges, empty content and action content inside the library-owned controls. |

The runnable examples exercise display density, column kinds and sublabels, previous values, mobile cards/details, status filtering, empty copy and a badge override. The remaining rows describe requirements for the implementation and migration.

### Integration and assets

- Install `django_tings.interactive_table` and `django_tables2`. Render with the usual `{% render_table table %}`. Use one namespaced assets include in the base page that hosts tables. It supplies the packaged stylesheet, table enhancement and a locally served Datastar runtime. Allow the include to skip the runtime when the host already loads it. A page loading two tables includes the assets once.
- Ship Django templates, template tags, static CSS/JS, the runtime's upstream license, and compiled message catalogs in the wheel. Keep public slot context documented. Generic labels use Django translation and pluralization. The host owns translations for its field names, status values and actions. JavaScript receives localized labels from the server.
- Verify packaging and German catalog coverage during migration. The fixture is in English. Theme authors should be able to reproduce the existing table UI without copying the library's JavaScript or internal SSE templates.

### Verification

A browser drove the real Datastar filter request, checked that the host badge remained after the patch, and used the ordinary GET link with JavaScript disabled. Both the live and portable examples retained keyboard focus on the selected filter, rendered the filtered empty state and exposed mobile row details. Carbonsheet's browser helper checked the fixture at 360, 768 and 1440 px with 30% copy expansion and reduced motion, including 200% zoom at the widest size. It reported no page overflow or browser errors. Full Carbonsheet behavior, authorization, German translations and production packaging belong to migration validation.
