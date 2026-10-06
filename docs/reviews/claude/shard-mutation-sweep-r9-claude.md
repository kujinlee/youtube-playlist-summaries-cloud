# Round 9 — Claude half · `shard-mutation-sweep` · PR #366 · `8756c623`

**Mandate: refute.** Immediate subject `git show 8756c623` (round 8's Codex fold — and the one
commit no round has seen). Deliverable subject `git diff master...HEAD -- .github/workflows/ci.yml`.

**Verdict: CONVERGED on the freeze's own criterion** — **zero** findings of any severity in the
deliverable's load-bearing half (the matrix, `--shard0`, the partition, `mutation-sweep-complete`,
`fail-fast`, the timeout). **This is the FIRST such round, not the second.**

⚠ **Stated both ways, so the coordinator is not guessing.** By the stricter standing rule
([`review-method.md`](../review-method.md):108 — any finding aimed at the deliverable → CONTINUE)
this round is **not** clean: one Medium and one Low stand against the **merge artifacts**, and one
Low against the **deliverable's blast radius**. None is Blocking or High, and none is in `ci.yml`,
so by the freeze's routing table **nothing I found changes the merge decision.**

`fixes_nontrivial: false` (this half changed no tracked file; `docs/explainers/questions.md` was
already dirty on arrival and was ignored as instructed).

---

## Verification

Run at `8756c623` on 2026-10-06. Local Python is **3.14.4**; CI pins **3.12**, so a local
`check-python-pin` result is advisory and no attribution figure below is taken from a local sweep.

### The coordinator's six measured claims — all re-derived, all TRUE

| Claim | How I checked it | Result |
|---|---|---|
| `--self-test` 178/178 | ran it | **178/178 passed**, rc=0 |
| manifest for `check-plan-code.py` = 106 | `EXPECTED_MUTATIONS` + a second count straight off the JSON | **106** |
| declared sum 1211 | `sum(EXPECTED_MUTATIONS.values())` **and** `len(load_manifests(repo)[0])` | **1211** both ways |
| 1,219 anchors, 0 unresolved, 0 duplicate tuples | second implementation over `scripts/mutations/*.json`: counted find-strings, keyed `(file, anchor-tuple)` | **1,219** anchors, **0** duplicate tuples, 57 manifests |
| six document guards rc=0 | `check-docs`, `check-anchors`, `check-review-rounds`, `check-dashboard-entry`, `check-selftest-counts`, `check-backlog-closure` | **all rc=0** |
| CI: 8 shards + `mutation-sweep-complete` + `schema-gates` green, only `verify` red | `gh pr checks 366` | confirmed; `verify` fails **only** at `check-review-recorded (PR only)` |

The anchor and duplicate-tuple figures were derived by a **second implementation** rather than read
back from the script, so they are not the script agreeing with itself.

### Not measured, and why

- **`strategy.job-index` / `job-total` under a PARTIAL re-run.** Every run on this branch is
  `attempt 1` (fifteen checked), so the behaviour has never been exercised here and I cannot
  trigger a GitHub re-run. **NOT MEASURED** — see *Refutations attempted* §6.
- **The home-escape residue, behaviourally.** My injection reddened the subject file itself, so the
  control was not green and the result is discarded. **NOT MEASURED**; the structural half (grep for
  callers) is measured and is L3 below.
