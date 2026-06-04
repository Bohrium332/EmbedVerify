"""Suite execution runner."""

from __future__ import annotations

import importlib
from importlib import util as importlib_util
import re
import time
import uuid
from pathlib import Path
from typing import Any, Callable

from embedverify.capabilities.registry import build_capability_registry

from .config_loader import ConfigLoader
from .expectations import evaluate_expectation
from .models import BoardProfile, CaseSpec, ExecutionRecord, utc_now_iso
from .report import ReportWriter


class RunnerError(RuntimeError):
    """Raised when execution cannot start."""


class TemplateError(ValueError):
    """Raised when a parameter template cannot be resolved."""


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
        board = self._load_board(board_name)
        capabilities = build_capability_registry(board)

        records: list[ExecutionRecord] = []
        if not dry_run:
            for case_ref in suite.cases:
                case = self.loader.load_case(case_ref)
                records.extend(_execute_case(case, board, capabilities, param_overrides or {}))

        status = "passed" if all(item.expectation.get("passed") for item in records) else "failed"
        if dry_run:
            status = "dry_run"
        report = _build_report(records, board, suite.name, status, target_type="suite")

        if suite.report_enabled and not dry_run:
            writer = ReportWriter(reports_dir or (self.root / project_config.report_dir))
            report["report_files"] = writer.write(report)
        return report

    def run_case(
        self,
        case_path: str | Path,
        *,
        board_name: str | None = None,
        reports_dir: str | Path | None = None,
        param_overrides: dict[str, Any] | None = None,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Run a single case config and return the report dictionary."""

        case = self.loader.load_case(case_path)
        project_config = self.loader.load_project_config()
        board = self._load_board(board_name)
        capabilities = build_capability_registry(board)
        records = [] if dry_run else _execute_case(case, board, capabilities, param_overrides or {})
        status = "dry_run" if dry_run else ("passed" if all(item.expectation.get("passed") for item in records) else "failed")
        report = _build_report(records, board, case.name, status, target_type="case")
        if not dry_run:
            writer = ReportWriter(reports_dir or (self.root / project_config.report_dir))
            report["report_files"] = writer.write(report)
        return report

    def run_function(
        self,
        function_name: str,
        params: dict[str, Any],
        *,
        board_name: str | None = None,
        reports_dir: str | Path | None = None,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Run a single function and return the report dictionary."""

        project_config = self.loader.load_project_config()
        board = self._load_board(board_name)
        records: list[ExecutionRecord] = []
        if not dry_run:
            capabilities = build_capability_registry(board)
            started = utc_now_iso()
            started_perf = time.perf_counter()
            result = _invoke_function(function_name, params, capabilities)
            expectation = evaluate_expectation(
                result,
                {
                    "pass_policy": "all",
                    "rules": [{"field": "code", "operator": "eq", "value": 0}],
                },
            )
            finished = utc_now_iso()
            records.append(
                ExecutionRecord(
                    case_name="single_function",
                    function_name=function_name,
                    label=None,
                    result=result,
                    expectation=expectation,
                    started_at=started,
                    finished_at=finished,
                    duration_ms=int((time.perf_counter() - started_perf) * 1000),
                    skipped=False,
                    save_output=True,
                )
            )
        status = "dry_run" if dry_run else ("passed" if all(item.expectation.get("passed") for item in records) else "failed")
        report = _build_report(records, board, function_name, status, target_type="function")
        if not dry_run:
            writer = ReportWriter(reports_dir or (self.root / project_config.report_dir))
            report["report_files"] = writer.write(report)
        return report

    def _load_board(self, board_name: str | None) -> BoardProfile:
        project_config = self.loader.load_project_config()
        selected_board = board_name or project_config.board
        if not selected_board:
            raise RunnerError("board is required, either in --board or config.yaml")
        return self.loader.load_board(selected_board)


def _invoke_function(
    name: str,
    params: dict[str, Any],
    capabilities: dict[str, Any],
) -> dict[str, Any]:
    module_name, function_name = _split_function_name(name)
    entrypoint_module = f"embedverify.functions.{module_name}.{function_name}"
    if _module_exists(entrypoint_module):
        module = importlib.import_module(entrypoint_module)
        callable_obj: Callable[..., dict[str, Any]] = getattr(module, "execute")
        return callable_obj(params, capability_registry=capabilities)

    legacy_module = importlib.import_module(f"embedverify.functions.{module_name}")
    callable_obj = getattr(legacy_module, function_name)
    return callable_obj(**params, capability_registry=capabilities)


def _execute_case(
    case: CaseSpec,
    board: BoardProfile,
    capabilities: dict[str, Any],
    param_overrides: dict[str, Any],
) -> list[ExecutionRecord]:
    records: list[ExecutionRecord] = []
    case_failed = False
    case_failure_reason = ""
    context: dict[str, Any] = {
        "board": _board_to_dict(board),
        "case": {"name": case.name, "module": case.module},
    }
    for function in case.functions:
        if not function.enabled:
            continue
        started = utc_now_iso()
        started_perf = time.perf_counter()
        skipped = False
        if function.skip_on_fail and case_failed:
            skipped = True
            result = _skipped_result(case_failure_reason)
            expectation = {"passed": True, "policy": "skipped", "failures": []}
        else:
            try:
                rendered_params = _render_templates(function.params, context)
                params = _apply_overrides(function.name, rendered_params, param_overrides)
                result = _invoke_function(function.name, params, capabilities)
            except TemplateError as exc:
                result = _runner_failed_result("parameter template resolution failed", {"error": str(exc)})
            expectation = evaluate_expectation(result, function.expect)
            if not expectation.get("passed"):
                case_failed = True
                case_failure_reason = f"{function.name}: {result.get('message', 'failed')}"
        finished = utc_now_iso()
        record = ExecutionRecord(
            case_name=case.name,
            function_name=function.name,
            label=function.label,
            result=result,
            expectation=expectation,
            started_at=started,
            finished_at=finished,
            duration_ms=int((time.perf_counter() - started_perf) * 1000),
            skipped=skipped,
            save_output=function.save_output,
        )
        records.append(record)
        _register_context(context, record)
    return records


def _build_report(
    records: list[ExecutionRecord],
    board: BoardProfile,
    target_name: str,
    status: str,
    *,
    target_type: str,
) -> dict[str, Any]:
    return {
        "request_id": uuid.uuid4().hex[:12],
        "suite": target_name,
        "target_type": target_type,
        "board": board.name,
        "status": status,
        "started_at": records[0].started_at if records else utc_now_iso(),
        "finished_at": records[-1].finished_at if records else utc_now_iso(),
        "results": [
            {
                "case_name": item.case_name,
                "function_name": item.function_name,
                "label": item.label,
                "result": item.result,
                "expectation": item.expectation,
                "started_at": item.started_at,
                "finished_at": item.finished_at,
                "duration_ms": item.duration_ms,
                "skipped": item.skipped,
                "save_output": item.save_output,
            }
            for item in records
        ],
        "board_profile": _board_to_dict(board),
    }


def _module_exists(module_name: str) -> bool:
    try:
        return importlib_util.find_spec(module_name) is not None
    except (AttributeError, ModuleNotFoundError):
        return False


def _split_function_name(name: str) -> tuple[str, str]:
    parts = name.split(".")
    if len(parts) != 2:
        raise RunnerError(f"function name must be module.function: {name}")
    return parts[0], parts[1]


def _apply_overrides(name: str, params: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    updated = dict(params)
    if name in ("storage.info", "storage.write_speed", "storage.integrity_check") and overrides.get("mount_point"):
        updated["mount_point"] = overrides["mount_point"]
    if name in ("storage.detect", "storage.info", "storage.read_speed", "storage.write_speed", "storage.integrity_check") and overrides.get("storage_device"):
        updated["device"] = overrides["storage_device"]
    if name in ("storage.write_speed", "storage.integrity_check") and overrides.get("file_size_mb") is not None:
        updated["file_size_mb"] = int(overrides["file_size_mb"])
    if name == "storage.read_speed" and overrides.get("read_min_speed_mbps") is not None:
        updated["min_speed_mbps"] = float(overrides["read_min_speed_mbps"])
    if name == "storage.write_speed" and overrides.get("write_min_speed_mbps") is not None:
        updated["min_speed_mbps"] = float(overrides["write_min_speed_mbps"])
    return updated


_TEMPLATE_RE = re.compile(r"{{\s*([^{}]+?)\s*}}")
_FULL_TEMPLATE_RE = re.compile(r"^\s*{{\s*([^{}]+?)\s*}}\s*$")


def _render_templates(value: Any, context: dict[str, Any]) -> Any:
    if isinstance(value, dict):
        return {key: _render_templates(item, context) for key, item in value.items()}
    if isinstance(value, list):
        return [_render_templates(item, context) for item in value]
    if not isinstance(value, str):
        return value

    full_match = _FULL_TEMPLATE_RE.match(value)
    if full_match:
        return _resolve_template_path(full_match.group(1), context)

    def replace(match: re.Match[str]) -> str:
        resolved = _resolve_template_path(match.group(1), context)
        return str(resolved)

    return _TEMPLATE_RE.sub(replace, value)


def _resolve_template_path(path: str, context: dict[str, Any]) -> Any:
    current: Any = context
    for part in [item.strip() for item in path.split(".") if item.strip()]:
        if isinstance(current, dict):
            if part not in current:
                raise TemplateError(f"template key not found: {path}")
            current = current[part]
        elif isinstance(current, list):
            try:
                current = current[int(part)]
            except (ValueError, IndexError) as exc:
                raise TemplateError(f"template list index not found: {path}") from exc
        else:
            raise TemplateError(f"template path cannot descend into {part!r}: {path}")
    return current


def _register_context(context: dict[str, Any], record: ExecutionRecord) -> None:
    entry = {
        "case_name": record.case_name,
        "function_name": record.function_name,
        "label": record.label,
        "result": record.result,
        "expectation": record.expectation,
        "skipped": record.skipped,
    }
    context["last"] = entry
    context[_context_key(record.function_name)] = entry
    if record.label:
        context[record.label] = entry


def _context_key(name: str) -> str:
    return re.sub(r"[^0-9A-Za-z_]+", "_", name).strip("_")


def _skipped_result(reason: str) -> dict[str, Any]:
    return {
        "code": 2,
        "message": "skipped because a previous function failed",
        "details": {"reason": reason},
        "metrics": {},
    }


def _runner_failed_result(message: str, details: dict[str, Any]) -> dict[str, Any]:
    return {"code": -1, "message": message, "details": details, "metrics": {}}


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
