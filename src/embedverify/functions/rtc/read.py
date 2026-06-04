"""RTC read function."""

from __future__ import annotations

from typing import Any

from .rtc_lib import read


def execute(
    params: dict[str, Any],
    *,
    capability_registry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Read RTC time with a stable Function return contract."""

    return read(params, capability_registry=capability_registry)
