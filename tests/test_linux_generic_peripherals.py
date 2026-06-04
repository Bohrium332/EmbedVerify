import json
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from embedverify.capabilities.base import CommandResult
from embedverify.capabilities.linux_generic import (
    GenericCameraCapability,
    GenericDisplayCapability,
    GenericI2CCapability,
    GenericNetworkCapability,
    GenericPCIeNVMeCapability,
    GenericUARTCapability,
    GenericWiFiCapability,
    _parse_bluetooth_controller,
    _parse_bluetooth_devices,
    _parse_i2cdetect_list,
    _parse_i2cdetect_table,
    _parse_iw_dev,
    _parse_iw_scan,
    _parse_xrandr_connectors,
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

    def test_wifi_scan_parses_iw_output(self):
        runner = MappingRunner(
            {
                ("iw", "dev"): CommandResult(
                    0,
                    "\n".join(["phy#0", "\tInterface wlan0", "\t\taddr 54:ef:33:9d:04:7e", "\t\ttype managed"]),
                    "",
                ),
                ("ip", "link", "set", "wlan0", "up"): CommandResult(0, "", ""),
                ("iw", "dev", "wlan0", "scan"): CommandResult(
                    0,
                    "\n".join(
                        [
                            "BSS 5c:02:14:a7:3c:0c(on wlan0)",
                            "\tfreq: 5180",
                            "\tsignal: -44.00 dBm",
                            "\tSSID: WiFi_5G",
                        ]
                    ),
                    "",
                ),
            }
        )
        cap = GenericWiFiCapability(runner)

        with patch("embedverify.capabilities.linux_generic.shutil.which", return_value="/usr/bin/tool"):
            result = cap.scan(interface="auto")

        self.assertEqual(result["code"], 0)
        self.assertEqual(result["metrics"]["network_count"], 1)
        self.assertEqual(result["details"]["networks"][0]["ssid"], "WiFi_5G")

    def test_wireless_parser_helpers(self):
        interfaces = _parse_iw_dev("phy#0\n\tInterface wlan0\n\t\taddr aa:bb\n\t\ttype managed\n")
        networks = _parse_iw_scan("BSS aa:bb(on wlan0)\n\tfreq: 2412\n\tsignal: -50.00 dBm\n\tSSID: test\n")
        controller = _parse_bluetooth_controller("Controller 54:EF:33:9D:04:7F (public)\n\tPowered: yes\n")
        devices = _parse_bluetooth_devices("[\u001b[0;92mNEW\u001b[0m] Device 01:02:03:04:05:06 Demo\n")

        self.assertEqual(interfaces[0]["name"], "wlan0")
        self.assertEqual(networks[0]["ssid"], "test")
        self.assertEqual(controller["address"], "54:EF:33:9D:04:7F")
        self.assertEqual(devices[0]["name"], "Demo")

    def test_camera_argus_capture_accepts_done_success_with_correctable_error(self):
        runner = MappingRunner(
            {
                (
                    "gst-launch-1.0",
                    "-q",
                    "nvarguscamerasrc",
                    "sensor-id=0",
                    "num-buffers=1",
                    "!",
                    "video/x-raw(memory:NVMM),width=1280,height=720,framerate=30/1",
                    "!",
                    "fakesink",
                ): CommandResult(
                    1,
                    "",
                    "CONSUMER: Producer has connected; continuing.\n"
                    "CONSUMER: Done Success\n"
                    "GST_ARGUS: Done Success\n"
                    "ERROR: CANCELLED\n"
                    "Argus Correctable Error Status\n",
                )
            }
        )
        cap = GenericCameraCapability(runner)

        result = cap._argus_capture(sensor_id=0, timeout=12)

        self.assertTrue(result["capture_ok"])
        self.assertEqual(result["exit_code"], 1)

    def test_xrandr_parser_extracts_connected_connector(self):
        connectors = _parse_xrandr_connectors(
            "\n".join(
                [
                    "Screen 0: minimum 8 x 8, current 1024 x 600, maximum 32767 x 32767",
                    "DP-0 disconnected (normal left inverted right x axis y axis)",
                    "DP-1 connected primary 1024x600+0+0 (normal left inverted right x axis y axis)",
                ]
            ),
            source="display_0_gdm",
        )

        connected = [item for item in connectors if item["status"] == "connected"]
        self.assertEqual(connected[0]["name"], "DP-1")
        self.assertEqual(connected[0]["current_mode"], "1024x600+0+0")

    def test_display_detect_uses_xrandr_fallback_connection(self):
        runner = MappingRunner(
            {
                ("xrandr", "--query"): CommandResult(1, "", "Can't open display"),
                ("env", "DISPLAY=:0", "XAUTHORITY=/run/user/128/gdm/Xauthority", "xrandr", "--query"): CommandResult(
                    0,
                    "DP-1 connected primary 1024x600+0+0 (normal left inverted right x axis y axis)\n",
                    "",
                ),
            }
        )
        cap = GenericDisplayCapability(runner)

        with (
            patch("embedverify.capabilities.linux_generic.shutil.which", return_value="/usr/bin/tool"),
            patch("embedverify.capabilities.linux_generic._display_connectors", return_value=[]),
            patch("embedverify.capabilities.linux_generic._display_driver_paths", return_value=[]),
            patch("embedverify.capabilities.linux_generic._glob_paths", return_value=[]),
            patch(
                "embedverify.capabilities.linux_generic._xrandr_candidates",
                return_value=[
                    {"label": "current_env", "cmd": ["xrandr", "--query"]},
                    {
                        "label": "display_0_gdm",
                        "cmd": ["env", "DISPLAY=:0", "XAUTHORITY=/run/user/128/gdm/Xauthority", "xrandr", "--query"],
                    },
                ],
            ),
        ):
            result = cap.detect(require_connected=True)

        self.assertEqual(result["code"], 0)
        self.assertEqual(result["metrics"]["connected_count"], 1)

    def test_uart_loopback_uses_pyserial_payload_length(self):
        opens = []
        writes = []
        reads = []

        class FakeSerialHandle:
            def __init__(self, port, *, baudrate, timeout):
                self.port = port
                self.baudrate = baudrate
                self.timeout = timeout
                opens.append((port, baudrate, timeout))

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def reset_input_buffer(self):
                pass

            def reset_output_buffer(self):
                pass

            def write(self, data):
                writes.append(data)

            def flush(self):
                pass

            def read(self, size):
                reads.append(size)
                return writes[-1]

        fake_serial = types.SimpleNamespace(Serial=FakeSerialHandle)

        with patch.dict("sys.modules", {"serial": fake_serial}):
            result = GenericUARTCapability().loopback(
                port="/dev/ttyTHS1",
                payload="EV_UART_LOOPBACK",
                baudrate=115200,
                timeout=2,
            )

        self.assertEqual(result["code"], 0)
        self.assertEqual(opens, [("/dev/ttyTHS1", 115200, 0.1), ("/dev/ttyTHS1", 115200, 2)])
        self.assertEqual(writes, [b"EV_UART_LOOPBACK"])
        self.assertEqual(reads, [1024])
        self.assertEqual(result["details"]["attempts"][0]["received"], "EV_UART_LOOPBACK")
        self.assertNotIn("status", result)

    def test_peripheral_suite_dry_run_loads(self):
        report = SuiteRunner(ROOT).run("suites/peripheral_smoke.yaml", dry_run=True)

        self.assertEqual(report["status"], "dry_run")
        self.assertEqual(report["suite"], "peripheral_smoke")

    def test_connected_peripherals_suite_dry_run_loads(self):
        report = SuiteRunner(ROOT).run("suites/connected_peripherals_smoke.yaml", dry_run=True)

        self.assertEqual(report["status"], "dry_run")
        self.assertEqual(report["suite"], "connected_peripherals_smoke")

    def test_invoke_new_function_entrypoint_has_no_status(self):
        class Network:
            def list_interfaces(self, **kwargs):
                return {"code": 0, "message": "ok", "details": kwargs, "metrics": {"interface_count": 1}}

        result = _invoke_function("network.list_interfaces", {"include_loopback": False}, {"network": Network()})

        self.assertEqual(result["code"], 0)
        self.assertNotIn("status", result)

    def test_invoke_camera_function_entrypoint_has_no_status(self):
        class Camera:
            def detect(self, **kwargs):
                return {"code": 0, "message": "ok", "details": kwargs, "metrics": {"capture_ok": True}}

        result = _invoke_function("camera.detect", {"sensor_id": 0}, {"camera": Camera()})

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
