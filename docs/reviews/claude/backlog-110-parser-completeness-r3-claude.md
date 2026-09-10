# Adversarial review — `fix/backlog-110-parser-completeness`, ROUND 3 (Claude half)

Reviewer: Claude, dispatched as the Claude half of the dual gate. Codex ran concurrently.
Date: 2026-09-10.

---

## Proof of subject

```
$ git rev-parse --abbrev-ref HEAD
fix/backlog-110-parser-completeness

$ git diff --stat
 .claude/hooks/regen-backlog-page.sh |  15 ++
 scripts/check-selftest-counts.py    |   3 +
 scripts/gen-backlog-page.py         | 483 +++++++++++++++++++++++++++++++++++-
 3 files changed, 489 insertions(+), 12 deletions(-)

$ python3 scripts/gen-backlog-page.py --self-test | tail -2
  ok    the REAL backlog does not contradict itself about what is closed
127/127 passed

$ grep -n "in_table\|fenced" scripts/gen-backlog-page.py | head -8
785:    # CONTIGUOUS BLOCK. ⚠ Reading is untouched: `in_table` gates the REPORT and nothing else.
786:    in_table = False
797:    # ⚠ WHAT REMAINS TRUE, AND IS NOT THIS CHANGE'S DEFECT: a fenced example table is still read as
804:            in_table, after_header = True, True
808:            in_table, after_header = True, True
827:            if in_table:
832:                    in_table = after_header = False
```

Two lines that exist only in this working diff:

* `scripts/gen-backlog-page.py:719` — `SEPARATOR_ROW = re.compile(r"^\|?[\s:|]*-[\s:|-]*\|?$")`
* `scripts/gen-backlog-page.py:831` — `                if "|" not in line:`

`table_ish` and `fenced` are both gone (`grep -c "table_ish" → 0`; `fenced` survives only inside a
comment at `:797` explaining the revert). Fence tracking is out of the read path, confirmed.

## How I worked

Everything below was **executed**, never reasoned about. All mutation work was done on a copy of
`scripts/` + `docs/` outside the repo, under a redirected `$HOME`, so no concurrent Codex run could
see an edited file and no live page under `~/explainers/` could be touched:

```
scratchpad/r3-claude/mirror/{scripts,docs}      # the copy that gets mutated
scratchpad/r3-claude/pristine.py                # the byte-for-byte original, used to restore
scratchpad/r3-claude/fakehome/                  # HOME for every child process
```

Control run in the mirror before and after every sweep: **127/127 passed** both times.

**46 mutations applied to the delivered file. 9 SURVIVED.** (r2 measured nine survivors too; these
are a different nine — the r2 set is dead.) Note for weighting: `grep -l "gen-backlog-page"
scripts/mutations/*.json` returns **nothing**, and `check-plan-code.py:668` says so in its own words
— *"`explainer-serve.py` and `gen-backlog-page.py` STILL HAVE NO MUTATION"* — so `--mutate .` in CI
covers none of this file. This sweep is the only mutation evidence it has.

---

## Summary

| Severity | Count |
|---|---|
| **Blocking** | **1** |
| High | 3 |
| Medium | 6 |
| Low | 5 |

Round 2's fold is real work and most of it holds: the fence revert is right and well argued, the
`KeyError` fix is a genuine pre-existing crash correctly found and correctly fixed, and the drift
box no longer contradicts the unread box. What round 3 finds is that **the change's central
invariant is still false, and three of the cases round 2 added assert the falsity**; that r2's H-1
fix was applied to one of the three channels that needed it; and that the two `inspect.getsource`
proxies substituted for r2's H-2 do not cover the defect class they were written for — a one-line
insertion kills the entire feature in production at 127/127 green.

---

## Blocking

### B-1 — the REPORT population is strictly narrower than the READ population, so `| ⭐111 |` is still dropped in silence exactly where `| 111 |` would have been rendered. Measured on the real `docs/backlog.md`; the new ratchet stays green

`parse` reads a row from **anywhere in the file** — the read branch at `:810` is a bare regex over
the line, with no reference to `in_table`:

```python
        if not re.match(r"^\|\s*\d+\s*\|", line):
```

The *report*, at `:827`, is gated on `in_table`:

```python
            if in_table:
                if "|" not in line:
                    in_table = after_header = False
                    continue
```

