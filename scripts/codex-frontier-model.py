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
  python3 scripts/codex-frontier-model.py --self-test   # 19 cases, pure, no network

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


def usable_models(data: dict) -> "list[str]":
    """LISTED, API-supported model slugs, most-frontier FIRST (ascending `priority`). PURE.

    ⛔ `visibility == "list"` IS REQUIRED, AND THAT REQUIREMENT IS THE POINT. `"hide"` is the
    server saying *not this one* — so accepting a hidden model silently commits every adversarial
    review to whatever the vendor has stopped advertising. Measured 2026-10-07: a FRESH fetch
    returned exactly two models, both hidden — `gpt-5.5`, whose own `description` is **"Legacy
    coding model."**, and `codex-auto-review`, which is `tool_mode: code_mode_only` and
    purpose-built for approval review. A loosened predicate would have picked the legacy one today
    and the special-purpose one the day it is withdrawn, REPORTING SUCCESS both times. That is the
    downgraded-gate-that-still-reports failure `docs/plugins.md` warns about above all others.

    ⚠ AN EARLIER DRAFT OF THIS FUNCTION DID LOOSEN IT, and the owner caught the mistake with one
    question: *"why do we have to use hidden model? why not use a listed model?"* The answer was
    that the CLI was 18 minor versions behind (0.142.5 against 0.160.1) and the server keys its
    answer to `client_version`, so this client was being offered no current model at all. The fix
    belongs at THAT layer, not here. What belongs here is a refusal that says so — see
    `refusal_message`.

    ⭐ CONFIRMED BY DOING IT. After `codex update` to 0.160.1 the same account's cache went from
    2 models (both hidden) to **10, SEVEN of them `list`**, topped by `gpt-6.1-sol` ("Latest
    workhorse model for coding and everyday work") and `gpt-6-astra` ("Frontier intelligence for
    the most demanding work"). This function, unchanged and strict, resolves `gpt-6.1-sol`. Two
    whole model generations were invisible to the old client, and the loosened draft would have
    run every adversarial review on the Legacy one instead — silently, and forever.
    """
    api = [m for m in data.get("models", [])
           if m.get("supported_in_api")
           and isinstance(m.get("priority"), (int, float))
           and not isinstance(m.get("priority"), bool)   # True is an int in Python
           and m.get("slug")]
    listed = sorted((m for m in api if m.get("visibility") == "list"),
                    key=lambda m: m["priority"])
    return [m["slug"] for m in listed]


def refusal_message(data: dict) -> str:
    """Why no model could be resolved, in terms the operator can ACT on. PURE.

    ⛔ THE OLD MESSAGE WAS "error: no visible, API-supported model with a priority found in
    cache", AND IT COST A WHOLE REVIEW ROUND. It states the predicate that failed and nothing
    about the world, so the only available reading was "Codex is unavailable" — which was false:
    `codex exec -m gpt-5.5` worked first try. A refusal that cannot be acted on gets read as an
    outage, and the documented response to an outage is to fall back to a single reviewer.

    So this names what was actually seen: how many models the cache holds, which ones are hidden
    but otherwise usable (the near-misses, which are the whole clue), the `client_version` the
    server keyed its answer to, and the one command that changes any of it.
    """
    models = data.get("models", [])
    near = sorted((m for m in models
                   if m.get("supported_in_api") and m.get("visibility") != "list"
                   and m.get("slug")),
                  key=lambda m: m.get("priority") if isinstance(m.get("priority"), (int, float))
                  else 1e9)
    bits = [f"error: no LISTED, API-supported model in {CACHE}"]
    bits.append(f"  the cache holds {len(models)} model(s), fetched by client_version "
                f"{data.get('client_version') or '?'}")
    if near:
        bits.append("  hidden but otherwise usable: "
                    + ", ".join(f"{m['slug']} ({m.get('description') or 'no description'})"
                                for m in near))
        bits.append("  `hide` means the server is NOT offering it — do not reach for it; a model "
                    "the vendor stopped advertising is one it is withdrawing.")
    bits.append("  MOST LIKELY CAUSE: this Codex CLI is behind, and the server keys the model list "
                "to client_version. Run `codex update`, then re-run this.")
    bits.append("  ⛔ TREAT THIS AS THE GATE NOT HAVING RUN. It is not evidence that Codex is "
                "unavailable — verify that separately with `codex exec -m <slug> ...` from inside "
                "a git worktree before recording a REVIEW GAP.")
    return "\n".join(bits)


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

    slugs = usable_models(data)
    if not slugs:
        sys.exit(refusal_message(data))
    return slugs


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


