# Round 13 — CLAUDE half, PR #371 `backlog-249-260-fixes`, subject `5dacbf59`

Adversarial half, run AFTER the Codex half, against a commit that changed **documents only** — so
the subject is this session's own CORRECTIONS, not a fix to code. Mandate was to refute six named
claims, the first of which is a re-measurement that replaced a published figure. Every number below
was re-derived by an instrument I wrote, not by running the session's own; the one place I ran the
session's superseded instrument, I say so and say why.

⛔ **I changed no file under `scripts/`, no mutation manifest, and no document other than this
review.** Two of the findings below say code should change; neither was acted on, per the brief's
constraint that the guarded files must stay byte-identical to the tree `…r13-codex.verdict.json`
records.

**Where I worked:** two `cp -a` copies of the worktree in my own scratchpad, each with an
**isolated git dir** (a copy of the worktree gitdir with an absolute `commondir`), so that a guard
running `git diff` could not refresh the reviewed worktree's index. Nothing was measured in
`wt-backlog` except four read-only document gates.

## Blocking

**None established.** No claim in `5dacbf59` was found to be false in the direction that would make
a reader believe a defect is smaller or closed than it is. Every correction I could refute made the
finding **bigger**, which is the third time in this row's history that attacking its number has had
that result.

## High

**H1 — `docs/roadmap-to-launch.md:3101` still publishes the WITHDRAWN figure as a measured fact, and
`check-withdrawal.py` is GREEN over it. The rule that catches this is written down in this branch,
about this class, four paragraphs from the sentence it was written about.**

`docs/backlog.md:291` now says the 11/15/0 split was wrong and names the corrected one. The
roadmap — which `docs/dev-process.md` calls *"the compaction-proof source"*, the layer a resuming
session reconciles against git — still reads:

```
roadmap-to-launch.md:3100  **What is still OPEN after round 12:** #270 (the intermittent shard red, NOT DIAGNOSED), #272,
roadmap-to-launch.md:3101  #275, #276 (now fully measured — 11 unasserted of 26, a DECISION the owner owns), #277, #278, and
```

Measured, whole-corpus: `grep -rni '11 unasserted'` over `docs/` returns exactly three live hits —
`backlog.md:291` (which quotes it as explicitly withdrawn), `codex/…-r13-codex.md:65` (correct as
testimony about what the row said), and **`roadmap-to-launch.md:3101`, which asserts it**. There are
no others. So this is one clause, in one file, and it is the one file whose job is to survive
compaction.