So there is a region — every line after the first pipe-less line in a table section — where `parse`
is **still reading and rendering rows** and the completeness report has switched itself off. That is
the same "one line silently switches the guard off for everything beneath it" shape r1 filed against
the first rule; it was not removed, it was moved from *unrecognised decoration* to *any pipe-less
line*, which is a strictly larger trigger set.

**Measured on the real file** (copy in the mirror; item #111 appended in the two most ordinary ways a
person adds one). Same insertion point, one character apart:

| Input | rows read | card on page | INCOMPLETE box | ⚠ UNREAD line | exit | `--self-test` |
|---|---|---|---|---|---|---|
| blank line, then `\| 111 \| … \|` | **111** | **yes** | no | no | 0 | 127/127 |
| blank line, then `\| ⭐111 \| … \|` | 110 | **no** | **no** | **no** | 0 | **127/127** |
| appended at EOF, `\| ⭐111 \| … \|` | 110 | **no** | **no** | **no** | 0 | **127/127** |

The first row proves reading crosses the boundary. The second is backlog #110's defect, verbatim,
untouched, on the real file — and the ratchet written to catch it,

```python
2621:    case("the REAL backlog has no row the parser silently skips",
2622:         lambda: _unread_of(BACKLOG.read_text().splitlines()) == [])
```

is **green over that file**. `grep -c 'FAIL.*silently skips'` → `0` in all three runs.

**Three delivered cases certify the silence rather than catching it** — every one of these asserts
`== []` over an input containing a decorated row:

