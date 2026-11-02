Reviewed head: 1dfb7344a4a75cd1947f8b20b5c94b4243d25c35

# Round 3 — `comprehensibility-spec` — Claude half

Subject: `docs/superpowers/specs/2026-11-02-comprehensibility-suite-design.md` at `1dfb7344`.
Scope: (1) the r2 fold, `git diff fde542a7..1dfb7344 -- docs/superpowers/specs/`; (2) a final-tree pass as the
implementer of row 1 (and of row 2, whose input table this round re-measures). The owner's answers (§1, §8, §10)
were not re-litigated.

## The r2 fixes, one by one

- **C2 (waiting = minus ANY live entry; non-`owner-wait` reference is a reported defect).** Holds. §1 D1, row 4
  and §7 now use the same predicate; the invariant and its falsifier (§7 *disjoint and complete*, last clause) agree.
- **C3 (answering order: row first, then entry; recovery via `closes entry <id>`).** Holds. Ledger entries do carry
  an `id` (`scripts/session-state.py:350`: `{"id": id_, "what": …, "on_done": …, "at": now, "kind": kind}`), so
  `closes entry <id>` names something real. The between-state ("blocking now" only) is stated and falsified (§7
  *Answering is ordered*). No new defect found.
- **C4 (freshness against `git ls-remote`, `mergedAt`, NOT RUN on failure).** Holds; it follows the repo's
  "cannot run is a failure" rule.
- **C1 (status migration table).** The COUNTS reproduce, but only under a normalisation the spec does not state —
  see M1. The `needs-you` hand-set is not reproducible — see M2.

## Independent re-measurement (r2's table)

Script: parse `git show fde542a7:docs/backlog.md` with `gen-backlog-page.parse`, take each row's `status`, normalise,
bucket. Output (abridged):

