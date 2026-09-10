# Adversarial review — `fix/backlog-110-parser-completeness`, ROUND 4 (Claude half)

Reviewer: Claude. Subject: the uncommitted working diff on branch `fix/backlog-110-parser-completeness`.
Date: 2026-09-10.

## Proof of subject

```
$ git rev-parse --abbrev-ref HEAD
fix/backlog-110-parser-completeness

$ git diff --stat
 .claude/hooks/regen-backlog-page.sh |  21 +
 scripts/check-selftest-counts.py    |   3 +
 scripts/gen-backlog-page.py         | 757 ++++++++++++++++++++++++++++++++++--
 3 files changed, 746 insertions(+), 35 deletions(-)

$ python3 scripts/gen-backlog-page.py --self-test | tail -2
  ok    the REAL backlog does not contradict itself about what is closed
152/152 passed

$ grep -n "def row_ish\|def is_delimiter\|def report_run\|def drift_notes_for" scripts/gen-backlog-page.py
717:def is_delimiter(line: str) -> bool:
740:def row_ish(line: str) -> bool:
757:def report_run(rows: list[dict], unread: Sequence[str]) -> None:
1078:def drift_notes_for(rows: list[dict], unread: Sequence[str] = ()) -> list[str]:
```

Two exact lines that exist only in this working diff:

* `scripts/gen-backlog-page.py:754` — `    return bool(sep) and len(head) <= 3`
* `scripts/gen-backlog-page.py:1100` — `            if ("no longer open" in n or "is not an open item" in n) else n`

`table_ish`, `in_table`, `after_header`, `SEPARATOR_ROW` and `fenced` do not appear in the file.
Working tree was left exactly as found (`git status --porcelain` identical before and after;
`152/152` re-verified at the end). All mutation work ran on an `rsync` copy at
`…/scratchpad/r4-claude/work/`, never on the repo.

## What I ran

1. **Read/report symmetry fuzz.** 13 trailing contexts × 11 decorations = **143 pairs**. For each,
   `parse` was asked whether the plain `| 111 | new | pending |` reaches the page, and separately
   whether the decorated twin is reported. **0 mismatches.**
2. **Mutation sweep**, two batches, **89 mutations** applied to a copy outside the repo, each run
   against a green control (`152/152`), each restored from a byte backup afterwards.
3. **Arm sensitivity**: the whole sweep re-run under a second `$HOME` populated with
   `~/explainers/*.html`, because the in-suite `main()` run changes which of `main`'s two success
   arms it exercises depending on that directory.
4. **Live-channel measurement**: `main()` run for real against a doctored backlog, terminal output
   captured verbatim; `explainer-serve`'s collector and the hook's `awk` executed against it.

**Mutation result: 66 killed, 18 survived** (excluding three no-op controls I planted, which
survived as expected — `unread_note/empty-returns-remedy`, `B2/main-out-default-used`,
`B2/box-heading-count-plus1` — and two provably equivalent mutants, noted under L-2 and L-3).

The core invariant is **sound**. Every finding below is about the ratchet, not the behaviour, and
none of them is a Blocking.

---

## Blocking

**None.** The read/report symmetry — the thing that has been wrong twice — held across all 143
probes, including the six contexts r3's `_CONTEXTS` already pins and seven it does not (fenced code,
blockquote, list item, horizontal rule, setext heading, a second `| # |` table with the same column
names, and one with different ones). The `header`-gated report gate now genuinely tracks the
`header`-gated read gate.

---

## High

### H-1 — the drift-note fixture is `_gnum = 17`, which is also in `DEPENDS`, so every GROUPS-side assertion passes on the DEPENDS note

`scripts/gen-backlog-page.py:2402`

```python
    _gnum = next(n for _, _, its in GROUPS for n, _ in its)
```

Measured: `_gnum` resolves to **17**, and `17 in DEPENDS` is **True**. So forcing it closed produces
*two* notes, one from each family:

```
GROUPS still names 1 item(s) that are no longer open: [17] — dropped from their group for this build
DEPENDS: #17 has a dependency but is not an open item
```

Every case built on `_drifted` is therefore satisfied by the DEPENDS note alone. Two mutations prove
it — both left the suite at **152/152**:

| Mutation | Effect |
|---|---|
| `drift_notes_for:1095` `notes += sanitise_groups(GROUPS, open_nums)[1]` → `notes += []` | the entire GROUPS family is deleted from the drift channel |
| `drift_notes_for:1100` `("no longer open" in n or "is not an open item" in n)` → `("is not an open item" in n)` | the GROUPS half of r3's H-1 qualification is reverted |

