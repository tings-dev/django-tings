# Extract Carbonsheet’s interactive table into django-tings

Label: wayfinder:map

## Destination

Agree on a public interface for `django_tings.interactive_table` and a validation contract for replacing Carbonsheet’s shared table implementation in its integration worktree. Demonstrate standalone reuse and feature parity in the subsequent implementation.

## Notes

- Start the MIT-licensed distribution `django-tings` from the [frkl-dev Python project template](https://github.com/frkl-dev/python-project-template). Each ting gets its own import path. A package can hold the table’s Python modules, Django templates and static assets.
- The maintainer authorized adapting Carbonsheet’s first-party table code under MIT. Third-party assets retain their own licenses.
- Ship a working standalone default with Django, django-tables2 and Datastar. A consuming project can supply its own theme. Carbonsheet’s Tailwind/daisyUI setup is optional for consumers.
- Use the sibling [Carbonsheet worktree](../../../carbonsheet-django-tings) on `extract/django-tings-interactive-table`. The migration baseline is `e106f21` on `develop`. Consult its [table guide](../../../carbonsheet-django-tings/docs/tables.md), [UI contract](../../../carbonsheet-django-tings/docs/design_language.md), implementation and tests.
- Use Wayfinder for the map, grilling and domain-modeling for decisions, and designing-carbonsheet-ui for Carbonsheet UI work. The local Markdown tracker orders open, unassigned, unblocked issues by filename.

## Decisions so far

- [How does an application supply rows and request context?](issues/01-table-data-interface.md) was resolved by passing a request-scoped async loader from the view.
- [How does a project configure and theme the table?](issues/02-display-and-theme.md) was resolved with `TableDisplay`, scoped CSS variables and named Django templates.

## Not yet specified

The migration sequence and any temporary compatibility imports still depend on how the library handles existing Carbonsheet URLs and refresh requests.

## Out of scope

Additional tings and unrelated Carbonsheet UI changes belong to separate efforts.
