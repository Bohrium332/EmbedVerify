import unittest
from pathlib import Path

from embedverify.core.runner import SuiteRunner


ROOT = Path(__file__).resolve().parents[1]


class RunnerTests(unittest.TestCase):
    def test_runner_dry_run_loads_suite_and_board(self):
        report = SuiteRunner(ROOT).run(
            "suites/usb_smoke.yaml",
            board_name="recomputer_j401",
            dry_run=True,
        )

        self.assertEqual(report["status"], "dry_run")
        self.assertEqual(report["suite"], "usb_smoke")
        self.assertEqual(report["board"], "recomputer_j401")


if __name__ == "__main__":
    unittest.main()

