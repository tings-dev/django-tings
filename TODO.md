# TODO

Things to do once, right after generating this project. Delete the entries as you go, and
delete this file when it's empty.

## Publishing to PyPI

The `release_python_package` job in `.github/workflows/build-linux.yaml` publishes with
[trusted publishing](https://docs.pypi.org/trusted-publishers/), so there is no API token to
create. You do have to register the publisher first:

1. Go to <https://pypi.org/manage/account/publishing/>.
2. Add a new pending publisher:
   - PyPI project name: `django-tings`
   - Owner: `frkl-dev`
   - Repository name: `django-tings`
   - Workflow name: `build-linux.yaml`
   - Environment name: `pypi`

Releases are triggered by pushing a tag; the version comes from that tag via
`uv-dynamic-versioning`, so `git tag 0.1.0 && git push --tags` is all it takes.
