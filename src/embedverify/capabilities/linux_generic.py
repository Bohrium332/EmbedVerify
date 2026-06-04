"""Generic Linux capability implementations."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time
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

    def detect(
        self,
        *,
        device: str = "",
        expected_type: str = "",
        min_size_bytes: int = 0,
        transport: str = "",
        timeout: int = 10,
    ) -> dict[str, Any]:
        """Detect storage devices with optional filters."""

        if not shutil.which("lsblk"):
            return _failed(-2, "lsblk not found: install util-linux", {"tool": "lsblk"})

        cmd = [
            "lsblk",
            "--bytes",
            "--json",
            "-o",
            "NAME,PATH,SIZE,TYPE,FSTYPE,MOUNTPOINT,MODEL,SERIAL,VENDOR,ROTA,TRAN,LOG-SEC",
        ]
        if device and device != "auto":
            cmd.append(device)
        try:
            result = self.runner(cmd, timeout)
        except subprocess.TimeoutExpired:
            return _failed(1, "storage detect timed out", {"device": device, "timeout": timeout})

        if result.returncode != 0:
            return _failed(
                -1,
                result.stderr.strip() or "lsblk failed",
                {"device": device, "exit_code": result.returncode},
            )

        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError:
            return _failed(-1, "failed to parse lsblk output", {"raw": result.stdout[:500]})

        devices = _flatten_blockdevices(data.get("blockdevices", []))
        filtered = []
        for item in devices:
            if expected_type and item.get("type") != expected_type:
                continue
            if transport and item.get("tran") != transport:
                continue
            try:
                size = int(item.get("size") or 0)
            except (TypeError, ValueError):
                size = 0
            if min_size_bytes and size < min_size_bytes:
                continue
            filtered.append(item)

        success = bool(filtered)
        return {
            "code": 0 if success else -1,
            "message": (
                f"found {len(filtered)} storage device(s)"
                if success
                else "no storage devices matched filters"
            ),
            "details": {
                "device": device,
                "expected_type": expected_type,
                "min_size_bytes": min_size_bytes,
                "transport": transport,
                "devices": filtered,
            },
            "metrics": {"device_count": len(filtered)},
        }

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
        device: str = "",
        mount_point: str = "auto",
        file_size_mb: int = 256,
        min_speed_mbps: float = 0,
        timeout: int = 120,
    ) -> dict[str, Any]:
        """Measure write speed by writing a temporary file to a mount point."""

        if not shutil.which("dd"):
            return _failed(-2, "dd not found: install coreutils", {"tool": "dd"})

        mount = self._prepare_write_mount(device=device, mount_point=mount_point)
        if mount["code"] != 0:
            return mount
        resolved_mount = str(mount["details"]["mount_point"])
        auto_mounted = bool(mount["details"]["auto_mounted"])
        mount_source = str(mount["details"]["mount_source"])
        mount_options = str(mount["details"]["mount_options"])
        discovery = mount["details"]["discovery"]

        test_file = str(Path(resolved_mount) / ".ev_write_test.bin")
        base_details = {
            "mount_point": resolved_mount,
            "mount_source": mount_source,
            "mount_options": mount_options,
            "file_size_mb": file_size_mb,
            "min_speed_mbps": min_speed_mbps,
            "auto_mounted": auto_mounted,
            "discovery": discovery,
        }
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
            return _failed(
                1,
                "storage write test timed out",
                base_details | {"dmesg_errors": _recent_storage_dmesg_errors(mount_source)},
            )
        finally:
            try:
                os.remove(test_file)
            except OSError:
                pass
            if auto_mounted:
                self._umount(resolved_mount)

        speed_mbps = _parse_dd_speed(result.stderr)
        if result.returncode != 0:
            return _failed(
                -1,
                "storage write test failed",
                base_details
                | {
                    "exit_code": result.returncode,
                    "stderr_tail": _tail_text(result.stderr),
                    "dmesg_errors": _recent_storage_dmesg_errors(mount_source),
                },
            )

        success = speed_mbps > 0 and (min_speed_mbps <= 0 or speed_mbps >= min_speed_mbps)
        return {
            "code": 0 if success else -1,
            "message": (
                f"write speed: {speed_mbps:.1f} MB/s"
                if success
                else f"write speed {speed_mbps:.1f} MB/s below threshold {min_speed_mbps} MB/s"
            ),
            "details": base_details | {"exit_code": result.returncode},
            "metrics": {"write_speed_mbps": round(speed_mbps, 2)},
        }

    def integrity_check(
        self,
        *,
        device: str = "",
        mount_point: str = "auto",
        file_size_mb: int = 64,
        timeout: int = 300,
    ) -> dict[str, Any]:
        """Write random data, read it back, and compare SHA256 hashes."""

        import hashlib

        mount = self._prepare_write_mount(device=device, mount_point=mount_point)
        if mount["code"] != 0:
            return mount
        resolved_mount = str(mount["details"]["mount_point"])
        auto_mounted = bool(mount["details"]["auto_mounted"])
        test_file = str(Path(resolved_mount) / ".ev_integrity_test.bin")
        write_hash = ""
        read_hash = ""
        write_time_s = 0.0
        read_time_s = 0.0

        try:
            start = time.monotonic()
            h = hashlib.sha256()
            deadline = start + timeout
            with open(test_file, "wb") as handle:
                for _ in range(int(file_size_mb)):
                    if time.monotonic() > deadline:
                        return _failed(1, "storage integrity write timed out", {"file_size_mb": file_size_mb})
                    chunk = os.urandom(1 << 20)
                    h.update(chunk)
                    handle.write(chunk)
                handle.flush()
                os.fsync(handle.fileno())
            write_hash = h.hexdigest()
            write_time_s = time.monotonic() - start

            start = time.monotonic()
            h = hashlib.sha256()
            with open(test_file, "rb") as handle:
                while True:
                    if time.monotonic() > start + timeout:
                        return _failed(1, "storage integrity read timed out", {"file_size_mb": file_size_mb})
                    chunk = handle.read(1 << 20)
                    if not chunk:
                        break
                    h.update(chunk)
            read_hash = h.hexdigest()
            read_time_s = time.monotonic() - start
        finally:
            try:
                os.remove(test_file)
            except OSError:
                pass
            if auto_mounted:
                self._umount(resolved_mount)

        integrity_match = bool(write_hash) and write_hash == read_hash
        return {
            "code": 0 if integrity_match else -1,
            "message": "data integrity verified" if integrity_match else "data integrity check failed",
            "details": {
                "mount_point": resolved_mount,
                "mount_source": mount["details"]["mount_source"],
                "file_size_mb": file_size_mb,
                "auto_mounted": auto_mounted,
                "discovery": mount["details"]["discovery"],
                "integrity_match": integrity_match,
                "write_hash": f"{write_hash[:16]}..." if write_hash else "",
                "read_hash": f"{read_hash[:16]}..." if read_hash else "",
            },
            "metrics": {
                "integrity_match": integrity_match,
                "write_speed_mbps": round(file_size_mb / max(write_time_s, 0.001), 2),
                "read_speed_mbps": round(file_size_mb / max(read_time_s, 0.001), 2),
                "write_time_s": round(write_time_s, 2),
                "read_time_s": round(read_time_s, 2),
            },
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
        health = self._ext_filesystem_health(partition, str(discovery.get("fstype") or ""))
        if health.get("checked") and not health.get("safe_to_mount"):
            return _failed(
                -1,
                "USB storage filesystem is not clean; repair required before write test",
                {
                    "partition": partition,
                    "fstype": discovery.get("fstype"),
                    "filesystem_health": health,
                    "dmesg_errors": _recent_storage_dmesg_errors(partition),
                },
            )
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

    def _prepare_write_mount(self, *, device: str = "", mount_point: str = "auto") -> dict[str, Any]:
        discovery: dict[str, Any] | None = None
        auto_mounted = False
        resolved_device = "" if device == "auto" else device
        resolved_mount = "" if mount_point == "auto" else mount_point
        if not resolved_mount and resolved_device:
            discovery = self._discovery_from_device(resolved_device)
            resolved_mount = str((discovery or {}).get("mount_point") or "")
        if not resolved_mount:
            if not discovery:
                discovery = self.discover_usb_storage(timeout=10)
            resolved_mount = str((discovery or {}).get("mount_point") or "")
        if not resolved_mount:
            mount_result = self._auto_mount_usb_storage(discovery)
            if mount_result.get("code") != 0:
                return mount_result
            resolved_mount = str(mount_result["details"]["mount_point"])
            auto_mounted = True
        if not os.path.ismount(resolved_mount):
            return _failed(-1, "mount point is not mounted", {"mount_point": resolved_mount})

        mount_source = self._mount_source(resolved_mount)
        mount_options = self._mount_options(resolved_mount)
        if "ro" in mount_options.split(","):
            if auto_mounted:
                self._umount(resolved_mount)
            return _failed(
                -1,
                "mount point is read-only",
                {
                    "mount_point": resolved_mount,
                    "mount_source": mount_source,
                    "mount_options": mount_options,
                    "dmesg_errors": _recent_storage_dmesg_errors(mount_source),
                },
            )
        return {
            "code": 0,
            "message": "mount point is ready for write test",
            "details": {
                "mount_point": resolved_mount,
                "mount_source": mount_source,
                "mount_options": mount_options,
                "auto_mounted": auto_mounted,
                "discovery": discovery,
            },
            "metrics": {},
        }

    def _discovery_from_device(self, device: str) -> dict[str, Any] | None:
        path = str(Path(device))
        if not Path(path).exists():
            return None
        mount_point = self._mount_target(path)
        return {
            "disk": path,
            "partition": path,
            "mount_point": mount_point,
            "fstype": self._fstype(path),
            "whole_disk_filesystem": True,
        }

    def _mount_source(self, mount_point: str) -> str:
        try:
            result = self.runner(["findmnt", "-n", "-o", "SOURCE", mount_point], 5)
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return ""
        if result.returncode != 0:
            return ""
        return result.stdout.strip()

    def _mount_options(self, mount_point: str) -> str:
        try:
            result = self.runner(["findmnt", "-n", "-o", "OPTIONS", mount_point], 5)
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return ""
        if result.returncode != 0:
            return ""
        return result.stdout.strip()

    def _mount_target(self, device: str) -> str:
        try:
            result = self.runner(["findmnt", "-n", "-o", "TARGET", device], 5)
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return ""
        if result.returncode != 0:
            return ""
        return result.stdout.strip()

    def _fstype(self, device: str) -> str:
        try:
            result = self.runner(["lsblk", "-n", "-o", "FSTYPE", device], 5)
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return ""
        if result.returncode != 0:
            return ""
        return result.stdout.strip().splitlines()[0] if result.stdout.strip() else ""

    def _ext_filesystem_health(self, partition: str, fstype: str) -> dict[str, Any]:
        if fstype not in ("ext2", "ext3", "ext4"):
            return {"checked": False, "reason": f"fstype {fstype or 'unknown'} is not ext"}
        if not shutil.which("tune2fs"):
            return {"checked": False, "reason": "tune2fs not found"}
        try:
            result = self.runner(["tune2fs", "-l", partition], 10)
        except subprocess.TimeoutExpired:
            return {"checked": False, "reason": "tune2fs timed out", "partition": partition}
        except FileNotFoundError:
            return {"checked": False, "reason": "tune2fs not found"}
        health = _parse_tune2fs_health(result.stdout)
        health["partition"] = partition
        health["fstype"] = fstype
        health["exit_code"] = result.returncode
        if result.returncode != 0:
            health["checked"] = False
            health["reason"] = _tail_text(result.stderr) or "tune2fs failed"
        return health


class GenericNetworkCapability:
    """Network interface checks via common Linux tools and sysfs."""

    def __init__(self, runner: CommandRunner = run_command) -> None:
        self.runner = runner

    def list_interfaces(
        self,
        *,
        include_loopback: bool = False,
        expected_count: int = 1,
        timeout: int = 10,
    ) -> dict[str, Any]:
        interfaces = self._interfaces(timeout)
        if not include_loopback:
            interfaces = [item for item in interfaces if item.get("name") != "lo"]
        success = len(interfaces) >= expected_count
        return {
            "code": 0 if success else -1,
            "message": (
                f"found {len(interfaces)} network interface(s)"
                if success
                else f"expected at least {expected_count} network interface(s), found {len(interfaces)}"
            ),
            "details": {
                "include_loopback": include_loopback,
                "expected_count": expected_count,
                "interfaces": interfaces,
            },
            "metrics": {"interface_count": len(interfaces)},
        }

    def link_status(
        self,
        *,
        interface: str = "auto",
        require_up: bool = True,
        require_carrier: bool = False,
        timeout: int = 10,
    ) -> dict[str, Any]:
        interfaces = self._interfaces(timeout)
        default_interface, gateway = self._default_route(timeout)
        resolved = default_interface if interface == "auto" else interface
        if not resolved:
            resolved = _first_non_loopback(interfaces)
        match = next((item for item in interfaces if item.get("name") == resolved), None)
        if not match:
            return _failed(
                -1,
                "network interface not found",
                {
                    "interface": interface,
                    "resolved_interface": resolved,
                    "available_interfaces": [item.get("name") for item in interfaces],
                },
            )

        operstate = str(match.get("operstate") or "").lower()
        carrier = match.get("carrier")
        link_up = operstate == "up"
        carrier_ok = carrier is True or carrier is None
        success = (not require_up or link_up) and (not require_carrier or carrier_ok)
        return {
            "code": 0 if success else -1,
            "message": (
                f"{resolved} link is usable"
                if success
                else f"{resolved} link is not usable: operstate={operstate}, carrier={carrier}"
            ),
            "details": {
                "interface": interface,
                "resolved_interface": resolved,
                "default_gateway": gateway,
                "require_up": require_up,
                "require_carrier": require_carrier,
                "link": match,
            },
            "metrics": {
                "link_up": link_up,
                "carrier": carrier,
                "speed_mbps": match.get("speed_mbps"),
            },
        }

    def ping(
        self,
        *,
        host: str = "gateway",
        count: int = 3,
        timeout: int = 10,
        interface: str = "",
    ) -> dict[str, Any]:
        if not shutil.which("ping"):
            return _failed(-2, "ping not found: install iputils-ping", {"tool": "ping"})
        target = host
        default_interface, gateway = self._default_route(timeout)
        if host in ("auto", "gateway"):
            target = gateway
        if not target:
            return _failed(-1, "ping target could not be resolved", {"host": host})

        per_packet_timeout = max(1, int(timeout / max(count, 1)))
        cmd = ["ping", "-c", str(count), "-W", str(per_packet_timeout)]
        resolved_interface = interface or default_interface
        if interface:
            cmd.extend(["-I", interface])
        cmd.append(target)
        try:
            result = self.runner(cmd, timeout)
        except subprocess.TimeoutExpired:
            return _failed(-1, "ping timed out", {"target": target, "timeout": timeout})

        metrics = _parse_ping_metrics(result.stdout)
        success = result.returncode == 0 and int(metrics.get("packets_received", 0)) > 0
        return {
            "code": 0 if success else -1,
            "message": (
                f"ping {target} ok"
                if success
                else f"ping {target} failed"
            ),
            "details": {
                "host": host,
                "target": target,
                "interface": resolved_interface,
                "exit_code": result.returncode,
                "stdout_tail": _tail_text(result.stdout, 1200),
                "stderr_tail": _tail_text(result.stderr, 1200),
            },
            "metrics": metrics,
        }

    def _interfaces(self, timeout: int) -> list[dict[str, Any]]:
        if shutil.which("ip"):
            try:
                result = self.runner(["ip", "-j", "addr"], timeout)
            except (subprocess.TimeoutExpired, FileNotFoundError):
                result = CommandResult(1, "", "")
            if result.returncode == 0:
                try:
                    data = json.loads(result.stdout)
                    if isinstance(data, list):
                        return _parse_ip_addr_json(data)
                except json.JSONDecodeError:
                    pass
        return _interfaces_from_sysfs()

    def _default_route(self, timeout: int) -> tuple[str, str]:
        if not shutil.which("ip"):
            return "", ""
        try:
            result = self.runner(["ip", "route", "show", "default"], timeout)
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return "", ""
        if result.returncode != 0:
            return "", ""
        return _parse_default_route(result.stdout)


class GenericPCIeNVMeCapability:
    """PCIe/NVMe discovery via lsblk and sysfs."""

    def __init__(self, runner: CommandRunner = run_command) -> None:
        self.runner = runner

    def detect(
        self,
        *,
        expected_count: int = 1,
        required: bool = True,
        timeout: int = 10,
    ) -> dict[str, Any]:
        devices: list[dict[str, Any]] = []
        lsblk_error = ""
        lsblk_available = bool(shutil.which("lsblk"))
        if lsblk_available:
            cmd = [
                "lsblk",
                "--bytes",
                "--json",
                "-o",
                "NAME,PATH,SIZE,TYPE,MODEL,SERIAL,VENDOR,TRAN",
            ]
            try:
                result = self.runner(cmd, timeout)
            except subprocess.TimeoutExpired:
                return _failed(-1, "NVMe detect timed out", {"timeout": timeout})
            if result.returncode == 0:
                try:
                    data = json.loads(result.stdout)
                    devices = _filter_nvme_block_devices(_flatten_blockdevices(data.get("blockdevices", [])))
                except json.JSONDecodeError:
                    lsblk_error = "failed to parse lsblk output"
            else:
                lsblk_error = result.stderr.strip() or "lsblk failed"

        controllers = _sysfs_children("/sys/class/nvme")
        found_count = len(devices) if lsblk_available and not lsblk_error else max(len(devices), len(controllers))
        success = found_count >= expected_count
        if not success and not required:
            success = True
        return {
            "code": 0 if success else -1,
            "message": (
                f"found {found_count} NVMe device(s)"
                if found_count
                else ("optional NVMe device not present" if not required else "no NVMe device detected")
            ),
            "details": {
                "expected_count": expected_count,
                "required": required,
                "devices": devices,
                "controllers": controllers,
                "lsblk_error": lsblk_error,
            },
            "metrics": {"device_count": found_count},
        }


class GenericRTCCapability:
    """RTC read-only checks."""

    def __init__(self, runner: CommandRunner = run_command) -> None:
        self.runner = runner

    def list_devices(self, *, expected_count: int = 1) -> dict[str, Any]:
        devices = _rtc_devices()
        success = len(devices) >= expected_count
        return {
            "code": 0 if success else -1,
            "message": (
                f"found {len(devices)} RTC device(s)"
                if success
                else f"expected at least {expected_count} RTC device(s), found {len(devices)}"
            ),
            "details": {"expected_count": expected_count, "devices": devices},
            "metrics": {"device_count": len(devices)},
        }

    def read(self, *, device: str = "auto", timeout: int = 10) -> dict[str, Any]:
        devices = _rtc_devices()
        resolved = devices[0]["path"] if device == "auto" and devices else device
        if not resolved:
            return _failed(-1, "RTC device not found", {"device": device})

        source = ""
        raw = ""
        if shutil.which("hwclock"):
            try:
                result = self.runner(["hwclock", "--show", "--rtc", resolved], timeout)
            except (subprocess.TimeoutExpired, FileNotFoundError):
                result = CommandResult(1, "", "")
            if result.returncode == 0 and result.stdout.strip():
                source = "hwclock"
                raw = result.stdout.strip()

        if not raw:
            name = Path(resolved).name
            date_text = _read_text(Path("/sys/class/rtc") / name / "date")
            time_text = _read_text(Path("/sys/class/rtc") / name / "time")
            if date_text and time_text:
                source = "sysfs"
                raw = f"{date_text} {time_text}"

        success = bool(raw)
        return {
            "code": 0 if success else -1,
            "message": f"RTC read ok from {resolved}" if success else f"RTC read failed from {resolved}",
            "details": {"device": resolved, "source": source, "raw": raw},
            "metrics": {"readable": success},
        }


class GenericFanCapability:
    """Read fan telemetry from Linux hwmon/sysfs."""

    def info(
        self,
        *,
        expected_count: int = 1,
        min_rpm: int = 0,
    ) -> dict[str, Any]:
        fans = _fan_hwmon_entries()
        rpm_values = [
            int(value)
            for fan in fans
            for value in fan.get("rpm_values", [])
            if isinstance(value, int)
        ]
        max_rpm = max(rpm_values) if rpm_values else 0
        success = len(fans) >= expected_count and max_rpm >= min_rpm
        return {
            "code": 0 if success else -1,
            "message": (
                f"found {len(fans)} fan hwmon entry(s)"
                if success
                else f"fan requirement not met: count={len(fans)}, max_rpm={max_rpm}"
            ),
            "details": {
                "expected_count": expected_count,
                "min_rpm": min_rpm,
                "fans": fans,
            },
            "metrics": {
                "fan_count": len(fans),
                "max_rpm": max_rpm,
            },
        }


class GenericGPIOCapability:
    """GPIO chip discovery via libgpiod tools and /dev."""

    def __init__(self, runner: CommandRunner = run_command) -> None:
        self.runner = runner

    def list_chips(self, *, expected_count: int = 1, timeout: int = 10) -> dict[str, Any]:
        chips = _gpio_chips_from_dev()
        if shutil.which("gpiodetect"):
            try:
                result = self.runner(["gpiodetect"], timeout)
            except (subprocess.TimeoutExpired, FileNotFoundError):
                result = CommandResult(1, "", "")
            if result.returncode == 0:
                chips = _merge_gpio_chip_info(chips, result.stdout)

        success = len(chips) >= expected_count
        return {
            "code": 0 if success else -1,
            "message": (
                f"found {len(chips)} GPIO chip(s)"
                if success
                else f"expected at least {expected_count} GPIO chip(s), found {len(chips)}"
            ),
            "details": {"expected_count": expected_count, "chips": chips},
            "metrics": {"chip_count": len(chips)},
        }

    def line_info(self, *, chip: str = "auto", line: int | None = None, timeout: int = 10) -> dict[str, Any]:
        chips = _gpio_chips_from_dev()
        resolved = chips[0]["path"] if chip == "auto" and chips else chip
        if not resolved:
            return _failed(-1, "GPIO chip not found", {"chip": chip})
        if not shutil.which("gpioinfo"):
            if line is None:
                return {
                    "code": 0,
                    "message": f"GPIO chip {resolved} exists; gpioinfo is not installed",
                    "details": {"chip": resolved, "line": line, "tool": "gpioinfo", "tool_available": False},
                    "metrics": {"line_count": 0},
                }
            return _failed(-2, "gpioinfo not found: install gpiod", {"tool": "gpioinfo", "chip": resolved})

        cmd = ["gpioinfo", resolved]
        try:
            result = self.runner(cmd, timeout)
        except subprocess.TimeoutExpired:
            return _failed(-1, "gpioinfo timed out", {"chip": resolved, "timeout": timeout})
        if result.returncode != 0:
            return _failed(
                -1,
                result.stderr.strip() or "gpioinfo failed",
                {"chip": resolved, "exit_code": result.returncode},
            )
        raw_lines = [item.strip() for item in result.stdout.splitlines() if item.strip()]
        matching_lines = raw_lines
        if line is not None:
            pattern = re.compile(rf"line\s+{int(line)}\b")
            matching_lines = [item for item in raw_lines if pattern.search(item)]
        success = bool(matching_lines)
        return {
            "code": 0 if success else -1,
            "message": (
                f"GPIO line info available for {resolved}"
                if success
                else f"GPIO line {line} not found on {resolved}"
            ),
            "details": {
                "chip": resolved,
                "line": line,
                "lines": matching_lines[:200],
            },
            "metrics": {"line_count": len(raw_lines), "matched_line_count": len(matching_lines)},
        }


class GenericI2CCapability:
    """I2C bus discovery and optional bus scan."""

    def __init__(self, runner: CommandRunner = run_command) -> None:
        self.runner = runner

    def list_buses(self, *, expected_count: int = 1, timeout: int = 10) -> dict[str, Any]:
        buses = self._buses(timeout)
        success = len(buses) >= expected_count
        return {
            "code": 0 if success else -1,
            "message": (
                f"found {len(buses)} I2C bus(es)"
                if success
                else f"expected at least {expected_count} I2C bus(es), found {len(buses)}"
            ),
            "details": {"expected_count": expected_count, "buses": buses},
            "metrics": {"bus_count": len(buses)},
        }

    def scan(
        self,
        *,
        bus: str = "auto",
        expected_addresses: list[Any] | None = None,
        min_device_count: int = 0,
        timeout: int = 10,
    ) -> dict[str, Any]:
        if not shutil.which("i2cdetect"):
            return _failed(-2, "i2cdetect not found: install i2c-tools", {"tool": "i2cdetect"})
        buses = self._buses(timeout)
        resolved = _normalize_i2c_bus(bus)
        if resolved is None and buses:
            resolved = int(buses[0]["bus"])
        if resolved is None:
            return _failed(-1, "I2C bus not found", {"bus": bus, "available_buses": buses})

        try:
            result = self.runner(["i2cdetect", "-y", "-r", str(resolved)], timeout)
        except subprocess.TimeoutExpired:
            return _failed(-1, "i2cdetect timed out", {"bus": resolved, "timeout": timeout})
        if result.returncode != 0:
            return _failed(
                -1,
                result.stderr.strip() or "i2cdetect failed",
                {"bus": resolved, "exit_code": result.returncode},
            )

        addresses = _parse_i2cdetect_table(result.stdout)
        expected = _normalize_i2c_addresses(expected_addresses or [])
        missing = [address for address in expected if address not in addresses]
        success = len(addresses) >= min_device_count and not missing
        return {
            "code": 0 if success else -1,
            "message": (
                f"I2C bus {resolved} scan found {len(addresses)} device(s)"
                if success
                else f"I2C bus {resolved} scan did not meet expectations"
            ),
            "details": {
                "bus": resolved,
                "expected_addresses": [f"0x{item:02x}" for item in expected],
                "missing_addresses": [f"0x{item:02x}" for item in missing],
                "addresses": [f"0x{item:02x}" for item in addresses],
            },
            "metrics": {"device_count": len(addresses)},
        }

    def _buses(self, timeout: int) -> list[dict[str, Any]]:
        if shutil.which("i2cdetect"):
            try:
                result = self.runner(["i2cdetect", "-l"], timeout)
            except (subprocess.TimeoutExpired, FileNotFoundError):
                result = CommandResult(1, "", "")
            if result.returncode == 0:
                return _parse_i2cdetect_list(result.stdout)
        return _i2c_buses_from_dev()


def _failed(code: int, message: str, details: dict[str, Any]) -> dict[str, Any]:
    return {"code": code, "message": message, "details": details, "metrics": {}}


def _flatten_blockdevices(devices: Any) -> list[dict[str, Any]]:
    if not isinstance(devices, list):
        return []
    flattened: list[dict[str, Any]] = []
    for device in devices:
        if not isinstance(device, dict):
            continue
        flattened.append(device)
        flattened.extend(_flatten_blockdevices(device.get("children", [])))
    return flattened


def _select_usb_storage(devices: list[dict[str, Any]]) -> dict[str, Any] | None:
    for disk in devices:
        if disk.get("type") != "disk" or disk.get("tran") != "usb":
            continue
        disk_path = _node_path(disk)
        children = disk.get("children") or []
        partition_info = _select_partition(children)
        if partition_info is None:
            disk_fstype = disk.get("fstype") or ""
            return {
                "disk": disk_path,
                "partition": disk_path if disk_fstype else "",
                "mount_point": disk.get("mountpoint") or "",
                "fstype": disk_fstype,
                "whole_disk_filesystem": bool(disk_fstype),
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


def _parse_tune2fs_health(output: str) -> dict[str, Any]:
    state = ""
    features: list[str] = []
    errors_behavior = ""
    for line in output.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip().lower()
        value = value.strip()
        if key == "filesystem state":
            state = value
        elif key == "filesystem features":
            features = value.split()
        elif key == "errors behavior":
            errors_behavior = value

    state_lower = state.lower()
    needs_recovery = "needs_recovery" in features
    safe_to_mount = state_lower == "clean"
    reasons = []
    warnings = []
    if state and state_lower != "clean":
        reasons.append(f"filesystem state is {state}")
    if needs_recovery:
        message = "filesystem journal recovery flag is set"
        if safe_to_mount:
            warnings.append(message)
        else:
            reasons.append(message)
    return {
        "checked": True,
        "tool": "tune2fs",
        "filesystem_state": state,
        "features": features,
        "errors_behavior": errors_behavior,
        "needs_recovery": needs_recovery,
        "safe_to_mount": safe_to_mount,
        "reasons": reasons,
        "warnings": warnings,
    }


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


def _recent_storage_dmesg_errors(device: str = "") -> list[str]:
    if not shutil.which("dmesg"):
        return []
    try:
        result = run_command(["dmesg"], 5)
    except Exception:
        return []
    if result.returncode != 0:
        return []

    names = _device_names(device)
    context_terms = ("uas", "usb-storage", "scsi", "blk_update_request", "buffer i/o", "ext4-fs", "journal")
    error_terms = ("error", "fail", "reset", "abort", "read-only", "offline", "timeout", "i/o")
    errors = []
    for line in result.stdout.splitlines():
        low = line.lower()
        has_context = any(term in low for term in context_terms) or any(name in low for name in names)
        has_error = any(term in low for term in error_terms)
        if has_context and has_error:
            errors.append(line.strip())
    return errors[-30:]


def _device_names(device: str) -> list[str]:
    name = Path(device).name if device else ""
    if not name:
        return []
    names = [name.lower()]
    disk_match = re.match(r"([a-z]+)", name.lower())
    if disk_match:
        names.append(disk_match.group(1))
    return list(dict.fromkeys(names))


def _parse_ip_addr_json(data: list[Any]) -> list[dict[str, Any]]:
    interfaces: list[dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        name = str(item.get("ifname") or "")
        if not name:
            continue
        interfaces.append(
            {
                "name": name,
                "operstate": str(item.get("operstate") or "").lower(),
                "mac_address": str(item.get("address") or ""),
                "mtu": item.get("mtu"),
                "flags": item.get("flags") if isinstance(item.get("flags"), list) else [],
                "carrier": _read_bool(Path("/sys/class/net") / name / "carrier"),
                "speed_mbps": _read_int(Path("/sys/class/net") / name / "speed"),
                "addresses": _ip_addresses(item.get("addr_info")),
            }
        )
    return interfaces


def _ip_addresses(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    addresses: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        local = item.get("local")
        if local:
            addresses.append(
                {
                    "family": item.get("family"),
                    "local": local,
                    "prefixlen": item.get("prefixlen"),
                }
            )
    return addresses


def _interfaces_from_sysfs() -> list[dict[str, Any]]:
    base = Path("/sys/class/net")
    interfaces = []
    for path in sorted(base.glob("*")):
        name = path.name
        interfaces.append(
            {
                "name": name,
                "operstate": _read_text(path / "operstate").lower(),
                "mac_address": _read_text(path / "address"),
                "mtu": _read_int(path / "mtu"),
                "flags": [],
                "carrier": _read_bool(path / "carrier"),
                "speed_mbps": _read_int(path / "speed"),
                "addresses": [],
            }
        )
    return interfaces


def _first_non_loopback(interfaces: list[dict[str, Any]]) -> str:
    for item in interfaces:
        name = str(item.get("name") or "")
        if name and name != "lo":
            return name
    return ""


def _parse_default_route(output: str) -> tuple[str, str]:
    for line in output.splitlines():
        parts = line.split()
        if not parts or parts[0] != "default":
            continue
        interface = ""
        gateway = ""
        if "dev" in parts:
            index = parts.index("dev")
            if index + 1 < len(parts):
                interface = parts[index + 1]
        if "via" in parts:
            index = parts.index("via")
            if index + 1 < len(parts):
                gateway = parts[index + 1]
        return interface, gateway
    return "", ""


def _parse_ping_metrics(output: str) -> dict[str, Any]:
    metrics: dict[str, Any] = {
        "packets_transmitted": 0,
        "packets_received": 0,
        "packet_loss_percent": 100.0,
    }
    packet_match = re.search(
        r"(\d+)\s+packets transmitted,\s+(\d+)\s+(?:packets )?received,.*?([\d.]+)%\s+packet loss",
        output,
    )
    if packet_match:
        metrics["packets_transmitted"] = int(packet_match.group(1))
        metrics["packets_received"] = int(packet_match.group(2))
        metrics["packet_loss_percent"] = float(packet_match.group(3))
    rtt_match = re.search(r"(?:rtt|round-trip).*?=\s*([\d.]+)/([\d.]+)/([\d.]+)/", output)
    if rtt_match:
        metrics["rtt_min_ms"] = float(rtt_match.group(1))
        metrics["rtt_avg_ms"] = float(rtt_match.group(2))
        metrics["rtt_max_ms"] = float(rtt_match.group(3))
    return metrics


def _filter_nvme_block_devices(devices: list[dict[str, Any]]) -> list[dict[str, Any]]:
    filtered = []
    for item in devices:
        name = str(item.get("name") or "")
        tran = str(item.get("tran") or "")
        if item.get("type") == "disk" and (tran == "nvme" or name.startswith("nvme")):
            filtered.append(item)
    return filtered


def _sysfs_children(path: str) -> list[str]:
    base = Path(path)
    if not base.exists():
        return []
    return sorted(item.name for item in base.iterdir())


def _rtc_devices() -> list[dict[str, Any]]:
    devices = []
    for path in sorted(Path("/dev").glob("rtc*")):
        name = path.name
        sysfs = Path("/sys/class/rtc") / name
        devices.append(
            {
                "path": str(path),
                "name": name,
                "sysfs": str(sysfs) if sysfs.exists() else "",
                "rtc_name": _read_text(sysfs / "name"),
                "hctosys": _read_text(sysfs / "hctosys"),
            }
        )
    return devices


def _fan_hwmon_entries() -> list[dict[str, Any]]:
    fans = []
    for hwmon in sorted(Path("/sys/class/hwmon").glob("hwmon*")):
        name = _read_text(hwmon / "name")
        rpm_values = _read_numbered_values(hwmon, "fan*_input")
        rpm_direct = _read_int(hwmon / "rpm")
        if rpm_direct is not None:
            rpm_values.append(rpm_direct)
        pwm_values = _read_numbered_values(hwmon, "pwm[0-9]*")
        if not rpm_values and not pwm_values and "fan" not in name.lower():
            continue
        fans.append(
            {
                "hwmon": str(hwmon),
                "name": name,
                "rpm_values": rpm_values,
                "pwm_values": pwm_values,
            }
        )
    return fans


def _read_numbered_values(base: Path, pattern: str) -> list[int]:
    values = []
    for path in sorted(base.glob(pattern)):
        if path.name.endswith("_enable"):
            continue
        value = _read_int(path)
        if value is not None:
            values.append(value)
    return values


def _gpio_chips_from_dev() -> list[dict[str, Any]]:
    chips = []
    for path in sorted(Path("/dev").glob("gpiochip*")):
        chips.append({"name": path.name, "path": str(path), "label": "", "line_count": None})
    return chips


def _merge_gpio_chip_info(chips: list[dict[str, Any]], output: str) -> list[dict[str, Any]]:
    by_name = {str(item.get("name")): dict(item) for item in chips}
    pattern = re.compile(r"^(gpiochip\d+)\s+\[([^\]]*)\]\s+\((\d+)\s+lines?\)")
    for line in output.splitlines():
        match = pattern.search(line.strip())
        if not match:
            continue
        name = match.group(1)
        item = by_name.get(name, {"name": name, "path": f"/dev/{name}"})
        item["label"] = match.group(2)
        item["line_count"] = int(match.group(3))
        by_name[name] = item
    return [by_name[name] for name in sorted(by_name)]


def _parse_i2cdetect_list(output: str) -> list[dict[str, Any]]:
    buses = []
    for line in output.splitlines():
        line = line.strip()
        match = re.match(r"i2c-(\d+)\s+(\S+)\s+(.+?)\s{2,}(.+)$", line)
        if match:
            buses.append(
                {
                    "bus": int(match.group(1)),
                    "type": match.group(2),
                    "name": match.group(3).strip(),
                    "adapter": match.group(4).strip(),
                    "path": f"/dev/i2c-{match.group(1)}",
                }
            )
            continue
        tab_parts = line.split("\t")
        if len(tab_parts) >= 3:
            bus_match = re.match(r"i2c-(\d+)", tab_parts[0])
            if bus_match:
                buses.append(
                    {
                        "bus": int(bus_match.group(1)),
                        "type": tab_parts[1].strip(),
                        "name": tab_parts[2].strip(),
                        "adapter": tab_parts[3].strip() if len(tab_parts) > 3 else "",
                        "path": f"/dev/i2c-{bus_match.group(1)}",
                    }
                )
    return sorted(buses, key=lambda item: int(item["bus"]))


def _i2c_buses_from_dev() -> list[dict[str, Any]]:
    buses = []
    for path in sorted(Path("/dev").glob("i2c-*")):
        bus = _normalize_i2c_bus(path.name)
        if bus is not None:
            buses.append({"bus": bus, "type": "", "name": "", "adapter": "", "path": str(path)})
    return buses


def _normalize_i2c_bus(value: str) -> int | None:
    if value in ("", "auto"):
        return None
    match = re.search(r"(\d+)$", str(value))
    if not match:
        return None
    return int(match.group(1))


def _parse_i2cdetect_table(output: str) -> list[int]:
    addresses = []
    for line in output.splitlines():
        line = line.strip()
        row_match = re.match(r"^([0-7][0-9a-fA-F]):\s+(.*)$", line)
        if not row_match:
            continue
        row_base = int(row_match.group(1), 16)
        cells = row_match.group(2).split()
        for offset, cell in enumerate(cells):
            if cell == "--":
                continue
            if cell == "UU" or re.fullmatch(r"[0-7][0-9a-fA-F]", cell):
                addresses.append(row_base + offset)
    return sorted(dict.fromkeys(addresses))


def _normalize_i2c_addresses(values: list[Any]) -> list[int]:
    addresses = []
    for value in values:
        if isinstance(value, int):
            addresses.append(value)
            continue
        text = str(value).strip()
        if not text:
            continue
        base = 16 if text.lower().startswith("0x") else 10
        try:
            addresses.append(int(text, base))
        except ValueError:
            continue
    return sorted(dict.fromkeys(addresses))


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def _read_int(path: Path) -> int | None:
    text = _read_text(path)
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def _read_bool(path: Path) -> bool | None:
    value = _read_int(path)
    if value is None:
        return None
    return value != 0


def _tail_text(text: str, limit: int = 4000) -> str:
    stripped = text.strip()
    if len(stripped) <= limit:
        return stripped
    return stripped[-limit:]


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
