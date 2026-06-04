"""PCIe NVMe function helper library."""

from __future__ import annotations

from typing import Any


def detect(
    params: dict[str, Any],
    *,
    capability_registry: dict[str, Any] | None,
) -> dict[str, Any]:
    cap = _pcie_nvme_cap(capability_registry)
    if isinstance(cap, dict):
        return cap
    return cap.detect(
        expected_count=int(params.get("expected_count", 1)),
        required=_as_bool(params.get("required", True)),
        timeout=int(params.get("timeout", 10)),
    )


def _pcie_nvme_cap(capability_registry: dict[str, Any] | None) -> Any:
    cap = (capability_registry or {}).get("pcie_nvme")
    if cap is None:
        return {"code": -2, "message": "pcie_nvme capability is not available", "details": {}, "metrics": {}}
    return cap


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).lower() in ("1", "true", "yes", "on")
