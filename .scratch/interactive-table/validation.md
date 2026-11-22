# Interactive table validation

## Installed wheel

Built `django_tings-0.0.0.post15.dev0+468a3fb-py3-none-any.whl` at library integration commit `468a3fb` using `uv build --wheel --out-dir ~/workspace/tings-implementation/release`.

SHA-256 `bcc4f46a15c3c7d7eaa78dfad0c629ef15ac29bdc093d7fd5f4eca98ed851f0a`

Each standalone consumer was created outside the checkout with `uv venv --python`, then installed with `uv pip install --python <consumer>/.venv/bin/python <wheel>` and the exact Django, django-tables2 and datastar-py pins below. Carbonsheet's existing locked environment received the same file with `uv pip install --python <host-venv>/bin/python --no-deps --reinstall <wheel>`. The installed distribution metadata in Carbonsheet identifies that file in `direct_url.json`.

Archive inspection verified MIT package metadata, the project's MIT license file, the Datastar runtime's upstream license, templates, template tags, CSS, all four JavaScript files, and the German message source and compiled catalog. `msgfmt --check --check-format` compiled the library catalog byte-for-byte to the shipped `django.mo`.

## Compatibility

| Consumer | Python | Django | django-tables2 | datastar-py |
| --- | --- | --- | --- | --- |
| Standalone, declared floor | 3.12.16 | 6.0 | 2.8.0 | 1.0.2 |
| Standalone, Carbonsheet versions | 3.14.10 | 6.1.1 | 3.0.1 | 1.0.3 |
| Carbonsheet, integration lock | 3.14.10 | 6.1.1 | 3.0.1 | 1.0.3 |

Carbonsheet used Carboncalc 0.0.8 from pinned revision `bfcf2b7`.

## Standalone results

- The copied `tests/installed_wheel.py` ran with `.venv/bin/python -I installed_wheel.py -v`. All 6 checks passed in each environment. They verified the import location, template and tag discovery, `collectstatic`, packaged and host-supplied runtime modes, German controls and feedback on GET and refresh, and German singular and plural counts.
- The copied `tests/browser` fixture ran with `../.venv/bin/python -E -s check_directory.py` in both consumer directories. Playwright 1.65.2 and Chromium 159.0.8154.6 passed on both stacks. Chromium loaded the collected assets, used one Datastar runtime under each boot mode, and exercised live search from page two, the matching count and pager, sort and filter retention, focus and caret, URL restoration, stale responses, error and retry, clear, and no-JavaScript search and sort. The two instances preserved their own state and the active host tab through live changes, reload and Back/Forward. The review fixture checked cross-page selection and POST, scoped feedback, the host badge template and responsive review at 360, 768 and 1440 px.
- The documented contacts view and template passed with an SQLite-backed model in both environments. Anonymous requests redirected on GET and refresh. Authenticated requests returned the expected filtered row, clamped page and owner-scoped choices.
- On the library development lock, `uv sync --locked --dev` passed. `uv run --locked --no-sync pytest --cov-report=xml --cov=django_tings tests` passed 10 tests. `ruff check --no-fix .`, `ruff format --check .`, `pyrefly check`, and `ty check src/django_tings/interactive_table tests` passed. The optional repository-wide `ty check` exited with six renamed-rule warnings in the unchanged template-generated `_debug.py`.

The standalone Chromium logs are under `release/minimum-L4ET04/browser.log` and `release/locked-p7fE1I/browser.log` in the private validation workspace.

## Review

| Review | Findings and verification |
| --- | --- |
| Standards | The review reported four defects and two maintainability issues. The library now opens record details through explicit links, preserves normal forms and links if either JavaScript asset is unavailable, and formats selection counts for the document language. Chromium covered desktop and mobile links, both missing-asset cases, and German and Bengali selection feedback. Carbonsheet preserved its baseline compiled German catalog in Git and compiles current messages during verification. Date-range spellings normalize through one function and have a request regression test. The unused sticky-header mapping was removed. |
| Spec | Chromium reproduced four regressions. The final wheel passed the browser checks for a delayed Back response overtaken by Forward, a failed Back refresh keeping the committed rows and URL, trailing whitespace and its caret surviving an update, and the lower pager keeping both focus and scroll position. The history retry case also preserves a sibling table's newer page. |

