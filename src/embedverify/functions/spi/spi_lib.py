"""SPI function helper library."""

from __future__ import annotations

from typing import Any


def detect(
    params: dict[str, Any],
    *,
    capability_registry: dict[str, Any] | None,
) -> dict[str, Any]:
    cap = _spi_cap(capability_registry)
    if isinstance(cap, dict):
        return cap
    return cap.detect(
        device=str(params.get("device", "auto")),
        expected_count=int(params.get("expected_count", 1)),
        require_access=_as_bool(params.get("require_access", False)),
    )


def transfer(
    params: dict[str, Any],
    *,
    capability_registry: dict[str, Any] | None,
) -> dict[str, Any]:
    cap = _spi_cap(capability_registry)
    if isinstance(cap, dict):
        return cap
    tx_bytes = params.get("tx_bytes")
    return cap.transfer(
        device=str(params.get("device", "auto")),
        tx_hex=str(params.get("tx_hex", "")),
        tx_text=str(params.get("tx_text", "EV_SPI_TRANSFER")),
        tx_bytes=tx_bytes if isinstance(tx_bytes, list) else None,
        speed_hz=int(params.get("speed_hz", 500000)),
        mode=int(params.get("mode", 0)),
        bits_per_word=int(params.get("bits_per_word", 8)),
    )


def loopback(
    params: dict[str, Any],
    *,
    capability_registry: dict[str, Any] | None,
) -> dict[str, Any]:
    cap = _spi_cap(capability_registry)
    if isinstance(cap, dict):
        return cap
    return cap.loopback(
        device=str(params.get("device", "auto")),
        test_pattern=str(params.get("test_pattern", "EVSPI")),
        tx_hex=str(params.get("tx_hex", "")),
        speed_hz=int(params.get("speed_hz", 500000)),
        mode=int(params.get("mode", 0)),
        bits_per_word=int(params.get("bits_per_word", 8)),
    )


def _spi_cap(capability_registry: dict[str, Any] | None) -> Any:
    cap = (capability_registry or {}).get("spi")
    if cap is None:
        return {"code": -2, "message": "spi capability is not available", "details": {}, "metrics": {}}
    return cap


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).lower() in ("1", "true", "yes", "on")
