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

        discovery = self.discover_usb_storage(timeout=timeout)
        resolved_device = "" if device == "auto" else device
        resolved_mount = "" if mount_point == "auto" else mount_point
        if not resolved_device and not resolved_mount and discovery:
            resolved_device = str(discovery.get("disk") or "")
            resolved_mount = str(discovery.get("mount_point") or "")
        if resolved_mount and not resolved_device:
            try:
                result = self.runner(["findmnt", "-n", "-o", "SOURCE", resolved_mount], 5)
                if result.returncode == 0:
                    resolved_device = result.stdout.strip()
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass

        cmd = [
            "lsblk",
            "--bytes",
            "--json",
            "-o",
            "NAME,PATH,SIZE,TYPE,FSTYPE,MOUNTPOINT,MODEL,SERIAL,VENDOR,ROTA,TRAN",
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
            "message": f"found {len(devices)} storage device(s)",
            "details": {
                "device": resolved_device,
                "mount_point": resolved_mount,
                "discovery": discovery,
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
        device: str = "auto",
        method: str = "auto",
        min_speed_mbps: float = 0,
        timeout: int = 120,
    ) -> dict[str, Any]:
        """Measure read speed from a block device."""

        discovery: dict[str, Any] | None = None
        resolved_device = "" if device == "auto" else device
        if not resolved_device:
            discovery = self.discover_usb_storage(timeout=10)
            resolved_device = str((discovery or {}).get("disk") or "")
        if not resolved_device:
            return _failed(-1, "USB storage device is required but was not auto-detected", {})
        if not Path(resolved_device).exists():
            return _failed(-1, "storage device not found", {"device": resolved_device})

        speed_mbps = 0.0
        method_used = ""
        if method in ("auto", "hdparm") and shutil.which("hdparm"):
            try:
                result = self.runner(["hdparm", "-t", resolved_device], timeout)
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
                    ["dd", f"if={resolved_device}", "of=/dev/null", "bs=1M", "count=256", "iflag=direct"],
                    timeout,
                )
            except subprocess.TimeoutExpired:
                return _failed(-1, "storage read test timed out", {"device": resolved_device})
            if result.returncode == 0:
                speed_mbps = _parse_dd_speed(result.stderr)
                if speed_mbps > 0:
                    method_used = "dd"

        success = speed_mbps > 0 and (min_speed_mbps <= 0 or speed_mbps >= min_speed_mbps)
        return {
            "code": 0 if success else -1,
            "message": (
                f"read speed: {speed_mbps:.1f} MB/s ({method_used})"
                if success
                else f"read speed {speed_mbps:.1f} MB/s below threshold {min_speed_mbps} MB/s"
            ),
            "details": {
                "device": resolved_device,
                "method_used": method_used,
                "min_speed_mbps": min_speed_mbps,
                "discovery": discovery,
            },
            "metrics": {"read_speed_mbps": round(speed_mbps, 2)},
        }

    def write_speed(
        self,
        *,
        mount_point: str = "auto",
        file_size_mb: int = 256,
        min_speed_mbps: float = 0,
        timeout: int = 120,
    ) -> dict[str, Any]:
        """Measure write speed by writing a temporary file to a mount point."""

        if not shutil.which("dd"):
            return _failed(-2, "dd not found: install coreutils", {"tool": "dd"})
        discovery: dict[str, Any] | None = None
        auto_mounted = False
        resolved_mount = "" if mount_point == "auto" else mount_point
        if not resolved_mount:
            discovery = self.discover_usb_storage(timeout=10)
            resolved_mount = str((discovery or {}).get("mount_point") or "")
        if not resolved_mount:
            if not discovery:
                discovery = self.discover_usb_storage(timeout=10)
            mount_result = self._auto_mount_usb_storage(discovery)
            if mount_result.get("code") != 0:
                return mount_result
            resolved_mount = str(mount_result["details"]["mount_point"])
            auto_mounted = True
        if not os.path.ismount(resolved_mount):
            return _failed(-1, "mount point is not mounted", {"mount_point": resolved_mount})

        test_file = str(Path(resolved_mount) / ".ev_write_test.bin")
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
            return _failed(-1, "storage write test timed out", {"mount_point": resolved_mount})
        finally:
            try:
                os.remove(test_file)
            except OSError:
                pass
            if auto_mounted:
                self._umount(resolved_mount)

        speed_mbps = _parse_dd_speed(result.stderr)
        success = speed_mbps > 0 and (min_speed_mbps <= 0 or speed_mbps >= min_speed_mbps)
        return {
            "code": 0 if success else -1,
            "message": (
                f"write speed: {speed_mbps:.1f} MB/s"
                if success
                else f"write speed {speed_mbps:.1f} MB/s below threshold {min_speed_mbps} MB/s"
            ),
            "details": {
                "mount_point": resolved_mount,
                "file_size_mb": file_size_mb,
                "min_speed_mbps": min_speed_mbps,
                "exit_code": result.returncode,
                "auto_mounted": auto_mounted,
                "discovery": discovery,
            },
            "metrics": {"write_speed_mbps": round(speed_mbps, 2)},
        }

    def discover_usb_storage(self, *, timeout: int = 10) -> dict[str, Any] | None:
        """Discover the first USB storage disk and preferred partition."""

        if not shutil.which("lsblk"):
            return None
        try:
            result = self.runner(
                [
                    "lsblk",
                    "--bytes",
                    "--json",
                    "-o",
                    "NAME,PATH,SIZE,TYPE,FSTYPE,MOUNTPOINT,MODEL,SERIAL,VENDOR,TRAN",
                ],
                timeout,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return None
        if result.returncode != 0:
            return None
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError:
            return None
        devices = data.get("blockdevices", [])
        if not isinstance(devices, list):
            return None
        return _select_usb_storage(devices)

    def _auto_mount_usb_storage(self, discovery: dict[str, Any] | None) -> dict[str, Any]:
        if not discovery:
            return _failed(-1, "USB storage partition was not auto-detected", {})
        partition = str(discovery.get("partition") or "")
        if not partition:
            return _failed(-1, "USB storage partition was not auto-detected", {"discovery": discovery})
        if os.geteuid() != 0:
            return _failed(
                -1,
                "USB storage is not mounted and auto-mount requires root",
                {"partition": partition},
            )
        mount_point = f"/mnt/embedverify-{Path(partition).name}"
        os.makedirs(mount_point, exist_ok=True)
        try:
            result = self.runner(["mount", partition, mount_point], 10)
        except subprocess.TimeoutExpired:
            return _failed(-1, "USB storage auto-mount timed out", {"partition": partition})
        if result.returncode != 0:
            return _failed(
                -1,
                result.stderr.strip() or "USB storage auto-mount failed",
                {"partition": partition, "mount_point": mount_point, "exit_code": result.returncode},
            )
        return {
            "code": 0,
            "message": f"auto-mounted USB storage at {mount_point}",
            "details": {"partition": partition, "mount_point": mount_point},
            "metrics": {},
        }

    def _umount(self, mount_point: str) -> None:
        try:
            self.runner(["umount", mount_point], 10)
        except Exception:
            pass


def _failed(code: int, message: str, details: dict[str, Any]) -> dict[str, Any]:
    return {"code": code, "message": message, "details": details, "metrics": {}}


def _select_usb_storage(devices: list[dict[str, Any]]) -> dict[str, Any] | None:
    for disk in devices:
        if disk.get("type") != "disk" or disk.get("tran") != "usb":
            continue
        disk_path = _node_path(disk)
        children = disk.get("children") or []
        partition_info = _select_partition(children)
        if partition_info is None:
            return {
                "disk": disk_path,
                "partition": "",
                "mount_point": "",
                "model": disk.get("model"),
                "serial": disk.get("serial"),
                "vendor": disk.get("vendor"),
                "size": disk.get("size"),
            }
        return {
            "disk": disk_path,
            "partition": partition_info["path"],
            "mount_point": partition_info["mount_point"],
            "fstype": partition_info["fstype"],
            "model": disk.get("model"),
            "serial": disk.get("serial"),
            "vendor": disk.get("vendor"),
            "size": disk.get("size"),
        }
    return None


def _select_partition(children: list[dict[str, Any]]) -> dict[str, Any] | None:
    partitions = [child for child in children if child.get("type") == "part"]
    mounted = [part for part in partitions if part.get("mountpoint")]
    candidates = mounted or partitions
    if not candidates:
        return None
    part = candidates[0]
    return {
        "path": _node_path(part),
        "mount_point": part.get("mountpoint") or "",
        "fstype": part.get("fstype") or "",
    }


def _node_path(node: dict[str, Any]) -> str:
    path = node.get("path")
    if isinstance(path, str) and path:
        return path
    name = str(node.get("name") or "")
    return f"/dev/{name}" if name else ""


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
    speed_by_device = _speed_map_from_tree(tree)
    devices: list[dict[str, Any]] = []
    for line in listing.splitlines():
        match = pattern.match(line.strip())
        if not match:
            continue
        bus = int(match.group(1))
        device = int(match.group(2))
        vid = match.group(3).lower()
        pid = match.group(4).lower()
        speed = speed_by_device.get((bus, device), "unknown")
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


def _speed_map_from_tree(tree: str) -> dict[tuple[int, int], str]:
    speeds: dict[tuple[int, int], str] = {}
    current_bus: int | None = None
    for line in tree.splitlines():
        bus_match = re.search(r"Bus\s+(\d+)", line)
        if bus_match:
            current_bus = int(bus_match.group(1))
        if current_bus is None:
            continue
        dev_match = re.search(r"Dev\s+(\d+)", line)
        if not dev_match:
            continue
        speed = _speed_from_tree_line(line)
        if speed != "unknown":
            speeds[(current_bus, int(dev_match.group(1)))] = speed
    return speeds


def _speed_from_tree_line(line: str) -> str:
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