## Carbonsheet routes

Carbonsheet integration commit `24cb79d` runs the library's `InteractiveTable` base. `manage.py shell` confirmed that each allowlisted dashboard class inherits from the installed base and that Django resolves both table templates and all shared styles and scripts under the wheel installation in `site-packages`. The old Carbonsheet shared templates, state and display modules, and table and selection scripts were removed in the migration.

All refreshes are GETs. The browser sends `Datastar-Request: true` and an explicit query string. The shared dashboard endpoint requires an allowlisted `table_key`. Scoped endpoints reconstruct the table from route identifiers, authorize access, and check that the requested key matches the reconstructed table. The same-page workspace endpoint also requires the Datastar header to select its refresh branch.

| Initial GET | Refresh GET | Request coverage |
| --- | --- | --- |
| `/clients/` | `/sse/tables/?table_key=clients` | `test_clients_table.py::test_client_directory_renders_packaged_table_and_refreshes_selected_rows`. `test_authorization.py` covers related clients for client and supplier contacts across both request modes. |
| `/suppliers/` | `/sse/tables/?table_key=suppliers` | `test_directory_pages.py::test_directory_applies_canonical_query_state_without_javascript` and `test_interactive_table_sse.py::test_shared_table_sse_routes_to_suppliers_table`. `test_authorization.py` checks visibility for both contact roles on GET and refresh. |
| `/articles/` | `/sse/tables/?table_key=articles` | `test_interactive_table_sse.py::test_directory_refresh_uses_selected_definition` and `test_article_detail.py::test_articles_table_rows_navigate_to_article_detail`. |
| `/quantities/` | `/sse/tables/?table_key=quantities` | `test_directory_pages.py::test_directory_applies_canonical_query_state_without_javascript` and `test_interactive_table_sse.py::test_shared_table_sse_routes_to_quantities_table`. |
| `/emissions-profiles/` | `/sse/tables/?table_key=emissions_profiles` | `test_interactive_table_sse.py::test_directory_refresh_uses_selected_definition` and `test_emissions_profile_detail.py::test_emissions_profiles_table_rows_navigate_to_profile_detail`. |
| `/reference-data/`, tabs `commodities`, `default-values`, `benchmarks` | `/sse/tables/`, keys `commodities`, `cbam-default-values`, `cbam-benchmarks` | `test_interactive_table_sse.py::test_directory_refresh_uses_selected_definition`. `test_reference_data_page.py` covers active-tab links, the three initial views, filter-only routes, and pagination clamping. |
| `/clients/<client_id>/` | `/clients/<client_id>/sse/table/` | `test_client_detail.py::test_client_detail_table_has_scoped_page_target_and_request_state`, `test_client_detail_sse_routes_to_client_scoped_table`, and `test_authorization.py::test_contact_user_cannot_open_unrelated_detail_pages`. `test_client_reports.py::test_reports_sse_refresh_preserves_granularity` and `test_certificates_tables.py::test_sse_serves_lots_and_drilled_purchases` cover report and certificate variants. |
| `/clients/<client_id>/reports/<period>/` | `/clients/<client_id>/reports/<period>/sse/table/` | `test_client_report_detail.py::test_tabs_are_scoped_to_client_and_period`, `test_report_detail_sse_serves_period_scoped_table`, `test_emissions_sse_carries_scenario`, and `test_method_filter_rides_in_the_table_state`. |
| `/suppliers/<supplier_id>/` | `/suppliers/<supplier_id>/sse/table/` | `test_supplier_detail.py::test_supplier_detail_table_has_scoped_page_target_and_request_state`, `test_supplier_detail_sse_routes_to_supplier_scoped_table`, and `test_authorization.py::test_contact_user_cannot_open_unrelated_detail_pages`. |
| `/articles/<supplier_id>/<article_id>/` | `/articles/<supplier_id>/<article_id>/sse/table/` | `test_article_detail.py::test_article_detail_tab_counts`, `test_article_detail_sse_routes_to_article_scoped_table`, and `test_article_detail_sse_rejects_mismatched_key`. |
| `/quantities/<public_id>/` | `/quantities/<public_id>/sse/table/` | `test_quantity_detail.py::test_quantity_detail_tab_counts`, `test_quantity_detail_sse_routes_to_quantity_scoped_table`, and `test_quantity_detail_sse_rejects_mismatched_key`. |
| `/emissions-profiles/<public_id>/` | `/emissions-profiles/<public_id>/sse/table/` | `test_emissions_profile_detail.py::test_emissions_profile_detail_tab_counts`, `test_emissions_profile_detail_sse_routes_to_profile_scoped_table`, and `test_emissions_profile_detail_sse_rejects_mismatched_key`. |
| `/reports/`, single-client mode | `/clients/<client_id>/sse/table/`, reports key with `granularity` | `test_single_client_mode.py::test_reports_page_renders_for_the_client` checks the initial page and the refreshed `/reports/` page target. `test_client_reports.py::test_reports_sse_refresh_preserves_granularity` verifies the granularity. |
| `/certificates/`, single-client mode | `/clients/<client_id>/sse/table/`, certificates key with optional `lot` | `test_certificates_single_client.py::test_standalone_page_lists_lots_and_offers_record_purchase`, `test_standalone_drilldown_uses_the_lot_param`, and `test_certificates_tables.py::test_sse_serves_lots_and_drilled_purchases`. The drill-down check asserts the refreshed URL retains its lot. |
| `/imports/<public_id>/`, staged category and errors tabs | `/imports/<public_id>/table/` | `test_workflow_views.py::test_detail_renders_discovered_sqlite_category_and_sse_is_owner_scoped`, `test_session_detail_and_actions_are_owner_scoped`, `test_sse_refresh_respects_status_filter`, `test_errors_tab_chip_counts_error_rows_not_messages`, and `test_errors_tab_groups_by_error_group_and_offers_fix_action`. |
| `/scenario-workspaces/` | `/scenario-workspaces/?table_key=scenario-workspaces` | `test_scenario_workspaces.py::test_directory_refresh_uses_only_owned_workspaces` checks owner filtering and table-key validation. `test_roles_require_real_contact_relations` checks both initial and refresh roles. The directory assertions in the older lifecycle and storage recovery tests run after workspace creation. |
| `/auction-prices/` | `/auction-prices/sse/table/?table_key=eua-auctions` | `auction_prices/test_views.py::test_historical_page_renders_the_eligible_count`, `test_historical_page_hides_search_and_offers_year_chips`, and `test_refresh_selects_historical_table_and_keeps_year_filter`. |

