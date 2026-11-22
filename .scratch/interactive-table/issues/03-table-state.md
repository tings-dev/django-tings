# What state belongs to one table instance?

Type: grilling
Label: wayfinder:grilling
Status: open

## Question

Which query parameters, Datastar signals and patch targets belong to an instance on initial render, ordinary GET navigation and SSE refresh? Decide how existing Carbonsheet links and legacy requests will behave, and whether two independently filtered instances must work on one page. Current DOM IDs include a table identifier, while signals such as `tablePage` and query parameters such as `page` are shared. Cover sorting, filtering, pagination, history, stale updates, error feedback and existing query context.
