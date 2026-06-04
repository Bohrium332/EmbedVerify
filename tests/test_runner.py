import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from embedverify.core.runner import SuiteRunner, _invoke_function, _render_templates


ROOT = Path(__file__).resolve().parents[1]


class RunnerTests(unittest.TestCase):
    def test_runner_dry_run_loads_suite_and_board_from_config(self):
        report = SuiteRunner(ROOT).run(
            "suites/usb_smoke.yaml",
            dry_run=True,
        )

        self.assertEqual(report["status"], "dry_run")
        self.assertEqual(report["suite"], "usb_smoke")
        self.assertEqual(report["board"], "recomputer_j401")

    def test_runner_accepts_cli_board(self):
        report = SuiteRunner(ROOT).run(
            "suites/usb_smoke.yaml",
            board_name="recomputer_j401",
            dry_run=True,
        )

        self.assertEqual(report["status"], "dry_run")
        self.assertEqual(report["board"], "recomputer_j401")

    def test_invoke_function_uses_operation_entrypoint(self):
        class USB:
            def detect(self, **kwargs):
                return {"code": 0, "message": "ok", "details": kwargs, "metrics": {}}

        result = _invoke_function(
            "usb.detect",
            {"bus_type": "any"},
            {"usb": USB()},
        )

        self.assertEqual(result["code"], 0)
        self.assertNotIn("status", result)

    def test_invoke_storage_operation_entrypoint(self):
        class Storage:
            def read_speed(self, **kwargs):
                return {
                    "code": 0,
                    "message": "ok",
                    "details": kwargs,
                    "metrics": {"read_speed_mbps": 1.0},
                }

        result = _invoke_function(
            "storage.read_speed",
            {"device": "auto"},
            {"storage": Storage()},
        )

        self.assertEqual(result["metrics"]["read_speed_mbps"], 1.0)
        self.assertNotIn("status", result)

    def test_invoke_storage_detect_entrypoint(self):
        class Storage:
            def detect(self, **kwargs):
                return {"code": 0, "message": "ok", "details": kwargs, "metrics": {"device_count": 1}}

        result = _invoke_function(
            "storage.detect",
            {"expected_type": "disk"},
            {"storage": Storage()},
        )

        self.assertEqual(result["metrics"]["device_count"], 1)
        self.assertNotIn("status", result)

    def test_invoke_storage_integrity_entrypoint(self):
        class Storage:
            def integrity_check(self, **kwargs):
                return {"code": 0, "message": "ok", "details": kwargs, "metrics": {"integrity_match": True}}

        result = _invoke_function(
            "storage.integrity_check",
            {"file_size_mb": 1},
            {"storage": Storage()},
        )

        self.assertTrue(result["metrics"]["integrity_match"])
        self.assertNotIn("status", result)

    def test_render_templates_uses_labeled_context(self):
        rendered = _render_templates(
            {
                "device": "{{ storage_info.result.details.discovery.disk }}",
                "summary": "disk={{ storage_info.result.details.discovery.disk }}",
            },
            {
                "storage_info": {
                    "result": {
                        "details": {
                            "discovery": {
                                "disk": "/dev/sda",
                            }
                        }
                    }
                }
            },
        )

        self.assertEqual(rendered["device"], "/dev/sda")
        self.assertEqual(rendered["summary"], "disk=/dev/sda")

    def test_skip_on_fail_skips_following_functions(self):
        def fake_invoke(name, params, capabilities):
            self.assertEqual(name, "usb.detect")
            return {"code": -1, "message": "no usb", "details": {}, "metrics": {"device_count": 0}}

        with tempfile.TemporaryDirectory() as tmp:
            with patch("embedverify.core.runner._invoke_function", side_effect=fake_invoke) as invoke:
                report = SuiteRunner(ROOT).run(
                    "suites/usb_smoke.yaml",
                    reports_dir=tmp,
                )

        self.assertEqual(report["status"], "failed")
        self.assertEqual(invoke.call_count, 1)
        self.assertEqual(len(report["results"]), 6)
        self.assertFalse(report["results"][0]["skipped"])
        self.assertTrue(report["results"][1]["skipped"])
        self.assertEqual(report["results"][1]["result"]["code"], 2)
        self.assertEqual(report["results"][1]["expectation"]["policy"], "skipped")

    def test_runner_resolves_templates_and_saves_outputs(self):
        calls = []

        def fake_invoke(name, params, capabilities):
            calls.append((name, params))
            if name == "usb.detect":
                return {"code": 0, "message": "usb ok", "details": {}, "metrics": {"device_count": 1}}
            if name == "storage.detect":
                return {"code": 0, "message": "detect ok", "details": {}, "metrics": {"device_count": 1}}
            if name == "storage.info":
                return {
                    "code": 0,
                    "message": "storage ok",
                    "details": {"discovery": {"disk": "/dev/from-info"}},
                    "metrics": {"device_count": 1},
                }
            if name == "storage.read_speed":
                return {
                    "code": 0,
                    "message": "read ok",
                    "details": {"params": params},
                    "metrics": {"read_speed_mbps": 1.0},
                }
            if name == "storage.write_speed":
                return {
                    "code": 0,
                    "message": "write ok",
                    "details": {"params": params},
                    "metrics": {"write_speed_mbps": 1.0},
                }
            if name == "storage.integrity_check":
                return {
                    "code": 0,
                    "message": "integrity ok",
                    "details": {"params": params},
                    "metrics": {"integrity_match": True},
                }
            raise AssertionError(name)

        with tempfile.TemporaryDirectory() as tmp:
            with patch("embedverify.core.runner._invoke_function", side_effect=fake_invoke):
                report = SuiteRunner(ROOT).run(
                    "suites/usb_smoke.yaml",
                    reports_dir=tmp,
                )

            self.assertEqual(report["status"], "passed")
            self.assertEqual(calls[3][0], "storage.read_speed")
            self.assertEqual(calls[3][1]["device"], "/dev/from-info")
            self.assertEqual(report["results"][2]["label"], "storage_info")
            self.assertIn("dir", report["report_files"])
            self.assertIn("storage_info", report["report_files"]["outputs"])
            self.assertTrue(Path(report["report_files"]["outputs"]["storage_info"]).exists())

    def test_runner_can_run_single_case(self):
        def fake_invoke(name, params, capabilities):
            if name == "usb.detect":
                return {"code": 0, "message": "ok", "details": {}, "metrics": {"device_count": 1}}
            if name == "storage.detect":
                return {"code": 0, "message": "ok", "details": {}, "metrics": {"device_count": 1}}
            if name == "storage.info":
                return {
                    "code": 0,
                    "message": "ok",
                    "details": {"discovery": {"disk": "/dev/from-info"}},
                    "metrics": {"device_count": 1},
                }
            if name == "storage.read_speed":
                return {"code": 0, "message": "ok", "details": {}, "metrics": {"read_speed_mbps": 1.0}}
            if name == "storage.write_speed":
                return {"code": 0, "message": "ok", "details": {}, "metrics": {"write_speed_mbps": 1.0}}
            if name == "storage.integrity_check":
                return {"code": 0, "message": "ok", "details": {}, "metrics": {"integrity_match": True}}
            raise AssertionError(name)

        with tempfile.TemporaryDirectory() as tmp:
            with patch("embedverify.core.runner._invoke_function", side_effect=fake_invoke):
                report = SuiteRunner(ROOT).run_case("cases/usb_host_storage.yaml", reports_dir=tmp)

        self.assertEqual(report["target_type"], "case")
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["suite"], "usb_host_storage")

    def test_runner_can_run_single_function(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch("embedverify.core.runner._invoke_function") as invoke:
                invoke.return_value = {"code": 0, "message": "ok", "details": {}, "metrics": {}}
                report = SuiteRunner(ROOT).run_function(
                    "storage.detect",
                    {"expected_type": "disk"},
                    reports_dir=tmp,
                )

        self.assertEqual(report["target_type"], "function")
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["results"][0]["function_name"], "storage.detect")


if __name__ == "__main__":
    unittest.main()