⛔ **And a gate named for exactly this passed over it.** `python3 scripts/check-withdrawal.py` →
rc=0, *"ok — 5 figure(s) corrected, and none of them survives elsewhere in docs/ (5 correction(s)
examined across 393 document(s))"*. It keys on the withdrawn STRING; the roadmap paraphrases
(`11 unasserted of 26` vs the row's `11 UNASSERTED / 15 ASSERTED / 0 CANNOT RUN`), so the surviving
dependent is invisible to it. That blindness is not news — it is written in this branch, in
`docs/reviews/architecture-review-2026-10-13.md:284`:

> `check-withdrawal.py` passes with *"5 figure(s) corrected, and none of them survives elsewhere in
> docs/"*, which is true of the WITHDRAWN figure and structurally blind to the figures that DEPEND
> on it — which is where both stale numbers were. … **A withdrawal needs its dependents re-derived,
> not just its own string removed.**

The sentence was written on 2026-10-13 about two stale numbers in the architecture review. The
withdrawal performed later the same day, in the same session, left a dependent standing in a
different file. The rule is not missing; it was not applied.

⚠ The roadmap figure is also wrong in a second way a reader cannot see: it says *"11 unasserted of
26"*, and the corrected measurement is not merely a different numerator — it splits the remainder
into asserted, CRASHED and not-measurable. A reader who believes `:3101` believes both a wrong
count and a wrong shape.

**FAILS IF:** a figure the row records as withdrawn is stated as current anywhere under `docs/`
outside a quotation that marks it withdrawn.

---

**H2 — the corrected split is RIGHT, and the POPULATION it is a fraction of is wrong at the
committed tree in five separate ways. Measured; the published figures reproduce exactly on
`5ce6fed2` and not on `5dacbf59`.**

First, the part that survives: **I reproduced `14 UNASSERTED / 8 asserted / 3 CRASHED /
1 NOT MEASURED` site-for-site**, by a method that shares no offset arithmetic with `sever3.py`
(stdlib `ast.get_source_segment` for the arm texts, a placeholder swap in TEXT, and a read-back that
re-parses the mutated file and asserts the two arms really did exchange before any suite is run).
Controls green either side of every measurement. The full table is in *Checked and found SOUND*.

So the corrected numerator stands. What does not stand is the denominator, and the denominator is
the cost input for the ①/②/③ decision the row says the owner owns.

**(a) `check-plan-code.py:2949` DOES NOT EXIST at the committed tree — the "1 NOT MEASURABLE" is a
stale line anchor, and the site measures as ASSERTED.** This is the row's third instance of *the
measurement, not the subject*, in a row that already warns about the other two.

```
git show 5ce6fed2:scripts/check-plan-code.py | sed -n 2949p
                said = (f"the child wrote NOTHING to stderr ({len(se)} byte(s)) — which "
git show d56a00ae:scripts/check-plan-code.py | sed -n 2949p
        # ENTRY NAMES", so True over an empty `fails` contradicts the field's own definition.
```

The r12 fold added 120 lines to that file (`6796 → 6916`); the `said` chain is now at **`:3009`**.
`sever3.py`'s locator requires `min(arm lineno) == lineno`, so at `:2949` it finds no pair and
returns `SKIP — no pair located`. Mine returns `NOT MEASURED — my finder located no arm pair`. The
row reports that as a property of the site (*"is NOT MEASURABLE by the corrected instrument and must
not be read as covered by it"*); it is a property of the anchor.

Re-anchored and measured by hand, explicit string replacement, no offsets, in a full checkout:

| `check-plan-code.py:3009` (`said`, three-world chain) | result |
|---|---|
| control | **291/291 passed** |
| the first and third arms' distinguishing literals exchanged | **289/291** — `[FAIL] …and says so explicitly, so the missing inference is asserted and not assumed`; `[FAIL] the THIRD world is named as well: stderr that names no exception says so` |
| control restored | **291/291 passed** |

So the site is **asserted**, the honest split over the published 26 is **14 / 9 / 3 / 0**, and the
row's claim that its arms *"are asserted separately by named cases in that file's 291-case suite"* is
true — it just has a measurement now instead of an assurance. (The two cases are named by manifest
entries 136 and 142, whose `edits` anchor on those exact lines.)

**(b) 2 of the 8 "asserted" are SELF-TEST FIXTURES — the half of the Codex half's M1 that was
neither folded nor answered.** `check-banner-armed.py:1958` (`lead`) and `:1962` (`tail`) are inside
`_flush_scenario`, defined at `:1933` **inside `_self_test` at `:1212`**. Measured over all 26 by
walking for an enclosing `_self_test` at any depth: exactly those two are `inside_self_test=True`
and the other 24 are False. Exchanging fixture text changes the constructed scenario, which is why
cases go red; that red says nothing about whether a production message's world labels are asserted.
Codex asked for them to be excluded from the claim. They are still in the row, still in the 26, and
still in the asserted count.

**(c) all 3 "CRASHED" sites are ILL-FORMED exchanges, not instances of the shape — and the code
documents each of them as a crash barrier.** The row says *"3 sites CRASH when their arms are
exchanged … a kill, not a case asserting the label"*, which is true and stops one step short. In all
three, one arm is only **valid** under the condition that selects it:

| site | the exchange | what it raises |
|---|---|---|
| `check-ci-watched.py:234` | `stale = f"…{watching_sha[:8]}…" if watching_sha else ""` | `TypeError: 'NoneType' object is not subscriptable` — the None-guard moves to the other arm |
| `check-ci-watched.py:557` | `armed = f" (armed {watching_sha[:8]})" if watching_sha else ""` | the same `TypeError`, the same cause |
| `check-banner-armed.py:1186` | `detail = f"…tool calls"` ⟷ `detail = f"{unticked} unticked"` | `UnboundLocalError: cannot access local variable 'unticked'` — `unticked` is assigned only in the sibling arm |

These are not messages whose world labels can be exchanged; there is no exchange to perform. And the
repo already says so, in the lines immediately above two of them — `check-ci-watched.py:550-556`
(*"They are crash barriers, not branches; no case asserts them"*) and `check-banner-armed.py:1174-1176`
(*"It is a crash barrier, not a branch; that is why no case asserts it"*). So the finder's shape-match
is a false positive for three sites that the code had already classified, in writing, as the thing
#276 is not about. They belong outside the denominator, not in a third bucket inside it.

**(d) the population figures are the PRE-FOLD ones. The finder at the committed tree returns 48
non-cosmetic sites / 29 files and 27 non-cosmetic `check-*` sites / 16 guards — not 47 and 26.**
Re-derived with the row's own finder (`scratchpad/r276/find-world-selection.py`), with a
known-positive control:

```
finder over 5dacbf59 scripts/   NON-COSMETIC: 48 site(s) in 29 file(s);  cosmetic: 25;  check-* non-cosmetic: 27 / 16 guards
finder over the same tree with check-plan-code.py replaced by its 5ce6fed2 version
                                NON-COSMETIC: 47 site(s) in 29 file(s);  cosmetic: 25
```

So the published 47/26 were correct for `5ce6fed2` and are off by one for the tree the row is filed
against. The set difference is exact: `:2949` leaves (it is now `:3009`) and **two sites arrive**,
`check-plan-code.py:3007` and `:3009`.

**(e) and the arriving site is one the r12 FOLD ITSELF ADDED — a new instance of #276's shape inside
the fix for #276's shape.** `check-plan-code.py:3007` is the `observed` ternary the fold introduced.
Its own comment says so and claims coverage; the claim holds, and I verified it rather than reading
it:

| `check-plan-code.py:3007` (`observed`) | result |
|---|---|
| control | **291/291 passed** |
| arms exchanged | **285/291** — `[FAIL] …and it says WHICH world: an empty stderr is reported as the bytes OBSERVED` (+5 more) |
| control restored | **291/291 passed** |

So this is not a coverage finding. It is a **population** finding, and it is the row's own
propagation story happening one more time: the component whose headline is *"fixing it in one file
reached zero siblings"* grew a fresh instance of the shape while being fixed, and the row's
population does not count it.

**What the honest production figure is.** Drop the 2 fixtures and the 3 ill-formed sites, re-anchor
`:2949 → :3009`, add `:3007`: **22 production world-selection sites in `check-*` guards, of which 14
are UNASSERTED and 8 asserted.** 14 of 22, not 14 of 26 — the fraction goes from 54% to **64%**, so
the third correction to this row moves it in the same direction as the first two.

**FAILS IF:** the row's population figures do not reproduce when its own finder is run over the tree
the row is filed against, or a site it counts cannot be resolved in that tree.

## Medium

**M1 — #279 and #280 were filed in the backlog and NOT in the roadmap, while #277 and #278 from the
round before have both halves. "Filed, not folded" is the whole defence of this commit, and the half
of filing that makes a discovery survive was not done.**

`docs/dev-process.md`: *"A **discovered** step (a review finding that becomes work, a blocker, a
follow-up) goes into the roadmap **and** the task list in the same turn"*, and *"Findings that become
work go to `docs/backlog.md` **and** the roadmap in the same turn."* Measured, counting occurrences
in `docs/roadmap-to-launch.md`:

```
#272: 2   #275: 2   #276: 1   #277: 2   #278: 2   #279: 0   #280: 0
```

`git log -- docs/roadmap-to-launch.md` shows its last touch is `d56a00ae` — the round-12 commit. So
`roadmap:3100`'s list is *"What is still OPEN after round 12"* with no round-13 successor, and the
two Highs this commit deliberately left open appear in it neither by name nor by count. The backlog
rows are real and tracked, so nothing is lost outright; what is wrong is that the document a
resuming session is told to reconcile against git now understates the open set by two Highs and
misstates the one it does mention (H1).

**FAILS IF:** a backlog row filed from a review round is absent from the roadmap at the commit that
files it, while a row filed from the previous round of the same review is present.

---

**M2 — #280's `FAILS IF` is ALREADY SATISFIED at HEAD by two bounds this repository has accepted and
documented, so the row cannot be closed by the remedy it proposes. Measured against real CPython
3.12.9.**

The row's falsifier: *"a real exception named in stderr produces no heading, **or** a line that is
not an exception is reported as one."* Both halves are satisfiable today, for reasons unrelated to
either direction the row measured, and both are already written down as bounds in
`exception_headings`' own docstring:

| child | stderr | `exception_headings` | which half of #280's FAILS IF |
|---|---|---|---|
| `sys.tracebacklimit = 0; raise RuntimeError("REAL_KILLER")` | `'RuntimeError: REAL_KILLER\n'` | `[]` | *a real exception produces no heading* |
| `traceback.print_stack(); sys.stderr.write("READY\n")` | a real frame block, then `READY` | `[('READY', False)]` | *a line that is not an exception is reported as one* |

And the remedy the row proposes — *"Report every column-zero line after a frame block VERBATIM"* —
cannot fix the first one, because that child prints **no frame block at all**: measured,
`any(FRAME_LINE.match(l) for l in stderr.split("\n"))` is `False`, so a rule keyed on *after a frame
block* still returns `[]`. The remedy is a hypothesis and this one is measurably insufficient for
one of its own two directions.

The cheap repair is to the row, not the code: narrow the `FAILS IF` to the two directions actually
measured (a printed class name that is not a dotted identifier; a frame-shaped line inside an
exception message), or name the two accepted bounds as exclusions. As written, the row is
unclosable, and an unclosable row is indistinguishable from an unfixed one.

---

**M3 — the Codex half's L1 and L2 are neither folded nor filed; their resolution exists only in a
commit body, which is the failure mode #273 was filed in this same branch to name.**

* **L1** (the 47/26/25 arithmetic). `docs/backlog.md:291` is byte-for-byte unchanged on this point:
  it still reads *"26 non-cosmetic sites across 16 guards … (47 sites / 29 files across all of
  `scripts/`; a further 25 sites are cosmetic … excluded deliberately)"*, which reads as 26 + 25
  against a total of 47. The commit body supplies the intended reading (*"47 non-cosmetic sites (all
  of `scripts/`), 26 of them in `check-*` guards, and 25 cosmetic sites is a separate total — 72
  overall"*) — and the artifact a reader greps does not. The uncommitted `FINAL.md` has the
  unambiguous form; it is not in the repository. ⚠ Under H2(d) the figures also need re-deriving, so
  the edit this needs is not purely editorial.
