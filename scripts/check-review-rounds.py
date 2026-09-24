#!/usr/bin/env python3
"""A review round has TWO halves, or a written reason why it does not — a RATCHET on silent gaps.

    python3 scripts/check-review-rounds.py             # audit docs/reviews/
    python3 scripts/check-review-rounds.py --self-test # 64 cases

WHY THIS EXISTS
---------------
`docs/plugins.md` requires both halves of every review — `codex:rescue` AND
`superpowers:requesting-code-review` — and the memory `dual-review-halves-are-not-redundant`
records what skipping one costs: Codex-only rounds 2-4 cleared a live money guard that the skipped
Claude half caught in one pass.

Nothing enforced it. On 2026-08-24 the M4 plan went through two rounds with only the Codex half,
and the gap was visible **only** as a paragraph in a commit message — which is the "prose instead of
a script" shape `docs/dev-process.md` warns about. The absence of a reviewer looks exactly like the
presence of a clean one.

⚠ **IT MUST NOT BLOCK WHEN A REVIEWER GENUINELY CANNOT RUN** (user decision, 2026-08-25). Codex hits
usage limits, auth failures and HTTP 400s routinely, and `docs/plugins.md` already answers that case:
*"do not wait, pause the phase, or burn time retrying — immediately run a rigorous Claude adversarial
review in Codex's place … and note the Codex gap in the review doc."* That documented fallback
already produces both things this check wants — a real review, and a recorded reason. So the check
fires on **silence**, never on unavailability.

WHAT IT ASSERTS
---------------
For each (subject, round) it can parse:

  * two distinct reviewer halves            -> pass
  * one half + a GAP LINE in any of its files -> pass  (this is the Codex-down path)
  * one half, no gap line                   -> FAIL, unless the round is in KNOWN below

⛔ AND THE VERDICT HALF HAS AN ERA BOUNDARY — see the block above `VERDICT_DIRNAME`. Verdicts
written before 2026-09-23 named their review from the dispatching wrapper's SCRATCH `--out`, so
they join to nothing here; this check's silence about them is not evidence. It is reported on every
run rather than left to a commit message.

The gap line is deliberately `REVIEW GAP:` rather than "unavailable" — because the M4 case was not
unavailability, it was **not invoked**, and a marker that only admits one of those would have
tempted a false reason. The check forces a reason to be STATED; judging it is a human's job.

    REVIEW GAP: claude — not invoked; the missing half ran as r3

⚠ COVERAGE IS REPORTED, NOT IMPLIED. Review filenames use four different shapes; only two carry a
round number. The audit prints how many files it could not parse, because an instrument whose
success line claims more than its input covers is this project's most-repeated defect — see
ADR-0007's note on `check-vocabulary-collisions.py`, whose green line covered a schema it could
not see.

⚠ IT IS A RATCHET, and `check-ratchet-contract.py` discovers ratchets two ways: a CI step, or the
word "ratchet" in this docstring. The first draft said neither, so the contract check could not see
it — an instrument invisible to the instrument that audits instruments. Both are now true.

FAILS IF
--------
a (subject, round) outside KNOWN has one reviewer half and no gap line; or `docs/reviews/` is
missing (exit 2 — treat as NOT RUN).
"""
from __future__ import annotations

import collections
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
REVIEWS = ROOT / "docs" / "reviews"

# Two naming shapes are in use. Measured 2026-08-25 across 718 files: 108 are `-r<N>-<who>`, 60 are
# `-<who>-r<N>`, 192 name a reviewer with no round, and 358 match neither. Supporting one shape
# would have covered 15% of the directory while printing a green line about all of it.
SHAPES = (
    re.compile(r"^(?P<subject>.+)-r(?P<round>\d+)-(?P<who>codex|claude|coordinator)\.md$"),
    re.compile(r"^(?P<subject>.+)-(?P<who>codex|claude|coordinator)-r(?P<round>\d+)\.md$"),
)

# A coordinator file ADJUDICATES the two halves; it is not itself a half. Counting it would let a
# round pass with one reviewer and its own summary — the shape this check exists to catch.
HALVES = ("codex", "claude")

# Emphasis may wrap the marker on EITHER side — `**REVIEW GAP:** codex — …` is the natural way to
# write it in a review doc, and the first version only tolerated it on the left. Caught by the
# self-test, which is why the case uses the bolded form rather than the bare one.
GAP = re.compile(
    r"^[*_>#\s-]*REVIEW GAP:[*_\s]*(codex|claude)\b[*_\s]*[—–-][*_\s]*(\S.*?)[*_\s]*$",
    re.M | re.I)

# Rounds that predate the check. A NAME list, not a count: swapping one violation for another must
# not pass, and a stale entry announces itself the moment its files are renamed or completed.
# Measured 2026-08-25 — 20 of 86 parseable rounds, which is the finding, not the exception:
# `plan-serve-bounding` ran EIGHT single-reviewer rounds. This was never a one-off.
#
# ⟳ The first version of this list had 12 entries, built from a terminal display truncated at
# `[:12]`, and the check caught the other 8 on its first real run. Same instrument failure as the
# `ls | head -20` that caused the anchor work (ADR-0010) two days ago — a list read off a truncated
# view is a claim about the view, not about the set.
KNOWN: set[tuple[str, int]] = {
    ("b4-share-tolerate-skew", 1),
    ("backlog-37-sidebar-refresh", 2), ("backlog-37-sidebar-refresh", 3),
    ("backlog-37-sidebar-refresh", 4),
    ("m3-1-cloud-e2e", 2), ("m3-1-cloud-e2e", 3),
    ("plan-serve-bounding", 1), ("plan-serve-bounding", 2), ("plan-serve-bounding", 3),
    ("plan-serve-bounding", 4), ("plan-serve-bounding", 5), ("plan-serve-bounding", 6),
    ("plan-serve-bounding", 7), ("plan-serve-bounding", 8),
    ("spec-proven-absence", 1),
    ("spec-serve-deadline", 1), ("spec-serve-deadline", 2), ("spec-serve-deadline", 3),
}


def parse(name: str) -> tuple[str, int, str] | None:
    """(subject, round, who) or None. PURE."""
    for shape in SHAPES:
        if m := shape.match(name):
            return m.group("subject"), int(m.group("round")), m.group("who")
    return None


def has_gap_line(text: str) -> str | None:
    """The stated reason a half is missing, or None. PURE."""
    m = GAP.search(text)
    return f"{m.group(1)}: {m.group(2).strip()}" if m else None


