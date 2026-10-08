#!/usr/bin/env python3
"""A figure in a NEW backlog row must say where it was measured.

WHY THIS EXISTS — backlog #256, and the damning part is that the rule already existed.
---------------------------------------------------------------------------------------
`docs/process-checklists.md` has carried *Qualify every number in prose* since **2026-08-27**,
unenforced. On the night of 2026-10-06 it was violated three times by an author who had read it:

  * `1,414 anchors` quoted as the delivered count when that was the count at `2780b05a` and the
    tree held **1,416** (PR #367 round 2, Low 1);
  * `437 ms` for a pass a reviewer then measured at **63 ms**, and a later run at **289 ms**;
  * `3 unbound` where the control was clean and the number was **2**.

Each was caught by a reviewer. None by a machine. The rule: a number that informs a decision
names **where it was measured** — a ref, a commit, a run, a path with a line.

⛔ THE CALIBRATION, MEASURED BEFORE THE RULE WAS CHOSEN — and it is the reason this guard is
shaped the way it is. Over `docs/backlog.md` as it stands (247 rows, 231 carrying a bolded
figure, 1,368 bolded figures in total):

    definition                                        fires on
    ------------------------------------------------  --------------------------------
    provenance anywhere in the row, incl. a DATE           0 of 231   ⛔ VACUOUS: every row
                                                                      carries its filing date,
                                                                      which is not where a
                                                                      number was measured
    a commit-ish or ref anywhere in the row              169 of 231   (73.2%)
    …or any backticked path                                2 of 231   ( 0.9%)
    provenance within ±150 chars of the figure           479 of 1368  (35.0%)
    provenance within ±400 chars of the figure           186 of 1368  (13.6%)

A whole-file rule is therefore unusable at BOTH ends: the loose definitions cannot fail, and the
tight ones fire on a third of the corpus — and backlog #56 measured exactly what happens to a
gate that is red without cause. It gets switched off.

So this is a RATCHET, not an audit. It reads only the rows this branch ADDS or CHANGES. Those are
rows someone is writing right now, where naming the ref costs a few characters and the author
still knows the answer. The 169 historical rows are grandfathered, visible under `--all`, and
never a failure.

WHAT COUNTS AS PROVENANCE
-------------------------
A commit-ish in backticks · `origin/<branch>` or `HEAD` · a `path.py:123` with a line · a run id
of six or more digits. ⛔ **NOT a bare date** — that is the filing date, and treating it as
provenance is what made the first definition vacuous. ⛔ **NOT a bare filename** — naming the
file a row is about does not say where its numbers came from.

EXIT CODES: 0 = ok, or findings in warn mode · 1 = findings under `--strict` · 2 = CANNOT RUN.

USAGE
    python3 scripts/check-provenance.py --base origin/master
    python3 scripts/check-provenance.py --all          # audit, context only, never fails
    python3 scripts/check-provenance.py --self-test    # 93 cases, pure, no git

⚠ THE COUNT ABOVE IS VERIFIED BY RUNNING IT (`scripts/check-selftest-counts.py`).
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BACKLOG = "docs/backlog.md"

ROW_RE = re.compile(r"^\| *(\d+) \|")
# ⛔ BALANCED, NON-OVERLAPPING SPANS — round 1 Codex Medium. The old pattern scanned for any
# `**…**` containing a digit, so `**DONE** after 99 checks **42 failures**` matched
# `** after 99 checks **` and LOST the actual bolded measurement. `(?:(?!\*\*).)+?` cannot
# cross a delimiter, so the spans pair the way a reader pairs them.
BOLD_RE = re.compile(r"\*\*(?:(?!\*\*).)+?\*\*", re.S)
# ⟳ r1 Claude M2 + L3 — A SINGLE DIGIT IS A FIGURE WHEN A COUNTED NOUN FOLLOWS IT, and this
# regex is DELIBERATELY DIFFERENT from `check-withdrawal.NUMBER_RE`, which is the identical
# pattern this one used to be. L3 was right that two copies of one rule is this repository's
# most-measured defect; the resolution is not one owner but one DIFFERENCE, written down:
#
#   check-withdrawal  scans UNBOLDED PROSE, where "2" occurs in every document in the repo and
#                     a signature built around it is noise. Two-digit floor justified.
#   HERE              scans only inside a `**…**` span the author chose to emphasise, which is
#                     the signal this guard keys on. The justification travelled with the bytes
#                     and not with the reasoning, and M2 is the consequence: #256's own third
#                     motivating defect — `**3 unbound**` where the control was clean and the
#                     number was 2 — was structurally invisible to the guard built for it.
#
# ⛔ "ALLOW ANY SINGLE DIGIT" WAS MEASURED AND REFUTED — a finding's proposed fix is a
# hypothesis. Over the 247 live rows it made 5 newly visible and not one was a measurement:
# `**M2b**`, `**F6 (Low)**`, `**R3 is satisfied …**`, `**exit 1 — the same code …**`. Those are
# identifiers and exit codes. The shape that IS a measurement is a digit followed by the thing
# counted, so the third alternative requires whitespace and a letter, and the lookbehinds
# refuse the exit-code idiom that otherwise sneaks in through it.
#
# MEASURED 2026-10-07 over docs/backlog.md: 11 of 11 adjacent positives and negatives correct,
# exactly ONE newly visible row (#156, "**The measured cost of the SIMPLER rule is 0 guards,
# not two**" — a real claim with no provenance), and the firing rate is UNCHANGED at 46%
# (102/223 against 102/222). A rule that adds a true positive and moves the rate by nothing is
# the one worth taking.
# ⟳ r2 Codex MEDIUM — THE THREE LOOKBEHINDS WERE A DENYLIST OF THREE IDIOMS, and the review
# found the fourth, fifth and sixth immediately: `**rc 1 is failure**` and
# `**Phase 1 is complete**` were COUNTED as measurements, while `**3%** failed` and
# `**3** failures` were still MISSED. Growing the lookbehind list is the wrong instrument — the
# distinction is not which word precedes the digit but which ROLE the digit plays:
#
#   a MEASUREMENT  puts the number before the thing counted   `3 unbound`, `2 gaps`, `5 rounds`
#   an IDENTIFIER  puts the number after a label              `ADR 2`, `rc 1`, `step 2`, `F6`
#   a STATUS CODE  makes the number the subject                `1 is failure`, `(2)`
#
# So the rule reads BOTH directions and lives in `single_digit_figures` where it can be read.
# MEASURED 2026-10-07: 20 of 20 witnesses correct — including all four the review supplied —
# with the live firing rate UNCHANGED at 48% (106/223) and not one row changing state. Same
# answer where it was already right, correct where it was wrong.
MULTI_NUM_RE = re.compile(r"\d[\d,]*\.?\d+|\d{2,}|\d\s*%")

# A STANDALONE digit. ⚠ `\w` and not `\d`: `(?<![\d.,])` let the `2` inside `**M2b**` and the
# `6` inside `**F6 (Low)**` match, so two identifier rows became figures (measured).
# ⚠ `%` IS EXCLUDED ON THE RIGHT so that `MULTI_NUM_RE`'s `\d\s*%` alternative actually
# OWNS the percentage case. Without this, SINGLE matched the `3` of `3%` and treated `%`
# as the counted noun — correct by accident, and it made the percentage alternative
# UNKILLABLE: the mutation removing it survived a green suite. One rule, one owner.
SINGLE_NUM_RE = re.compile(r"(?<![\w.,])\d(?![\w.,%])")

# A parenthesised digit is a label or an exit code, never a count — `**CANNOT RUN (2)**`, which
# is row #152's own wording. A SHAPE rule rather than another word in a list.
PARENTHESISED_NUM_RE = re.compile(r"\(\s*\d\s*\)")

# The number is LABELLED by what precedes it, so it identifies rather than counts.
LABEL_BEFORE = frozenset({
    "exit", "exits", "code", "rc", "phase", "adr", "step", "round", "shard", "task", "pr",
    "issue", "case", "row", "gate", "arm", "milestone", "part", "section", "version",
})

# The number is the SUBJECT of what follows, so again it is not counting anything.
SUBJECT_AFTER = frozenset({
    "is", "was", "are", "were", "be", "been", "being", "means", "meant", "says", "said",
    "shows", "showed", "states", "stated", "reads", "from", "of", "to", "in", "on", "at",
    "and", "or", "but", "then", "if", "that", "which", "while", "because",
})

TOKEN_STRIP = "`*_([{)]}>,.:;!?\"'"


def single_digit_figures(span: str, after: str = "") -> list[str]:
    """Single-digit MEASUREMENTS in a bold span, as "<digit> <noun>". PURE.

    `after` is the row text following the span, because the counted noun can sit OUTSIDE the
    bold — `**3** failures` is row-shaped and the span alone cannot see the word that makes it
    a measurement (r2 Codex Medium).
    """
    out: list[str] = []
    labelled = {m.start() + next(i for i, c in enumerate(m.group(0)) if c.isdigit())
                for m in PARENTHESISED_NUM_RE.finditer(span)}
    for m in SINGLE_NUM_RE.finditer(span):
        if m.start() in labelled:
            continue
        before = [t for t in (w.strip(TOKEN_STRIP) for w in span[:m.start()].split()) if t]
        tail = [t for t in (w.strip(TOKEN_STRIP)
                            for w in (span[m.end():] + " " + after).split()) if t]
        prev = before[-1].lower() if before else ""
        nxt = tail[0].lower() if tail else ""
        if prev in LABEL_BEFORE or nxt in SUBJECT_AFTER or not nxt:
            continue
        out.append(f"{m.group(0)} {nxt}")
    return out


def figures_in_span(span: str, after: str = "") -> list[str]:
    """Every figure a bold span carries, single digits included. PURE."""
    return [m.group(0) for m in MULTI_NUM_RE.finditer(span)] + single_digit_figures(span, after)


# Retained as the MULTI-digit rule's name: `check-withdrawal.NUMBER_RE` is still deliberately
# different from it (r1 Claude L3), and a case asserts that difference.
NUM_RE = MULTI_NUM_RE

# ⛔ Each alternative names WHERE a measurement happened. A bare date and a bare filename are
# deliberately absent; including the date took the firing rate to 0 of 231, which is a rule
# that cannot fail.
PROVENANCE_RE = re.compile(
    r"`[0-9a-f]{7,40}`"                                   # a commit-ish in backticks
    r"|\borigin/\w+"                                       # a ref (\b: `notorigin/x` is not one)
    # ⟳ r1 Claude M3 — `HEAD` MUST BE THE SOURCE, NOT THE SUBJECT. A bare `\bHEAD\b` counted
    # prose ABOUT git as provenance, so row #255's own wording — "**`--clear` REPORTS QUIET
    # SUCCESS WHEN IT CANNOT READ HEAD** and it cost **47 s** of CI" — passed with an
    # unqualified `**47 s**` because the sentence happens to contain the token. Backticked, or
    # suffixed (`HEAD~1`), or introduced by at / as of / measured: those are a reader being told
    # where a number came from. MEASURED over the live file, FOUR rows pass today on a bare
    # HEAD alone (#131 #133 #134 #255) — and the ratchet reads ADDED rows, so tightening this
    # does not retro-fire on them; it stops the next one.
    # ⟳⟳ r2 Codex MEDIUM — `\bat` WAS A SEMANTIC BYPASS, not just a word-boundary question.
    # It correctly refused `format HEAD` and `lookat HEAD`, and then accepted
    # **"we cannot look at HEAD"** — prose ABOUT git being unreadable, which is the exact class
    # M3 was filed to stop, one word away. Measured independently by this coordinator and by the
    # review within two minutes of each other.
    #
    # A ref is provenance when something was MEASURED there. So: backticked, suffixed, `as of`,
    # or an explicit measurement verb within two words. ⚠ `the tree at HEAD held 1,416` NO
    # LONGER counts, and that is deliberate — it is indistinguishable, by any rule short of
    # reading English, from `we cannot look at HEAD`. MEASURED over the live file: 11 of 11
    # witnesses correct, **ZERO rows lose provenance**, firing rate unchanged at 46% (90/195).
    r"|`HEAD`|\bHEAD[~^]|\bas of\s+HEAD\b"
    # ⚠ `read` IS NOT IN THIS LIST, and my first draft had it. "cannot read HEAD" is the exact
    # prose M3 exists to refuse — row #255's own wording — so the verb that most naturally
    # describes reading a ref is the one that cannot be trusted to mean a measurement happened.
    # Caught by one of this file's own cases, not by inspection.
    r"|(?:measured|re-?derived|derived|taken|counted|observed|verified|sampled)"
    r"(?:\s+\w+){0,2}\s+HEAD\b"
    r"|`[^`]+\.(?:py|sh|md|yml|yaml|ts|tsx|sql|json):\d+`"  # a path WITH a line
    r"|\brun\s+`?\d{6,}"                                  # a CI run id
)


# ── the rule, pure ───────────────────────────────────────────────────────────

# ⟳ THE 80-CHARACTER CAP IS GONE — round 1 Codex Medium, confirmed by measurement. It was meant
# to exclude bolded SENTENCES, and it excluded real claims: row #17's
# *"Five dual adversarial rounds produced 26 Blocking findings and NONE was in the predicate"*
# is a measurement, and it is 88 characters. Re-measured across the live file, the cap moves the
# firing rate by a single point — 45% at 80 chars, 46% with no cap at all — so it dropped
# genuine claims and bought nothing. Length was never evidence that a count is incidental.
DATE_RE = re.compile(r"\b20\d\d-\d\d-\d\d\b")


def bolded_figures(row: str) -> list[str]:
    """Every bolded span in `row` that carries a load-bearing figure. PURE.

    Bold is the signal: this repository bolds the figure a verdict rests on, and an unbolded
    number in passing prose is not what #256 is about. Two exclusions, both measured against the
    live file rather than guessed:

      * a bolded DATE is not a measurement — `**ADOPTED 2026-07-30**` was the first thing this
        rule flagged, and it is a decision marker, not a count;
      * (a length cap once lived here and is GONE — see the note above `DATE_RE`.)

    ⚠ The date exclusion narrows the population and does NOT move the firing rate, which is how
    we know the rate is real: it is a ratchet over new rows rather than an audit that would be
    red on half the file.
    """
    out = []
    for m in BOLD_RE.finditer(row):
        b = m.group(0)
        # ⟳ r2 Codex Medium: the counted noun can live OUTSIDE the span (`**3** failures`), so
        # the following text is handed over too. 40 characters is the next word and then some.
        if figures_in_span(DATE_RE.sub("", b), row[m.end():m.end() + 40]):
            out.append(b)
    return out


def has_provenance(row: str) -> bool:
    """True when the row says where a measurement came from. PURE."""
    return bool(PROVENANCE_RE.search(row))


def is_backlog_row(line: str) -> bool:
    """True for a `| <id> | …` table row. PURE."""
    return bool(ROW_RE.match(line))


def row_id(line: str) -> str:
    """The row's id, or '' when the line is not a row. PURE."""
    m = ROW_RE.match(line)
    return m.group(1) if m else ""


