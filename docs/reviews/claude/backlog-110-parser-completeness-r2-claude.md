# Adversarial review r2 — `fix/backlog-110-parser-completeness` (Claude half)

Reviewer: Claude. Subject: the **uncommitted working diff** on branch `fix/backlog-110-parser-completeness`,
covering `scripts/gen-backlog-page.py` **and** `.claude/hooks/regen-backlog-page.sh`.
Everything below was produced by executing code, never by reading it. Every mutation was applied to a
**copy of the tree outside the repo** (`$SCRATCH/muttree/{scripts,docs}`, `HOME` redirected); the
repo's own copy was never mutated and `git diff --stat` is unchanged from the numbers quoted below.

---

## Proof of subject

```
$ git rev-parse --abbrev-ref HEAD
fix/backlog-110-parser-completeness

$ git diff --stat
 .claude/hooks/regen-backlog-page.sh |  11 ++
 scripts/gen-backlog-page.py         | 278 +++++++++++++++++++++++++++++++++++-
 2 files changed, 284 insertions(+), 5 deletions(-)

$ grep -n "in_table" scripts/gen-backlog-page.py | head -5
738:    # CONTIGUOUS BLOCK. ⚠ Reading is untouched: `in_table` gates the REPORT and nothing else.
739:    in_table = False
749:            in_table = after_header = False
755:            in_table = after_header = False
759:            in_table, after_header = True, True
```

Exact lines that exist **only** in this working diff (round 1's `table_ish` is gone; these are the
round-2 design):

```python
# scripts/gen-backlog-page.py:747-752
        if line.startswith("```"):
            fenced = not fenced
            in_table = after_header = False
            continue
        if fenced:
            continue
```

```python
# scripts/gen-backlog-page.py:779-786
                if after_header and SEPARATOR_ROW.match(line.strip()):
                    after_header = False       # the delimiter, recognised by POSITION not spelling
                    continue
                after_header = False
                if not line.strip():
                    in_table = False           # a blank line ends a Markdown table. So does `## `.
                elif unread is not None:
                    unread.append(line)
```

```bash
# .claude/hooks/regen-backlog-page.sh:114
echo "$OUT" | grep -E '^⚠|^   UNREAD:' || true
```

Baseline, run before any analysis:

```
$ python3 scripts/gen-backlog-page.py --self-test | tail -1
110/110 passed
```

Second-order guards, all green (nothing regressed):

```
check-docs.py             rc=0  Documentation integrity OK
check-ratchet-contract.py rc=0  ratchet contract OK
check-anchors.py          rc=0  anchors: 11 registered, all claimed; ... floor 22 held
check-selftest-counts.py  rc=0  31 script(s) declare a count, every one verified
check-plan-file-tags.py   rc=0  plan-mode tags: 0 across 1136 documents under docs/
check-dashboard-entry.py  rc=0  check-review-rounds.py rc=0
```

---

## Summary

| Severity | Count |
|---|---|
| **Blocking** | **1** |
| High | 2 |
| Medium | 4 |
| Low | 4 |

Round 1's two Highs and three Mediums were all answered, and the *rule* is now genuinely better: the
inversion is right, `in_table` bounds the population correctly, the delimiter-by-position split is
real (two cases disagree about identical text and both are falsifiable). The findings are that
**the fence fix introduced a brand-new silent row-loss path that is strictly worse than the one
#110 was filed about** (B-1), that **H-2 was answered by adding a box and not by removing the
sentence H-2 was about** (H-1), and that **every delivery mechanism round 1 added — the hook, the
two-prefix split, the page box — survives being deleted with a green 110/110** (H-2).

---

## Blocking

### B-1 — the new fence tracking silently deletes rows. One stray ` ``` ` in `docs/backlog.md` drops 61 of 110 items, reports **nothing**, writes the page, exits 0 — and both of this change's own ratchets stay green

`scripts/gen-backlog-page.py:745-752`

```python
    fenced = False
    for line in lines:
        if line.startswith("```"):
            fenced = not fenced
            in_table = after_header = False
            continue
        if fenced:
            continue