- **`--mutate .` unsharded** — forbidden by the brief, and a local shard would be a false
  `NOT MEASURED` on this machine anyway (the coordinator's 81 s / 120 s warning).

---

## Findings

### M1 — Medium · **MERGE ARTIFACT** · not caused by a previous fold (caused by two of them)

**The PR body's CORRECTIONS block is itself stale by 11 entries and 17 cases — the third generation
of the defect it exists to record.**

Exhibit, PR body lines 223–224:

| Claim in the body's correction table | Measured at `8756c623` |
|---|---|
| declared sum **1196** → **1200** | **1211** |
| self-test **160** → **161** | **178** |

The block is headed *"⟳ CORRECTIONS, 2026-10-06 — this body was one of four narration sites round 5
found stale"* and says *"Corrected rather than edited in place, so the drift is visible."* That
framing is an instruction to the reader to trust these as the current figures. They are not. Rounds
5 and 8 each repaired this exact site; the correction has now gone stale faster than the claim it
corrected, twice — which the body itself names as *"the shape this PR has produced most often."*

Same artifact, same class, smaller: the PR **title** asserts *"1,758s becomes 346s"* and `ci.yml`
records `353 s`. Both are local figures from one machine. CI's eight shards at this commit took
**172–239 s**. Nothing is overstated in the favourable direction, but the squash subject will
permanently carry a number no CI run has produced, and it is the only number most readers will see.

**Filed, not folded** (merge artifact, Medium). The cheap half is free, though: amending two cells of
the body costs nothing and is not a tracked-file edit.

### L1 — Low · **INSTRUMENT** · **caused by the round-8 fold** (it is the fold)

**The new `SHARD_FLAGS` collision guard is blind to the one collision the dict itself can
introduce — two keys that normalise to the same `dest`.**

The parser-construction block inside `main` (`scripts/check-plan-code.py:4729` — the `_taken`
snapshot; there is no `_build_parser` function, despite two comments naming one) takes the set of
taken names *before* the loop and never adds to it:

```python
_taken = ({_a.dest for _a in ap._actions}
          | {_s.lstrip("-") for _a in ap._actions for _s in _a.option_strings})
for _opt, (_zero, _help) in SHARD_FLAGS.items():
    if shard_dest(_opt) in _taken or _opt in _taken:
        raise ValueError(...)
    ap.add_argument(f"--{_opt}", metavar="I/N", help=_help)
```

So each key is compared only against the parser's **pre-existing** options, never against the keys
this loop has already registered.

Exhibiting input — measured, not reasoned:

```
SHARD_FLAGS = {"shard": <shipped>, "shard-x": (False, "a"), "shard_x": (True, "b")}

main([])                                   -> NO ERROR, rc=2      # guard does not fire
main(["--mutate", <root>, "--shard-x", "1/8"])
  -> rc=2  "CANNOT RUN — --shard-x, --shard_x are the same control with different bases;
            pass one. NOTHING WAS MEASURED. Treat this as NOT CHECKED."
```

Both keys map to dest `shard_x`; argparse accepts `--shard-x` and `--shard_x` as distinct option
strings, so it raises nothing, and the second silently owns the namespace slot.

⛔ **It is NOT a false green** — the condition is caught downstream, by `main`'s exclusivity
refusal, at rc=2 with `NOTHING WAS MEASURED`. What is wrong is narrower and is exactly the r8 Codex
Low's own subject: the sentence **blames the invocation** (*"pass one"*) for a **declaration
error** (the dict names one dest twice), which is one more shape for one mistake — the thing the
guard was added to collapse. The guard's claim, *"a colliding key is refused by name"*, does not
hold for the intra-dict case.

Why no case reaches it: `_collide()` installs exactly one extra key beside `shard`, so the helper
cannot construct a pair. Fix is one line — `_taken.add(shard_dest(_opt))` after `add_argument`, plus
a case passing two colliding keys. **Filed, not folded** (instrument, Low).

### Asked of me directly: `:4717`'s *"its only two readers"* — **CONFIRMED**, and worse than reported

Not filed as a new finding — the comment-over-claim class is already filed and the brief says another
instance changes nothing. Recorded because the coordinator asked, and because the form it takes here
is checkable without reading any prose.

`scripts/check-plan-code.py:4716-4717`: *"The dict is the single declaration; **this loop and the mode
check in `main` are its only two readers**."* Production readers of `SHARD_FLAGS` at HEAD, from
`grep -n SHARD_FLAGS` minus the declaration, the comments and `_self_test`:

| Site | Reader |
|---|---|
| `:4731` | argparse registration — the *"this loop"* it names |
| `:4751` | the mode refusal — the second one it names |
| `:4811` | **exclusivity** (`_given`) — not named |
| `:4821` | **zero-basedness** (`SHARD_FLAGS[_f][0]`) — not named |

⭐ **The strongest form of the confirmation is that the file contradicts itself about this number,
twice.** `:4092` (*"FIVE readers, not two"*) and `:4806-4808` (*"there were FIVE readers, not the two
it named"*) are both round 8's M1 — whose entire subject was that this count was wrong — and the
sentence they correct was left standing 75 lines below one of them. `grep` finds four distinct
sites; whether the fifth is `shard_refusal` reached through `mutate_delivered` is a question about
where you cut, which is precisely why a hand-written count is the wrong instrument. Three numbers,
one file, same session.

⚠ **And it is now positionally wrong as well, which is new in the unseen commit.** `8756c623` moved
`ap.add_argument("--compare", …)` to the line immediately after this comment, so *"this loop"* now
sits above `--compare` and 14 lines above the loop it describes. Same shape as `ci.yml`'s paragraph
that described a shell guard `d95908c0` had removed — which that file documents against itself.

### L2 — Low · **MERGE ARTIFACT** · not caused by a previous fold

**`check-merge-ready.py` now prints a permanent ⛔ line about a waiver that was deliberately
withdrawn, and the repo's own rule is to relay that output verbatim.**

```
⛔ review recorded: the body contains 'NO-REVIEW', which is not `NO-REVIEW:`.
   The gate matches that literal exactly — case, hyphen and colon.
```

⟳ **CLOSED DURING THIS ROUND — re-measured after the coordinator amended the body.** `grep -c
'NO-REVIEW'` over the live body is now **0**, and `check-merge-ready.py --pr 366` no longer prints
the ⛔ line at all. Recorded rather than deleted, because the exhibit above is the gate output this
round actually relayed, and because the ordering matters for the record: the token was **present**
when I ran the gate at `8756c623` and is **absent** now, so the coordinator's rewrite is the fix for
this, not its cause. **Nothing to file.** M1 is likewise now fixed in the body (`1196 → 1211`,
`160 → 178`, with the third-generation drift recorded in place).

The original claim, kept for the record: the token was in the body's own heading *"⟳ THE NO-REVIEW
WAIVER IS WITHDRAWN"*. The gate's
observation is literally correct and its near-miss detection is working as designed; the effect was
that every future relay of this PR's readiness — and `check-merge-ready`'s verdict is required to be
relayed verbatim — carries a line that reads as a live near-miss defect and describes prose. Cheapest
disposition: rename the heading to *"the review waiver is withdrawn"*. **Filed, not folded.**

### L3 — Low · **DELIVERABLE** (blast radius) · not caused by a previous fold

**One global manifest check genuinely did leave the required context: the home-escape scan.**

This is the surviving residue of a hypothesis I otherwise refuted (§5 below). `ci.yml`'s comment
lists what runs in every shard — *"the counts against EXPECTED_MUTATIONS in both directions, the
duplicate name and anchor refusals, the home-escape scan over every target and every replacement"* —
and for the first three that is true **and** they are additionally held inside `verify` by
`check-plan-code.py --self-test` (proved in §5). The home-escape scan is not: `home_escapes()` is
called from exactly one place that reads the delivered tree, `mutate_delivered`
(`scripts/check-plan-code.py:1798` and `:1809`, both inside `mutate_delivered`), which only the sweep invokes.

Measured (grep over `scripts/`, `.claude/hooks/`, `.github/workflows/`): the other five files
naming `home_escapes` / `expanduser` / `not-a-home-escape` are **subjects** of the rule or carry the
string as a fixture; `check-fixture-variation.py:623` names `'home_escapes.src'` only as a
parameter pair in its signature ratchet, not as an enforcer.

Consequence, bounded honestly: between this merge and the repository setting landing,
`required_status_checks.contexts` is `["verify", "schema-gates"]` (read from the API, below), so a
home-escape route newly added to a mutation **target** or to a mutation's **replacement text** would
red only `mutation-sweep`, which cannot block the merge button. The route it protects is a mutation
reaching the reader's pages under `~/explainers/`. Low rather than High because reaching it needs a
manifest or target edit that also has to survive review, and because the window closes with the same
one setting the PR already asks for.

**Behavioural half NOT MEASURED** — see *Verification*. **Filed, not folded** (the fix is a cheap
global-checks-only invocation, which does not exist today, so it is instrument work).

---

## What I tried to refute and could not

Under a freeze this is the round's product, so each item states the observation that would have
falsified it.

### 1. The partition — re-derived by RUNNING it, at the real size

Imported `check-plan-code`, loaded the **real** manifests, and compared
`shard_slice(muts, I, N)` for `I = 1..N` against the whole list, keyed on `(file, name)`:

```
entries loaded: 1211   problems: []   declared sum: 1211   all 1211 keys unique
N=    1 union=True disjoint=True total=1211 min=1211 max=1211
N=    2 union=True disjoint=True total=1211 min=605  max=606
N=    3 union=True disjoint=True total=1211 min=403  max=404
N=    4 union=True disjoint=True total=1211 min=302  max=303
N=    5 union=True disjoint=True total=1211 min=242  max=243
N=    7 union=True disjoint=True total=1211 min=173  max=173
N=    8 union=True disjoint=True total=1211 min=151  max=152
N=   16 union=True disjoint=True total=1211 min=75   max=76
N= 1211 union=True disjoint=True total=1211 min=1    max=1
N= 1212 union=True disjoint=True total=1211 min=0    max=1   empty_shards=[1212]  refusal fires: [1212]
```

Would have falsified it: any `union=False`, any `disjoint=False`, any `total != 1211`, or an empty
shard at `N <= 1211`. None occurred. The empty-shard refusal fires at exactly the first N where a
shard is empty and nowhere earlier.

**And the round-robin claim, which a count cannot show.** The three largest manifests spread across
all eight shards rather than clustering:

```
scripts/check-plan-code.py      (106)  {1:13, 2:14, 3:14, 4:13, 5:13, 6:13, 7:13, 8:13}
scripts/recall-llm.py            (96)  {1:12, 2:12, 3:12, 4:12, 5:12, 6:12, 7:12, 8:12}
scripts/check-review-recorded.py (68)  {1:8,  2:8,  3:8,  4:9,  5:9,  6:9,  7:9,  8:8}
```

⚠ **One measurement that sharpens a cost claim rather than refuting it.** Each shard mutates
**49–53 of the 57 target files**, so it pays controls for ~90% of them. `ci.yml` is right that the
control cost *"is repeated across shards rather than divided"*; what the number adds is that at
N=8 the *"must not pay for the suites of files it never touches"* saving is ~10%, essentially nil,
and the whole economy is the `1606/N` mutation term. This is consistent with the file's own
`153 + 1606/N` model and with #231. Not a finding.

### 2. Eight DISTINCT shards actually ran — the thing #230 says the aggregator cannot see

Read it out of the eight job logs by hand, which is what backlog #230 exists because nothing does:

```
job 112521633358 : measured over shard 1 of 8
job 112521633290 : measured over shard 2 of 8
job 112521633070 : measured over shard 3 of 8
job 112521633252 : measured over shard 4 of 8
job 112521633604 : measured over shard 5 of 8
job 112521633267 : measured over shard 6 of 8
job 112521633503 : measured over shard 7 of 8
job 112521633417 : measured over shard 8 of 8
```

Eight jobs, eight distinct indices, one denominator. Would have falsified it: a repeated index, a
missing index, or a denominator other than 8. **For THIS run, #230's blind spot is not a live
defect** — verified by hand, which is the only instrument that can.

⛔ **AND THE BUILD IT WAS VERIFIED AGAINST, because a tick without one is the defect
[`dev-process.md`](../dev-process.md) names:** commit `8756c623`, workflow run **37537354847**, read
2026-10-06. It expires at the next run. A hand-read is an observation, not a mechanism, so this
does **not** reduce #230's severity — the aggregator's blind spot is still total.

⚠ **What it does change is the COST of #230's fix, and I think r1's proposal is over-built.** The
evidence is already produced: `shard_label()` prints `measured over shard I of N` in every shard's
log, so nothing needs to be *computed* — only *collected*. r1 proposed each shard upload its
slice's entry names and the aggregator assert the union equals the manifest. That ships 1,211
strings through artifacts to re-prove a partition `shard_slice`'s own suite already holds (and that
§1 above re-derived at ten values of N). **One line per shard is enough** for every failure
reachable today: resolved `I`, `N`, the slice count, and a digest of the slice's sorted
`(file, name)` pairs. The aggregator then asserts N reports arrived, the indices are exactly `1..N`
distinct, every `N` agrees, the counts sum to the manifest size, and the digests are pairwise
distinct — which kills *N copies of one shard*, a missing index, and a mismatched denominator in
bytes rather than lists. ⛔ **Not by scraping the logs**, which is the brittle shape this repository
has paid for repeatedly: a grep over a log format is a second implementation of the rule
`shard_label` owns.

### 3. The aggregator, on a REAL red run rather than by reading `always()`

Run `37528420394` (`56eafeef`), where the nested-sweep defect reddened three shards:

```
mutation-sweep (1) failure   (2) failure   (4) failure
mutation-sweep (3) success   (5) success   (6) success   (7) success   (8) success
mutation-sweep-complete  failure
```

Both claims hold on live evidence: `fail-fast: false` let the other five run to completion and
report, and `needs.mutation-sweep.result` over a matrix is the aggregate, so three red shards make
the aggregator exit 1. Would have falsified it: a cancelled sibling, or a `success` aggregator.

### 4. The repository setting, read rather than assumed — and the one thing that makes requiring it SAFE

```
GET /repos/.../branches/master/protection -> required_status_checks.contexts
  ["verify", "schema-gates"]
```

So the sequencing warning in `ci.yml`, in the PR body, and in the 2026-10-05 `[needs-you]` dashboard
entry is **accurate**: `mutation-sweep-complete` is not required, and a red sweep does not block the
button today. All three sites say so; I could not find a merge artifact that omits it.

⭐ **And the half none of the three states, which I checked because requiring the context is the
owner's next action.** `ci.yml`'s `on:` block is `pull_request: branches: [master]` / `push:
branches: [master]` with **no `paths:` filter anywhere in the file**. That is precisely the
condition #137 turned on: a workflow-level path filter means the context never reports on a
docs-only PR, and a required check that never reports leaves the PR *pending forever*. There is no
filter, so **adding `mutation-sweep-complete` to the required contexts is safe and will not recreate
#137.** Would have falsified it: any `paths:` or `paths-ignore:` key in the workflow.

### 5. ⭐ The hypothesis I most expected to land, and it is false

**Hypothesis:** the sweep leaving `verify` moved the *global manifest invariant* out of the only
required context, so deleting mutation entries would merge green — the textbook false green, in the
guard whose whole purpose is to prevent coverage shrinking unnoticed.

**Refuted, by a controlled experiment.** `git archive 8756c623` into two scratch trees, `node_modules`
symlinked into both so the `HARNESS_TREE` cases can run, one entry removed from
`scripts/mutations/check-rc-contract.json` (17 → 16) in one of them:

```
CONTROL  (pristine)              python3 scripts/check-plan-code.py --self-test  ->  178/178 passed   rc=0
SHRUNKEN (one entry deleted)     python3 scripts/check-plan-code.py --self-test  ->  177/178          rc=1
  [FAIL] ...and the entry count they yield is the pinned sum, not a typed literal: got 1210 want 1211
```

`--self-test` is a step of **`verify`**, the required context, and it reads the manifests **on disk**
(`scripts/check-plan-code.py:4624`, `_repo = Path(__file__).resolve().parent.parent`), asserting
both `_live_problems == []` and `len(_live_entries) == sum(EXPECTED_MUTATIONS.values())`. So counts
in both directions and the duplicate name/anchor refusals are still held by a required check, in
well under a second, independent of the sweep. r3's H2 put those two cases there and the comment
above them anticipates exactly this attack vector ("backlog #173 proposes skipping the sweep … it
makes the only instrument that catches this class conditional"). The restructuring did not void it.

⚠ **The control is why this is reportable.** My first pass ran the non-self-test readers and
`check-selftest-counts.py` went rc=1 on the shrunken tree — which looked like a second catch. The
pristine control went **rc=1 too**: it was ambient (`check-plan-code` and
`check-paid-caller-arrival` suites red for want of `node_modules`), not a catch. Four other readers
— `check-ratchet-contract`, `check-fixture-variation`, `check-docs`, `check-anchors`,
`check-plan-file-tags` — are rc=0 under the shrink and genuinely do **not** see it. The only
surviving residue is L3.

### 6. The re-run hazard — stated, bounded, and already filed

The one path to *green over unmeasured work* I could construct and not close: if a partial re-run
("Re-run failed jobs") ever reported `strategy.job-index` collapsed to 0 while `job-total` stayed 8,
the re-run job would measure shard 1's slice and report as shard 3, and
`needs.mutation-sweep.result` would be `success` over a slice nobody ran. Nothing in the design
cross-checks it: `matrix.shard` is written out as `[1..8]` and **referenced nowhere in the steps** —
it exists only so the UI reads `mutation-sweep (3)` — so the one hand-written value that could
corroborate `job-index` is unused.

**Three reasons this is not a finding this round:**

1. **NOT MEASURED, and unmeasurable from here.** All fifteen runs on this branch are `attempt 1`;
   I cannot trigger a GitHub re-run, and GitHub's docs for the `strategy` context do not state the
   behaviour either way ([community discussion #52505](https://github.com/orgs/community/discussions/52505),
   [actions/runner#2810](https://github.com/actions/runner/issues/2810) document re-run quirks in
   matrices but not these two values). Asserting a direction would be an inference dressed as a
   measurement.
2. **The other branch is safe, not dangerous.** If `job-total` collapsed to 1 instead, `--shard0
   "0/1"` sweeps the **whole** manifest — strictly more work, so the failure direction is a timeout
   (loud, merge-blocking per #231), not a silent pass.
3. **It is already dispositioned.** Backlog **#230** names this exact blind spot in its own words —
   *"blind to … that N distinct shards ran rather than N copies of one"* — with round 1's proposed
   fix (each shard uploads its slice; the aggregator asserts the union equals the manifest and the
   indices are `1..N` distinct) recorded as **deferred**. Filing it again is the duplication #230
   was written to stop.

⚠ What I would say to the owner rather than to the backlog: `matrix.shard` is already in the file
and already costs nothing, and the measurable form of the one-line corroboration is a *second
declared value* — `--shard0 "$SHARD_INDEX/$SHARD_TOTAL" --shard-label "${{ matrix.shard }}"` with
`parse_shard` refusing a disagreement — which keeps `ci.yml`'s *"no logic lives here any more"* rule
intact because the comparison lands in tested code. That is #230's candidate fix at one-tenth the
size. Not folded, not filed as new.

### 7. `check-review-recorded` is the only red, it is a TRUE positive, and the unseen code is instrument-only

`verify` fails at exactly one step. Its message:

```
FAILED — 8 round(s) ran and guarded code was committed after every one of them.
  The closest (shard-mutation-sweep-r8-codex.verdict.json) never saw:
    scripts/check-plan-code.py, scripts/mutations/check-plan-code.json
```

Derived from git rather than trusted: `docs/reviews/verdicts/shard-mutation-sweep-r8-codex.verdict.json`
was added in **`8756c623` itself** — the same commit that changed `check-plan-code.py` (+87/−16) and
its manifest (+11). `git log 8756c623..HEAD` is empty, so there is nothing later to confuse it. The
gate is literally right, and the red is the correct state for a tree whose newest guarded change
postdates every filed verdict.

**What that unseen change is, reviewed here because nobody else has** — and it is entirely the
**instrument**: `ci.yml` is **not** in `8756c623`. Three repairs plus one self-inflicted fourth, all
in `_self_test` and `main`'s parser:

| Change | Verified |
|---|---|
| r8 High 1 — the two `SHARD_FLAGS` cases move from `--mutate .` to `--mutate <empty temp dir>` | the diff applies it to **both** call sites; CI shards 1, 2, 4 are now green where `56eafeef` had them red |
| r8 High 2 — the `shard_dest` round-trip case gains a leading-hyphen input `("-shard-x")` | `shard_dest("-shard-x") == "shard_x"`; `lstrip` then `replace`, and the pair `("shard-x", "-shard-x")` is discriminating where the single value was not |
| r8 Low — a colliding `SHARD_FLAGS` key raises one `ValueError` naming the key | reproduced all four: `mutate`, `compare`, `self_test`, `plan` each refuse by name. **Except the intra-dict case — L1** |
| self-inflicted fourth — `_collide` uses `main([])`, not `main(["--self-test"])` | `main([])` builds the parser and returns rc=2 for want of a mode; no re-entry |
| `--compare` moved above the `SHARD_FLAGS` loop | necessary and sufficient: `_taken` is computed after it, so a key named `compare` is now caught by the guard rather than by argparse |

So: **the red is the only thing standing between this PR and green**, and filing both halves of
round 9 in a commit that changes no guarded path clears it. The newly unseen code has now been read,
and it yields exactly one Low.

### 8. Three deliverable paths I probed and found closed

- **A matrix shorter than the denominator.** `SHARD_TOTAL: ${{ strategy.job-total }}` — there is no
  hand-written `/8` anywhere, so shortening `shard: [1..8]` to four entries gives `job-total: 4`.
  The silent-halving failure mode the comment warns about is structurally unavailable. (An
  `exclude:` key would reintroduce it, per GitHub's note that `job-total` ignores exclusions; none
  is present, and it is #230's territory if one ever is.)
- **A skipped shard, or a sweep step that never runs.** `needs.mutation-sweep.result` is non-`success`
  for `skipped` and `cancelled` as well as `failure`, and `if: always()` keeps the aggregator
  reporting instead of being skipped — which is the pending-forever shape. All six steps of
  `mutation-sweep` carry no step-level `if:` (re-verified; #230 measured the same).
- **The python pin in the aggregator job.** `mutation-sweep-complete` pins 3.12 with no
  `check-python-pin.py` step of its own, which looked like a gap. It is not: the rule is *every job
  pins or is exempt in writing*, the pin is present, `EXEMPT_JOBS` is empty, and `verify` runs the
  pin-took-effect assertion — which passed in CI at this commit.

---

## Findings table

| # | Severity | Deliverable or instrument | Caused by a previous fold? |
|---|---|---|---|
| M1 | Medium | **merge artifact** (PR body + title) | no — but it is the third generation of the site rounds 5 and 8 each repaired |
| L1 | Low | **instrument** (`check-plan-code.py:4729`, the `_taken` snapshot in `main`) | **yes — it IS the round-8 fold** (the collision guard added for r8's Codex Low) |
| L2 | Low | **merge artifact** (PR body heading vs `check-merge-ready`) | no |
| L3 | Low | **deliverable** (blast radius of moving the sweep out of `verify`) | no |

**Blocking: 0. High: 0. In `ci.yml`, the partition, or the aggregator: 0.**

Fold-class under the freeze (Blocking or High in the deliverable): **none**. Everything above is
filing-class.

---

## Merge readiness — relayed verbatim

```
pull request           : #366
base                   : origin/master
pull-request-only steps: 2 derived from ci.yml — dashboard entry ratchet, check-review-recorded (PR only)

  ok  dashboard entry    rc=0  ok — an entry block was added
  NO  review recorded    rc=1  ok — review recorded in this range: docs/reviews/claude/shard-mutation-sweep-r1-claude.m
  ok  review rounds      rc=0  ⚠ verdict corpus: 223 read — 31 meaningfully checked below, 192 PRE-CUTOVER (schema < 3:
     ⛔ review recorded: the body contains 'NO-REVIEW', which is not `NO-REVIEW:`. The gate matches that literal exactly — case, hyphen and colon.
  NO  mergeability       rc=1  mergeStateStatus is BLOCKED
  NO  CI                 rc=1  failing: verify

NOT READY — CI, mergeability, review recorded
  ⚠ A local gate sweep cannot answer the pull-request-only checks above. That is why this script exists and why 'all my gates are green' is a different claim.
```

`rc=1`. All three `NO` rows are the **same fact** — `check-review-recorded` is red, which fails
`verify`, which makes CI red, which makes `mergeStateStatus` `BLOCKED`. Filing round 9's two halves
in a commit that touches no guarded path clears all three at once. The ⛔ line is L2, not a defect.

---

## Verdict

**CONVERGED** on the freeze's criterion — zero Blocking and zero High, and zero findings of any
severity in `ci.yml`, the shard partition, or the aggregator. **This is the FIRST clean round for
the deliverable, not the second.** Under the stricter standing rule (any deliverable finding →
CONTINUE) the single Low at L3 keeps the counter at zero; it is the coordinator's call which rule
the freeze supersedes, and either way nothing here is fold-class.

The honest summary of a ninth round: **the deliverable survived everything I could run at it.** The
one defect I found in the never-reviewed commit is a Low in the instrument, in the exact class the
instrument has been paying for all branch. The one hypothesis with real teeth — that the required
check stopped guarding manifest coverage — is **false**, and provably so.
