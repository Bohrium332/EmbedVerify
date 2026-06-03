"""Execution report writer."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class ReportWriter:
    """Write JSON and text reports."""

    def __init__(self, reports_dir: str | Path) -> None:
        self.reports_dir = Path(reports_dir)
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def write(self, report: dict[str, Any]) -> dict[str, Any]:
        request_id = str(report["request_id"])
        status = str(report["status"])
        report_dir = self.reports_dir / _report_dir_name(report)
        report_dir.mkdir(parents=True, exist_ok=True)
        outputs = _write_saved_outputs(report, report_dir)
        json_path = report_dir / "report.json"
        text_path = report_dir / "report.txt"

        with json_path.open("w", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2, ensure_ascii=False)

        with text_path.open("w", encoding="utf-8") as handle:
            handle.write(_to_text(report))

        return {"dir": str(report_dir), "json": str(json_path), "text": str(text_path), "outputs": outputs}


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
        code = result.get("code", "unknown")
        message = result.get("message", "")
        display_name = item.get("label") or item["function_name"]
        function_note = "" if display_name == item["function_name"] else f" ({item['function_name']})"
        skipped_note = " [skipped]" if item.get("skipped") else ""
        lines.append(
            f"- {item['case_name']}::{display_name}{function_note}: "
            f"code={code} {message}{skipped_note}"
        )
        metrics = result.get("metrics") or {}
        if metrics:
            lines.append(f"  metrics: {json.dumps(metrics, ensure_ascii=False)}")
        if item.get("output_file"):
            lines.append(f"  output: {item['output_file']}")
        failures = item.get("expectation", {}).get("failures") or []
        if failures:
            lines.append(f"  expectation failures: {json.dumps(failures, ensure_ascii=False)}")
    lines.append("")
    return "\n".join(lines)


def _report_dir_name(report: dict[str, Any]) -> str:
    request_id = _safe_name(str(report["request_id"]))
    status = _safe_name(str(report["status"]))
    started = str(report.get("started_at") or "")
    try:
        timestamp = datetime.fromisoformat(started).astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    except ValueError:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{timestamp}_{request_id}_{status}"


def _write_saved_outputs(report: dict[str, Any], report_dir: Path) -> dict[str, str]:
    outputs_dir = report_dir / "outputs"
    outputs: dict[str, str] = {}
    for index, item in enumerate(report.get("results", []), start=1):
        if not item.get("save_output"):
            continue
        outputs_dir.mkdir(parents=True, exist_ok=True)
        key = str(item.get("label") or item["function_name"])
        filename = f"{index:02d}_{_safe_name(item['case_name'])}__{_safe_name(key)}.json"
        output_path = outputs_dir / filename
        payload = {
            "case_name": item["case_name"],
            "function_name": item["function_name"],
            "label": item.get("label"),
            "result": item["result"],
            "expectation": item.get("expectation", {}),
            "skipped": bool(item.get("skipped")),
        }
        with output_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
        item["output_file"] = str(output_path)
        outputs[key] = str(output_path)
    return outputs


def _safe_name(value: str) -> str:
    cleaned = re.sub(r"[^0-9A-Za-z_.-]+", "_", value).strip("._")
    return cleaned or "item"