```

The `if fenced: continue` is placed **before** every other branch, including the `## ` reset at
`:753` and the unread-collection branch at `:786`. So an **odd** number of ` ``` ` lines in the file
makes the rest of the file invisible to `parse` — not skipped-and-reported, *invisible*. The one
path out of this function that loses a row without saying so was a bare `continue` at `:768`; this
diff closes that one and opens a wider one four lines above it.

**Measured on the real `docs/backlog.md`.** A single ` ``` ` line inserted before source line 81:

```
$ python3 $SCRATCH/fence3.py
stray ``` inserted before source line 81 (of 166)
real backlog reads 110 rows -> now 49.  unread reported: []   rc=0, page WRITTEN
--- everything the run said ---
wrote .../f.html  (49 rows, 39 open, Ask tray lifted)
⚠  GROUPS still names 20 item(s) that are no longer open: [53, 54, 56, 57, 58, 60, 61, 62, 63, 66,
   67, 72, 73, 85, 86, 93, 103, 106, 108, 109] — dropped from their group for this build
     http://127.0.0.1:7391/backlog-table
```

Read that output as the human would. 61 items are gone from the page. The run printed **zero**
`UNREAD` lines. The one warning it did print is **false** — all twenty of those items are open; they
were swallowed by the fence. The page carries no INCOMPLETE box, and (see H-1) still tells the reader
*"every row on this page was read from `docs/backlog.md` in this run"*.

**It is not one unlucky placement.** Sweeping every insertion point in the real file
(`$SCRATCH/fence4.py`, parse + build only, no `main`):

```
real = 110 rows.  Placements where a single stray ``` builds a page SUCCESSFULLY with fewer rows
and NO unread report: 74
   line   81 ->  49 rows ( 61 LOST)   page still says 'every row ... was read': True
   line   82 ->  50 rows ( 60 LOST)   page still says 'every row ... was read': True
   ...
```

**Both of this change's ratchets are blind to it**, which is the part that makes it Blocking rather
than High. With an unterminated fence 30 lines into the Items table:

```
mid-table unterminated fence:       rows = 28  unread = []
   -> the suite's floor case `len(real) > 20`:            True
   -> the new ratchet `_unread_of(REAL) == []`:           True
```

`:2418` is the case this change added specifically so the `> 20` floor could not tolerate a silent
loss — *"this fails on the FIRST row the parser cannot read, and names it"*. It does not. It asserts
that the **reported** set is empty, and the fence path's whole defect is that it reports nothing. The
expectation and the subject are back to sharing a source, one level up: the case reads `unread`, and
`unread` is produced by the same walk that decided to skip.

**This is a pure regression.** HEAD, on byte-identical input:

```
$ HEAD parse on the same doctored file
HEAD reads: 110 rows
```

And on the smaller fixtures (HEAD → this diff):

```
A  unclosed fence, next section       HEAD [1, 2]     -> [1]        unread=[]   row 2 LOST, SILENT
B  a stray ``` inside the table       HEAD [1, 2, 3]  -> [1]        unread=[]   rows 2,3 LOST, SILENT
```

`docs/backlog.md` carrying 0 fences today is not a defence — it is the same "no false positives *on
this corpus*" argument r1 rejected for the population, and the file already discusses code fences in
prose (`docs/backlog.md:156`, *"strip markdown code fences"*). The hook fires on **every write** to
`docs/backlog.md`, so the file is regenerated in the intermediate state where the opening fence has
been typed and the closing one has not.

**What I would change.** Two independent repairs, and I would take both:

1. Do not let `fenced` survive a `## ` heading — hoist the `line.startswith("## ")` reset above the
   fence check, or reset `fenced = False` there. That bounds the blast radius to one section.
2. Make an unterminated fence **loud**. `parse` already has the vocabulary: at end of walk,
   `if fenced: raise ShapeError("unterminated ``` fence — N line(s) after it were not read")`. A
   refusal here is the correct outcome by this file's own standard: the sibling width mismatch has
   raised since day one, and the hook's failure arm already knows how to render a `REFUSED:`.
   Alternatively push the skipped lines into `unread` and keep exit 0 — but then the message must
   stop saying they "sit inside a table".