# ── backlog #68 (d): THIS IS THE CONSUMER THAT IS NOT THE CALLER ───────────────────────────────
# `scripts/codex-review.py` now writes a verdict per run into `docs/reviews/verdicts/`, because its
# exit code has a single consumer and no memory: measured 2026-08-28, a caller wrapped the run as
# `… ; echo "WRAPPER_RC=$?"` and reported the ECHO's status, so `WRAPPER_RC=1` sat unread while the
# round was treated as reviewed.
#
# ⚠ WRITING THE VERDICT DOWN FIXES NOTHING BY ITSELF. A file the caller ignores is an exit code the
# caller ignores with extra steps. The mechanism is that THIS check reads it, in CI, where the
# caller cannot intervene. What it catches is the exact round-3 shape: the gate did not run, and an
# artifact bearing its name was filed anyway.
#
# ⚠ STATED LIMIT, NOT PAPERED OVER: this reads COMMITTED verdicts, so someone who deletes one
# before committing evades it entirely. That is deliberate scope, not an oversight. The failure
# being fixed was an ACCIDENT — a `$?` that read the wrong command's status — and an accident
# cannot delete a file. A determined caller can still defeat this; a distracted one cannot, and
# every occurrence so far has been the distracted kind. Claiming more would be the "green check
# over the wrong subject" this project keeps measuring.
#
# ⛔⛔ THE ERA BOUNDARY — A PRE-CUTOVER VERDICT CANNOT BE TRUSTED TO NAME A FILED REVIEW, AND THIS
# CHECK'S SILENCE OVER THOSE MEANS NOTHING (backlog #176).
# Before the cutover, `codex-review.py` built the `review` field below from the BASENAME OF ITS
# `--out`, which is a scratch path the documented call shape puts outside the repository as
# `--out "$(mktemp -d)/r.md"`. So the join key of every such run is the string `r.md`, which is
# not the name of anything in `docs/reviews/` and therefore matches nothing here. Driven through
# `verdict_problems` below, the identical failed gate reports **0** problems under the scratch
# name against **1** under the review's real name. FROM the cutover the identity is supplied by
# the caller (`--review-id`) and the wrapper files the review itself, so the two names are the
# same string by construction.
#
# ⛔ **IT IS A NUMBER IN THE DATA NOW, NOT A DATE IN A COMMENT (r1 M2).** The caveat used to be
# this paragraph plus one `print`, with nothing in any record marking which era it belonged to:
# deleting both went green everywhere, and `VERDICT_SCHEMA` sat at `2` on both sides of the
# boundary, so 99 pre-cutover records were byte-indistinguishable from post-cutover ones. The
# producer now stamps `schema: 3` — the field whose MEANING changed is exactly what a schema
# version is for — and this check reads that number rather than trusting prose. `TRUSTED_SCHEMA`
# is the consumer's OWN threshold and is deliberately not imported from the producer: a later
# bump to 4 must not silently stop trusting 3, and the import would be circular anyway
# (`codex-review.py` imports this module for the filing grammar).
#
# ⚠ THE PRE-CUTOVER RECORDS ARE LEFT UNTOUCHED, DELIBERATELY (user decision). They are committed
# testimony about runs nobody can re-observe, and rewriting their `review` field would be
# inventing a name for a file that may never have existed — the same ground on which
# `read_verdicts` below refuses to back-fill history.
#
# ⚠ AND THE COUNTS ARE DERIVED, NEVER QUOTED (r1 M3). This paragraph used to state *"183 verdicts,
# 58 (32%)"*; the true figure was **184** at both base and head, it was wrong when it was written,
# and it was copied into three further places rather than re-derived. The denominator moves every
# run, so any frozen copy is stale by construction — `main` prints both counts live instead.
VERDICT_DIRNAME = "verdicts"
# The first `schema` whose `review` field is the review's DURABLE filename. Below it the join key
# is a scratch basename and a silence here is not evidence. A record with no `schema` at all is
# older still, and reads as 0.
TRUSTED_SCHEMA = 3


def schema_of(rec: dict) -> "int | None":
    """The record's schema version as an int, or None when the field is not a version. PURE.

    ⚠ **r2 Claude half, L1 — ONE RULE, THREE CALL SITES.** `(rec.get("schema") or 0)` was written
    three times, the third by the commit whose stated purpose was that malformed testimony must be
    refused LOUDLY: a record carrying `{"schema": "3"}` raised an unhandled `TypeError` out of
    `read_verdicts`, and `main` reports an uncaught exception as rc 1 (contradictions were FOUND)
    rather than rc 2 (this check CANNOT RUN) — inverting the one distinction this guard maintains
    deliberately, and contradicting `read_verdicts`'s own docstring one line above the raise.

    ⚠ AN ABSENT FIELD IS 0, NOT None. A record written before the field existed belongs to the
    oldest era, which is a readable answer; only a field that is PRESENT and is not a version is
    unreadable. And a `bool` is rejected on its own line because `True` IS an `int` in Python —
    `isinstance(True, int)` is True — and a schema version is not a flag.

    ⛔ **AND A PRESENT VERSION MUST BE POSITIVE — r2 Codex half, High.** The first version of this
    helper rejected bools and non-ints and then returned whatever integer it found, so
    `{"schema": -1}` was accepted AS A VERSION, compared as `-1 < TRUSTED_SCHEMA`, and read as
    pre-cutover. Measured on the delivered code: a record with `schema: -1`, `gate_ran: true` and a
    `review` naming a file that does not exist produced `bad=0`, `pre_cutover=1`, `problems=0` — the
    exact join contradiction this guard exists to report, silenced by a malformed field it had just
    promised to refuse. **That is the fourth shape in this slice by which malformed testimony
    switched the check off** (`refused` truthy, `gate_ran` truthy, `schema` non-int, now `schema`
    negative), which is why the rule is stated as a RANGE rather than patched value by value.
    ⚠ An explicit `0` is refused too, deliberately: 0 is this function's answer for ABSENT, so a
    record carrying it would be indistinguishable from one written before the field existed. The
    sentinel must not be expressible as a real value.
    """
    if "schema" not in rec:
        return 0
    v = rec["schema"]
    if isinstance(v, bool) or not isinstance(v, int):
        return None
    if v < 1:
        return None
    return v