The second is the sharper one. The case named for it —

`scripts/gen-backlog-page.py:2419`
```python
    case("a `no longer open` note is qualified while anything is unread",
         lambda: "could not be READ this run" in _box(_drifted(["| ⭐2 | x |"]), _DRIFT)
```

— asserts only that the *substring* appears somewhere in the box. It does, on the
`is not an open item` note. The mirror-image mutation (`("no longer open" in n)` only) **is** killed,
by `a DEPENDS note is qualified too, not just a GROUPS one` at `:2374`. So the suite pins exactly one
of the two families r3's H-1 is about, and it is not the one the finding was originally raised on
(r3's H-3 quotes the terminal saying *"the flat, false 'no longer open'"*).

This is the shape this repo has a name for: fixing a premise instead of covering the branch. The
fixture is *not* vacuous — the box does render — but the assertion it carries is satisfied by the
wrong half.

**Change I would make.** Pick `_gnum` so it cannot be in `DEPENDS`, and assert per family:

```python
    _gnum = next(n for _, _, its in GROUPS for n, _ in its if n not in DEPENDS)
```
plus a case whose predicate names the GROUPS sentence explicitly, mirroring `:2374`:

```python
    case("a GROUPS note is qualified too, not just a DEPENDS one",
         lambda: any("no longer open" in n and "could not be READ this run" in n
                     for n in drift_notes_for(_rows_missing(_gnum), ["| ⭐%d | x |" % _gnum])))
```

Falsifier: reverting `:1100` to `("is not an open item" in n)` must go red, and deleting `:1095`
must go red.

### H-2 — `report_run`'s third channel is the only one firing on the real file today, and it is entirely unobserved

`scripts/gen-backlog-page.py:773-778`

```python
    still = undescribed(GROUPS, {r["num"] for r in rows if not r["closed"]})
    if still:
        print(f"⚠  {len(still)} open item(s) have no description in GROUPS: {still}")
        print("   They render under \"Filed, but nobody has described them yet\" — the page is "
              "complete, the prose is not.")
        print("   Add them to GROUPS in scripts/gen-backlog-page.py.")
```

Measured against the real `docs/backlog.md`:

```
undescribed() on the REAL backlog: [89, 90, 92, 94, 100, 101, 104, 105, 107, 110]
```

and in the real terminal output of `main()`:

```
'⚠  10 open item(s) have no description in GROUPS: [89, 90, 92, 94, 100, 101, 104, 105, 107, 110]'
'   They render under "Filed, but nobody has described them yet" — the page is complete, the prose is not.'
'   Add them to GROUPS in scripts/gen-backlog-page.py.'
```

Note that #110 — this branch's own item — is in that list. Three mutations, all **152/152 green**:

| Mutation | What is lost |
|---|---|
| `:774` `if still:` → `if False:` | the whole warning, silently |
| `:775` `⚠  ` → `   ` | the warning stops reaching the Refresh button and the hook |
| `:776` three-space indent → four | the two detail lines stop reaching the hook |

`report_run`'s own docstring is explicit that this is one of the three things the no-tray arm was
dropping: *"also silently dropped the GROUPS, DEPENDS and undescribed warnings"*. The suite pins the
UNREAD channel (`report_unread`, `:2426`) and the drift channel (`the terminal carries the SAME
qualified notes the page does`), and nothing at all pins this one — the only one whose population is
non-empty on the file as it stands.

This is r2's H-2 recurring one function later: the rule is well covered, and the *delivery* is not.

**Change I would make.** Assert on the real terminal output that already exists in the suite, rather
than adding a new fixture — `_main_end_to_end()[0]` contains the line today:

```python
    case("the undescribed-items warning is delivered, marked, and actionable",
         lambda: any(ln.startswith("⚠  ") and "have no description in GROUPS" in ln
                     for ln in _main_end_to_end()[0].splitlines())
         and any(ln.startswith("   Add them to GROUPS") for ln in _main_end_to_end()[0].splitlines()))
```

⚠ That case is only non-vacuous while `undescribed()` is non-empty, so it needs a companion pinning
the population, in the same shape §21 asks for:

```python
    case("…and that warning has something to report (the population is not empty)",
         lambda: undescribed(GROUPS, {r["num"] for r in parse(BACKLOG.read_text().splitlines())
                                      if not r["closed"]}) != [])
```

### H-3 — `gen-backlog-page.py` is in no mutation manifest, which is why r1/r2/r3/r4 each found a fresh crop of unfalsifiable cases

```
$ grep -l "gen-backlog-page" scripts/mutations/*.json
NOT in any mutation manifest
$ ls scripts/mutations/ | grep "gen-"
gen-dashboard.json
```

`EXPECTED_MUTATIONS` in `scripts/check-plan-code.py:396` carries `"scripts/gen-dashboard.py": 64` and
`"scripts/page_markup.py": 14`. The sibling page producer has 64 mutations running in CI. This file —
2,985 lines, 152 cases, the subject of four review rounds — has **zero**, so `--mutate .` never
touches it and no machine has ever asked whether any of these cases can fail.

The evidence that this matters is the round-by-round count of unfalsifiable cases found *by hand*:
r1 → 1, r2 → 9, r3 → 8, r4 → 15 surviving non-equivalent mutations. Every one of them was invisible
to CI at the moment it shipped, and every one of them was found only because a human went looking.
The branch did the right adjacent thing — it pinned the *count* by adding `gen-backlog-page.py` to
`check-selftest-counts.POPULATION` (`scripts/check-selftest-counts.py:92`, verified: *"32 script(s)
declare a count, every one verified by running it"*) — but a count says how many cases exist, never
whether any of them can go red.

**Change I would make.** I would not ask this branch to author 60 mutation entries; that is its own
slice. I would ask it to (a) add `scripts/mutations/gen-backlog-page.json` seeded with the mutations
named in H-1, H-2, M-1, M-2 and M-3 below — the five that revert this branch's own fixes — and
register the file's count in `EXPECTED_MUTATIONS`, and (b) file the remainder as a named backlog
follow-up rather than leaving the gap implied. Five entries with a manifest in place is a ratchet
that can only go up; zero entries is the state that produced four rounds of the same finding.

---

## Medium

### M-1 — `row_ish`'s "three characters" is pinned at 3 and at 24, and anything between drifts silently

`scripts/gen-backlog-page.py:754`

```python
    return bool(sep) and len(head) <= 3
```

The docstring claims:

> A decoration on a number cell is a character or two … Three characters is the line between
> them, and it is a JUDGEMENT: **both boundary cases are pinned in the suite, so moving it is a
> deliberate act rather than a silent one.**

Measured, that sentence is false in the upward direction. The positive case at `:2270` uses
`"-- | 5 | x |"` (head = `"-- "`, 3 chars); the negative at `:2273` uses
`"> paragraphs of literal \`|\` on GitHub…"` (head = 24 chars). Every value in between passes:

```
SURVIVED  rowish/prefix-4      SURVIVED  rowish/prefix-5
SURVIVED  rowish/prefix-8      SURVIVED  B2/rowish-prefix-20
SURVIVED  B2/rowish-prefix-23
```

Only `<= 2`, `< 3` and `== 0` are killed. So the threshold is pinned from below and free to travel
20 values upward, which is the exact direction that turns the detector into the cry-wolf failure
backlog #92 is about. The real corpus cannot help here — I measured the prefix-length histogram of
every pipe-bearing line inside a live-header region of `docs/backlog.md` and the only bucket is
`prefix len 0: 2 line(s)` (both delimiters). The population that would discriminate is empty, so the
suite is the only instrument there is.

**Change I would make.** Add the upper boundary case, so the pair brackets the value:

```python
    case("a FOUR-character prefix is prose, not a decorated row — the other side of the judgement",
         lambda: _unread_of(["## Items", "| # | Item | Status |", "|---|---|---|",
                             "note | 5 | x |"]) == [])
```

### M-2 — the `$` in `DELIMITER_CELL` is load-bearing and nothing observes it

`scripts/gen-backlog-page.py:714`

```python
DELIMITER_CELL = re.compile(r"^:?-+:?$")
```

Removing the `$` survives at 152/152 (`delim/cell-unanchored-end`, and its equivalent spelling
`B2/delim-cell-dot-star` → `r"^:?-+:?.*$"`). Measured failing input for the mutant:

```
row:    |--- draft, fill me in ---|---|
cells:  ['--- draft, fill me in ---', '---']
shipped is_delimiter: False      (reported as unread — correct)
without $           : True       (swallowed as this table's delimiter — silent)
```

The three negatives at `:2296` are `| : | - | : |`, `| | | |` and `| 5 | x | y |`. None of them has a
cell that *starts* with a valid delimiter run and then continues, so none can see the end anchor.
The docstring says *"ONE hyphen per cell, not three"* and enumerates three past spellings that were
wrong; this is a fourth direction it does not cover.

(The `^` is a different matter — `DELIMITER_CELL.match` anchors at the start regardless, so removing
`^` is a genuinely equivalent mutant. It survived, correctly.)

**Change I would make.** Extend the existing negative case rather than adding one:

```python
    case("a cell that is not a delimiter cell makes it not a delimiter",
         lambda: not is_delimiter("| : | - | : |") and not is_delimiter("| | | |")
         and not is_delimiter("| 5 | x | y |")
         and not is_delimiter("|--- draft, fill me in ---|---|"))
```

### M-3 — the ⚠ prefix on the drift notes is the delivery mechanism and is unpinned

`scripts/gen-backlog-page.py:771-772`

```python
    for note in drift_notes_for(rows, unread):
        print(f"⚠  {note}")
```

Changing `⚠  ` to `   ` survives at **152/152**, under both `$HOME`s I tested. The docstring three
lines above states the property it breaks:

> ⚠ The ⚠ prefix is the existing channel: `explainer-serve._regenerate` collects those lines into
> the Refresh button's warning

Confirmed at `scripts/explainer-serve.py:1010`:

```python
        warn = [l.strip() for l in (r.stdout or "").splitlines() if l.strip().startswith("⚠")]
```

Measured on the real output of `main()`:

```
  shipped, Refresh button shows: 2 warning(s)
  with ⚠ dropped              : 0 warning(s)
```

The case that looks like it covers this — `the terminal carries the SAME qualified notes the page
does` — tests `"could not be READ this run" in _main_end_to_end()[0]`, a substring of the note body.
It is indifferent to the prefix. Same gap on `report_run:775` (covered under H-2) and on
`main:2950`'s `⚠  WITHOUT the Ask tray` headline (`B2/no-tray-headline-no-warn`, survived).

**Change I would make.** Assert the marker, not the sentence, on the run that already exists:

```python
    case("every drift note reaches the Refresh button — it is marked ⚠, not merely printed",
         lambda: all(any(ln.startswith("⚠  ") and n[:40] in ln
                         for ln in _main_end_to_end()[0].splitlines())
                     for n in drift_notes_for(*_main_end_to_end_inputs())))
```

or, more cheaply and with the same falsifier, count `⚠`-prefixed lines in `_main_end_to_end()[0]`
against `len(drift_notes_for(...)) + 1`.

### M-4 — the hook's `awk` is executed, but against a fixture that cannot distinguish it from a two-pattern grep

`.claude/hooks/regen-backlog-page.sh:124`

```sh
echo "$OUT" | awk '/^⚠/ {p=1; print; next} p && /^   [^ ]/ {print; next} {p=0}'
```

r3's L-4 fix is real — it extracts and runs the program, and four of my six `hook/*` mutations died
against it. But two survived, and together they delete the entire `p` state machine:

* `hook/no-reset` — drop `{p=0}` → **survived**
* `B2/hook-drop-p-guard` — drop `p &&` → **survived**

Measured, the gutted program `'/^⚠/ {print; next} /^   [^ ]/ {print; next}'` is **byte-identical** on
the suite's `_SAMPLE_OUT` (`:2503`). It differs the moment ordinary prose sits between a warning and
an indented line:

```
input:   "wrote /x\n⚠  UNREAD: summary\n   UNREAD: detail\nordinary prose\n   an indented continuation of PROSE\n"
shipped: '⚠  UNREAD: summary\n   UNREAD: detail\n'
gutted:  '⚠  UNREAD: summary\n   UNREAD: detail\n   an indented continuation of PROSE\n'
```

The fixture is a hand-typed second copy of `main`'s output, which is the coupling this project keeps
paying for. Related and measured: `main:2980`'s URL line

```python
    print("     http://127.0.0.1:7391/backlog-table   (start: python3 scripts/explainer-serve.py)")
```

uses five spaces *specifically* so the awk does not treat it as warning detail — the hook comment says
so in capitals (*"⚠ EXACTLY THREE SPACES THEN A NON-SPACE. `main` also prints a five-space URL
line"*). Narrowing it to three spaces (`main/url-three-space`) survives at 152/152, because the awk
never sees `main`'s real output.

**Change I would make.** Feed the real thing into the real program — both halves already exist in the
suite:

```python
    case("the hook, run on main's ACTUAL output, keeps every warning and no ordinary line",
         lambda: (lambda got: "UNREAD:" in got and "have no description in GROUPS" in got
                  and "7391" not in got and "rows, " not in got)(
                      _hook_awk(_main_end_to_end()[0])))
```

That one case kills `main/url-three-space`, `hook/no-reset` and `B2/hook-drop-p-guard`, and removes
`_SAMPLE_OUT` as a second copy of the subject.

---

## Low

### L-1 — `.strip()` in `row_ish` is load-bearing only past three spaces, and the case uses one

`scripts/gen-backlog-page.py:753` — `head, sep, _ = line.strip().partition("|")`. Dropping `.strip()`
survives at 152/152. Measured indent sweep on the shipped code: 1, 2, 3, 4, 8 spaces and a tab are
all reported; without the strip, 4+ spaces stop being reported (head becomes 4 chars, over the M-1
threshold). The only case is `one leading space is reported` (`:2168`). Note the suite's own
`unread_note` fixture at `:2552` uses a *four*-space-indented row (`"    | ⭐2 | x |"`), so the
display path is asserted to handle an indent that the detection path is not asserted to find.
Fix: make `:2168` a sweep — `for n in (1, 2, 4, 8)`.

### L-2 — `bool(cells)` at `:737` is provably dead

`cells = s.strip("|").split("|")` — `str.split` never returns an empty list, so `bool(cells)` is
always `True`. Verified over `""`, `"|"`, `"||"`, `"|||"`, `" | "` (all yield a non-empty list).
Deleting it survives, and correctly so: it is an equivalent mutant, not a coverage gap. Worth
removing, because a defensive clause that cannot be False reads as a guarded case that is not one.

### L-3 — two `seen_delimiter = False` resets, each individually dead

`:844` (init), `:854` (on `## `), `:858` (on a `| # |` header). Removing the init or the `## ` reset
each survives, because `header` is emptied on `## ` and nothing is reported while `header` is falsy,
and the header branch resets `seen_delimiter` anyway. Removing the *header* reset also survives on
its own; removing the header reset **and** the `## ` reset together is what breaks the real file
(there are two `| # |` tables, at `docs/backlog.md:30` and `:150`, with delimiters at `:31` and
`:151`). So exactly one of the three is load-bearing and the suite pins none of them individually.
Fix: drop the two dead assignments, and add the two-`| # |`-tables-in-one-section case, which is
also the input that exposes L-6.

### L-4 — `extra > 0` and the 110-character cut are both off-boundary

`:817` `([f"… and {extra} more"] if extra > 0 else [])` → `extra > 1` survives: with exactly four
unread lines the note reads *"4 line(s) …"*, quotes three, and says nothing about the fourth. The
case uses nine (`extra = 6`). `:816`'s `[:110]` → `[:200]` also survives; the cut length is pinned
only by "longer than the cut is marked as cut", which holds for any cut. Fix: add a four-line case.

### L-5 — `contradiction_errors` in the drift list has an empty population

`:1094` `notes = contradiction_errors(rows)` → `notes = []` survives at 152/152. Measured:
`contradiction_errors(rows)` is `[]` on the real file today, so the corpus is empty and the fold of
this pre-existing warning into `drift_notes_for` is unverified in either channel. A synthetic row
(`sev == "done"`, `closed == False`) makes it non-empty; `drift_notes_for` should be asserted to
carry it.

### L-6 — `parse` can raise `KeyError`, and `main` catches only `ShapeError`

`:890` — `num, item, status = col["#"], col["item"], col["status"]`. Input:

```python
parse(["## Items", "| # | Key | Note |", "|---|---|---|", "| 7 | a | b |"])
→ KeyError: 'item'
```

`main`'s handler at `:2920` is `except ShapeError`, so this reaches the user as a traceback, not as
`REFUSED: …`. **Pre-existing** — the same two lines are on `master` at `690`/`699`, so this branch
did not introduce it. I raise it because this branch's `parse` docstring now argues a two-outcome
dichotomy that this input falsifies: *"where `header` is live, `| 5 | Bundle E |` in a legend is read
as item 5 **or raises on its width**"*. There is a third outcome — right width, wrong column names —
and it is the one that produces a traceback. Either widen the handler to
`except (ShapeError, KeyError)` or narrow the sentence.

### L-7 — which of `main`'s two arms the end-to-end case exercises is decided by `$HOME`

Measured. With `HOME` pointing at a directory with no `explainers/`, the in-suite `main()` run takes
the **no-tray** arm:

```
'⚠  WITHOUT the Ask tray — brief-compose.py could not lift one:'
'   brief-compose: no explainer directory at …/fakehome/explainers — run /explain-diff once first'
```

With `HOME` pointing at a copy of the real `~/explainers/` (52 pages), the same run takes the
**tray** arm (`Ask tray lifted`). So `…and the page it wrote carries the INCOMPLETE box` is asserting
about the fallback `args.out.write_text(fragment)` on a fresh clone and about the composed page on a
developer machine, and the case name says neither. It is not currently a hole — I re-ran the
arm-sensitive mutations under the populated `$HOME` and all of them still die, `main/no-tray-arm-silent`
via the source-shape proxy at `:2487` rather than via the run — but the proxies are doing load-bearing
work that the comment beside them describes as covering "the arm the end-to-end case did not happen
to take", and *which* arm that is, is not something the suite decides.

Related, and clean: I checked what the in-suite run writes. Under a redirected `HOME` **zero files**
were created outside the temp dir — `--out` goes to a `TemporaryDirectory`, the `NamedTemporaryFile`
fragment is unlinked in a `finally`, `attach_history` is stubbed, and `BACKLOG`/`attach_history`/
`sys.argv` are all restored in the `finally`. The one latent hazard is that `DEFAULT_OUT` is
`pathlib.Path.home() / "explainers" / "backlog-table.html"` and the suite has **no `HOME` redirect of
its own** — it is safe only because `--out` is passed explicitly at `:2462`. Given this project has
already paid for exactly that (`--mutate .`'s redirected `HOME`), wrapping `_main_end_to_end` in a
`HOME` redirect is cheap insurance rather than a finding.

### L-8 — `_main_end_to_end()` is called seven times, unmemoised

`grep -c "_main_end_to_end()" → 7`. Each call re-parses the backlog, re-renders the whole page and
spawns `brief-compose.py`. `_built` beside it *is* memoised, with a comment explaining why. Same
treatment would cut the suite's runtime meaningfully. Not a correctness issue.

---

## What I checked and found sound

* **Read/report symmetry** — 143 probes, 0 mismatches. Includes fenced code, blockquotes, list
  items, horizontal rules, setext headings and both flavours of second `| # |` table, none of which
  `_CONTEXTS` covers. The `header` gate is genuinely shared.
* **The stated gap** is drawn where the code draws it: `_unread_of(["## Notes", "| ⭐111 | … |"]) == []`
  and the plain twin raises `ShapeError`. Confirmed by direct probe.
* **`is_delimiter`** — 8 of 10 mutations killed, including all three spellings the docstring names as
  past failures (`| | | |`, `|---|---|---` without outer pipes, `| : | - | : |`) and the pipe
  requirement (`---` as a horizontal rule).
* **`report_run` / `drift_notes_for` duplication** — both callers reach one function; nothing is said
  twice. `report_run/drop-unread-call`, `drop-drift-loop`, `unread-not-passed`,
  `main/no-tray-arm-silent`, `main/tray-arm-silent`, `main/clear-unread-after-parse` and
  `main/build-not-given-unread` all die, under both `$HOME`s. r3's `unread.clear()` regression is
  genuinely caught now.
* **The `unread` out-parameter** does not change what is read (`parse/never-report`,
  `B2/read-gate-allows-indent`, `B2/read-gate-allows-star` all die).
* **`check-selftest-counts.py`** — the new `POPULATION` entry is verified by running the suite:
  *"32 script(s) declare a count, every one verified by running it"*, and the docstring's `# 152 cases`
  matches.
* **The in-suite `main()` run leaks nothing** — three globals saved and restored in a `finally`, zero
  files written outside the temp dir under a redirected `HOME`.

---

## Counts

| Severity | Count |
|---|---|
| Blocking | 0 |
| High | 3 |
| Medium | 4 |
| Low | 8 |

The three Highs are all one shape — a channel that reaches a human is asserted by its *content* and
never by the mechanism that *delivers* it — and H-3 is the reason that shape keeps coming back
undetected. None of them changes what this branch does; all of them change what a future edit can
quietly undo. H-1 and H-2 are small, local case additions. H-3 is the one worth arguing about, and my
recommendation is the five-entry seed manifest rather than a full one, so the ratchet exists and can
only rise.

**VERDICT: NOT CONVERGED**