* **L2** (the stale membership claim). `docs/reviews/architecture-review-2026-10-13.md:286` still
  reads **"AND ONE OF THE TWO IS MIS-GRADED BY THE AGENT THAT FOUND IT"** and names
  `rec.get("gate_ran")`, which `:282-284` — two lines earlier, in the same paragraph block —
  excludes from the two. `git log -- docs/reviews/architecture-review-2026-10-13.md` last touches it
  at `d56a00ae`, so nothing in `5dacbf59` changed it.

The commit message states both as findings. Neither is in `docs/backlog.md`, neither is in the
roadmap, and the brief's known-true list does not include them as deliberate deferrals. A finding
that is acknowledged and recorded nowhere a gate or a reader looks has not been deferred; it has been
dropped with a note.

## Low

**L1 — the DIRECTION claim is stated as a mechanism-level impossibility and is only measured as a
property of this corpus. The bound is 0 of 6, not "never".**

The claim, carrying a ⭐ in both the commit and the row: *"a broken splice can only turn a true
UNASSERTED into a false asserted, never the reverse."* Its mechanism is *a mangled splice is a
SyntaxError, a SyntaxError exits 1, and rc=1 was read as asserted* — which holds exactly as long as
every mangled splice fails to parse. Nothing guarantees that: a window shifted into a comment, or
into a region where the substituted text happens to be syntactically admissible, parses and runs,
and its verdict can then be wrong in either direction.

