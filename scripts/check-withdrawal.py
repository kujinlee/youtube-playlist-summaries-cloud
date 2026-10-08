#!/usr/bin/env python3
"""A figure corrected in one document must not still stand, unmarked, in another.

WHY THIS EXISTS — backlog #257, and it was the most mechanical of six rules left as prose.
------------------------------------------------------------------------------------------
The rule: *when a claim is withdrawn, enumerate every site it reached before correcting any of
them.* It was written on 2026-10-06 and broken **within the hour**, by its author:

  * `visibility` *"governs the picker, NOT whether a model works"* was refuted and corrected in
    `docs/process-rationale.md` while the same sentence stood in `docs/plugins.md` and in newly
    added dashboard prose — PR #367 round 2, Medium 3.
  * *"the 0.142.5 cache no longer exists to compare against"* stood in **three** documents as the
    stated reason for softening a claim, and was false in all three.

Both were caught by a reviewer reading, never by a machine — and the row's own `Fails if` is a
search. That is what makes leaving it as prose the clearest of the six mistakes.

⛔ AND THE SEARCH MUST NOT BE LINE-BASED. Measured 2026-10-07 (backlog #258): a wrapped phrase
defeats line-oriented `grep`, and `grep -z` returned **0** against a file holding **2**. A
line-based implementation of this rule would read as enforced and catch nothing. So the matcher
is **imported from `scripts/find-claim.py`**, not rewritten here — a second implementation of one
rule is this repository's most-measured defect (17 instances, `check-vocabulary-collisions.py`).

WHAT IT DOES
------------
For every figure REMOVED by this branch's `docs/` diff and not re-added in the same hunk, it
builds a SIGNATURE — the number plus up to two words either side — and searches the rest of
`docs/` for that signature, whitespace-insensitively. A hit is a SURVIVOR: the figure was
corrected in one place and still stands in another.

⚠ WARN-ONLY, DELIBERATELY. Exit 0 even with survivors unless `--strict`. Backlog #56 measured
what happens to a blocking gate that fires on a docs-only mismatch: it gets switched off. The
value here is the report, and a report nobody disabled beats a gate everybody did.

WHAT IT EXEMPTS, AND WHY IT MUST
--------------------------------
This repository is **full of deliberately superseded figures** — `⟳` trails, review documents,
dated explainer pages — and a rule that fires on those is red forever, which is the same #56
death. Two exemptions, both narrow and both stated:

  * PATH: `docs/reviews/` and `docs/explainers/` are dated artifacts. A review document quoting
    the figure it found wrong is the system working.
  * CONTEXT: a hit whose surrounding text carries a history marker (`⟳`, `CORRECTED`,
    `superseded`, `was`, `earlier`, `previously`, `no longer`, `historical`) is a past-tense
    trail, not a live claim.

⛔ THE LIMIT, STATED RATHER THAN HIDDEN. This checks FIGURES, because the row's own `Fails if`
says *"a figure is corrected in one document and its superseded value survives"*. The
`visibility` instance above was a CLAIM, not a figure, and this guard would NOT have caught it.
Saying so is the point: a caveat headed "stated rather than hidden" that is wrong is worse than
none. A survivor whose neighbouring words were reworded is also missed — the signature binds on
context, and context that moved does not match.

EXIT CODES: 0 = ok, or survivors in warn mode · 1 = survivors under `--strict` · 2 = CANNOT RUN.

USAGE
    python3 scripts/check-withdrawal.py --base origin/master
    python3 scripts/check-withdrawal.py --base origin/master --strict
    python3 scripts/check-withdrawal.py --self-test        # 172 cases, pure, no git

⚠ THE COUNT ABOVE IS VERIFIED BY RUNNING IT (`scripts/check-selftest-counts.py`).
"""

from __future__ import annotations

import argparse
import collections
import importlib.util
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# Directories whose whole job is to record what was once believed.
EXEMPT_DIRS = ("docs/reviews/", "docs/explainers/")

# A hit sitting near one of these is a past-tense trail, not a live claim. Kept deliberately
# small: every token added here is a way for a real survivor to hide.
# ⟳ r1 Claude M4 — THE LIST IS SPLIT, BECAUSE ITS MEMBERS ARE NOT EQUALLY GOOD EVIDENCE.
# `⟳` and `superseded` are written BY an author performing a correction. `"was "` is an English
# past-tense auxiliary, and in a 360-character window (CONTEXT_CHARS either side) it is simply
# common prose. Measured over every figure occurrence in non-exempt `docs/`:
#
#     figure occurrences                         47,988
#     exempted, every marker window-wide         12,559  (26.2%)
#     `"was "` alone, as first marker             7,620  (15.9%)
#
# This prong became load-bearing in the same fold that tightened the corrected-form prong, and
# that fold ADDED a token ("quoted") to a list whose own comment says "every token added here is
# a way for a real survivor to hide". In a warn-only tool a false NEGATIVE is the expensive
# direction — a suppressed survivor is invisible, a spurious warning is merely dismissed — so a
# marker that exempts more than every other combined needs a tighter binding than co-occurrence.
#
# STRONG markers still hold anywhere in the window: an author who wrote `⟳` nearby is correcting
# something. WEAK markers must sit in THE SAME SENTENCE as the figure, which is what "near" was
# always meant to approximate. MEASURED: exemption falls 26.2% -> 15.1%, un-suppressing 5,297
# occurrences, of which `"was "` accounts for 4,940.
STRONG_MARKERS = (
    "⟳", "CORRECTED", "corrected", "superseded",
    "previously", "no longer", "historical", "stale", "used to",
)

# ⚠ EVERY MEMBER HERE IS ORDINARY PROSE that happens to be past-tense, so each is required to
# share a sentence with the figure it exempts. "quoted" joined in the r1 fold; "earlier" and
# "was " predate it. Together they were 8,108 of the 12,559 exemptions.
WEAK_MARKERS = ("was ", "(was", "earlier", "quoted")

# Retained as the union so a reader (and `check-vocabulary-collisions`) still finds one name for
# the concept. ⛔ NOT the thing `is_history_context` tests — it tests the two halves separately,
# and a future edit that collapses this back into one membership test re-opens M4.
HISTORY_MARKERS = STRONG_MARKERS + WEAK_MARKERS

# A figure worth tracking: at least two digits, optional thousands separators and decimals.
# ⚠ One digit is excluded ON PURPOSE. "2" occurs in every document in this repository, and a
# signature built around it is noise — the guard would report hundreds of survivors and be
# switched off within a day (#56).
#
# ⟳ r1 Claude L3 — THIS PATTERN AND `check-provenance.NUM_RE` WERE BYTE-IDENTICAL AND MUST NOT
# BE AGAIN. L3 was right that a second implementation of one rule is this repository's
# most-measured defect (17 instances), and wrong that the answer here is one owner: the two
# guards read DIFFERENT TEXT, so they need different rules. The exclusion above is justified by
# UNBOLDED PROSE, which is what this guard scans. `check-provenance` scans only inside a
# `**…**` span an author chose to emphasise, so there the same exclusion made #256's own third
# motivating defect invisible — M2. The justification travelled with the bytes and not with the
# reasoning, which is how one correct rule became one correct and one wrong.
#
# ⛔ The difference is ASSERTED BY A CASE ("the two figure rules are DELIBERATELY different"),
# so a future de-duplication that collapses them fails loudly instead of silently reinstating
# M2. That is the one thing a comment cannot do.
NUMBER_RE = re.compile(r"\d[\d,]*\.?\d+|\d{2,}")

CONTEXT_WORDS = 2       # words of context either side of the figure, forming the signature
CONTEXT_CHARS = 180     # window around a hit searched for a history marker


