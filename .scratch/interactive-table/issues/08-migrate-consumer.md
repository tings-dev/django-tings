# Replace Carbonsheet’s shared implementation
Status: ready-for-agent
Blocked by: none for baseline and porting. Requires the integrated library for final verification.

In Carbonsheet’s integration worktree route every table through the library, retain only app-specific data/permissions/routes/theme, and remove superseded common code. Test current callers and initial/refresh behavior with the published spec's compatibility criteria.
