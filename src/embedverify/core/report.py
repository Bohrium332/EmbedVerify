"""Execution report writer."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class ReportWriter:
    """Write JSON and text reports."""

    def __init__(self, reports_dir: str | Path) -> None:
        self.reports_dir = Path(reports_dir)
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def write(self, report: dict[str, Any]) -> dict[str, str]:
        request_id = str(report["request_id"])
        status = str(report["status"])
        json_path = self.reports_dir / f"{request_id}_{status}.json"
        text_path = self.reports_dir / f"{request_id}_{status}.txt"

        with json_path.open("w", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2, ensure_ascii=False)

        with text_path.open("w", encoding="utf-8") as handle:
            handle.write(_to_text(report))

        return {"json": str(json_path), "text": str(text_path)}


def _to_text(report: dict[str, Any]) -> str:
    lines = [
        f"Request: {report['request_id']}",
        f"Suite: {report['suite']}",
        f"Board: {report['board']}",
        f"Status: {report['status']}",
        "",
        "Results:",
    ]
    for item in report.get("results", []):
        result = item["result"]
        lines.append(
            f"- {item['case_name']}::{item['function_name']}: "
            f"{result.get('status')} ({result.get('code')}) {result.get('message', '')}"
        )
        metrics = result.get("metrics") or {}
        if metrics:
            lines.append(f"  metrics: {json.dumps(metrics, ensure_ascii=False)}")
        failures = item.get("expectation", {}).get("failures") or []
        if failures:
            lines.append(f"  expectation failures: {json.dumps(failures, ensure_ascii=False)}")
    lines.append("")
    return "\n".join(lines)

