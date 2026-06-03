"""YAML configuration loader."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .models import BoardProfile, CaseSpec, FunctionSpec, ProjectConfig, SuiteSpec


class ConfigError(ValueError):
    """Raised when a configuration file is invalid."""


class ConfigLoader:
    """Load board, suite, and case configuration files."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).resolve()

    def load_board(self, board_name: str) -> BoardProfile:
        path = self.root / "boards" / f"{board_name}.yaml"
        data = self._load_mapping(path)
        return BoardProfile(
            name=self._required_str(data, "name", path),
            platform=self._required_str(data, "platform", path),
            adapter=str(data.get("adapter", "linux_generic")),
            capabilities=dict(data.get("capabilities", {})),
            interfaces=dict(data.get("interfaces", {})),
            tools_required=list(data.get("tools_required", [])),
            metadata=dict(data.get("metadata", {})),
        )

    def load_project_config(self) -> ProjectConfig:
        path = self.root / "config.yaml"
        if not path.exists():
            return ProjectConfig()
        data = self._load_mapping(path)
        board = data.get("board")
        report_dir = data.get("report_dir", "reports")
        log_level = data.get("log_level", "info")
        return ProjectConfig(
            board=board if isinstance(board, str) and board else None,
            report_dir=str(report_dir or "reports"),
            log_level=str(log_level or "info"),
        )

    def load_suite(self, suite_path: str | Path) -> SuiteSpec:
        path = self._resolve_path(suite_path)
        data = self._load_mapping(path)
        cases = data.get("cases")
        if not isinstance(cases, list) or not all(isinstance(item, str) for item in cases):
            raise ConfigError(f"{path}: 'cases' must be a list of paths")
        return SuiteSpec(
            name=self._required_str(data, "name", path),
            cases=cases,
            board=data.get("board") if isinstance(data.get("board"), str) else None,
            description=str(data.get("description", "")),
            execution=str(data.get("execution", "sequential")),
            report_enabled=bool(data.get("report_enabled", True)),
        )

    def load_case(self, case_path: str | Path, *, base_dir: str | Path | None = None) -> CaseSpec:
        path = self._resolve_path(case_path, base_dir=base_dir)
        data = self._load_mapping(path)
        raw_functions = data.get("functions")
        if not isinstance(raw_functions, list):
            raise ConfigError(f"{path}: 'functions' must be a list")
        functions: list[FunctionSpec] = []
        for index, raw in enumerate(raw_functions):
            if not isinstance(raw, dict):
                raise ConfigError(f"{path}: functions[{index}] must be a mapping")
            functions.append(
                FunctionSpec(
                    name=self._required_str(raw, "name", path),
                    params=dict(raw.get("params", {})),
                    expect=dict(raw["expect"]) if isinstance(raw.get("expect"), dict) else None,
                    timeout=int(raw["timeout"]) if raw.get("timeout") is not None else None,
                    enabled=bool(raw.get("enabled", True)),
                )
            )
        return CaseSpec(
            name=self._required_str(data, "name", path),
            description=str(data.get("description", "")),
            module=str(data.get("module", "")),
            execution=str(data.get("execution", "sequential")),
            functions=functions,
        )

    def _resolve_path(self, value: str | Path, *, base_dir: str | Path | None = None) -> Path:
        path = Path(value)
        if path.is_absolute():
            return path
        if base_dir is not None:
            candidate = Path(base_dir) / path
            if candidate.exists():
                return candidate.resolve()
        return (self.root / path).resolve()

    @staticmethod
    def _load_mapping(path: Path) -> dict[str, Any]:
        if not path.exists():
            raise ConfigError(f"config file not found: {path}")
        with path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
        if not isinstance(data, dict):
            raise ConfigError(f"{path}: top-level config must be a mapping")
        return data

    @staticmethod
    def _required_str(data: dict[str, Any], key: str, path: Path) -> str:
        value = data.get(key)
        if not isinstance(value, str) or not value:
            raise ConfigError(f"{path}: '{key}' is required")
        return value