def _self_test() -> int:
    """The ordering rule, over fixtures. No cache, no network."""
    ok = fail = 0

    def case(name: str, got, want) -> None:
        nonlocal ok, fail
        if got == want:
            ok += 1
        else:
            print(f"[FAIL] {name}\n       expected {want!r}\n       got      {got!r}")
            fail += 1

    def M(slug, priority=1, visibility="list", api=True, **kw):
        d = {"slug": slug, "priority": priority, "visibility": visibility,
             "supported_in_api": api}
        d.update(kw)
        return d

    # ⚠ TWO DISTINCT `data` VALUES THROUGHOUT — a function ignoring its argument must not pass.
    LIVE = {"client_version": "0.142.5", "models": [
        M("gpt-5.5", 13, "hide", description="Legacy coding model."),
        M("codex-auto-review", 43, "hide", description="Automatic approval review model."),
    ]}

    case("a LISTED model is returned",
         usable_models({"models": [M("shown", 7)]}), ["shown"])
    case("...ordered by ASCENDING priority, most-frontier first",
         usable_models({"models": [M("c", 30), M("a", 10), M("b", 20)]}), ["a", "b", "c"])
    case("...which a DIFFERENT set orders differently, so the input is read",
         usable_models({"models": [M("z", 5), M("y", 7)]}), ["z", "y"])
    # ⭐ THE CASE THAT PINS THE WHOLE DECISION. `hide` is the server declining to offer a model;
    # accepting one commits every review to something being withdrawn. An earlier draft DID accept
    # them and this case is what refuses that draft.
    case("⭐ a HIDDEN model is EXCLUDED even when supported_in_api — `hide` means not this one",
         usable_models(LIVE), [])
    case("...and an unknown visibility value is excluded too, since it is not `list`",
         usable_models({"models": [M("weird", 2, "archived")]}), [])
    case("a model not supported in the API is excluded",
         usable_models({"models": [M("no", 1, api=False), M("yes", 2)]}), ["yes"])
    case("...and one with no priority at all is excluded",
         usable_models({"models": [{"slug": "np", "visibility": "list",
                                    "supported_in_api": True}, M("ok", 4)]}), ["ok"])
    case("...and one whose priority is not a number is excluded",
         usable_models({"models": [M("txt", "first"), M("ok2", 4)]}), ["ok2"])
    # ⚠ `True` is an `int` in Python, so `isinstance(p, (int, float))` admits it. A boolean
    # priority is a malformed entry, not a rank, and sorting on it is meaningless.
    case("...and a BOOLEAN priority is excluded, because True is an int in Python",
         usable_models({"models": [M("boolp", True), M("ok3", 4)]}), ["ok3"])
    case("...and one with no slug is excluded, since there would be nothing to pass to --model",
         usable_models({"models": [{"priority": 1, "visibility": "list",
                                    "supported_in_api": True}, M("ok4", 9)]}), ["ok4"])
    case("an empty model list yields nothing, which the caller turns into a REFUSAL",
         usable_models({"models": []}), [])
    case("...and so does a payload with no `models` key at all", usable_models({}), [])

    # ── the REFUSAL must be actionable — the old one cost a whole review round ──────────
    case("the refusal NAMES the hidden near-misses, which are the whole clue",
         "gpt-5.5" in refusal_message(LIVE) and "codex-auto-review" in refusal_message(LIVE), True)
    case("...with their descriptions, so `Legacy` is visible to whoever reads it",
         "Legacy coding model." in refusal_message(LIVE), True)
    case("...and the client_version the server keyed its answer to",
         "0.142.5" in refusal_message(LIVE), True)
    case("...and the one command that changes any of it",
         "codex update" in refusal_message(LIVE), True)
    # ⛔ THE SENTENCE THAT WOULD HAVE PREVENTED THE WRONG TURN: a refusal here is NOT evidence
    # about Codex's availability, and the old message left that inference wide open.
    case("...and says explicitly that this is NOT evidence Codex is unavailable",
         "not evidence that Codex is unavailable" in refusal_message(LIVE), True)
    # a SECOND, distinct payload — so the message is shown to be about the data, not a constant
    case("a DIFFERENT cache yields a message naming ITS models, not the other one's",
         ("solo-model" in refusal_message({"client_version": "9.9.9", "models": [
             M("solo-model", 1, "hide", description="Something else.")]})
          and "gpt-5.5" not in refusal_message({"client_version": "9.9.9", "models": [
             M("solo-model", 1, "hide", description="Something else.")]})), True)
    case("...and an EMPTY cache still reports the count and the likely cause",
         ("0 model(s)" in refusal_message({"models": []})
          and "codex update" in refusal_message({"models": []})), True)

    print(f"\n{ok}/{ok + fail} self-test cases passed")
    return 1 if fail else 0


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--write-config", action="store_true",
                    help="sync the resolved model into ~/.codex/config.toml (managed block)")
    ap.add_argument("--self-test", action="store_true",
                    help="run the pure ordering cases; no cache or network needed")
    ap.add_argument("--list", action="store_true",
                    help="print ALL candidate slugs, most-frontier first (one per line)")
    args = ap.parse_args()

    # ⚠ BEFORE anything that touches the cache — the cases are pure and must run on a machine
    # with no `~/.codex` at all, which is what CI is.
    if args.self_test:
        sys.exit(_self_test())

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
