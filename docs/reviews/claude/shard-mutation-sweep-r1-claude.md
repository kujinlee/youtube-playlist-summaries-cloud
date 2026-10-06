# shard-mutation-sweep — round 1, Claude half

**Subject:** `git diff origin/master...eee31527` — `scripts/check-plan-code.py`,
`scripts/mutations/check-plan-code.json`, `.github/workflows/ci.yml` (backlog #217).
**Branch:** `shard-mutation-sweep` · **PR** #366 · **commit** `eee31527` · **date** 2026-10-05.
**Mandate:** refute, not confirm. This half designs experiments.

**VERDICT: NOT CONVERGED.** 2 High · 2 Medium · 4 Low. **No dropped-mutation hole was found** —
the partition survived every attack I could construct. The reason this is not converged is
different and simpler: **the gate this change installs is RED in CI on this very commit, and the
cause is unexplained.**

⚠ I deliberately did **not** read `docs/reviews/codex/shard-mutation-sweep-r1-codex.md`, which
appeared untracked in the tree while I was working. Instruction is not isolation; the only way the
two halves stay independent is for me not to open it.

---

## Verification — what I ran

Everything below is real output from this machine or from the live CI run, re-derived rather than
quoted from the brief.

### Executed

| # | Command | Result |
|---|---|---|
| V1 | `python3 scripts/check-plan-code.py --self-test` | `155/155 passed` — re-derived, matches the docstring |
| V2 | `/usr/bin/time -p … --mutate . --shard 5/8` | `rc=0`, **420.50s real**. `OK — delivered scripts mutated: 54 file(s), 149 mutation(s), 149 killed, 149 attributed to the case each names, 0 survivor(s) — measured over shard 5 of 8 (round-robin)` |
| V3 | `load_manifests(".")` driven directly | 0 problems · **1,193 entries** · `EXPECTED_MUTATIONS` sum **1,193** · 57 manifest targets == 57 declared targets · `check-plan-code.py` 92 == 92 · all `(file,name)` ids unique |
| V4 | partition over the real 1,193 ids at N = 1,2,3,7,8,16,1193,1198 | exact multiset equality every time, **zero duplicates**, see table below |
| V5 | 11 malformed / out-of-range `--shard` specs against the real manifest | all **rc=2**, **zero bytes on stdout**, a `CANNOT RUN` sentence on stderr |
| V6 | `--shard 2/8` without `--mutate` | rc=2, sentence on stderr |
| V7 | `--shard ""`, `--shard=` | **rc as if the flag were absent** — see Finding L1 |
| V8 | 6 severs of the partition and the global checks, each re-run through `--self-test` | 5 caught, **1 survived** — see Finding M1 |
| V9 | `gh pr checks 366`; `gh run view --job …` for `mutation-sweep (1)` and `verify` | **`mutation-sweep (1)` fail**, `mutation-sweep-complete` fail, 7 shards pass — see Finding H1 |
| V10 | per-file suite costs derived from the CI control-loop timestamps, then round-robin vs contiguous | round-robin spread at N=8 = **1.15x** — see Experiment E3 |
| V11 | `check-python-pin.py`, `check-ratchet-contract.py`, `check-docs.py`, `check-selftest-counts.py`, `check-guard-coverage.py --self-test`, `check-merge-ready.py --self-test` | rc=0 / OK / 50 scripts verified / 37/37 / 74/74 |

V4 in full, re-derived (the brief claimed "sizes within 1.01x"):

```
N=    1 exact=True dup=False nonempty=1/1       min=1193 max=1193 ratio=1.0000
N=    2 exact=True dup=False nonempty=2/2       min=596  max=597  ratio=1.0017
N=    3 exact=True dup=False nonempty=3/3       min=397  max=398  ratio=1.0025
N=    7 exact=True dup=False nonempty=7/7       min=170  max=171  ratio=1.0059
N=    8 exact=True dup=False nonempty=8/8       min=149  max=150  ratio=1.0067
N=   16 exact=True dup=False nonempty=16/16     min=74   max=75   ratio=1.0135   <- not 1.01
N= 1193 exact=True dup=False nonempty=1193/1193 min=1    max=1    ratio=1.0000
N= 1198 exact=True dup=False nonempty=1193/1198 min=0    max=1    ratio=1.0000   <- 5 EMPTY shards
```

### Could not run — treat these as NOT MEASURED

- **`--mutate .` unsharded.** ~29 minutes; the brief forbade it and it would have exhausted the
  budget. So I have **no independent confirmation of the 1,758s baseline** and no independent
  confirmation that the whole manifest is green on this tree today.
- **The root cause of the `check-banner-armed.py` re-control failure in CI (Finding H1).** I did
  not reproduce it. My local shard 5 of 8 was clean, and shards 2–8 were clean in CI. Everything
  I say about *why* it happened is labelled as hypothesis.
- **The claimed contiguous spread of 17.9x at N=8.** I derived 8.20x from CI-measured per-file
  costs (E3). I cannot reproduce 17.9x, and I cannot refute it either — it was computed from
  local per-suite costs I did not measure. The claim's *direction and order of magnitude* are
  confirmed; the specific figure is NOT MEASURED by me.
- **`python3` on this machine is 3.14; CI pins 3.12.** `check-python-pin.py` printed its ADVISORY.
  Every local result above is therefore PROVISIONAL in this repo's own sense.

---

## Findings

Findings and proposed fixes are stated separately. **Every proposed fix is UNVERIFIED** — I wrote
no fix and ran no fix.

---

### H1 — HIGH · The gate this change installs is RED in CI on this commit, and the brief's verified list does not mention it

**Finding.** On `headSha eee31527` — the exact commit under review — run
[37390914914](https://github.com/kujinlee/youtube-playlist-summaries-cloud/actions/runs/37390914914)
reports:

```
mutation-sweep (1)         fail   3m4s
mutation-sweep-complete    fail   3s
mutation-sweep (2..8)      pass   2m32s .. 3m40s
verify                     fail   2m44s    <- check-review-recorded, i.e. this round. Not a defect.
```

Shard 1's own last lines (job 112035620545):

```
  ✗ CANNOT RUN — scripts/check-banner-armed.py is no longer green AFTER the sequence (exit 1),
    so the tree changed underneath it. Any 'caught' above may be an artefact of that, not of its
    mutation. Treat this run as NOT CHECKED.
  …
  155/160 self-test cases passed
NOT MEASURED — the mutation harness produced no coverage verdict. Treat this as NOT CHECKED.
  — measured over shard 1 of 8 (round-robin)
```

So: shard 1 **measured nothing**, 150 mutations' worth of work is discarded, and the aggregator is
correctly red. The before-control for `check-banner-armed.py` was green (a red one returns earlier);
the **after**-control was not, with 5 of its 160 cases failing.

**This is not a dropped-mutation hole.** The harness did exactly the right thing — it refused rather
than printing a tally. That is the behaviour the design promises and it held. The problem is
upstream of that: *the sharded sweep produced a NOT-MEASURED verdict that the unsharded sweep did
not produce on the same tree.* Supporting evidence that this is new:

- master's last **12 consecutive CI runs are `success`** (`gh run list --workflow CI --branch master
  --limit 12`), each of which ran the unsharded sweep inside `verify`.
- the coordinator's own local unsharded run was green at 1,758s.

**Why it blocks convergence.** The whole claim of this PR is "it is NOT weaker". A gate that is red,
for a reason nobody has named, on the commit being reviewed, is not evidence of that either way —
it is an unanswered question about the instrument every other guard's evidence rests on. A verdict
of CONVERGED over a red gate is precisely the "a reviewer asked to confirm ships a wrong conclusion"
failure this repository has measured.

**Exhibiting input.** The CI run above. Reproduce with
`gh run view --job 112035620545 --log-failed`.

**Hypothesis, UNVERIFIED and offered only so the next person has somewhere to start.**
`check-banner-armed.py:146` holds `WARN_LOG = ROOT / ".claude/banner-warnings.log"` — a
repo-root-relative path, and `.claude/banner-warnings.log` is **not** in `HARNESS_TREE` (which
stages `.claude/hooks`, not `.claude/`). Inside one shard the suite runs ~56 times against the same
staged tree, so anything written there accumulates. The diagnostic tail in the log ends with
`Logged to .claude/banner-warnings.log.`, which is consistent with that. But **it does not explain
why only 1 of 8 shards failed** — all 8 shards mutate and control that file (verified: at N=8,
shards containing `scripts/check-banner-armed.py` = `[1,2,3,4,5,6,7,8]`), and all 8 ran a
near-identical 149–150 mutations. A deterministic accumulation would have failed all eight. So the
dependence is on something that differs between shards — order, or wall-clock. I did not establish
which.

**Proposed fix — UNVERIFIED.** Do not fix this by relaxing the re-control. Either (a) root-cause
the `check-banner-armed.py` suite's cross-invocation state dependence and make its suite
idempotent, or (b) if it proves environmental and genuinely not this change's doing, file it with
the measurement and say in the PR body which shard measured nothing — but **do not merge on 7 of 8
shards**, because "7 of 8" is 87.5% of a gate the repo describes as the foundation of every other
guard's evidence.

---

### H2 — HIGH · Sharding multiplies the after-control's failure exposure 7.21x, and the design treats the repeated controls as COST only

**Finding.** Each shard runs the control **and** re-control for every file it mutates. The ci.yml
comment and the docstring both say so, and both frame it purely as a price:

> "⚠ EACH SHARD PAYS THE CONTROL RUNS for the files IT mutates, so that cost is repeated across
> shards rather than divided. Deliberate … It also means N is not free, and it is why the measured
> speedup at N=8 is 5.0x (1758s -> 353s) rather than 8x"

Measured, on the real 1,193-entry manifest:

```
unsharded control+re-control suite runs:  114  (57 files x 2)
N= 2 : 228   amplification 2.00x   per-shard distinct files 57..57
N= 4 : 456   amplification 4.00x   per-shard distinct files 57..57
N= 8 : 822   amplification 7.21x   per-shard distinct files 49..54
N=16 : 1316  amplification 11.54x  per-shard distinct files 39..43
```

So at the chosen N=8 the sweep performs **7.21x as many control runs**, and for a file present in
every shard (which `check-banner-armed.py` is) its re-control runs **8 times instead of once**.

A re-control red is not a soft signal. It sets `ok = False`, clears `controls_green`, makes
`Measured` unconstructible, and the run reports NOT MEASURED at rc 1 — a **hard gate failure that
discards the whole shard's work**. If a given file's re-control is red with per-invocation
probability `p`, the sweep now fails with roughly `1 - (1-p)^8` instead of `p`. **Finding H1 is one
realisation of exactly this**, and its 1-in-8 incidence is what that arithmetic predicts for a
small `p`.

Nothing in the diff — comment, docstring, manifest entry or workflow — states that N multiplies the
false-red rate of the one check whose job is to invalidate a run. The cost is written down three
times; the reliability consequence is written down nowhere. This is a **structural property this
change creates**, not a pre-existing one.

**Exhibiting input.** `N=8` over the shipped manifest: 822 control suite runs against 114 unsharded,
and shard 1 of 8 red in CI while 2–8 are green.

**Proposed fixes — UNVERIFIED, and they are alternatives, not a list to do all of.**
(a) Write the amplification down beside the cost sentence, with the 7.21x figure, so the next person
retuning N knows both axes move. (b) Make a re-control red *attributable*: it currently cannot say
which case went red (see L4), so it cannot be distinguished from a real tree corruption. (c) The
expensive option, stated for completeness and **not** recommended without measurement: have the
re-control run only for files whose mutations the shard actually applied *and* re-run just the
failing suite once before declaring, which trades a little rigour for a 1/N false-red rate. (c)
weakens a guard this project paid review rounds for; (a) and (b) do not.

---

### M1 — MEDIUM · The rationale asserts one property for three checks; it is true of one, and the suite is blind to the difference for the other two

**Finding.** `scripts/check-plan-code.py:1670-1677` and the docstring at `:66-73` both enumerate
three things as whole-manifest invariants and give one reason for all three:

> "The counts against EXPECTED_MUTATIONS (both directions), the duplicate name/anchor refusals
> inside `load_manifests`, and the home-escape scan over every target and every REPLACEMENT are
> statements about the manifest as a whole. … If a shard validated only its own slice, one global
> invariant would quietly become N local ones and coverage could shrink with every shard still
> green, which is this repository's definition of a false green."

I severed each one to per-shard and re-ran `--self-test`. Clean baseline on this scripts-only copy
is **152/155** (3 known `HARNESS_TREE` staging failures, which need the real repo root).

| Sever | Result | Cases that reddened |
|---|---|---|
| `counts` computed from the shard's slice | **148/155 — CAUGHT** | incl. the dedicated `⛔ a count mismatch fails shard 2 of 3 exactly as it fails unsharded` |
| home-escape scan over **REPLACEMENT** text narrowed to the shard's entries | **152/155 — SURVIVED** | none |
| home-escape scan over **TARGET** files narrowed to the shard's entries | **152/155 — SURVIVED** | none |

Two of the three claimed invariants can be silently converted from global to per-shard with the
suite fully green.

**And the reason the suite is blind is substantive, which makes this a claim defect rather than a
coverage hole.** Every entry is in exactly one shard, and each shard scans the entries it owns —
so the **per-shard union of either home-escape scan IS the global scan.** Coverage would *not*
shrink. The counts check is genuinely different: per-shard it breaks *noisily* (every shard sees a
shortfall against `EXPECTED_MUTATIONS`), which is why it is the one with a case.

So the sentence is wrong in the direction that matters here: it asserts a hazard for two checks that
cannot exhibit it, in the file whose own recorded rule is *assert the property, not the mechanism* —
and the un-asserted property is what a future reader will take as covered.

**Exhibiting input.** The two severs above, both 152/155.

**Proposed fix — UNVERIFIED.** Correct the comment: say that the counts check must be global
because per-shard it is incoherent, and that the home-escape scans are run globally for cheapness
and locality of blame while their per-shard union would be equivalent. If instead the author wants
them genuinely pinned as global, add a case in the shape of the counts one — a fixture whose
*other* shard's entry carries a flagged replacement, asserted to fail from inside shard 1. Do not
add machinery; this is a sentence and possibly one case.

---

### M2 — MEDIUM · The CI step guards an absent N and not an absent I, and nothing anywhere observes that the N shards were N DISTINCT shards

**Finding.** The workflow builds the spec in the shell:

```yaml
env:
  SHARD_INDEX: ${{ strategy.job-index }}
  SHARD_TOTAL: ${{ strategy.job-total }}
run: |
  python3 scripts/check-plan-code.py --mutate . \
    --shard "$((SHARD_INDEX + 1))/$SHARD_TOTAL"
```

and the comment above it defends exactly one direction:

> "An absent N makes the spec `1/`, which `parse_shard` refuses as CANNOT RUN (rc 2) rather than
> sweeping everything under a sharded log line — the failure direction that matters, since the quiet
> alternative is N jobs each measuring the whole manifest."

Measured, reproducing that expression under `bash -e`:

```
I=''     N=8    -> spec=1/8     <- ACCEPTED
I=x      N=8    -> spec=1/8     <- ACCEPTED
I=0      N=8    -> spec=1/8     <- correct (0-based -> 1)
I=3      N=''   -> spec=4/      <- refused, rc 2   (the guarded direction)
I=''     N=''   -> spec=1/      <- refused, rc 2
I=0      N=x    -> spec=1/x     <- refused, rc 2
```

Bash arithmetic treats an empty or non-numeric `SHARD_INDEX` as 0, so the spec becomes `1/8` and is
**accepted**. Eight jobs would then each run shard 1 of 8, each print
`measured over shard 1 of 8 (round-robin)`, each exit 0 — and **7/8 of the manifest would never be
measured with every shard green.** That is the precise failure the brief names as the one that
matters most, and the guarded half is the loud half while the unguarded half is the silent one.

**`mutation-sweep-complete` cannot see it.** Its only observation is
`needs.mutation-sweep.result != "success"`. There is no cross-shard coverage statement anywhere —
no shard reports *which* slice it took to anything that aggregates. Compare how this repo handles
the analogous problem for review halves: `codex-review.py` writes
`docs/reviews/verdicts/<id>.verdict.json` and `check-review-rounds.py` reads it **in CI**, precisely
because the caller who loses it cannot be trusted to report it.

**Why Medium and not High — stated so the severity can be argued with.** `strategy.job-index` is a
GitHub-provided integer. The realistic way to empty it is to delete the matrix, and that empties
`job-total` too, giving `1/`, which refuses. I could not construct a path where `job-total` is
present and `job-index` is not. So the live exposure today is low; what is unguarded is the
*asymmetry* and the absence of any coverage observation, both of which are permanent features of the
design rather than of today's YAML.

**Proposed fixes — UNVERIFIED, alternatives.**
(a) Cheapest and it closes the exhibited input: refuse an index that is not a plain non-negative
integer, in the step — e.g. require `[[ "$SHARD_INDEX" =~ ^[0-9]+$ ]]` before the arithmetic, or
pass `I` and `N` as separate arguments so the shell never does arithmetic on them.
(b) The structural one: have each shard write a tiny per-shard marker naming the slice it took and
the entry count, and have `mutation-sweep-complete` download the artifacts and assert the union is
`1..N` exactly once each and that the counts sum to the manifest size. That is what turns
"the aggregator read a pass/fail" into "the aggregator read the coverage", and it is the shape this
repo already uses for review verdicts.

---

### L1 — LOW · `--shard ""` and `--shard=` are silently ignored and sweep the whole manifest

**Finding.** `main` tests `if a.shard:` — a truthiness test — so an empty string is dropped rather
than refused. Measured against a cheap root:

```
$ … --mutate $D                 -> NOT MEASURED … — measured over the WHOLE manifest   rc=1
$ … --mutate $D --shard ""      -> NOT MEASURED … — measured over the WHOLE manifest   rc=1
$ … --mutate $D --shard=        -> NOT MEASURED … — measured over the WHOLE manifest   rc=1
$ … --mutate $D --shard 3/8     -> NOT MEASURED … — measured over shard 3 of 8 (round-robin)  rc=1
```

Confirmed on the real manifest too: `--shard ""` started a full ~29-minute sweep (I killed it).

The **dangerous half is covered** — the verdict line honestly says `the WHOLE manifest`, so a log
cannot be misread. What is missing is the refusal, and `main`'s own comment is the one that asks for
it: *"`--shard` alone changes nothing about the subject measured … so accepting it silently would let
a CI matrix run N whole-manifest sweeps while its log said 'shard 3 of 5'."* Low because the CI step
cannot produce an empty argument (the `/` is a literal) and because the label stays truthful.

**Proposed fix — UNVERIFIED.** `if a.shard is not None:` instead of `if a.shard:`, so an empty
spec reaches `parse_shard` and gets the existing `not of the form I/N` sentence.

---

### L2 — LOW · A case named "PAIRWISE DISJOINT, counted not assumed" cannot observe disjointness

**Finding.** `scripts/check-plan-code.py:3698-3700`:

```python
case("...and the shards of one N are PAIRWISE DISJOINT, counted not assumed",
     {n: sum(len(p) for p in ps) for n, ps in _parts.items()},
     {1: 37, 2: 37, 3: 37, 7: 37, 40: 37})
```

It compares a **sum of lengths**. The comment eight lines above it says exactly why that is not the
property: *"a length alone passes when one entry is dropped and another duplicated."* A partition
that drops `m5` and duplicates `m6` has the same total and passes this case.

The property **is** carried — by the multiset-equality case immediately before it, which I severed
four ways and which reddened every time. So this is a name over-claiming in the file that preaches
against proxies for properties, not a gap in coverage. Low.

**Proposed fix — UNVERIFIED.** Rename it for what it measures ("...and no shard is empty and the
total is the manifest size") or make it an actual pairwise check
(`all(not set(a) & set(b) for a, b in combinations(ps, 2))`).

---

### L3 — LOW · Two re-derived numbers in the brief need correcting

**Finding.** Both are small and neither changes a conclusion, but the brief asked for these above
new Lows.

1. **"sizes within 1.01x" is 1.0135 at N=16.** See the V4 table. True at N ≤ 8 (1.0067); false at
   the next N the ci.yml comment itself costs out.
2. **N=1198 is "exact" but not usable.** The partition is complete and disjoint, and **5 of the
   1,198 shards are empty** — each would be `rc=2 CANNOT RUN` and `mutation-sweep-complete` would
   be red. That is correct behaviour, and it is the empty-shard refusal doing its job. But
   "verified at N=1198" in a list of verified Ns reads as "N=1198 works", and it does not.

**Proposed fix — UNVERIFIED.** State the N=16 ratio as 1.0135, and label N=1198 as
*verified to refuse*, not *verified to partition*.

---

### L4 — LOW · A re-control red cannot be diagnosed from the CI log

**Finding.** Shard 1's log (H1) reports `155/160 self-test cases passed` and then a
`diagnostic_tail` window that contains only `PASS` lines and a fragment of a hook message — **none
of the five `[FAIL]` case names**. So the reader is told the tree changed underneath the run and
cannot be told what changed.

**NOT caused by this change** — `diagnostic_tail`'s budget is pre-existing. Filed because H2 makes
this the failure a reader is now 7.21x more likely to have to diagnose, which moves it from a
latent wart to the thing standing between this PR and a green gate.

**Proposed fix — UNVERIFIED.** When `control_is_green` fails, prefer the `[FAIL] ` lines over the
tail window — `parse_fail_names` already exists in this file and already reads exactly that
grammar, so this is a reuse, not a new mechanism.

---

## The experiments I designed, and what each showed

### E1 — Sever the stride, sever the offset. Does the suite see BOTH, or only one?

Both, independently, and the headline falsifier fires on all four variants. Run against a
scripts-only copy whose clean baseline is 152/155.

| Sever of `return muts[index - 1::total]` | Score | Cases reddened (excl. the 3 baseline) |
|---|---|---|
| `muts[index - 1:]` — stride gone | 148/155 | multiset partition · cardinality · round-robin balance · the shard-runs-only-its-own-mutations wiring case |
| `muts[index::total]` — offset off by one | 146/155 | all of the above **plus** `...and shard 2 of 2 is the OTHER file` and `a shard past the end of the list is empty` |
| `muts[::total]` — index dropped entirely | 145/155 | adds both empty-shard refusal cases and the rc=2 case |
| `list(muts)` — both gone | 144/155 | 8 cases |

**What it showed:** the two arms are separately falsified, and the `⭐ every mutation runs in
EXACTLY ONE shard and the union is the whole manifest` case — a genuine multiset equality — fires
on every one of the four. This is the strongest thing in the change.

### E2 — Sever the control-target set in both directions. Can a shard report OK without a green control for a file it mutated?

| Sever of `targets = sorted({m["file"] for m in shard_muts})` | Score | Verdict |
|---|---|---|
| `{… for m in muts}` — control the whole manifest (slower, still correct) | 150/155 | **CAUGHT**, by both shard-wiring cases |
| `targets = []` — control nothing | crash (`KeyError`) | caught, though not cleanly |

**What it showed:** the question is structurally unanswerable in the bad direction — `targets` is
*derived* from `shard_muts`, so every file a shard mutates is a file it controls, by construction
rather than by a check. And `run_mutations`' `known` set is that same derived set, so a mutation
can never target a file outside it. I could not build a shard that reports OK over an uncontrolled
file.

### E3 — Construct the cost/count divergence the design rests on, using CI-measured costs rather than the author's local ones

The load-bearing claim is *"a per-shard mutation COUNT is even either way, which is exactly why
counting them proves nothing."* I derived per-file suite costs independently: the shard-1 CI log
prints `[i/50] control <file>` with ISO timestamps, so consecutive deltas are each file's real suite
time **on a GitHub runner**. 49 files recovered, summing to 35.0s; the expensive tail is
`check-rc-contract.py` 9.01s, `check-paid-caller-arrival.py` 6.03s, `gen-backlog-page.py` 5.85s,
`check-surface-recall.py` 4.98s. Weighting each of the 1,193 entries by its file's cost:

```
N=4    ROUND-ROBIN min=184.5s max=204.6s spread= 1.11x | CONTIGUOUS min=127.1s max=293.6s spread= 2.31x
N=8    ROUND-ROBIN min= 90.1s max=103.9s spread= 1.15x | CONTIGUOUS min= 20.3s max=166.8s spread= 8.20x
N=16   ROUND-ROBIN min= 41.2s max= 54.6s spread= 1.32x | CONTIGUOUS min=  5.3s max=146.6s spread=27.68x
counts at N=8: round-robin 149..150   contiguous 149..150     <- even BOTH ways
```

**What it showed:** the claim survives, and the headline number is reproduced exactly —
**1.15x at N=8**, matching the ci.yml comment to two decimals, from a completely different
measurement path. The counts-prove-nothing claim is confirmed outright: 149..150 under both
schemes. The contiguous spread I get is 8.20x rather than the claimed 17.9x; the difference is
consistent with my costs coming from a faster runner where the expensive block is less dominant,
and with my taking `min` of the two control passes. **Direction and order of magnitude confirmed;
the 17.9x figure itself is NOT MEASURED by me.**

### E4 — Can two shards in CI partition DIFFERENT lists (a manifest added between job starts)?

**No, and for two independent reasons.** (1) `load_manifests` reads
`files = sorted(d.glob("*.json"))` and then each file's entries in file order — the list is fully
deterministic, with no filesystem-order dependence. (2) Every matrix job runs
`actions/checkout@v4` against the same workflow-pinned SHA, so all eight see byte-identical
manifests. And (3) as a backstop, a manifest difference would fail the global
`EXPECTED_MUTATIONS` check in whichever shard saw it. Could not refute.

### E5 — Can `SHARD_TOTAL` be empty in a way that yields a whole-manifest sweep under a sharded log line?

**No for N; yes-ish for I.** `1/` is refused as claimed (V5). The claim is true. But the symmetric
case is not guarded and is the silent one — Finding M2. And the separate `--shard ""` form (L1)
does sweep everything, though it correctly labels itself `the WHOLE manifest`.

### E6 — Is the final stdout line genuinely unambiguous?

Yes, on every path I could reach.

| Invocation | stdout final line | stderr | rc |
|---|---|---|---|
| `--mutate . --shard 5/8` (real) | `OK — … 149 mutation(s), 149 killed, … 0 survivor(s) — measured over shard 5 of 8 (round-robin)` | progress | 0 |
| `--mutate .` (no shard) | `… — measured over the WHOLE manifest` | progress | 0/1 |
| `--mutate . --shard 1194/1194` | *(nothing on stdout)* | `CANNOT RUN — shard 1194 of 1194 is EMPTY: the manifest holds 1193 mutation(s) …` | 2 |
| any of 11 malformed specs | *(nothing on stdout)* | a `CANNOT RUN` sentence | 2 |
| `--shard 2/8` without `--mutate` | *(nothing)* | `CANNOT RUN — --shard 2/8 only means something with --mutate ROOT …` | 2 |
| CI shard 1, re-control red | `NOT MEASURED — … — measured over shard 1 of 8 (round-robin)` | progress | 1 |

Every refusal is rc=2 with **zero bytes on stdout**, and every verdict names its slice. A CI log
cannot be read as a whole-repo pass. The one residue is L1's empty-flag form, which labels itself
honestly.

### E7 — Can `mutation-sweep-complete` pass while a shard is red, cancelled or skipped?

No, and this is confirmed *live* rather than by reading. `needs.<job>.result` over a matrix is the
aggregate; `if: always()` keeps the job reporting; the step exits 1 on anything but `success`. On
this very run `mutation-sweep-complete` is **fail** because shard 1 is fail. `fail-fast: false`
also means a red shard does not cancel its siblings, so there is no cancelled-shard path to pass
over. Could not refute.

### E8 — Do the new jobs break the guards that parse `ci.yml`?

No. `check-python-pin.py` rc=0 (both new jobs pin 3.12, and `mutation-sweep-complete` pins it even
though it runs no Python — the comment is right that an empty `EXEMPT_JOBS` is the stronger form).
`check-ratchet-contract.py` OK, 43 guards discovered, `check-plan-code.py` still has a caller.
`check-docs.py` OK. `check-selftest-counts.py`: 50 scripts, every declared count verified by
running it — so the docstring's `155` is machine-checked. `check-guard-coverage --self-test` 37/37,
`check-merge-ready --self-test` 74/74. Backlog #227's workaround (job-level comments) holds.

---

## What I tried to refute and could not

- **The partition.** Exact multiset equality over the real 1,193 entries at N = 1, 2, 3, 7, 8, 16,
  1193, 1198. Zero duplicates, zero drops, at every N. Both arms of `muts[index-1::total]`
  independently falsified by the suite (E1). This is the part of the change I attacked hardest and
  it did not move.
- **The balance claim**, by an independent measurement path: 1.15x at N=8 from CI-derived per-file
  costs, matching the stated figure exactly, with per-shard counts even under both schemes (E3).
- **"A shard reports OK while a file it mutated had no green control."** Structurally impossible —
  `targets` and `run_mutations`' `known` set are both derived from `shard_muts` (E2).
- **"The whole-manifest checks became per-shard."** The counts check is pinned by a dedicated case
  and fires from inside a shard. (The two home-escape scans are *not* pinned — M1 — but their
  per-shard union is the global statement, so coverage does not shrink.)
- **Every refusal.** 11 malformed/out-of-range specs, the empty shard on the real manifest, and
  `--shard` without `--mutate`: all rc=2, all with a sentence, none on stdout (V5–V7).
- **`mutation-sweep-complete` passing over a red/cancelled/skipped shard** (E7) — confirmed red
  live.
- **Two shards partitioning different lists** (E4).
- **"The CI runner is slower than the author's machine, so the N=8 sizing has no headroom."** This
  was my best shot at the sizing argument and it is **wrong in the reassuring direction**: local
  shard 5 of 8 took **420s**, CI shards took **152–220s**. The GitHub runner is roughly 2x *faster*
  here, so the real headroom under the 30-minute ceiling is better than the comment claims, not
  worse.
- **"A red sweep is completely unguarded until the repository setting lands."** Partly refuted:
  `check-merge-ready.py`'s `ci_conclusion` fails on **any** check not in `("pass", "skipping")`, so
  the repo's own pre-merge script does see a red `mutation-sweep (N)`. The merge *button* is
  genuinely unguarded, as the comment says; the process is not. The PR body should say this — it
  currently states only the gap.
- **The declared numbers.** 1,193 entries == `EXPECTED_MUTATIONS` sum 1,193; 57 == 57 targets;
  `check-plan-code.py` 92 == 92; self-test 155/155; shard 5 of 8 149 killed / 149 attributed /
  0 survivors.

---

## Q4(a)

| # | Severity | Aim | Caused by this change? |
|---|---|---|---|
| H1 | High | **Deliverable** — the shipped gate is red and NOT MEASURED on this commit | **Surfaced by it, root cause not established.** The sharded sweep produced a verdict the unsharded one did not on the same tree (master green 12/12). The suspected subject, `check-banner-armed.py`'s suite, is not in this diff — but H2 is why it fires now |
| H2 | High | **Instrument** — the sweep's own reliability as a gate | **Yes.** 7.21x control amplification at N=8 is created by the per-shard control design; the cost is documented three times and the false-red consequence nowhere |
| M1 | Medium | **Instrument** — the suite's ability to falsify its own stated invariant | **Yes.** The three-invariant claim and both severable scans are new in this diff |
| M2 | Medium | **Instrument** — the shell seam between the matrix and the flag | **Yes.** The `env:` + arithmetic step and the pass/fail-only aggregator are both new |
| L1 | Low | Instrument — the flag's refusal contract | **Yes** (`if a.shard:` is new) |
| L2 | Low | Instrument — a case name that over-claims | **Yes** (the case is new) |
| L3 | Low | Instrument — two numbers in the branch's own evidence | **Yes** |
| L4 | Low | Instrument — diagnosability of a re-control red | **No** — `diagnostic_tail` is pre-existing. Filed because H2 multiplies how often it matters |

---

## Verdict

### NOT CONVERGED

The engineering is strong and the part I expected to break did not: **the partition is correct, the
round-robin rationale is independently reproduced to two decimals, every refusal is rc=2 with a
sentence, the whole-manifest counts check genuinely fires from inside a shard, and I could not
construct a dropped or doubled mutation at any N.** If the question were only "is the partition
sound", the answer would be yes.

It is not converged for two reasons:

1. **H1 — the gate is red on this commit.** `mutation-sweep (1)` reports NOT MEASURED in CI and
   nobody has said why. This repository's own rule is that "cannot run" is a failure, never a pass;
   a verdict of converged over a NOT MEASURED shard would be that rule broken on the instrument
   every other guard's evidence rests on.
2. **H2 — the change multiplies the after-control's false-red exposure 7.21x and says only that it
   costs more.** H1 looks like the first bill for that, and the two should be resolved together
   rather than H1 being treated as a flake.

M1 and M2 are both single-sentence-or-single-case repairs and neither blocks on its own.

**Document:** `/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/reviews/claude/shard-mutation-sweep-r1-claude.md`
