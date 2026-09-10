# Adversarial review r1 — `fix/backlog-110-parser-completeness` (Claude half)

Reviewer: Claude. Subject: the **uncommitted working diff** on branch `fix/backlog-110-parser-completeness`.
Everything below was produced by running code in the repo working tree, not by reading it.

---

## Proof of subject

```
$ git rev-parse --abbrev-ref HEAD
fix/backlog-110-parser-completeness

$ git diff --stat
 scripts/gen-backlog-page.py | 154 ++++++++++++++++++++++++++++++++++++++++++--
 1 file changed, 150 insertions(+), 4 deletions(-)
```

Exact lines that exist only in this working diff (`git diff | head -40` and beyond):

```
+SEPARATOR_ROW = re.compile(r"^\|[\s:|-]+\|$")
```

```
+| ⭐2 | 🟠 **Star** — a ⭐ ahead of the number | b.ts | S | A | pending |
```

```
+            if unread is not None and header and table_ish(line):
+                unread.append(line)
```

Baseline suite, run before any analysis:

```
$ python3 scripts/gen-backlog-page.py --self-test | tail -4
  ok    the real file parses at all (fail-closed on a restructure)
  ok    the REAL backlog has no row the parser silently skips
  ok    the REAL backlog does not contradict itself about what is closed

99/99 passed
```

Second-order guards, all green after the change (nothing regressed):

```
$ python3 scripts/check-docs.py       | tail -1   ->  Documentation integrity OK
$ python3 scripts/check-ratchet-contract.py | tail -1 -> ratchet contract OK
$ python3 scripts/check-anchors.py    | tail -1   ->  anchors: 11 registered, all claimed; ... floor 22 held
$ python3 scripts/gen-goals-page.py --self-test | tail -1 -> 15/15 self-test cases passed
$ python3 scripts/check-selftest-counts.py       -> 31 script(s) declare a count, every one verified
```

`gen-backlog-page.py` is **not** in `check-selftest-counts.POPULATION` and declares no
`# N cases` marker, so the 86 → 99 move is not pinned by any gate. Not a finding, but the
count in the change description is unenforced.

**The docstring's corpus measurement is TRUE.** Re-measured independently:

```
lines beginning with a pipe (col 0): 114
lines whose STRIPPED form begins with a pipe: 114
separators: 2      | # | headers: 2      rows parse() reads: 110
## sections: ['## Items', '## Bundles', '## Found during testing (2026-06-19/20)', '## Sequence', '## Notes']
pipe lines per section: {'Items': 109, 'Found during testing (2026-06-19/20)': 5}
```

114 − 2 − 2 = 110. The arithmetic holds. What it does **not** establish is anything about the
rule, and that is where the findings are.

---

## Summary

| Severity | Count |
|---|---|
| Blocking | 0 |
| High | 2 |
| Medium | 3 |
| Low | 3 |

The core mechanism works and is genuinely non-self-referential — `table_ish` reads the file's own
text, and I confirmed by mutation that the delete-the-feature mutation turns four cases red. The
findings are about **the population** (H-1), **what the reader is told once the note fires** (H-2),
and **the note not reaching the human at the moment it matters** (M-1).

---

## High

### H-1 — `header` is a SECTION latch, not a table bound; a second table in one section makes the warning fire on healthy content

`scripts/gen-backlog-page.py:739-747`

```python
        if not re.match(r"^\|\s*\d+\s*\|", line):
            # `header` bounds the POPULATION to a table this parser has claimed: a pipe-leading
            # line in prose, or in a table with no `| # |` header above it, is not a row we were
            # ever going to read and reporting it would make the warning noise.
            if unread is not None and header and table_ish(line):
                unread.append(line)
```

`header` is cleared **only** at `## ` (`:732`). It is never cleared when a table ends. So the
population is not "rows of the table this parser claimed" — it is *every pipe-leading line
anywhere after the first `| # |` header in the same `## ` section*.

Measured. A legend table — the single most likely second table for a file whose rows carry
🟠/🟡/🟢 markers:

