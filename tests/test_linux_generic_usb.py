import unittest

from embedverify.capabilities.linux_generic import _parse_lsusb


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


if __name__ == "__main__":
    unittest.main()

