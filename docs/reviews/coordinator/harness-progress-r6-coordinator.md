REVIEW GAP: codex — the Codex CLI timed out on every candidate model and the gate did not run; this Claude adversarial review ran in its place per docs/plugins.md.

# Adversarial review — `harness-progress-output`, round 6 (stand-in for the Codex half)

**Verdict: NOT CONVERGED** — 1 High, 1 Medium, 2 Low. **No Blocking.**

| # | Sev | Finding | Status |
|---|---|---|---|
| H1 | High | the third `enumerate(..., 1)` start has a failing case, no entry, and the commit says all three were closed | **open** |
| M1 | Medium | the LOAD-BEARING verdict was measured at 458 mutations and tabulated beside a 466 result as one experiment | fixed in the working tree during this review |
| L1 | Low | `progress_line`'s docstring quotes 534 progress lines; the run emits 542 | fixed in the working tree during this review |
| L2 | Low | a retarget moved a code-bound anchor onto comment prose; the duplicate-anchor rule ignores `repl`, which is what forces it | **open** |

**This is the first round in six whose Blocking is not the previous round's fix.** The pattern the
brief most feared did not recur. Rounds 1–5 each introduced their Blocking in the prior round's
repair; `6a660454`'s repairs hold under re-measurement:

- `--mutate .` reproduces **466/466/466/0, exit 0** exactly as claimed;
- both anchor retargets carry the **identical mutation text** — same property, not a weaker one;
- the load-bearing verdict **survives re-measurement at the new manifest size** (466 killed / 465
  attributed — the shortfall of 1 is unchanged), so the number was stale but the conclusion was not;
- the diagnostic the whole branch exists to fix **works on the real CANNOT RUN path**, shown against
  a genuine control failure rather than a fixture.

H1 is the one thing that would have been caught by the round's own corrected predicate had it been
run over the `enumerate` family, and it is a coverage gap rather than a correctness defect.

## Proof of subject

```
$ git log --oneline origin/master..HEAD
6a660454 Round 5: a fixture must differ from itself along the axis it tests   <-- SUBJECT
d6f55881 Round 4: an input far inside the boundary pins nothing, a third time
c3d53a70 Round 3: the want was not the only thing deriving from its subject
5e4bd163 Round 2: a guard whose want moves with its subject has no ceiling
b64b4cbc Round 1: inject the reporter, instead of emitting progress
915dfa67 File the review round for the progress change — both halves NOT CONVERGED
7ae516fc The mutation harness says where it is, instead of going silent for minutes

$ git rev-parse HEAD
6a660454dacf43bc1acf7e9916e1b7cb0f0624b8

$ git show --stat 6a660454
 docs/dashboard-entries.md                          |  28 +-
 docs/reviews/claude/harness-progress-r5-claude.md  | 689 +++++++++++++++++++++
 .../coordinator/harness-progress-r5-codex.md       |  89 +++
 .../harness-progress-r5-codex.verdict.json         |  16 +
 scripts/check-plan-code.py                         |  77 ++-
 scripts/mutations/check-plan-code.json             | 112 +++-
 6 files changed, 1000 insertions(+), 11 deletions(-)
```

## Lens and method

The brief's items **3, 4, 5, 6** plus end-to-end behaviour; a concurrent reviewer holds items 1
and 2, and nothing below duplicates them.

Every measurement below ran over a control **proved green first**. Staging per the brief: `scripts`
copied, `supabase` / `docs` / `node_modules/typescript` / `.claude/hooks` symlinked, `$HOME`
redirected into the stage. Repo control: `python3 scripts/check-plan-code.py --self-test` →
`126/126 passed`. Stage control: same, `126/126 passed`.

---

## Blocking

None.

---

## High

### H1 — the third `enumerate(..., 1)` start has a failing case, no manifest entry, and the commit message says it was closed

**`scripts/check-plan-code.py:1013`** — the **re-control** loop.

The commit message states:

> M2 — five more edges with a failing case and no entry: `room - 1`, the stderr cap, and **three
> `enumerate(..., 1)` starts**.