def era_split(records: "list[tuple[str, dict]]") -> "dict[str, int]":
    """How many records this check can MEAN anything about, derived. PURE.

    ⛔ r1 M3: the alternative is a number typed into a comment, and the one that was there was
    wrong at the denominator from the day it was written. This is computed from the records in
    hand, so the caveat printed below cannot go stale. `unnamed` counts the post-cutover records
    naming a review that is not on disk — reported rather than left to be inferred from silence.

    ⛔ **`is True`, NOT TRUTHINESS — r2 Claude half, M1, AND THE SAME LINE AS `verdict_problems`.**
    The r2 Codex High was fixed at ONE of the three sites reading `refused`, and this is the one
    whose whole job is that the caveat printed to the reader is DERIVED rather than guessed.
    Measured on the delivered functions: a record carrying `"refused": "false"` was counted HERE as
    a refusal and skipped THERE as pre-cutover — one file, two partitions, from the function that
    exists so the partition is not a guess. `read_verdicts` now refuses a non-bool outright, so no
    such record reaches either site; this is the CLASS being closed, not a reachable mis-count.
    """
    out = {"total": len(records), "refused": 0, "pre_cutover": 0, "checked": 0}
    for _src, rec in records:
        if rec.get("refused") is True:
            out["refused"] += 1
        elif (schema_of(rec) or 0) < TRUSTED_SCHEMA:
            out["pre_cutover"] += 1
        else:
            out["checked"] += 1
    return out


def verdict_problems(records: "list[tuple[str, dict]]", review_names: "set[str]") -> list[str]:
    """One problem per verdict that contradicts what is on disk. PURE.

    `gate_ran` is READ, never re-derived from `exit_code`. Deriving it here would be a second
    implementation of the wrapper's rule, and the two would drift — this project has measured that.

    ⛔ **A REFUSAL IS NOT TESTIMONY ABOUT A GATE (r1 B1).** `refused: true` marks a run that
    declined to start because the artifact was already there. It carries `gate_ran: false` because
    that is true OF THE RUN, and it names the review because that is what it is about — but the
    sentence this check makes out of those two facts, *a filed review with no gate behind it*, is
    the opposite of what a refusal means: the review exists BECAUSE an earlier run produced it.
    Read without this clause, every re-dispatch would accuse a real review. The refusal's own
    testimony also lives at a different path (`codex-review.refusal_verdict_path`) so it cannot
    overwrite the record it is about; that is the write-side half of the same finding, and it is
    deliberately a different mechanism — keying this clause on the FILENAME instead would be a
    second implementation of the naming rule.

    ⛔ **AND BOTH DIRECTIONS OF THE JOIN ARE READ, NOT ONE (r1 M1).** `gate_ran: true` naming a
    review that is NOT filed is the mirror contradiction, and it is the one backlog #176 was
    convened over: a coordinator citing a verdict for a round whose half never reached
    `docs/reviews/`. The wrapper produces exactly that state on its `exit 3` path — a real review
    captured at `--out`, the promotion refused — and prints how to resolve it. It was `continue`d
    before this change because under scratch naming the key matched nothing, so it would have
    fired on almost everything; the era gate below is what makes it safe to read now.

    ⚠ THE ERA GATE IS A NUMBER IN THE RECORD, NOT A DATE. Below `TRUSTED_SCHEMA` the `review`
    field is the basename of a scratch path and neither direction means anything. Measured at the
    cutover: 53 of the pre-cutover records are `gate_ran: true` with the named review not on disk,
    and every one of them is an artefact of the naming, not a missing review.
    """
    out = []
    for src, rec in records:
        # ⛔ **`is True`, NOT TRUTHINESS — r2 Codex half, High.** `rec.get("refused")` accepted any
        # truthy value, so a CURRENT-ERA record carrying `"refused": "false"` — a string, which is
        # truthy — was silently skipped in BOTH join directions. Measured: `"false"`, `"no"` and `1`
        # all suppressed the check; only `0`, `False` and absence reported. The field was added to
        # stop the read side falsely accusing a genuine review (r1 B1); truthiness turned it into a
        # way for malformed testimony to switch the whole CI join off without being reported as
        # unreadable. `read_verdicts` now refuses a non-bool `refused` outright, so the two form
        # one rule: the value must BE a boolean, and it must be True.
        #   ⟳ **r2 CLAUDE HALF, M1 — THIS COMMENT SAID "two halves" AND THERE ARE THREE SITES.**
        #   `era_split` reads the same field and was left on truthiness, so one record was counted
        #   there as a refusal and skipped here as pre-cutover. A comment asserting a completeness
        #   the file does not have is this branch's signature defect; the third site is fixed and
        #   the sentence is corrected in place rather than annotated.
        if rec.get("refused") is True:
            continue
        if (schema_of(rec) or 0) < TRUSTED_SCHEMA:
            continue
        review = rec.get("review") or "(unnamed)"
        # ⛔ **`is not True`, FOR THE SAME REASON, ON THE FIELD THE WHOLE JOIN TURNS ON — r2 Claude
        # half, H1.** The truthiness fix above was applied to `refused` and not to `gate_ran` five
        # lines below it, which `verdict_record`'s docstring calls *the load-bearing field*.
        # Measured on the delivered function against a FILED review: `gate_ran` of `False`, `0` and
        # `None` were each reported, while `"false"`, `"no"` and `"0"` — all truthy strings — read
        # as *the gate RAN* and silenced the r1 B1 direction entirely, without being reported as
        # unreadable, because the refusal in `read_verdicts` named only `refused`. Identical shape,
        # one field over; closing it at one site is what produced this finding.
        if rec.get("gate_ran") is not True:
            if review in review_names:
                out.append(
                    f"{src}: the Codex gate did NOT run "
                    f"({rec.get('reason', 'no reason recorded')}), "
                    f"yet `{review}` is filed in docs/reviews/. A failed gate must not leave an "
                    f"artifact that reads as a completed one — delete it, or if it is a Claude "
                    f"review, name it as one and record a `REVIEW GAP:` line")
        elif review not in review_names:
            out.append(
                f"{src}: the Codex gate RAN ({rec.get('reason', 'no reason recorded')}), but "
                f"`{review}` is NOT filed in docs/reviews/. Testimony that a review exists under "
                f"a name nothing on disk carries is the false green this join was built to close "
                f"— file the capture under that name (codex-review.py exits 3 and prints where it "
                f"left it), or if the review is genuinely gone, remove its testimony too")
    return out


