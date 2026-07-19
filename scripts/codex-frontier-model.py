#!/usr/bin/env python3
"""Resolve the current Codex frontier model from the live models cache.

OpenAI changes frontier model names over time (gpt-5.3 -> gpt-5.4 -> gpt-5.5 -> ...),
so we never hard-code a version. The Codex CLI fetches the account's available models
into ~/.codex/models_cache.json (with a server-assigned `priority`; lower = more
frontier). This script reads that cache and prints the top model, so the adversarial
review always runs on whatever OpenAI currently ships as frontier.

Usage:
  python3 scripts/codex-frontier-model.py              # print the frontier slug (e.g. gpt-5.5)
  python3 scripts/codex-frontier-model.py --write-config  # also sync ~/.codex/config.toml

Selection: among models that are visible (visibility == "list") and API-supported,
pick the one with the smallest `priority`. Exits non-zero with a message on stderr if
the cache is missing or yields no candidate (caller should fall back to `codex`'s own
default or pass --model explicitly).

KNOWN LIMITATION — this script CANNOT guarantee the slug it prints is runnable.
The cache carries no minimum-client-version field, so a model newer than the pinned Codex
CLI still looks like a perfectly good candidate here. Re-verified 2026-07-19 by dumping every
key across all 7 cached models: the only version-ish field is `multi_agent_version`, which is
an unrelated capability marker and not documented as a client-compatibility contract, so keying
off it would be guesswork.

Live example on 2026-07-19 (unchanged since it was first hit on 2026-07-18): this script returns
`gpt-5.6-sol` (priority 1), and `codex exec -m gpt-5.6-sol` fails with

    ERROR: {"type":"error","status":400,... "requires a newer version of Codex ..."}

The fix therefore lives at the POINT OF USE, not here: `scripts/codex-review.py` walks
`resolve_candidates()` in priority order and falls through to the next slug when one fails.
Prefer that wrapper over this script for anything that must actually produce a review.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

CACHE = os.path.expanduser("~/.codex/models_cache.json")
CONFIG = os.path.expanduser("~/.codex/config.toml")
BEGIN = "# >>> codex-frontier (managed by scripts/codex-frontier-model.py) >>>"
END = "# <<< codex-frontier <<<"


def resolve_candidates() -> "list[str]":
    """All usable model slugs, most-frontier FIRST (ascending `priority`).

    Returns the WHOLE ordered list, not just the winner, because the cache cannot tell us which
    models the locally-pinned Codex CLI supports — see "Known limitation" in the module docstring.
    `scripts/codex-review.py` walks this list, so a top-priority slug the CLI rejects costs one
    failed attempt instead of silently yielding an empty review.
    """
    try:
        with open(CACHE, encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        sys.exit(f"error: {CACHE} not found — run `codex` once to populate the model cache")
    except (OSError, json.JSONDecodeError) as e:
        sys.exit(f"error: cannot read {CACHE}: {e}")

    candidates = [
        m for m in data.get("models", [])
        if m.get("visibility") == "list"
        and m.get("supported_in_api")
        and isinstance(m.get("priority"), (int, float))
        and m.get("slug")
    ]
    if not candidates:
        sys.exit("error: no visible, API-supported model with a priority found in cache")

    # Lower priority number = more frontier.
    return [m["slug"] for m in sorted(candidates, key=lambda m: m["priority"])]


def resolve_frontier() -> str:
    """The single most-frontier slug. Kept for callers that just want a model to pass to --model."""
    return resolve_candidates()[0]


def write_config(slug: str) -> None:
    """Insert/replace a managed top-level `model = "..."` block at the top of config.toml.

    Top-level TOML keys must precede any [table], so the managed block goes first.
    Idempotent: a prior managed block is stripped before the fresh one is written.
    """
    existing = ""
    if os.path.exists(CONFIG):
        with open(CONFIG, encoding="utf-8") as f:
            existing = f.read()
    # Remove any previous managed block.
    existing = re.sub(rf"{re.escape(BEGIN)}.*?{re.escape(END)}\n?", "", existing, flags=re.DOTALL)
    block = (
        f"{BEGIN}\n"
        f"# Current frontier model, derived from ~/.codex/models_cache.json (lowest priority).\n"
        f"# Do NOT hand-edit the slug — re-run scripts/codex-frontier-model.py --write-config to refresh.\n"
        f'model = "{slug}"\n'
        f"{END}\n"
    )
    os.makedirs(os.path.dirname(CONFIG), exist_ok=True)
    with open(CONFIG, "w", encoding="utf-8") as f:
        f.write(block + existing.lstrip("\n"))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--write-config", action="store_true",
                    help="sync the resolved model into ~/.codex/config.toml (managed block)")
    ap.add_argument("--list", action="store_true",
                    help="print ALL candidate slugs, most-frontier first (one per line)")
    args = ap.parse_args()

    if args.list:
        for s in resolve_candidates():
            print(s)
        return

    slug = resolve_frontier()
    if args.write_config:
        write_config(slug)
        print(f"synced ~/.codex/config.toml -> model = \"{slug}\"", file=sys.stderr)
    print(slug)


if __name__ == "__main__":
    main()