There are three such sites, and only two gained an entry:

| site | what it is | entry? |
|---|---|---|
| `:981` | before-control loop | ✅ *"the before-control phase counts from zero…"* (disambiguated by the following `# SILENT UNLESS A CALLER ASKS`) |
| `:1013` | **re-control loop** | ❌ **none** |
| `:1058` | mutation loop | ✅ *"the mutation loop counts from zero…"* |

The round's own corrected predicate says the same thing:

```
$ # find.count(expr) > repl.count(expr), over every entry for this file
'enumerate(targets, 1)': 2 site(s) in source, 1 entry/entries MOVE it
     - the before-control phase counts from zero, so the first subject is rep…
'enumerate(muts, 1)':    1 site(s) in source, 1 entry/entries MOVE it
     - the mutation loop counts from zero, so the last mutation is reported a…
```

**MEASURED.** Staged tree, control green at `126/126`. Applying the missing mutation — the anchor
resolves exactly once —

```python
find = ('        for position, name in enumerate(targets, 1):\n'
        '            if progress is not None:\n'
        '                progress(position, len(targets), f"re-control {name}")')
# occurrences of find: 1
repl = find.replace("enumerate(targets, 1)", "enumerate(targets, 0)")
```

```
  [FAIL] every phase of --mutate reports its position when a caller asks: got [(1, 1, 'control scripts/thing.py'), (1, 1, 'value is two'), (0, 1, 're-control scripts/thing.py')] want [(1, 1, 'control scripts/thing.py'), (1, 1, 'value is two'), (1, 1, 're-control scripts/thing.py')]
  [FAIL] --mutate itself supplies the reporter, so a real run is not silent: got ['[1/1] control scripts/thing.py', '[1/1] value is two'] want ['[1/1] control scripts/thing.py', '[1/1] value is two', '[1/1] re-control scripts/thing.py']

124/126 passed
```

So this is precisely r4 L2's class — *a failing case with no entry* — surviving the commit that
claims to have closed it, in one of the three sites the commit enumerates explicitly. The
behaviour is guarded by the suite; what is missing is the entry that makes CI see the guard, which
is the entire subject of this round.

The entry is writable today: `"every phase of --mutate reports its position when a caller asks"`
matches **exactly one** red case, satisfying the attribution rule at
`scripts/check-plan-code.py:1158` (`w == f`, exact equality).

**Why it is High rather than Medium.** M2 was Medium as an unnoticed gap. This one was *named,
counted, and reported closed* — the failure is in the enumeration the round was scoped to fix, and
the declared count (three) disagrees with the artefact (two). A wrong count in a closure claim is
what makes the next round trust the sweep.

---

## Medium

### M1 — the LOAD-BEARING verdict is stale: it was measured over 458 mutations and is tabulated beside a 466-mutation result as "the SAME experiment"

**`scripts/check-plan-code.py:430-432`**:

```
    # Asked separately, with the same experiment, they disagree:
    #     `if err_keep else ""`  removed -> 458 killed, 457 attributed   LOAD-BEARING
    #     `if out_keep else ""`  removed -> 466 killed, 466 attributed   DEAD
```

The two rows come from **different corpora**. `458` is r4's manifest; `466` is this commit's. The
commit raised `EXPECTED_MUTATIONS["scripts/check-plan-code.py"]` 63 → 71 and the declared sum
458 → 466, and the `err_keep` row was carried forward unchanged from `d6f55881`.

That is not a bookkeeping nit here, because two of the eight entries this commit **adds** anchor on
the very expression the `err_keep` guard sits in. Measured — deleting `if err_keep else ""` from
the current file orphans exactly two anchors:

```
ORPHAN: the two kept halves are joined with no separator, fusing the last stderr line an…
   find: '    return "\n".join(p for p in (err[-err_keep:] if err_keep else "",'
ORPHAN: the stderr half is sliced from the FRONT, so a traceback is reported by its open…
   find: '    return "\n".join(p for p in (err[-err_keep:] if err_keep else "",\n                    out[-ou…'
```