```
--- A legend table in the same section: rows=[1] unread=['| Marker | Meaning |', '| 🟠 | high |', '| 🟡 | medium |']
```

Three UNREAD lines, on a completely healthy file, including the legend's own header. A wrapped-cell
continuation line does the same:

```
--- C prose starting with a pipe: rows=[1] unread=['| this is a continuation line | of a wrapped cell |']
```

And a fenced code block quoting the row format — `docs/backlog.md` has 0 fences today, but this
file's house style quotes shapes constantly:

```
--- B fenced example table: rows=[1, 7] unread=['| ⭐8 | bad | pending |']
```

Note that one: the fenced `| 7 | ... |` was **parsed as a real backlog row** (`rows=[1, 7]`). That
half is pre-existing, but the new code inherits the same fence-blindness and turns it into a
user-visible ⚠.

**This is the prompt's own question, and §21's own first row.** `docs/portable-practices.md:952`:

> | row insertion into a Markdown table | *"insert after the last table row"* | the last row **in the file** was in a SECOND table with a different column count, sharing one id space |

That is a *measured* instance in this repo of exactly this population error, on exactly this kind of
subject. The docstring cites §21 and then commits §21's row 1. The corpus measurement (114/2/2/110)
is a statement about today's `docs/backlog.md`, which happens to have one table per section — it
proves the rule has no false positives *on this corpus*, not that the population is right. §21's
instruction is to ask the two questions separately; the answer to the second one here is "every
pipe-line after the first `| # |` header in a section", which is strictly larger than the set the
rule is about.

**What I would change:** clear `header` when the table ends, not when the section does. One line in
the walk — reset `header = []` on any line that is not `table_ish` and not blank (or simply on a
blank line, which is what terminates a Markdown table). Then the population becomes "the contiguous
table this parser claimed", which is what the comment already says it is. Add a case: a legend table
after the items table in the same `## Items` section reports nothing.

---

### H-2 — the page tells the reader the opposite of the note, and points at the wrong file

`scripts/gen-backlog-page.py:1043` folds the note into `drift_notes`; `:1163-1170` renders that box
with fixed prose above and below.

Rendered, with one unread line (real run against `docs/backlog.md`, tags stripped):

```
⚠ this view is built from a grouping that has drifted
  UNREAD: 1 line(s) in docs/backlog.md look like table rows and were not read, so they are on no
          count and no card on this page
  UNREAD: | ⭐7 | 🟢 **Drop bullet labels** — … | render.ts | S | C | pending |
  UNREAD: the number cell must be a bare integer — no ⭐, no #, no leading space

  The items themselves are current — every row on this page was read from docs/backlog.md in this
  run. What is out of date is the hand-written grouping in scripts/gen-backlog-page.py.
```

Three things are wrong for this note class, in the same box:

1. **The heading is false.** Nothing has drifted in the grouping. A row was unreadable.
2. **The closing sentence directly contradicts the note it sits under** — "every row on this page was
   read from `docs/backlog.md` in this run". Technically defensible (the unread row is not *on* the
   page), and that is what makes it worse: its whole job is to reassure the reader the page is
   complete, printed immediately below a line saying it is not.
3. **It sends the reader to the wrong file.** "What is out of date is the hand-written grouping in
   `scripts/gen-backlog-page.py`" — the fix for an unread row is in `docs/backlog.md`, which the note
   above says and the paragraph below overrides.

The change's own docstring cites r2 finding R2-9 — "an unactionable warning" that cost three runs —
as the reason the note quotes the line rather than counting it. That reasoning is right and then
undone by the container: the quoted line is actionable, and the paragraph under it tells the reader
to go edit the generator.

