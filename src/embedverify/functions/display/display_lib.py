"""Display function helper library."""

from __future__ import annotations

from typing import Any


def detect(params: dict[str, Any], *, capability_registry: dict[str, Any] | None) -> dict[str, Any]:
    cap = _display_cap(capability_registry)
    if isinstance(cap, dict):
        return cap
    return cap.detect(
        require_connected=_as_bool(params.get("require_connected", False)),
        timeout=int(params.get("timeout", 10)),
    )


def _display_cap(capability_registry: dict[str, Any] | None) -> Any:
    cap = (capability_registry or {}).get("display")
    if cap is None:
        return {"code": -2, "message": "display capability is not available", "details": {}, "metrics": {}}
    return cap


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).lower() in ("1", "true", "yes", "on")