The second of those **did not exist** when `458/457` was taken — it is new in this commit. So the
row labelled LOAD-BEARING describes a mutation space that no longer exists, in a table whose whole
rhetorical point is that the two clauses were "asked separately, with the same experiment".

**RE-MEASURED at 466.** Stage2: `if err_keep else ""` deleted, both orphaned anchors retargeted so
each carries the identical mutation (`"\n".join` → `"".join`; `err[-err_keep:]` → `err[:err_keep]`),
0 orphans remaining, stage control green at `126/126`.

```
FAILED — delivered scripts mutated: 38 file(s), 466 mutation(s), 466 killed,
         465 attributed to the case each names, 0 survivor(s)
EXIT=1
```

**The guard is still LOAD-BEARING, and the committed conclusion is right.** 0 control failures in
the run. The lost attribution is the same entry as before —

```
✗ mutation 'a flooded stdout is allowed to starve stderr of its half…':
  `expect` "...and a flooded stdout cannot evict stderr's traceback" matched 0 red case(s)
  — it was caught by something else: ['both streams flooded, and the stderr half is exactly
  half the window', '...and it is the END of each stream that is kept, never the start',
  '...and the window never exceeds its budget, however much is offered']
```

— the floor mutation described at `scripts/check-plan-code.py:444-447`, which drives `err_keep` to
0 with `err` non-empty. Worth noting for the record: one of the three cases now catching it
*instead* is **this round's new B1 case**, so the new fixture partially compensates for the deleted
guard without restoring the attribution.

So **the number was stale, the verdict was not**: the shortfall is 1 in both corpora
(457/458 then, 465/466 now). This is a defect of record, not of substance — which is why it is
Medium and not Blocking. The brief named this as the only result whose being wrong would change
what ships; it is not wrong.

### Note on the retarget discipline used for M1

Both retargets preserve the mutation text exactly and change only the surrounding context, so
neither weakens the entry it moves:

| entry | mutation before | mutation after |
|---|---|---|
| *two kept halves joined with no separator* | `"\n".join` → `"".join` | `"\n".join` → `"".join` |
| *stderr half sliced from the FRONT* | `err[-err_keep:]` → `err[:err_keep]` | `err[-err_keep:]` → `err[:err_keep]` |

---

## Low

### L1 — `progress_line`'s docstring states 534 progress lines; its own arithmetic gives 542, and the run emits 542

**`scripts/check-plan-code.py:1297`**, added by this commit:

> the RATE: one line per mutation plus one per control and re-control — **534 at this writing**, and
> it moves whenever the manifest does, which is why the arithmetic is given instead of the total.

The arithmetic it states is `mutations + 2 × files`. Read statically from the same file:

```
files: 38  sum: 466
predicted progress lines = 466 + 2 * 38 = 542
```

**MEASURED** — progress lines on the full baseline run:

```
$ wc -l < baseline-mutate.err
542
```

