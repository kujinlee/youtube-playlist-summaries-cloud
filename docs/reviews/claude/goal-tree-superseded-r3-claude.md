Reviewed head: c6e84c0761bf6b86361295e7fa171b7fb5c8daef

# goal-tree-superseded (backlog #484, PR #480) — round 3 — Claude half

Reviewed range: `origin/master...c6e84c07` (branch `build-484`), with the focus on the r2 fold
`a7af562d..c6e84c07`. Round 3 is the last full round. From round 4, only a BLOCKER is fixed (`docs/review-method.md` §0 Q4c).

Method: read the r2 coordinator doc and the r2 fold's code and manifest diff. Ran
`python3 scripts/goal-tree.py --self-test`, which passed 200/200. Ran `row_fates` over the REAL
`docs/backlog.md`, then ran thirteen constructed Status cells through `row_fates` and `derive_thread`
(a scratch probe outside the repository). Applied six mutants to a scratch copy of `scripts/` and ran
the self-test against each. I made no git writes except this file and its verdict, and I ran no Postgres.
Everything marked EXECUTED was run. Anything else is labelled UNVERIFIED.

**The real backlog (EXECUTED):** 434 Items rows, no problems. The fated rows are 124, 125, 127, 189 and 213
(`superseded`) and 405 (`superseded → backlog #481`). This matches the r2 coordinator's figure.

No BLOCKER. One Medium and five Lows. Every one fails toward the pre-PR behaviour (a ✅ or the wrong
pointer), never toward a false CANNOT RUN or a crash.

---

## M1 — Medium — the cut at the first `Previously:` hides a marker appended AFTER it, and the backlog really appends current text there

**Where:** `scripts/goal-tree.py:592` (`fate_text`: `.split(HISTORY_CUT, 1)[0]`).

The r2 fold (X2-M1) assumes that everything after `Previously:` is history. The real backlog does not follow that
convention. Three rows APPEND current-state prose after their `Previously:` clause (EXECUTED, read from
`docs/backlog.md`):

- row 137 (line 165): `Previously: CODE HALF DONE — … ⟳ **SHIPPED BY A DIFFERENT SHAPE THAN THIS ROW PRESCRIBES …**`.
  This is a supersession in all but its marker.
- row 160 (line 188): `Previously: 🟠 **OPEN — …** ⟳ re-rated 2026-10-24: 🟠 → 🟡 …`
- row 340 (line 324): `Previously: pending — filed 2026-10-21; … ⟳ **audit 2026-10-23, master `92c78bff` — STILL FIRING:** …`

Row 340 is the shape of the 2026-10-26 audit, the same audit that appended the `✅ **SUPERSEDED 2026-10-26 (audit)**`
markers this PR reads on rows 124–213. Suppose an audit appends a marker to a row that already has a
`Previously:` clause:

```
✅ (was 🟠) **FIXED** — x. Previously: pending — filed 2026-10-21 ⟳ **audit 2026-10-26** ✅ **SUPERSEDED by backlog #481 (audit)** — gone
```

EXECUTED: the fate is `None`, and the leaf prints `merged aaaa111`, which is the ✅ this PR exists to remove. No real
row has this shape today, so nothing is misclassified now. The r2 fix moved the error from "historical marker
read" to "appended marker dropped". The second is the direction this PR's own FAILS-IF names.

**FILE.** The fix is not one line. A hypothesis, which needs measuring before it is adopted: the history
segment ends at the next `⟳`, the backlog's append glyph. Rows 137, 160 and 340 all resume with `⟳`.
Row 113's `Previously: ⛔ **RE-RATED …**` needs checking against that rule.

## L1 — Low — a struck-through marker is read as the row's fate

**Where:** `fate_text` / `FATE_RE` (`:138`). `~~` is not treated as history.