def findings_for(rows: list[str]) -> list[tuple[str, int]]:
    """(row_id, figure_count) for each row carrying a bolded figure and no provenance. PURE."""
    out: list[tuple[str, int]] = []
    for line in rows:
        if not is_backlog_row(line):
            continue
        figs = bolded_figures(line)
        if figs and not has_provenance(line):
            out.append((row_id(line), len(figs)))
    return out


def added_rows(diff_text: str) -> list[str]:
    """Backlog rows this diff ADDS. PURE.

    Changed rows arrive as an add too, which is what we want: editing a row is re-authoring it.
    """
    # ⚠ No `not l.startswith("+++")` guard: `is_backlog_row` already rejects the diff header,
    # because `"+++ b/docs/backlog.md"[1:]` is `"++ b/docs/backlog.md"` and that is not a row.
    # The clause was here and a mutation SURVIVED its removal — dead code wearing the look of a
    # safety check, which is the shape `a-test-that-cannot-fail` is about. Deleted rather than
    # given a contrived case.
    return [l[1:] for l in diff_text.split("\n")
            if l.startswith("+") and is_backlog_row(l[1:])]


def verdict(n_findings: int, n_rows: int, strict: bool) -> tuple[int, str]:
    """(exit_code, message). PURE.

    `n_rows == 0` is ok, not cannot-run: a branch that touches no backlog row has nothing to
    qualify. Cannot-run is decided by the caller, before the numbers exist.
    """
    if n_rows == 0:
        return 0, "ok — this branch adds or changes no backlog row."
    if n_findings == 0:
        return 0, f"ok — {n_rows} backlog row(s) authored, every bolded figure names a source."
    noun = "row" if n_findings == 1 else "rows"
    msg = (f"{n_findings} new backlog {noun} carry a bolded figure with no ref, commit or run id "
           f"saying where it was measured.")
    return (1 if strict else 0), ("FOUND — " if strict else "WARN — ") + msg


