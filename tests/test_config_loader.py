import unittest
from pathlib import Path

from embedverify.core.config_loader import ConfigLoader


ROOT = Path(__file__).resolve().parents[1]


class ConfigLoaderTests(unittest.TestCase):
    def test_load_project_config(self):
        config = ConfigLoader(ROOT).load_project_config()

        self.assertEqual(config.board, "recomputer_j401")
        self.assertEqual(config.report_dir, "reports")

    def test_load_recomputer_j401_board(self):
        board = ConfigLoader(ROOT).load_board("recomputer_j401")

        self.assertEqual(board.name, "recomputer_j401")
        self.assertEqual(board.capabilities["usb"], "linux_generic")
        self.assertEqual(board.capabilities["storage"], "linux_generic")

    def test_load_usb_suite_and_case(self):
        loader = ConfigLoader(ROOT)
        suite = loader.load_suite("suites/usb_smoke.yaml")
        case = loader.load_case(suite.cases[0])

        self.assertEqual(suite.name, "usb_smoke")
        self.assertEqual(case.name, "usb_host_storage")
        self.assertEqual(
            [fn.name for fn in case.functions],
            [
                "usb.detect",
                "storage.info",
                "storage.read_speed",
                "storage.write_speed",
            ],
        )


if __name__ == "__main__":
    unittest.main()
