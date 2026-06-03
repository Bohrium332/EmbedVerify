"""USB function helper library."""

from __future__ import annotations

from typing import Any


def detect_devices(
    params: dict[str, Any],
    *,
    capability_registry: dict[str, Any] | None,
) -> dict[str, Any]:
    """Detect USB devices through the selected board capability."""

    cap = (capability_registry or {}).get("usb")
    if cap is None:
        return {
            "code": -2,
            "message": "usb capability is not available",
            "details": {},
            "metrics": {},
        }
    return cap.detect(
        bus_type=str(params.get("bus_type", "any")),
        vendor_id=params.get("vendor_id"),
        product_id=params.get("product_id"),
        expected_count=int(params.get("expected_count", 1)),
        timeout=int(params.get("timeout", 10)),
    )