# ── self-test ────────────────────────────────────────────────────────────────

ROW_SHA = "| 300 | 🟠 **A thing broke 1,416 times** — measured at `93e3133a`. | x | M | y | open |"
ROW_BARE = "| 301 | 🟠 **A thing broke 1,416 times** — found 2026-10-07. | x | M | y | open |"
ROW_NONUM = "| 302 | 🟠 **A thing broke often** — found 2026-10-07. | x | M | y | open |"
ROW_PATHLINE = "| 303 | 🟠 **2,048 rows** — see `scripts/x.py:84`. | x | M | y | open |"
ROW_RUN = "| 304 | 🟠 **14 shards** — run `37661154718` was green. | x | M | y | open |"

BOLD_CASES: list[tuple[str, str, int]] = [
    ("a bolded figure is found", "**1,416** times", 1),
    ("two bolded figures are both found", "**12** and **34**", 2),
    ("bold without a figure does not count", "**a thing broke**", 0),
    ("an unbolded figure does not count", "it broke 1,416 times", 0),
    ("a bolded figure with words around it still counts", "**broke 1,416 times**", 1),
    ("a decimal inside bold counts", "**0.9%** of rows", 1),
    ("a single digit alone does not count as a figure", "**7**", 0),
    ("⛔ a bolded DATE is a decision marker, not a measurement", "**ADOPTED 2026-07-30**", 0),
    # ⟳ r1 Claude M3 — the witness is row #255's OWN wording. `has_provenance` is the subject
    # here, not `bolded_figures`, so this pair lives in the provenance cases below as well; this
    # entry keeps the figure half honest (the row DOES carry a figure, so the row reaching the
    # provenance test is the precondition M3 is about).
    # ⚠ ONE, not two: the first bold span holds no digit, so only `**47 s**` is a figure. I
    # asserted 2 and the suite corrected me — derive the number, do not type it.
    ("⭐ M3: row #255's wording carries a real figure, which is why its provenance matters",
     "**`--clear` REPORTS QUIET SUCCESS WHEN IT CANNOT READ HEAD** and it cost **47 s** of CI", 1),
    ("a bolded date WITH a real figure still counts", "**12 rounds on 2026-07-30**", 1),
    # ⟳ r1 Claude M2 — THIS CASE USED TO ASSERT 0, "per the single-digit rule above". It was
    # documenting the blind spot rather than a property: `3 rounds` is a measurement, and the
    # only reason it scored 0 was that NUM_RE could not see one digit. A case asserting a gap
    # breaks when the gap closes, and the red is the alarm — `a-stated-bound-outlives-its-hole`.
    ("...and a single digit BESIDE a date counts, now the counted noun makes it a figure",
     "**3 rounds on 2026-07-30**", 1),
    ("⭐ M2's own witness: #256's third motivating defect is no longer invisible to it",
     "**3 unbound** anchors", 1),
    # ⛔ THE ADJACENT NEGATIVES, not absurd ones — these are the four live shapes that made
    # "allow any single digit" the wrong fix, each taken from docs/backlog.md.
    ("...but an identifier is not a count, however bold", "**M2b**", 0),
    ("...nor a severity label", "**F6 (Low)**", 0),
    ("...nor a phase number with no noun counted", "**Phase 6**", 0),
    # ⚠ EACH LOOKBEHIND NEEDS A FIXTURE THAT WOULD MATCH WITHOUT IT. The first version of the
    # singular case read "**exit 1 — the same code …**", and the character after "1 " is an
    # EM-DASH, not a letter — so the counted-noun alternative never matched it and the case
    # passed because of the punctuation, not because of the lookbehind. The mutation that strips
    # the lookbehinds survived it. `fixing-a-premise-is-not-covering-the-branch`.
    ("...and an EXIT CODE is not a measurement, because the digit is the SUBJECT of `is`",
     "**exit 1 is the same code a legitimate warning produces**", 0),
    ("...including its plural spelling, which is the shape row #118 actually uses",
     "**exits 1 from check-review-decision.py**", 0),
    ("...and `code 2 means` is refused the same way", "**code 2 means CANNOT RUN**", 0),
    # ── r2 Codex MEDIUM's four witnesses: two MISSED measurements, two wrongly COUNTED ───────
    ("⭐ r2: a single-digit PERCENTAGE is a measurement and was missed entirely",
     "**3%** failed", 1),
    ("⭐ r2: the counted noun can live OUTSIDE the bold, which the span alone cannot see",
     "**3** failures", 1),
    ("⭐ r2: `rc 1 is failure` is a STATUS CODE and was counted as a measurement",
     "**rc 1 is failure**", 0),
    ("⭐ r2: `Phase 1 is complete` is a PHASE and was counted as a measurement",
     "**Phase 1 is complete**", 0),
    # ⚠ `says` is itself in SUBJECT_AFTER, so `**ADR 2 says**` is refused by EITHER half and
    # cannot tell them apart — the mutation dropping the label test survived it. This fixture's
    # next word is NOT a subject word, so only the LABEL half can refuse it.
    ("...and `ADR 2 says` is labelled by what PRECEDES it, which no lookbehind list reached",
     "**ADR 2 says**", 0),
    ("⭐ ...and the LABEL half alone refuses this one, whose next word is not a subject word",
     "**ADR 2 requires provenance**", 0),
    ("⭐ ...while the SUBJECT half alone refuses this one, which nothing labels",
     "**1 is the only survivor**", 0),
    ("...and `step 2 of 5` likewise", "**step 2 of 5**", 0),
    ("...and a PARENTHESISED digit is a code, which is row #152's own wording",
     "**CANNOT RUN (2)** printing nothing", 0),
    ("...while a digit before a VERB still counts when nothing labels it — the rule is about "
     "ROLE, not about the part of speech that follows",
     "**2 failed**", 1),
    ("...and a version identifier is not a count", "**v2 ships**", 0),
    ("⭐ a long bolded measurement is NOT dropped — the 80-char cap is gone (r1 Codex Medium)",
     "**Five dual adversarial rounds produced 26 Blocking findings and NONE was in the "
     "predicate**", 1),
    # ⚠ COUNTED, AND THAT WAS NOT ENOUGH. The unbalanced pattern also returns ONE span here —
    # the wrong one, `** after 99 checks **` — so a count-only case could not tell the two
    # apart and the mutation survived. The CONTENT is the assertion.
    ("⭐ bold spans pair the way a reader pairs them, so the real figure is not lost",
     "**DONE** after 99 checks **42 failures**", 1),
]