```
rows 422   closed(parser) 154   severity glyph leading the Status cell: 189
raw first words after stripping only 🔴🟠🟡🟢🔵⏳⟳ (the spec's literal rule):
  **OPEN 196, ✅ 124, PENDING 50, OPEN 7, **✅ 6, **OPEN** 5, **PARTLY 5, OPEN. 5, **SPEC 2, **REOPENED 2,
  *(WAS 1, **SCOPE 1, **2026-08-27 1, **PARTIALLY 1, **FUNCTION 1, **NARROWED 1, **BLOCKED 1, HALF 1, **HALF 1,
  **FIX 1, **TIER 1, **DECIDED 1, **2026-10-25 1, **OPEN, 1, DEFERRED 1, **CLOSED, 1, 2026-10-24: 1, OWNER 1,
  **IN 1, **DEFERRED 1
after ALSO stripping `*` emphasis and trailing `.,:` (not in the spec):
  done (✅) 124 + 6 (`**✅`) + 1 (row 31, `*(was #17 …)* ✅`) = 131
  open-words 249 (+20 whose cell has a later ✅: 105 111 120 122 124 125 127 152 174 189 213 218 253 255 301 305
  312 350 351 354)
  DEFERRED 2 ; prose 20 (PARTLY 5, PARTIALLY 1, HALF 2, FUNCTION 1, TIER 1, NARROWED 1, SCOPE 1 = 12;
  dates 39/208/339 = 3; SPEC 2; DECIDED 194, CLOSED 335, OWNER 347) ; empty 0
```

So **131 / 249 / 2 / 40 (20+20) reproduce exactly** — with the extra stripping. Cross-check: the Item-cell `✅`
(parser `sev == "done"`) is on 150 rows; the 23 where it disagrees with the Status first word are the 20
"contradicted" rows plus 64, 78, 335, all already in a by-hand bucket. So the "two signals" bucket is complete.
**16 does not reproduce** — see M2.

## Findings

### M1 — MEDIUM — §4 line 132–135 — fix_induced: true

The stated normalisation ("strip leading `🔴🟠🟡🟢🔵⏳⟳`, then a `(was …)`/`(filed …)` parenthetical; take the first
word, upper-cased") does not produce the table's counts. 196 cells begin `**OPEN`, 6 `**✅`, 5 `**OPEN**`, row 31
begins `*(was #17 …)* ✅`, and `OPEN.`, `**OPEN,`, `**CLOSED,`, `2026-10-24:` carry trailing punctuation. Applied
literally, `✅` yields 124, not 131, and the OPEN family matches ~13 rows, not 249. The counts reproduce only once
Markdown emphasis (`*`, `**`, before the word and after a parenthetical) and trailing `.,:` are also stripped. The
spec calls this rule "row 2's first test", so the implementer of row 2 must guess the missing steps to make the test
pass.
Diff hunk: `@@ -127,16 +127,26 @@`, the added line `strip leading 🔴🟠🟡🟢🔵⏳⟳, then a (was …)/(filed …)
parenthetical; take the first word, upper-cased`.
Evidence: the script above; `('**OPEN', 196)`, `('**✅', 6)`, `('*(WAS', 1)`, `('OPEN.', 5)`.
**Fix:** state the full rule, e.g. "strip leading severity/status glyphs, whitespace and `*`/`_` emphasis; drop a
leading `(was …)`/`(filed …)` parenthetical and any emphasis closing it; take the first word, strip trailing `.,:;*`,
upper-case it" — and say that this exact rule over `fde542a7` yields 131/249/20/2/20/0.

### M2 — MEDIUM — §4 line 146–147 — fix_induced: true

"set by hand on the 16 not-done rows whose Status says `NEEDS-OWNER`, 'needs decision' or an unanswered 'owner
question' (each reviewed …)" names a count and a review but not the rows. A case-insensitive search for exactly those
three phrases over the not-closed rows finds **27**: 2 26 27 28 53 66 86 90 114 117 126 193 194 198 211 222 224 288 306
307 308 318 327 337 339 347 384 (row 347 itself reads "owner question (answered 2026-10-28 …)", i.e. answered). The
implementer cannot tell which 11 were reviewed out, and the 16 is not in §9's measured table, so it has no provenance.
Since this set seeds "waiting until picked" (D1), a guess here is a wrong "needs you" list on day one.
Diff hunk: `@@ -127,16 +127,26 @@`, the added line `No first word maps to needs-you: it is set by hand on the 16
not-done rows …`.
Evidence: `re.search(r"NEEDS-OWNER|needs decision|owner question", status, re.I)` over rows with `closed == False`
→ 27 rows (listed above).
**Fix:** list the 16 row numbers in §4 (and the excluded ones with a one-word reason, e.g. "answered"), add the line
to §9 with its source commit, or say the set is decided by the owner during row 2 rather than already reviewed.

### M3 — MEDIUM — row 4 line 188–192, §7 line 232–233 — fix_induced: false

"Rows ANY live ledger entry references" is undefined: a ledger entry is `{id, what, on_done, at, kind}`
(`scripts/session-state.py:350`) and has no row field. Whether "references" means a `backlog #N` key in `what`, in
`on_done`, or a new field decides both sets and the §7 disjointness falsifier. The word predates r2 (r1's "a live
`owner-wait` entry references"), so not fix-induced, but r2 widened it to ANY kind, which makes a free-text match
in an unrelated entry's `what` able to hide a needs-you row.
Evidence: `grep -n 'entries.append' scripts/session-state.py` → `350: entries.append({"id": id_, "what": what,
"on_done": on_done, "at": now, "kind": kind})`.
**Fix:** row 4 defines the reference: e.g. an explicit `row: <N>` field written by the pick (one write, as row 4
already requires), and only that field counts; prose mentions of `backlog #N` do not.

### L1 — LOW — §5 line 165 — fix_induced: false

"`✅` in the Item cell on 117 of 333 rows (MEASURED, backlog #385)" is a stale figure from `9ac7c80d` beside
r2's fresh `fde542a7` figures in the same cell. Today the parser counts 150 of 422 (`sev == "done"`).
**Fix:** re-measure on `fde542a7` (150 of 422) or label the commit inline.

## Final-tree pass (row 1)

Row 1 is buildable without guessing: `gen-features-page.py:444` already emits `id="<slug>"`, `gen-backlog-page.py:1581`
emits `id="i<N>"`, `gen-dashboard.repo_slug` (682) and `_slug` (764) and `goal-tree.segments` (680) exist where §3
says. Nothing to add.

## Thrashing note (for the coordinator)

M1 and M2 sit in text the r2 fold wrote, in the **status-facet** component; r2's C1 was fix-induced in the same
component. That is two consecutive rounds of fix-induced findings in one component — the Phase 6 arming condition
in `docs/dev-process.md` — for `status-facet`. The `needs-you` component has NO fix-induced finding this round (M3
is pre-existing). Both M1 and M2 are fixable by adding text (the rule; the list), not by redesign.

VERDICT: NOT CONVERGED