def read_verdicts(directory: pathlib.Path) -> "tuple[list[tuple[str, dict]], list[str]]":
    """(records, unreadable). A malformed verdict is a CANNOT-RUN, never a silent skip.

    An absent directory is fine and returns nothing: verdicts only exist from the moment the
    wrapper started writing them, and back-filling history would be inventing testimony.
    """
    records, bad = [], []
    if not directory.is_dir():
        return records, bad
    for p in sorted(directory.glob("*.json")):
        try:
            rec = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            bad.append(f"{p.name}: unreadable ({exc})")
            continue
        if not isinstance(rec, dict) or "gate_ran" not in rec:
            bad.append(f"{p.name}: no `gate_ran` field — cannot tell whether the gate ran")
            continue
        # ⚠ A malformed `schema` is a CANNOT RUN, not a TRACEBACK (r2 Claude half, L1). The era
        # gate is an arithmetic comparison, so a non-numeric version raised out of this function
        # and `main` reported it as rc 1 — *contradictions were found* — which is the opposite of
        # what a record nobody can read means. `schema_of` owns the rule; it is asked here and
        # merely READ at the two pure sites, so there is one answer to what a version is.
        if schema_of(rec) is None:
            bad.append(f"{p.name}: `schema` is {type(rec.get('schema')).__name__}, not a version "
                       f"number — the era gate cannot say whether this record can be judged")
            continue
        # ⚠ A malformed `gate_ran` is a CANNOT RUN too (r2 Claude half, H1), and it is held to a
        # boolean at EVERY era rather than only above the cutover. Measured over the corpus at this
        # commit: 185 of 185 records carry a real bool (179 True, 5 False pre-cutover, 1 True
        # after), so unlike `refused` — which the pre-cutover era predates and carries `None`
        # throughout — there is no history to exempt. The field is already REQUIRED present two
        # lines up; requiring it to be a boolean is the same clause finished.
        #   ⚠ `.get`, NOT `rec["gate_ran"]`, EVEN THOUGH THE PRESENCE CHECK IS TWO LINES UP. The
        #   mutation that deletes that check is in the manifest, and a subscript here would turn
        #   its kill into a KeyError traceback — a suite that CRASHES prints no `[FAIL] <case>`
        #   line, which this harness reports as unattributable rather than as a kill. Sibling of
        #   the `_first()` rule in the suite below.
        _gr = rec.get("gate_ran")
        if not isinstance(_gr, bool):
            bad.append(f"{p.name}: `gate_ran` is {type(_gr).__name__}, not a boolean — a truthy "
                       f"non-bool reads as `the gate ran` and switches the failed-gate direction "
                       f"off for that record")
            continue
        # ⚠ A malformed `refused` is a CANNOT RUN, never a quiet skip (r2 Codex High). Only records
        # at or above the trusted schema are held to it: the pre-cutover corpus predates the field
        # and carries `None` throughout (measured: 184 records, all `refused=None`), so demanding a
        # boolean there would fail 184 files about runs nobody can re-observe.
        _ref = rec.get("refused")
        if (schema_of(rec) or 0) >= TRUSTED_SCHEMA and _ref is not None and not isinstance(_ref, bool):
            bad.append(f"{p.name}: `refused` is {type(_ref).__name__}, not a boolean — a truthy "
                       f"non-bool would switch this check off for that record")
            continue
        records.append((p.name, rec))
    return records, bad


# ── WHERE A REVIEW HALF MAY LIVE — two layouts, and the reason is backlog #92, not taste ──────
# `scripts/codex-review.py` watches the TOP LEVEL of docs/reviews/ NON-RECURSIVELY so it can catch
# an agent that guesses its way into the artifact root; that is the round-3 failure and the
# detector is worth keeping. But the documented dual-review workflow also wrote BOTH halves there,
# so every run whose halves overlapped accused the agent falsely — recorded in four review docs —
# and on the failure path the wrapper MOVED a concurrent half out of the tree entirely (measured
# 2026-09-04). Halves now land in a per-writer SUBDIRECTORY, which the non-recursive snapshot
# cannot see. That makes the two mechanisms consistent instead of contradictory: nothing legitimate
# is written to the top level DURING a run, so anything appearing there really is an intrusion.
# The ~700 historical files stay flat and are still audited — this reads both layouts.
HALF_DIRS = ("codex", "claude", "coordinator")


def review_files(reviews: pathlib.Path) -> tuple[list[pathlib.Path], list[str]]:
    """Every review half on disk: the flat layout AND one level of per-writer subdirectories.

    ONE level, and `verdicts/` is excluded because it holds JSON testimony, not reviews.

    Returns `(paths, problems)`. A basename appearing in TWO places is a problem, never a silent
    pick: `rounds[key][who] = p` would keep whichever it saw last, so a duplicate would shrink
    coverage while the round still looked complete — a collision that overwrites cannot be found
    by counting what survived it.
    """
    flat = sorted(reviews.glob("*.md"))
    nested: list[pathlib.Path] = []
    for d in sorted(p for p in reviews.iterdir() if p.is_dir()):
        if d.name == VERDICT_DIRNAME:
            continue
        nested.extend(sorted(d.glob("*.md")))

    seen: dict[str, pathlib.Path] = {}
    problems: list[str] = []
    for p in flat + nested:
        if p.name in seen:
            problems.append(
                f"{p.name}: filed in BOTH `{seen[p.name].parent.name}/` and `{p.parent.name}/` — "
                f"two files cannot be the same review half, and pairing would keep only one"
            )
            continue
        seen[p.name] = p
    return list(seen.values()), problems


def audit(reviews: pathlib.Path, known: set[tuple[str, int]] = KNOWN) -> tuple[list[str], dict]:
    """(problems, stats). Reads `reviews`; the parsing above is pure."""
    rounds: dict[tuple[str, int], dict[str, pathlib.Path]] = collections.defaultdict(dict)
    unparsed = 0
    paths, path_problems = review_files(reviews)
    for p in paths:
        got = parse(p.name)
        if got is None:
            unparsed += 1
            continue
        subject, rnd, who = got
        rounds[(subject, rnd)][who] = p

    problems, exempt_used = list(path_problems), set()
    for key, files in sorted(rounds.items()):
        present = [w for w in HALVES if w in files]
        if len(present) >= 2:
            continue
        if any(has_gap_line(p.read_text(errors="replace")) for p in files.values()):
            continue
        if key in known:
            exempt_used.add(key)
            continue
        missing = [w for w in HALVES if w not in files] or ["both"]
        problems.append(
            f"{key[0]} round {key[1]}: only {'+'.join(present) or 'nothing'} — "
            f"{'/'.join(missing)} neither ran nor recorded a `REVIEW GAP:` line"
        )

    for stale in sorted(known - exempt_used):
        problems.append(
            f"KNOWN entry `{stale[0]}` round {stale[1]} is no longer a violation — remove it, "
            f"or the exemption outlives what it excused"
        )

    # The verdict half. `review_names` is what is ACTUALLY on disk, so the contradiction the
    # check reports is between two observations, never between an observation and an assumption.
    vrecs, vbad = read_verdicts(reviews / VERDICT_DIRNAME)
    # Both layouts, or a verdict naming a half filed in `claude/` would read as testimony about a
    # review that does not exist — the check contradicting itself over a file it can plainly see.
    review_names = {p.name for p in paths}
    problems.extend(verdict_problems(vrecs, review_names))

    return problems, {"rounds": len(rounds), "unparsed": unparsed, "exempt": len(exempt_used),
                      "verdicts": len(vrecs), "verdicts_bad": vbad, "era": era_split(vrecs)}