# ── r2 Codex Medium: the predicate's own cases, at two DISTINCT `after` values ─────────────
SINGLE_DIGIT_CASES: list[tuple[str, str, str, list]] = [
    ("a digit before the thing counted is a measurement", "**3 unbound**", "", ["3 unbound"]),
    ("...and the noun may sit after the span", "**3**", " failures", ["3 failures"]),
    ("a digit the previous word LABELS is not", "**ADR 2 says**", "", []),
    ("a digit that is the SUBJECT of what follows is not", "**rc 1 is failure**", "", []),
    ("a PARENTHESISED digit is never a count", "**CANNOT RUN (2)**", " printing", []),
    ("a bare digit with nothing following counts nothing", "**7**", "", []),
    ("a digit inside an identifier is not a standalone digit at all", "**M2b**", "", []),
]

PROV_CASES: list[tuple[str, str, bool]] = [
    ("a backticked commit-ish is provenance", "measured at `93e3133a`", True),
    ("a ref is provenance", "measured against origin/master", True),
    # ⟳ r2 Codex Medium: this case USED TO assert that bare `at HEAD` is provenance. It is not —
    # the same three words appear in `we cannot look at HEAD`, which names no source at all.
    ("HEAD is provenance when something was MEASURED there",
     "measured at HEAD, the tree held 1,416", True),
    ("...and a bare `at HEAD` is NOT, because it is indistinguishable from prose about git",
     "the tree at HEAD held 1,416", False),
    ("⭐ r2: the semantic bypass — `we cannot look at HEAD` names no source",
     "**3 failures**; we cannot look at HEAD", False),
    ("...nor does `it fails to look at HEAD`", "it fails to look at HEAD when unreadable", False),
    ("...while `re-derived at HEAD` does, and so does any measurement verb within two words",
     "re-derived at HEAD", True),
    ("...and `as of HEAD` still introduces a source", "1,416 anchors as of HEAD", True),
    # ── r1 Claude M3: `HEAD` as the SUBJECT is not provenance ────────────────────────────────
    # ⛔ THE WITNESS IS ROW #255'S OWN WORDING. A bare \bHEAD\b counted prose ABOUT git, so an
    # unqualified `**47 s**` passed because the sentence happened to contain the token.
    ("⭐ M3: prose ABOUT reading HEAD is not provenance for a figure beside it",
     "`--clear` REPORTS QUIET SUCCESS WHEN IT CANNOT READ HEAD and it cost **47 s** of CI",
     False),
    ("...but a BACKTICKED `HEAD` is a reader being told the ref", "measured at `HEAD`", True),
    ("...and a suffixed one is too, because `HEAD~1` can only be a ref",
     "measured against HEAD~1", True),
    ("...and `as of HEAD` introduces it as a source", "1,416 anchors as of HEAD", True),
    ("...while HEAD merely NAMED mid-sentence does not", "we cannot read HEAD here", False),
    ("...and `read` is deliberately NOT a measurement verb, because that is row #255's wording",
     "`--clear` cannot read HEAD and it cost **47 s**", False),
    ("a path WITH a line is provenance", "see `scripts/x.py:84`", True),
    ("a run id is provenance", "run `37661154718` was green", True),
    ("⛔ a bare date is NOT provenance — it is the filing date", "found 2026-10-07", False),
    ("⛔ a bare filename is NOT provenance", "see `scripts/check-docs.py`", False),
    ("⭐ `notorigin/fiction` is NOT a ref — the word boundary (r1 Codex Medium)",
     "source notorigin/fiction", False),
    ("...and a real `origin/<branch>` still is", "measured against origin/main", True),
    ("plain prose is not provenance", "it broke a lot", False),
    ("a short hex string is not a commit-ish", "the value `abc`", False),
]