def _check_provenance():
    """Import the sibling guard, to ASSERT its figure rule differs from this one (r1 Claude L3).

    Read-only and only from the suite: this guard does not depend on that one at runtime. The
    import exists so the DIFFERENCE between two deliberately-different rules has a falsifier.
    """
    spec = importlib.util.spec_from_file_location(
        "check_provenance", REPO / "scripts/check-provenance.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _find_claim():
    """Import the matcher rather than reimplement it (backlog #258 owns the rule)."""
    spec = importlib.util.spec_from_file_location("find_claim", REPO / "scripts/find-claim.py")
    if spec is None or spec.loader is None:          # pragma: no cover - unreachable
        raise RuntimeError("cannot load scripts/find-claim.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ── the rule, pure ───────────────────────────────────────────────────────────

def signature_of(line: str, number: str, context_words: int = CONTEXT_WORDS) -> str:
    """The figure plus up to `context_words` words either side. PURE.

    A bare number is not a claim — `1,414` alone matches a hundred unrelated sentences. The
    signature is what makes a survivor identifiable, and it is also this guard's main limit:
    a survivor whose surrounding words were reworded will not match.
    """
    # ⛔ WHOLE TOKENS. Round 1 Codex Medium: slicing at the number's offset split the TOKEN that
    # contains it, so `the sweep holds **1,414 anchors** today` yielded the signature
    # `holds ** 1,414 anchors** today` — tokens joined by `\s+`, demanding whitespace between
    # `**` and `1,414` that the source does not have. The signature found ZERO matches in its
    # own source line, and `--strict` returned rc=0 over a live survivor.
    tokens = line.split()
    idx = next((k for k, tok in enumerate(tokens) if number in tok), -1)
    if idx < 0:
        return number
    lo = max(0, idx - context_words) if context_words else idx
    hi = idx + context_words + 1 if context_words else idx + 1
    return " ".join(tokens[lo:hi])


def removed_figures(diff_text: str) -> list[tuple[str, str, str, tuple[str, ...]]]:
    """(path, old_line, figure, replacements) per figure a hunk removes and does not re-add. PURE.

    Pairing is per HUNK, not per line: a correction routinely rewraps, so the figure may leave
    one line and its replacement arrive on another. Comparing hunk-wide is what survives that.

    ⭐ `replacements` — the figures the same hunk ADDED — is what makes the exemption principled
    rather than a growing word-list. MEASURED 2026-10-07 over the seven live survivors of
    `1,414` in this repository: the marker list alone classified 4 correctly and produced **2
    false positives**, and BOTH of those sat within 180 characters of the replacement `1,416`.
    Text that names the new figure beside the old one is already doing the correction. Adding
    this prong took the sample to 1 true positive, 0 false positives.
    """
    out: list[tuple[str, str, str, tuple[str, ...]]] = []
    path = ""
    removed: list[str] = []
    added: list[str] = []

    def flush() -> None:
        if not removed:
            return
        added_blob = "\n".join(added)
        removed_blob = "\n".join(removed)
        # ⛔ A figure present on BOTH sides is UNCHANGED, not a replacement. Treating it as one
        # is a FAIL-OPEN, and it was measured: a synthetic correction of `1,414 -> 1,416` on a
        # line also containing `59` made `59` an exemption token, and the real survivor — whose
        # text also says "59 manifests" — was silently exempted. The known-positive run reported
        # 0 where it had to report 1. Found 2026-10-07 by running the guard against a survivor
        # it was built to catch, not by reading it.
        repls = tuple(dict.fromkeys(
            n for n in NUMBER_RE.findall(added_blob) if n not in removed_blob))
        for line in removed:
            for n in NUMBER_RE.findall(line):
                if n not in added_blob:
                    out.append((path, line, n, repls))

    for raw in diff_text.split("\n"):
        if raw.startswith("+++ b/"):
            flush(); removed, added = [], []
            path = raw[6:].strip()
        elif raw.startswith("@@"):
            flush(); removed, added = [], []
        elif raw.startswith("-") and not raw.startswith("---"):
            removed.append(raw[1:])
        elif raw.startswith("+") and not raw.startswith("+++"):
            added.append(raw[1:])
    flush()
    return out


def is_exempt_path(path: str) -> bool:
    """True for directories whose job is recording superseded belief. PURE."""
    return any(path.startswith(d) or f"/{d}" in path for d in EXEMPT_DIRS)


# ⟳ r2 Codex HIGH — A BARE `\n` IS NOT A SENTENCE BOUNDARY, and treating it as one made this
# guard's answer depend on where a line happens to WRAP. Measured witness:
#
#     the sweep holds 1,414 anchors today (was wrong).     -> suppressed, rc=0
#     the sweep holds\n1,414 anchors today (was wrong).     -> SURVIVOR, rc=1
#
# Same claim, same marker, opposite verdicts. Wrap-insensitivity is the entire premise of
# backlog #258 and of `find-claim`, which this file IMPORTS precisely so a wrapped claim is
# still found — and then the sentence rule reintroduced the sensitivity one function away.
#
# A sentence therefore ends at `.!?`, at a PARAGRAPH break, or where a markdown BLOCK begins
# (a table row, heading, quote or list item) — those are genuinely separate statements, and two
# table rows must never share a sentence. MEASURED over 47,990 figure occurrences in non-exempt
# docs/: weak-marker suppressions 2,330 -> 3,688, median sentence 96 -> 180 chars against a
# 360-char window, and the table-row fixture still refuses to leak a marker between rows.
#
# ⛔ AND THE DIRECTION OF THAT CHANGE IS TOWARD **MORE** SUPPRESSION, which this file's own
# docstring calls "the expensive direction" — r2 Claude MEDIUM, and the previous version of this
# note stated the 2,330 -> 3,688 rise as evidence the prong was "narrowed, not deleted" without
# saying which way it moved. It is a 1,358-hit INCREASE in exemptions, and 1,418 of the new
# suppressions reach across a line break.
#
# ⚠ The trade is still net positive and the review agreed: it sampled the new suppressions and
# found the majority are GENUINE WRAPS the old rule got wrong, and could not produce a live
# false negative. But five constructed shapes are plainly separate statements that now share a
# sentence — a colon lead-in, two unterminated prose lines, a fenced code block, a markdown hard
# break (two trailing spaces), and a `1)` list marker where only `1.` is modelled. Those are
# known-open, not fixed, and recovering them is three more alternatives in a regex that has
# three. Filed rather than left implied.
# ⟳ r3 Codex HIGH — THE COLON LOOPHOLE HAD A LIVE INSTANCE, which upgrades it from the
# "acknowledged, constructed" list round 2 left it on. `docs/dashboard-entries.md:10440`:
#
#     ⚠ The API was used *instead of* `fly deploy` deliberately:
#     the running image is ...
#     **177 commits** since, **6 touching shipped code** ...
#
# A lead-in ending in `:` is a separate statement from what follows it, and `was` in the lead-in
# was exempting the current claim below. Measured: changing only `deliberately:` to
# `deliberately.` flipped the verdict from rc=0 to rc=1 reporting the survivor.
#
# Three boundaries added, closing three of the five shapes round 2's Claude half listed: the
# colon lead-in, a markdown HARD break (two trailing spaces), and `1)` as well as `1.`.
# MEASURED over **49,240** figure occurrences across the **393** files `docs_files()` returns:
# weak suppressions 3,688 -> 3,630 (58 fewer false negatives), median sentence **184 -> 181**,
# and a genuine wrap is still ONE sentence.
#
# ⟳ r3 Claude MEDIUM — THE FIRST VERSION OF THIS LINE SAID 48,046 AND 180 -> 177, measured with
# `docs/**/*.md` instead of calling `docs_files()`. That probe saw **390 of 393 files**. The
# -58 delta reproduces exactly and the conclusion is unchanged, but the population was mine and
# not the guard's — `measure-the-population-the-code-actually-sees`, and the fix is to call the
# function rather than to re-describe what it does.
#
# ⚠ TWO SHAPES REMAIN OPEN AND ARE NOT CLAIMED FIXED: two unterminated prose lines (genuinely
# ambiguous — that IS what a wrap looks like), and a fenced code block, which needs fence state
# a regex cannot carry. Both were constructed, not live.
# ⛔ TWO RULES, TWO QUESTIONS — and r6 Claude M1 was right about the defect and wrong about the fix.
# It found that `mask_inline_code` recognised only a BLANK line as a paragraph end, so it whitened
# the `\n` before a list item and erased the boundary `SENTENCE_SPLIT` adds for exactly that (37
# disagreeing inputs in 29 shapes, every one containing `\n* `). Real defect. Its proposed fix was to
# share ONE constant between the two — and MEASURED against cmark and markdown-it-py, that is wrong,
# because the two constants answer different questions:
#
#   next line starts    paragraph ENDS (both parsers)    SENTENCE_SPLIT wants a boundary
#   `- `  `* `  `+ `              yes                                 yes
#   `1. ` `1) `                   yes                                 yes
#   `2. ` `2) `                   **NO** — an ordered item can         yes — it reads as a new
#                                 interrupt a paragraph ONLY           statement whatever its
#                                 if it starts with 1                  number
#   `| `                          **NO** — a GFM table needs a         yes — a table row is its
#                                 delimiter row                        own statement (r2 Codex)
#   `    - ` (4 spaces)           **NO** — indented code               yes
#
# So `SENTENCE_SPLIT` keeps its own broader rule for PROSE, and the mask gets `PARA_END`, derived
# from what the parsers actually do. ⤳ One rule per QUESTION is the honest form of one-rule-one-place
# here; collapsing them would have made `` `anchors\n2) 1,414` `` stop being code, which both
# parsers say it is.
SENTENCE_SPLIT = re.compile(
    r"(?<=[.!?])\s+"                               # ordinary end of sentence
    r"|\n\s*\n"                                    # a paragraph break
    r"|(?<=:)\r?\n"                                 # a colon lead-in ENDS a statement — `\r?` because
                                                   # under CRLF the char before `\n` is `\r`, not
                                                   # `:`, so this boundary never fired and the
                                                   # figure's sentence absorbed the lead-in. Found
                                                   # folding r7 Claude H2, whose own point is that a
                                                   # CR fix in ONE alternative is a fix in one
                                                   # alternative. The other four handle `\r` already:
                                                   # `\s+` and `\s*` both match it.
    r"|(?<=\s\s)\n"                                # a markdown hard break
    r"|\n(?=\s*(?:[|#>]|[*+-]\s|\d+[.)]\s))"      # a markdown block start; `1)` too
)


BACKTICK_RUN = re.compile(r"`+")
# ⛔⛔ WHAT ENDS A PARAGRAPH IS A BLOCK-PARSING QUESTION, AND THIS IS THE SEVENTH ROUND OF
# RE-DERIVING IT BY HAND. Measured against cmark AND markdown-it-py (they agree on all 20 shapes
# below), because r6 proved a hand-read of the spec is not good enough here:
#
#   next line after the opener's line          paragraph ENDS?   why
#   blank                                            yes
#   `- b`  `* b`  `+ b`                              yes          a non-empty bullet interrupts
#   `* ` / `1. ` with NOTHING after                  NO           an EMPTY item cannot interrupt
#   `- ` with nothing after                          yes          ⚠ NOT the list rule — a bare `-`
#                                                                 line is a SETEXT underline
#   `1. b`  `1) b`                                   yes
#   `2. b`  `2) b`                                   NO           only a `1` may interrupt
#   `# b` … `###### b`                               yes
#   `####### b` (seven)  `#b` (no space)             NO
#   `> b` / `>b` / `>> b` after PROSE                yes
#   `> b` after a `>` line (CONTINUATION)            NO           the quote's paragraph continues
#   `>> b` after a `>` line (DEEPER)                 yes
#   `> # b` / `> - b` after a `>` line               yes          a block start INSIDE the quote
#   `   - b` (≤3 spaces)                             yes
#   `    - b` (4 spaces)                             NO           indented code
#
# ⛔ THE QUOTE RULE CANNOT BE A REGEX: it depends on the PREVIOUS line, and Python has no
# variable-length lookbehind. So this is a function over line pairs, not a pattern.
#
# ⚠ `---` IS NOT CLEARED, and r7's Low caught me claiming it was. A BARE `---` line after a
# paragraph is a SETEXT UNDERLINE and both parsers end the paragraph there. My earlier measurement
# put the marker on the SAME LINE as the figure (`---1,414`), so it never tested a bare `---` — the
# probe was wrong, not the parsers. The `[-=]+[ \t]*$` clause above covers it.
#
# ⭐⭐⭐ READ THE PATTERN BEFORE THE NUMBER. This note has claimed "zero lenient disagreements" FOUR
# times. Every one of the first three was FALSIFIED, each time because the corpus I measured was the
# corpus I had thought of:
#
#   claim                              falsified by                     the real figure
#   "0 over 380 shapes"   (r7)         r7 Claude, generated 1,400       196 lenient
#   "0 over 1,400 shapes" (r7 fold)    r8's quote-nesting shapes        42-48 lenient
#   "0 over ~1,920 shapes" (r8 fold)   MY OWN corpus, re-run at commit   16 lenient
#   "0 over 1,620 shapes" (r8 fold)    MY OWN INSTRUMENT'S INDEX        0 held, EVERY
#                                      — and r8 Claude B1, separately   OTHER figure wrong
#   "0 over 1,620 + 196"  (now)        — not yet —                      ?
#
# ⛔⛔ ROW FOUR IS A DIFFERENT KIND OF FAILURE FROM THE FIRST THREE, AND THE MORE DANGEROUS KIND.
# The first three were grids too small. Row four is the INSTRUMENT: the generator scored each shape
# with `mask_inline_code(doc)[doc.index("\n")]` — the FIRST newline in the document — while one of
# its three leads was `"> intro\nlazy"`, whose own newline sits BEFORE the span opener, where the
# mask can never whiten it. For 540 of 1,620 shapes the instrument therefore always answered "the
# paragraph ends here", and under the classification that scores `ok` or `noisy` and NEVER lenient.
# ⤳ **So the instrument was LENIENT-BLIND on a third of the grid** — the expensive direction — and
# ⛔⛔ r9 Codex M2 — AND THE EXPLANATION I FIRST WROTE HERE WAS WRONG IN THE DANGEROUS DIRECTION.
# It said a wrong index "cannot produce a false CLEAN claim, only a false COST figure, so nothing
# ever looked alarming". That is self-contradictory: being lenient-BLIND *is* reporting 0 lenient
# where lenient shapes exist, which is exactly a false clean claim. Measured — 14 r7 shapes whose
# genuine LENIENT result scores `ok` at the old index, e.g. `'> intro\nlazy `a\n~~~\nb` x'`, where
# all three parsers end the paragraph, the r7 mask preserves the document's first newline and
# whitens the span's. ⤳ So the reason reviewers read past it was NOT that it failed safely; it is
# that the only visible symptom was a noise figure nobody was auditing. Found twice independently, by
# re-running at commit time and by r8's Claude half, agreeing to the unit. The fix is to score at
# the SPAN's own newline, `doc.index("\n", doc.index("`a"))`.
#
# ⤳ ROW THREE IS THE USEFUL ONE, AND IT IS WHY THIS CORPUS IS RE-RUN RATHER THAN CITED. It was
# falsified before the commit that would have shipped it, by re-generating the shapes instead of
# repeating the figure — and the 16 were one class the grid had never contained: a FENCED CODE BLOCK.
# `BLANK_OR_BLOCK` had clauses for thematic breaks, setext, ATX and HTML and none for ``` or ~~~, and
# `ANY_BLOCK_ISH` was missing them too, which is why four survived the first clause.
#
# ⤳ So the honest statement is not the number, it is this: **every "zero" here has been a statement
# about a grid, and three of four grids were too small.** Measured now, cmark-gfm and markdown-it in
# BOTH dialects agreeing, over markers × indents × {LF,CRLF} × {prose, quoted, `> > ` spaced-nested,
# `>>` nested, 3-space-indented quote, lazy-prefixed} = 1,620 shapes, PLUS a second corpus of
# 7 list containers × 14 middles × {LF,CRLF} = 196 shapes, which the grid above cannot express
# because its only container spelling is a quote (that blind spot WAS r8 Claude H1), and a third of
# 294 shapes for the classes r9 found (span opening BELOW the marker, TABBED marker runs,
# INTERLEAVED quote/list containers). ⚠ r9 Codex M3 — THE DENOMINATOR IS NOT THE SHAPE COUNT: of
# the 1,620 grid shapes, FOUR are excluded because the parsers disagree (strict CommonMark has no
# tables), so 1,616 are adjudicated. A parser split is not a claim about this code, and counting it
# either way would be a different measurement than the one reported:
#
#   version                                         LENIENT   noisy   total   list LENIENT
#   `3b49db97` (r7 as shipped)                          228      88     316     138 of 196
#   r8, quote depth tracked per line                     30      88     118     138 of 196
#   r8, depth from the PARAGRAPH's first line            28      34      62     138 of 196
#   r8 + the fence clause in `BLANK_OR_BLOCK`             8      34      42     130 of 196
#   r8 + the fence clause in BOTH predicates              0      34      34     130 of 196
#   r8 + the LIST CONTENT COLUMN (r8 Claude H1)           0      34      34       0 of 196
#   r9 + TAB COLUMNS and the INDENT fallback               0      34      34       0 of 196
#   r9 Claude + the LAZY column, the quote COMPARISON       0      34      34       0 of 196
#   r10 + ANY ordered number closes an open item            0      34      34       0 of 196
#
# ⛔ r10 — AND THE ONE REMAINING CLASS IS NOW A SINGLE QUESTION, WHICH IS THE POINT OF
# SAYING SO. r9 Claude left FOUR lenient classes; two were comparison bugs (closed), and of
# the two it judged structural, `0*1[.)]` turned out to be LOCALLY fixable after all: a line
# below an open item's content column is CLOSING the item, and every ordered number does
# that. Measured 672 -> 72 with zero added noise, and a boundary corpus running the pad to
# col+2 puts it at 368 -> 48 with zero noise at any pad. ⤳ THE 72 AND THE 48 ARE THE SAME
# CLASS AS THE ONE LEFT: a block start between the OUTER and INNER content column, where
# `cont` is ONE INTEGER and the answer is a SET of columns. That is the whole of what now
# needs #267's decision — one class, not two.
#     and the indent fallback DELETED as dead code
#
# ⚠ THE GRID AND THE LIST CORPUS HAVE READ 0/34 AND 0/0 FOR FOUR CONSECUTIVE VERSIONS, AND
# THAT IS THE WARNING, NOT THE REASSURANCE — three of those versions had a LENIENT class
# running into the hundreds that neither corpus can express. A corpus that stops moving has
# stopped being evidence; what moved the measurement every time was a NEW corpus.
#
# ⛔ AND THE LIST COLUMN DID NOT CLOSE THE CLASS — r9 Codex H1 and H2. Taking `cont` from the
# paragraph's first line is wrong whenever the span opens BELOW the item's marker, because the
# walk-back breaks AT the marker line and the continuation it lands on has no marker left to read;
# and `m.end() - i` counted CHARACTERS, so a tab in the marker run undercounted its own column. Both
# were LENIENT on the shape the first fix was written for. Measured over 294 shapes of the three
# classes no earlier corpus could express:
#
#   version                     LENIENT   noisy    per class (lenient)
#   r8 (the list column alone)      170       0    below-marker 130, tabbed 14, interleaved 26
#   r9 (columns + indent)             3       0    tabbed 1, interleaved 2
#
# ⛔⛔ THAT SENTENCE SAID "THREE RESIDUAL" AND WAS WRONG IN BOTH HALVES — r9 Claude B1, and it is
# the sixth consecutive round in which a figure here was a property of the grid that produced it.
#   · THE COUNT WAS NOT THREE. Three was the residual of the 294-shape corpus this file wrote for
#     itself. Over 3,902 adjudicated shapes the residual at `47e33e71` was 1,199, in FOUR classes.
#   · AND THE TWO IT NAMED WERE MISATTRIBUTED, which is the half that misdirects. It called them
#     "interleaved containers nested deeper than one level" and handed them to #267 — a structural
#     redesign that is the owner's call. They are a SINGLE quote around a SINGLE item, where
#     `list_content_column` already returns the right column and the defect was the COMPARISON:
#     `d2 > d` forgets the depth already stripped from the line, so it is dead at every quote depth
#     >= 1. One token (`d + d2 > depth`) closed all ten, free in both directions. ⤳ Parking a
#     comparison bug as a design question is how eight of nine rounds handed the next round a
#     false floor.
#
# What this fold closed, and what is genuinely left — each figure re-derived on its own corpus:
#
#   class                                                     LENIENT before   after
#   C1  the span opens on a LAZY continuation (196)                      130       0
#   C2  a list inside ONE quote, block start a nested `>` (10)            10       0
#   C5  a legal 1-3 space TOP-LEVEL paragraph indent (192)           0 / 132 noisy  0 / 0
#   C3  a block start between the OUTER and INNER column (120)            72      72
#   C4  an ordered marker other than `1` inside an item (672)            672     672
#
# ⛔⛔ C3 AND C4 ARE NOT LOCALLY FIXABLE, AND THAT IS THE POINT. C3: `cont` is ONE integer, and
# CommonMark ends the item's paragraph for a block start at ANY column from the OUTER container's
# content column up — no scalar can express a SET of columns, so the repair is a stack of open
# container columns, i.e. block-structure parsing. It bites this file's own fixture: `- - - ` is
# pinned at column 6 and is LENIENT at 4 and 5. C4: `0*1[.)]` is right at top level, where only
# `1` can interrupt a paragraph, and wrong inside an item, where ANY ordered number CLOSES it —
# which is r8 Claude H1's mistake (a rule correct at top level, wrong in a container) for the
# THIRD consecutive round. Both are recorded on #267 as evidence; the decision is the owner's.
#
# ⚠ THE SECOND COLUMN IS THE ONE TO READ, AND IT FALLS: noise goes 88 → 34 and never rises. ⛔ r8
# Claude B1 — the version of this paragraph that shipped at `d6967caa` said the count "ROSE from
# 186", cited "216 REMAINING" ten lines under a table reading 108, and disowned the 216 as a figure
# from "the previous version of this note". All three were wrong: 216 appears NOWHERE in r7 (which
# carried 132), so the sentence disowning it as old was about a figure THIS commit introduced. That
# is the exact failure mode this note exists to prevent, committed inside the note that states it.
#
# ⤳ What the last three rows DO show is that the two fence clauses and the list content column each
# cost ZERO noise — 34 before and 34 after, and 0 noise on the list corpus — which is unusual here
# and is the reason to state it. ⚠ But "free" is a property of THESE corpora, not of the clauses:
# r8 Claude M3 found a real noise class outside them (a backtick fence's info string may not contain
# a backtick, so ```` ```a`b ```` is NOT a fence and the paragraph continues, where this clause
# declines the span — 18 of 132 info-string shapes). Noisy, so the regex is left alone; recorded so
# the next round does not have to find it again.
#
# The three r8 Codex Highs (spaced nesting, a table unreachable inside a quote, quote state lost
# after one lazy line) and r8 Claude's H1 (a block start at a LIST ITEM's content column) are each
# verified fixed by name, and 24 named witnesses accumulated across rounds 4-8 all agree with both
# parsers. ⚠ THE 34 THAT REMAIN ARE ALL NOISY — the mask declines a span a parser keeps, costing a
# dismissible warning — which is the deliberate trade: this guard's docstring says a false negative
# is the expensive direction.
#
# ⚠ A SHIPPED NOISE CLASS, RECORDED RATHER THAN SILENTLY CARRIED — r8 Claude L3. In the `d < depth`
# branch `ANY_BLOCK_ISH` is matched against the RAW next line, which still begins with `>` when
# `0 < d < depth`, so every depth DECREASE inside a quote ends the paragraph where CommonMark
# continues it lazily (`'> > intro `a\n> q\nb` x'`: all three parsers say the paragraph does not
# end; this predicate says it does). ⛔ The obvious repair is NOT free and that is why it is not
# made: matching the stripped remainder instead moves a 6,000-shape multi-line corpus from
# LENIENT=114/noisy=851 to LENIENT=181/noisy=506 — the total improves while the expensive direction
# gets worse, which is this note's own named trap.
#
# ⛔ EXPECT THE NEXT ROUND TO FALSIFY THIS TOO, and treat that as the process working. What would
# make the claim finally trustworthy is not a bigger grid of my own devising but the thing #267 names:
# asking a real parser at RUNTIME instead of re-deriving its answers here.
#
# ⚠⚠ AND THE DESIGN QUESTION IS STILL THE OWNER'S — filed as backlog #267. SEVEN rounds have refined
# this predicate; each refinement was individually right and each was followed by another shape. The
# structural options are (a) depend on a real CommonMark parser, which CI would have to install, or
# (b) keep the conservative direction and stop tracking the spec at all. This fold happens to land
# close to (b) by measurement rather than by decision, and saying so is the honest version.
# ⛔ EVERY `$`-ANCHORED ALTERNATIVE CARRIES `\r?` — r7 Claude H2. r6's CR fix went into ONE of the
# five, so under CRLF a bare setext underline and an empty ATX heading were still missed, and both
# failed LENIENT. A character class fixed in one alternative is fixed in one alternative.
# ⛔ r10 — INSIDE AN ITEM, ANY ORDERED NUMBER CLOSES IT, not only `1`. `BLANK_OR_BLOCK`'s
# `0*1[.)]` is correct where it was measured (r7 H1): at top level only `1` may INTERRUPT a
# paragraph. A line indented BELOW an open item's content column is not interrupting that
# paragraph — it is CLOSING the item, and every ordered number does that.
CLOSES_ITEM = re.compile(r"[ \t]{0,3}\d{1,9}[.)][ \t]+\S")


BLANK_OR_BLOCK = re.compile(
    r"[ \t\r]*$"                                # blank
    r"|[ \t]{0,3}(?:[-*+][ \t]+\S"              # a NON-EMPTY bullet
    r"|(?:[-*_][ \t]*){3,}\r?$"                  # a THEMATIC BREAK — `***`, `___`, `* * *` (r7 H1)
    r"|[-=]+[ \t]*\r?$"                          # a setext underline (`-` alone, `=` alone)
    r"|0*1[.)][ \t]+\S"                          # an ordered item: only the NUMBER ONE interrupts,
                                                 # and `01.`/`001)` ARE one — measured (r7 H1)
    r"|#{1,6}(?:[ \t]|\r?$)"                     # an ATX heading, at most six hashes
    r"|(?:`{3,}|~{3,})"                      # ⛔ A FENCE — three or more backticks OR
                                             # tildes, measured: two do not interrupt, and
                                             # the `[ \t]{0,3}` above is what excludes the
                                             # four-space-indented one. ⚠ A fence WITH an
                                             # INFO STRING was measured as splitting the two
                                             # parsers, and ⛔ r8 Claude M3: THAT WAS MY ORACLE,
                                             # NOT THE PARSERS. The oracle stripped `<pre>` with a
                                             # literal tag, so cmark's `<pre lang="ruby">` escaped
                                             # the strip; with `<pre\b[^>]*>` the split goes 84 → 0
                                             # and all three parsers AGREE the fence ends the
                                             # paragraph. The clause takes the CORRECT side here,
                                             # not a defensible guess — the question has an answer
    r"|<[a-zA-Z!/?]"                             # ⚠ AN HTML BLOCK, CONSERVATIVELY. CommonMark type 6
                                                 # is a ~60-tag list and `<span>` is NOT in it, so
                                                 # this over-fires on inline tags. That lands in the
                                                 # NOISY direction (a dismissible warning) and
                                                 # removes five LENIENT shapes; embedding the tag
                                                 # list here is the #267 design question, not a fold.
    r")")
def _column(chunk: str, start: int) -> int:
    """Width of `chunk` in TAB-EXPANDED columns, starting from column `start`.

    ⛔ r9 Codex H2 — `m.end() - i` counted CHARACTERS. A tab advances to the next multiple-of-four
    tab stop, so `-\t- ` is six columns wide and not four, and the undercount left a block start at
    the real content column invisible again — LENIENT, on the shape the first fix was for.
    """
    col = start
    for ch in chunk:
        col = (col // 4 + 1) * 4 if ch == "\t" else col + 1
    return col


LIST_MARKER = re.compile(r"[ \t]{0,3}(?:[-*+]|\d{1,9}[.)])[ \t]+")


def list_content_column(rest: str) -> int:
    """How far a block start may be indented and still interrupt, from a paragraph's FIRST line.

    ⛔ r8 Claude H1 — `[ \t]{0,3}` is the right cap at TOP LEVEL, where four spaces is indented
    code. Inside a LIST ITEM it is not: the block-start column is the item's CONTENT column, which
    is 4 for `- - `, 5 for `- 1. ` and 6 for `- - - `. Every block start at that column was
    invisible to BOTH predicates, so the mask whitened the newline and the span absorbed the
    figure — LENIENT, the expensive direction.

    ⤳ THIS IS THE SAME MOVE THE QUOTE FIX MADE, ONE CONTAINER OVER. r8's Codex half taught
    `paragraph_ends_between` to carry the open paragraph's QUOTE DEPTH as state instead of
    comparing adjacent lines; a list item's content column needs carrying for exactly the same
    reason, and the predicate knowing about `>` but not about `- ` is why this survived eight
    rounds. Measured on a 196-shape list corpus (7 containers × 14 middles × {LF, CRLF}), both
    parsers in both dialects agreeing:

        container (opener, content column)      LENIENT before   after
        `- `      (2)                                  0           0
        `1. `     (3)                                  0           0
        `  - `    (4)                                 26           0
        `- - `    (4)                                 26           0
        `- 1. `   (5)                                 26           0
        `- - - `  (6)                                 26           0
        `1. 1. `  (6)                                 26           0

    ⚠ COLUMNS 2 AND 3 CONTRIBUTE ZERO *ON THAT CORPUS*, and the earlier version of this note drew
    a bolded rule from it — "the defect is exactly CONTENT COLUMN >= 4". ⛔ r9 Claude M1: FALSE, and
    a mutation proved it while all 163 cases stayed green. `if cont >= 4:` adds 24 LENIENT shapes,
    because the strip runs on a remainder whose QUOTE MARKER HAS ALREADY BEEN REMOVED, so the two
    columns it takes off are not the two `BLANK_OR_BLOCK`'s own cap would have covered. Witness,
    `cont` = 2 and load-bearing: `'- > - first\n  >   the count was `wrong:\n  >     # h\n…'`.
    ⤳ The honest statement is narrower: on a corpus of SIMPLE containers at top level, columns 2
    and 3 contribute nothing. Inside a quote they do.

    ⚠ DIRECTION, STATED RATHER THAN HIDDEN: stripping the container indent can only make MORE
    lines match a block start, so this fails NOISY (a dismissible warning) and never lenient.
    Measured: noise on the list corpus is 0 before and 0 after, and the 1,620-shape grid in the
    measurement note is UNMOVED at 0 lenient / 34 noisy — at top level `cont` is 0 and every
    clause here is a no-op.

    ⚠ IT IS STILL AN APPROXIMATION, and backlog #267 is the place that says so: interleaved
    containers (`> - > `) are read only as far as the leading run of list markers goes. The
    structural answer remains a real CommonMark parser.
    """
    col, i = 0, 0
    while True:
        m = LIST_MARKER.match(rest, i)
        if not m:
            # ⛔ r9 CLAUDE: THIS USED TO FALL BACK TO THE BARE INDENT, and the fallback is now DEAD
            # CODE — measured 0 of 2,466 shapes distinguish it from `return col`. r9 Codex H1 added
            # it because the span may open on a line BELOW the marker, where no marker is left to
            # read; the walk-back in `paragraph_ends_between` now carries `cont_seen` across the
            # continuation lines INCLUDING the one that breaks it, which is where the marker lives,
            # so it answers that case more generally and this answered it twice. ⤳ Two mechanisms
            # for one property, and the spare one was UNKILLABLE: its mutation survived the whole
            # suite because the other mechanism supplied the same answer. Deleted rather than
            # shipped, and its manifest entry is RETIRED WITH ITS SUBJECT.
            # ⚠ AND IT WAS NOT MERELY REDUNDANT: returning the bare indent made `cont` 3 for a
            # legal 1-3 space paragraph indent at TOP LEVEL, where this function's docstring
            # promises 0 — 132 noisy shapes (r9 Claude M2). The promise is structural again now.
            return col
        col = _column(rest[i:m.end()], col)
        i = m.end()


QUOTE_MARKER = re.compile(r"[ \t]{0,3}>")
# ⛔ A GFM TABLE INTERRUPTS A PARAGRAPH, BUT ONLY WITH ITS DELIMITER ROW — r7 Claude M1, and it is
# the one rule here that needs TWO lines of lookahead rather than a line pair. The comment above
# excludes a bare `| ` correctly ("a GFM table needs a delimiter row") and then stops one line early:
# when the delimiter row IS present, the table starts. ⚠ THE ORACLES SPLIT HERE and the split is the
# answer rather than a problem: strict CommonMark has no tables, so `markdown-it` in commonmark mode
# keeps the span, while cmark-gfm AND markdown-it in gfm mode both end the paragraph. This repo's
# markdown is rendered by GitHub, so GFM is the operative dialect and the lenient reading was wrong
# in the one that matters.
TABLE_DELIM = re.compile(r"[ \t]{0,3}\|?[ \t]*:?-+:?[ \t]*(?:\|[ \t]*:?-+:?[ \t]*)*\|?[ \t]*\r?$")
# Anything that COULD begin a block, used only for lazy continuation inside a quote (r7). Broader
# than `BLANK_OR_BLOCK` on purpose: an empty marker cannot interrupt a fresh paragraph but it does
# close a quote, because a non-`>` line may continue one only as plain paragraph text.
ANY_BLOCK_ISH = re.compile(r"[ \t\r]*$|[ \t]{0,3}(?:[-*+=_>#<~`]|\d+[.)])")




def quote_depth(line: str) -> tuple:
    """`(blockquote depth, the line with its markers stripped)`. PURE. r8 Codex H1.

    ⛔ `> > ` IS DEPTH TWO. The previous version matched `(>+)` — CONTIGUOUS markers only — so a
    SPACED nested quote read as depth ONE and everything inside it was classified against the wrong
    level. Measured: `> > the count was …` masked straight through a setext boundary and exempted a
    live figure, while the contiguous `>>` twin was handled correctly. One space, opposite answers.
    """
    depth, i = 0, 0
    while True:
        m = QUOTE_MARKER.match(line, i)
        if not m:
            return depth, line[i:]
        depth += 1
        i = m.end()
        if i < len(line) and line[i] in " \t":
            i += 1


def paragraph_ends_between(text: str, start: int, end: int) -> bool:
    """True when a paragraph boundary lies in `text[start:end]`. PURE. r7 Codex H1, r8 Codex H1-H3.

    ⛔⛔ IT TRACKS THE OPEN PARAGRAPH'S QUOTE DEPTH AS STATE rather than comparing adjacent lines.
    The pairwise version had three LENIENT defects that are all the same mistake, and each was
    invisible to the other two (r8 Codex H1, H2, H3):

      · H1 — a SPACED nested quote (`> > `) read as depth one, so the inner block structure was
        tested against the outer level;
      · H2 — the table lookahead sat in a branch the quote cases returned before, so a table INSIDE
        a quote was never reached;
      · H3 — after ONE lazy-continuation line the previous line carries no marker, so the quote
        state was gone and an empty `* ` was judged by the FRESH-paragraph rule (which permits it)
        instead of the quote rule (which closes on it).

    ⤳ So: strip the markers, carry `depth` ACROSS lines, and test the REMAINDER. Which markers end
    a paragraph is the measured table above; what the earlier versions scored is the corpus note
    above that. Both come from cmark-gfm and markdown-it(gfm), never from a reading of the spec.
    """
    nl = text.find("\n", start)
    if nl == -1 or nl >= end:
        return False
    # ⛔ THE PARAGRAPH'S DEPTH IS SET BY ITS FIRST LINE, NOT BY THE LINE THE SPAN OPENS ON — r8, and
    # it is H3 one level deeper. A span may open on a LAZY continuation line, which carries no `>`
    # while the paragraph is still inside the quote; starting from that line read depth 0 and judged
    # everything after it by the fresh-paragraph rule. Measured: all 42 remaining lenient shapes on a
    # 1,980-shape corpus were exactly this one construction. So walk BACK to the paragraph's first
    # line — lazy lines inherit the container — and take the greatest depth seen on the way.
    line_start = text.rfind("\n", 0, nl) + 1
    depth, _ = quote_depth(text[line_start:nl])
    scan, cont_seen = line_start, 0
    while scan > 0:
        prev_start = text.rfind("\n", 0, scan - 1) + 1
        pd, prest = quote_depth(text[prev_start:scan - 1])
        if BLANK_OR_BLOCK.match(prest):
            cont_seen = max(cont_seen, list_content_column(prest))
            break                              # that line starts a block, so the paragraph begins here
        depth = max(depth, pd)
        cont_seen = max(cont_seen, list_content_column(prest))
        scan = prev_start
    _, first_rest = quote_depth(text[scan:text.find("\n", scan)])
    cont = max(cont_seen, list_content_column(first_rest))     # ⛔ r8 Claude H1 / r9 Claude H1:
                                               # `cont_seen` is what makes a LAZY continuation work
    while nl != -1 and nl < end:
        nxt_end = text.find("\n", nl + 1)
        nxt = text[nl + 1:nxt_end if nxt_end != -1 else len(text)]
        d, rest = quote_depth(nxt)
        below_item = False
        if cont:
            k, c = 0, 0
            while k < len(rest) and rest[k] in " \t" and c < cont:
                c = (c // 4 + 1) * 4 if rest[k] == "\t" else c + 1
                k += 1
            if c >= cont:
                rest = rest[k:]                # ⛔ r8 Claude H1 / r9 H2 — tab-expanded columns
            else:
                below_item = True              # ⛔ r10 — it did NOT reach the content column
            d2, rest2 = quote_depth(rest)      # a `>` can sit AT that column, past QUOTE_MARKER's
            if d + d2 > depth:                         # 3-space cap — that was the last 10 of the 130
                return True
            rest = rest2
        if d > depth:
            return True                        # the quote OPENS or DEEPENS
        if d < depth:
            # Fewer markers continues the paragraph ONLY as plain prose (lazy continuation);
            # anything that could begin a block closes the quote instead. ⛔ `depth` is NOT
            # re-derived here — that is H3: one lazy line must not erase the quote the paragraph
            # is still inside.
            if ANY_BLOCK_ISH.match(nxt):
                return True
        elif BLANK_OR_BLOCK.match(rest):
            return True
        elif below_item and CLOSES_ITEM.match(rest):
            return True                        # ⛔ r10 — BELOW an item's column, any number closes it
        elif "|" in rest and nxt_end != -1:
            after_end = text.find("\n", nxt_end + 1)
            after = text[nxt_end + 1:after_end if after_end != -1 else len(text)]
            _, after_rest = quote_depth(after)
            if "-" in after_rest and TABLE_DELIM.match(after_rest):
                return True                    # a header is a table only WITH its delimiter row
        nl = text.find("\n", nl + 1)
    return False


def backtick_escaped(text: str, pos: int) -> bool:
    """True when the character at `pos` is backslash-escaped. PURE. r5 Codex H1.

    An ODD number of preceding backslashes escapes; an even number is itself escaped backslashes.
    `\\`code`` is a literal backslash followed by a REAL delimiter, and treating it as escaped
    would stop masking a genuine span.
    """
    n = 0
    i = pos - 1
    while i >= 0 and text[i] == "\\":
        n += 1
        i -= 1
    return n % 2 == 1


def mask_inline_code(text: str) -> str:
    """`text` with whitespace INSIDE inline code spans replaced by `x`. PURE, LENGTH-PRESERVING.

    ⛔ r4 Codex M1 — WITHOUT THIS, WHERE A LINE WRAPS DECIDES THE VERDICT. Three of
    `SENTENCE_SPLIT`'s alternatives are newline-based, and a newline inside an inline code span
    satisfied them, so the span was cut in half and the history marker before it fell outside the
    sentence. Measured on the shipped functions at `ea857e4a`, same prose, same figure:

        the count was `anchors: 1,414` today        -> marker 'was ', suppressed, rc=0
        the count was `anchors:\n1,414` today       -> marker '',     SURVIVOR  docs/live.md:2
        the count was `anchors  \n1,414` today      -> marker '',     SURVIVOR
        the count was `anchors\n1) 1,414` today     -> marker '',     SURVIVOR

    The first and the rest are the SAME SENTENCE differing only in where it wraps, which is a
    property of the editor and not of the claim. A boundary inside code is never a sentence
    boundary, because code is not prose.

    ⚠ LENGTH-PRESERVING IS THE WHOLE TRICK: every offset in the masked copy is the same offset in
    the original, so `sentence_around` finds bounds on the mask and slices the ORIGINAL. Nothing
    downstream sees an `x`.

    ⚠ THREE BOUNDS, STATED RATHER THAN HIDDEN — and the third was MISSING from this list until
    r4 Claude L1, which is the failure mode a caveat headed *stated rather than hidden* has:
      · Runs of THREE OR MORE backticks are left alone — those are fences, and the fenced-code
        case is deferred. ⟳ r5 Claude L1 — AND THE OLD JUSTIFICATION HERE WAS WRONG ABOUT WHICH
        WAY THAT DEFERRAL FAILS. It said widening the mask to fences "risks pairing an unbalanced
        fence and masking prose". The risk is real but it is not the live one: dropping 3+ runs
        from the list leaves the SINGLE backticks INSIDE a fenced block free to pair with each
        other, so the mask already reaches into fenced code — measured document-level over the 393
        files, **597** span-level disagreements with cmark across **121** files (`anchors.md`,
        `deploy.md`, `m1.4-finishup-checklist.md`, …). The deferral fails toward masking MORE, not
        less, which is the same lenient direction this list warns about. No verdict change was
        measured for it; a case below pins the behaviour so a future fence-aware rewrite moves it
        deliberately. ⤳ Knowing where fences are is the same question as knowing where spans are,
        and the answer is a parser — see the note at the end of this list.
      · An UNCLOSED inline span masks nothing — and ⟳ r5 Codex M1, it no longer stops the scan
        either. `break` here meant one stray backtick disabled masking for every LATER genuine
        span, turning a suppressed figure into a false SURVIVOR; the opener is skipped instead.
      · ⟳ r5 Codex H1 — AN ESCAPED BACKTICK IS NOT A DELIMITER, and A SPAN CANNOT CONTAIN A BLANK
        LINE. Both were measured against cmark: `the count was \\`wrong: … \\`` and the same text
        with a paragraph break are PROSE, and pairing their backticks masked the prose between
        them, inheriting a `was` that belongs to a different statement. Both failed LENIENT — a
        live stale figure reported as history, which is the expensive direction.
      ⚠ THIS IS THE THIRD ROUND OF CORRECTIONS TO THIS ONE FUNCTION (r4 L1 pairing, r4 L2 scope,
        r5 H1+M1 escapes/blank lines/unmatched openers). Every fix has been a markdown rule
        re-derived by hand. The structural answer is to ask a real CommonMark parser where the
        code spans are rather than to keep adding rules, and that belongs to the Phase 6 review
        backlog #262 already arms — recorded here so the next reader meets the pattern, not just
        the latest rule.
      · ⟳ IT MASKS EVERY `SENTENCE_SPLIT` ALTERNATIVE, NOT ONLY THE THREE NEWLINE ONES. Masking
        whitespace inside a span also stops `(?<=[.!?])\\s+` firing there, so a version string in
        code no longer ends a sentence. Measured: `the count was `v1. 2` and 1,414 today` gave
        marker `''` (a SURVIVOR) before and `'was '` now. That is the RIGHT answer — a period
        inside `v1. 2` is not a sentence end — but it is a behaviour change beyond the three
        boundaries this function was written for, and r4 Claude L2 is that it went unstated.
        A case pins it, so the widening is asserted rather than incidental.
    """
    # ⛔ AN OPENER PAIRS WITH THE NEXT RUN OF EQUAL LENGTH, SKIPPING OTHERS — r4 Claude L1. The
    # first version compared only ADJACENT runs and advanced past the opener on a mismatch, which
    # could pair two runs that are not a span and mask the prose between them. Witness, measured:
    #
    #   'a `b`` c `the count was wrong:\n1,414 anchors` d'   runs = [1, 2, 1, 1]
    #
    # Adjacent-only pairing joined runs 2 and 3 and masked `wrong:\n`, so the colon boundary never
    # fired and the figure kept the `was` in front of it — SUPPRESSED. Equal-length pairing joins
    # runs 0 and 2 (run 1 is span CONTENT), leaving run 3 unclosed and `wrong:` as prose, so the
    # boundary fires and the figure is a SURVIVOR, which is the right answer. The old direction was
    # LENIENT, and leniency here is what hides a stale figure.
    # Each run is (start, end, escaped). Escaping is resolved PER ROLE below, not by dropping the
    # run — see the two rules in the docstring.
    runs = [(mt.start(), mt.end(), backtick_escaped(text, mt.start()))
            for mt in BACKTICK_RUN.finditer(text) if len(mt.group(0)) <= 2]
    out = list(text)
    i = 0
    while i < len(runs):
        s, e, esc = runs[i]
        # ⛔ AN ESCAPED FIRST BACKTICK TRUNCATES THE OPENER, IT DOES NOT DELETE THE RUN — r6 Codex
        # M1. `\\``` is a LITERAL backtick followed by a REAL one-backtick opener, and both cmark
        # and markdown-it-py open a span there. r5 discarded the whole run, so the span's newline
        # went unmasked and the figure after it became a false SURVIVOR. Measured:
        #
        #   the count was \\``v1:\n2` and 1,414 today     parsers: span = `v1: 2`     r5: no span
        #
        # ⚠ I REASONED ABOUT THIS CASE WHILE WRITING r5 AND DID NOT WRITE IT DOWN — and I called it
        # "conservative", which it is not: it produces a spurious warning, not a missed one. A bound
        # thought about and left unstated is indistinguishable from one never seen.
        open_start = s + 1 if esc else s
        open_len = e - open_start
        if open_len < 1:
            i += 1                      # a lone escaped backtick is a literal and delimits nothing
            continue
        # ⛔ AND ESCAPING IS IRRELEVANT TO A CLOSER (r5 Claude H1): inside an open span the scan is
        # purely lexical, so the FULL run closes it however many backslashes precede it.
        j = i + 1
        while j < len(runs) and (runs[j][1] - runs[j][0]) != open_len:
            j += 1
        if j >= len(runs):
            i += 1
            continue
        cs = runs[j][0]
        # A code span cannot cross the end of a PARAGRAPH. `paragraph_ends_between` owns that
        # question and is measured against two real parsers — see its table (r6 Claude M1, r7 Codex
        # H1). It takes the whole `text` and offsets, not a slice, because the block-quote rule needs
        # the line BEFORE the newline and a slice starting mid-span does not contain it.
        if paragraph_ends_between(text, e, cs):
            i += 1
            continue
        for k in range(e, cs):
            if out[k].isspace():
                out[k] = "x"
        i = j + 1
    return "".join(out)


_MASKED_DOCS: dict = {}


def masked_of(text: str) -> str:
    """`mask_inline_code(text)` for a whole document, memoised BY VALUE. r5 Claude H2, r6 Claude H1.

    Every hit in one document shares one mask, and masking a large file per-hit would turn a cheap
    guard into a slow one.

    ⛔⛔ IT USED TO KEY ON `(id(text), len(text))`, AND THE SENTENCE DEFENDING THAT WAS FALSE IN THE
    ONE WAY THAT MATTERS. It read: "keyed on `id(text)` AND length so a recycled id cannot serve the
    wrong document". The length is not an independent discriminator — it is IMPLIED by the
    collision. `id()` in CPython is the object's address and the allocator reuses an address for an
    object OF THE SAME SIZE, so same-length is exactly what a recycled id has in common. Measured on
    the real entry point, two equal-length documents driven through `main()` alternately in one
    process, with the memo instrumented to recompute and compare on every hit:

        40 main() runs:  misses=7  hits=33  WRONG=18     cache size at end: 7

    **18 of 33 hits served a mask computed from a DIFFERENT document**, and seven misses for forty
    runs is the tell on its own. ⚠ The r6 Codex half cleared this as sound, correctly but too
    narrowly: `blobs` does hold every document for the whole run, so no collision is possible WITHIN
    one `main()`. The cache was module-global and never cleared, so entries outlived the list that
    justified them — the hazard is ACROSS invocations, and `--self-test` alone left 7 entries behind.
    ⚠ And the length check added to `sentence_around` the same round cannot catch it: a stale mask
    from a same-length document has exactly the right length and the wrong content.

    ⤳ SO THE KEY IS THE TEXT ITSELF. A dict keyed by value cannot serve another document's mask, a
    string caches its own hash after the first lookup, and the masking it guards is already O(n).
    `main` also clears the memo on entry, which bounds it to one run's documents — the scope this
    docstring claimed all along.
    """
    key = text
    got = _MASKED_DOCS.get(key)
    if got is None:
        got = mask_inline_code(text)
        _MASKED_DOCS[key] = got
    return got


def _memo_key_probe() -> tuple:
    """`(mask is right, id-key entry ignored, a 2nd equal-length doc gets its own)`. r6 Claude H1.

    ⛔ DETERMINISTIC, BECAUSE AN id-COLLISION IS NOT. Reproducing the real collision needs the
    allocator to recycle an address, which no case can require. So this plants the entry an
    id-KEYED memo would hit — `(id(text), len(text))` — and asserts the memo ignores it. Under the
    old key that planted value is returned; under the current key it cannot be.

    ⚠ A verdict-level case CANNOT replace this: measured over the real entry point the collision
    served 18 wrong masks in 33 hits and the verdict did not flip in that pair, so rc is green for a
    real reason while the input is wrong. The mask is the input to every sentence boundary, so what
    stood between this and an arbitrary verdict was only that no case's answer depended on it.
    """
    text = "`a b` and the count was 1,414 today"
    other = "xa bx and the count was 1,414 today"      # SAME LENGTH, different content
    assert len(text) == len(other)
    _MASKED_DOCS.clear()
    masked_of(text)                                   # populate under the real key
    _MASKED_DOCS[(id(text), len(text))] = "X" * len(text)   # what an id-keyed memo would serve
    served = masked_of(text)
    # ⛔ AND A SECOND, EQUAL-LENGTH DOCUMENT GETS ITS OWN MASK. This is the property the whole fix
    # is about, and passing a different document is also what makes `masked_of`'s parameter VARIED —
    # `check-fixture-variation` reads argument EXPRESSIONS and refused one call site spelled `text`
    # at both places, which is the fourth time it has caught exactly that on this branch.
    return (served == mask_inline_code(text),
            served != "X" * len(text),
            masked_of(other) == mask_inline_code(other))


def sentence_around(window: str, at: int, *, masked: str) -> str:
    """The sentence of `window` containing offset `at`. PURE.

    ⛔⛔ `masked` IS KEYWORD-ONLY WITH NO DEFAULT, AND THAT IS THE WHOLE FIX FOR r5 Claude H2.
    It must be `mask_inline_code` applied to the WHOLE DOCUMENT and then sliced to the same bounds
    as `window` — never `mask_inline_code(window)`. A window is a raw ±CONTEXT_CHARS slice, so it
    routinely BEGINS INSIDE a code span; the first backtick in it is then a closer whose opener is
    outside, which inverts the parity of every backtick after it. The mask pairs that orphan with
    the next genuine opener and masks the PROSE between them.

    ⛔ MEASURED over 75,076 windows built from the 393 files `docs_files()` returns: masking the
    FRAGMENT changed `history_marker` in **205** windows, and in **205 of 205** the change was a
    SUPPRESSION the document-level rule calls a SURVIVOR. 0 of 205 went the other way. So the
    fragment version's entire live effect on verdicts was false suppression — the direction that
    hides a stale figure — while three rounds of corrections each refined a CommonMark micro-rule.

    ⤳ Length preservation is what makes the fix exact: `mask_inline_code` replaces characters
    one-for-one, so an offset in the masked document is the same offset in the document, and the
    same window bounds slice both. The sentence is sliced from `window` (real text); only the
    BOUNDS come from `masked`.

    ⛔ NO DEFAULT, for the reason `figure_at` has none a few functions down: a default would let a
    caller silently fall back to the fragment behaviour this exists to abolish, and this file has
    already paid once for a parameter whose default was the old behaviour. Omitting it is a
    TypeError — loud, at the call site. A caller whose `window` IS the whole document passes
    `mask_inline_code(window)`, and says so.

    r1 Claude M4's instrument. Sentence rather than a second character budget because "near" in
    the original comment meant "in the same statement", and a tighter character window would be
    one more number with no reason behind it.
    """
    # ⛔ BOUNDS ON THE MASK, SLICE THE ORIGINAL (r4 Codex M1). `mask_inline_code` is
    # length-preserving, so every offset below indexes both strings identically.
    if len(masked) != len(window):
        # A mask of a different length cannot share offsets, so every bound below would be wrong
        # about a different string. Loud, not silently approximate.
        raise ValueError(f"masked is {len(masked)} chars and window is {len(window)}; "
                         f"sentence_around needs the SAME bounds sliced from the masked document")
    bounds = [0] + [m.end() for m in SENTENCE_SPLIT.finditer(masked)] + [len(window)]
    for i in range(len(bounds) - 1):
        if bounds[i] <= at < bounds[i + 1]:
            return window[bounds[i]:bounds[i + 1]]
    return window


def suppression_line(counts: "collections.Counter") -> str:
    """One line naming what each marker suppressed, or "" when nothing was. PURE.

    ⟳ r1 Claude M4. The run reported `ok — none of them survives elsewhere` and a reader could
    not tell that from *five survivors each within 180 characters of the word "was"*. Extracted
    rather than inlined in `main` so it has a case: the live corpus currently suppresses NOTHING,
    so an inline version would have been unreachable code asserting its own correctness.
    """
    if not counts:
        return ""
    detail = ", ".join(f"{k!r}x{v}" for k, v in counts.most_common())
    return f"  suppressed as history: {sum(counts.values())} hit(s) — {detail}"


def figure_offset_in_hit(hit_text: str, figure: str) -> int:
    """Where the FIGURE sits inside the matched signature. PURE.

    ⛔ r2 Codex HIGH — THE SIGNATURE IS NOT THE FIGURE, and conflating them reinstated M4.
    `signature_of` returns the figure plus up to `CONTEXT_WORDS` words either side, so the
    match can begin a sentence earlier than the number it is about. The caller passed the
    SIGNATURE's offset as `figure_at`, and the witness is two commits in a real repository:

        The status was green. count 1,414 anchors today     -> suppressed by 'was ', rc=0
        The status is  green. count 1,414 anchors today     -> SURVIVOR, rc=1

    The figure's own sentence holds no marker in either case. One word in the PREVIOUS sentence
    decided it, which is exactly the cross-sentence suppression M4 exists to stop.

    The figure never contains whitespace, so it cannot be split by a wrap inside the match;
    a figure the match somehow does not contain falls back to 0, which is the old behaviour and
    no worse than it.
    """
    i = hit_text.find(figure)
    return i if i >= 0 else 0


def figure_offsets_in_hit(hit_text: str, figure: str) -> list[int]:
    """EVERY offset at which `figure` occurs inside the matched signature. PURE.

    ⛔ r3 Codex HIGH — `find` TAKES THE FIRST OCCURRENCE, so a repeated figure inherited the
    first one's exemption. The witness is two commits in a real repository:

        was 1,414. 1,414 anchors today      -> suppressed by 'was ', rc=0

    The first `1,414` is in a sentence carrying `was `; the second is in a live claim with no
    marker at all, and the run reported `2 figure(s) corrected, none survives`. The review notes
    that `rfind` merely picks a DIFFERENT occurrence rather than preserving identity — so the
    answer is not to choose one. A hit is exempt only when EVERY occurrence of the figure in it
    is exempt, which errs toward reporting a survivor: in a warn-only tool a false negative is
    the expensive direction, and this is the cheap one.
    """
    out, i = [], hit_text.find(figure)
    while i >= 0:
        out.append(i)
        i = hit_text.find(figure, i + 1)
    return out or [0]


def figure_offset_in_window(start: int, span: int = CONTEXT_CHARS) -> int:
    """Where the hit sits inside `window_around`'s result. PURE.

    ONE owner for the arithmetic, because `window_around` CLIPS at 0: near the top of a document
    the hit is at `start`, not at `span`, and a caller that assumed the centre would hand
    `history_marker` the wrong sentence for exactly the documents whose first lines carry the
    correction notices.
    """
    return min(start, span)


def history_marker(window: str, figure_at: int, *, masked: str) -> str:
    """The marker exempting this hit, or "". PURE — and it NAMES the marker rather than
    answering yes/no, so the live run can report what each one suppressed (r1 Claude M4).

    `masked` is the document-level mask sliced to `window`'s bounds — see `sentence_around`, whose
    docstring records the 205-of-205 false suppressions a fragment mask produced.
    """
    for mark in STRONG_MARKERS:
        if mark in window:
            return mark
    sentence = sentence_around(window, figure_at, masked=masked)
    for mark in WEAK_MARKERS:
        if mark in sentence:
            return mark
    return ""


def is_history_context(window: str, corrected_forms: tuple[str, ...] = (),
                       *, figure_at: int, masked: str) -> bool:
    """True when the text around a hit is a past-tense trail rather than a live claim. PURE.

    Two prongs:
      * a history MARKER sits nearby (`⟳`, `CORRECTED`, `superseded`, `quoted`, …);
      * or the CORRECTED FORM of this very claim sits nearby — the signature with the new figure
        substituted in. Text that states the corrected sentence beside the old one is performing
        the correction.

    ⟳ **THE SECOND PRONG USED TO BE A BARE NUMBER, AND ROUND 1'S CODEX HALF BROKE IT.** Mere
    proximity to the replacement figure is not a correction:

        the sweep holds 1,414 anchors today. Another suite holds 1,416 tests.

    The old claim is still asserted and the second number measures something else — yet the bare
    prong exempted it, so a real survivor was suppressed. In a warn-only tool a FALSE NEGATIVE is
    the expensive direction, because a suppressed survivor is invisible while a spurious warning
    is merely dismissed. Measured over the seven live `1,414` survivors: the bare prong exempted
    **6 of 7** including the counterexample; the corrected-form prong exempts **0 of 7** and
    correctly refuses the counterexample, with the markers doing the real work.
    """
    # ⛔ `figure_at` IS KEYWORD-ONLY AND HAS NO DEFAULT, deliberately. A default would let a
    # caller silently fall back to the window-wide rule M4 exists to narrow, and this file has
    # already paid once for a parameter whose default was the old behaviour. Missing it is a
    # TypeError — loud, at the call site.
    if history_marker(window, figure_at, masked=masked):
        return True
    return any(cf and cf in window for cf in corrected_forms)


def window_around(text: str, start: int, end: int, span: int = CONTEXT_CHARS) -> str:
    """The text surrounding a hit, for marker inspection. PURE."""
    return text[max(0, start - span):min(len(text), end + span)]


def hit_offset(text: str, hit) -> int:
    """The character offset of THIS hit, from its own line/col. PURE.

    `text.find(hit.text)` is the first occurrence, not this one — the defect round 1 found.
    """
    line_start = 0
    for _ in range(hit.line - 1):
        line_start = text.index("\n", line_start) + 1
    return line_start + hit.col - 1


def verdict(n_survivors: int, n_corrections: int, strict: bool) -> tuple[int, str]:
    """(exit_code, message). PURE.

    ⚠ `n_corrections == 0` is NOT cannot-run: a branch that corrects no figure genuinely has
    nothing to withdraw. Cannot-run is for a search that could not reach its subject, and the
    caller decides that before getting here.
    """
    if n_corrections == 0:
        return 0, "ok — this diff removes no figure, so there is nothing to withdraw."
    if n_survivors == 0:
        return 0, (f"ok — {n_corrections} figure(s) corrected, and none of them survives "
                   f"elsewhere in docs/.")
    plural = "s" if n_survivors != 1 else ""
    msg = (f"{n_survivors} superseded figure{plural} still stand{'' if n_survivors != 1 else 's'} "
           f"elsewhere in docs/, unmarked — corrected in one place, live in another.")
    return (1 if strict else 0), ("FOUND — " if strict else "WARN — ") + msg


# ── self-test ────────────────────────────────────────────────────────────────

DIFF_ONE = """--- a/docs/x.md
+++ b/docs/x.md
@@ -1,1 +1,1 @@
-the sweep holds 1,414 anchors today
+the sweep holds 1,416 anchors today
"""

DIFF_REWRAP = """--- a/docs/y.md
+++ b/docs/y.md
@@ -1,2 +1,2 @@
-a total of 437 ms was
-measured for the pass
+a total of 63 ms was
+measured for the pass
"""

DIFF_NOCHANGE = """--- a/docs/z.md
+++ b/docs/z.md
@@ -1,1 +1,1 @@
-the count is 1,416 and rising
+the count is 1,416 and falling
"""

SIG_CASES: list[tuple[str, str, str, str]] = [
    ("figure with two words either side",
     "the sweep holds 1,414 anchors today in total", "1,414", "sweep holds 1,414 anchors today"),
    ("figure at the start of a line takes only right context",
     "1,414 anchors are bound", "1,414", "1,414 anchors are"),
    ("figure at the end takes only left context",
     "we counted 1,414", "1,414", "we counted 1,414"),
    ("a figure absent from the line degrades to the bare figure",
     "nothing here", "999", "999"),
]

REMOVED_CASES: list[tuple[str, str, int, str]] = [
    ("a corrected figure is reported once", DIFF_ONE, 1, "1,414"),
    ("a rewrapped correction is still paired, because pairing is per HUNK", DIFF_REWRAP, 1, "437"),
    ("a figure present on BOTH sides is not a correction", DIFF_NOCHANGE, 0, ""),
]

# ⛔ THE FAIL-OPEN THIS PINS, measured 2026-10-07. `replacements` once meant "every figure the
# hunk added", so an UNCHANGED figure on the same line became an exemption token — and because
# a survivor usually repeats its context, that exempted the very survivor the guard was built
# to catch. The known-positive run reported 0 where it had to report 1.
REPL_SET_CASES: list[tuple[str, str, tuple[str, ...]]] = [
    ("a changed figure is a replacement", DIFF_ONE, ("1,416",)),
    ("⭐ an UNCHANGED figure on the same line is NOT a replacement",
     """--- a/docs/a.md
+++ b/docs/a.md
@@ -1,1 +1,1 @@
-sub-second over 1,414 anchors across 59 manifests
+sub-second over 1,416 anchors across 59 manifests
""", ("1,416",)),
    ("a hunk that adds no figure has no replacements",
     """--- a/docs/b.md
+++ b/docs/b.md
@@ -1,1 +1,1 @@
-we measured 1,414 anchors
+we stopped measuring
""", ()),
]

EXEMPT_PATH_CASES: list[tuple[str, str, bool]] = [
    ("a review document is exempt", "docs/reviews/claude/x-r1.md", True),
    ("an explainer page is exempt", "docs/explainers/2026-10-07-topic-x.html", True),
    ("an ordinary document is NOT exempt", "docs/process-checklists.md", False),
    ("the backlog is NOT exempt", "docs/backlog.md", False),
    ("a nested review path is exempt too", "a/b/docs/reviews/x.md", True),
]

# ⟳ r1 Claude M4 — the third column is the FIGURE'S OFFSET in the window. Each value was
# computed by locating the figure, not typed: a weak marker is now only history when it shares
# the figure's SENTENCE, so a case that lies about where the figure is tests nothing.
HISTORY_CASES: list[tuple[str, str, int, bool]] = [
    ("a ⟳ trail is history", "⟳ 2026-09-08: the count was 1,414 then", 28, True),
    ("an explicit CORRECTED marker is history", "CORRECTED: it is not 1,414", 21, True),
    ("'superseded' is history", "superseded by the 1,416 figure", 18, True),
    ("'no longer' is history", "that cache no longer holds 1,414", 27, True),
    ("a bare live claim is NOT history", "the sweep holds 1,414 anchors", 16, False),
    ("a nearby unrelated sentence is NOT history", "we ship 1,414 anchors in CI", 8, False),
    # ── M4's witness: a WEAK marker must share the figure's sentence ─────────────────────────
    # ⛔ "was " is an English past-tense auxiliary. Window-wide it exempted 7,620 of 47,988
    # figure occurrences — more than every other marker combined — so a live claim one sentence
    # away from any past-tense prose was invisible. These two differ ONLY in the sentence break.
    ("⭐ M4: 'was ' in ANOTHER sentence does not exempt a live claim",
     "The plan was approved last week. The sweep holds 1,414 anchors.", 46, False),
    ("...but 'was ' in the SAME sentence still does, which is the case the marker is for",
     "The sweep was 1,414 anchors before the merge.", 15, True),
    ("...and 'earlier' is weak the same way", "We shipped earlier. It holds 1,414 now.", 31, False),
    ("...as is 'quoted', the token the r1 fold added to a list warning against additions",
     "The figure was quoted elsewhere. The sweep holds 1,414 anchors.", 48, False),
    # a STRONG marker is deliberately NOT sentence-bound — an author who wrote ⟳ nearby is
    # correcting something, whichever sentence it landed in.
    ("⭐ a STRONG marker still reaches ACROSS sentences, which is the half M4 did not narrow",
     "⟳ Corrected in the r1 fold. The sweep holds 1,414 anchors.", 42, True),
    ("history_marker NAMES the marker rather than answering yes/no, so a run can report it",
     "superseded by the 1,416 figure", 18, True),
]

# ⭐ The replacement prong, measured against the seven live survivors of `1,414` in this repo:
# markers alone gave 4 correct and 2 FALSE POSITIVES, both within 180 chars of `1,416`.
REPLACEMENT_CASES: list[tuple[str, str, int, tuple[str, ...], bool]] = [
    # ⚠ NO HISTORY MARKER IN THESE STRINGS, deliberately. The first version of this table used
    # "I had quoted 1,414 …", and once `quoted` joined HISTORY_MARKERS that case passed through
    # the MARKER prong while claiming to exercise the replacement prong — an ambient pass inside
    # the table written to test the thing it stopped testing.
    ("the CORRECTED FORM beside the old claim means the text is correcting itself",
     "holds 1,414 anchors today; it holds 1,416 anchors now", 6,
     ("holds 1,416 anchors",), True),
    ("⭐ mere PROXIMITY to the replacement number is NOT a correction (r1 Codex Medium)",
     "the sweep holds 1,414 anchors today. Another suite holds 1,416 tests.", 16,
     ("sweep holds 1,416 anchors",), False),
    ("...and with no corrected form nearby the same sentence stays a live claim",
     "sub-second over 1,414 anchors across 59 manifests", 16, ("over 1,416 anchors",), False),
    ("an empty tuple falls back to markers alone",
     "sub-second over 1,414 anchors", 16, (), False),
    ("a marker still wins with no corrected form present",
     "⟳ it was 1,414 back then", 9, (), True),
    ("one of several corrected forms is enough",
     "we said holds 1,414 anchors, then holds 1,416 anchors", 14,
     ("nope 999 nope", "holds 1,416 anchors"), True),
    ("an empty corrected form never exempts, however many are passed",
     "holds 1,414 anchors", 6, ("", ""), False),
]

VERDICT_CASES: list[tuple[str, int, int, bool, int]] = [
    ("no corrections at all -> ok, and not cannot-run", 0, 0, False, 0),
    ("corrections with no survivors -> ok", 0, 3, False, 0),
    ("⭐ survivors in WARN mode still exit 0, by #56", 2, 3, False, 0),
    ("survivors under --strict exit 1", 2, 3, True, 1),
    ("one survivor under --strict exits 1", 1, 1, True, 1),
    ("no corrections under --strict is still ok", 0, 0, True, 0),
]

WINDOW_CASES: list[tuple[str, str, int, int, int, str]] = [
    ("a window clips at the start of the text", "abcdef", 0, 2, 2, "abcd"),
    ("a window clips at the end of the text", "abcdef", 4, 6, 2, "cdef"),
    ("a window takes span either side when it fits", "abcdefghij", 4, 6, 2, "cdefgh"),
]


def self_test() -> int:
    failures = 0
    fc = _find_claim()

    # Direct calls with literal, pairwise-distinct arguments, inside the suite function:
    # `check-fixture-variation.py` reads call sites in the SUITE BODY, and a table loop is one
    # call site, so every parameter would otherwise look like a constant.
    def _ends_in_span(doc: str) -> bool:
        """`paragraph_ends_between` over the FIRST backtick pair, bounds DERIVED from the text.

        ⛔ Typed offsets are how this file has already been wrong twice: a hand-counted index put a
        figure inside `anchors:` instead of on the number, and again here on a quote fixture. The
        bounds come from `str.index` now, so the case cannot lie about where the span is.
        """
        # ⚠ the parameter is `doc`, not `text`, ON PURPOSE: `check-fixture-variation` reads argument
        # EXPRESSIONS, and a second call site spelled `text` records ONE value however many
        # documents the cases hand in. It has caught that five times on this branch.
        o = doc.index("`") + 1
        return paragraph_ends_between(doc, o, doc.index("`", o))

    def _marker_at(text: str, figure: str = "1,414") -> str:
        """`history_marker` at the figure's REAL offset, derived from the text. r4 Codex M1."""
        return history_marker(text, text.index(figure), masked=mask_inline_code(text))

    direct: list[tuple[str, object, object]] = [
        ("signature_of with context_words=0 is the bare figure",
         signature_of("we hold 1,414 anchors", "1,414", 0), "1,414"),
        ("signature_of with context_words=1 takes one word either side",
         signature_of("we hold 1,414 anchors here", "1,414", 1), "hold 1,414 anchors"),
        ("is_history_context over an empty window is False",
         is_history_context("", figure_at=0, masked=mask_inline_code("")), False),
        ("is_history_context finds a marker in a long window",
         is_history_context("x" * 100 + " previously " + "y" * 100, figure_at=150,
                            masked=mask_inline_code("x" * 100 + " previously " + "y" * 100)), True),
        ("window_around with span 0 is the match itself",
         window_around("abcdef", 2, 4, 0), "cd"),
        ("is_exempt_path on a literal review path",
         is_exempt_path("docs/reviews/coordinator/x-r3.md"), True),
        ("is_exempt_path on a literal live document",
         is_exempt_path("docs/process-rationale.md"), False),
        ("removed_figures over DIFF_ONE finds the corrected figure",
         removed_figures(DIFF_ONE)[0][2], "1,414"),
        ("removed_figures over DIFF_REWRAP pairs across the rewrap",
         removed_figures(DIFF_REWRAP)[0][2], "437"),
        ("verdict with literal survivors, corrections and strict=False warns",
         verdict(4, 6, False)[0], 0),
        ("verdict with different literals and strict=True fails",
         verdict(3, 5, True)[0], 1),
        ("⭐ hit_offset returns THIS match's offset, not the first occurrence's",
         (lambda tx: [hit_offset(tx, h) for h in
                      _find_claim().find_in_text(tx, _find_claim().build_pattern("ab"), "t")]
          )("ab\nxx ab"), [0, 6]),
        # ⚠ the TEXT is a literal here and a bound name at the other call site: the guard reads
        # argument EXPRESSIONS, so two calls both spelled `tx` are one value to it.
        ("hit_offset over a DIFFERENT text and a different hit",
         hit_offset("aa\nbb\nzz", _find_claim().find_in_text(
             "aa\nbb\nzz", _find_claim().build_pattern("zz"), "q")[0]), 6),
        ("is_history_context's corrected-FORM prong fires on a bare figure match",
         is_history_context("the tree held 1,416 not 1,414", ("1,416",), figure_at=24,
                            masked=mask_inline_code("the tree held 1,416 not 1,414")), True),
        ("sentence_around returns the sentence holding the offset, not the whole window",
         sentence_around("First one. Second one here. Third.", 14,
                         masked=mask_inline_code("First one. Second one here. Third.")), "Second one here. "),
        # ⚠ A DIFFERENT WINDOW, not just a different offset — `check-fixture-variation` reads
        # argument EXPRESSIONS, so two calls spelled with the same literal are ONE value to it
        # and no case could tell `window` from a constant. It refused this file for exactly that.
        ("...and a DIFFERENT window splits on ITS OWN sentence boundaries",
         sentence_around("Alpha ends here? Beta runs on.", 20,
                         masked=mask_inline_code("Alpha ends here? Beta runs on.")), "Beta runs on."),
        # ⟳ r2 Codex HIGH — THIS CASE USED TO ASSERT THAT A BARE `\n` IS A BOUNDARY, which is
        # the behaviour that made the verdict depend on line wrapping. A markdown BLOCK start
        # is a boundary; a wrap inside a sentence is not.
        ("a markdown TABLE ROW is its own sentence — a marker must not leak between rows",
         sentence_around("| 1 | it was fine |\n| 2 | holds 1,414 here |", 24,
                         masked=mask_inline_code("| 1 | it was fine |\n| 2 | holds 1,414 here |")),
         "| 2 | holds 1,414 here |"),
        ("⭐ ...but a WRAPPED sentence is ONE sentence, so a wrap cannot change the verdict",
         sentence_around("the sweep holds\n1,414 anchors today (was wrong).", 16,
                         masked=mask_inline_code("the sweep holds\n1,414 anchors today (was wrong).")),
         "the sweep holds\n1,414 anchors today (was wrong)."),
        # ── r3 Codex HIGH: three more statement boundaries, one of them LIVE ───────────────
        ("⭐ r3: a COLON lead-in ends a statement — the live instance at "
         "docs/dashboard-entries.md:10440 had `was` in the lead-in exempting the claim below",
         "was " in sentence_around(
             "Measured, and the earlier figure was wrong:\nthe sweep holds 1,414 anchors", 48,
             masked=mask_inline_code(
                 "Measured, and the earlier figure was wrong:\nthe sweep holds 1,414 anchors")),
         False),
        ("...and a markdown HARD break (two trailing spaces) is a boundary too",
         "was " in sentence_around("the count was wrong  \nholds 1,414 here", 29,
                                   masked=mask_inline_code("the count was wrong  \nholds 1,414 here")), False),
        ("...and `1)` is a list marker, not only `1.`",
         "was " in sentence_around("the count was wrong\n1) holds 1,414 here", 31,
                                   masked=mask_inline_code("the count was wrong\n1) holds 1,414 here")), False),
        # ── r3 Codex HIGH: EVERY occurrence of the figure, not the first ───────────────────
        ("⭐ r3: figure_offsets_in_hit returns ALL occurrences, so a repeated figure cannot "
         "inherit the first one's exemption",
         figure_offsets_in_hit("was 1,414. 1,414 anchors", "1,414"), [4, 11]),
        ("...and a single occurrence still yields one offset",
         figure_offsets_in_hit("holds 1,414 anchors", "1,414"), [6]),
        ("...and a figure the hit does not contain falls back to [0], not an empty list",
         figure_offsets_in_hit("no number here", "1,414"), [0]),
        ("⭐ r3: the FIRST occurrence is marked and the SECOND is not, so the hit is NOT exempt",
         (lambda t, f: [bool(history_marker(t, o, masked=mask_inline_code(t)))
                       for o in figure_offsets_in_hit(t, f)]
          )("was 1,414. 1,414 anchors", "1,414"), [True, False]),
        ("...and a PARAGRAPH break is still a boundary",
         sentence_around("it was fine\n\nholds 1,414 here", 15,
                         masked=mask_inline_code("it was fine\n\nholds 1,414 here")), "holds 1,414 here"),
        # ── the figure's offset inside the signature (r2 Codex High) ────────────────────────
        ("⭐ figure_offset_in_hit locates the FIGURE, not the signature's start",
         figure_offset_in_hit("green. count 1,414 anchors", "1,414"), 13),
        ("...and a second hit text at a different figure gives its own offset, so neither is "
         "a constant",
         figure_offset_in_hit("holds 1,416 now", "1,416"), 6),
        ("...and a figure the match does not contain falls back to 0 rather than -1",
         figure_offset_in_hit("no number here", "1,414"), 0),
        ("⭐ THE WITNESS: a marker in the PREVIOUS sentence no longer reaches the figure once "
         "the offset points at the figure instead of the signature (r2 Codex High)",
         (lambda t, f: history_marker(
              t, figure_offset_in_window(0) + figure_offset_in_hit(t, f),
              masked=mask_inline_code(t))
          )("The status was green. count 1,414 anchors today", "1,414"), ""),
        ("...while the SAME text with the marker in the figure's own sentence still suppresses",
         (lambda t, f: history_marker(
              t, figure_offset_in_window(0) + figure_offset_in_hit(t, f),
              masked=mask_inline_code(t))
          )("The status is green. count was 1,414 anchors today", "1,414"), "was "),
        ("history_marker returns the STRONG marker it matched",
         history_marker("⟳ corrected later; the sweep holds 1,414", 34,
                        masked=mask_inline_code("⟳ corrected later; the sweep holds 1,414")), "⟳"),
        ("...and the WEAK one when that is what exempted the hit",
         history_marker("The sweep was 1,414 anchors then.", 14,
                        masked=mask_inline_code("The sweep was 1,414 anchors then.")), "was "),
        ("...and \"\" when nothing exempts it, which is what makes it a SURVIVOR",
         history_marker("The sweep holds 1,414 anchors.", 16,
                        masked=mask_inline_code("The sweep holds 1,414 anchors.")), ""),
        # ── r4 Codex MEDIUM: three of r3's new boundaries also split INSIDE an inline code
        # span, so WHERE A LINE WRAPS decided the verdict. Each case below is the same prose
        # wrapped a different way; before `mask_inline_code` every wrapped one lost its marker.
        # ⛔ THE OFFSET IS DERIVED, NOT TYPED. The first draft of these cases hard-coded it and
        # three of six pointed INSIDE `anchors:` rather than at the figure — they passed for the
        # wrong reason, and the single one that FAILED is the only reason I looked. The
        # `figure_offset_in_hit` docstring in this file already says a case that lies about where
        # the figure is tests nothing; a typed offset is how that lie gets written.
        ("⭐ r4: the control — a figure inside an inline span, on ONE line, is exempted by `was`",
         _marker_at("the count was `anchors: 1,414` today"), "was "),
        ("⭐ r4: ...and the SAME sentence wrapped at the span's COLON is exempted too, where it "
         "used to be a survivor — a colon inside code is not a sentence boundary",
         _marker_at("the count was `anchors:\n1,414` today"), "was "),
        ("⭐ r4: ...and wrapped at a markdown HARD BREAK inside the span",
         _marker_at("the count was `anchors  \n1,414` today"), "was "),
        # ⟳⟳ r6 Claude M1 — THIS CASE WAS WRONG AND THE PARSERS SAY SO. r4 asserted that a `1)`
        # line inside a span is masked ("was "). It is not a span at all: an ordered list item CAN
        # interrupt a paragraph when it starts with 1, so cmark and markdown-it-py both report NO
        # code span here, and the figure is a SURVIVOR. The expectation is flipped, not deleted —
        # the input still exercises the boundary, it just has the right answer now.
        ("⟳ r6: a `1)` line ENDS the paragraph, so these backticks are not a span and the figure "
         "survives — r4 asserted the opposite and both parsers refute it",
         _marker_at("the count was `anchors\n1) 1,414` today"), ""),
        ("⭐ r6: ...but `2)` CANNOT interrupt a paragraph — only a `1` can — so THIS one IS a span "
         "and its newline is masked. The two differ by one character and by one CommonMark rule",
         _marker_at("the count was `anchors\n2) 1,414` today"), "was "),
        ("⭐ r6: a bullet line ends it too", _marker_at("the count was `anchors\n- 1,414` today"), ""),
        # ── r7 Codex HIGH: the regex mistook a quote CONTINUATION and an EMPTY marker for a
        # paragraph interruption. Rejecting a genuine span leaves its closer free to open another,
        # which masked the prose downstream and SUPPRESSED a live figure — the expensive direction.
        # ── r8 Codex H1/H2/H3: three LENIENT defects of the pairwise predicate, each invisible to
        # the other two, all fixed by carrying the paragraph's quote depth as STATE. Every fixture
        # keeps the `:` INSIDE the span: accepting the span whitens that newline, so the marker
        # three lines up reaches the figure — which is the lenient direction, and the only one that
        # costs anything. Expect "" throughout; each mutation below turns one of them into "was ".
        ("⛔ r8H1: a NESTED quote `> > ` is depth TWO and interrupts the quoted paragraph — the "
         "pairwise version matched contiguous `(>+)` only, read depth one, and masked through it",
         _marker_at("> the count was `wrong:\n> > holds 1,414 anchors today`"), ""),
        ("⛔ r8H1: ...and the CONTIGUOUS `>>` spelling is the same depth — one space, and the old "
         "code gave the two opposite answers",
         _marker_at("> the count was `wrong:\n>> holds 1,414 anchors today`"), ""),
        ("⛔ r8H2: a GFM table INSIDE a quote ends the paragraph — the delimiter-row lookahead sat "
         "after a branch the quote cases returned from, so inside a quote it was unreachable",
         _marker_at("> the count was `wrong:\n> | h |\n> |---|\n> holds 1,414 anchors today`"), ""),
        ("⛔ r8H3: quote state SURVIVES a lazy-continuation line — after `plain` the next line "
         "carries no marker, and an empty `* ` was then judged by the FRESH-paragraph rule, which "
         "permits it, instead of the quote rule, which closes on it",
         _marker_at("> the count was `wrong:\nplain\n* \nholds 1,414 anchors today`"), ""),
        ("⛔ r8: ...and a span OPENING on a lazy line inherits the quote too — depth comes from the "
         "PARAGRAPH's first line, and all 42 shapes still lenient after H1-H3 were this one",
         _marker_at("> intro\nthe count was `wrong:\n* \nholds 1,414 anchors today`"), ""),
        # ── r8, found by RE-RUNNING my own corpus at commit time rather than citing its number:
        # a FENCED CODE BLOCK interrupts a paragraph and neither predicate knew the shape. All six
        # verified against cmark-gfm and markdown-it in both dialects; the negatives are what stop
        # the clause being a `~`-sniffer.
        ("⛔ r8 own-corpus: a TILDE fence ends the paragraph — 16 of 1,620 shapes were lenient on "
         "this class and the grid that scored zero had never contained a fence at all",
         _marker_at("the count was `wrong:\n~~~\nholds 1,414 anchors today`"), ""),
        ("⛔ r8 own-corpus: ...and a BACKTICK fence likewise, where the fence run is longer than "
         "the span's own delimiter",
         _marker_at("the count was `wrong:\n```\nholds 1,414 anchors today`"), ""),
        ("⛔ r8 own-corpus: ...and a fence on a LAZY line inside a quote, which `ANY_BLOCK_ISH` "
         "governs — four shapes survived fixing only `BLANK_OR_BLOCK`, so the clause went in BOTH",
         _marker_at("> the count was `wrong:\n~~~\nholds 1,414 anchors today`"), ""),
        ("⛔ r8 own-corpus: ...and a CRLF tilde fence",
         _marker_at("the count was `wrong:\r\n~~~\r\nholds 1,414 anchors today`"), ""),
        ("...while TWO tildes are not a fence and do NOT interrupt, so the rule reads the RUN "
         "LENGTH — measured, not read off the spec",
         _marker_at("the count was `wrong:\n~~\nholds 1,414 anchors today`"), "was "),
        ("...nor does a FOUR-SPACE-indented fence, which is an indented code line; the `[ \\t]{0,3}` "
         "prefix is the clause that excludes it, and without it this case goes red",
         _marker_at("the count was `wrong:\n    ~~~\nholds 1,414 anchors today`"), "was "),
        # ── r8 Claude H1: a block start at a LIST ITEM's CONTENT COLUMN. `[ \t]{0,3}` is right at
        # top level, where four spaces is indented code, and wrong inside an item, where the
        # block-start column is the item's content column. Measured 130 of 196 list shapes LENIENT
        # before `list_content_column`, 0 after, with the noise count unmoved at 0. ⚠ The two
        # NEGATIVES are what stop this being an indent-sniffer: column 2 was already inside the old
        # cap, and a line at cont+4 IS indented code and must still be swallowed.
        ("⛔ r8 Claude H1: a BULLET at an item's content column 4 ends the paragraph — invisible to "
         "both predicates for eight rounds, because the predicate knew about `>` and not about `- `",
         _marker_at("  - the count was `wrong:\n    - x\n    holds 1,414 anchors today`"), ""),
        ("⛔ r8 Claude H1: ...and an ATX HEADING at content column 6, which `- - - ` produces — the "
         "column is the MARKER RUN's width, not a fixed indent",
         _marker_at("- - - the count was `wrong:\n      # h\n      holds 1,414 anchors today`"), ""),
        ("⛔ r8 Claude H1: ...and a QUOTE sitting AT the content column, which `QUOTE_MARKER`'s own "
         "3-space cap hides — this was the last 10 of the 130 and needs the depth RE-READ after "
         "the strip, not the strip alone",
         _marker_at("  - the count was `wrong:\n    > q\n    holds 1,414 anchors today`"), ""),
        ("...while content column 2 was ALREADY inside the old cap, so this case passed before the "
         "fix too and is here to bound it. ⚠ It does NOT establish the bolded rule the fold "
         "drew from it — inside a quote `cont` is load-bearing at 2 (r9 Claude M1)",
         _marker_at("- the count was `wrong:\n  - x\n  holds 1,414 anchors today`"), ""),
        ("...and a line at the content column PLUS FOUR is an indented code block INSIDE the item, "
         "which does not interrupt — a fix that widened the cap blindly would go red here",
         _marker_at("  - the count was `wrong:\n        - x\n    holds 1,414 anchors today`"),
         "was "),
        # ── r10: INSIDE AN ITEM, ANY ORDERED NUMBER CLOSES IT. `BLANK_OR_BLOCK`'s `0*1[.)]` is
        # right where r7 measured it — at TOP LEVEL only `1` may INTERRUPT a paragraph — and wrong
        # below an open item's content column, where the line is not interrupting the paragraph but
        # CLOSING the item, and every ordered number does that. Measured 672 of 672 LENIENT before
        # (r9 Claude H4, reproduced independently to the unit); 72 after, and those 72 are pad >= 4
        # under a content column of 5-6, i.e. r9 Claude H3's class and not this one.
        # ⚠ THE `pad == col` NEGATIVE BELOW IS WHY THIS CLAUSE IS GUARDED BY `below_item` AND NOT
        # BY `cont`. The first version tested the STRIPPED remainder, so it fired on a line AT the
        # content column too — a continuation, not a close — and added noise. The 672-shape corpus
        # could not see it: it was built from `range(0, col)`, so the one shape that refutes the
        # hypothesis was excluded by construction. A boundary corpus running pad to col+2 puts the
        # clause at 368 -> 48 LENIENT with ZERO noise at any pad.
        ("⛔ r10: an ordered marker OTHER than `1` closes an open list item, so it ends the item's "
         "paragraph — `0*1[.)]` is a TOP-LEVEL rule and this is not top level",
         _marker_at("- the count was `wrong:\n2) x\nholds 1,414 anchors today`"), ""),
        ("⛔ r10: ...and the number's WIDTH is irrelevant, which `0*1` cannot express at all",
         _marker_at("  - the count was `wrong:\n  999. x\n"
                    "  holds 1,414 anchors today`"), ""),
        ("...while at TOP LEVEL only `1` interrupts a paragraph, so `2)` does NOT — the r7 "
         "measurement this clause must not overturn",
         _marker_at("the count was `wrong:\n2) x\nholds 1,414 anchors today`"), "was "),
        ("...and a line AT the content column is a CONTINUATION of the item, not a close, so it "
         "does not end the paragraph either. ⛔ THIS IS THE CASE THAT CAUGHT THE FIRST VERSION OF "
         "THE CLAUSE, which tested the stripped remainder and so fired here too",
         _marker_at("- the count was `wrong:\n  2) x\n  holds 1,414 anchors today`"), "was "),
        # ── r9 CLAUDE B1/H1/H2/M1/M2. Four of these pin properties the fold ASSERTED and did
        # not test, and the last one is the case that would have caught 132 noisy shapes.
        ("⛔ r9 Claude H1: the span opens on a LAZY continuation — a line that omits the item's "
         "prefix entirely, so there is neither a marker NOR an indent to read and `cont` came back "
         "0. All three generations of this fix missed it: 130 of 196 shapes, unmoved by r8 and r9",
         _marker_at("  - first\nthe count was `wrong:\n    - x\n"
                    "    holds 1,414 anchors today`"), ""),
        ("⛔ r9 Claude H2/B1: a list inside ONE quote whose block start is a nested quote. `d2 > d` "
         "is structurally DEAD at quote depth >= 1 — `1 > 1` is false — which is exactly where the "
         "clause was added for. The test that belongs there is `d + d2 > depth`. ⚠ AND THE FOLD "
         "MISATTRIBUTED THIS SHAPE to 'interleaved containers nested deeper than one level' and "
         "handed it to #267: there is ONE quote and ONE item, and `cont` is already correct",
         _marker_at(">   - the count was `wrong:\n>     > q\n"
                    ">     holds 1,414 anchors today`"), ""),
        ("⛔ r9 Claude M1: `cont` is LOAD-BEARING below 4, which refutes the fold's bolded claim "
         "that the defect is exactly content column >= 4 — the strip runs on a remainder whose "
         "quote marker is already gone, so the 2 columns it removes are not the 2 that "
         "`BLANK_OR_BLOCK`'s own cap would have covered. `if cont >= 4:` kept all 163 cases green",
         _marker_at("- > - first\n  >   the count was `wrong:\n  >     # h\n"
                    "  >     holds 1,414 anchors today`"), ""),
        ("⛔ r9 Claude M2: a TOP-LEVEL paragraph with a legal 1-3 space indent gains NO container, "
         "and the block start sits at column 4 — the column that DISCRIMINATES. The indent "
         "fallback used to return the bare indent here, making `cont` 3 at top level where the "
         "docstring promised 0, and declaring a boundary the parsers do not: 132 noisy shapes. "
         "⚠ THIS IS THE CASE THE FOLD SHOULD HAVE WRITTEN AND DID NOT",
         _marker_at("   the count was `wrong:\n    # h\n    holds 1,414 anchors today`"),
         "was "),
        ("...and the same shape with the block start at column 7, which is the column the FOLD's "
         "own negative used. ⛔ It passed at r8 AND at HEAD and could not tell the two apart: four "
         "columns past the indent, `BLANK_OR_BLOCK`'s cap declines it either way. A case that "
         "passes for an ambient reason is not covering the branch it names",
         _marker_at("   the count was `wrong:\n       # h\n"
                    "       holds 1,414 anchors today`"), "was "),
        # ── r9 Codex H1/H2: the container must be recovered from the ENCLOSING ITEM, not from
        # whichever line the span happens to open on, and its width is in TAB-EXPANDED columns.
        # Measured over a 294-shape corpus of the three classes the earlier corpora could not
        # express (span-below-marker, tabbed markers, interleaved quote/list): LENIENT 170 -> 3,
        # noise 0 -> 0. ⚠ THAT 3 WAS A PROPERTY OF THIS CORPUS — over 3,902 shapes it was
        # 1,199 (r9 Claude B1). Of this corpus's 3, one is an oracle artifact (the negative below)
        # and TWO are interleaved containers nested deeper than one level — the bound this
        # function's docstring states and #267 owns.
        ("⛔ r9 Codex H1: the span opens on the item's SECOND line, where there is no marker left "
         "to read and the INDENT is the only remaining evidence of the container — the walk-back "
         "breaks at the marker line, so `cont` came back 0 and the fix did not apply at all",
         _marker_at("  - first\n    second the count was `wrong:\n    # h\n"
                    "    holds 1,414 anchors today`"), ""),
        ("⛔ r9 Codex H1: ...and INTERLEAVED quote/list containers, which the first fix read only "
         "as far as the leading run of list markers — a bound it stated and did not close",
         _marker_at("> - > - - first\n>   >     the count was `wrong:\n>   >     # h\n"
                    ">   >     holds 1,414 anchors today`"), ""),
        ("⛔ r9 Codex H2: a TAB inside the marker run is FOUR COLUMNS to the next tab stop, not one "
         "character — `-\t- ` is six columns wide, and counting characters undercounted it to four, "
         "which left the block start invisible again on the very shape the first fix was for",
         _marker_at("-\t- the count was `wrong:\n        # h\n"
                    "        holds 1,414 anchors today`"), ""),
        ("⛔ r9 Codex M1: a THREE-DIGIT ordered marker still opens an item — `LIST_MARKER` reads "
         "`\\d{1,9}`, and narrowing it to one digit leaves every other case in this file green",
         _marker_at("999) the count was `wrong:\n     # h\n"
                    "     holds 1,414 anchors today`"), ""),
        ("...while a TAB AT COLUMN 0 is FOUR columns of indent, so the whole document is an "
         "INDENTED CODE BLOCK and there is no paragraph for the span rule to be about. ⚠ THIS "
         "CASE PINS CURRENT BEHAVIOUR AND IS NOT A CLAIM THAT THE ANSWER IS RIGHT: the two "
         "parsers report `no inline code`, which the oracle construction reads as a boundary, but "
         "here it means `no paragraph at all`. It is cased so a future fence/code-aware rewrite "
         "moves it DELIBERATELY rather than silently (r8 Claude CANNOT RUN 5)",
         _marker_at("\tthe count was `wrong:\n\t    # h\n\t    holds 1,414 anchors today`"),
         "was "),
        ("...and a 3-space-indented paragraph at TOP LEVEL gains no container, so a block start "
         "needs the usual cap and this stays a genuine span — the clause must not turn a legal "
         "paragraph indent into a list content column",
         _marker_at("   the count was `wrong:\n       # h\n       holds 1,414 anchors today`"),
         "was "),
        # ── r8 Claude H2: `quote_depth`'s one-space consumption had NO case. Deleting it left the
        # suite fully green while the predicate went lenient on 208 of a 4,000-shape fuzz corpus,
        # because `QUOTE_MARKER` tolerates three leading spaces and so OVERLAPS the consumption on
        # every spelling the other cases use. Only FOUR spaces separates the two clauses.
        ("⛔ r8 Claude H2: a nested quote whose inner `>` is FOUR spaces in is still depth two — the "
         "spelling that separates `quote_depth`'s space consumption from `QUOTE_MARKER`'s own cap, "
         "and the one no other case contained",
         _marker_at("> the count was `wrong:\n>    > q\n> holds 1,414 anchors today`"), ""),
        ("⛔ r8 Claude L2: a MIXED run `` `~~ `` is NOT a fence, so the fence clause must read ONE "
         "character class per alternative — collapsing it to `[`~]{3,}` leaves every other fence "
         "case green",
         _marker_at("the count was `wrong:\n`~~\nholds 1,414 anchors today`"), "was "),
        ("⛔ r7: a `>` line CONTINUING a quote does not end the paragraph, so the span is genuine "
         "and the figure after it survives — rejecting the span made its closer open another",
         _marker_at("> intro `a\n> b` the count was wrong:\nholds 1,414 anchors today`"), ""),
        ("⛔ r7: ...and an EMPTY `* ` marker cannot interrupt a paragraph either",
         _marker_at("intro `a\n* \nb` the count was wrong:\nholds 1,414 anchors today`"), ""),
        ("⛔ r7: LAZY CONTINUATION — inside a quote, a line WITHOUT `>` continues the paragraph "
         "only as plain prose; an empty `* ` marker closes the quote, where in prose it cannot "
         "interrupt. Both parsers agree, and getting this wrong put the lenient count UP",
         _ends_in_span("> intro `a\n* \nb` x"), True),
        ("...and plain prose on a non-`>` line DOES continue it, so the span is genuine",
         _ends_in_span("> intro `a\nplain text` x"), False),
        # ── r7 Claude BLOCKING: "zero lenient" was true of my 380-shape GRID and false of a
        # 1,320-shape corpus — 184 lenient. These are the classes the grid never contained, each
        # one measured LENIENT before the clause that fixes it, and each confirmed by both parsers.
        # ── r7 Claude MEDIUM: a GFM table interrupts a paragraph only WITH its delimiter row, and
        # that needs two lines of lookahead rather than a line pair. The oracles SPLIT here and the
        # split is the answer: strict CommonMark has no tables; both GFM parsers end the paragraph.
        ("⛔ r7M1: a table HEADER plus its DELIMITER row ends the paragraph — GFM is the dialect "
         "GitHub renders, and the lenient reading was wrong in the one that matters",
         _ends_in_span("intro `a\n| h |\n|---|\nb` x"), True),
        ("⛔ r7M1: ...and a header with NO delimiter row does NOT — which is the distinction the "
         "comment drew correctly and then stopped one line short of",
         _ends_in_span("intro `a\n| h |\nb` x"), False),
        ("...nor does a pipe appearing mid-prose, so the rule reads a DELIMITER ROW and not a `|`",
         _ends_in_span("intro `a\nx | y\nb` x"), False),
        ("⛔ r7B1: a THEMATIC BREAK `***` ends the paragraph — the grid had `---` and never `***`",
         _marker_at("the count was `wrong:\n***\nholds 1,414 anchors today`"), ""),
        ("⛔ r7B1: ...and `___` likewise", _marker_at("the count was `wrong:\n___\nholds 1,414 anchors today`"), ""),
        ("⛔ r7B1: an HTML block start ends it — CONSERVATIVELY, see the clause's own caveat",
         _marker_at("the count was `wrong:\n<div>\nholds 1,414 anchors today`"), ""),
        ("⛔ r7B1: `01.` IS the number one, so it interrupts — the `1`-only rule read the DIGIT and "
         "not the NUMBER, and both parsers end the paragraph here",
         _marker_at("the count was `wrong:\n01. holds 1,414 anchors today`"), ""),
        ("⛔ r7B1: ...while `02.` is not one and does NOT interrupt, so the rule reads the number",
         _marker_at("the count was `wrong:\n02. holds 1,414 anchors today`"), "was "),
        ("⛔ r7B1+H2: a CRLF setext underline ends it — r6's `\\r` fix went into ONE of five "
         "anchored alternatives, so this stayed LENIENT while the LF twin passed",
         _marker_at("the count was `wrong:\r\n---\r\nholds 1,414 anchors today`"), ""),
        ("⛔ r7H2: ...and a CRLF `===` setext underline, which ONLY the setext alternative covers — "
         "the thematic-break clause is `[-*_]` and does not include `=`, so this is the case that "
         "actually pins `\\r?` there (the `---` twin passes either way, which is why its mutation "
         "SURVIVED until this case existed)",
         _marker_at("the count was `wrong:\r\n===\r\nholds 1,414 anchors today`"), ""),
        ("⛔ r7H2: ...and a CRLF EMPTY ATX heading likewise",
         _marker_at("the count was `wrong:\r\n#\r\nholds 1,414 anchors today`"), ""),
        ("⟳ r7 L1: a bare `---` line is a SETEXT underline and ends the paragraph — my earlier "
         "measurement put the marker on the figure's own line and so never tested it",
         _marker_at("the count was `wrong:\n---\nholds 1,414 anchors today`"), ""),
        # ⚠ A SECOND CALL SITE, spelled with its own expressions on purpose. The gate counts call
        # sites INSIDE THE SUITE and there was only one (the helper), so `text`, `start` and `end`
        # each recorded a single value. Bounds are `len()` of the literal — derived, not counted.
        ("⚠ r7: while a `>` that OPENS a quote does interrupt, and one that DEEPENS it does too — "
         "the three quote answers differ and all three are measured against cmark",
         # ⛔ r7 Claude M2 — EVERY BOUND DERIVED, AND STILL A DISTINCT EXPRESSION. `len("intro `")`
         # was `len()` of a RETYPED COPY of the prefix, coupled to nothing: perturbing the literal's
         # prefix left 3 of 10 variants GREEN with the bounds pointing into prose, which is the
         # hazard `_ends_in_span` exists to kill. A lambda gives `check-fixture-variation` the second
         # expression it needs while `str.index` keeps the bounds honest.
         (lambda d: paragraph_ends_between(d, d.index("`") + 1,
                                           d.index("`", d.index("`") + 1)))("intro `a\n> b` x"),
         True),
        ("...and a bare `-` line ends it as a SETEXT UNDERLINE, not as a list item — which is why "
         "`- ` alone and `* ` alone give different answers",
         (lambda d: paragraph_ends_between(d, d.index("`") + 1,
                                           d.index("`", d.index("`") + 1)))("intro `a\n- \nb` x"),
         True),
        ("⟳ r6: a CRLF blank line is a paragraph break too — `[ \\t]*` could not cross the `\\r`",
         _marker_at("the count was `wrong\r\n\r\nholds 1,414 anchors today`"), ""),
        ("⭐ r6: ...and a `|` table row does NOT, because a GFM table needs a delimiter row — which "
         "is why the mask has its own rule instead of sharing SENTENCE_SPLIT's",
         _marker_at("the count was `anchors\n| 1,414` today"), "was "),
        ("⛔ r4: and the boundary STILL FIRES outside a span — r3's colon rule is intact, which "
         "is what stops this fix from being a quiet revert of it",
         _marker_at("the count was:\n1,414 anchors today"), ""),
        ("⛔ r4: an UNCLOSED span masks NOTHING, so the colon still cuts and the marker is lost "
         "— the stated bound, asserted rather than assumed",
         _marker_at("the count was `anchors:\n1,414 today"), ""),
        # ⛔ THREE DISTINCT INPUTS, because one cannot tell the parameter from a constant —
        # `check-fixture-variation.py` refused the first draft of this case for exactly that
        # (`mask_inline_code(text=…)` passed the SAME value at every call site). Asserting the
        # CONTENT rather than the length is also stronger: equality proves length preservation
        # and proves nothing else was touched.
        ("...and mask_inline_code rewrites ONLY whitespace inside a span, byte-for-byte elsewhere "
         "— which is what makes every offset above index the mask and the original identically",
         mask_inline_code("a `b:\nc` d"), "a `b:xc` d"),
        ("...and prose with NO span comes back unchanged, so the mask never rewrites prose",
         mask_inline_code("a b:\nc d"), "a b:\nc d"),
        ("...and a FENCE is left alone, which is the deferred-fenced-code bound as an assertion "
         "rather than a sentence",
         mask_inline_code("```\nc: d\n```"), "```\nc: d\n```"),
        # ── r4 Claude L1: pairing is EQUAL-LENGTH, not adjacent. The witness below was
        # suppressed by the first version, which paired two runs that are not a span.
        ("⭐ r4: runs [1,2,1,1] — the opener pairs with the next run of EQUAL length, so the "
         "second span is UNCLOSED, `wrong:` stays prose and the figure is a SURVIVOR. "
         "Adjacent-only pairing masked the colon and suppressed it",
         _marker_at("a `b`` c `the count was wrong:\n1,414 anchors` d"), ""),
        # ── r4 Claude L2: the mask also reaches the sentence-END alternative, which the
        # docstring did not say. The new answer is the right one; the silence was the defect.
        ("⭐ r4: a period inside a code span no longer ends a sentence, so `v1. 2` keeps the "
         "figure in the sentence that carries `was` — it was a SURVIVOR before the mask",
         _marker_at("the count was `v1. 2` and 1,414 today"), "was "),
        # ── r5 Codex HIGH + MEDIUM: the mask suppressed LIVE PROSE two ways, and one stray
        # backtick disabled it entirely. Measured by the reviewer against cmark (cmarkgfm), which
        # rendered both H1 inputs as prose with NO <code> span, and confirmed here on the shipped
        # functions. Both H1 directions are LENIENT — a real stale figure reported as history.
        ("⛔ r5: ESCAPED backticks are not delimiters, so the prose between two of them keeps its "
         "sentence boundary and the figure is a SURVIVOR — this was suppressed as history",
         _marker_at("the count was \\`wrong:\n holds 1,414 anchors today \\`"), ""),
        ("⛔ r5: ...and a BLANK LINE cannot sit inside a code span — a paragraph break ends it, so "
         "these two backticks are not a pair and the figure is a SURVIVOR",
         _marker_at("the count was `wrong\n\nholds 1,414 anchors today`"), ""),
        ("⛔ r5: ...and ONE unmatched opener no longer disables every later span — it is SKIPPED, "
         "where `break` let a stray backtick turn a genuine span into a false survivor",
         _marker_at("a `unclosed then ``the count was wrong:\nholds 1,414 anchors today``"),
         "was "),
        # ── r5 Claude HIGH: the escape rule is OPENER-ONLY. cmark and markdown-it-py both end
        # the span AT an escaped backtick inside it, because backslash escapes do not apply within
        # a code span. Applying the test to closers too ran the span past its end and masked prose.
        # ── r6 Codex MEDIUM: an escaped FIRST backtick truncates the run, it does not delete it.
        ("r6: an escaped FIRST backtick truncates the opener, it does not delete the run",
         _marker_at("the count was \\``v1:\n2` and 1,414 today"), "was "),
        # ── r6 Claude HIGH: the mask memo keyed on `id(text)`, and same-length is exactly what a
        # recycled id has in common. 18 of 33 hits served another document's mask over 40 real
        # `main()` runs. Keyed by VALUE now, and `main` clears it per run.
        ("⛔ r6: the mask memo ignores the entry an id-KEYED cache would serve, so a recycled "
         "address cannot hand one document another's mask",
         _memo_key_probe()[0], True),
        ("...and what it serves is not the planted value, which is what the old key returned",
         _memo_key_probe()[1], True),
        ("...and a SECOND document of the SAME LENGTH gets its own mask, which is the property the "
         "id-key could not provide — same length is exactly what a recycled address has in common",
         _memo_key_probe()[2], True),
        ("...and a LONE escaped backtick still delimits nothing, which is the same rule at length 1",
         mask_inline_code("a \\` b c"), "a \\` b c"),
        ("⛔ r5: an escaped backtick INSIDE a span still CLOSES it — the span is `a \\` and the "
         "space before `b` is PROSE, where the opener-and-closer rule masked it",
         mask_inline_code("`a \\` b` c"), "`ax\\` b` c"),
        ("⛔ r5: ...so the figure after it is a SURVIVOR, where extending the span suppressed it",
         _marker_at("`a \\` the count was wrong:\n1,414 anchors`"), ""),
        ("⚠ r5 L1 STATED BEHAVIOUR: single backticks INSIDE a fenced block DO pair, so the mask "
         "reaches into fenced code — 597 span-level disagreements with cmark over 121 files, no "
         "verdict change measured. Pinned so a fence-aware rewrite moves it on purpose",
         mask_inline_code("```md\nsee `a b` here\n```"), "```md\nsee `axb` here\n```"),
        ("...while an escaped backtick in PROSE still cannot OPEN one, which is the r5 Codex half "
         "of the same rule and must not be lost to this fix",
         _marker_at("the count was \\`wrong:\n holds 1,414 anchors today \\`"), ""),
        ("...and backtick_escaped counts an EVEN run of backslashes as not escaping, so a literal "
         "backslash before a REAL delimiter still opens a span",
         backtick_escaped("a \\\\`x`", 5), False),
        ("...while an ODD run does escape", backtick_escaped("a \\`x", 3), True),
        ("⭐ suppression_line NAMES each marker and its count, so a quiet run is not mistaken "
         "for a clean one (r1 Claude M4)",
         suppression_line(collections.Counter({"was ": 5, "⟳": 2})),
         "  suppressed as history: 7 hit(s) — 'was 'x5, '⟳'x2"),
        ("...and an empty counter yields NO line, so a clean run stays quiet",
         suppression_line(collections.Counter()), ""),
        ("figure_offset_in_window clips at the start of a document, where window_around did too",
         (figure_offset_in_window(12), figure_offset_in_window(4000)), (12, CONTEXT_CHARS)),
        # ⚠ `span` AT A SECOND, EXPLICIT VALUE. Both calls above take the default, so the guard
        # saw one expression and no case could tell `span` from the constant 180.
        ("...and `span` is a parameter, so a narrower window clips sooner",
         (figure_offset_in_window(12, span=5), figure_offset_in_window(99, span=40)), (5, 40)),
        # ── r1 Claude L3: ONE DIFFERENCE, asserted ──────────────────────────────────────────
        ("⭐ L3: the two figure rules are DELIBERATELY different, so collapsing them back into "
         "one fails here rather than silently reinstating M2",
         # ⟳ r2: the comparison moved with the subject. `check-provenance` no longer expresses
         # the single-digit rule as a REGEX at all — r2 Codex Medium replaced it with a
         # two-direction predicate — so the right question is whether that guard SEES a
         # single-digit measurement while this one still does not, and whether the multi-digit
         # patterns remain distinct. Asserting the old regex equality would have quietly
         # stopped testing anything.
         (lambda mod: (NUMBER_RE.pattern == mod.MULTI_NUM_RE.pattern,
                       bool(mod.figures_in_span("**3 unbound**", " anchors")),
                       bool(NUMBER_RE.search("3 unbound"))))(_check_provenance()),
         (False, True, False)),
        ("⭐ the matcher is IMPORTED, and it still finds a wrapped claim here",
         len(fc.find_in_text("holds 1,414\nanchors", fc.build_pattern("holds 1,414 anchors"), "t.md")), 1),
    ]

    # ── ADR-0014 D2: a case must reach main() with a world it BUILT ────────────────────────
    import tempfile as _tf, contextlib as _ctx, io as _io, os as _os
    def _drive_main():
        with _tf.TemporaryDirectory() as td:
            r = Path(td); (r / "docs").mkdir()
            (r / "docs" / "a.md").write_text("nothing to see\n")
            with _ctx.redirect_stdout(_io.StringIO()), _ctx.redirect_stderr(_io.StringIO()):
                # not a git repo -> the instrument cannot reach its subject -> CANNOT RUN
                return main(["--base", "origin/master"], root=r)
    direct.append(("⭐ main() is driven from a case against a BUILT world, and a world with no "
                   "git history is CANNOT RUN rather than a pass (ADR-0014 D2)",
                   _drive_main(), 2))

    def _drive_main_strict():
        """A SECOND drive, at a different argv and a different root — one call site cannot
        tell `argv` or `root` from a constant."""
        with _tf.TemporaryDirectory() as td2:
            r2 = Path(td2); (r2 / "docs").mkdir()
            (r2 / "docs" / "b.md").write_text("unrelated\n")
            with _ctx.redirect_stdout(_io.StringIO()), _ctx.redirect_stderr(_io.StringIO()):
                return main(["--strict", "--base", "HEAD~1"], root=r2)
    direct.append(("...and a second drive at a distinct argv and root is CANNOT RUN too",
                   _drive_main_strict(), 2))

    # ── r2 Codex HIGH: the CALL SITE, which no unit case can reach ──────────────────────────
    # ⛔ MUTATING THE CALLER IS WHY THIS EXISTS. The unit cases above compute `figure_at`
    # themselves, so an entry that breaks `main`'s arithmetic left them green and SURVIVED —
    # `unit-coverage-does-not-compose`, measured on this very fix. This builds a real
    # repository, commits a correction, and asserts the live verdict.
    def _drive_live(lead: str) -> int:
        import subprocess as _sp
        with _tf.TemporaryDirectory() as td3:
            r3 = Path(td3)
            def g(*a):
                return _sp.run(["git", *a], cwd=r3, capture_output=True, text=True)
            g("init", "-q"); g("config", "user.email", "t@t"); g("config", "user.name", "t")
            (r3 / "docs").mkdir()
            # ⛔ THE LEAD MUST BE IN THE **OLD LINE** TOO, or the fixture cannot discriminate.
            # `signature_of` takes CONTEXT_WORDS words either side OF THE OLD LINE, so with the
            # lead only in the copy the signature begins exactly at the sentence boundary and
            # the mutated and correct offsets land in the SAME sentence — measured:
            #   old line "count 1,414 anchors today"              -> both offsets, marker ''
            #   old line "<lead> count 1,414 anchors today"       -> 'was ' vs '', discriminates
            (r3 / "docs" / "src.md").write_text(f"{lead} count 1,414 anchors today\n")
            (r3 / "docs" / "copy.md").write_text(f"{lead} count 1,414 anchors today\n")
            g("add", "-A"); g("commit", "-q", "-m", "base")
            base = g("rev-parse", "HEAD").stdout.strip()
            (r3 / "docs" / "src.md").write_text(f"{lead} count 1,416 anchors today\n")
            g("add", "-A"); g("commit", "-q", "-m", "correct")
            with _ctx.redirect_stdout(_io.StringIO()), _ctx.redirect_stderr(_io.StringIO()):
                return main(["--strict", "--base", base], root=r3)
    def _drive_span_window(suppressed: bool = False) -> int:
        """rc from the LIVE path over a document whose window OPENS INSIDE a code span. r5 Claude H2.

        ⛔ THIS IS THE CASE A FRAGMENT MASK FAILS. The leading span is longer than CONTEXT_CHARS,
        so `window_around` begins inside it and the window's first backtick is a CLOSER whose opener
        is outside. A later genuine opener always exists here, so a mask computed from
        the FRAGMENT pairs the orphan with it and masks the PROSE between — including the `. ` after
        "wrong", which kills the `(?<=[.!?])\\s+` boundary and lets the figure's sentence absorb the
        `was`. Measured both ways on this exact text: fragment -> marker `'was '` (SUPPRESSED, rc=0);
        document -> marker `''` (SURVIVOR, rc=1). Over the real corpus the class is 205 windows and
        205 of 205 are false suppressions.

        `suppressed=True` is the KNOWN POSITIVE: the same span shape with `was` inside the figure's
        OWN sentence, which is a genuine history exemption and must return 0. Without it this probe
        could return 1 for any reason at all and the case above would assert nothing.
        ⚠ An earlier draft used "no trailing span" as the control and expected 1 from BOTH — which
        proves nothing, and its own docstring said so while the code contradicted it.
        """
        import contextlib as _ctx, io as _io, subprocess as _sp, tempfile as _tf
        lead = "`" + ("x" * 200) + " src/a.test.ts` the count was wrong."
        # ⟳ r6 Claude L3 — THE later-span FLAG IS GONE. After r5 replaced the control with a
        # known positive it had ONE live value, so its False branch was unexercised code wearing the
        # shape of a choice. The later span is what creates the spurious pair, so it is now
        # unconditional. (The identifier is spelled out nowhere here on purpose: an earlier attempt
        # at this comment named it, and the assertion that no reference survived caught my own text.)
        tail = " in `master` today."
        middle = "It holds 1,414 anchors that was" if suppressed else "It holds 1,414 anchors"
        line = f"{lead} {middle}{tail}"
        with _tf.TemporaryDirectory() as td:
            r = Path(td)
            def g(*a):
                return _sp.run(["git", *a], cwd=r, capture_output=True, text=True)
            g("init", "-q"); g("config", "user.email", "t@t"); g("config", "user.name", "t")
            (r / "docs").mkdir()
            (r / "docs" / "src.md").write_text(line + "\n")
            (r / "docs" / "copy.md").write_text(line + "\n")
            g("add", "-A"); g("commit", "-q", "-m", "base")
            base = g("rev-parse", "HEAD").stdout.strip()
            (r / "docs" / "src.md").write_text(line.replace("1,414", "1,416") + "\n")
            g("add", "-A"); g("commit", "-q", "-m", "correct")
            with _ctx.redirect_stdout(_io.StringIO()), _ctx.redirect_stderr(_io.StringIO()):
                return main(["--strict", "--base", base], root=r)
    direct.append(("⭐⭐ r5 LIVE: a window that OPENS INSIDE a code span reports its survivor — the "
                   "mask is decided on the DOCUMENT, where a fragment mask paired an orphan closer "
                   "with a later opener and masked the prose boundary away (205/205 false "
                   "suppressions measured)",
                   _drive_span_window(), 1))
    direct.append(("...and the KNOWN POSITIVE with `was` in the figure's OWN sentence is still "
                   "suppressed, so the case above is not asserting rc=1 for any input",
                   _drive_span_window(suppressed=True), 0))
    direct.append(("⭐ LIVE: a marker in the PREVIOUS sentence does not suppress a survivor — "
                   "the caller passes the FIGURE's offset, not the signature's (r2 Codex High)",
                   _drive_live("The status was green."), 1))
    direct.append(("...and the known positive: a marker in the figure's OWN sentence still "
                   "suppresses it, so the case above is not just asserting rc=1 everywhere",
                   _drive_live("The status is green. count was"), 0))
    direct.append(("...and with no marker anywhere the survivor stands, which is the control",
                   _drive_live("The status is green."), 1))

    # ── r3 Codex HIGH, at the CALL SITE: a REPEATED figure ──────────────────────────────────
    # ⛔ The unit cases above compute the markers themselves, so the entry that flips the
    # caller's `all(...)` to `any(...)` left them green and SURVIVED. Only driving `main` over a
    # real repository sees it — `unit-coverage-does-not-compose`, twice in this file now.
    def _drive_repeated(line: str) -> int:
        import subprocess as _sp
        with _tf.TemporaryDirectory() as td4:
            r4 = Path(td4)
            def g(*a):
                return _sp.run(["git", *a], cwd=r4, capture_output=True, text=True)
            g("init", "-q"); g("config", "user.email", "t@t"); g("config", "user.name", "t")
            (r4 / "docs").mkdir()
            (r4 / "docs" / "src.md").write_text(line + "\n")
            (r4 / "docs" / "live.md").write_text(line + "\n")
            g("add", "-A"); g("commit", "-q", "-m", "base")
            base = g("rev-parse", "HEAD").stdout.strip()
            (r4 / "docs" / "src.md").write_text(line.replace("1,414", "1,416") + "\n")
            g("add", "-A"); g("commit", "-q", "-m", "fix")
            with _ctx.redirect_stdout(_io.StringIO()), _ctx.redirect_stderr(_io.StringIO()):
                return main(["--strict", "--base", base], root=r4)
    direct.append(("⭐ LIVE r3: a repeated figure whose FIRST occurrence is marked and second is "
                   "not is a SURVIVOR — the caller requires every occurrence to be exempt",
                   _drive_repeated("was 1,414. 1,414 anchors today"), 1))
    direct.append(("...and when EVERY occurrence is marked it is still suppressed, so the case "
                   "above is not asserting rc=1 for all repeated figures",
                   _drive_repeated("was 1,414 and was 1,414 again"), 0))

    total = (len(SIG_CASES) + len(REMOVED_CASES) + len(EXEMPT_PATH_CASES)
             + len(HISTORY_CASES) + len(REPLACEMENT_CASES) + len(REPL_SET_CASES) + len(VERDICT_CASES)
             + len(WINDOW_CASES) + len(direct))
    print(f"check-withdrawal --self-test  ({total} cases)")

    for name, line, number, want in SIG_CASES:
        got = signature_of(line, number)
        ok = got == want
        failures += not ok
        print(f"  [{'ok' if ok else 'FAIL'}] {name}: got {got!r} want {want!r}")

    for name, diff, want_n, want_fig in REMOVED_CASES:
        rows = removed_figures(diff)
        got_n = len(rows)
        got_fig = rows[0][2] if rows else ""
        ok = got_n == want_n and got_fig == want_fig
        failures += not ok
        print(f"  [{'ok' if ok else 'FAIL'}] {name}: got {(got_n, got_fig)} want {(want_n, want_fig)}")

    for name, path, want in EXEMPT_PATH_CASES:
        got = is_exempt_path(path)
        ok = got == want
        failures += not ok
        print(f"  [{'ok' if ok else 'FAIL'}] {name}: got {got} want {want}")

    for name, window, figure_at, want in HISTORY_CASES:
        got = is_history_context(window, figure_at=figure_at,
                                 masked=mask_inline_code(window))
        ok = got == want
        failures += not ok
        print(f"  [{'ok' if ok else 'FAIL'}] {name}: got {got} want {want}")

    for name, diff, want in REPL_SET_CASES:
        rows = removed_figures(diff)
        got = rows[0][3] if rows else ()
        ok = got == want
        failures += not ok
        print(f"  [{'ok' if ok else 'FAIL'}] {name}: got {got} want {want}")

    for name, window, figure_at, repls, want in REPLACEMENT_CASES:
        got = is_history_context(window, repls, figure_at=figure_at,
                                 masked=mask_inline_code(window))
        ok = got == want
        failures += not ok
        print(f"  [{'ok' if ok else 'FAIL'}] {name}: got {got} want {want}")

    for name, surv, corr, strict, want in VERDICT_CASES:
        got = verdict(surv, corr, strict)[0]
        ok = got == want
        failures += not ok
        print(f"  [{'ok' if ok else 'FAIL'}] {name}: got {got} want {want}")

    for name, text, a, b, span, want in WINDOW_CASES:
        got = window_around(text, a, b, span)
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

def git_diff(base: str, root: Path = REPO) -> tuple[str, str]:
    """(diff_text, error). Unified=0 keeps hunks tight so pairing stays local."""
    try:
        r = subprocess.run(
            ["git", "diff", "--unified=0", f"{base}...HEAD", "--", "docs/"],
            capture_output=True, text=True, cwd=root,
        )
    except OSError as exc:
        return "", f"CANNOT RUN — cannot invoke git: {exc}"
    if r.returncode != 0:
        return "", f"CANNOT RUN — git diff against {base} failed: {r.stderr.strip()[:200]}"
    return r.stdout, ""


def docs_files(root: Path = REPO) -> list[Path]:
    d = root / "docs"
    if not d.is_dir():
        return []
    return sorted(p for p in d.rglob("*")
                  if p.is_file() and p.suffix in {".md", ".html", ".txt"}
                  and not is_exempt_path(str(p.relative_to(root))))


def main(argv: "list[str] | None" = None, root: Path = REPO) -> int:
    """ADR-0014 D2: the world arrives as a defaulted PARAMETER so a case can drive it."""
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    ap.add_argument("--base", default="origin/master")
    ap.add_argument("--strict", action="store_true",
                    help="exit 1 on survivors instead of warning (default is warn, per #56)")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args(argv)

    if args.self_test:
        return self_test()

    # ⛔ r6 Claude H1 — ONE RUN, ONE MEMO. The cache is module-global and `main` is called many
    # times per process (the suite alone drives it through four probes), so entries outlived the
    # `blobs` list that justified them. Keying by value already makes a stale entry harmless; this
    # keeps the memo's SIZE matched to its stated scope instead of to the process lifetime.
    _MASKED_DOCS.clear()
    fc = _find_claim()
    diff, err = git_diff(args.base, root)
    if err:
        print(err, file=sys.stderr)
        return 2

    corrections = removed_figures(diff)
    corrections = [c for c in corrections if not is_exempt_path(c[0])]
    if not corrections:
        code, msg = verdict(0, 0, args.strict)
        print(msg)
        return code

    files = docs_files(root)
    if not files:
        print("CANNOT RUN — no documents found under docs/. A zero over nothing is not a pass.",
              file=sys.stderr)
        return 2

    blobs: list[tuple[Path, str]] = []
    for f in files:
        try:
            blobs.append((f, f.read_text(encoding="utf-8")))
        except (OSError, UnicodeDecodeError):
            continue

    survivors = 0
    # ⟳ r1 Claude M4 — WHAT EACH MARKER SUPPRESSED IS REPORTED, not inferred. The run used to
    # say "none of them survives elsewhere" and a reader could not tell that from "five
    # survivors each within 180 characters of the word was".
    suppressed: dict = collections.Counter()
    for path, old_line, figure, repls in corrections:
        sig = signature_of(old_line, figure)
        if len(sig.split()) < 2:        # a bare figure is not a claim; skip rather than spam
            continue
        pat = fc.build_pattern(sig, ignore_case=True)
        for f, text in blobs:
            for hit in fc.find_in_text(text, pat, str(f.relative_to(root))):
                # ⛔ THIS MATCH'S OWN OFFSET. Round 1 Codex Medium: `text.find(hit.text)` returns
                # the FIRST occurrence every time, so a second, unmarked survivor inherited the
                # first one's history exemption — measured with 500 chars of padding between
                # them, `--strict` returned rc=0 over a live claim.
                start = hit_offset(text, hit)
                win = window_around(text, start, start + len(hit.text))
                # ⛔⛔ THE MASK IS DECIDED ON THE DOCUMENT AND SLICED, NEVER COMPUTED FROM `win`
                # — r5 Claude H2. A window is a raw ±CONTEXT_CHARS slice that routinely opens
                # INSIDE a code span, and a fragment mask then pairs that orphan closer with the
                # next real opener and masks the prose between. Measured over 75,076 windows: the
                # fragment version changed the verdict in 205 and ALL 205 were false suppressions.
                # `masked_doc` is computed once per document by `masked_of`, because
                # `mask_inline_code` over a large file is not free and every hit in it shares one.
                masked_win = window_around(masked_of(text), start, start + len(hit.text))
                # ⛔ THE FIGURE'S OFFSET, NOT THE SIGNATURE'S (r2 Codex High). The signature
                # carries up to CONTEXT_WORDS words of lead-in, which can cross a sentence.
                # ⛔ EVERY occurrence, not the first (r3 Codex H3). Exempt only if all are.
                base = figure_offset_in_window(start)
                ats = [base + off for off in figure_offsets_in_hit(hit.text, figure)]
                # the corrected FORM of this claim: the signature with each replacement swapped in
                corrected = tuple(sig.replace(figure, r) for r in repls)
                if all(is_history_context(win, corrected, figure_at=a, masked=masked_win)
                       for a in ats):
                    suppressed[history_marker(win, ats[0], masked=masked_win)
                               or "corrected form"] += 1
                    continue
                survivors += 1
                print(f"  SURVIVOR {hit.path}:{hit.line}: {' '.join(hit.text.split())}")
                print(f"           corrected away in {path}; still live here, with no history marker")

    code, msg = verdict(survivors, len(corrections), args.strict)
    print(f"{msg}  ({len(corrections)} correction(s) examined across {len(blobs)} document(s))")
    line = suppression_line(suppressed)
    if line:
        print(line)
    return code


if __name__ == "__main__":
    sys.exit(main())