The `table_key` endpoint allowlist and rejection of unvalidated global signals are covered by `test_dashboard_table_resolver_uses_allowlist` and `test_shared_endpoint_rejects_unvalidated_global_signals` in `test_interactive_table_sse.py`.

### Role coverage

- The standard Carbonsheet test client is an Editor. The directory suite also exercises ordinary GETs as Read Only, and the auction test uses Read Only for both the historical page and its refresh. Related client and supplier contacts exercise both modes in `test_authorization.py`.
- Client and supplier detail tests cover Editor access and denial for unrelated client contacts on GET and refresh. The article, quantity, report and emissions-profile refresh tests exercise Editor access with scoped data or mismatched route keys. Those cases rely on the route's existing permission gate for other roles.
- Import tests cover the owning user, different owners and users without the required import permission. The browser exercise verifies the owner can submit eligible records across pages while a visitor receives a denial.
- Workspace tests verify Editor and App Admin access on GET and refresh. Users with no eligible role, Read Only, or a contact group without the required relationship receive 403 in both modes. The dedicated workspace test also seeds a second owner and checks that both request modes return only the current user's records.

## Carbonsheet results

The host checks ran from the Carbonsheet integration worktree using the prepared Python environment and repository source paths.

```sh
uv run --no-sync pytest -q --disable-warnings --tb=line
just check
just i18n verify
just i18n compile
node tests/js/table_sticky_header_dom_test.mjs
uv run --no-sync pytest -q tests/test_interactive_table_js.py -k ephemeral
```