`534` is `458 + 2 × 38` — the **pre-commit** manifest. The paragraph exists to replace an unmeasured
recollection (it says so: *"the first draft of this docstring said '~25 minutes' from exactly that
unmeasured recollection"*) and states a total that the same commit made wrong by the eight
mutations it added. Nothing pins it: it is prose in a docstring, outside
`check-selftest-counts.py`'s population.

The self-correcting instinct in the sentence is right — the arithmetic *is* given, so a reader can
recompute. The stale total should be dropped or corrected to 542.

### L2 — a retarget moved a code-bound anchor onto comment prose, and the duplicate-anchor rule is what forces that

Exactly **two** existing entries were modified by this commit (the brief's "five anchors were
retargeted" counts the throwaway retargets inside the experiments, which are not in the tree):

```
=== CHANGED ENTRY: a quiet stderr no longer hands its unused half back, …
 BEFORE: [["max(half, window - len(out)))\n    out_keep = min(len(out), window - err_keep)",
           "max(half, window - len(out)))\n    out_keep = min(len(out), window - half)"]]
 AFTER : [["    out_keep = min(len(out), window - err_keep)\n    # ⛔ THESE TWO",
           "    out_keep = min(len(out), window - half)\n    # ⛔ THESE TWO"]]

=== CHANGED ENTRY: stdout's budget stops accounting for what stderr already took, …
 BEFORE: [["    out_keep = min(len(out), window - err_keep)\n    # ⛔ THE",  "… window)\n    # ⛔ THE"]]
 AFTER : [["    out_keep = min(len(out), window - err_keep)\n    # ⛔ THESE", "… window)\n    # ⛔ THESE"]]
```

**Both are FAIR.** The mutated text is byte-identical before and after in each case
(`window - err_keep` → `window` and `window - err_keep` → `window - half`), so each entry still
tests the same property, not a weaker one. That was the brief's item-4 question and the answer is
clean.

The durability is the finding. Entry *"a quiet stderr no longer hands its unused half back"* was
anchored to the **code line above it**; it is now anchored to the **comment line below it**. Both
anchors on that line are now distinguished from each other only by comment prose — `# ⛔ THESE`
versus `# ⛔ THESE TWO`, one a strict prefix of the other. This round had to retarget them *because
a comment was reworded*, and the retarget guarantees the same work next time the comment changes.

**Root cause, and it is mechanical.** `scripts/check-plan-code.py:870,876`:

```python
nm, anchors = e.get("name"), tuple(f for f, _ in e.get("edits", []))
...
if anchors and anchors in seen_anchors:
    problems.append(f"{man.name}: entry {nm!r} repeats the edit anchors of an "
                    f"earlier entry — it measures nothing new")
```

Identity is the tuple of **`find`** strings; `repl` is not part of it. Two entries that mutate the
same line in genuinely different ways are distinct coverage, but the rule refuses them unless their
`find` strings differ textually — and on this line the only available differentiator is a comment.
Including `repl` in the identity tuple would let both anchor on the bare code line and would still
refuse a true copy (the case the rule was bought for at `:864-869` — "entry 32 swapped for a
duplicate of entry 1").

Not a false green: an unresolved anchor fails loud at `:1087-1090` (*"anchor NOT FOUND — it was not
applied, so its 'caught' verdict would be meaningless"*), and a multi-match fails loud at
`:1079-1084`. This is maintenance cost, not lost coverage — hence Low.

---

## What held, with the measurement (named attacks that found nothing)

### Item 6 — `--mutate .` still reports 466/466/466/0

```
$ python3 scripts/check-plan-code.py --mutate .
OK — delivered scripts mutated: 38 file(s), 466 mutation(s), 466 killed, 466 attributed to the case each names, 0 survivor(s)
EXIT=0
```

Non-progress bytes on stderr across the whole run: **0** (`grep -vc '^\[[0-9]*/[0-9]*\] '` → 0), so
the nested-self-test silence claim holds too.

### End-to-end — a real control failure produces a genuinely useful report

This is the behaviour four rounds of coverage work could have drifted from, and it is the exact
scenario r5 B1 was about. A staged tree with `scripts/check-anchors.py` made to emit **2,136 B** of
stdout ending in `[FAIL] final case: got 3 want 4`, plus stderr ending in
`ValueError: THE ACTUAL CAUSE`:

```
$ python3 .../check-plan-code.py --mutate <stage3>
  ✗ CANNOT RUN — control run of scripts/check-anchors.py did not prove the suite works (exit 1)
    BEFORE any mutation was applied. Every verdict below would be an artefact. Treat this as NOT CHECKED.
    FFFFFFFFFFFF…FFFFF
ValueError: THE ACTUAL CAUSE
 does not need
  [ok] routine progress line number 18 — filler that a reader does not need
  [ok] routine progress line number 19 — filler that a reader does not need
  [FAIL] final case: got 3 want 4
NOT MEASURED — the mutation harness produced no coverage verdict. Treat this as NOT CHECKED.
exit 1
```

Both halves show their **end**: the exception that ended the traceback, and the `[FAIL]` line the
suite died on. Under the pre-r5 code this report would have opened with stack frames and 200
characters of routine filler and contained neither. The fix works on the real path, not only in
fixtures, and the CANNOT RUN framing, the exit code and the `NOT MEASURED` verdict are all correct.

### Item 5 — cases against entries, and recomputation

- **122** literal `case()` names; **71** manifest entries for this file (63 → 71, +8; sum 458 → 466,
  +8 — consistent).
- **0 duplicate case names.** A duplicate would make any `expect` naming it match two red cases and
  become unattributable the moment both went red.
- **0 `expect` names that do not resolve** to a literal case name, across all 71 entries.
- **Recomputation sweep, mechanical.** An AST pass over every `case(name, got, want)` in
  `_self_test`, flagging any `want` referencing a module-level production symbol, returns **2 of
  122**, and both are legitimate relational invariants rather than r2-B1 ceilings:
  - `:2839` `case("a missing entry is CANNOT RUN, one problem per absent path", len(_probs), len(HARNESS_TREE))` —
    the property *is* "one problem per absent path" over an empty root, so both sides must move
    together; the failure it is built for is a loop that skips an entry, and only `got` moves then.
    The comment at `:2836-2837` says exactly this.
  - `:1490-1492` `(0, (d3 / CHILD_HOME).resolve())` — the property is "inside the run's own tree",
    and `CHILD_HOME` names which subdirectory that is.
  - Every want added by this commit is a literal: `"E" * 200`, `400`, `(True, True, False, False)`,
    `466`.

### The `out_keep` DEAD verdict, checked by reasoning against the new corpus

`out_keep` is `min(len(out), window - err_keep)`, so it reaches 0 only when `len(out) == 0` or
`err_keep == window`. Walking all four manifest mutations that move terms of that expression —
`max(half, …)` → `max(0, …)`, `window - err_keep` → `window`, `window - err_keep` → `window - half`,
`half = window // 2` → `window // 4` — none drives `out_keep` to 0 with `out` non-empty, and with
`out` empty `out[-0:]` is `""` and is dropped by the `if p` filter regardless. The DEAD verdict
survives the eight new entries. (The commit measured this; the reasoning is the independent check,
not a substitute for it.)

---

### `progress_line`'s ceiling on the REAL corpus, not a fixture

r2 B1 was a want that moved with its subject, and r1 M2 was "the position is never what gets cut".
Both were cased against fixtures. Measured here against all **542** lines the real run emitted:

```
lines: 542
max width: 79      min: 24
lines OVER 79 chars: 0
truncated lines (end in …): 213
lines without a [n/N] head: 0
longest emitted line: '[1/466] --tick stops consulting the pause, so a paused plan advances again (ba…'
```

The ceiling holds exactly at 79 on a population of real manifest names (the longest of which the
suite pins at 232 characters), 213 of them long enough to be truncated, and the position survived
every one. This is the one claim on this branch that now has a corpus rather than a fixture behind
it.

### The coverage ratchet refuses a silent shrink, fast and legibly

Stage4, one manifest entry deleted:

```
$ python3 .../check-plan-code.py --mutate <stage4>        # elapsed: 0s
  ✗ scripts/check-plan-code.py: manifest holds 70 mutation(s), expected 71. Coverage cannot
    change silently — if this is deliberate, change EXPECTED_MUTATIONS in check-plan-code.py in
    the SAME commit and say why in the message
NOT MEASURED — the mutation harness produced no coverage verdict. Treat this as NOT CHECKED.
exit 1
```

It refuses **before** staging or running any suite, so a user gets the diagnosis in under a second
rather than seven minutes later.

### Manifest hygiene across the whole tree

Every manifest under `scripts/mutations/`, every entry, against its target file:

```
orphaned=0  multimatch=0  dup_anchor_sets=0  dup_names=0
```

---

## Concurrent edits to the working tree during this review

At **07:07:30**, while this review was running, `scripts/check-plan-code.py` was modified in the
working tree by another agent — not by me; I wrote only to my own temp stages and to this file.
The two edits address **M1** and **L1** above:

- the `430-432` table gains *"⚠ THOSE TWO WERE TAKEN AT DIFFERENT MANIFEST SIZES (458 and 466) and
  read as one experiment. Re-run at today's 466: the live arm gives 466 killed / 465 attributed —
  the SHORTFALL is the verdict, not the absolute number, and it is unchanged."* **That number
  matches my independent measurement exactly**, arrived at from a separate stage;
- the `progress_line` docstring drops the total entirely rather than correcting it to 542, and says
  why. That is the stronger fix — a derived quantity written as prose has no guard, and L1 is the
  second time this file has quoted one.

Both edits are comments only. Re-verified against the edited working tree: suite `126/126`, 0
anchors failing to resolve exactly once, and **H1 still stands** — the re-control loop is now at
`scripts/check-plan-code.py:1016` and the corrected predicate still reports *2 sites, 1 entry moves
it*. H1 is the outstanding finding.

---

## On the scoping, and whether a round 7 is warranted

The brief invited an argument if the coverage scoping looked wrong. It does not, and this round
produced the evidence that settles it rather than restating the reasoning.

The human's decision was to answer the four-round Phase 6 trigger with a coverage-scoped round, on
the ground that the recurring defect follows the **method**, not the module. `docs/dev-process.md`
says to read the trigger off the **cause, not the count**, and distinguishes two shapes: a genuine
non-convergence, versus rounds that stay productive because the artefact has nothing to execute.
This branch is the first shape — it executes — so the count alone was never the answer.

What decides it is the **character** of the findings, and it shifted this round:

| round | Blocking | introduced by |
|---|---|---|
| 1–5 | one per round | the previous round's fix |
| **6** | **none** | — |

The severity curve fell *and* the class changed. H1 is a missing manifest entry for a
progress-numbering detail; L2 is anchor durability; M1 and L1 are stale numbers in comments. None
is a defect in what `diagnostic_tail` or `progress_line` *do* — and the end-to-end measurement shows
both doing the right thing on the real path. That is the shape of a branch approaching convergence,
not one circling.

**Recommendation: file H1 and L2, fix H1, and do not convene Phase 6.** A round 7 scoped to
verifying H1's entry would be cheap and is the natural stopping point. A redesign of the diagnostic
subsystem is not warranted on this evidence — I could not show by measurement that any restructure
removes a defect rather than moving it, which is the bar the brief set, and the subsystem's
behaviour is now measured correct end to end.

One caveat against my own recommendation, stated rather than buried: this is **one** reviewer's
convergence signal, and this project has a recorded memory that *a single CONVERGED verdict was
wrong 4 of 5 times* and that *dual review halves are not redundant*. My verdict is NOT CONVERGED, so
nothing is being cleared on one reviewer's say-so — but the "character has shifted" judgement above
should be weighed against the concurrent Claude half before anyone acts on it.

---

## What I did NOT measure

- **Brief items 1 and 2** — the third fixture axis, and the independent corrected-predicate
  enumeration over every expression the branch touches. Held by the concurrent reviewer by
  agreement. My corrected-predicate work was scoped to the `enumerate` family (H1) and to the
  `err_keep` / `out_keep` / `min(len(out), …)` anchors (M1), not to all 17 edges.
- **The `out_keep` 466/466 and `min(len(out), …)` 466/466 runs were not reproduced by execution.**
  The brief named the `err_keep` row as the only one whose being wrong changes what ships, and that
  is the one I ran. The other two are checked above by reasoning over the new corpus only.
- **The 60,000-pair and 324-combination input sweeps** cited in the commit were not reproduced.
- **60 of 122 cases are named by no manifest entry.** I counted them but did not classify which are
  unreachable by any production edit versus genuinely unguarded — that classification is item 2's
  territory and overlaps the concurrent reviewer.
- **Concurrency caveat.** The baseline and the M1 experiment ran as two concurrent `--mutate .`
  processes. Both reported `0` control failures and `0` timeouts, and the baseline's tally is
  byte-identical to the committed claim, so neither shows contamination. If the M1 result had come
  back red on a *control*, it would have been re-measured alone before being believed.
