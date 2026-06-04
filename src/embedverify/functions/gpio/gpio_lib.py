"""GPIO function helper library."""

from __future__ import annotations

from typing import Any


def list_chips(
    params: dict[str, Any],
    *,
    capability_registry: dict[str, Any] | None,
) -> dict[str, Any]:
    cap = _gpio_cap(capability_registry)
    if isinstance(cap, dict):
        return cap
    return cap.list_chips(
        expected_count=int(params.get("expected_count", 1)),
        timeout=int(params.get("timeout", 10)),
    )


def line_info(
    params: dict[str, Any],
    *,
    capability_registry: dict[str, Any] | None,
) -> dict[str, Any]:
    cap = _gpio_cap(capability_registry)
    if isinstance(cap, dict):
        return cap
    raw_line = params.get("line")
    line = int(raw_line) if raw_line not in (None, "") else None
    return cap.line_info(
        chip=str(params.get("chip", "auto")),
        line=line,
        timeout=int(params.get("timeout", 10)),
    )


def _gpio_cap(capability_registry: dict[str, Any] | None) -> Any:
    cap = (capability_registry or {}).get("gpio")
    if cap is None:
        return {"code": -2, "message": "gpio capability is not available", "details": {}, "metrics": {}}
    return cap