3. The case that pins it must not read `unread`. Anchor it to the file's own text:
   `len(parse(BACKLOG.read_text().splitlines())) == <count of `^\|\s*\d+\s*\|` lines outside fences>`,
   or simply assert `parse` raises on a fixture with an odd fence count.

---

## High

### H-1 — H-2 was answered by adding a box, not by removing the sentence H-2 was about. With `unread` non-empty the page still says *"every row on this page was read"* — now printed **directly underneath** the INCOMPLETE box

`scripts/gen-backlog-page.py:1209-1226`, rendered at `:1619` as `{unread_box}{drift}`.

Round 1's H-2 named the fix and named the case: *"the closing paragraph must become conditional on
`unread` being empty. Case to add: the rendered fragment, given a non-empty `unread`, does **not**
contain the string 'every row on this page was read'."* Neither happened. `:1080` records the
reasoning for the separate box and stops there; `:1225` is untouched.

**Measured end-to-end.** Three real rows of `docs/backlog.md` decorated the way a human would (⭐, `#`,
one leading space), `BACKLOG` pointed at the doctored copy, `main()` run for real. The emitted
fragment, consecutive, no elision:

```html
<div class="drift"><b>&#9888; this view is INCOMPLETE — 3 line(s) in <code>docs/backlog.md</code>
could not be read</b><ul>…</ul><p>Each line above sits inside a table but is not a row this page can
read, so it has no card here and is counted nowhere. Fix them in <code>docs/backlog.md</code> …</p></div>

<div class="drift"><b>&#9888; this view is built from a grouping that has drifted</b><ul><li>GROUPS
still names 2 item(s) that are no longer open: [6, 18] — dropped from their group for this build</li>
</ul><p>The items themselves are current — every row on this page was read from
<code>docs/backlog.md</code> in this run. What is out of date is the hand-written grouping in
<code>scripts/gen-backlog-page.py</code>.</p></div>
```

The reader now gets the contradiction *adjacent* instead of *nested*, which is not obviously better —
two identically-styled `.drift` boxes, the second one reassuring them about exactly what the first one
denies, and sending them to `scripts/gen-backlog-page.py` when the fix is in `docs/backlog.md`.

