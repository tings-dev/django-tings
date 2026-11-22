# Load a scoped, configurable table and serve its refresh
Status: resolved
Blocked by: none

Implement the public loader, table, display, theme, state, URLs and Django SSE response. Port applicable first-party behavior from Carbonsheet. Exercise initial GET and refresh via the approved public boundary, including per-instance options, routes and authorization. Coordinate the rendering contract with the presentation ticket.

Request-scoped loading and rendering landed in a495141. Sort links and lazy refresh URLs were verified in f27b883. See the [validation report](../validation.md).
