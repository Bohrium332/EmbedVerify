import unittest

from embedverify.capabilities.linux_generic import _parse_lsusb, _select_usb_storage


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


if __name__ == "__main__":
    unittest.main()