# ---------------------------------------------------------------- self-test
def self_test() -> int:
    import tempfile
    cases = failures = 0

    def check(label: str, got: bool, want: bool) -> None:
        nonlocal cases, failures
        cases += 1
        ok = got == want
        print("  ✓ " + label if ok else f"  [FAIL] {label}: got {got!r} want {want!r}")
        failures += 0 if ok else 1

    check("shape A parsed", parse("plan-x-r2-codex.md") == ("plan-x", 2, "codex"), True)
    check("shape B parsed", parse("plan-x-claude-r2.md") == ("plan-x", 2, "claude"), True)
    check("no round number -> unparsed", parse("plan-x-codex.md") is None, True)
    check("unrelated file -> unparsed", parse("retrospective.md") is None, True)
    check("gap line found", has_gap_line("**REVIEW GAP:** codex — usage limit") is not None, True)
    check("gap line needs a reason", has_gap_line("REVIEW GAP: codex —") is None, True)
    check("prose mentioning a gap is not a gap line",
          has_gap_line("there was a review gap: codex was slow") is None, True)

    with tempfile.TemporaryDirectory() as td:
        def tree(files: dict[str, str]) -> pathlib.Path:
            d = pathlib.Path(td) / f"t{len(list(pathlib.Path(td).iterdir()))}"
            d.mkdir()
            for n, body in files.items():
                # A key may carry ONE subdirectory (`claude/p-r1-claude.md`), so the cases can
                # build the per-writer layout backlog #92 introduced, not only the flat one.
                (d / n).parent.mkdir(parents=True, exist_ok=True)
                (d / n).write_text(body)
            return d

        d = tree({"p-r1-codex.md": "x", "p-r1-claude.md": "y"})
        check("both halves pass", audit(d, set())[0] == [], True)
        # ⟳ 2026-09-08 — MEASURED: the case above passes when the FLAT scan is deleted, and the
        # nested one below passes when the NESTED scan is deleted. Both assert an ABSENCE of
        # problems, and reading no files produces exactly that absence: "nothing went wrong" is
        # satisfied by "nothing happened". Assert the round was SEEN, or the pairing is unguarded.
        check("…and the flat pair was actually SEEN, not merely un-complained-about",
              audit(d, set())[1]["rounds"], 1)

        d = tree({"p-r1-codex.md": "x"})
        check("solo half FAILS", len(audit(d, set())[0]) == 1, True)

        d = tree({"p-r1-codex.md": "REVIEW GAP: claude — not invoked; ran as r3"})
        check("solo half + gap line passes (the Codex-down path)", audit(d, set())[0] == [], True)

        d = tree({"p-r1-codex.md": "x"})
        check("KNOWN exempts it", audit(d, {("p", 1)})[0] == [], True)

        d = tree({"p-r1-codex.md": "x", "p-r1-claude.md": "y"})
        check("a KNOWN entry that is no longer violating is reported",
              len(audit(d, {("p", 1)})[0]) == 1, True)

        d = tree({"p-r1-codex.md": "x", "p-r1-coordinator.md": "adjudication"})
        check("coordinator is NOT a second half", len(audit(d, set())[0]) == 1, True)

        d = tree({"p-r1-codex.md": "x", "p-r1-claude.md": "y", "notes.md": "z"})
        check("unparsed files are counted, not judged", audit(d, set())[1]["unparsed"] == 1, True)

        # ── backlog #92: the per-writer layout ──
        # THE POINT OF THE WHOLE CHANGE. If this case fails, halves have become invisible to CI
        # and every round reads as half-missing — the loud failure, but still worth naming.
        d = tree({"codex/p-r1-codex.md": "x", "claude/p-r1-claude.md": "y"})
        check("halves in per-writer subdirectories pair normally", audit(d, set())[0] == [], True)
        check("…and the nested pair was actually SEEN, not merely un-complained-about",
              audit(d, set())[1]["rounds"], 1)

        # MIXED, because the migration is not atomic: ~700 files stay flat while new halves nest.
        d = tree({"p-r1-codex.md": "x", "claude/p-r1-claude.md": "y"})
        check("a nested half pairs with a flat one", audit(d, set())[0] == [], True)

        # A subdirectory must not RESCUE a solo half — the gate still wants two writers.
        d = tree({"claude/p-r1-claude.md": "y"})
        check("a solo half in a subdirectory still FAILS", len(audit(d, set())[0]) == 1, True)

        # ⛔ THE COLLISION, asserted rather than assumed. `rounds[key][who] = p` keeps the LAST
        # write, so without this the duplicate would vanish and the round would look complete.
        d = tree({"p-r1-claude.md": "y", "claude/p-r1-claude.md": "y2", "p-r1-codex.md": "x"})
        probs = audit(d, set())[0]
        check("the same half filed in two places is REPORTED, not silently deduped",
              any("filed in BOTH" in s for s in probs), True)

        # `verdicts/` holds JSON testimony; a stray .md there is not a review half. Without the
        # exclusion it would parse as one and invent a round.
        d = tree({"p-r1-codex.md": "x", "p-r1-claude.md": "y", "verdicts/q-r9-claude.md": "z"})
        check("verdicts/ is not scanned for review halves", audit(d, set())[0] == [], True)

    # ── backlog #68 (d): the verdict half ──
    # THE ROUND-3 SHAPE, as a case: the gate did not run and an artifact bearing its name is filed.
    # That is what actually happened — four models each overwrote a committed review while the
    # wrapper wrote nothing — and no check could see it, because the only signal was an exit code
    # the caller had already discarded.
    # ⚠ EVERY FIXTURE CARRIES `schema` FROM r1 M2 ON. The era gate reads a number in the record,
    # so a fixture without one is PRE-CUTOVER and would be skipped — a case that passes because
    # nothing was examined is the "test that cannot fail" shape this repo keeps paying for.
    _filed = {"plan-x-r3-codex.md"}
    _did_not_run = ("plan-x-r3-codex.verdict.json",
                    {"schema": TRUSTED_SCHEMA, "gate_ran": False,
                     "review": "plan-x-r3-codex.md", "reason": "no candidate"})
    _ran = ("plan-x-r3-codex.verdict.json",
            {"schema": TRUSTED_SCHEMA, "gate_ran": True,
             "review": "plan-x-r3-codex.md", "reason": "ok"})
    # ⚠ NEVER `[0]` ON A LIST A MUTATION CAN EMPTY. Measured while writing r1 M1's entry: the
    # unguarded form raised IndexError, so the suite CRASHED after its first red case and printed
    # no further `[FAIL] <case>` line — which the harness reports as unattributable, not as a kill.
    # A case must FAIL readably; this is the sibling of the `.get`-not-`[...]` rule next door.
    def _first(problems: list[str]) -> str:
        return problems[0] if problems else ""

    check("a failed gate with its artifact filed anyway is caught",
          len(verdict_problems([_did_not_run], _filed)) == 1, True)
    check("…and the message names the review",
          "plan-x-r3-codex.md" in _first(verdict_problems([_did_not_run], _filed)), True)
    check("a failed gate that left NO artifact is not a contradiction",
          verdict_problems([_did_not_run], set()) == [], True)
    check("a gate that RAN is never a problem", verdict_problems([_ran], _filed) == [], True)
    # ⛔ **`TRUSTED_SCHEMA` HAD NO FALSIFIER, AND THAT IS THE ONE SHAPE THIS REPO SAYS IS WORSE THAN
    # NO GUARD AT ALL.** Found by the coordinator before round 2, by perturbing it: `3 -> 99` passed
    # **40/40**. That mutant reclassifies EVERY record as pre-cutover, so `era_split` reports the
    # whole corpus as unmeanable and every clause below it goes vacuous — the check keeps printing
    # and stops checking. ⚠ The literal 3 is the OUTSIDE OBSERVER; writing `TRUSTED_SCHEMA` here
    # would agree with whatever value the constant took, which is exactly the hole being closed.
    # ── r2 Codex half, High: `refused` must BE a boolean, and only True suppresses ──────────────
    # ⚠ THE TRUTHY VALUES ARE THE CASE. Asserting only `True` suppresses and `False` does not would
    # pass under the defect, because both are bools; what defeated the join was a truthy NON-bool.
    _rf = lambda v: {"schema": TRUSTED_SCHEMA, "gate_ran": False, "review": "x-r1-codex.md",
                     "reason": "r", "refused": v}
    _filed_x = {"x-r1-codex.md"}
    check("a genuine refusal (refused is True) is skipped, so the read side cannot accuse the "
          "review it protected", verdict_problems([("v.json", _rf(True))], _filed_x) == [], True)
    check("…but a TRUTHY NON-BOOL `refused` does NOT suppress the check — the string \"false\" is "
          "truthy, and accepting it let malformed testimony switch the CI join off",
          len(verdict_problems([("v.json", _rf("false"))], _filed_x)), 1)
    check("…at a second distinct truthy non-bool, so this is not a special case for one value",
          len(verdict_problems([("v.json", _rf(1))], _filed_x)), 1)
    # ── r2 Claude half, H1: THE SAME RULE ON `gate_ran`, WHICH IS THE FIELD THE JOIN TURNS ON ──
    # ⛔ THE FIX WITHOUT THESE CASES IS NOT A FIX. Measured by the reviewer: hardening `:245` to
    # `is not True` in a staged copy left the suite at 49/49 — no case could tell the defect from
    # its repair, which is this repo's *a test that cannot fail* shape applied to a High's own fix.
    # ⚠ AND THE TRUTHY VALUES ARE THE CASE, for the reason recorded above: `True`/`False` are both
    # bools and pass under the defect. What silenced the failed-gate direction was a truthy STRING.
    _gr = lambda v: {"schema": TRUSTED_SCHEMA, "gate_ran": v, "review": "x-r1-codex.md",
                     "reason": "r"}
    check("a filed review whose verdict says the gate did NOT run is reported — the r1 B1 "
          "direction, and the baseline the truthy cases below are measured against",
          len(verdict_problems([("v.json", _gr(False))], _filed_x)), 1)
    check("…and a TRUTHY NON-BOOL `gate_ran` does NOT read as `the gate ran` — the string "
          "\"false\" is truthy, and accepting it silenced that direction entirely",
          len(verdict_problems([("v.json", _gr("false"))], _filed_x)), 1)
    check("…at a second distinct truthy non-bool, so this is not a special case for one value "
          "either", len(verdict_problems([("v.json", _gr("no"))], _filed_x)), 1)
    check("…while a real `gate_ran: True` beside its filed review is still silent, so reading it "
          "by identity did not turn the honest case into a finding",
          verdict_problems([("v.json", _gr(True))], _filed_x), [])
    with tempfile.TemporaryDirectory() as _td:
        _vd = pathlib.Path(_td)
        (_vd / "bad.json").write_text(json.dumps(_rf("false")), encoding="utf-8")
        _recs, _bad = read_verdicts(_vd)
        check("a non-bool `refused` in the trusted era is a CANNOT RUN, not a quiet skip",
              (len(_recs), len(_bad)), (0, 1))
        check("…and the refusal SAYS what was wrong, so a reader is not left guessing",
              "not a boolean" in (_bad[0] if _bad else ""), True)
        # ⚠ The pre-cutover corpus predates the field and carries None throughout — measured, 184
        # records. Holding it to a boolean would fail 184 files about runs nobody can re-observe.
        (_vd / "old.json").write_text(
            json.dumps({"schema": 2, "gate_ran": True, "review": "y.md"}), encoding="utf-8")
        _recs2, _bad2 = read_verdicts(_vd)
        check("…while a PRE-CUTOVER record with no `refused` at all is still read, not condemned",
              any(n == "old.json" for n, _ in _recs2), True)
    # ── r2 Claude half, H1 + L1: THE READ SIDE OF THE SAME TWO FIELDS ──────────────────────────
    # ⚠ `gate_ran` is held to a boolean at EVERY era, not only above the cutover, and that is a
    # MEASUREMENT rather than a preference: all 185 records in the corpus carry a real bool. The
    # `refused` rule needs its era gate because 184 of them predate the field entirely.
    with tempfile.TemporaryDirectory() as _td2:
        _vd2 = pathlib.Path(_td2)
        (_vd2 / "gr.json").write_text(
            json.dumps({"schema": TRUSTED_SCHEMA, "gate_ran": "false", "review": "y.md"}),
            encoding="utf-8")
        _r3, _b3 = read_verdicts(_vd2)
        check("a non-bool `gate_ran` is a CANNOT RUN, not a record read as `the gate ran`",
              (len(_r3), len(_b3)), (0, 1))
        check("…and the refusal names the FIELD, so a reader is not sent to the wrong one",
              "`gate_ran` is str" in (_b3[0] if _b3 else ""), True)
        (_vd2 / "gr.json").unlink()
        # ⛔ L1: the docstring promises a malformed verdict is a CANNOT-RUN. `{"schema": "3"}` met
        # an arithmetic comparison and raised, and `main` reports an uncaught exception as rc 1 —
        # *contradictions found* — which is the one distinction this guard exists to keep.
        (_vd2 / "sch.json").write_text(
            json.dumps({"schema": "3", "gate_ran": True, "review": "y.md"}), encoding="utf-8")
        _r4, _b4 = read_verdicts(_vd2)
        check("a NON-NUMERIC `schema` is a CANNOT RUN too, not a TypeError out of the era gate",
              (len(_r4), len(_b4)), (0, 1))
        (_vd2 / "sch.json").unlink()
        # ⚠ A SECOND, DISTINCT malformed shape: `True` IS an `int` in Python, so a rule written as
        # `isinstance(v, int)` alone would read a flag as version 1 and judge the record.
        (_vd2 / "boolsch.json").write_text(
            json.dumps({"schema": True, "gate_ran": True, "review": "y.md"}), encoding="utf-8")
        _r5, _b5 = read_verdicts(_vd2)
        check("…and so is a BOOLEAN schema, which `isinstance(v, int)` alone would call version 1",
              (len(_r5), len(_b5)), (0, 1))
        (_vd2 / "boolsch.json").unlink()
        # …and the honest shapes still pass, so the three refusals above are not simply a closed
        # door: a record with no `schema` at all is the oldest era, which is a readable answer.
        (_vd2 / "ok.json").write_text(
            json.dumps({"gate_ran": False, "review": "y.md"}), encoding="utf-8")
        _r6, _b6 = read_verdicts(_vd2)
        check("…while a record with NO `schema` field is still read — absent is the oldest era, "
              "not unreadable", (len(_r6), len(_b6)), (1, 0))
    check("schema_of answers the era gate's question and nothing else: a version, 0 for absent, "
          "None for a field that is not a version",
          (schema_of({"schema": 3}), schema_of({}), schema_of({"schema": "3"}),
           schema_of({"schema": True})), (3, 0, None, None))
    # ⛔ r2 Codex half, High: a PRESENT version must be positive. `{"schema": -1}` was accepted AS a
    # version, compared `-1 < TRUSTED_SCHEMA`, and read as pre-cutover — silencing the join
    # contradiction this guard exists to report. ⚠ Explicit 0 is refused with it, because 0 is this
    # function's answer for ABSENT and the sentinel must not be expressible as a real value.
    check("a NEGATIVE schema is unreadable, not an old era — it is malformed testimony carrying the "
          "field, and reading it as legacy silences the join",
          schema_of({"schema": -1}), None)
    check("…and an EXPLICIT 0 is unreadable too, because 0 is the answer for ABSENT and the two "
          "must not be indistinguishable", schema_of({"schema": 0}), None)
    check("…while 1 — the oldest REAL version — is still read, so the floor is a floor and not an "
          "off-by-one that condemns the earliest corpus", schema_of({"schema": 1}), 1)
    check("TRUSTED_SCHEMA is pinned — the threshold that decides which records this check can mean "
          "anything about cannot drift silently", TRUSTED_SCHEMA, 3)
    # ⚠ **AND THE PRODUCER'S STAMP MUST CLEAR IT — READ FROM SOURCE, NEVER IMPORTED.** The
    # not-importing is deliberate and stays (a later bump to 4 must not silently stop trusting 3,
    # and `codex-review.py` imports THIS module for the filing grammar, so the import is circular).
    # But "deliberately independent" is not the same as "unchecked": two constants that must agree,
    # in two files, with no shared owner, is the defined-not-derived shape. This case reads the
    # producer's literal rather than its module, so the rule stays pure and the fetch is local.
    _prod_schema = re.search(r"^VERDICT_SCHEMA = (\d+)",
                             (ROOT / "scripts" / "codex-review.py").read_text(encoding="utf-8"),
                             re.M)
    check("the producer's current schema is READABLE at all — otherwise the next case is vacuous",
          _prod_schema is not None, True)
    check("…and it CLEARS this consumer's threshold, so a producer bump that outpaces this file is "
          "visible here rather than silently untrusting every record",
          int(_prod_schema.group(1)) >= TRUSTED_SCHEMA if _prod_schema else False, True)
    # gate_ran is READ, not re-derived. A verdict claiming the gate ran while exiting 1 is
    # self-inconsistent, but it is the WRAPPER's job to be consistent; re-deriving here would be a
    # second implementation of that rule, and the two copies would drift.
    check("exit_code is not consulted",
          verdict_problems([("v.json", {"schema": TRUSTED_SCHEMA, "gate_ran": True,
                                        "exit_code": 1,
                                        "review": "plan-x-r3-codex.md"})], _filed) == [], True)

    # ── r1 M1: THE REVERSE DIRECTION OF THE JOIN, which is what #176 was convened over ──
    # `gate_ran: true` naming a review nothing on disk carries is a coordinator citing a gate for
    # a half that was never filed. The wrapper produces exactly this on its `exit 3` path.
    check("⭐ a gate that RAN whose review is NOT filed is reported — the mirror contradiction",
          len(verdict_problems([_ran], set())), 1)
    check("…and the message names the review that is missing, not merely that one is",
          "plan-x-r3-codex.md" in _first(verdict_problems([_ran], set())), True)
    # ⚠ A SECOND, DISTINCT review name. With one fixture the clause could compare the record to
    # itself and still pass; two prove the membership test is against the disk set.
    _ran_b = ("spec-y-claude-r2.verdict.json",
              {"schema": TRUSTED_SCHEMA, "gate_ran": True, "review": "spec-y-claude-r2.md",
               "reason": "ok"})
    check("…at a different id too, so the join reads the name in the record",
          len(verdict_problems([_ran_b], _filed)), 1)
    check("…and it stays silent once that review IS on disk",
          verdict_problems([_ran_b], {"spec-y-claude-r2.md"}), [])

    # ── r1 B1: A REFUSAL IS NOT TESTIMONY ABOUT A GATE ──
    # Without this clause a re-dispatch that touched nothing would make CI tell the reader to
    # DELETE the genuine review it declined to overwrite. `refused` is READ from the record, not
    # inferred from the filename — the filename rule belongs to the producer.
    _refusal = ("plan-x-r3-codex.refused.verdict.json",
                {"schema": TRUSTED_SCHEMA, "gate_ran": False, "refused": True,
                 "review": "plan-x-r3-codex.md",
                 "reason": "refused: the promoted review already exists"})
    check("⭐ a REFUSAL beside the filed review it declined to overwrite is not a problem",
          verdict_problems([_refusal], _filed), [])
    check("…and the refusal does not fire the reverse clause either, when nothing is filed",
          verdict_problems([_refusal], set()), [])

    # ── r1 M2: THE ERA BOUNDARY IS A NUMBER IN THE RECORD ──
    # Pre-cutover the `review` field is a scratch basename, so neither direction means anything.
    # ⚠ THE LITERAL 2, not `TRUSTED_SCHEMA - 1`: an expectation written through the constant moves
    # with it, which is the self-agreeing-constant hole this repo has paid for twice.
    _old = ("legacy.verdict.json",
            {"schema": 2, "gate_ran": False, "review": "plan-x-r3-codex.md", "reason": "old"})
    check("a PRE-CUTOVER verdict is not judged — its join key is a scratch basename",
          verdict_problems([_old], _filed), [])
    _oldest = ("oldest.verdict.json",
               {"gate_ran": True, "review": "nothing-on-disk.md", "reason": "older still"})
    check("…and a record with no schema at all reads as older still, not as trusted",
          verdict_problems([_oldest], set()), [])
    check("the boundary is the CURRENT schema, so today's records ARE judged",
          len(verdict_problems([_did_not_run], _filed)), 1)

    # ── r1 M3: THE CAVEAT'S NUMBERS ARE DERIVED ──
    # The figure that used to be typed into the comment above was wrong at the denominator from
    # the day it was written, and the denominator moves on every run.
    check("era_split counts each record exactly once, in the class it belongs to",
          era_split([_did_not_run, _ran, _old, _oldest, _refusal]),
          {"total": 5, "refused": 1, "pre_cutover": 2, "checked": 2})
    check("…and an empty corpus is zeros, never a crash",
          era_split([]), {"total": 0, "refused": 0, "pre_cutover": 0, "checked": 0})
    # ── r2 Claude half, M1: era_split IS THE THIRD SITE, AND IT PARTITIONED THE SAME RECORD ────
    # ⛔ Measured on the delivered functions before the fix: `{"schema": 2, "refused": "false"}`
    # came out of `era_split` as a REFUSAL — printed to the reader as *deliberately excluded* —
    # while `verdict_problems` skipped it as PRE-CUTOVER. Two partitions of one file, from the
    # function whose entire purpose (r1 M3) is that the caveat is derived rather than guessed.
    # Hardening the line in a staged copy left the suite at 49/49, so this is the falsifier the
    # fix did not have. ⚠ The fixture is PRE-CUTOVER on purpose: above the cutover `read_verdicts`
    # now refuses the record first, and a case that passes because nothing was examined is the
    # shape this repo keeps paying for.
    _tnb = lambda v: [("v.json", {"schema": 2, "gate_ran": True, "review": "y.md", "refused": v})]
    check("a truthy NON-BOOL `refused` is not counted as a refusal in the derived caveat either — "
          "the two readers of this field must not partition one record two ways",
          era_split(_tnb("false")), {"total": 1, "refused": 0, "pre_cutover": 1, "checked": 0})
    check("…at a second distinct truthy non-bool, so era_split is not a special case for one value",
          era_split(_tnb(1)), {"total": 1, "refused": 0, "pre_cutover": 1, "checked": 0})

    with tempfile.TemporaryDirectory() as td:
        vd = pathlib.Path(td) / "verdicts"
        vd.mkdir()
        (vd / "good.json").write_text('{"gate_ran": true, "review": "a.md"}')
        (vd / "broken.json").write_text("{not json")
        (vd / "nofield.json").write_text('{"review": "b.md"}')
        recs, bad = read_verdicts(vd)
        check("a readable verdict is collected", len(recs) == 1, True)
        # A verdict that cannot be parsed must be a CANNOT RUN, never a silent skip: "unreadable"
        # and "the gate ran" are indistinguishable to a check that drops it.
        # ⚠ THE MESSAGE, NOT ONLY THE COUNT — r2 Claude half, H1's second effect. The `gate_ran`
        # type check added above ALSO refuses a record with no `gate_ran` at all (absent is not a
        # bool), so deleting the presence check left this tally at 2 and the mutation for it
        # survived. A count is satisfied by any two refusals; the reason is what this case is for.
        check("malformed and field-less verdicts are reported, not skipped",
              (len(bad), any("no `gate_ran` field" in b for b in bad)), (2, True))
        check("an absent verdict directory is not an error",
              read_verdicts(pathlib.Path(td) / "nope") == ([], []), True)

    print(f"\n{cases - failures}/{cases} self-test cases passed")
    return 1 if failures else 0