**And the second box's content is false, caused by the first.** `GROUPS still names 2 item(s) that
are no longer open: [6, 18]` — items 6 and 18 **are** open. They are unread. r1 flagged this in M-2's
tail (*"a silently-skipped row does not merely vanish; it makes a different warning state something
false"*) and nothing was done. Both channels carry it: the terminal prints the same false line
(`⚠  GROUPS still names 2 item(s) that are no longer open: [6, 18]`), and under B-1 it is the *only*
line printed.

**What I would change.** `:1225` becomes conditional — when `unread` is non-empty, drop "every row on
this page was read from docs/backlog.md in this run" and say "every row **this page could read**".
Separately, `sanitise_groups`' "no longer open" message must be suppressed or qualified for numbers
that are not in `rows` at all while `unread` is non-empty ("…or could not be read this run"). Add r1's
own case verbatim: build a fragment with a non-empty `unread` and assert the string is absent.

### H-2 — every delivery mechanism round 1 added is unfalsifiable. Deleting the page box, deleting the terminal report from either exit path, or reverting the ⚠-prefix split all leave **110/110 green**

21 mutations applied to the delivered file on a copy outside the repo, whole suite re-run per
mutation, control proved green first (`CONTROL: (110, 110) rc=0 fails=[]`).

```
M15 report_unread marks EVERY line with ⚠ (revert r1 M-2)  -> 110/110  killed=0
M16 report_unread removed from the normal success path     -> 110/110  killed=0
M17 report_unread removed from the no-Ask-tray path        -> 110/110  killed=0
M18 build ignores unread — no page box                     -> 110/110  killed=0
M19 build never receives unread from main                  -> 110/110  killed=0
M22 fence line does not close the table block              -> 110/110  killed=0
M23 unread box heading claims the page is COMPLETE         -> 110/110  killed=0
M7  `## ` does not close the block                         -> 110/110  killed=0
M13 quoted line not stripped                               -> 110/110  killed=0
```

Read the top five together. **The entire response to r1's M-1, M-2 and H-2 can be reverted with a
green suite.** The on-page INCOMPLETE box (`:1209`) is the single biggest piece of this round's work
and `M18` deletes it for free. `M15` reverts the exact two-prefix mechanism that `:2471-2478` and
`.claude/hooks/regen-backlog-page.sh:107-113` both call *"a contract with gen-backlog-page.main"* —
a contract with no falsifier on either side. `M23` rewrites the box heading to claim the page is fine.

The *rule* is in much better shape and I want to say so — the same run:

```
M1  never append to unread                     -> 100/110  killed=10
M3  SEPARATOR_ROW never matches                -> 100/110  killed=10
M20 the `| # |` header does not open a block   -> 100/110  killed=10
M2  drop the in_table population bound         -> 106/110  killed=4
M4  revert the hyphen requirement (r1 M-3 fix) -> 108/110  killed=2
M5  drop the POSITION constraint               -> 109/110  killed=1
M6  a blank line does NOT close the block      -> 107/110  killed=3
M21 summary grows past the Refresh budget      -> 109/110  killed=1
```

M4 killing 2 and M5 killing 1 is the direct answer to r1's *"reverting the hyphen requirement killed
0 of 108 cases"*, and the position-vs-spelling pair at `:2079-2085` is a genuinely good case design.
The gap is entirely on the **delivery** side, which is where round 1's findings were.

**What I would change.** Four cases, none of which needs a subprocess:

* `report_unread`'s marking: capture stdout, assert exactly one line starts with `⚠` and every other
  line starts with `   UNREAD: ` (kills M15, and makes the "contract" a measured one).
* both success paths: assert `report_unread` is reachable from each — or at minimum a case that runs
  `main()` against a doctored fixture on each arm and greps the output (kills M16/M17).
* the box: `"INCOMPLETE" in build(rows, …, unread=["| ⭐2 | x |"])` and
  `"INCOMPLETE" not in build(rows, …, unread=[])` (kills M18/M19/M23).
* a `## `-crossing fixture (kills M7, and is the one-line version of B-1 repair 1).

---

## Medium

### M-1 — the new population reports perfectly healthy lines, and tells the reader they "sit inside a table" when they do not

`scripts/gen-backlog-page.py:779-786`. Measured against the delivered code:

```
C  delimiter with no trailing pipe    rows=[5]  unread=['|---|---|---']
E  `### Notes` right after a row      rows=[1]  unread=['### Notes', 'prose']
G  `<!-- note -->` right after a row  rows=[1]  unread=['<!-- note -->']
```

Input for C — a **valid GFM delimiter row**; leading and trailing pipes are optional in GFM:

```python
["## Items", "| # | Item | Status |", "|---|---|---", "| 5 | x | y |"]
```

`SEPARATOR_ROW` (`:685`) is anchored `\|$`, so this delimiter is not recognised, `after_header` falls
through, and the line is reported as a lost backlog item. HEAD read the same file identically and said
nothing. E and G are block-level structures that terminate a GFM table; the block-closing rule at
`:783-784` only knows about a blank line and `## `, so the first line of whatever follows a table
that is not blank-line-separated gets reported, and then everything after it until the next blank.

The message makes it worse. `unread_note` (`:709-710`) says *"N line(s) in docs/backlog.md **sit
inside a table** and were not read"* and the box says *"a row must begin with `|` and its number cell
must be a bare integer"*. For `### Notes` both sentences are wrong, and the remedy is unfollowable.
This is precisely the cry-wolf failure `:737` cites backlog #92 for.

**What I would change.** Allow an optional trailing pipe in `SEPARATOR_ROW`
(`^\|[\s:|]*-[\s:|-]*\|?$`), and close the block on any line that does not start with `|` after
stripping — that is what actually bounds a GFM table, and it costs nothing on today's corpus because
`| … |` is how every real row is written. Cases: C, E and G above.

### M-2 — fence tracking can turn a readable file into a hard failure, and the failure is a traceback rather than this file's own refusal grammar

Input (a 4-backtick fence closed with 3, which is how a fence containing a fence is written):

```python
["## Items", "````", "| # | Item | Status |", "|---|---|---|", "| 9 | x | y |", "```",
 "| 1 | real | y |"]