ROWSET_CASES: list[tuple[str, list[str], int]] = [
    ("a row naming a commit passes", [ROW_SHA], 0),
    ("⭐ a row with a bolded figure and only a date FIRES", [ROW_BARE], 1),
    ("a row with no figure at all passes", [ROW_NONUM], 0),
    ("a path-with-line passes", [ROW_PATHLINE], 0),
    ("a run id passes", [ROW_RUN], 0),
    ("mixed rows report only the bare one", [ROW_SHA, ROW_BARE, ROW_RUN], 1),
    ("a non-row line is ignored entirely", ["just some prose with **1,416**"], 0),
]

VERDICT_CASES: list[tuple[str, int, int, bool, int]] = [
    ("no rows touched -> ok", 0, 0, False, 0),
    ("rows touched, all qualified -> ok", 0, 4, False, 0),
    ("⭐ findings in WARN mode still exit 0, by #56", 2, 4, False, 0),
    ("findings under --strict exit 1", 2, 4, True, 1),
    ("no rows touched under --strict is still ok", 0, 0, True, 0),
]



def self_test() -> int:
    failures = 0

    # Direct calls with literal, pairwise-distinct arguments, inside the suite body:
    # `check-fixture-variation.py` reads call sites HERE, and a table loop is one call site.
    # ⛔ The verdict arms share exit codes, so a code-only case cannot tell them apart —
    # measured: the mutation deleting `if n_rows == 0:` SURVIVED a green suite. What differs is
    # the SENTENCE, and "nothing was checked" must not read like "everything passed".
    # ⚠ These live INSIDE the suite function: `check-fixture-variation` counts call sites in the
    # suite body only, and a module-level table does not count. I made that exact mistake on
    # `find-claim.py` an hour earlier and repeated it here.
    MESSAGE_CASES: list[tuple[str, str, str]] = [
        ("⭐ no rows touched says so, rather than claiming everything passed",
         verdict(0, 0, False)[1], "ok — this branch adds or changes no backlog row."),
        ("rows touched and clean says how many it checked",
         verdict(0, 2, False)[1], "ok — 2 backlog row(s) authored, every bolded figure names a source."),
    ]

    direct: list[tuple[str, object, object]] = [
        ("⭐ ...and the span it returns is the REAL figure, not the text between two bold runs",
         bolded_figures("**DONE** after 99 checks **42 failures**"), ["**42 failures**"]),
        ("bolded_figures on a literal row with a figure",
         len(bolded_figures("| 9 | **1,416** rows |")), 1),
        ("bolded_figures on a literal row with none",
         len(bolded_figures("| 9 | plain prose |")), 0),
        ("has_provenance on a literal commit-ish",
         has_provenance("measured at `deadbeef1`"), True),
        ("has_provenance on literal prose with only a date",
         has_provenance("filed 2026-01-02"), False),
        ("verdict with literal 1 finding over 1 row, strict",
         verdict(1, 1, True)[0], 1),
        ("verdict with literal 0 findings over 9 rows, warn",
         verdict(0, 9, False)[0], 0),
        ("added_rows keeps an added backlog row",
         added_rows("+| 400 | **9,000** at `deadbee` |\n-| 401 | old |"), ["| 400 | **9,000** at `deadbee` |"]),
        ("added_rows drops the +++ header and removed lines",
         added_rows("+++ b/docs/backlog.md\n-| 402 | gone |"), []),
        ("row_id reads the id from a literal row", row_id("| 123 | x |"), "123"),
        ("row_id on a non-row is empty", row_id("## a heading"), ""),
        ("is_backlog_row on a literal row", is_backlog_row("| 7 | x |"), True),
        ("is_backlog_row on a table separator", is_backlog_row("|---|---|"), False),
        ("findings_for over a literal clean row", findings_for([ROW_PATHLINE]), []),
        ("findings_for over a literal bare row", findings_for([ROW_BARE]), [("301", 1)]),
    ]

    # ── ADR-0014 D2: a case must reach main() with a world it BUILT ────────────────────────
    import tempfile as _tf, contextlib as _ctx, io as _io
    def _drive_main():
        with _tf.TemporaryDirectory() as td:
            r = Path(td)
            with _ctx.redirect_stdout(_io.StringIO()), _ctx.redirect_stderr(_io.StringIO()):
                # no docs/backlog.md in this world -> CANNOT RUN, never a quiet pass
                return main(["--base", "origin/master"], root=r)
    direct.append(("⭐ main() is driven from a case against a BUILT world, and a world with no "
                   "backlog is CANNOT RUN rather than a pass (ADR-0014 D2)",
                   _drive_main(), 2))

    def _drive_main_all():
        """A SECOND drive, at a different argv and root."""
        with _tf.TemporaryDirectory() as td2:
            r2 = Path(td2); (r2 / "docs").mkdir()
            (r2 / "docs" / "backlog.md").write_text("no rows here\n")
            with _ctx.redirect_stdout(_io.StringIO()), _ctx.redirect_stderr(_io.StringIO()):
                return main(["--all"], root=r2)
    direct.append(("...and `--all` over a backlog that parses to ZERO rows is CANNOT RUN",
                   _drive_main_all(), 2))

    total = (2 + len(BOLD_CASES) + len(SINGLE_DIGIT_CASES) + len(PROV_CASES) + len(ROWSET_CASES)
             + len(VERDICT_CASES) + len(MESSAGE_CASES) + len(direct))
    print(f"check-provenance --self-test  ({total} cases)")

    for name, text, want in BOLD_CASES:
        got = len(bolded_figures(text))
        ok = got == want
        failures += not ok
        print(f"  [{'ok' if ok else 'FAIL'}] {name}: got {got} want {want}")

    # ⚠ DIRECT CALLS AT PAIRWISE-DISTINCT LITERALS. The table below drives this function from
    # ONE call site, so `span` and `after` are each a single expression to
    # `check-fixture-variation`, which reads argument EXPRESSIONS and refused the file for it.
    for name, got, want in [
        ("single_digit_figures over a literal span, with no trailing text",
         single_digit_figures("**4 shards**"), ["4 shards"]),
        ("...and over a DIFFERENT span whose noun arrives in a DIFFERENT trailing string",
         single_digit_figures("**6**", " regressions found"), ["6 regressions"]),
    ]:
        ok = got == want
        failures += not ok
        print(f"  [{'ok' if ok else 'FAIL'}] {name}: got {got} want {want}")

    for name, span, after, want in SINGLE_DIGIT_CASES:
        got = single_digit_figures(span, after)
        ok = got == want
        failures += not ok
        print(f"  [{'ok' if ok else 'FAIL'}] {name}: got {got} want {want}")

    for name, text, want in PROV_CASES:
        got = has_provenance(text)
        ok = got == want
        failures += not ok
        print(f"  [{'ok' if ok else 'FAIL'}] {name}: got {got} want {want}")

    for name, rows, want in ROWSET_CASES:
        got = len(findings_for(rows))
        ok = got == want
        failures += not ok
        print(f"  [{'ok' if ok else 'FAIL'}] {name}: got {got} want {want}")

    for name, nf, nr, strict, want in VERDICT_CASES:
        got = verdict(nf, nr, strict)[0]
        ok = got == want
        failures += not ok
        print(f"  [{'ok' if ok else 'FAIL'}] {name}: got {got} want {want}")

    for name, got, want in MESSAGE_CASES:
        ok = got == want
        failures += not ok
        print(f"  [{'ok' if ok else 'FAIL'}] {name}: got {got!r} want {want!r}")

    for name, got, want in direct:
        ok = got == want
        failures += not ok
        print(f"  [{'ok' if ok else 'FAIL'}] {name}: got {got!r} want {want!r}")

    print(f"{total - failures}/{total} passed")
    return 1 if failures else 0


