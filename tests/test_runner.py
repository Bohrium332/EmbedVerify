import unittest
from pathlib import Path

from embedverify.core.runner import SuiteRunner, _invoke_function


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


if __name__ == "__main__":
    unittest.main()
