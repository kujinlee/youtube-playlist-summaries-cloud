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
  python3 scripts/codex-frontier-model.py --self-test   # 22 cases, pure, no network

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

    ⛔ `visibility == "list"` IS REQUIRED. THIS IS A SELECTION POLICY, NOT A CLAIM ABOUT VENDOR
    INTENT — and TWO successive drafts of this docstring got that wrong, each refuted by a
    different half of round 1.

    Draft 1 said `"hide"` means the vendor has WITHDRAWN the model. Codex (Medium 3) refuted it.
    Draft 2 then said `visibility` governs the picker and "NOT whether a model works" — and the
    Claude half refuted THAT by reading the source: `openai_models.rs` documents the field as
    *"Visibility of a model in the picker **or APIs**"*, and
    `app-server-protocol/schema/json/v2/ModelListParams.json` does not mention `visibility` at
    all. So the second draft cited a file that says nothing on the subject and overrode the one
    that does.

    ⛔ SO NO CLAIM IS MADE HERE ABOUT WHAT `visibility` GOVERNS. What is known: the field exists,
    it takes `list`/`hide`/`none`, and `supported_in_api` is a separate field. Anything further
    about vendor intent is inference, and this docstring has now been wrong twice by making it.

    THE POLICY STANDS ON ITS OWN GROUND AND NEEDS NO SUCH CLAIM: `list` is the narrower set, the
    vendor marks it, and narrowing is the conservative direction for a gate. ⚠ The cost is real
    and stated: this excludes API-supported hidden models — today `gpt-reserve`, `gpt-5.5`,
    `codex-auto-review` — and that exclusion is a CHOICE, not a deduction from anything the
    vendor says. Measured 2026-10-07: a FRESH fetch
    returned exactly two models, both hidden — `gpt-5.5`, whose own `description` is **"Legacy
    coding model."**, and `codex-auto-review`, which is `tool_mode: code_mode_only` and
    purpose-built for approval review. A loosened predicate would have picked the legacy one today
    and the special-purpose one the day it is withdrawn, REPORTING SUCCESS both times. That is the
    downgraded-gate-that-still-reports failure `docs/plugins.md` warns about above all others.

    ⚠ AN EARLIER DRAFT OF THIS FUNCTION DID LOOSEN IT, and the owner caught the mistake with one
    question: *"why do we have to use hidden model? why not use a listed model?"* The CLI was 18
    minor versions behind (0.142.5 against 0.160.1), and after `codex update` the same account was
    offered seven listed models where it had had none. ⚠ **THAT IS AN ASSOCIATION, NOT A PROVEN
    SERVER-SIDE CAUSE** — round 1 Codex Medium 3 again: the 0.142.5 cache no longer exists to
    compare against, so "the server keys its answer to `client_version`" is the best explanation
    available and not something measured here. What IS measured is the before/after pair itself.

    ⭐ CONFIRMED BY DOING IT, AND THE BEFORE HALF IS ON DISK. After `codex update` to 0.160.1
    the same account's cache went from 2 models (both hidden) to **10, SEVEN of them `list`**,
    topped by `gpt-6.1-sol` and `gpt-6-astra`. This function, unchanged and strict, resolves
    `gpt-6.1-sol`.

    ⚠ AN EARLIER DRAFT SAID THE 0.142.5 CACHE "no longer exists to compare against" AND THAT WAS
    FALSE — round 1 Claude HIGH. `~/.codex/models_cache.json.bak-2026-10-07` is a copy I took at
    03:20 before updating: `client_version: 0.142.5`, 2 models, both `hide`, both
    `supported_in_api`, fetched 10:20:48Z against the new cache's 10:31:31Z. **It contains no
    `gpt-6*` entry at all.** So the difference is in the SERVER'S RESPONSE, not in local
    filtering — which is STRONGER evidence than the "association" the same draft downgraded it
    to. I had the data and asserted I did not; the remaining honest gap is narrow, that
    `client_version` is the likeliest but not the only thing that changed in those eleven minutes.
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
    # ⚠ THE SAME FILTERS `usable_models` APPLIES, MINUS VISIBILITY — round 1 Codex Medium 2. The
    # first version omitted the priority requirements, so it labelled a model with a null or
    # boolean priority "hidden but otherwise usable" when the resolver would reject it even if
    # listed. A near-miss has to actually be a near-miss.
    near = sorted((m for m in models
                   if m.get("supported_in_api")
                   and isinstance(m.get("priority"), (int, float))
                   and not isinstance(m.get("priority"), bool)
                   and m.get("slug")
                   and m.get("visibility") != "list"),
                  key=lambda m: m["priority"])
    bits = [f"error: no LISTED, API-supported model in {CACHE}"]
    bits.append(f"  the cache holds {len(models)} model(s), fetched by client_version "
                f"{data.get('client_version') or '?'}")
    if near:
        bits.append("  hidden but otherwise usable: "
                    + ", ".join(f"{m['slug']} ({m.get('description') or 'no description'})"
                                for m in near))
        bits.append("  this tool's POLICY is to use only models marked `list`. That is a "
                    "deliberate narrowing, not a claim about what `hide` means.")
        # ⚠ CONDITIONAL — round 1 Codex Medium 2. The first version printed this whatever the
        # data said, so it diagnosed an outdated CLI even when the cache held no usable model for
        # some entirely different reason. It is only the likely cause when models ARE on offer
        # and none of them is listed.
        bits.append("  MOST LIKELY CAUSE: this Codex CLI is behind — models were offered but none "
                    "is listed. Run `codex update`, then re-run this.")
    elif models:
        bits.append("  ⚠ and NONE of them is a near-miss: every entry fails a requirement other "
                    "than visibility (API support, or a numeric non-boolean priority, or a slug). "
                    "Inspect the cache rather than assuming the CLI is stale.")
    else:
        bits.append("  the cache is EMPTY. Run `codex` once to populate it; if it stays empty, "
                    "check `codex login status`.")
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
    # ⛔ THE DIAGNOSIS IS CONDITIONAL NOW, AND THESE THREE CASES ARE WHAT MAKE IT SO — round 1
    # Codex Medium 2. An earlier version printed "this CLI is behind" whatever the data said, so
    # it diagnosed staleness over an empty cache and over models that fail for other reasons.
    case("an EMPTY cache says so, and does NOT blame the CLI version",
         ("0 model(s)" in refusal_message({"models": []})
          and "cache is EMPTY" in refusal_message({"models": []})
          and "codex update" not in refusal_message({"models": []})), True)
    _NOT_API = {"client_version": "1.2.3", "models": [M("x", 1, "list", api=False)]}
    case("...and models that fail for a reason OTHER than visibility are not blamed on it either",
         ("NONE of them is a near-miss" in refusal_message(_NOT_API)
          and "codex update" not in refusal_message(_NOT_API)), True)
    # ⚠ A MALFORMED PRIORITY IS NOT A NEAR-MISS — round 1 Codex Medium 2: the first near-miss
    # predicate omitted the priority requirements, so it advertised as "otherwise usable" a model
    # the resolver would reject even if it were listed.
    _BADP = {"client_version": "1.2.3", "models": [M("badpriority", None, "hide")]}
    case("...and a model with a malformed priority is NOT advertised as otherwise usable",
         "badpriority" not in refusal_message(_BADP), True)
    # ⚠ AND THE VENDOR-MEANING CLAIM IS GONE (round 1 Codex Medium 3): the message states the
    # POLICY and what `visibility` actually governs, and never asserts withdrawal.
    case("the message states a POLICY and never claims the vendor withdrew anything",
         ("POLICY" in refusal_message(LIVE)
          and "withdraw" not in refusal_message(LIVE).lower()), True)

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
