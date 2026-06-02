import unittest

from embedverify.core.expectations import evaluate_expectation


class ExpectationTests(unittest.TestCase):
    def test_expectation_all_passes(self):
        result = {"status": "passed", "metrics": {"read_speed_mbps": 120.5}}
        expect = {
            "pass_policy": "all",
            "rules": [
                {"field": "status", "operator": "eq", "value": "passed"},
                {"field": "metrics.read_speed_mbps", "operator": "gt", "value": 0},
            ],
        }

        self.assertTrue(evaluate_expectation(result, expect)["passed"])

    def test_expectation_reports_failure(self):
        result = {"status": "passed", "metrics": {"write_speed_mbps": 0}}
        expect = {
            "pass_policy": "all",
            "rules": [
                {
                    "field": "metrics.write_speed_mbps",
                    "operator": "gt",
                    "value": 0,
                    "message": "write speed must be positive",
                }
            ],
        }

        outcome = evaluate_expectation(result, expect)

        self.assertFalse(outcome["passed"])
        self.assertTrue(outcome["failures"])


if __name__ == "__main__":
    unittest.main()