```

```
HEAD  -> [9, 1]
NOW   -> RAISED ShapeError: row has 3 cells, header has 0: | 1 | real | y |
```

The fence pairing consumed the `| # |` header, so a real row now has no header to be read against.
And with a single stray ` ``` ` mid-table in the **real** file, `main()` does not refuse — it dies:

```
  File ".../gen-backlog-page.py", line 493, in dependency_svg
    clean = re.sub(r"[*`]", "", by_num[n]["title"])
KeyError: 52
```

`main`'s `try` catches `ShapeError` only (`:2491`), so this reaches the hook's failure arm as
`tail -4` of a Python traceback under the heading *"If this is a coverage refusal, add the item to
GROUPS"*. Which of B-1's silent-loss or this loud-but-wrong death you get depends on whether the
swallowed rows happen to be named in `DEPENDS` — the loudness is incidental, not designed.

**What I would change.** Fold into B-1's repair 2: raising a `ShapeError` naming the unterminated
fence makes both shapes report the same, correct cause.

### M-3 — the hook's new grep prints a colon-terminated headline with its explanation filtered out, reproducing R2-9 in the channel it just opened

`.claude/hooks/regen-backlog-page.sh:114`

```bash
echo "$OUT" | grep -E '^⚠|^   UNREAD:' || true
```

`main`'s no-Ask-tray arm (`:2521-2531`) prints `⚠  WITHOUT the Ask tray — brief-compose.py could not
lift one:` and then the *actionable* part on the following lines, indented three spaces but **not**
prefixed `UNREAD:`. The grep keeps the headline and drops the body. Simulated against that exact
output shape:

```
$ grep -E '^⚠|^   UNREAD:' sim.out
⚠  WITHOUT the Ask tray — brief-compose.py could not lift one:
⚠  UNREAD: 3 line(s) in docs/backlog.md sit inside a table and were not read — …
   UNREAD: | ⭐31 | ...
   UNREAD: a row must start with `|` and its number cell must be a bare integer — …
```

The first line ends in a colon and is followed by someone else's message. `:2523-2525` is a comment
recording that printing only the headline *"told the reader a page had failed and never why"* and cost
three runs — R2-9 — and the hook added in the same diff does that to the same message. The same is
true of the `undescribed` warning, whose two `   `-indented follow-up lines the grep also drops (I
confirmed this on a live run of the real file: the hook would show `⚠  10 open item(s) have no
description in GROUPS: […]` and neither of the lines saying what to do).

**What I would change.** Grep for the ⚠ line **and its indented continuation**, e.g.
`awk '/^⚠/{p=1;print;next} /^   /{if(p)print;next} {p=0}'`, or agree one indent marker across all of
`main`'s notes instead of special-casing `UNREAD:`. Either way it needs a case — the hook has no
`--self-test` and nothing executes it.

### M-4 — `rows_of` is a second implementation of "what is a row", and the fence change made the two disagree

`scripts/gen-backlog-page.py:622-629`

```python
def rows_of(text: str) -> dict[int, str]:
    """Item number → its row's raw text, for one version of the file."""
    out = {}
    for line in text.splitlines():
        m = ROW.match(line)
```

with `ROW = re.compile(r"^\|\s*(\d+)\s*\|(.*)$")` (`:619`). No fences, no blocks, no header. It feeds
`attach_history` (`:839`) and `changes_from_versions` across every historical version of the file. As
of this diff `parse` and `rows_of` answer differently for any row inside a ` ``` ` region: `parse`
does not see it, `rows_of` does, and a number that appears both in a fenced example and as a real row
resolves to whichever comes last in the file.

`parse`'s docstring at `:719-724` argues at length against a second walker — *"a second
implementation of one rule … which this repo has watched drift into fabricating text on a live page"* —
and the second walker is 90 lines above it, unmentioned. The consequences today are small (the extra
keys are ignored by `hist.get`), which is why this is Medium and not High; the divergence is the point.

**What I would change.** Say so in the docstring at minimum. Better: have `rows_of` reuse the walk, or
note explicitly that history is deliberately fence-blind and why.