- The final full suite finished with 2,602 passed, 4 skipped and 12 failed. The failed test IDs matched the baseline exactly. Both failures introduced in the initial cutover passed after the review fixes.
- The browser fixture was served with `uv run --no-sync pytest -c pyproject.toml -p tests.conftest -o addopts= <workspace>/browser/test_browser_site.py`. The fixture and result directory was selected through `TINGS_BROWSER_RUN`. The host interpreter ran `browser/flows.py <run-dir>` for the four workflows and `browser/viewport_checks.py <run-dir>` for the project browser helper's viewport checks.
- Four authenticated Chromium workflows passed against the installed wheel. The clients directory exercised sort and search from page two, focus and caret, saved URL, a superseded response arriving after the newer one, retry, clear, and matching rows through the no-JavaScript form. A scoped client detail exercised tenant isolation, tab context, and Back/Forward after sorting. The record-details sheet closed on Back, restored focus to its trigger, and reopened on Forward while the table retained its rows and tab without making a request. The workspace directory searched its in-memory records through the same page's refresh. Import review searched discovered columns from page two with a status filter and sort, returned to page one with both controls active, retained two selected records and submitted them in a CSRF-protected POST. An unauthorized visitor received 403.
- Sixteen project browser helper runs covered the four views at 360, 768 and 1440 px, plus native 200% zoom with 30% copy expansion from 1440 px. All runs requested reduced motion. There were zero HTTP status, focus, contrast, viewport, zoom, overflow, or reduced-motion failures and zero unexpected request failures, page errors or console errors. The 29 touch-target entries at unzoomed 768 and 1440 px were labeled search fields, labeled checkboxes, and inline workspace row links within the documented compact sizes. The 360 px and native 200% runs had zero touch-target entries. On the shared VM, the final audit flagged seven interactions and one layout shift. The baseline audit flagged 15 interactions and three layout shifts.
- `just i18n verify` and `just i18n compile` passed with 1,354 Carbonsheet translations. The compiled host catalog is in `release/host-compiled-django.mo` in the validation workspace. The standalone wheel's German catalog was checked independently.
- The sticky header and ephemeral toolbar Node checks passed using JavaScript from Carbonsheet's wheel installation. The pytest live-server fixture supplies the URL and session to `tests/js/interactive_table_ephemeral_toolbar_dom_test.mjs`.
- `uv pip check --python <host-venv>/bin/python` passed for all 202 installed packages.
- `just check` reported the three baseline Pyrefly errors for instantiating `StoredReferenceDataSource` without `load_cn_sectors`, reproduced on `e106f21`.
- The initial cutover run found two additional failures. The report warning test now checks each responsive renderer separately. The record-details sheet now restores its own history state and lets the table receive the same history transition. The final focused cases exercise both fixes.

The Carbonsheet browser results are under `browser/final` in the private validation workspace. The full run is in `final-full.log` and the import and asset origin trace is in `host-installed-origins.log`.

## Carbonsheet baseline

Baseline Carbonsheet `e106f21` used Carboncalc `bfcf2b7`. The focused baseline logged 137 passed and 7 failed. The full baseline logged 2,601 passed, 4 skipped, and 12 failed.

- `data_import/test_workflow_views.py::test_data_import_navigation_is_final_permission_gated_item` found a workspace item after the import link.
- Three `test_inspection_sources.py` cases could not instantiate the abstract `StoredReferenceDataSource`: `test_all_reference_versions_and_incomplete_rows_are_retained`, `test_acquisition_owns_read_transaction_and_materializes`, and `test_all_years_resolve_by_production_year_and_survive_saved_reopen`.
- `test_manual_seeds.py::test_manual_seed_creation` raised `WorkspaceMissing`.
- Seven `test_scenario_workspaces.py` cases failed in lifecycle setup, expected forms, or storage recovery: `test_example_crud_and_legacy_compatibility`, `test_upload_validation_and_csrf`, `test_contact_scope_mixed_roles_and_independent_copies`, `test_source_failure_and_preselection`, `test_failed_preparation_retains_counts_and_can_retry`, `test_german_workspace_ui`, and `test_storage_failures_preserve_work_and_show_recovery`.
