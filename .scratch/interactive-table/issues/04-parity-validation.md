# What demonstrates standalone reuse and a complete Carbonsheet replacement?

Type: grilling
Label: wayfinder:grilling
Status: open
Blocked by: 01, 02, 03

This decision uses the outcomes of [How does an application supply rows and request context?](01-table-data-interface.md), [How does a project configure and theme the table?](02-display-and-theme.md) and [What state belongs to one table instance?](03-table-state.md).

## Question

Which use cases and tests establish that both consumers use the packaged implementation? Include installation from a built wheel with its templates and static assets, the supported Python and Django versions, and a minimal Django project with the standalone default. In the Carbonsheet worktree, trace existing table callers through the library and identify tests for state, permissions, rendering, SSE and browser behavior, including no-JavaScript navigation and the responsive UI contract. Decide which app-specific code stays and what evidence allows the old shared implementation to be removed.