---

## Low

* **L-1 — the `## ` block-close clause has zero coverage.** `M7` (delete `in_table = after_header =
  False` from `:754-755`) → **110/110**. `:784`'s comment asserts *"a blank line ends a Markdown
  table. So does `## `"* and only the first half is pinned. Same class as r1's L-3, one round later.
* **L-2 — `unread_note`'s `.strip()[:110]` (`:710`) is uncovered and the truncation is unmarked.**
  `M13` (drop `.strip()`) and `M13b` (drop both) → **110/110**. In the live run the quoted lines cut
  mid-word with no ellipsis and lose their closing `|`, so they cannot be searched for verbatim:
  `UNREAD: | #18 | 🟡 **Skill inventory audit — trim the dormant, reinforce the load-bearing** —
  \`scripts/skill-usage-audi`. Append `…` when `len(ln.strip()) > 110`.
* **L-3 — `html.escape` on the unread box (`:1214`) has no case.** It works (verified: a `"` in a real
  row emitted `&quot;`), and the input is arbitrary file text reaching a rendered page, so it deserves
  a falsifier rather than a passing observation.
* **L-4 — the box states the same two facts four times, and the suite count is still unpinned.** The
  `<b>` heading, the first `<li>`, the last `<li>` and the closing `<p>` all say "N lines could not be
  read" and "the number cell must be a bare integer". `unread_note` line 0 exists because the terminal
  needs a standalone summary; the box has a heading already and does not. Separately,
  `gen-backlog-page.py` is still absent from `check-selftest-counts.POPULATION` and declares no
  `# N cases` marker, so `99 → 110` is unenforced — the third such drift this project has recorded.

---

## What I checked and found sound

* **The inversion is right, and the population fix is real.** `M2` (drop the `in_table` bound) kills 4,
  including the legend-table case r1's H-1 asked for. A legend table in the same section reports
  nothing; a table with no `| # |` header of its own reports nothing; a blank line closes the block.
* **The delimiter-by-position split is genuine, not decorative.** `:2083` and `:2085` assert opposite
  outcomes for byte-identical input (`| - | - | - |`), and `M5` — dropping only the `after_header and`
  guard — kills exactly the body-position one. This is the right shape and it is what r1's M1 (Codex)
  asked for.
* **r1's M-3 regex fix is falsifiable now.** `M4` reverts `SEPARATOR_ROW` to `^\|[\s:|-]+\|$` and kills
  2 (`| | | |` and `| : | : |` directly under a header), against r1's measured **0 of 108**.
* **The Refresh-button budget fix works.** Live doctored run: total ⚠ characters **312** against
  `explainer-serve.py:1012`'s `[:400]`, nothing dropped — against r1's measured 781 with 2 of 6
  warnings lost. Summary line is 97–99 chars at every count from 1 to 100, so `:2110`'s `<= 100`
  ratchet holds and `M21` kills it.
* **No mutable-default or aliasing hazard.** `parse(..., unread=None)` / `build(..., unread=())`;
  `parse` only appends, both readers are pure, and the list is fully populated before `build` sees it.
* **Second-order guards all green** (quoted above), and `check-review-rounds.py` reads this file's
  round without a gap.
* **`main`'s `unread` really is declared outside the `try`** (`:2469`) and reported on both success
  arms (`:2532`, `:2550`) — the claim at `:2465-2468` is true. It just has no falsifier (H-2).

---

## Verdict

**NOT CONVERGED.**

B-1 must move: this change exists to make it impossible for a row to leave `docs/backlog.md` without
anyone being told, and the fence tracking it added does exactly that to 61 rows at once, past both
ratchets, with the only printed warning being false. That is the defect class of #110 with a larger
blast radius than the original.

H-1 and H-2 are the round-1 findings coming back in the shape this project keeps measuring: H-2's
remedy was named case-by-case in r1 and the case was not added, and the whole delivery half of this
round — hook, prefix contract, page box — reverts to green. The rule is in good shape; the machinery
that carries the rule to a human is untested, and B-1 is what an untested carrier looks like when it
is also wrong.

M-1 through M-4 are smaller and could ride with the B-1 repair, which touches the same walk.
