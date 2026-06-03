import unittest

from embedverify.core.report import _to_text


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


if __name__ == "__main__":
    unittest.main()
