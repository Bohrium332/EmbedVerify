"""Stable USB test functions."""

from __future__ import annotations

from typing import Any


def detect(
    *,
    bus_type: str = "any",
    vendor_id: str | None = None,
    product_id: str | None = None,
    expected_count: int = 1,
    timeout: int = 10,
    capability_registry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Detect USB devices with a stable output contract."""

    cap = (capability_registry or {}).get("usb")
    if cap is None:
        return {
            "code": -2,
            "message": "usb capability is not available",
            "details": {},
            "metrics": {},
        }
    return cap.detect(
        bus_type=bus_type,
        vendor_id=vendor_id,
        product_id=product_id,
        expected_count=expected_count,
        timeout=timeout,
    )