So I measured it rather than arguing it. Replicating `sever2.py`'s splice exactly (its own
`get_source_segment` texts at its own character-interpreted byte offsets) and classifying all 26
sites with no suite run:

```
SAME           19    the old splice and a byte-correct splice are the same file
SYNTAX-ERROR    6    the old splice does not parse -> rc=1 could ONLY be a false "asserted"
VALID-WRONG     0    the old splice parses and is not the byte-correct mutation
NO SITE         1    check-plan-code.py:2949 (H2(a))
```

**0 of 6.** The claim holds here, with a stated bound; it is not a theorem, and the repository's own
rule is to state the bound rather than the absolute (`a-forced-choice-test-cannot-fail`). ⚠ v1 of
this instrument modelled the old splice as a slice rather than a `get_source_segment` substitution
and returned 20/5/0 — **treat that run as NOT RUN**; it was caught by `check-paid-caller-arrival.py:444`,
which v1 called SAME and which the old severer reproducibly reports as rc=1.

There is a second, smaller thing the same measurement shows. **Six** of the published 26 verdicts
were produced by a source that does not compile, not three: `check-features.py:97`,
`check-test-counts.py:204`, `check-banner-armed.py:1958`, `:1962`,
`check-paid-caller-arrival.py:444` and `:446`. Three of the six happened to agree with the corrected
answer. The row names the three that FLIPPED, which is the right thing for a reader of the
conclusion and the wrong thing for a reader asking *which of these verdicts was measured?* — for
three of them the answer is "neither the old one nor the correction distinguishes a measurement from
a coincidence".

