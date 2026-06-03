import json
import tempfile
import unittest
from pathlib import Path

from embedverify.core.report import ReportWriter, _to_text


class ReportWriterTests(unittest.TestCase):
    def test_text_report_does_not_require_function_status(self):
        report = {
            "request_id": "req-1",
            "suite": "usb_smoke",
            "board": "recomputer_j401",
            "status": "passed",
            "results": [
                {
                    "case_name": "usb_host_storage",
                    "function_name": "storage.write_speed",
                    "result": {
                        "code": 0,
                        "message": "write speed: 572.0 MB/s",
                        "details": {},
                        "metrics": {"write_speed_mbps": 572.0},
                    },
                    "expectation": {"passed": True, "failures": []},
                }
            ],
        }

        text = _to_text(report)

        self.assertIn("storage.write_speed: code=0 write speed: 572.0 MB/s", text)
        self.assertNotIn("None (0)", text)

    def test_writer_uses_report_directory_and_saved_outputs(self):
        report = {
            "request_id": "req-1",
            "suite": "usb_smoke",
            "board": "recomputer_j401",
            "status": "passed",
            "started_at": "2026-06-03T09:13:03+00:00",
            "results": [
                {
                    "case_name": "usb_host_storage",
                    "function_name": "storage.info",
                    "label": "storage_info",
                    "result": {"code": 0, "message": "ok", "details": {}, "metrics": {}},
                    "expectation": {"passed": True, "failures": []},
                    "save_output": True,
                    "skipped": False,
                }
            ],
        }

        with tempfile.TemporaryDirectory() as tmp:
            files = ReportWriter(tmp).write(report)

            self.assertTrue(Path(files["dir"]).is_dir())
            self.assertEqual(Path(files["json"]).name, "report.json")
            self.assertEqual(Path(files["text"]).name, "report.txt")
            self.assertIn("storage_info", files["outputs"])
            output_path = Path(files["outputs"]["storage_info"])
            self.assertTrue(output_path.exists())
            payload = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["function_name"], "storage.info")
            self.assertEqual(report["results"][0]["output_file"], str(output_path))


if __name__ == "__main__":
    unittest.main()