**What I would change:** do not fold this into `drift_notes`. It is a different claim with a
different remedy. Emit a second box (or split `drift` into "the grouping drifted" and "a row could
not be read"), with its own heading and its own closing sentence naming `docs/backlog.md`. If the
one-box shape is worth keeping, the closing paragraph must become conditional on `unread` being
empty. Case to add: the rendered fragment, given a non-empty `unread`, does **not** contain the
string "every row on this page was read".

---

## Medium

### M-1 — the hook that fires at the exact moment the defect is introduced discards the warning

`.claude/hooks/regen-backlog-page.sh:92-104`. The generator's output is captured into `$OUT` and
printed only on the **failure** path:

```bash
OUT=$(python3 "$REPO/scripts/gen-backlog-page.py" 2>&1) || {
  ...
  echo "$OUT" | tail -4
  ...
  exit 0
}

rm -f "$MARK"
echo "↻ backlog view regenerated — http://127.0.0.1:7391/backlog-table"
exit 0
```

`main()` returns 0 when it reports UNREAD, so the success arm runs and `$OUT` is dropped on the
floor. Demonstrated by running that exact shell shape against a stub generator that prints a
`⚠  UNREAD:` line on stdout and exits 0:

```
↻ backlog view regenerated — http://127.0.0.1:7391/backlog-table
^^^ that is everything the hook shows the human on the SUCCESS path
```

This hook is registered in `.claude/settings.json:61` and fires on edits to `docs/backlog.md` — i.e.
at the precise moment somebody types the decorated row. That is the highest-value delivery moment
the feature has, and the warning does not survive it.

Yes, the pre-existing GROUPS ⚠ lines have the same gap. The difference is that those are about rows
that *are* on the page; this one is about a row that is not, and the change is filed specifically to
stop a row disappearing unnoticed. Shipping the detector without opening its most timely channel
leaves the failure mode intact for anyone who does not press Refresh or read the page.

**What I would change:** print `$OUT`'s `⚠` lines on the success path too (a `grep '^⚠' <<<"$OUT"`
before the `↻` line), or have `main()` return a distinct non-zero-but-not-refusal code. The former is
smaller and does not disturb the failure marker logic.

### M-2 — the second delivery channel truncates, and the new note displaces the existing warnings out of it

`scripts/explainer-serve.py:1010-1013`:

```python
        warn = [l.strip() for l in (r.stdout or "").splitlines() if l.strip().startswith("⚠")]
        ...
            body["warning"] = " ".join(warn)[:400]
```

Measured end-to-end against the **real** `docs/backlog.md` with three rows decorated in-cell
(⭐ / `#` / leading space), by pointing `BACKLOG` at a doctored copy in a temp dir and calling
`main()`:

```
rc: 0  unread lines emitted: 5
TOTAL ⚠ chars: 781  -> explainer-serve caps at 400

SILENTLY DROPPED by the cap:
 ive version-aware regeneration** — deep-dive HTML serves a stale cache and the "Deep Dive" men
 ⚠  UNREAD: the number cell must be a bare integer — no ⭐, no #, no leading space
 ⚠  GROUPS still names 3 item(s) that are no longer open: [1, 5, 7] — dropped from their group for this build
 ⚠  10 open item(s) have no description in GROUPS: [89, 90, 92, 94, 100, 101, 104, 105, 107, 110]
```

Three effects, all measured in that one run:

* the third quoted line is cut mid-word;
* the `UNREAD: the number cell must be a bare integer` remedy line — the only line that says what to
  *do* — is lost;
* **both pre-existing GROUPS warnings are pushed out of the Refresh button entirely.** The new note
  is emitted first (`report_unread()` at `:2428`, before the `contradiction_errors` loop), so it wins
  the budget and the older warnings lose it.

The `[:400]` cap is pre-existing, but the new note is by far the largest ⚠ producer in the file and
this is a real regression in what the Refresh button shows.

Also visible in that run, and worth its own sentence: the dropped rows made the generator print
`GROUPS still names 3 item(s) that are no longer open: [1, 5, 7]`. Those items **are** open — they
are unreadable. A silently-skipped row does not merely vanish; it makes a *different* warning state
something false.

**What I would change:** put the remedy line first (or fold it into the summary line so it cannot be
cut), and cap the unread block itself — e.g. quote at most 3 lines and say "… and N more" — so one
class of note cannot consume the whole 400-char budget.

### M-3 — `table_ish` is narrower than "dropped by parse", and every silent miss is outside every case

