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

    args = parser.parse_args(argv)
    root = Path(args.root).resolve() if args.root else _discover_root(Path.cwd())
    runner = SuiteRunner(root)
    overrides = {
        "storage_device": args.storage_device,
        "mount_point": args.mount_point,
        "file_size_mb": args.file_size_mb,
        "read_min_speed_mbps": args.read_min_speed_mbps,
        "write_min_speed_mbps": args.write_min_speed_mbps,
    }
    try:
        report = runner.run(
            args.suite,
            board_name=args.board,
            reports_dir=args.reports_dir,
            param_overrides=overrides,
            dry_run=args.dry_run,
        )
    except (RunnerError, ValueError, FileNotFoundError) as error:
        print(json.dumps({"status": "error", "message": str(error)}, indent=2), file=sys.stderr)
        return 2

    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["status"] in ("passed", "dry_run") else 1


def _discover_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (candidate / "boards").is_dir() and (candidate / "suites").is_dir():
            return candidate
    return start


if __name__ == "__main__":
    raise SystemExit(main())