```python
2173:    case("a new `## ` section closes the block",
2174:         lambda: _unread_of(["## Items", "| # | Item | Status |", "|---|---|---|",
2175:                             "| 5 | x | y |", "## Notes", "| ⭐9 | x | y |"]) == [])
2181:    case("a sub-heading straight after the table ends it, and is not reported",   # ← "### Notes"
2184:    case("an HTML comment straight after the table ends it, and is not reported",  # ← "<!-- note -->"
```

For `### ` and `<!-- -->` the section's `header` is **not** reset, so a plain row below them is read
onto the page while a decorated one vanishes. The suite pins that asymmetry as correct.

**And r2's own M3 fix is what widened it.** Identical input, delivered code vs the r2-era terminator
(`if not line.strip():`), measured side by side:

```
  "### Notes" then "| ⭐6 | x | y |"
      delivered (r3):                REPORTED []
      r2-era (blank-line terminator): REPORTED ['### Notes', '| ⭐6 | x | y |']
      rows READ either way:          [5]
```

r2 traded a false positive (`### Notes`) for a false negative (`| ⭐6 |`) and only the first half was
measured. Same result for `<!-- note -->` and for an ordinary prose line.

**Change I would make.** The rule and the population have to fail together, which is what
`portable-practices` §21 — cited by this very diff — is about. Either:

* **(a) widen the report to the read population.** A line is reportable if the section's `header` is
  live and the line was not read; keep `in_table` only to *suppress* the legend-table false positive
  r1 found (a second `| … |` block with no `| # |` header of its own). Concretely: do not let a
  pipe-less line clear `in_table` for the rest of the section — clear it only on `## `, and re-open
  it on any line matching the read predicate; or
* **(b) narrow the read to the report population.** Make a numeric row found while `in_table` is
  False a `ShapeError`, exactly as the width-mismatch sibling already is. Then nothing is read
  outside a block, so nothing outside a block can be lost.

(b) is smaller and matches the file's existing fail-loud posture; (a) preserves current rendering.
Either way the falsifier is cheap and is the pair of rows in the table above: **a decorated row in
any position where a plain row would be READ must be REPORTED.** Assert the two populations against
each other rather than asserting each alone — a case that runs the same input twice, once decorated
and once not, and requires "read" and "reported" to cover the same positions.

---

## High

### H-1 — r2's H-1 was fixed for `sanitise_groups` only. `depends_errors` still states something false about an OPEN item, on the same page, three lines under the box saying that item could not be read

The qualification added at `:1144` covers exactly one note family:

```python
1144:    if unread:
1145:        group_notes = [n + " — or could not be READ this run; see the incomplete-view box"
1146:                       if "no longer open" in n else n for n in group_notes]
```

`depends_errors` is appended **after** it, unqualified:

```python
1153:    drift_notes += [f"DEPENDS: {e}" for e in depends_errors(DEPENDS, ROOTS, open_nums)]
```

and `depends_errors:443` decides from `open_nums`, which an unread row has already left:

```python
443:        if item not in open_nums:
444:            errors.append(f"#{item} has a dependency but is not an open item")
```

**Measured.** Real `docs/backlog.md` in the mirror, one character changed — `| 17 |` → `| ⭐17 |` —
then `python3 scripts/gen-backlog-page.py`. Text extracted from the written page:

```
⚠ this view is INCOMPLETE — 1 line(s) in docs/backlog.md could not be read
  * | ⭐17 | 🟠 **Fence the worker persist against sync (paid-blob orphaning)** — …

⚠ this view is built from a grouping that has drifted
  * GROUPS still names 1 item(s) that are no longer open: [17] … — or could not be READ this run; see the incomplete-view box
  * DEPENDS: #17 has a dependency but is not an open item
```

Item #17 **is** an open item. The page says it is not, in a sentence with no qualifier, directly
below a box saying the row was unreadable. This is r2's H-1 word for word — *"a warning that states
something false about a DIFFERENT row is worse than the omission it was reporting"* — surviving in a
sibling channel. Instance, not class.

The dependency picture is silently wrong the same way: `dependency_svg`/`dependency_mermaid` now skip
`n not in by_num`, so the diagram draws **5 children instead of 6** with nothing on the page saying
one is missing. The r2 comment's justification — *"Nothing goes unsaid by skipping: `depends_errors`
already reports …"* — is true only in the sense that *something* is said; what is said is false.

**Change I would make.** Qualify at the point where the unread list is known, not per note family.
Pass `unread` into a single `qualify(notes, unread)` applied to `drift_notes` as a whole, keyed on
the item numbers each note names rather than on the phrase `"no longer open"` (a phrase test is why
the sibling was missed). Falsifier: with `| ⭐17 |` unread, **no** note in the drift box may assert
anything about #17 without the qualifier — assert over the note list, not over one string.

### H-2 — the two `inspect.getsource` proxies do not cover the class they replaced. One inserted line kills the whole feature in production at **127/127 green**, with both proxies satisfied

```python
2289:         lambda: inspect.getsource(main).count("report_unread(unread)") == 2)
2297:         lambda: inspect.getsource(main).count("unread=unread") == 2)
```

They assert that two strings occur twice in `main`'s source. They cannot observe whether the list
those calls receive still holds anything. **Measured** — one line added to `main`, both counts
unchanged at 2:

```python
        attach_history(rows, text)
        unread.clear()            # ← the entire mutation
```

Result, in the mirror, with `| ⭐17 |` in the real backlog:

```
$ python3 scripts/gen-backlog-page.py --self-test | tail -1
127/127 passed
$ python3 scripts/gen-backlog-page.py | grep -c UNREAD
0
$ grep -c "this view is INCOMPLETE" ~/explainers/backlog-table.html
0
```

Page box gone, terminal report gone, row #17 silently absent, exit 0, suite fully green. That is the
whole of backlog #110 back, undetected — which is the exact defect r2's H-2 was filed about, one
round later, in the machinery built to answer it. (Compare the ask-choices lesson in memory: *every
Blocking in the next round was a regression from the machinery built on it.*)

**The stated reason for using a proxy is refuted by execution.** The comment at `:2284` says:

```
    # ⚠ A SHAPE assertion, not a behavioural one, and deliberately so. Reaching both arms for real
    # needs `brief-compose` and a live HOME, and a case that cannot run is worse than a narrow one
```

Reaching the **ask-tray-failure arm** needs neither. With `HOME` pointed at an empty directory,
`brief-compose` fails by design, `main` takes the `composed.returncode != 0` path at `:2708`, and
`report_unread(unread)` at `:2723` runs for real. I did exactly that, four times, in this review; the
output is quoted in H-1 above. So a real end-to-end case is available today: write a two-line
backlog copy containing one decorated row to a temp dir, point `BACKLOG`/`--out`/`HOME` at it, run
`main`, and assert on the captured stdout **and** the written page.

**Change I would make.** Replace both proxies with that one integration case. It kills
`unread.clear()`, both `unread=unread` deletions, both `report_unread` deletions and `box-not-
rendered` — every mutation the two proxies were written for, plus the class they miss. Keep at most
one shape assertion for the *success* arm if a tray-bearing fixture is genuinely out of reach, and
say in the comment that only that arm is proxied.

### H-3 — `main`'s terminal notes and `build`'s page notes now disagree, and the comment asserting they cannot is load-bearing and false

`main:2743` recomputes the notes and prints them raw:

```python
2743:    for _note in contradiction_errors(rows) + sanitise_groups(GROUPS, _open)[1]:
2744:        print(f"⚠  {_note}")
```

Directly above it, `:2736`:

```
    # ⚠ RECOMPUTED, exactly as `undescribed` below already is — these are pure functions over the
    # same rows, so a second call cannot disagree with the one `build` made.
```

That was true before this branch. It is false now, because `build` **post-processes**
`sanitise_groups`'s output at `:1145` and `main` does not. Measured, one row unread:

```
  PAGE says    : GROUPS still names 1 item(s) that are no longer open: [17] … — or could not be READ this run; see the incomplete-view box
  TERMINAL says: GROUPS still names 1 item(s) that are no longer open: [17] — dropped from their group for this build
```

The terminal gets the unqualified, false sentence — and the terminal is the channel
`.claude/hooks/regen-backlog-page.sh` surfaces (`^⚠` lines, verified below), i.e. the one the human
reads *at the moment they typed the decorated row*. The page, which they may never open, gets the
truthful one. This is precisely backwards.

**Change I would make.** Hoist the qualification into `sanitise_groups`' caller-agnostic form — a
module-level `qualify(notes, unread)` — and call it from both sites, or have `build` return its notes
so `main` prints what was rendered. Then correct the `:2736` comment, which currently licenses future
readers to add more post-processing in `build` on the same false premise. Falsifier: with a row
unread, the ⚠ lines `main` prints and the `<li>` texts in the drift box must be the same set.

---

## Medium

### M-1 — pipe-bearing prose directly under a table is reported as a lost backlog row. r2's M3 fixed only the pipe-free spellings, and this file's own house style writes the pipe-bearing ones

Measured against the delivered parser:

```
  blockquote with inline code containing a pipe   → REPORTED ['> markers: `🟠` | `🟡` | `🟢`']
  HTML comment CONTAINING a pipe                  → REPORTED ['<!-- cols: # | Item | Status -->']
  a bullet quoting a pipe                         → REPORTED ['- a row must start with `|`']
  a `### ` heading containing a pipe              → REPORTED ['### `a | b` naming']
```

`docs/backlog.md:26` is already the first shape — `> paragraphs of literal `|` on GitHub. Both are
now enforced by …` — it just happens to sit *above* the header today. Move it, or add a note like it
under the Items table, and the reader is told a healthy blockquote "sits inside a table" and should
be given "a bare integer" number cell. The M3 comment at `:843` argues correctly that an allowlist of
openers can never be finished; the conclusion drawn from that — test only for a pipe — makes the
opposite error, and `"|" in line` is a *weaker* discriminator than the thing it replaced in both
directions at once (B-1 is the other direction).

**Change I would make.** Keep `"|" not in line` as the terminator but do not report a line that is
recognisably non-tabular *prose*: a line whose first non-space character is `>`, `#`, `<`, `-`, `*`
or a digit-dot **and** which does not start with `|`. That is not an allowlist of block openers (the
block is still bounded by the pipe test); it is a suppression list for the *report*, so a
mis-classification costs a missed warning rather than a deleted row — and B-1's fix restores the
missed warning. Falsifier: each of the four lines above, asserted `== []`.

### M-2 — a real GFM delimiter row is reported as a lost backlog item when a decorated row precedes it, and the remedy text is nonsense for it

```
  parse(["## Items", "| # | Item | Status |", "| ⭐2 | x | y |", "|---|---|---|", "| 5 | x | y |"])
      REPORTED: ['| ⭐2 | x | y |', '|---|---|---|']
```

`after_header` is cleared at `:837` by the decorated row, so the genuine delimiter one line later
fails the `after_header and …` test at `:834` and is reported. The page then tells the reader:
*"a row must begin with `|` and its number cell must be a bare integer"* — about `|---|---|---|`.
The second warning is pure noise attached to the first real one, which is the way a reader learns to
skim the box.

**Change I would make.** Let the delimiter be recognised while nothing has been *read* yet in this
block, not while nothing has been *seen* — track `rows_read_in_block == 0` instead of clearing
`after_header` on an unread line. Falsifier: the input above must report only `| ⭐2 | x | y |`.

### M-3 — SURVIVOR: r2's M-1 fix (optional outer pipes in `SEPARATOR_ROW`) has no falsifier

Mutation `sep-outer-pipes-required` at `:719`:

```python
-SEPARATOR_ROW = re.compile(r"^\|?[\s:|]*-[\s:|-]*\|?$")
+SEPARATOR_ROW = re.compile(r"^\|[\s:|]*-[\s:|-]*\|$")
```

→ **127/127 passed.** The behaviour does change: `["## Items", "| # | Item | Status |",
"---|---|---", "| 5 | x | y |"]` reports `[]` as delivered and reports `['---|---|---']` under the
mutation — the exact false positive on healthy GFM that r2's M-1 was filed about. The fix is
correct and nothing defends it.

**Change I would make.** Add the case: a delimiter with no outer pipes, and one with only a leading
pipe, directly under the header, both `== []`.

### M-4 — SURVIVOR: the "NOT AN ALLOWLIST OF BLOCK OPENERS" decision at `:843` has no falsifier

Mutation `term-heading-allowlist` at `:831`:

```python
-                if "|" not in line:
+                if "|" not in line or line.startswith("#"):
```

→ **127/127 passed.** This is the shape the comment spends six lines arguing against — a `#`-prefixed
line now ends the block whatever else is on it, so the guard switches off under any heading, and a
decorated row below it goes silent. The argument is sound; nothing in the suite holds it.

**Change I would make.** One case: `["## Items", H, D, "| 5 | x | y |", "# a | b", "| ⭐6 | x | y |"]`
must report `| ⭐6 | x | y |` — i.e. a pipe-bearing heading does *not* end the block. (Note this case
and M-1's pull in opposite directions; resolving them together is the substance of B-1's fix.)

### M-5 — SURVIVOR: the `after_header = False` at `:837` is unfalsifiable and does change behaviour

Deleting it → **127/127 passed**. With it deleted,
`["## Items", H, "| ⭐2 | x | y |", "| - | - | - |", "| 5 | x | y |"]` stops reporting
`| - | - | - |` — a body row swallowed as a delimiter, which is exactly the disagreement r1's M1
(Codex) established the two positional cases to protect. The line is right; nothing pins it.

**Change I would make.** The case above — a delimiter-shaped row *two* lines under the header, with
an unread line between, must be reported.

### M-6 — SURVIVOR ×2: both stated counts can be off by one at 127/127 green, and the count is the number the reader acts on

```
box-count-off-by-one   :1287  f'{len(unread)} line(s) …'      → {len(unread) + 1}   → 127/127
note-count-off-by-one  :755   f"{len(unread)} line(s) …"      → {len(unread) + 1}   → 127/127
```

The case at `:2308` checks the *"… and N more"* tail and `len(unread_note(...)) == 6`; neither
constrains the leading total. A box that says "2 line(s) could not be read" and lists one is a
reader hunting for a row that does not exist.

**Change I would make.** `unread_note([a, b])[0].startswith("2 line(s)")`, and the same assertion on
`_box(_built([a, b]), _INC)`.

---

## Low

### L-1 — SURVIVOR: r2's L-4 fix (`[1:]`, dropping the duplicate summary from the page box) has no falsifier

`:1291` `unread_note(unread)[1:]` → `[0:]` → **127/127 passed**, and the box then prints its heading
sentence twice. Add: the box's `<li>` count equals `len(unread_note(unread)) - 1`.

### L-2 — SURVIVOR: the page box's remedy paragraph has no falsifier

Deleting the whole `'Each line above sits inside a table …'` paragraph at `:1292-1295` →
**127/127 passed**. The case at `:2318` (*"the remedy is said, whatever the count"*) tests
`unread_note`, not the box, and the box's remedy is a separate literal. Assert `"bare integer" in
_box(_built([...]), _INC)`.

### L-3 — SURVIVOR: the `after_header = False` at `:851` (after a real row) is near-equivalent

Deleting it → **127/127 passed**. It is only reachable in a table with no delimiter row at all, since
the delimiter already clears the flag. Either pin it with a delimiter-less-table case or delete it and
say in a comment that the delimiter is the only clearer — right now it reads as load-bearing and is not.

### L-4 — the hook's `awk` — r2's M-3/M4 fix — has no falsifier of any kind

`.claude/hooks/regen-backlog-page.sh:118` is shell, has no `--self-test`, is not a `check-*` guard, and
appears in no `scripts/mutations/*.json`. I verified it by hand and it is **correct**:

```
$ printf '⚠  UNREAD: summary\n   UNREAD: detail\n   UNREAD: remedy\nwrote /x\n⚠  GROUPS still names 1\n' \
    | awk '/^⚠/ {p=1; print; next} p && /^   / {print; next} {p=0}'
⚠  UNREAD: summary
   UNREAD: detail
   UNREAD: remedy
⚠  GROUPS still names 1
```

Recording it as verified-by-hand rather than as covered. The r2 finding it answers (a headline with
its actionable line filtered out) would return silently under any edit to that line.

### L-5 — `rows_of`'s new docstring states a rule with no enforcement

`:641-651` ends *"⛔ What it must NOT become is a second answer to 'is this row on the page' — that
question has one owner, and it is `parse`."* Nothing observes that. Given
`check-vocabulary-collisions.py` exists for exactly this class ("one mechanism per concern"), this is
a candidate for it rather than for a comment; at minimum the comment should say it is a convention,
not a guard. *(Memory: "a convention catches what you READ; a script catches what is THERE".)*

---

## What I checked and found sound

* **The fence revert, and its "0 fences today" premise — CHECKED, and true in the sense that
  matters.** `grep -c '^ *```' docs/backlog.md` → **0**: no line opens a fence. A bare
  `"```" in line` test would have returned **3** — rows #4, #49 and #85 quote `` ` ```python ` ``
  inside backticks — so the reverted code would have had to get that distinction right too, which
  strengthens the revert rather than weakening it. `parse` has no fence state; the
  docstring at `:790-800` states the residue plainly and scopes it to its own slice. r2's Blocking is
  genuinely closed, and the reasoning about *where* the fix lived is the right diagnosis.
* **The `KeyError` fix is real and correctly attributed.** `dep-mermaid-no-guard-ALL` (removing both
  `n in by_num` guards) → `FAIL … [raised KeyError(19)]` ×2. With `| ⭐17 |` in the real file the page
  is written and exits 0; the case at `:2230-2233` and its partner at `:2234` both kill it.
* **`report_unread` at module level.** `report-silent`, `report-all-warn`, `report-no-indent`,
  `report-wrong-prefix` all killed by `:2278`. r2's H-2 is answered *for this function*.
* **The ⚠ budget claim is accurate.** `explainer-serve.py:1010,1013` — `startswith("⚠")` then
  `" ".join(warn)[:400]`. The `<= 100` ratchet at `:2324` is measured against the real mechanism, and
  `note-summary-long` is killed by it.
* **The drift box's conditional sentence.** `drift-claims-all-read` (`if not unread` → `if True`) is
  killed by `:2262`. r1's H-2 is properly closed on the page side.
* **The escaping case is not vacuous** — `box-no-escape` killed; both arms (`&lt;script&gt;` present,
  `<script>` absent) are asserted at `:2244-2246`.
* **`check-selftest-counts.py`** passes with the new `POPULATION` entry: *"32 script(s) declare a
  count, every one verified by running it"*, `--self-test` 18/18. `check-docs.py` green.
* **The `_built`/`_drifted` fixtures are not vacuous** — `:2260` asserts the drift box exists in both
  arms before anything asserts about its contents, which is the r2 lesson applied correctly.
* **`sep-no-hyphen`, `sep-always-matches`, `sep-never-matches`, `term-blank-line`,
  `term-leading-pipe`, `header-sets-only-in-table`, `section-does-not-close-block`, `no-append`,
  `main-no-parse-unread`, `main-no-build-unread`, `box-not-rendered`, `box-never-built`,
  `box-always-built`, `drift-unqualified`, and the six `unread_note` mutations** — all killed, most
  by the case that names them. The rule, *within its population*, is well defended.

---

## Verdict

**NOT CONVERGED.**

B-1 is the item's own invariant, still false on the real file, with the ratchet green over it and
three cases asserting the silent paths — and r2's M3 fix measurably widened the silent region while
only the narrowing half was measured. H-2 means the delivery guarantees are still not guaranteed:
one inserted line removes the whole feature from production at 127/127. H-1 and H-3 are r2's H-1
surviving in the two channels the fix did not reach, one of which is the channel the hook shows the
human first.

The Medium survivors (M-3, M-4, M-5, M-6) plus L-1, L-2, L-3 are the same shape as r2's nine: fixes
that are correct and undefended. That count is not falling — r2 found nine survivors, r3 finds nine
— but the *character* has shifted: r2's survivors were whole delivery channels, r3's are individual
correctness details around a rule whose population is the remaining structural problem. Per
`docs/review-method.md`'s stop condition that is a round-4 signal, not a Phase 6 one: the defects are
converging on one cause (rule vs population), and B-1 names it.

Round 4 should be scoped to B-1's fix and its interaction with M-1/M-2/M-4, which pull against each
other and should be resolved as one decision rather than four patches.
