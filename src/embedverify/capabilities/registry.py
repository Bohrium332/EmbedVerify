"""Capability registry construction."""

from __future__ import annotations

from typing import Any

from embedverify.core.models import BoardProfile

from .jetson import JetsonSystemInfoCapability
from .linux_generic import GenericStorageCapability, GenericUSBCapability
from .rk import RKSystemInfoCapability


def build_capability_registry(board: BoardProfile) -> dict[str, Any]:
    """Build capabilities for a board profile."""

    registry: dict[str, Any] = {}
    for name, implementation in board.capabilities.items():
        if name == "usb" and implementation == "linux_generic":
            registry[name] = GenericUSBCapability()
        elif name == "storage" and implementation == "linux_generic":
            registry[name] = GenericStorageCapability()
        elif name == "system_info" and implementation == "jetson":
            registry[name] = JetsonSystemInfoCapability()
        elif name == "system_info" and implementation == "rk":
            registry[name] = RKSystemInfoCapability()
    return registry