EXECUTED: `🟠 **OPEN** — ~~✅ **SUPERSEDED by backlog #12**~~ reinstated by the owner` reads as
`superseded → backlog #12`, and the merged leaf prints ✖. The backlog uses strikethrough for retired
text (row 34's Item cell, `~~YH4~~` in row 327), so striking out a marker is a plausible way to reopen a row.
The BOUND comment does not mention it. **FILE**, or add one clause to the BOUND comment.

## L2 — Low — two un-cancelled SUPERSEDED markers print the FIRST pointer, not the latest

**Where:** `:619` (`sup = next(m for m in marks if …)`).

EXECUTED: `✅ **SUPERSEDED by backlog #11** — then ✅ **SUPERSEDED by backlog #12 (re-pointed)**` prints
`superseded → backlog #11`. Status cells are append-only, so the later pointer is the current one. The
r2 note's own case (supersede, reopen, supersede) already chooses the LAST pointer. Without the
reopen, the code chooses the first, and nothing pins either choice. Mutant 6 below (`reversed(marks)`)
SURVIVES. **FILE.** The fix is probably `reversed(marks)` plus a case, but it is a decision about which
pointer wins, so it should not be taken in a cap round.

## L3 — Low — three mutants of the r2 regexes survive (tests that cannot fail)

EXECUTED on a scratch copy of `scripts/`. Each mutant ran 200/200 green:

| # | Mutant | Claim it leaves unpinned |
|---|---|---|
| 2 | `CODE_SPAN_RE`: drop the closer's trailing `(?!`)` | the comment's "a run of N backticks closes only on a run of **exactly** N" (only the shorter-run half is tested) |
| 3 | `REOPEN_RE`: drop the leading `\s*` | a bold span with a leading space, `** REOPENED**` |
| 4 | `REOPEN_RE`: `[—–-]` → `[—]` | the en dash and hyphen spellings of the date-dash form |

A killing input for mutant 2, EXECUTED against both regexes, is
`✅ **FIXED** — ``a``` ✅ **SUPERSEDED by backlog #12** ``` `. The original strips `a``` … ` as one span, so
the row is live. The mutant closes at `` ``a`` ``, so the marker is read.
**FIX (one case + one manifest entry) for mutant 2.** Its claim is stated in the code comment. **FILE** mutants 3 and 4.

The other three mutants were killed. Mutant 1 dropped the skip of the marker's closing `**` (2 cases red).
Mutant 5 dropped the opener lookbehind of `CODE_SPAN_RE` (1 case red). The manifest already registers a
mutant of the `.match` → `.search` kind.

## L4 — Low — one `*` inside any bold span throws off the bold pairing, so an UNBOLDED `REOPENED` cancels the fate

**Where:** `_reopened_after` (`:598`), `BOLD_RE = \*\*([^*]+)\*\*` (`:142`).

EXECUTED: `✅ **SUPERSEDED by backlog #12** — see **a*b** REOPENED is just quoted, **x**` gives fate `None`.
`**a*b**` does not match, so `BOLD_RE` pairs its closing `**` with the opening `**` of `**x**`. That reads
`" REOPENED is just quoted, "` as a bold span that leads with REOPENED. The BOUND says an unbolded
reopen is "not seen". Here an unbolded one is seen. This is contrived: a `*` inside bold is rare outside
code spans, which are stripped first. **FILE.**

## L5 — Low — prose that no longer matches the behaviour

1. **`docs/dashboard-entries.md:18655`** (this PR's tech entry) is stale after both folds. It says
   `SUPERSEDED by backlog #M` gives `superseded → backlog #M (method refuted, goal moved)` (r1 L3 removed that suffix),
   "else `WITHDRAWN`" (it is now marker-only), "Self-test 176 cases" (now 200) and "8 mutations added (83 …)"
   (now 112). The page reader sees this paragraph. **FIX (one paragraph).**
2. The module docstring (`:22-24`) and `docs/goal-threads.md` do not mention the `Previously:` cut or the
   REOPENED cancel. They also say the fate replaces "the merge's ✅", but it also replaces ⬜ next and ✖ closed
   (`derive_thread`). The code comment at `:126-136` is accurate. **FILE.**

The page legend (`✖ closed, superseded (→ where the goal went) or withdrawn`) and
`.claude/commands/goal-tree.md:35-37` match the behaviour.

---

**Checked and found sound (EXECUTED):**

- A reopen with a date and an en dash and no spaces (`**2026-11-02—REOPENED**`) cancels the fate.
- Supersede, then reopen, then a later WITHDRAWN: only the earlier marker is cancelled, so the row reads `withdrawn`.
- An italic inside the marker's own span (`**SUPERSEDED … *(audit)***`) followed by unbolded REOPENED
  cancels nothing.
- `**Previously:**` in bold still cuts the cell.
- A multi-ref leaf with one fated row and one live row keeps `merged` and names the fate.
- Lowercase `previously:` does not cut. This is consistent with the case-sensitive grammar, though not stated.
- `REOPENED` inside the marker's own span does not cancel it, and a reopen whose date carries a time
  (`**2026-11-02 10:00 — REOPENED**`) is not seen. Both sit inside the stated BOUND ("not leading its bold span").
- A pointer written `by backlog #12 and backlog #13` prints only `→ backlog #12`. The `#40, #41 and #42` form is
  covered. Treat this as UNVERIFIED for impact: no real row uses the long form.

M1 is the only finding with a real-backlog precedent. It is not live today, and it fails toward the
behaviour the PR replaced, so it does not block. Under the cap, everything except the two one-line FIXes
(L3 mutant 2, L5.1) is FILED.

VERDICT: NOT CONVERGED