def main() -> int:
    if "--self-test" in sys.argv:
        return self_test()

    if not REVIEWS.is_dir():
        print(f"CANNOT RUN — no review directory at {REVIEWS}. Treat this as NOT RUN.",
              file=sys.stderr)
        return 2

    problems, stats = audit(REVIEWS)
    # ⛔ THE ERA CAVEAT, ON EVERY PATH THAT READ THE CORPUS — r1 L2. It used to sit after both
    # early returns, so the commit message and `docs/process-rationale.md` both claimed it printed
    # "on every run" while it printed on the rc=0 path alone. The reader hitting a RED run is
    # exactly the reader about to re-read the verdict corpus, and the claim was load-bearing for
    # the argument that the caveat could not be missed.
    # ⚠ The numbers are DERIVED from the records just read (r1 M3), never quoted: the denominator
    # moves on every run, and the figure that used to be typed into a comment here was wrong.
    _era = stats["era"]
    print(f"  ⚠ verdict corpus: {_era['total']} read — {_era['checked']} meaningfully checked "
          f"below, {_era['pre_cutover']} PRE-CUTOVER (schema < {TRUSTED_SCHEMA}: the `review` "
          f"field is the basename of the wrapper's scratch --out, so it names nothing here and "
          f"this check's silence about them is NOT evidence), {_era['refused']} refusal record(s) "
          f"(a run that declined to start; not testimony about a gate)")
    if problems:
        print(f"FAILED — {len(problems)} review round(s) with one half and no stated reason:\n")
        for p in problems:
            print(f"  ✗ {p}")
        print("\nEither run the missing half, or record why it could not run:")
        print("    REVIEW GAP: codex — usage limit; Claude ran in its place per docs/plugins.md")
        return 1

    if stats["verdicts_bad"]:
        print("CANNOT RUN — a codex-review verdict could not be read, so whether that gate ran is "
              "UNKNOWN. Treat these as NOT CHECKED:\n", file=sys.stderr)
        for b in stats["verdicts_bad"]:
            print(f"  ? {b}", file=sys.stderr)
        return 2

    print(f"review rounds: {stats['rounds']} parsed, {stats['exempt']} pre-existing exemptions, "
          f"0 silent gaps; {stats['verdicts']} codex-review verdict(s) read, none contradicted")
    print(f"  ⚠ {stats['unparsed']} files in docs/reviews/ carry no round number and are NOT "
          f"covered by this check")
    # The era caveat is printed ABOVE, before the early returns — see the comment there. It is not
    # repeated here: a second copy would be a second sentence to keep true.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
