import json
import unittest
from pathlib import Path
from unittest.mock import patch

from embedverify.capabilities.base import CommandResult
from embedverify.capabilities.linux_generic import (
    GenericI2CCapability,
    GenericNetworkCapability,
    GenericPCIeNVMeCapability,
    _parse_i2cdetect_list,
    _parse_i2cdetect_table,
)
from embedverify.core.runner import SuiteRunner, _invoke_function


ROOT = Path(__file__).resolve().parents[1]


class LinuxGenericPeripheralTests(unittest.TestCase):
    def test_network_capability_lists_interfaces_from_ip_json(self):
        runner = MappingRunner(
            {
                ("ip", "-j", "addr"): CommandResult(
                    0,
                    json.dumps(
                        [
                            {"ifname": "lo", "operstate": "UNKNOWN", "address": "00:00:00:00:00:00"},
                            {
                                "ifname": "eth0",
                                "operstate": "up",
                                "address": "aa:bb:cc:dd:ee:ff",
                                "addr_info": [{"family": "inet", "local": "192.168.4.149", "prefixlen": 24}],
                            },
                        ]
                    ),
                    "",
                )
            }
        )
        cap = GenericNetworkCapability(runner)

        with patch("embedverify.capabilities.linux_generic.shutil.which", return_value="/usr/bin/tool"):
            result = cap.list_interfaces()

        self.assertEqual(result["code"], 0)
        self.assertEqual(result["metrics"]["interface_count"], 1)
        self.assertEqual(result["details"]["interfaces"][0]["name"], "eth0")

    def test_pcie_nvme_detect_filters_nvme_disks(self):
        runner = MappingRunner(
            {
                ("lsblk", "--bytes", "--json", "-o", "NAME,PATH,SIZE,TYPE,MODEL,SERIAL,VENDOR,TRAN"): CommandResult(
                    0,
                    json.dumps(
                        {
                            "blockdevices": [
                                {"name": "sda", "path": "/dev/sda", "type": "disk", "tran": "usb"},
                                {"name": "nvme0n1", "path": "/dev/nvme0n1", "type": "disk", "tran": "nvme"},
                            ]
                        }
                    ),
                    "",
                )
            }
        )
        cap = GenericPCIeNVMeCapability(runner)

        with patch("embedverify.capabilities.linux_generic.shutil.which", return_value="/usr/bin/tool"):
            result = cap.detect()

        self.assertEqual(result["code"], 0)
        self.assertEqual(result["metrics"]["device_count"], 1)
        self.assertEqual(result["details"]["devices"][0]["path"], "/dev/nvme0n1")

    def test_i2c_scan_parses_detect_table(self):
        runner = MappingRunner(
            {
                ("i2cdetect", "-l"): CommandResult(
                    0,
                    "i2c-7\ti2c\tc240000.i2c\tI2C adapter\n",
                    "",
                ),
                ("i2cdetect", "-y", "-r", "7"): CommandResult(
                    0,
                    "\n".join(
                        [
                            "     0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f",
                            "10: -- -- -- -- -- -- -- -- -- -- 1a -- -- -- -- --",
                            "50: UU -- -- -- -- -- -- -- -- -- -- -- -- -- -- --",
                        ]
                    ),
                    "",
                ),
            }
        )
        cap = GenericI2CCapability(runner)

        with patch("embedverify.capabilities.linux_generic.shutil.which", return_value="/usr/bin/tool"):
            result = cap.scan(bus="7", expected_addresses=["0x1a"], min_device_count=2)

        self.assertEqual(result["code"], 0)
        self.assertEqual(result["metrics"]["device_count"], 2)
        self.assertIn("0x1a", result["details"]["addresses"])
        self.assertIn("0x50", result["details"]["addresses"])

    def test_i2c_parser_helpers(self):
        buses = _parse_i2cdetect_list("i2c-7\ti2c\tc240000.i2c\tI2C adapter\n")
        addresses = _parse_i2cdetect_table("20: -- -- -- UU -- -- -- -- -- -- -- -- -- -- -- --\n")

        self.assertEqual(buses[0]["bus"], 7)
        self.assertEqual(addresses, [0x23])

    def test_peripheral_suite_dry_run_loads(self):
        report = SuiteRunner(ROOT).run("suites/peripheral_smoke.yaml", dry_run=True)

        self.assertEqual(report["status"], "dry_run")
        self.assertEqual(report["suite"], "peripheral_smoke")

    def test_invoke_new_function_entrypoint_has_no_status(self):
        class Network:
            def list_interfaces(self, **kwargs):
                return {"code": 0, "message": "ok", "details": kwargs, "metrics": {"interface_count": 1}}

        result = _invoke_function("network.list_interfaces", {"include_loopback": False}, {"network": Network()})

        self.assertEqual(result["code"], 0)
        self.assertNotIn("status", result)


class MappingRunner:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def __call__(self, args, timeout):
        self.calls.append(args)
        key = tuple(args)
        response = self.responses.get(key)
        if response is None:
            raise AssertionError(f"unexpected command: {args}")
        return response


if __name__ == "__main__":
    unittest.main()
