REVIEW GAP: codex — not run. This was a POST-MERGE audit of already-merged work (#278–#282),
dispatched as a single Claude pass to answer 'what did we ship unreviewed', not as a gate on
an open branch. The Codex half is owed if any of these findings becomes a slice.

# Post-merge adversarial review — PR #280 and the four docs merges (Claude)

## PROOF OF SUBJECT

**Master has moved since #280.** `8e961766` (#280) was followed by `cd10139a` (#281) and
`b08084e0` (#282), and #282 touched `scripts/gen-backlog-page.py` again (+18 lines). I reviewed the
**merged state of `origin/master` = `b08084e0`**, pinned outside the repo with
`git archive origin/master | tar -x -C <scratch>/pm`:

```
scripts/gen-backlog-page.py          git=2303e6dd8df8bf99  disk=2303e6dd8df8bf99  MATCH
.claude/hooks/regen-backlog-page.sh  git=871118aee88f1097  disk=871118aee88f1097  MATCH

$ python3 scripts/gen-backlog-page.py --self-test
86/86 passed
```

Nothing was written inside the repository. Every claim below was executed against that pinned tree.

---

## What I checked and found sound — stated because a post-merge review that only lists defects misreads the change

**Item 2 — "every open item reaches the page exactly once, however GROUPS has drifted" is a real
invariant.** I mutated `sanitise_groups` five ways; the live case caught all five:

| mutation | result |
|---|---|
| drop every 7th item silently | 85/86 — killed |
| drop items with a short description | 81/86 — killed |
| drop the last item of every group | 84/86 — killed |
| keep duplicates (remove the dedupe) | 85/86 — killed |
| stop dropping closed items | 84/86 — killed |

The function itself is sound: an open item named in `GROUPS` is placed exactly once, one not named
lands in `undescribed`, and the union is `open_nums` by construction. **Within its population** —
see PM-1.

**Item 3 — the tag counts are exactly right, under both states.** All 28 tags, against the real
page:

```
tags whose stated TOTAL disagrees with data-tags in the DOM:      NONE
tags whose stated OPEN  disagrees with data-state=open in the DOM: NONE
cards in DOM: 109    rows parsed: 109 (open 69, closed 40)
open cards in DOM: 69   parse says: 69
```

The family rollup works as documented — `cloud` reports 21 open · 29 total and the DOM carries 29
cards tagged `cloud`, including every `cloud / …` leaf. `data-state` is derived from the same
`r["closed"]` that `bundle_options` counts, so the two cannot drift.

**The drop-instead-of-refuse trade is honest: the reader is told.** With drift injected, the page
renders it:

```
drift element rendered: True
  ⚠ this view is built from a grouping that has drifted
    GROUPS still names 1 item(s) that are no longer open: [9] — dropped from their group…
    item(s) claimed by more than one group: [1] — kept in the first group only
```

Not stdout only. That was the main risk in replacing a `ShapeError` with a silent drop, and it was
handled.

**The four docs PRs.** Only `f8c29942` touches a script — `check-backlog-closure.py`, docstring
only, recording the rejected head-form extension with the measurement that refuses it. Still
`20/20 passed`. `88b4b778`, `cd10139a` are docs-only. No findings.

---

# PM-1 — HIGH. An open item *can* vanish from the page entirely — through `parse()`, not `sanitise_groups` — and the completeness invariant cannot see it, because it is measured over `parse()`'s own output.

**file:line** — `scripts/gen-backlog-page.py`, `parse()`:

```python
        if not re.match(r"^\|\s*\d+\s*\|", line):
            continue
```

A line that looks like a table row but whose first cell is not bare digits is **skipped silently**.
A cell-count mismatch raises `ShapeError` — fail-loud, correct — but this branch has no such
counterpart.

Three plausible decorations drop a row, measured:

```
| 102 | 🟠 **T** | …    -> parsed 1 row(s)
| 102 ⭐ | 🟠 **T** | …  -> parsed 0 row(s)     ⭐ markers are house style in this file
| #102 | 🟠 **T** | …   -> parsed 0 row(s)
 | 102 | 🟠 **T** | …   -> parsed 0 row(s)     one leading space
```

**Why the invariant cannot catch it.** The live case is:

```python
    _open_real = {r["num"] for r in real if not r["closed"]}      # real = parse(...)
    _san, _ = sanitise_groups(GROUPS, _open_real)
    case("every open item reaches the page exactly once, however GROUPS has drifted",
         lambda: sorted(_placed + undescribed(GROUPS, _open_real)) == sorted(_open_real) …)
```

Both sides derive from `parse()`. A dropped row leaves `_open_real` *and* the page, so the equation
still balances. The corpus is the parser's output, never the file — the recorded
*"a measurement is only as good as its CORPUS"* shape.

**The only guard on parse completeness is a floor of 20 against an actual 109:**

```
case("the real file parses at all (fail-closed on a restructure)", lambda: len(real) > 20)
real len = 109  ->  the guard tolerates losing 88 rows silently
```

**Currently latent** — I measured the real file and it is clean:

```
table-ish lines: 109   parsed: 109   SILENTLY SKIPPED: 0
```

So nothing is wrong on the page today. It is High because #280's whole thesis is *the page must
always build rather than refuse*, and the failure mode of always-building is silent omission — the
one thing this page exists to prevent. The module docstring states the guarantee unconditionally:

> *Its COMPLETENESS, though, is mechanical. `sanitise_groups` + `undescribed` guarantee that every
> open item reaches the page exactly once*

**Fix shape:** count candidate rows independently of the parser — lines starting `|` that are
neither header nor separator — and refuse (or report as drift) when that count exceeds
`len(rows)`. Two lines, and it turns the `> 20` floor into a real ratchet.

---

# PM-2 — MEDIUM. The hook exits **1** when `$HOME` is unset, contradicting the contract written at the top of the same file. #280 introduced the reference.

**file:line** — `.claude/hooks/regen-backlog-page.sh:23` (`set -uo pipefail`) and `:45`
(`PAGE="$HOME/explainers/backlog-table.html"`).

```
$ env -u HOME bash regen-backlog-page.sh <<< '{"tool_input":{"file_path":"/x/README.md"}}'
regen-backlog-page.sh: line 45: HOME: unbound variable
measured rc = 1
```

The file's own header says:

> *NEVER BLOCKS, NEVER FAILS THE TURN. Exits 0 unconditionally.*

`set -uo pipefail` predates #280; the `$HOME` reference does not — the pre-#280 hook contains no
`HOME` at all, so this path was created by the new trigger. Every other failure mode in the script
is carefully routed to `exit 0`; this one is not, and it is the only one that can fire before any
of that handling is reached.

**Fix:** `PAGE="${HOME:-}/explainers/backlog-table.html"`, or `[ -n "${HOME:-}" ] || exit 0`.

---

# PM-3 — MEDIUM. Under-fire: the trigger watches `docs/backlog.md` only, but the generator is also a source of the page. **The very next PR in the series is the case it misses.**

**file:line** — `regen-backlog-page.sh`, `stale()`:

```bash
stale() {
  [ -f "$SRC" ] || return 1
  [ -f "$PAGE" ] || return 0
  [ "$SRC" -nt "$PAGE" ]
}
```

`SRC` is `docs/backlog.md`. But the page's content also comes from `gen-backlog-page.py` itself —
`GROUPS` titles and descriptions, the framing prose, the dependency map, the CSS, the layout.

Deterministic test (page newer than the backlog, generator touched):

```
C. page newer than backlog, but the GENERATOR changed (what #282 did)
   <silent — no regeneration>
   -> the page still renders the OLD group descriptions
```

**This is not hypothetical.** `b08084e0` (#282), merged straight after #280, added exactly that
kind of content:

```
+        (102, "The rule that keeps the five generated pages readable in both light and dark …"),
+        (103, "Ask a question on one of these pages and the answer comes from whichever session …"),
+        (106, "Rebuilding a /brief page twice does not produce the same page twice …"),
+        (93,  "Two checkers look near-identical and differ on purpose …"),
```

Four new group descriptions in `scripts/gen-backlog-page.py`, and the freshly-installed hook is
silent for all of them. The change replaced a tool-shaped trigger with a content-shaped one and
then named only one of the two contents.

**Fix:** make `stale()` compare against the newest of `docs/backlog.md` and
`scripts/gen-backlog-page.py`.

---

# PM-4 — MEDIUM. Over-fire: when the generator fails, the page is never written, so *every* Edit/Write anywhere in the repo re-runs it and prints a message that is not true.

**file:line** — `stale()`'s `[ -f "$PAGE" ] || return 0` ("no page yet is the stalest case there
is"), plus the failure branch which writes nothing.

`parse()` still raises `ShapeError`, so the generator can still exit nonzero even after #280 removed
the coverage refusals. With one malformed row appended to `docs/backlog.md`, three consecutive hook
invocations **on unrelated files**:

```
   call 1 on an UNRELATED file: ⚠  docs/backlog.md changed but the HTML view was NOT regenerated:
   call 2 on an UNRELATED file: ⚠  docs/backlog.md changed but the HTML view was NOT regenerated:
   call 3 on an UNRELATED file: ⚠  docs/backlog.md changed but the HTML view was NOT regenerated:
   page exists after 3 calls? NO
```

Each costs a full generator run (~0.5s measured) and each asserts *"docs/backlog.md changed"* when
it did not — the file that changed was `/x/unrelated.ts`. The state is self-sustaining: no page is
written, so the next call is stale again, for every tool call until someone fixes the backlog.

The fresh-clone case, by contrast, is **fine** and I want to be clear about the difference:

```
   page exists? no
   ↻ backlog view regenerated    real 0.49
   after: ~/explainers/backlog-table.html now exists
```

One rebuild, then it stops. The "no page" arm is self-limiting **when the generator succeeds**;
the defect is only the failure path.

**Fix:** distinguish "no page" from "generator failing" — e.g. touch a marker on failure, or only
take the no-page arm when `FILE_PATH` was the backlog.

---

# PM-5 — LOW. `-nt` is false on equal mtimes, so an edit and a rebuild landing in the same second read as fresh.

```
B. EXACTLY equal mtimes  ->  <silent>
```

`[ "$SRC" -nt "$PAGE" ]` compares whole seconds on this platform. An edit immediately followed by a
regeneration, or two edits inside one second, can leave the page one revision behind with the hook
reporting nothing. Narrow, and the next edit corrects it — listed because the hook's stated purpose
is that a stale page is indistinguishable from a current one.

---

# PM-6 — LOW. `order.get(sev, len(order))` stops the crash, but the row it rescues is then counted in no severity tile.

**file:line** — `order = {...}` and `open_rows.sort(key=lambda r: (order.get(r["sev"], len(order)), r["num"]))`;
`by_sev = {k: sum(1 for r in open_rows if r["sev"] == k) for k in ("crit","high","med","low","none")}`.

The fallback is correct — `order.get("done", 5)` sorts a contradiction row last instead of raising
`KeyError` — but `by_sev` enumerates only the five known severities, so such a row is rendered and
tallied nowhere:

```
   real backlog today:              open=69  tiles sum=69  OK
   real + ONE contradiction row:    open=70  tiles sum=69  MISMATCH — 1 row in NO tile
      contradiction_errors: 1 note(s)
```

`contradiction_errors` *does* report it, and the page builds and shows the drift note, so the reader
is not left in the dark — that is why this is Low rather than Medium. But the note says *"add the ✅
to the Status cell"*; it does not say *"the counts on this page are off by one"*, and the count is
the thing a reader trusts at a glance. Deriving `by_sev` from the same fallback (an "other" bucket)
closes it.

---

# PM-7 — LOW. The hook's path match is not repo-scoped.

```bash
case "$FILE_PATH" in
  */docs/backlog.md|docs/backlog.md) ;;
```

`*/docs/backlog.md` matches *any* project's `docs/backlog.md`, so editing an unrelated repo's
backlog in the same session regenerates this one's page. Harmless (it rebuilds from the correct
`$REPO`), but the guard says something narrower than it means.

---

## Summary

| Severity | Count | Findings |
|---|---|---|
| Blocking | 0 | — |
| High | 1 | PM-1 |
| Medium | 3 | PM-2, PM-3, PM-4 |
| Low | 3 | PM-5, PM-6, PM-7 |

**Nothing here warrants a revert.** #280 is a net improvement and its central design decision —
replace refusals with reported drops, because a page frozen five days told the reader nothing — is
correct, well-argued, and *implemented honestly*: the drops are reported, they reach the page, and
the invariant that replaces the refusal is genuinely load-bearing under mutation. The tag work is
clean; I could not make the counts disagree with the DOM in any state.

The findings cluster in one place, and it is the same place as the last three rounds on this
author's other change: **the new code is right about its own subject and wrong about its
population.**

- **PM-1** — the completeness guarantee is measured over the parser's output rather than the file,
  so the parser's one silent-skip branch is invisible to it. Latent today (0 skipped, measured), and
  it is the failure mode that "always build" converts refusals into.
- **PM-3** — the trigger moved from tool-shaped to content-shaped, correctly, and then named one of
  the page's two sources. The PR merged an hour later is the counterexample.
- **PM-4** and **PM-2** are both the failure path of a script whose header promises it has none.

**Recommended next action:** PM-2 and PM-3 are one line each and worth doing together in a single
follow-up; PM-1 is the one to file, because it is the only finding that can cost a reader an item
without anything saying so.

⚠ **The real finding is the process gap, not the code.** Five PRs merged with no review doc and no
verdict file, and #280 — the one carrying all the behaviour change — was reviewed only because the
gap was noticed afterwards. Every defect above was reachable by running the code for twenty minutes.

VERDICT: NOT CONVERGED (post-merge; no revert warranted, PM-1 to file, PM-2/PM-3 to fix)