The change's guarantee needs `table_ish` to accept **every** line `parse` drops that a reader would
call a row. It does not, and no case pins that direction. All measured, header established, run
against the delivered code:

```
in-cell star   '| ⭐2 | x | y |'                read=0 reported=1
in-cell hash   '| #3 | x | y |'                read=0 reported=1
leading space  ' | 4 | x | y |'                read=0 reported=1
star BEFORE the pipe '⭐| 2 | x | y |'          read=0 reported=0  SILENT MISS
hash BEFORE the pipe '#3| 2 | x | y |'         read=0 reported=0  SILENT MISS
bullet before  '- | 2 | x | y |'               read=0 reported=0  SILENT MISS

--- SEPARATOR_ROW misclassification ---
all-dash row   '| - | - | - |'                 read=0 reported=0  SILENT MISS
dash + colon   '| : | - | - |'                 read=0 reported=0  SILENT MISS

--- count('|') >= 2 boundary ---
truncated row  '| ⭐2 | x | y'                  read=0 reported=1
one pipe only  '|⭐2'                           read=0 reported=0  SILENT MISS
```

Two distinct causes:

* **`s.startswith("|")`** (`:694`) — any decoration placed *before* the leading pipe is invisible.
  This is the same defect class #110 is filed about (a decoration on the number cell), one character
  to the left. Note the note's own remedy line says "no ⭐, no `#`, no leading space", which reads as
  a promise that a leading ⭐ is covered. It is not.
* **`SEPARATOR_ROW = r"^\|[\s:|-]+\|$"`** (`:682`) — it has no minimum content and no position
  constraint, so any row whose cells are all blank, `-` or `:` is classified as a separator and
  silently dropped. `| | | | | |` — a half-typed row somebody is about to fill in — is the realistic
  member of this class, and it is exactly how a row gets lost.

Neither is catastrophic on today's file. Both are silent, which is the property the change exists to
remove, and neither has a case.

**What I would change:** require `SEPARATOR_ROW` to contain at least one `-` (`^\|[\s:|]*-[\s:|-]*\|$`),
which kills the all-blank and all-colon cases at no cost to real separators. For the pre-pipe
decoration, either accept a short non-pipe prefix in `table_ish` or state in the docstring that the
predicate is deliberately anchored at the line start and that a pre-pipe decoration is out of scope —
right now the code is silent about a limit its own message denies.

---

## Low

### L-1 — one new case survives all nine mutations, including deleting the feature

I ran a nine-mutation harness in-process (patching module globals, re-running `self_test()`, parsing
the `ok`/`FAIL` lines) over the delivered code. Baseline 99/99. Per-case kill map:

```
  KILLED by M1                       a ⭐ before the number is reported, not silently dropped
  KILLED by M1                       a # before the number is reported
  KILLED by M1,M4                    one leading space is reported
  KILLED by M1,M3,M4,M6              all three decorations are caught, and the readable row still parses
  KILLED by M3,M6                    the header and the separator are NOT reported — they are not rows
  KILLED by M2                       a table-ish line with no header above it is not reported
  KILLED by M3,M6                    prose and blank lines are not reported
  KILLED by M3,M5,M6                 a separator written with alignment colons is not reported
  KILLED by M3,M6                    well-formed tables report nothing unread
  *** SURVIVES ALL 9 ***             unread is optional — the existing call sites are unchanged
  KILLED by M8                       the note quotes the offending line rather than counting it
  KILLED by M9                       no note at all when nothing was unread
  KILLED by M3,M6                    the REAL backlog has no row the parser silently skips
```

(M1 = never append to `unread`; M2 = drop the `header and` bound; M3 = drop the `SEPARATOR_ROW`
term; M4 = no `.strip()`; M5 = drop `:` from the class; M6 = `table_ish` always True;
M7 = drop `count("|") >= 2`; M8 = count instead of quote; M9 = drop the empty early-return.)

**12 of 13 are falsifiable, and M1 — deleting the feature entirely — leaves 95/99 green with four
red.** That is a real result and the suite is in good shape. The exception:

