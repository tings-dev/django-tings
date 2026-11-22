# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Markus Binsteiner

"""Render one complete, instance-scoped Datastar patch per refresh."""

import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any

from asgiref.sync import sync_to_async
from datastar_py import ServerSentEventGenerator as SSE
from datastar_py.django import DatastarResponse
from datastar_py.sse import DatastarEvent
from django.core.exceptions import PermissionDenied
from django.core.handlers.asgi import ASGIRequest
from django.http import Http404, HttpRequest
from django.template.loader import render_to_string
from django.utils.html import format_html
from django.utils.translation import gettext as _

from .base import InteractiveTable
from .state import TablePage, TableQuery

logger = logging.getLogger(__name__)


def render_table_fragment(table: InteractiveTable, request: HttpRequest) -> str:
    """Use the same django-tables2 render tag as the containing page."""
    return render_to_string(
        "django_tings/interactive_table/_render.html",
        {"table": table},
        request=request,
    )


def _patch_response(
    html: str, request: HttpRequest | None, *, status: int = 200
) -> DatastarResponse:
    event = SSE.patch_elements(html)
    if isinstance(request, ASGIRequest):

        async def stream() -> AsyncIterator[DatastarEvent]:
            yield event

        return DatastarResponse(stream(), status=status)
    return DatastarResponse(event, status=status)


def successful_table_response(
    table: InteractiveTable, request: HttpRequest
) -> DatastarResponse:
    """Deliver rows, status, controls and the effective page URL together."""
    return _patch_response(render_table_fragment(table, request), request)


def table_error_response(
    table_id: str, request: HttpRequest | None = None
) -> DatastarResponse:
    """Preserve the current results and report a localized refresh failure."""
    status = format_html(
        '<div id="{}-status" role="status">{}</div>',
        table_id,
        _("The table could not be refreshed. Try again."),
    )
    return _patch_response(status, request, status=500)


async def table_sse_response_async(
    table_class: type[InteractiveTable],
    request: HttpRequest,
    *,
    load_page: Callable[[TableQuery], Awaitable[TablePage]] | None = None,
    **options: Any,
) -> DatastarResponse:
    """Build a refresh from the same authorized loader and options as a GET."""
    try:
        if load_page is None:
            table = await table_class.create_for_request(request, **options)
        else:
            table = await table_class.for_request(
                request, load_page=load_page, **options
            )
        return await sync_to_async(successful_table_response)(table, request)
    except (PermissionDenied, Http404):
        raise
    except Exception:
        logger.exception("Interactive table refresh failed")
        table_id = (
            options.get("instance_name")
            or (options.get("config") or {}).get("table_id")
            or table_class.table_id
        )
        return table_error_response(table_id, request)
