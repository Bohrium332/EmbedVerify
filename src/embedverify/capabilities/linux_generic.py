"""Generic Linux capability implementations."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from .base import CommandRunner, CommandResult, run_command


class GenericUSBCapability:
    """USB enumeration via Linux usbutils."""

    def __init__(self, runner: CommandRunner = run_command) -> None:
        self.runner = runner

    def detect(
        self,
        *,
        bus_type: str = "any",
        vendor_id: str | None = None,
        product_id: str | None = None,
        expected_count: int = 1,
        timeout: int = 10,
    ) -> dict[str, Any]:
        """Detect USB devices and return the stable Function contract."""

        if not shutil.which("lsusb"):
            return _failed(-2, "lsusb not found: install usbutils", {"tool": "lsusb"})

        try:
            tree = self.runner(["lsusb", "-t"], timeout).stdout
            listing = self.runner(["lsusb"], timeout).stdout
        except subprocess.TimeoutExpired:
            return _failed(-1, "USB detect timed out", {"timeout": timeout})

        devices = _parse_lsusb(listing, tree, bus_type, vendor_id, product_id)
        dmesg_errors = _recent_usb_dmesg_errors()
        success = len(devices) >= expected_count
        return {
            "code": 0 if success else -1,
            "status": "passed" if success else "failed",
            "message": (
                f"found {len(devices)} USB device(s)"
                if success
                else f"expected at least {expected_count} USB device(s), found {len(devices)}"
            ),
            "details": {
                "bus_type": bus_type,
                "vendor_id": vendor_id,
                "product_id": product_id,
                "expected_count": expected_count,
                "devices": devices,
                "dmesg_errors": dmesg_errors[-20:],
            },
            "metrics": {"device_count": len(devices)},
        }


class GenericStorageCapability:
    """Storage inspection and speed tests via common Linux tools."""

    def __init__(self, runner: CommandRunner = run_command) -> None:
        self.runner = runner

    def info(self, *, device: str = "", mount_point: str = "", timeout: int = 10) -> dict[str, Any]:
        """Return storage information using lsblk and findmnt."""

        if not shutil.which("lsblk"):
            return _failed(-2, "lsblk not found: install util-linux", {"tool": "lsblk"})

        resolved_device = device
        if mount_point and not resolved_device:
            try:
                result = self.runner(["findmnt", "-n", "-o", "SOURCE", mount_point], 5)
                if result.returncode == 0:
                    resolved_device = result.stdout.strip()
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass

        cmd = [
            "lsblk",
            "--bytes",
            "--json",
            "-o",
            "NAME,SIZE,TYPE,FSTYPE,MOUNTPOINT,MODEL,SERIAL,VENDOR,ROTA,TRAN",
        ]
        if resolved_device:
            cmd.append(resolved_device)

        try:
            result = self.runner(cmd, timeout)
        except subprocess.TimeoutExpired:
            return _failed(-1, "storage info query timed out", {"timeout": timeout})

        if result.returncode != 0:
            return _failed(
                -1,
                result.stderr.strip() or "lsblk failed",
                {"device": resolved_device, "exit_code": result.returncode},
            )

        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError:
            return _failed(-1, "failed to parse lsblk output", {"raw": result.stdout[:500]})

        devices = data.get("blockdevices", [])
        if not isinstance(devices, list) or not devices:
            return _failed(-1, "no storage device found", {"device": resolved_device})

        return {
            "code": 0,
            "status": "passed",
            "message": f"found {len(devices)} storage device(s)",
            "details": {
                "device": resolved_device,
                "mount_point": mount_point,
                "blockdevices": devices,
            },
            "metrics": {
                "device_count": len(devices),
                "partition_count": _count_partitions(devices),
                "total_size_bytes": _sum_sizes(devices),
            },
        }

    def read_speed(
        self,
        *,
        device: str,
        method: str = "auto",
        min_speed_mbps: float = 0,
        timeout: int = 120,
    ) -> dict[str, Any]:
        """Measure read speed from a block device."""

        if not device:
            return _failed(-1, "device is required", {})
        if not Path(device).exists():
            return _failed(-1, "storage device not found", {"device": device})

        speed_mbps = 0.0
        method_used = ""
        if method in ("auto", "hdparm") and shutil.which("hdparm"):
            try:
                result = self.runner(["hdparm", "-t", device], timeout)
                if result.returncode == 0:
                    match = re.search(r"=\s*([\d.]+)\s*MB/sec", result.stdout)
                    if match:
                        speed_mbps = float(match.group(1))
                        method_used = "hdparm"
            except subprocess.TimeoutExpired:
                pass

        if method in ("auto", "dd") and speed_mbps <= 0:
            if not shutil.which("dd"):
                return _failed(-2, "dd not found: install coreutils", {"tool": "dd"})
            try:
                result = self.runner(
                    ["dd", f"if={device}", "of=/dev/null", "bs=1M", "count=256", "iflag=direct"],
                    timeout,
                )
            except subprocess.TimeoutExpired:
                return _failed(-1, "storage read test timed out", {"device": device})
            if result.returncode == 0:
                speed_mbps = _parse_dd_speed(result.stderr)
                if speed_mbps > 0:
                    method_used = "dd"

        success = speed_mbps > 0 and (min_speed_mbps <= 0 or speed_mbps >= min_speed_mbps)
        return {
            "code": 0 if success else -1,
            "status": "passed" if success else "failed",
            "message": (
                f"read speed: {speed_mbps:.1f} MB/s ({method_used})"
                if success
                else f"read speed {speed_mbps:.1f} MB/s below threshold {min_speed_mbps} MB/s"
            ),
            "details": {
                "device": device,
                "method_used": method_used,
                "min_speed_mbps": min_speed_mbps,
            },
            "metrics": {"read_speed_mbps": round(speed_mbps, 2)},
        }

    def write_speed(
        self,
        *,
        mount_point: str,
        file_size_mb: int = 256,
        min_speed_mbps: float = 0,
        timeout: int = 120,
    ) -> dict[str, Any]:
        """Measure write speed by writing a temporary file to a mount point."""

        if not shutil.which("dd"):
            return _failed(-2, "dd not found: install coreutils", {"tool": "dd"})
        if not mount_point:
            return _failed(-1, "mount_point is required", {})
        if not os.path.ismount(mount_point):
            return _failed(-1, "mount point is not mounted", {"mount_point": mount_point})

        test_file = str(Path(mount_point) / ".ev_write_test.bin")
        try:
            result = self.runner(
                [
                    "dd",
                    "if=/dev/zero",
                    f"of={test_file}",
                    "bs=1M",
                    f"count={int(file_size_mb)}",
                    "oflag=direct",
                    "conv=fdatasync",
                ],
                timeout,
            )
        except subprocess.TimeoutExpired:
            return _failed(-1, "storage write test timed out", {"mount_point": mount_point})
        finally:
            try:
                os.remove(test_file)
            except OSError:
                pass

        speed_mbps = _parse_dd_speed(result.stderr)
        success = speed_mbps > 0 and (min_speed_mbps <= 0 or speed_mbps >= min_speed_mbps)
        return {
            "code": 0 if success else -1,
            "status": "passed" if success else "failed",
            "message": (
                f"write speed: {speed_mbps:.1f} MB/s"
                if success
                else f"write speed {speed_mbps:.1f} MB/s below threshold {min_speed_mbps} MB/s"
            ),
            "details": {
                "mount_point": mount_point,
                "file_size_mb": file_size_mb,
                "min_speed_mbps": min_speed_mbps,
                "exit_code": result.returncode,
            },
            "metrics": {"write_speed_mbps": round(speed_mbps, 2)},
        }


def _failed(code: int, message: str, details: dict[str, Any]) -> dict[str, Any]:
    return {"code": code, "status": "failed", "message": message, "details": details, "metrics": {}}


def _parse_lsusb(
    listing: str,
    tree: str,
    bus_type: str,
    vendor_id: str | None,
    product_id: str | None,
) -> list[dict[str, Any]]:
    pattern = re.compile(
        r"Bus\s+(\d+)\s+Device\s+(\d+):\s+ID\s+([0-9a-fA-F]{4}):([0-9a-fA-F]{4})\s+(.*)"
    )
    devices: list[dict[str, Any]] = []
    for line in listing.splitlines():
        match = pattern.match(line.strip())
        if not match:
            continue
        bus = int(match.group(1))
        device = int(match.group(2))
        vid = match.group(3).lower()
        pid = match.group(4).lower()
        speed = _speed_for_bus(tree, bus)
        if bus_type == "usb2" and speed not in ("480M", "12M", "1.5M", "unknown"):
            continue
        if bus_type == "usb3" and speed not in ("5G", "10G", "20G", "unknown"):
            continue
        if vendor_id and vid != vendor_id.lower():
            continue
        if product_id and pid != product_id.lower():
            continue
        devices.append(
            {
                "bus": bus,
                "device": device,
                "vendor_id": vid,
                "product_id": pid,
                "description": match.group(5).strip(),
                "speed": speed,
            }
        )
    return devices


def _speed_for_bus(tree: str, bus: int) -> str:
    bus_pattern = re.compile(rf"Bus\s+{bus:02d}\.")
    for line in tree.splitlines():
        if bus_pattern.search(line) or f"Bus {bus}" in line:
            for marker, speed in (
                ("20000M", "20G"),
                ("10000M", "10G"),
                ("5000M", "5G"),
                ("480M", "480M"),
                ("12M", "12M"),
                ("1.5M", "1.5M"),
            ):
                if marker in line:
                    return speed
    return "unknown"


def _recent_usb_dmesg_errors() -> list[str]:
    if not shutil.which("dmesg"):
        return []
    try:
        result = run_command(["dmesg"], 5)
    except Exception:
        return []
    errors = []
    for line in result.stdout.splitlines():
        low = line.lower()
        if "usb" in low and ("error" in low or "fail" in low or "unable" in low):
            errors.append(line.strip())
    return errors


def _parse_dd_speed(stderr: str) -> float:
    patterns = [
        r"([\d.]+)\s*MB/s",
        r"([\d.]+)\s*GB/s",
        r"([\d.]+)\s*kB/s",
        r"([\d.]+)\s*bytes/s",
    ]
    for pattern in patterns:
        match = re.search(pattern, stderr)
        if not match:
            continue
        value = float(match.group(1))
        if "GB/s" in pattern:
            return value * 1000
        if "kB/s" in pattern:
            return value / 1000
        if "bytes/s" in pattern:
            return value / 1_000_000
        return value
    return 0.0


def _count_partitions(devices: list[dict[str, Any]]) -> int:
    total = 0
    for dev in devices:
        children = dev.get("children") or []
        total += len(children)
        for child in children:
            total += len(child.get("children") or [])
    return total


def _sum_sizes(devices: list[dict[str, Any]]) -> int:
    total = 0
    for dev in devices:
        try:
            total += int(dev.get("size") or 0)
        except (TypeError, ValueError):
            pass
    return total