`case("unread is optional — the existing call sites are unchanged", lambda: len(parse(DECORATED.splitlines())) == 1)`
(`:2001-2002`) passes with the whole feature deleted and under all nine mutations. It is defensible as
a signature-compatibility guard for the eleven other call sites, but as written it asserts a property
of the *pre-existing* parser, not of this change. Making `unread` a required parameter is the only
edit that reddens it. Either say so in the comment, or strengthen it to assert that the default path
also does not raise when a decorated row is present *and* that a caller passing `unread` gets the same
`rows` as one that does not.

### L-2 — half of one case's assertion is unreachable

`:1994-1995`:

```python
    case("the header and the separator are NOT reported — they are not rows",
         lambda: not any("Touches" in ln or "---" in ln for ln in _dropped()))
```

The `"Touches"` disjunct can never fire. The header line is consumed by the `^\|\s*#\s*\|` branch at
`:735` before control ever reaches the unread branch. Proven by forcing the predicate wide open:

```
with table_ish ALWAYS TRUE, dropped lines are:
    '|---|------|---------|------|--------|--------|'
    '| ⭐2 | 🟠 **Star** — a ⭐ ahead of the number | b.ts | S | A | pending |'
    '| #3 | 🟠 **Hash** — a # ahead of the number | c.ts | S | A | pending |'
    ' | 4 | 🟠 **Indent** — one leading space | d.ts | S | A | pending |'

any line containing "Touches"? -> False
any line containing "---"?     -> True
```

The case name promises two guarantees and pins one. Not wrong, but it reads as coverage that is not
there — drop the header half, or move it to a fixture where the header is *not* `| # |`-shaped (which
is the H-1 scenario, and would then fail).

### L-3 — `count("|") >= 2` is a clause of the new rule with zero coverage

M7 above — removing `s.count("|") >= 2` from `table_ish` — turned **0 of 99** cases red. The clause is
load-bearing for the "a line with a single pipe is not a row" claim and nothing in the suite would
notice its removal. One case (`_unread_of(["## Items", "| # | Item | Status |", "|---|---|---|", "|x"]) == []`)
would fix it.

---

## What I checked and found sound

* **The non-self-referential claim holds.** `table_ish` reads the raw line; nothing in the reporting
  path consults `parse`'s output. §21's "expectation and subject share a source" defect is genuinely
  fixed for the decorated-number class.
* **No HTML injection.** `:1168` renders every drift note through `html.escape(n)`, and the unread
  lines are raw file text. Verified in the rendered fragment.
* **Both success paths report.** `report_unread()` is called at `:2410` (no-Ask-tray) and `:2428`
  (normal). The `ShapeError` path returns 1 without reporting, which is correct — nothing was written.
* **Defaults are immutable.** `build(..., unread=())` and `parse(..., unread=None)` — no shared-mutable-default hazard.
* **No second-order breakage.** `check-docs.py`, `check-ratchet-contract.py`, `check-anchors.py`,
  `check-selftest-counts.py` and `gen-goals-page.py --self-test` are all green (output quoted above).
  `gen-goals-page.py` reads `ROOTS`/`DEPENDS` by regex and never calls `parse`, so it is unaffected.
* **Not refusing is the right call**, and the docstring argues it. I am not flagging it.
* **The out-parameter is the right shape** given eleven call sites and this repo's measured cost of a
  second implementation of one rule. I tried to construct an aliasing or accumulation bug across the
  `parse` → `build` → `report_unread` sharing of one list object and could not: `parse` only appends,
  and the two readers are pure.

---

## Verdict

**NOT CONVERGED.**

H-1 and H-2 are the two that must move. H-1 because the change's central claim is about the
population and the population is wrong in a way this repo has already measured once (§21 row 1);
H-2 because a reader who sees the note is then told, in the same box, that nothing is missing and to
go edit the wrong file — which reproduces the R2-9 failure the change cites as its own justification.
M-1 is close behind: the detector works and its most timely channel drops it.

M-3 and the Lows are smaller and could ride a follow-up, but M-3's `SEPARATOR_ROW` half is a one-line
regex fix with a one-line case and I would take it now.
