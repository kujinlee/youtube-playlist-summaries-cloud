# main-drivable round 11 — Claude adversarial half

**Subject:** worktree `wt-365`, branch `d2-main-drivable`, commit `70ad61d1` (merge of `origin/master`
= PR #366 into this branch). Interpreter: `/usr/local/bin/python3.12` (3.12.9) for every invocation.

**Charter:** rounds 1-10 converged on `scripts/check-main-drivable.py`. Round 11 exists because the
repo's own gate named two files the closest verdict never saw —
`.github/workflows/ci.yml` and `scripts/check-plan-code.py` — in their current merged form.

**Mandate: refute, not confirm.** What follows reports three findings, none of them in the
deliverable, and a list of claims I set out to break and could not. The refutations are the larger
part of the value here and are stated with their methods so the next round can attack them in turn.

---

## The defect class I most feared, and what I did about it

A merge of two long-running branches breaks things that neither branch's CI ever ran together. For
this pair the specific shape is: **#366 rewrote the mutation harness (staging, child env, sharding)
while this branch added the single most expensive target in the manifest.** The two had never met.
`docs/dev-process.md` records the exact precedent — *"the harness stages `HARNESS_TREE`, not
`scripts/` alone — four guards resolve their SUBJECT from the repo root, so a scripts-only tree gave
each a red control and left them unmanifested for weeks."*

`scripts/check-main-drivable.py` resolves its subject from the repository root (its population is
`scripts/check-*.py` on disk, `:4`), and its self-test contains at least one case that reconciles
`MAIN_DEBT` against that live population (`[ok] ...no pinned name complies`). So it is a member of
exactly the class that paid for that comment. **If its control went red inside the staged tree,
every one of its 183 mutation verdicts would be an artefact, and the coordinator's two locally-run
entries (`--shard 1/1000`) could not have detected it.**

I tested it directly rather than reasoning about it. Three real single-entry shards chosen to land
on `check-main-drivable` entries (its global manifest indices are 363-545, so with the round-robin
rule `muts[I-1::N]` at `N=1000`, `I ∈ {400,450,500}` lands inside that span):

```
shard 400/1000  control green · 1 killed · 1 attributed · 0 survivors   real 175.02s
shard 450/1000  control green · 1 killed · 1 attributed · 0 survivors   real 146.82s
shard 500/1000  control green · 1 killed · 1 attributed · 0 survivors   real 160.40s
```

**The feared class is refuted.** The control and re-control are green for this target inside the
staged harness tree, and the mutation dies through the case it names. This is the single most
load-bearing thing verified this round, and it was not verified by either earlier list.

---

## Findings

### 1. High — `mutation-sweep-complete` is not a required status check, so this branch's 183 mutation entries do not gate the merge button

**NOT in the deliverable** (a repository setting plus the merged `ci.yml`).

**Claim.** The merge moved the mutation sweep out of `verify` and into a matrix whose aggregate is
reported by `mutation-sweep-complete`. That job is correct and fail-closed. It is also not required,
so a surviving mutation reports red beside a green merge button.

**Evidence.**

- `.github/workflows/ci.yml:733-738` states the requirement and the ordering, in the file's own words:
  *"`verify` no longer runs the sweep, so until `mutation-sweep-complete` is in
  `required_status_checks.contexts` — a repository setting, which must land AFTER this file and never
  before it — a surviving mutation reports red and does NOT block the merge button. Nothing in this
  file can do that for you; say it in the pull request."*
- `gh api repos/:owner/:repo/branches/master/protection --jq '.required_status_checks.contexts'`
  → `["verify","schema-gates"]`.
- `gh api repos/:owner/:repo/rulesets` → empty, so no ruleset supplies it either. Both halves of
  GitHub's two protection mechanisms were checked; a classic-protection-only check would have been
  the weaker claim.
- PR #366 is `MERGED` at `2026-10-06T22:56:00Z`, so the stated precondition ("must land AFTER this
  file") is **already satisfied** and the setting is actionable now.
- PR #365 is `OPEN`; its body does not mention `mutation-sweep-complete`, `required`, or `contexts`.
- Unfiled: `docs/backlog.md` mentions `mutation-sweep-complete` only in row #230, which is about
  *what the job observes*, not whether it is required. The one closed row of this exact shape is
  #137 (`docs/backlog.md:165`), which was `🟠` for `schema-gates` — *"is NOT a required status check,
  so the fifteen schema gates can report RED and the PR merges anyway."* This is that defect again
  for a different context.

**Why it matters for #365 specifically, not just for master.** This PR's whole mechanical
contribution is two `verify` steps plus 183 mutation entries. The two steps are enforced, because
`verify` is required. The 183 entries — the evidence that the guard's own rule is mutation-covered,
and the larger half of ten rounds' work — land in a check that cannot block anything. Merging #365
as it stands ships a guard whose mutation coverage is unenforced on arrival.

**Proposed fix — HYPOTHESIS, not verified.** Add `mutation-sweep-complete` to
`required_status_checks.contexts` on `master`, and say so in PR #365's body per the file's own
instruction. I did not attempt the change (it is outward-facing and a repository setting).
⚠ Two things I did **not** establish: that the context name as reported matches
`mutation-sweep-complete` exactly on a real run, and that requiring it cannot reintroduce #137's
pending-forever shape. The second looks safe by construction — `if: always()` at
`.github/workflows/ci.yml:743` and no workflow-level `paths:` filter — but "looks safe by
construction" is what #137 was, so verify against a real run before changing the setting.

---

### 2. Medium — backlog #231 projects ~1.9x of shard headroom once #365 lands; the real CI run on this commit measures **1.31x**, 123 s short of #231's own FAILS-IF trigger

**NOT in the deliverable** (`.github/workflows/ci.yml` comments and `docs/backlog.md` row #231).

**Claim.** The cost model that chose `N=8`, and the dated threshold that tells the next person when
to re-tune it, both rest on one number: the per-run cost of `check-main-drivable.py --self-test`,
stated as "~30 s" in both. The number is low and #231's resulting headroom figure is wrong by
roughly half. ⟳ **Updated after this document was first written: CI has since completed on
`70ad61d1`, so the key quantity is now MEASURED on a real runner rather than projected — and the
measurement corrects my own estimate as well as #231's.** See *Measured on CI* below.

**Evidence — the sites.**

- `.github/workflows/ci.yml:563-564`: *"one guard (`check-main-drivable.py`) held 183 entries against
  its own ~30s self-test — ~87 of the ~90 minutes"*.
- `.github/workflows/ci.yml:636-639`: the worst case is *"~90 min (~5,100s) because one guard holds
  183 entries against a ~30s suite. There the control pass is ~107s, so mutation work is ~4,890s"*.
- `docs/backlog.md:257` (#231): *"183/8 x 30s ≈ 686 s per shard, taking the slowest shard to ~934 s
  and the margin to ~1.9x"*, with **FAILS IF:** any shard exceeds 1,500 s.

**Evidence — direct measurement, all on this machine, 438/438 passing each time.**

| condition | wall |
|---|---|
| cold, normal env | 64.11 s |
| warm, normal env | 54.47 s |
| warm, `PYTHONDONTWRITEBYTECODE=1` — the variable `child_env` sets | 74.40 s |

`run_suite_parts` (`scripts/check-plan-code.py:547-549`) invokes
`[sys.executable, name, "--self-test"]` with `env=child_env(d)`, so the third row is the condition
the sweep actually pays. The lowest of the three is 1.8x the modelled figure; the harness condition
is 2.5x.

**Evidence — `ci.yml`'s sizing block is also internally inconsistent, on its own numbers alone.**
`:563` puts this one guard at ~87 of ~90 minutes, i.e. ≈5,220 s. That alone exceeds the 5,100 s
`:637` assigns to the **whole** worst-case sweep, before adding the 1,606 s `:629` separately
measured for the other 1,211 entries. Self-consistently the worst case is ≈7,040 s, not 5,100 s,
which changes one row's sign in the decision table at `:641-646`: `N=4` is given as *"~1,436s =
23.9 min -> 1.25x under the 30-minute ceiling"* when the self-consistent figure is
214 + 6,826/4 ≈ 1,920 s ≈ **32 min, i.e. over the cap**. The chosen `N=8` survives either reading
(17.8 min self-consistent, vs the stated 13.8 min), so the conclusion is unaffected and is in fact
better supported than its own arithmetic shows.

**Measured on CI — run `37546762434`, commit `70ad61d1`, all eight shards green**
(`gh api repos/:owner/:repo/actions/runs/37546762434/jobs`):

```
mutation-sweep (1..8)   1310  977  659  856  1228  1304  1289  1377  s   (mean 1125, spread 2.09x)
baseline at a5fcd951     248  216  209  227   179   225   218   248  s   (mean  221, spread 1.39x; #231's own figures)
```

| quantity | #231 projects | measured |
|---|---|---|
| slowest shard | ~934 s | **1,377 s** |
| margin to `timeout-minutes: 30` | ~1.9x | **1.31x** (76.5% of the cap) |
| distance to #231's FAILS-IF (1,500 s) | not reached | **123 s short** — 91.8% of the way |
| round-robin spread at N=8 | "1.15x" (`ci.yml:648-649`) | **2.09x** |

**⚠ The measurement also corrects ME, in the opposite direction, and that matters more than the part
of my claim it confirms.** Deriving the runner's per-suite cost from the real numbers: the mean shard
grew 221 s → 1,125 s, i.e. **+904 s**, covering this shard's ~22.9 mutation runs plus the two added
control runs — 24.9 suite runs, so **~36.3 s each**. That is 1.21x the modelled 30 s, **not** the
1.8-2.5x my laptop showed. **My laptop overstates this runner by 1.5-2.0x, so the three timings in
the table above are weak evidence about CI and I withdraw them as such** — they establish only that
the figure is not 30 s on any machine I can reach. My predicted slowest shard (~1,460 s) landed
within 6% of the actual 1,377 s, but partly by luck: I applied an inflated per-suite cost to a
baseline that also understated the control floor, and two errors in opposite directions are not a
model.

**So what is wrong with #231 is smaller and sharper than I first claimed.** Its arithmetic is
`183/8 x 30s ≈ 686 s`, which misses two things: the per-suite cost (1.21x) and the **two extra
control runs per shard** that `check-main-drivable` adds, which the file itself says do not divide
by N (`ci.yml:581-583`). Together those take 686 s to the measured 904 s. The row's disposition —
*"Not a defect today; a dated threshold"* — survives. Its headroom number does not, and that number
is the whole reason the row exists.

**Proposed fix — HYPOTHESIS, not verified.** Amend #231 (do not file a new row — it already owns
this subject, the correct lever and a falsifier) with the measured slowest shard of **1,377 s at
`70ad61d1`, run `37546762434`**, a margin of **1.31x**, and the corrected arithmetic including the
two non-dividing control runs. ⚠ The FAILS-IF has **not** fired, so this is still not a defect
today; what changed is that the next reader is 123 s from the trigger rather than comfortably clear,
and #231's stated lever (raise `N`, never `timeout-minutes`) is the one to reach for. I did not
amend the row myself — this is a review half, and the brief says report only.

---

### 3. Low — four sites declare numbers about the deliverable that are stale, and two of them disagree with each other

**NOT in the deliverable** (`docs/dashboard-entries.md`, `docs/roadmap-to-launch.md`, a `ci.yml`
comment).

**Claim and evidence.** Actuals on `70ad61d1`: **438** self-test cases, **183** mutation entries,
**27 of 37** pinned. The tool prints them itself — *"44 guards on disk · 7 without main() · 37 in
population / 10 drive main() ... / 27 pinned as ADR-0014 identity debt"* — and `MAIN_DEBT` literally
holds 27 names at `scripts/check-main-drivable.py:123-151`. The declared 438 at
`scripts/check-main-drivable.py:6` is correct and is verified by running it
(`check-selftest-counts.py`: *"51 script(s) declare a count, every one verified by running it"*).

| site | says | actual |
|---|---|---|
| `docs/dashboard-entries.md:13428` | "73 cases, 18 mutations, 29 of 37 pinned" | 438 / 183 / 27 |
| `docs/roadmap-to-launch.md:2213-2217` | "74 cases, 18 mutations" … "Measured exposure 29 of 37" | 438 / 183 / 27 |
| `.github/workflows/ci.yml:390` | "Ships with 29 of 37 guards PINNED as identity debt" | 27 of 37 |

**Provenance, derived rather than recalled.** All three were correct at `840a7b43`, the branch's
first commit: `git show 840a7b43:scripts/mutations/check-main-drivable.json` has 18 entries and
`MAIN_DEBT` held 29 names. Round 1's commit `5d3f3c2c` took `MAIN_DEBT` to 27 and the manifest to 40,
and `MAIN_DEBT` has been 27 at every one of the 21 commits since. No round re-read these three
files. The two prose sites also disagree with each other about the same quantity — 73 against 74 —
which is the tell that neither was derived.

**Why nothing caught it.** `check-selftest-counts.py` is the guard for this class and its population
is script docstrings, so it is structurally blind to all three sites; `check-test-counts.py` reads
the roadmap's *test* counts, not a guard's case count. This is the fourth instance of the
declared-count-drift class that `docs/dev-process.md` records three `⟳` corrections for.

**Proposed fix — HYPOTHESIS, not verified.** Correct the three sites to 438 / 183 / 27. I
specifically do **not** propose widening `check-selftest-counts.py` to prose sites: a blocking gate
on a docs-only mismatch is the shape backlog #56 measured getting switched off, and
`check-backlog-closure.py` is already WARN-ONLY for that reason.

---

## Claims I set out to refute and could not

Each of these is a claim from the two prior verification lists, or one of my own hypotheses, that I
attacked by a method different from the one that produced it. Divergence would have been the signal;
there was none.

1. **The deliverable is byte-identical across the merge.** `scripts/check-main-drivable.py` is blob
   `34ffb91a` and its manifest `af1100e3` at *both* the branch parent `5651d28f` and `HEAD`. So
   rounds 1-10's subject did not move; only its environment did. This is why zero findings in the
   deliverable is a credible result rather than a thin one.

2. **The declared sum 1394 has real provenance — which the merge commit said it lacked.** Its
   message settles for *"1211 + 183 = 1394 is a cross-check that agrees, and agreement is not
   provenance."* It is derivable. With `merge-base = 0af517ce`: `EXPECTED_MUTATIONS` sums to
   **1178** over 57 files at the base, **1361**/58 at the branch parent, **1211**/57 at the master
   parent, **1394**/58 at `HEAD` — and 1178 + 183 + 33 = 1394 exactly. Stronger: **zero files had
   their count changed on both sides**, so there was no collision candidate anywhere in the dict;
   no key from either parent is absent from `HEAD`; and `HEAD` is below neither parent on any file.
   The three files master bumped (`check-plan-code` 77→106, `check-rc-contract` 15→17,
   `check-surface-recall` 19→21) took master's value while the branch held base values, which is the
   correct resolution. Coverage did not shrink, and that is now measured rather than asserted.

3. **Whole-manifest anchor resolution, by a third independent method.** The coordinator drove
   `run_mutations` with `run_suite` stubbed; Codex scanned each `find` against delivered source; I
   re-implemented the harness's rule from `scripts/check-plan-code.py:1968-1980` — sequential
   application against a mutating `src`, `src.count(find) > 1` → ambiguous, `find not in src` →
   not found — and ran it over all 1394 entries against the delivered tree. **0 problems**, 0 missing
   targets, 0 entries with an empty `expect`. Three methods, one answer. I also confirmed
   `load_manifests(".")` returns an empty problem list, which is the manifest-level check the other
   two did not separately report.

4. **Codex's rebuttal of the coordinator's stub concern is sound.** `run_mutations` resolves and
   applies the anchor at `:1959-1980` and calls `run_suite` only at `:1987`, so a stubbed
   `run_suite` cannot mask an anchor failure. Verified by reading the control flow, not accepted
   on assertion.

5. **`check-python-pin.py` survives the `ci.yml` auto-merge — verified *and falsified*.** The
   concern was real: it parses jobs by indentation (backlog #227), and an interleaving auto-merge
   could move a pin between jobs. `job_blocks` over both workflow files yields exactly
   `['verify','mutation-sweep','mutation-sweep-complete']` and `['schema-gates','prod-drift']`, each
   resolving exactly one `3.12` pin and zero unreadable scalar openers;
   `unpinned_jobs(all, exempt={})` → `[]`. **The part neither prior list reported: I falsified it.**
   Deleting the `mutation-sweep` pin in-memory yields `['ci.yml:mutation-sweep']`, so the pass is not
   vacuous. The branch's two new steps land inside `verify` (lines 26-556), not between jobs.

6. **`mutation-sweep-complete` is fail-closed for every failure mode reachable through the job
   result.** `if: always()` (`:743`) so it reports rather than skipping, and
   `needs.mutation-sweep.result != "success"` → `exit 1` (`:752-757`), which the comment correctly
   notes is the matrix *aggregate*. A cancelled, failed, skipped or timed-out shard therefore fails
   it. Its residual blind spot — it cannot see that eight *distinct* shards ran, or that their slices
   unioned to the manifest — is already filed and explicitly deferred as backlog #230. Finding 1 is
   not this: #230 is about what the job observes, finding 1 is that nothing requires the job.

7. **`docs/backlog.md` is exactly the union of its two parents.** 233 distinct rows, **zero**
   duplicate ids, nothing lost from either parent, nothing present that is in neither
   (`HEAD == branchP | masterP` exactly). Ids 220 and 221 are absent from `HEAD` **and from both
   parents**, so they were never allocated — not a merge loss, which is what the shape first
   suggested. The discarded longer #217 diagnostic was a deliberate resolution (master closed #217),
   consistent with the roadmap, and the information is preserved in #231's citation of it.

8. **`docs/roadmap-to-launch.md` auto-merged to the semantically right state.** This was worth
   attacking because an auto-merge is git saying the *text* did not collide, not that the semantics
   did not — and lines were dropped from both parents. Both drops are correct: `#217` → `[x]`
   (master's closure winning, `:2263`, a one-character diff from the branch parent) and `D2` → `[x]`
   carrying the branch's BUILT text (`:2213`, replacing master's unticked draft). The file's #217
   tick and `docs/backlog.md`'s now agree.

9. **A sixth file is a true merge edit that the merge commit does not enumerate, and it is clean.**
   The message accounts for five files ("three conflicts" plus `ci.yml` and the roadmap
   auto-merging). `docs/memory/MEMORY.md` also differs from both parents and is listed nowhere. It
   is a clean union: 165 lines against 163/164, no line lost from either parent, no duplicated
   bullet row. A gap in the merge's own account rather than in the tree — not filed as a finding,
   but recorded so the next reader does not re-derive it.

10. **Three duplicate mutation *names* exist globally, and this is correct by design — not a
    finding.** I expected a defect here, since `docs/dev-process.md` says duplicate names are
    refused. The refusal at `scripts/check-plan-code.py:1514` keys on `man.name`, i.e. per manifest
    file, and all three pairs span *different* manifests targeting *different* source files
    (`check-banner-armed`/`check-ci-watched`, and two pairs across
    `check-rc-contract`/`check-surface-recall`). Each file's suite runs separately, so attribution
    is unambiguous and the per-file scope is right. Recorded because the obvious reading makes it
    look like a defect.

11. **#366's five modified guards did not change any guard's drivability.** All five
    (`check-fixture-variation`, `check-plan-code`, `check-rc-contract`, `check-selftest-counts`,
    `check-surface-recall`) are inside the deliverable's own population, and
    `check-selftest-counts.py` is in `MAIN_DEBT`. Had #366's refactor made a pinned guard comply, or
    removed a driving case from an unpinned one, the deliverable's two-directional reconciliation
    would fire — *"a pinned guard that now complies is a violation naming itself"*. It exits 0. This
    was the second cross-branch class I feared and the tool refutes it by its own run. #366 added and
    removed no `scripts/check-*.py`, so the population itself did not move.

12. **Guard battery on the merged tree.** `rc=0` for `check-python-pin`, `check-selftest-counts`,
    `check-ratchet-contract`, `check-guard-coverage`, `check-docs`, `check-dashboard-entry`,
    `check-anchors`, `check-plan-file-tags`, `check-rc-contract`, `check-fixture-variation`,
    `check-memory-link`, `check-roadmap-consistency`, `check-gate-falsifiability`,
    `check-producer-enumeration`, `check-sentinel-meanings`, and `check-backlog-closure` (WARN, 2
    possibly-stale rows, which is its designed non-failing hygiene output). Two non-zero, **neither
    a defect and neither waved past**: `check-review-rounds` → rc=1 naming exactly one cause, *"main-drivable
    round 11: only codex — claude neither ran nor recorded a `REVIEW GAP:` line"*, which is this
    document's own absence and resolves when it lands; and `check-test-counts` → rc=1 *"Treat this
    check as NOT RUN — an absent results file is not a passing suite"*, correct CANNOT-RUN behaviour
    for a worktree with no jest results, reported as NOT RUN rather than as a pass.

13. **`--self-test` on the merged `check-plan-code.py`: 438/438 for the deliverable and
    `--mutate . --shard` works end to end.** The coordinator's 178/178 on `check-plan-code.py`
    reproduces; `check-selftest-counts.py` independently verifies all 51 declared counts by running
    them, which is a stronger statement than any single self-test invocation.

---

## What remains unverified, and by whom it should be

Stated so a clean severity column is not read as full coverage.

- ✅ **CLOSED since this document was written: every mutation has now run.** The gap was 1,389 of
  1,394 (the coordinator ran 2, I ran 3 — the first three against this branch's new target, which
  is the half that mattered). CI run `37546762434` on `70ad61d1` reports all eight `mutation-sweep`
  shards and `mutation-sweep-complete` green, so all 1,394 died on a pinned 3.12 runner. ⚠ This
  does **not** soften finding 1: passing and blocking are different properties, and
  `mutation-sweep-complete` is still absent from `required_status_checks.contexts`.
- ✅ **CLOSED: GitHub-runner timing.** Supplied by the same run and folded into finding 2, which
  now rests on it rather than on my laptop.
- **The required-context change itself.** Finding 1's fix is a repository setting I did not attempt.
- **`verify` is red on this commit** (258 s, run `37546762434`) — per the coordinator, solely on
  `check-review-recorded` awaiting this round. I did not independently confirm that it is the only
  failing step, so treat the cause as reported rather than verified by me.

---

## Verdict

**CONVERGED.**

Reason: **zero findings at any severity in the deliverable.** `scripts/check-main-drivable.py` and
its manifest are byte-identical to the tree rounds 1-10 converged on (claim 1), and the merge's two
new risks to it — a red control inside #366's rewritten harness tree, and #366's five guard edits
disturbing the two-directional `MAIN_DEBT` reconciliation — were both tested directly and both
refuted (the three shards above; claim 11). Coverage is measured not to have shrunk, with the
three-way provenance the merge commit said it did not have (claim 2). The three findings are all
outside the deliverable and file as backlog rows under the round-10 freeze: finding 1 as a new row,
finding 2 as an amendment to #231, finding 3 as a docs correction.

⟳ **Strengthened after writing:** CI run `37546762434` on `70ad61d1` has since reported all eight
`mutation-sweep` shards and `mutation-sweep-complete` green, so **all 1,394 mutations died on a
pinned 3.12 runner** — the deliverable's 183 included. That was the one gap I could not close
locally, and it closes in the direction of the verdict rather than against it.

⛔ **One qualification, because the freeze governs what is FIXED and not what a merge needs.**
Finding 1 is High and is not a code change — it is a one-line repository setting whose stated
ordering precondition is already met. Merging #365 before it lands ships a guard whose 183 mutation
entries are measured by a check that cannot block anything, which is most of what this PR is for.
Convergence is a statement about the deliverable; it is not a recommendation to merge with finding 1
open. Merging is the human gate, and this is the fact the human needs for it.
