"""Capability registry construction."""

from __future__ import annotations

from typing import Any

from embedverify.core.models import BoardProfile

from .jetson import JetsonSystemInfoCapability
from .linux_generic import (
    GenericBluetoothCapability,
    GenericCameraCapability,
    GenericDisplayCapability,
    GenericFanCapability,
    GenericGPIOCapability,
    GenericI2CCapability,
    GenericNetworkCapability,
    GenericPCIeNVMeCapability,
    GenericRTCCapability,
    GenericStorageCapability,
    GenericUARTCapability,
    GenericUSBCapability,
    GenericWiFiCapability,
)
from .rk import RKSystemInfoCapability


def build_capability_registry(board: BoardProfile) -> dict[str, Any]:
    """Build capabilities for a board profile."""

    registry: dict[str, Any] = {}
    for name, implementation in board.capabilities.items():
        if name == "usb" and implementation == "linux_generic":
            registry[name] = GenericUSBCapability()
        elif name == "storage" and implementation == "linux_generic":
            registry[name] = GenericStorageCapability()
        elif name == "network" and implementation == "linux_generic":
            registry[name] = GenericNetworkCapability()
        elif name == "pcie_nvme" and implementation == "linux_generic":
            registry[name] = GenericPCIeNVMeCapability()
        elif name == "rtc" and implementation == "linux_generic":
            registry[name] = GenericRTCCapability()
        elif name == "fan" and implementation == "linux_generic":
            registry[name] = GenericFanCapability()
        elif name == "gpio" and implementation == "linux_generic":
            registry[name] = GenericGPIOCapability()
        elif name == "i2c" and implementation == "linux_generic":
            registry[name] = GenericI2CCapability()
        elif name == "camera" and implementation == "linux_generic":
            registry[name] = GenericCameraCapability()
        elif name == "wifi" and implementation == "linux_generic":
            registry[name] = GenericWiFiCapability()
        elif name == "bluetooth" and implementation == "linux_generic":
            registry[name] = GenericBluetoothCapability()
        elif name == "display" and implementation == "linux_generic":
            registry[name] = GenericDisplayCapability()
        elif name == "uart" and implementation == "linux_generic":
            registry[name] = GenericUARTCapability()
        elif name == "system_info" and implementation == "jetson":
            registry[name] = JetsonSystemInfoCapability()
        elif name == "system_info" and implementation == "rk":
            registry[name] = RKSystemInfoCapability()
    return registry
