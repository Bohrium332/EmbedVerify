"""Suite execution runner."""

from __future__ import annotations

import importlib
import time
import uuid
from pathlib import Path
from typing import Any, Callable

from embedverify.capabilities.registry import build_capability_registry

from .config_loader import ConfigLoader
from .expectations import evaluate_expectation
from .models import BoardProfile, ExecutionRecord, utc_now_iso
from .report import ReportWriter


class RunnerError(RuntimeError):
    """Raised when execution cannot start."""


class SuiteRunner:
    """Load and run suites."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).resolve()
        self.loader = ConfigLoader(self.root)

    def run(
        self,
        suite_path: str | Path,
        *,
        board_name: str | None = None,
        reports_dir: str | Path | None = None,
        param_overrides: dict[str, Any] | None = None,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Run a suite and return the final report dictionary."""

        suite = self.loader.load_suite(suite_path)
        project_config = self.loader.load_project_config()
        selected_board = board_name or project_config.board
        if not selected_board:
            raise RunnerError("board is required, either in --board or config.yaml")
        board = self.loader.load_board(selected_board)
        capabilities = build_capability_registry(board)

        records: list[ExecutionRecord] = []
        if not dry_run:
            for case_ref in suite.cases:
                case = self.loader.load_case(case_ref)
                for function in case.functions:
                    if not function.enabled:
                        continue
                    params = _apply_overrides(function.name, function.params, param_overrides or {})
                    started = utc_now_iso()
                    started_perf = time.perf_counter()
                    result = _invoke_function(function.name, params, capabilities)
                    expectation = evaluate_expectation(result, function.expect)
                    finished = utc_now_iso()
                    records.append(
                        ExecutionRecord(
                            case_name=case.name,
                            function_name=function.name,
                            result=result,
                            expectation=expectation,
                            started_at=started,
                            finished_at=finished,
                            duration_ms=int((time.perf_counter() - started_perf) * 1000),
                        )
                    )

        status = "passed" if all(item.expectation.get("passed") for item in records) else "failed"
        if dry_run:
            status = "dry_run"
        report = {
            "request_id": uuid.uuid4().hex[:12],
            "suite": suite.name,
            "board": board.name,
            "status": status,
            "started_at": records[0].started_at if records else utc_now_iso(),
            "finished_at": records[-1].finished_at if records else utc_now_iso(),
            "results": [
                {
                    "case_name": item.case_name,
                    "function_name": item.function_name,
                    "result": item.result,
                    "expectation": item.expectation,
                    "started_at": item.started_at,
                    "finished_at": item.finished_at,
                    "duration_ms": item.duration_ms,
                }
                for item in records
            ],
            "board_profile": _board_to_dict(board),
        }

        if suite.report_enabled and not dry_run:
            writer = ReportWriter(reports_dir or (self.root / project_config.report_dir))
            report["report_files"] = writer.write(report)
        return report


def _invoke_function(
    name: str,
    params: dict[str, Any],
    capabilities: dict[str, Any],
) -> dict[str, Any]:
    module_name, function_name = _split_function_name(name)
    module = importlib.import_module(f"embedverify.functions.{module_name}")
    callable_obj: Callable[..., dict[str, Any]] = getattr(module, function_name)
    return callable_obj(**params, capability_registry=capabilities)


def _split_function_name(name: str) -> tuple[str, str]:
    parts = name.split(".")
    if len(parts) != 2:
        raise RunnerError(f"function name must be module.function: {name}")
    return parts[0], parts[1]


def _apply_overrides(name: str, params: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    updated = dict(params)
    if name in ("storage.info", "storage.write_speed") and overrides.get("mount_point"):
        updated["mount_point"] = overrides["mount_point"]
    if name in ("storage.info", "storage.read_speed") and overrides.get("storage_device"):
        updated["device"] = overrides["storage_device"]
    if name == "storage.write_speed" and overrides.get("file_size_mb") is not None:
        updated["file_size_mb"] = int(overrides["file_size_mb"])
    if name == "storage.read_speed" and overrides.get("read_min_speed_mbps") is not None:
        updated["min_speed_mbps"] = float(overrides["read_min_speed_mbps"])
    if name == "storage.write_speed" and overrides.get("write_min_speed_mbps") is not None:
        updated["min_speed_mbps"] = float(overrides["write_min_speed_mbps"])
    return updated


def _board_to_dict(board: BoardProfile) -> dict[str, Any]:
    return {
        "name": board.name,
        "platform": board.platform,
        "adapter": board.adapter,
        "capabilities": board.capabilities,
        "interfaces": board.interfaces,
        "tools_required": board.tools_required,
        "metadata": board.metadata,
    }