---

**L2 — #280's two directions have ZERO reachability in the delivered corpus, measured, and the row
states no bound — in a function whose every neighbouring bound carries exactly that grep.**

`exception_headings`' docstring states three bounds and gives each a reachability measurement
(`grep -rn 'tracebacklimit' scripts/` → 0; `print_tb|print_stack|…` → 0; `ExceptionGroup|TaskGroup|
asyncio` → 0 of 58). #280 is filed with the same marker as #277 and #279 and no such line. Measured
over `scripts/` at HEAD:

* dynamically-created exception classes (`type("…", (Exception…` ) → **0**;
* `__module__` assignments → **0**;
* `  File "` inside any string literal → **1 file, `check-plan-code.py`, lines 3950-4084, all inside
  its own `_self_test` fixtures** — zero production raise sites.

The children this harness runs are text-mutated copies of the repo's own scripts, so neither a
non-identifier printed exception name nor a frame-shaped line in a production exception message can
arise from a manifest edit today. That makes both directions **bounds**, not live defects — which is
not a reason to drop the row (a bound stated is the repo's own practice) but is a reason the row
should say so, and a reason I would grade the pair lower than the Codex half did. See *Where I
disagree*.

## Checked and found SOUND

**The corrected #276 split, reproduced site-for-site by an independent instrument.** Method: arm
texts from `ast.get_source_segment` (stdlib, byte-correct by construction), the exchange performed
as a three-step placeholder replacement in TEXT so there is no offset to get wrong, then a
**read-back verification** — re-parse the mutated file, re-locate the arms, and refuse to run a
suite unless they read back exchanged. Arms collected by walking each branch body in full rather
than its top-level statements only. Full checkout, prepared `.venv/bin/python` 3.12.9, control green
either side of every site.

```
UNASSERTED  14   explainer-delivery:134  handoff-path:169  live-schema:865 :891 :982 :1004
                 plan-file-tags:196  python-pin:817  ratchet-contract:1152  test-counts:132
                 test-counts:204  anon-exposure:635  paid-caller-arrival:444 :446
asserted     8   features:97  main-drivable:2303  review-recorded:947 :965  review-rounds:443
                 banner-armed:1177  banner-armed:1958 :1962
CRASHED      3   ci-watched:234 :557   banner-armed:1186
NOT MEASURED 1   plan-code:2949
```

Identical to the corrected tally, including the three sites the correction moved and the three it
re-bucketed as crashes. Two instruments, three methods, one answer. (What the buckets *mean* is
H2(a)-(c).)

**The two hand-verifications stand, re-done by a third method.**

| site | control | arms exchanged | control restored |
|---|---|---|---|
| `check-ratchet-contract.py:1152` (`GREW`/`SHRANK`) | 56/56 | **56/56 STILL GREEN** | 56/56 |
| `check-anon-exposure.py:635` (`LOCAL container` / `PRODUCTION (read-only claude_ro)`) | 74/74 | **74/74 STILL GREEN** | 74/74 |

Also reproduced: `check-live-schema.py:891` (119/119 → 119/119 → 119/119) and
`check-test-counts.py:132` (27/27 → 27/27 → 27/27). All three sites the row calls *"the three that
matter most"* are unasserted on my instrument too.

**Claim 4 — no guarded file changed, and the gate's own verdict logic really is satisfied.**
`git diff d56a00ae 5dacbf59 -- scripts/` is **empty**; `git diff --name-status` over the same range
is exactly three documents (`docs/backlog.md` M, the Codex review A, its verdict A). Run in the
worktree: `python3 scripts/check-review-recorded.py` → **rc=0**, final line *"ok — the final tree was
in the tree handed to backlog-249-260-r13-codex.verdict.json"*.

**Claim 5 — the replay figures.** `check-plan-code.py --self-test` → **291/291 passed**.
`--binding` → *"binding OK — **1557** anchor(s) across **1549** entries each resolve to exactly one
site; 67 expect(s) name no whole literal but ARE explained by one"*. `scripts/mutations/check-plan-code.json`
holds **147** entries (143 at `5ce6fed2`), and a structural JSON comparison against `5ce6fed2`
returns **exactly five** new-or-changed entries at in-file indices **135, 143, 144, 145, 146** —
matching the Codex half's claim exactly.

**Codex H1 (#280) reproduced in both directions, real children, CPython 3.12.9.**

```
raise type("bad-name", (Exception,), {})("ROOT_MARKER")        stderr ends 'bad-name: ROOT_MARKER'   -> []
__module__ = "bad-module"                                      'bad-module.Err: ROOT_MARKER'        -> []
raise RuntimeError('real\n  File "fake", line 1\nValueError: MESSAGE_ONLY')
     -> [('RuntimeError: real', False), ('ValueError: MESSAGE_ONLY', False)]   (one exception, two headings)
control: raise RuntimeError("PLAIN_MARKER")                    -> [('RuntimeError: PLAIN_MARKER', False)]
```

A third instance of the drop I added, not in the Codex half: `__module__ = "two words"` prints
`two words.Err: SP_MARKER` and also returns `[]`. And a near-miss that correctly does NOT drop: a
class literally named `class` passes `str.isidentifier()` and is reported. The row's account of
`_is_type_name` (`:534`) is accurate.

**Codex H2 (#279) reproduced — the fourth world is real.** Child: a passing assertion, `print("1/1
passed", flush=True)`, then `os._exit(1)`. Through the module's own `parse_fail_names` and the
branch's own expression:

```
rc=1  stdout='1/1 passed\n'  stderr=''   caught=True  fails=[]  attributed=False
control_is_green on the same child with os._exit(0): True
reaches the `elif not fails` branch: True
```

And it is none of the three worlds the message names: not a report-format defect (it printed its
tally on stdout), not a suite that never reached its cases (the case ran), not a case named on
stderr (stderr is empty). The row's description is exact.

**The THRASHING arming is properly made, not asserted.**
`docs/reviews/coordinator/backlog-249-260-r11-thrashing.md` applies `review-method.md:200`'s single
test (*can a redesign remove it?*) **per finding**, names the component, records which findings are
NOT evidence for it, and explicitly rejects the symptom list the method file warns about. The
`review-method.md:200` citation in the commit body is accurate and in context.

**The gate this review unblocks, and its siblings, measured with exit codes read from the process
and not from a pipe:**

```
check-review-rounds.py     rc=1  ✗ backlog-249-260 round 13: only codex — claude neither ran nor recorded a `REVIEW GAP:` line
check-review-recorded.py   rc=0  ok — the final tree was in the tree handed to …r13-codex.verdict.json
check-dashboard-entry.py   rc=0  ok — an entry block was added
check-docs.py              rc=0  Documentation integrity OK
check-anchors.py           rc=0  13 registered, all claimed; floor 22 held
check-backlog-closure.py   rc=0  WARN — 3 of 5 commit(s) claiming FILED add no backlog row
```

`check-review-rounds` is red for exactly one reason and this file is that reason.
`check-backlog-closure`'s warn names three OLDER commits (rounds 1 and 3, and a scoping commit) and
not `5dacbf59`, which does add its rows — so that warn is pre-existing and is not a round-13
finding.

**Whole-corpus guard sweep — every `--self-test` under `scripts/`, 68 suites, in a tree with git
present.** One non-zero: `subject_status.py` rc=1 at **16/17**, which
`scripts/check-ratchet-contract.py:374` already records verbatim as *"rc=1 — 16/17, a suite RED on
master that nothing runs"*. Nothing else in the corpus is red at `5dacbf59`, and no suite reported a
cannot-run.

## CANNOT RUN

⛔ **Treat every item here as NOT RUN, not as a pass.**

1. **A full local `scripts/check-plan-code.py --mutate .` — NOT RUN.** Excluded by the brief. No
   claim about population-wide mutation coverage at `5dacbf59` is supported by anything I did; the
   scoped single-site severances below are not a substitute.
2. **An independent CI replay — NOT RUN.** The CI states in the brief (8 shards + complete green,
   `schema-gates` green, `verify` red on `check-review-recorded` only) remain supplied evidence. I
   verified only that `check-review-recorded` is now rc=0 locally, which is a different measurement
   from the one CI makes.
3. **My first guard sweep returned rc=127 for all 68 guards — NOT RUN.** macOS has no `timeout`
   binary; every line of that run was `command not found` wearing a guard's name. Re-run without it.
4. **My second guard sweep ran without `.git` — NOT RUN.** It reddened five `subject_status.py`
   cases for an environmental reason (`last_commit` needs git) and could equally have turned a
   git-dependent case GREEN by skipping it. Superseded by the sweep in *Checked and found SOUND*,
   run against an isolated git dir.
5. **v1 of my splice-direction instrument — NOT RUN.** It modelled the superseded severer as a slice
   substitution rather than a `get_source_segment` substitution, and returned 20 SAME / 5
   SYNTAX-ERROR. Superseded by the 19/6/0 run in L1. It is in this list rather than deleted because
   the error is the same shape as the one round 13 corrected: an instrument whose model of its
   subject is off by a convention.
6. **`check-plan-code.py:3009` could not be measured by a naive arm exchange — not measurable that
   way, and that is a fact about the splice, not the site.** Both my textual swap and (at its stale
   anchor) `sever3.py` fail there: the first arm interpolates `observed`, which is bound only inside
   that branch, and the third arm has no enclosing parentheses, so a straight exchange is either a
   `NameError` or an `IndentationError`. H2(a)'s measurement exchanges the two arms' *distinguishing
   literals* instead, which is a legal severance of the same two worlds. Anyone re-deriving this
   should know the naive exchange is not available there.
7. **I did not establish that the 26-site inventory is complete.** I re-ran the row's own finder,
   which is the same instrument, so a shape it cannot see is invisible to me too. What I did
   establish is that the finder's output at the committed tree is 27 sites and the row says 26
   (H2(d)) — a disagreement about the SAME instrument's output, not an independent inventory.

## Instruments

* Prepared `.venv/bin/python` **3.12.9** (`wt-backlog/.venv`), with `.venv/bin` first on `PATH`.
  A bare `python3.12` raises `ParserUnavailable` by design and was not used for any measurement.
* **Two `cp -a` copies of the worktree in my own scratchpad** (`r13c/tree`, `r13c/tree2`), each
  given an **isolated git dir** — a copy of `/…/.git/worktrees/wt-backlog1` with `commondir`
  rewritten to an absolute path — so that `git diff` inside a guard could not write the reviewed
  worktree's index. `node_modules` is a symlink into the main checkout, so `HARNESS_TREE`'s
  TypeScript case has what it needs. Controls confirm the copies behave like the original:
  `check-review-recorded.py --self-test` 196/196 and `check-plan-code.py --self-test` 291/291.
* `r13c/xchg.py` — my severer. Independent of `sever3.py` in the three ways that matter: stdlib
  source segments instead of hand-rolled offsets, a textual placeholder swap instead of a splice,
  and a read-back verification that refuses to run a suite over a mutation it cannot confirm
  happened. Records each site's enclosing function, which is what made H2(b) visible.
* `r13c/direction2.py` — replicates the superseded severer's splice exactly and asks whether its
  output ever parses, with no suite run (L1).
* `r13c/hand3009c.py` — the hand severance of the three-world chain, explicit string replacement
  with a sentinel, asserting the file parses and the phrase count is 1 before running anything.
* `r13c/probe_h1.py`, `r13c/probe_h2.py` — real children through the delivered
  `exception_headings` / `parse_fail_names` / `control_is_green`, loaded from the committed file.
* `scratchpad/r276/find-world-selection.py` (the row's own finder) over `5dacbf59` and over the same
  tree with `check-plan-code.py` restored to `5ce6fed2` — the known-positive control for H2(d).
* `scratchpad/r276/sever2.py`, run once, deliberately, on four sites — only to confirm that the
  superseded instrument reproducibly reports `check-paid-caller-arrival.py:444` as asserted, which
  is what refuted v1 of my own direction instrument. Its verdicts are not used as evidence.
* Read first, before any measurement: `git log -1 --format=%B 5dacbf59`,
  `docs/reviews/codex/backlog-249-260-r13-codex.md`, both round-12 halves, the r11 thrashing
  determination, `docs/review-method.md:180-225`.

**Files written: one — this review.** `git status` in the worktree shows no other change;
`scripts/` and `scripts/mutations/` are byte-identical to `d56a00ae`.

## Where I disagree with the Codex half

**1. Its M1 is right about the split and makes the same category error it is correcting.** Codex
reports *"The observed split was 14 green / 12 nonzero, with **no cannot-run**"*, and separately
*"I exchanged the expressions at all 26 named sites"*. One of those 26 is
`check-plan-code.py:2949`, which does not exist in the tree it reviewed (`d56a00ae`) — the `said`
chain is at `:3009`. So either it located the site by name rather than by the published line, in
which case its 26 is not the row's 26 and its denominator silently differs; or it did not measure
that site, in which case **"no cannot-run" is the error it graded the row Medium for** — rc!=0
standing in for a measurement. Its text does not say which, and I cannot tell from the text. My own
run reports that site as NOT MEASURED and then re-anchors and measures it (H2(a)); the honest column
for `:2949` is not "nonzero".

**2. I grade #280 lower than High, and the row should carry a reachability bound.** Both directions
reproduce exactly as Codex describes — I reproduced them and added a third instance — but neither is
reachable in the delivered corpus today: zero dynamically-created exception classes under
`scripts/`, zero `__module__` assignments, and the only frame-shaped literals are inside
`check-plan-code.py`'s own self-test fixtures. Codex calls the dropped direction *"the exact harm the
diagnostic exists to prevent"*, which is true of the behaviour and not of the corpus. The
neighbouring bounds in the very same docstring each state their reachability grep; this one does
not, and the pair reads as a live defect because of it. Medium, with the bound stated — and the row's
`FAILS IF` needs the repair in M2 either way.

**3. Its L1 and L2 were not a reason to stop, and were not a reason to drop them either.** Codex
graded both Low, correctly. The commit answers them in prose and changes neither artifact (M3). I
agree with the grading and disagree with the disposition.

**4. Where I agree and want it on the record, because it is the load-bearing agreement.** Codex's
count of the fixture problem (`check-banner-armed.py:1958`, `:1962`) and its reading of
`check-ci-watched.py:234` as *"a kill, not an assertion"* are both correct and both go further than
the fold took them. H2(b) and H2(c) are that observation, measured over the whole population and
extended: 2 of 26 are fixtures and 3 of 26 are not instances of the shape at all.

---

**Convergence: 0 of 2.** Two Highs, three Mediums, two Lows. ⚠ Both Highs and M1 are
**document-only** repairs and none of them requires touching `scripts/`, so they are available
without disturbing the verdict head that `check-review-recorded` joins on. M2 is a repair to a filed
row's falsifier. The two Highs this round's commit left open (#279, #280) I do not re-report; the
brief records them as deliberate, and I found the deliberation sound.
