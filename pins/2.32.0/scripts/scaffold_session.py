#!/usr/bin/env python3
"""Create the session folder structure for a research session.

Usage:
    python scripts/scaffold_session.py --ticker JPM --date 2026-07-25 \\
      --orchestrator-model grok-4.5

    # Second run same as-of day (auto session_key …/YYYY-MM-DD__r2)
    python scripts/scaffold_session.py --ticker META --date 2026-08-10 \\
      --orchestrator-model grok-4.5

    # Named run / experiment
    python scripts/scaffold_session.py --ticker META --date 2026-08-10 \\
      --experiment exp-model-bakeoff --slug model-grok45 --replicate 1 \\
      --orchestrator-model grok-4.5 --subagent-model grok-4.5

Creates archive/research/<TICKER>/<SESSION_KEY>/{reports,data/...,charts,registry,meta},
writes registry/phase_status.json, registry/session_isolation.json, meta/run_manifest.json.
Same-day re-runs auto-allocate __rN when the bare date folder is taken (unless --slug).

``--orchestrator-model`` is **required** (or env RESEARCH_ORCHESTRATOR_MODEL). It is
stamped into meta/run_manifest.json at scaffold time so the model id never has to be
recalled after a long context. Subagent model defaults to the orchestrator model.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from packages.kd_research.scaffold import SUBDIRS, scaffold  # noqa: E402
from packages.kd_research.ticker_lookup import live_ticker_check  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ticker", required=True)
    ap.add_argument(
        "--date",
        required=True,
        help="As-of session date YYYY-MM-DD (or full session_key date__slug)",
    )
    ap.add_argument(
        "--slug",
        default=None,
        help="Optional run slug → folder date__slug. If omitted and bare date "
        "folder is taken, auto-allocates r2, r3, …",
    )
    ap.add_argument(
        "--experiment",
        dest="experiment_id",
        default=None,
        help="Experiment id grouping A/B runs in the compare DB",
    )
    ap.add_argument(
        "--experiment-label",
        default=None,
        help="Human label for the experiment (default: --experiment value)",
    )
    ap.add_argument(
        "--replicate",
        type=int,
        default=None,
        help="Replicate number within an experiment (1..N)",
    )
    ap.add_argument(
        "--orchestrator-model",
        default=None,
        help=(
            "Required LLM id for the main/orchestrator agent (e.g. grok-4.5). "
            "Or set env RESEARCH_ORCHESTRATOR_MODEL. Stamped at scaffold only."
        ),
    )
    ap.add_argument(
        "--subagent-model",
        dest="default_subagent_model",
        default=None,
        help=(
            "Default LLM id for subagents (defaults to --orchestrator-model). "
            "Or set env RESEARCH_SUBAGENT_MODEL."
        ),
    )
    ap.add_argument(
        "--notes",
        default=None,
        help="Why this run exists (bakeoff axis, hypothesis, etc.)",
    )
    ap.add_argument(
        "--output-dir",
        default=None,
        help="Project root or archive path override (default: ARCHIVE_ROOT or "
        "<workspace>/archive).",
    )
    ap.add_argument(
        "--no-auto-replicate",
        action="store_true",
        help="Do not auto-allocate __rN; refuse if bare date folder exists",
    )
    ap.add_argument("--force", action="store_true")
    ap.add_argument(
        "--skip-ticker-check",
        action="store_true",
        help="Skip market-ticker lookup (tests/offline only). New Mode A runs must not pass this.",
    )
    args = ap.parse_args()
    ticker = args.ticker.strip().upper()
    if not args.skip_ticker_check:
        try:
            checked = live_ticker_check(args.ticker)
        except RuntimeError as e:
            raise SystemExit(f"TICKER CHECK ABORTED: {e}") from e
        if not checked.ok:
            raise SystemExit(f"TICKER CHECK ABORTED: {checked.reason}")
        ticker = checked.typed
    try:
        root = scaffold(
            ticker,
            args.date,
            args.output_dir,
            args.force,
            slug=args.slug,
            experiment_id=args.experiment_id,
            experiment_label=args.experiment_label,
            replicate=args.replicate,
            orchestrator_model=args.orchestrator_model,
            default_subagent_model=args.default_subagent_model,
            notes=args.notes,
            auto_replicate=not args.no_auto_replicate,
        )
    except (ValueError, RuntimeError, FileExistsError) as e:
        raise SystemExit(str(e)) from e
    sk = root.name
    man_path = root / "meta" / "run_manifest.json"
    man = json.loads(man_path.read_text(encoding="utf-8")) if man_path.is_file() else {}
    print(f"Session scaffolded: {root}")
    print(f"  session_key={sk}")
    print(f"  quote_symbol={man.get('quote_symbol')!r} (orchestrator stamps after tools)")
    print(f"  orchestrator_model={man.get('orchestrator_model')}")
    print(f"  default_subagent_model={man.get('default_subagent_model')}")
    for sub in SUBDIRS:
        print(f"  {root / sub}/")
    print(f"  {root / 'registry' / 'phase_status.json'}")
    print(f"  {root / 'registry' / 'session_isolation.json'}")
    print(f"  {root / 'meta' / 'run_manifest.json'}")


if __name__ == "__main__":
    main()
