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
    python3 scripts/check-provenance.py --self-test    # 144 cases, pure, no git

⚠ THE COUNT ABOVE IS VERIFIED BY RUNNING IT (`scripts/check-selftest-counts.py`).
"""

from __future__ import annotations

import argparse
import importlib.util
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BACKLOG = "docs/backlog.md"

_CELL_SPLIT_CACHE: "re.Pattern | None" = None


def _cell_split() -> "re.Pattern":
    """`check-docs.CELL_SPLIT`, the ONE owner of the markdown-cell rule (r2 Claude M3).

    Imported rather than restated: a `\\|` escape inside a cell is not a delimiter, and that
    exception lives in exactly one place. Cached because the import reads a 5,000-line module.
    """
    global _CELL_SPLIT_CACHE
    if _CELL_SPLIT_CACHE is None:
        spec = importlib.util.spec_from_file_location(
            "check_docs_for_cells", Path(__file__).resolve().parent / "check-docs.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _CELL_SPLIT_CACHE = mod.CELL_SPLIT
    return _CELL_SPLIT_CACHE

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
# ⛔⛔ THIS RULE IS A HEURISTIC, AND THE COMMENT THAT SAID "CORRECT" WAS WRONG TWICE OVER.
# Round 2's Claude half found fifteen witnesses beyond the twenty I chose, and the twenty were
# mine — "20 of 20 on witnesses I chose" is not a bound, it is a description of my sample.
#
#   COUNTED, and should not be — an identifier, not a count:
#     **Stage 3 cloud-sync shipped**   **Sub-project 2 ships**   **Day 2 metrics**
#     **item 2 blocked**  **option 3 chosen**  **tier 2 users only**  **level 2 access**
#     **attempt 2 failed the gate**   **Python 3 ships**   **table 3 lists them**
#   MISSED, and should not be — a genuine count:
#     **2 and 3 were red**  **4 from the sweep**  **6 that survived**  **2 in total**
#     **3 or more rounds**
#
# `Stage 3` and `Sub-project 2` are THIS REPOSITORY'S OWN VOCABULARY (`dev-process.md` §
# Project-Specific). `SUBJECT_AFTER` holds `from of to in on at and or but that`, which are the
# words that most often follow a real count — so the two directions fight each other.
#
# ⚠ AND THE REVIEW'S PROPOSED ALTERNATIVE WAS MEASURED AND IS WORSE. "Require the counted noun
# to be a PLURAL or a known unit" still admits `users`, `access`, `ships`, `lists`, `metrics` —
# five of the ten false positives — and makes ALL FIVE false negatives worse, because none of
# them is followed by a plural. Nothing lexical separates `Stage 3` from `3 rounds`.
#
# ⭐ SO IT IS STATED AS A HEURISTIC RATHER THAN EXTENDED AGAIN. That is defensible for exactly
# one reason, and it is a property of this guard and not of the rule: `verdict` is WARN-ONLY
# unless `--strict` (measured: findings=3, strict=False -> rc=0; strict=True -> rc=1), and the
# population is rows a branch ADDS. A wrong answer here costs a dismissible warning on one new
# row. The witnesses above are kept as cases, so a future change that makes them worse is
# visible rather than discovered in round four.
#
# MEASURED 2026-10-07 over docs/backlog.md, re-derived with the SHIPPED functions of each
# revision rather than an ad-hoc reimplementation — which is how the previous version of this
# comment came to quote a denominator the file has never had:
#
#            revision             rows   fired   findings
#            1efc6c51 (pre-r2)     247     194         90
#            31e8768a (r2 fold)    247     195         90
#
# The finding COUNT is unchanged at 90. The MEMBERSHIP is not: rows #13 and #198 gain a figure,
# #212 loses one, and the findings exchange #212 for #198.
#
# ⟳⟳ THE PREVIOUS VERSION OF THIS COMMENT SAID "the firing rate is UNCHANGED at 46%
# (102/223 against 102/222)" AND "not one row changing state". Both were false. There is no
# 223-row revision of this file in range (247 at origin/master, ecc1460f, 1efc6c51 and
# 31e8768a) and no figure of 106; three rows do change state. The count was what I observed and
# the row-level claim was stronger than the measurement supported. Round 2's Claude half caught
# it by re-deriving, which is the only thing that catches this.
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
# ⛔ IT IS A HEURISTIC WITH A STATED BOUND — see the long note above `NUM_RE`, which lists the
# fifteen witnesses it gets wrong and why no lexical rule fixes them. ⚠ This paragraph used to
# claim "20 of 20 witnesses correct … firing rate UNCHANGED at 48% (106/223) and not one row
# changing state", and TWO of those figures do not reproduce: the file has 247 rows at every
# revision in range and three rows DO change state. Re-derived figures are in that note.
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

# ⟳ r2 Claude MEDIUM — `|` WAS ABSENT, so a pipe survived stripping and became the "counted
# noun": `single_digit_figures("**7**", " |")` returned `['7 |']`, which made ANY bold single
# digit ending a table cell a measurement. `docs/backlog.md` is a markdown table and is this
# guard's only corpus.
TOKEN_STRIP = "`*_([{)]}>,.:;!?\"'|"


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


def after_within_cell(row: str, at: int, limit: int = 40) -> str:
    """The row text after `at`, clipped at the end of ITS OWN table cell. PURE.

    ⟳ r2 Claude MEDIUM. The previous version took `row[at:at+40]` flat, and 40 characters cross
    a cell boundary: for `| 249 | **3** | failures in the sweep |` the counted noun came from the
    NEXT COLUMN. A figure's noun must come from the figure's own cell.

    ⛔ THE CELL RULE IS IMPORTED, NOT REWRITTEN. `check-docs.CELL_SPLIT` owns it and
    `check-features`, `check-plan-code` and `gen-backlog-page` already import it; this guard
    read raw characters instead, which is a second implementation of one rule — this
    repository's most-measured defect — and it is the direct cause of this finding.
    """
    nxt = _cell_split().search(row, at)
    end = min(nxt.start(), at + limit) if nxt else at + limit
    return row[at:end]


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
    # witnesses correct, **ZERO rows lose provenance**, firing rate unchanged at 46% (91/197, re-derived — ⟳ r3 Claude LOW: this said 90/195 at two sites and was stale; round 3's Codex half said so and the fold did not act).
    # ⟳⟳⟳ r2 Claude HIGH — THE VERB LIST IS GONE, NOT EXTENDED, and that is the point.
    #
    # Round 2's Codex half replaced a bare `\bHEAD\b` with `at|as of|measured …`; its Claude
    # half then showed the replacement had no `\b` and, worse, that no word list can carry this
    # rule at all. Eleven witnesses, all accepted as provenance by the verb form:
    #
    #     unverified at HEAD · unmeasured at HEAD · underived from HEAD   (inside-word: no \b)
    #     not verified against HEAD · nothing was observed at HEAD        (NEGATION)
    #     we have not derived this from HEAD · cannot be measured at HEAD (NEGATION)
    #
    # Prose asserting that NO measurement happened, read as proof that one did. A `\b` fixes the
    # first three; the negation half is not lexical, and a second word list to catch it is how
    # this rule reached its third consecutive round of findings.
    #
    # ⭐ SO IT IS STRUCTURAL NOW, WHICH IS WHAT EVERY OTHER ALTERNATIVE IN THIS REGEX ALREADY
    # IS: a commit must be backticked, a path:line must be backticked, a run id is `run <digits>`.
    # The HEAD prong was the only one that accepted bare English, and that is why it was the only
    # one that kept failing. Backticked or suffixed — the convention this repository already
    # writes refs in. MEASURED over `docs/backlog.md`: 15 of 15 witnesses correct, including all
    # six inside-word and all four negation cases, **ZERO rows lose provenance**, firing rate
    # unchanged at 46% (90/195). The rule got SHORTER.
    #
    # ⚠ THE COST, STATED: `measured at HEAD` without backticks no longer counts. That is
    # deliberate — it is indistinguishable, by any rule short of reading English, from
    # `we cannot look at HEAD`. Write `` `HEAD` `` and it counts.
    # ⚠⚠ AND THAT SENTENCE OVERSTATES WHAT THE RULE DOES — r4 Claude M2. The backtick requirement
    # applies to BARE `HEAD` only. A SUFFIXED HEAD needs no backticks, so the negation class the
    # paragraph above says was cured survives for every suffixed form. Measured at this commit:
    # `we cannot look at HEAD` -> False, but `we cannot look at HEAD~1` -> True,
    # `we have not derived this from HEAD~3` -> True, `nothing was observed at HEAD^` -> True.
    # ⛔ NOT INTRODUCED BY ANY FOLD — `git show e330ca80:` gives True for all three as well. What
    # was wrong is this comment, which claimed a cure it never had. Nothing lexical separates
    # `measured at HEAD~1` from `we cannot look at HEAD~1`; the honest statement is that the
    # backtick rule narrows the bare case and leaves the suffixed case lenient.
    # ⟳ r3 Codex MEDIUM — DIGITS ONLY AFTER `~` OR `^`. `` `HEAD[~^]?\d*` `` accepted
    # `` `HEAD123` ``, which `git rev-parse --verify` rejects, and which this branch INTRODUCED
    # (False at 31e8768a, True at e330ca80). `HEAD123` and `HEADS` are refused by both.
    # ⟳⟳ r4 Claude M2 — AND r3's STATED LIMIT HERE IS NOW SUPERSEDED, DELIBERATELY. It read:
    # "`HEAD~fiction` still matches — on its `HEAD~` prefix, which IS a valid ref, so that is a
    # ref followed by prose rather than a malformed token." That is a reasoned decision and not an
    # oversight, so it is overridden on the record rather than quietly: the same argument would
    # admit `HEAD~garbage` and `HEAD^nonsense`, because `\d*` matches the empty string and every
    # `HEAD~`-prefixed word therefore "contains a valid ref". The question the guard asks is
    # whether the token AS WRITTEN names a source, and `HEAD~fiction` does not. Direction of the
    # old answer was LENIENT — it accepted a row as sourced on a ref nobody can resolve.
    # ⚠ THE ORACLE, CORRECTED: "measured against git for each token" is sound for MALFORMED tokens
    # and UNSOUND for well-formed ones that merely do not resolve here. `HEAD^2` is valid syntax
    # (the second parent of a merge) and `git rev-parse --verify HEAD^2` gives rc=128 only because
    # HEAD is not a merge — verified both ways: `f559bdd4^2` rc=0, `HEAD^2` rc=128. So `HEAD^2`
    # and `HEAD~1^2` are ACCEPTED and cased as such, and resolvability is not the test.
    #
    # ⛔ AND THE SEMANTIC LIMIT, STATED RATHER THAN CLAIMED AWAY: a backticked ref names a
    # SOURCE; it does not establish that a measurement happened. `we cannot measure at `HEAD``
    # passes, and so does a `HEAD` appearing in a code span about git syntax. That is beyond any
    # pattern short of reading English, it is the same class as M2's single-digit heuristic, and
    # it is defensible for the same reason: `verdict` is warn-only unless `--strict`, over rows a
    # branch ADDS. The deleted verb list did not create this class and removing it did not cure
    # it — what it cured was eleven witnesses where prose asserting NO measurement counted as one.
    # ⟳ r4 Claude M2 — `\d*` MATCHES THE EMPTY STRING, so `HEAD~` followed by ANYTHING satisfied
    # this. Measured against `git rev-parse --verify` for each token: `HEAD~fiction`, `HEAD~1x` and
    # `HEAD^^zz` were accepted here and rejected by git (rc=128). The suffix must now be a run of
    # `~`/`^` with optional digits, followed by neither a word character nor another ref operator —
    # so a real suffix is required and a word glued to it refuses. The backticked arm was affected
    # too: this alternative matches INSIDE backticks, so `` `HEAD~fiction` `` was accepted as well.
    # ⟳ r5 Codex M4 — `\d` IS UNICODE AND THE TAIL LET A DECIMAL THROUGH. `\d` matches `١`
    # (Arabic-Indic) and `１` (fullwidth), so `HEAD~١` passed while `git rev-parse --verify`
    # rejected it (rc=128); and `HEAD~1.5` matched on its `HEAD~1` prefix because `.` is not in
    # `[\w~^]`. Digits are `[0-9]` now, and `(?!\.\d)` refuses a decimal tail while still allowing
    # `HEAD~1.` — a ref at the end of a sentence, which a blanket `.` exclusion would have broken.
    r"|`HEAD(?:[~^][0-9]*)?`|\bHEAD(?:[~^][0-9]*)+(?![\w~^])(?!\.\d)"
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
        if figures_in_span(DATE_RE.sub("", b), after_within_cell(row, m.end())):
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
    # ⭐ r2 Claude M3, at ROW level: the noun must come from the figure's OWN cell.
    ("⭐ r2: the counted noun may NOT come from the next table column",
     "| 249 | **3** | failures in the sweep |", 0),
    ("...and a bold single digit ending a cell is not a measurement",
     "| 249 | **7** |", 0),
    ("...while a noun in the SAME cell still supplies it",
     "| 249 | **3** failures in the sweep |", 1),
    ("...and a version identifier is not a count", "**v2 ships**", 0),
    # ── r2 Claude MEDIUM: the FIFTEEN witnesses the rule gets WRONG, kept as cases ───────────
    # ⛔ THESE ASSERT THE CURRENT, KNOWN-IMPERFECT BEHAVIOUR. They are here so a future change
    # that makes any of them worse is visible, and so the next reader meets the bound as data
    # rather than as a sentence. `a-stated-bound-outlives-its-hole`: if one of these starts
    # disagreeing because the rule improved, the red is the alarm and the case gets updated.
    ("⚠ KNOWN WRONG — `Stage 3` is this repo's own vocabulary and counts as a measurement",
     "**Stage 3 cloud-sync shipped**", 1),
    ("⚠ KNOWN WRONG — and so does `Sub-project 2`", "**Sub-project 2 ships**", 1),
    ("⚠ KNOWN WRONG — `item 2 blocked`", "**item 2 blocked**", 1),
    ("⚠ KNOWN WRONG — `tier 2 users only`", "**tier 2 users only**", 1),
    ("⚠ KNOWN WRONG — `Python 3 ships`", "**Python 3 ships**", 1),
    ("⚠ KNOWN WRONG — `Day 2 metrics`", "**Day 2 metrics**", 1),
    # ⛔ r4 Codex LOW — FIVE OF THE FIFTEEN WITNESSES HAD NO CASE, so the sentence below ("the
    # witnesses above are kept as cases") was false about a third of them, and a change that made
    # those five worse would have been invisible. Measured: 11 cases over 15 documented witnesses.
    # ⟳ r4 Claude M3 — THIS COMMENT SAID "FOUR" AND THE SAME COMMIT ADDED FIVE CASES. Four of them
    # are here (the COUNTED arm) and the fifth, `6 that survived`, is in the MISSED arm below. The
    # figure was wrong in a comment written to fix figures being wrong in comments, which is #261's
    # class inside its own remedy — and it is the sixth instance of that habit on this branch.
    ("⚠ KNOWN WRONG — `option 3 chosen`", "**option 3 chosen**", 1),
    ("⚠ KNOWN WRONG — `level 2 access`", "**level 2 access**", 1),
    ("⚠ KNOWN WRONG — `attempt 2 failed the gate`", "**attempt 2 failed the gate**", 1),
    ("⚠ KNOWN WRONG — `table 3 lists them`", "**table 3 lists them**", 1),
    ("⚠ KNOWN MISSED — `2 and 3 were red` is a genuine count and is not seen",
     "**2 and 3 were red**", 0),
    ("⚠ KNOWN MISSED — `4 from the sweep`", "**4 from the sweep**", 0),
    ("⚠ KNOWN MISSED — `2 in total`", "**2 in total**", 0),
    ("⚠ KNOWN MISSED — `3 or more rounds`", "**3 or more rounds**", 0),
    ("⚠ KNOWN MISSED — `6 that survived`, the fifth documented miss and the one that had no "
     "case until r4", "**6 that survived**", 0),
    # ⟳ r4 Claude L5 — RELABELLED. This read "⚠ KNOWN MISSED" while asserting **1**, i.e. that the
    # span IS counted. Those two cannot both be true: a miss is a 0. `1 in 60` is this repository's
    # own phrasing for a false-fire bound and IS a measurement, so counting it is the RIGHT answer
    # and this is an ordinary case, not a witness to a known defect. It also sat inside the block
    # headed "the FIFTEEN witnesses the rule gets WRONG" without being one of the fifteen, which is
    # how a correct case came to be filed as a known failure for two rounds.
    ("⭐ `1 in 60` IS a measurement — this repo's own phrasing for a false-fire bound — and is "
     "correctly counted, which is why it is not one of the fifteen witnesses above",
     "**1 in 60**", 1),
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
    # ── r2 Claude MEDIUM: TABLE-SHAPED rows, which this table had none of ───────────────────
    ("⭐ a pipe is a CELL DELIMITER, never the counted noun — any bold single digit ending a "
     "cell was a measurement before this",
     "**7**", " |", []),
    # ⚠ AND THE CLIP IS THE CALLER'S JOB, so a span-level case cannot see it. Handed
    # ` | rounds |` directly, this function legitimately reports `7 rounds`; what prevents that
    # on a real row is `after_within_cell`, which has its own direct cases below.
    ("...and handed a noun past the delimiter it still counts, because clipping happens in "
     "`after_within_cell`, not here",
     "**7**", " | rounds |", ["7 rounds"]),
]

PROV_CASES: list[tuple[str, str, bool]] = [
    ("a backticked commit-ish is provenance", "measured at `93e3133a`", True),
    ("a ref is provenance", "measured against origin/master", True),
    # ⟳ r2 Codex Medium: this case USED TO assert that bare `at HEAD` is provenance. It is not —
    # the same three words appear in `we cannot look at HEAD`, which names no source at all.
    # ── r2 Claude HIGH: the HEAD prong is STRUCTURAL, so these four cases changed shape ──────
    # ⟳ They used to assert that a measurement VERB near HEAD is provenance. Eleven witnesses
    # showed no word list can carry that, so the rule is now the one every other alternative
    # here already uses: backticked, or unambiguously suffixed.
    ("HEAD is provenance when it is BACKTICKED, as this repo writes every other ref",
     "measured at `HEAD`, the tree held 1,416", True),
    ("...or unambiguously suffixed, which cannot be prose", "measured against HEAD~1", True),
    ("...and `HEAD^2` likewise", "counted at HEAD^2", True),
    ("⛔ ...but a BARE HEAD is not, whatever verb sits beside it — the cost, stated",
     "measured at HEAD, the tree held 1,416", False),
    ("...and a bare `at HEAD` is NOT, because it is indistinguishable from prose about git",
     "the tree at HEAD held 1,416", False),
    ("⭐ r2 Codex: the semantic bypass — `we cannot look at HEAD` names no source",
     "**3 failures**; we cannot look at HEAD", False),
    ("...nor does `it fails to look at HEAD`", "it fails to look at HEAD when unreadable", False),
    # ⭐ the eleven r2 Claude H2 witnesses: six inside-word, four negation, one modal.
    ("⭐ r2 Claude H2: `unverified at HEAD` asserts NO measurement and was read as provenance",
     "**3 gaps**; unverified at HEAD", False),
    ("...and `unmeasured at HEAD` likewise", "**3 gaps**; unmeasured at HEAD", False),
    ("...and `underived from HEAD`", "**3 gaps**; underived from HEAD", False),
    ("⭐ r2 Claude H2, the NEGATION class a verb list cannot reach: `not verified against HEAD`",
     "**3 gaps**; not verified against HEAD", False),
    ("...and `nothing was observed at HEAD`", "**3 gaps**; nothing was observed at HEAD", False),
    ("...and `we have not derived this from HEAD`",
     "**3 gaps**; we have not derived this from HEAD", False),
    ("...and `the count cannot be measured at HEAD`",
     "**3 gaps**; the count cannot be measured at HEAD", False),
    # ── r1 Claude M3: `HEAD` as the SUBJECT is not provenance ────────────────────────────────
    # ⛔ THE WITNESS IS ROW #255'S OWN WORDING. A bare \bHEAD\b counted prose ABOUT git, so an
    # unqualified `**47 s**` passed because the sentence happened to contain the token.
    ("⭐ M3: prose ABOUT reading HEAD is not provenance for a figure beside it",
     "`--clear` REPORTS QUIET SUCCESS WHEN IT CANNOT READ HEAD and it cost **47 s** of CI",
     False),
    ("...but a BACKTICKED `HEAD` is a reader being told the ref", "measured at `HEAD`", True),
    ("...and a suffixed one is too, because `HEAD~1` can only be a ref",
     "measured against HEAD~1", True),
    ("...and a bare `as of HEAD` does NOT introduce a source any more — backtick it",
     "1,416 anchors as of HEAD", False),
    ("...while `as of `HEAD`` does", "1,416 anchors as of `HEAD`", True),
    ("...while HEAD merely NAMED mid-sentence does not", "we cannot read HEAD here", False),
    # ── r3 Codex MEDIUM: a MALFORMED HEAD token is not a ref ────────────────────────────────
    ("⭐ r3: `` `HEAD123` `` is not a ref — git rejects it, and this branch INTRODUCED it",
     "**47 s**; measured at `HEAD123`", False),
    ("...while `` `HEAD~1` `` is one", "**47 s**; measured at `HEAD~1`", True),
    ("...and `` `HEAD` `` plain is one", "**47 s**; measured at `HEAD`", True),
    ("...and `` `HEADS` `` is not", "**47 s**; measured at `HEADS`", False),
    # ── r4 Claude MEDIUM: `\d*` matches EMPTY, so `HEAD~` + anything was a ref ──────────────
    # ⛔ AND THE CLASS MEMBER WAS PRINTED IN THE EVIDENCE OF THE FINDING THAT WAS FOLDED: r3's
    # Codex half listed `'at `HEAD123`' True` and `'at HEAD~fiction' True` two lines apart; the
    # fold acted on the first and not the second. Instance, not class, with the class visible in
    # the same four lines of the review being folded.
    ("⭐ r4: `HEAD~fiction` is not a ref — `git rev-parse --verify` gives rc=128",
     "measured at HEAD~fiction", False),
    ("...and backticking it does not make it one, because this alternative matches INSIDE "
     "backticks and so the backticked arm carried the same hole",
     "measured at `HEAD~fiction`", False),
    ("...and `HEAD~1x` is not a ref either — a digit followed by a word is not a suffix",
     "measured at HEAD~1x", False),
    ("...nor `HEAD^^zz`, the third mismatch and the one the review did not list",
     "measured at HEAD^^zz", False),
    ("...while `HEAD^^` IS a ref and still passes, so the fix refused the glued word and not "
     "the repeated operator",
     "measured at HEAD^^", True),
    # ⚠ THE ORACLE IS SYNTAX, NOT RESOLVABILITY, AND r3's COMMENT CONFLATED THEM. `HEAD^2` is
    # valid git syntax — the second parent of a merge — and `git rev-parse --verify HEAD^2` gives
    # rc=128 here only because HEAD is not a merge commit. Verified both ways at this commit:
    # `f559bdd4^2` rc=0, `HEAD^2` rc=128. So "measured against git for each token" is a sound
    # oracle for MALFORMED tokens and an unsound one for well-formed tokens that do not resolve,
    # and this case pins the accept so a future tightening cannot quietly refuse a real ref form.
    ("⚠ r4: `HEAD^2` is ACCEPTED — valid ref syntax whose rc=128 here means `HEAD has no second "
     "parent`, not `bad token`",
     "measured at HEAD^2", True),
    ("...and so is `HEAD~1^2`, a compound suffix", "measured at HEAD~1^2", True),
    # ── r5 Codex MEDIUM: `\d` is UNICODE, and the tail assertion allowed a decimal ──────────
    ("⛔ r5: `HEAD~\u0661` (Arabic-Indic digit) is not a ref — `\\d` matched it, `[0-9]` does not",
     "measured at HEAD~\u0661", False),
    ("⛔ r5: ...nor `HEAD~\uff11` (fullwidth digit)", "measured at HEAD~\uff11", False),
    ("⛔ r5: ...nor `HEAD~1.5` — it matched on its `HEAD~1` prefix because `.` is not a word char",
     "measured at HEAD~1.5", False),
    ("⚠ r5: ...while `HEAD~1.` at the END OF A SENTENCE still counts, which is why the rule "
     "refuses `.` followed by a DIGIT and not `.` itself",
     "measured at HEAD~1.", True),
    ("⚠ r3 STATED LIMIT: a backticked ref names a SOURCE and does not prove a measurement "
     "happened — this passes, and no pattern short of reading English refuses it",
     "**47 s**; we cannot measure at `HEAD`", True),
    ("...and row #255's own wording stays refused, which is what M3 was filed for",
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

    total = (7 + len(BOLD_CASES) + len(SINGLE_DIGIT_CASES) + len(PROV_CASES) + len(ROWSET_CASES)
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
        # ⚠ OFFSET 13 IS DERIVED, not guessed: `BOLD_RE` ends `**3**` there in all three rows.
        # My first attempt used 19 and 17 and the suite returned ' lures here ' — a reminder
        # that a hand-typed offset is a second thing that can be wrong.
        ("⭐ after_within_cell stops at the figure's own cell boundary (r2 Claude M3)",
         after_within_cell("| 249 | **3** | failures here |", 13), " "),
        ("...and returns the rest of the cell when the noun IS in it",
         after_within_cell("| 249 | **3** failures here |", 13), " failures here "),
        ("...and a DIFFERENT row at a DIFFERENT offset yields its own cell tail, so no case "
         "can tell `at` from a constant",
         after_within_cell("| 7 | **2 gaps** remain |", 16), " remain "),
        ("...and `limit` is a parameter, so a narrower window clips sooner than the cell does",
         after_within_cell("| 249 | **3** failures here |", 13, limit=4), " fai"),
        ("...and an ESCAPED pipe is not a delimiter, which is why the rule is imported rather "
         "than restated",
         after_within_cell("| 249 | **3** a \\| b |", 13), " a \\| b "),
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
