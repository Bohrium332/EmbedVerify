"""Command line interface."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from embedverify.core.runner import RunnerError, SuiteRunner


def main(argv: list[str] | None = None) -> int:
    """Run the CLI."""

    parser = argparse.ArgumentParser(prog="ev")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="run a suite")
    run_parser.add_argument("suite", help="suite YAML path")
    run_parser.add_argument("--board", required=False, help="board profile name")
    run_parser.add_argument("--root", default=None, help="workspace root")
    run_parser.add_argument("--reports-dir", default=None, help="report output directory")
    run_parser.add_argument("--storage-device", default=None, help="USB storage block device, such as /dev/sda")
    run_parser.add_argument("--mount-point", default=None, help="USB storage mount point")
    run_parser.add_argument("--file-size-mb", type=int, default=None, help="write test file size")
    run_parser.add_argument("--read-min-speed-mbps", type=float, default=None, help="read speed threshold")
    run_parser.add_argument("--write-min-speed-mbps", type=float, default=None, help="write speed threshold")
    run_parser.add_argument("--dry-run", action="store_true", help="load configs without executing functions")

    case_parser = subparsers.add_parser("run-case", help="run a single case")
    case_parser.add_argument("case", help="case YAML path")
    case_parser.add_argument("--board", required=False, help="board profile name")
    case_parser.add_argument("--root", default=None, help="workspace root")
    case_parser.add_argument("--reports-dir", default=None, help="report output directory")
    case_parser.add_argument("--storage-device", default=None, help="storage block device, such as /dev/sda")
    case_parser.add_argument("--mount-point", default=None, help="storage mount point")
    case_parser.add_argument("--file-size-mb", type=int, default=None, help="write test file size")
    case_parser.add_argument("--read-min-speed-mbps", type=float, default=None, help="read speed threshold")
    case_parser.add_argument("--write-min-speed-mbps", type=float, default=None, help="write speed threshold")
    case_parser.add_argument("--dry-run", action="store_true", help="load configs without executing functions")

    function_parser = subparsers.add_parser("run-function", help="run a single function")
    function_parser.add_argument("function", help="function name, such as storage.detect")
    function_parser.add_argument("--params", default="{}", help="JSON object passed to the function")
    function_parser.add_argument("--board", required=False, help="board profile name")
    function_parser.add_argument("--root", default=None, help="workspace root")
    function_parser.add_argument("--reports-dir", default=None, help="report output directory")
    function_parser.add_argument("--dry-run", action="store_true", help="load configs without executing functions")

    args = parser.parse_args(argv)
    root = Path(args.root).resolve() if args.root else _discover_root(Path.cwd())
    runner = SuiteRunner(root)
    try:
        if args.command == "run":
            report = runner.run(
                args.suite,
                board_name=args.board,
                reports_dir=args.reports_dir,
                param_overrides=_storage_overrides(args),
                dry_run=args.dry_run,
            )
        elif args.command == "run-case":
            report = runner.run_case(
                args.case,
                board_name=args.board,
                reports_dir=args.reports_dir,
                param_overrides=_storage_overrides(args),
                dry_run=args.dry_run,
            )
        else:
            params = json.loads(args.params)
            if not isinstance(params, dict):
                raise ValueError("--params must be a JSON object")
            report = runner.run_function(
                args.function,
                params,
                board_name=args.board,
                reports_dir=args.reports_dir,
                dry_run=args.dry_run,
            )
    except (RunnerError, ValueError, FileNotFoundError, json.JSONDecodeError) as error:
        print(json.dumps({"status": "error", "message": str(error)}, indent=2), file=sys.stderr)
        return 2

    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["status"] in ("passed", "dry_run") else 1


def _discover_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (candidate / "boards").is_dir() and (candidate / "suites").is_dir():
            return candidate
    return start


def _storage_overrides(args: argparse.Namespace) -> dict[str, object]:
    return {
        "storage_device": args.storage_device,
        "mount_point": args.mount_point,
        "file_size_mb": args.file_size_mb,
        "read_min_speed_mbps": args.read_min_speed_mbps,
        "write_min_speed_mbps": args.write_min_speed_mbps,
    }


if __name__ == "__main__":
    raise SystemExit(main())
