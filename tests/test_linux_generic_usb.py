import json
import unittest
from unittest.mock import patch

from embedverify.capabilities.base import CommandResult
from embedverify.capabilities.linux_generic import (
    GenericStorageCapability,
    _parse_lsusb,
    _parse_tune2fs_health,
    _select_usb_storage,
)


class LinuxGenericUSBTests(unittest.TestCase):
    def test_parse_lsusb_uses_device_level_speed(self):
        listing = "\n".join(
            [
                "Bus 002 Device 003: ID 0951:1666 Kingston Technology DataTraveler",
                "Bus 002 Device 002: ID 2109:0822 VIA Labs, Inc. USB3.1 Hub",
                "Bus 002 Device 001: ID 1d6b:0003 Linux Foundation 3.0 root hub",
            ]
        )
        tree = "\n".join(
            [
                "/:  Bus 02.Port 1: Dev 1, Class=root_hub, Driver=tegra-xusb/4p, 10000M",
                "    |__ Port 1: Dev 2, If 0, Class=Hub, Driver=hub/4p, 10000M",
                "        |__ Port 1: Dev 3, If 0, Class=Mass Storage, Driver=usb-storage, 5000M",
            ]
        )

        devices = _parse_lsusb(listing, tree, "any", None, None)

        self.assertEqual(devices[0]["speed"], "5G")
        self.assertEqual(devices[1]["speed"], "10G")

    def test_select_usb_storage_prefers_mounted_partition(self):
        devices = [
            {
                "name": "nvme0n1",
                "path": "/dev/nvme0n1",
                "type": "disk",
                "tran": "nvme",
            },
            {
                "name": "sda",
                "path": "/dev/sda",
                "type": "disk",
                "tran": "usb",
                "model": "DataTraveler 3.0",
                "children": [
                    {
                        "name": "sda1",
                        "path": "/dev/sda1",
                        "type": "part",
                        "fstype": "vfat",
                        "mountpoint": "",
                    },
                    {
                        "name": "sda2",
                        "path": "/dev/sda2",
                        "type": "part",
                        "fstype": "ext4",
                        "mountpoint": "/media/usb",
                    },
                ],
            },
        ]

        selected = _select_usb_storage(devices)

        self.assertEqual(selected["disk"], "/dev/sda")
        self.assertEqual(selected["partition"], "/dev/sda2")
        self.assertEqual(selected["mount_point"], "/media/usb")

    def test_select_usb_storage_returns_unmounted_partition(self):
        devices = [
            {
                "name": "sda",
                "path": "/dev/sda",
                "type": "disk",
                "tran": "usb",
                "children": [
                    {
                        "name": "sda1",
                        "path": "/dev/sda1",
                        "type": "part",
                        "fstype": "vfat",
                        "mountpoint": None,
                    }
                ],
            }
        ]

        selected = _select_usb_storage(devices)

        self.assertEqual(selected["disk"], "/dev/sda")
        self.assertEqual(selected["partition"], "/dev/sda1")
        self.assertEqual(selected["mount_point"], "")

    def test_select_usb_storage_supports_whole_disk_filesystem(self):
        devices = [
            {
                "name": "sda",
                "path": "/dev/sda",
                "type": "disk",
                "tran": "usb",
                "fstype": "ext4",
                "mountpoint": "",
                "children": [],
            }
        ]

        selected = _select_usb_storage(devices)

        self.assertEqual(selected["disk"], "/dev/sda")
        self.assertEqual(selected["partition"], "/dev/sda")
        self.assertEqual(selected["fstype"], "ext4")
        self.assertTrue(selected["whole_disk_filesystem"])

    def test_parse_tune2fs_health_blocks_dirty_ext(self):
        output = "\n".join(
            [
                "Filesystem features:      has_journal needs_recovery extent 64bit",
                "Filesystem state:         clean with errors",
                "Errors behavior:          Continue",
            ]
        )

        health = _parse_tune2fs_health(output)

        self.assertTrue(health["checked"])
        self.assertFalse(health["safe_to_mount"])
        self.assertTrue(health["needs_recovery"])
        self.assertIn("filesystem journal recovery flag is set", health["reasons"])

    def test_parse_tune2fs_health_allows_clean_state_with_recovery_flag(self):
        output = "\n".join(
            [
                "Filesystem features:      has_journal needs_recovery extent 64bit",
                "Filesystem state:         clean",
                "Errors behavior:          Continue",
            ]
        )

        health = _parse_tune2fs_health(output)

        self.assertTrue(health["safe_to_mount"])
        self.assertTrue(health["needs_recovery"])
        self.assertIn("filesystem journal recovery flag is set", health["warnings"])

    def test_write_speed_blocks_dirty_ext_before_mount(self):
        runner = RecordingRunner(
            {
                "lsblk": CommandResult(
                    0,
                    json.dumps(
                        {
                            "blockdevices": [
                                {
                                    "name": "sda",
                                    "path": "/dev/sda",
                                    "type": "disk",
                                    "tran": "usb",
                                    "children": [
                                        {
                                            "name": "sda1",
                                            "path": "/dev/sda1",
                                            "type": "part",
                                            "fstype": "ext4",
                                            "mountpoint": "",
                                        }
                                    ],
                                }
                            ]
                        }
                    ),
                    "",
                ),
                "tune2fs": CommandResult(
                    0,
                    "\n".join(
                        [
                            "Filesystem features:      has_journal needs_recovery extent",
                            "Filesystem state:         clean with errors",
                        ]
                    ),
                    "",
                ),
            }
        )
        cap = GenericStorageCapability(runner)

        with patch("embedverify.capabilities.linux_generic.shutil.which", return_value="/usr/bin/tool"):
            result = cap.write_speed(mount_point="auto")

        self.assertEqual(result["code"], -1)
        self.assertIn("not clean", result["message"])
        self.assertFalse(any(call[0] == "mount" for call in runner.calls))


class RecordingRunner:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def __call__(self, args, timeout):
        self.calls.append(args)
        response = self.responses.get(args[0])
        if response is None:
            raise AssertionError(f"unexpected command: {args}")
        return response


if __name__ == "__main__":
    unittest.main()
