"""CLI entrypoint: `python -m app.cli new-run --paper path.pdf --brief \"...\"`."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from app.llm_env import ensure_dotenv
from app.paths import REPO_ROOT
from app.storage.run_store import RunStore

ensure_dotenv()


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

    compare = sub.add_parser(
        "compare-layout",
        help="Write one deck's SVGs and pptx side by side for visual fidelity review",
    )
    compare.add_argument("--layout", type=Path, default=None, help="Path to layout_spec.json")
    compare.add_argument("--run-id", default=None, help="Load layout_spec.json from a run's latest round")
    compare.add_argument("--round", type=int, default=None, dest="round_n", help="Round number (with --run-id)")
    compare.add_argument("--out", type=Path, required=True, help="Output directory")
    compare.add_argument(
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


def cmd_compare_layout(args: argparse.Namespace) -> int:
    from app.generation.layout import load_layout_spec
    from app.generation.pptx_writer import write_pptx
    from app.rendering.svg_renderer import write_slide_svgs

    layout_path = args.layout
    if layout_path is None:
        if not args.run_id:
            print("error: provide --layout or --run-id", file=sys.stderr)
            return 1
        store = RunStore(root=args.runs_dir) if args.runs_dir else RunStore()
        run = store.get_run(args.run_id)
        n = args.round_n or run.best_round_n or (run.rounds[-1].n if run.rounds else 1)
        layout_path = store.round_dir(args.run_id, n) / "layout_spec.json"
    if not Path(layout_path).is_file():
        print(f"error: layout spec not found: {layout_path}", file=sys.stderr)
        return 1
    spec = load_layout_spec(layout_path)
    out = Path(args.out)
    svg_dir = out / "svg"
    write_slide_svgs(spec, svg_dir)
    pptx = write_pptx(spec, out / "deck.pptx")
    print(svg_dir)
    print(pptx, file=sys.stderr)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "new-run":
        return cmd_new_run(args)
    if args.command == "extract":
        return cmd_extract(args)
    if args.command == "compare-layout":
        return cmd_compare_layout(args)
    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
