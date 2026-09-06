"""CLI entrypoint: `python -m app.cli new-run --paper path.pdf --brief \"...\"`."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from app.paths import REPO_ROOT
from app.storage.run_store import RunStore


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="app.cli", description="MA-Darwin CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    new_run = sub.add_parser("new-run", help="Create a run directory and print the run id")
    new_run.add_argument("--paper", required=True, type=Path, help="Path to source PDF")
    new_run.add_argument("--brief", required=True, type=str, help="Freeform generation brief")
    new_run.add_argument(
        "--blueprint",
        default="msl_physician_8",
        help="Blueprint id (default: msl_physician_8)",
    )
    new_run.add_argument(
        "--skill-version",
        default="v1",
        help="Skill version directory name (default: v1)",
    )
    new_run.add_argument(
        "--runs-dir",
        type=Path,
        default=None,
        help="Override runs root (default: <repo>/runs)",
    )

    extract = sub.add_parser(
        "extract",
        help="Extract claim ledger and numbers index for an existing run",
    )
    extract.add_argument("--run-id", required=True, help="Run id (run_xxxxxxxxxxxx)")
    extract.add_argument(
        "--runs-dir",
        type=Path,
        default=None,
        help="Override runs root (default: <repo>/runs)",
    )
    return parser


def cmd_new_run(args: argparse.Namespace) -> int:
    paper = args.paper
    if not paper.is_file():
        print(f"error: paper not found: {paper}", file=sys.stderr)
        return 1

    store = RunStore(root=args.runs_dir) if args.runs_dir else RunStore()
    run = store.create_run(
        paper_path=paper,
        brief=args.brief,
        blueprint_id=args.blueprint,
        skill_version=args.skill_version,
    )
    # Print only the run id for easy scripting; path goes to stderr for humans.
    print(run.id)
    run_path = store.run_dir(run.id)
    try:
        display = run_path.resolve().relative_to(REPO_ROOT.resolve())
    except ValueError:
        display = run_path
    print(f"created {display}", file=sys.stderr)
    return 0


def cmd_extract(args: argparse.Namespace) -> int:
    from app.ingestion.ledger import extract_run

    store = RunStore(root=args.runs_dir) if args.runs_dir else RunStore()
    try:
        ledger_path, index_path = extract_run(args.run_id, store=store)
    except (KeyError, FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(ledger_path)
    print(index_path, file=sys.stderr)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "new-run":
        return cmd_new_run(args)
    if args.command == "extract":
        return cmd_extract(args)
    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