# ── the git/filesystem half ──────────────────────────────────────────────────

def main(argv: "list[str] | None" = None, root: Path = REPO) -> int:
    """ADR-0014 D2: the world arrives as a defaulted PARAMETER so a case can drive it.

    Shipped first with `main()` reading `REPO` directly, and `check-main-drivable.py` refused the
    whole branch for it — every mutation shard's control went red behind one guard's suite.
    """
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    ap.add_argument("--base", default="origin/master")
    ap.add_argument("--all", action="store_true",
                    help="audit every row in the file; context only, never fails")
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args(argv)

    if args.self_test:
        return self_test()

    path = root / BACKLOG
    if not path.is_file():
        print(f"CANNOT RUN — {BACKLOG} is missing. A zero over nothing is not a pass.", file=sys.stderr)
        return 2

    if args.all:
        rows = [l for l in path.read_text(encoding="utf-8").split("\n") if is_backlog_row(l)]
        if not rows:
            print("CANNOT RUN — no backlog rows parsed; the table shape moved.", file=sys.stderr)
            return 2
        found = findings_for(rows)
        print(f"audit — {len(found)} of {len(rows)} rows carry a bolded figure with no source named.")
        print("These are GRANDFATHERED: the live rule reads only rows a branch adds or changes. "
              "A gate red on a third of its corpus gets switched off (#56).")
        return 0

    try:
        r = subprocess.run(["git", "diff", "--unified=0", f"{args.base}...HEAD", "--", BACKLOG],
                           capture_output=True, text=True, cwd=root)
    except OSError as exc:
        print(f"CANNOT RUN — cannot invoke git: {exc}", file=sys.stderr)
        return 2
    if r.returncode != 0:
        print(f"CANNOT RUN — git diff against {args.base} failed: {r.stderr.strip()[:200]}",
              file=sys.stderr)
        return 2

    rows = added_rows(r.stdout)
    found = findings_for(rows)
    for rid, nfigs in found:
        print(f"  #{rid}: {nfigs} bolded figure(s), and the row names no commit, ref, "
              f"path:line or run id. Where was it measured?")
    code, msg = verdict(len(found), len(rows), args.strict)
    print(msg)
    return code


if __name__ == "__main__":
    sys.exit(main())
