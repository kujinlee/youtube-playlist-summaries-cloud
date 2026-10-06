# Round 5 — Claude adversarial half · `shard-mutation-sweep` (PR #366) at `a5fcd951`

Subject: **the sharding deliverable** — `--shard I/N` in `scripts/check-plan-code.py`, the 8-way
`mutation-sweep` matrix and the `mutation-sweep-complete` aggregator in `.github/workflows/ci.yml`.
Introduced in `d74d1c2b`; rounds 2–4 were about the bytecode race, not about this.

Mandate: **REFUTE**. Per the brief I did not re-attack the bytecode scrub except through one
concrete route the env-capture might not see (§5 item 7) — I could not find one.

**Headline.** I attacked the partition, the per-shard global invariants, attribution, the
aggregator, `fail-fast: false` and the empty-shard refusal by *running* them, and **could not break
any of them**. The deliverable's mechanism is sound. What I did find is that **three of round 1's
findings about the shipped half were never fixed and never dispositioned** — they appear in neither
the later rounds nor the coordinator's "two findings remain open" statement — plus two bookkeeping
gaps. That is why the verdict is NOT CONVERGED, and none of it is a redesign.

---

## 1. Verification

Working directory `/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud`,
`HEAD` = `a5fcd951647d2cd374ae5b2b8aa4ed46184b7b35`, tree clean apart from
`docs/explainers/questions.md` (ignored per instruction).

**No tracked file was modified.** Every perturbation was applied to a `git archive` copy of
`a5fcd951` under `…/scratchpad/clone`, restored and md5-verified after each test
(`8190ec79bf76525be6cd1a0665929c93` before and after). `git status --porcelain` after all runs:
`M docs/explainers/questions.md` only. `git rev-parse HEAD` unchanged. No tracked `.pyc`.

### 1.1 The three self-tests — the brief's figures confirmed

```text
$ python3 scripts/check-plan-code.py --self-test       → 161/161 passed            rc=0
$ python3 scripts/check-rc-contract.py --self-test     → 56/56 cases passed        rc=0
$ python3 scripts/check-surface-recall.py --self-test  → 59/59 cases passed        rc=0
```

### 1.2 Manifest size and declared sum — **both differ from the brief**

```text
manifest length: 1200     problems: []
declared sum:    1200
```

The brief lists the falsification N values as "1, 2, 3, 7, 8, 16, **1193, 1198**". Those were the
manifest length at `d74d1c2b` and the sum at `fcc46c01`. At the merging tree both are **1200**. This
is not a defect — the ratchet agrees with itself — but it propagates into finding M2.

### 1.3 Gate battery, all run here

```text
check-docs                 rc=0   Documentation integrity OK
check-selftest-counts      rc=0   50 script(s) declare a count, every one verified by running it
check-python-pin           rc=0
check-anchors              rc=0   13 registered, all claimed
check-review-rounds        rc=0
check-dashboard-entry      rc=0   ok — an entry block was added
check-ratchet-contract     rc=0   ratchet contract OK
check-guard-coverage       rc=0
check-plan-file-tags       rc=0   0 across 1698 documents
check-backlog-closure      rc=0   WARN — 2 row(s) may be stale (#117, #159), 0 orphaned
check-merge-ready          rc=0   READY — head a5fcd951, CLEAN, 12 check(s) green
```

### 1.4 One shard run end-to-end, independently — shard **1 of 8**

The brief measured shards 5/8 and 8/8. I ran **1/8**, the shard that originally went red:

```text
$ /usr/bin/time -p python3 scripts/check-plan-code.py --mutate . --shard 1/8
OK — delivered scripts mutated: 51 file(s), 150 mutation(s), 150 killed,
     150 attributed to the case each names, 0 survivor(s)
     — measured over shard 1 of 8 (round-robin)
real 401.36     rc=0
```

⚠ **On Python 3.14.4, not the pinned 3.12.** My run is therefore *not* a measurement of the
interpreter CI pins; CI's is (§1.5).

### 1.5 CI at the merging commit

```text
$ gh run view 37480588749 --json headSha,conclusion
headSha = a5fcd951647d2cd374ae5b2b8aa4ed46184b7b35   conclusion = success
$ git rev-parse HEAD
a5fcd951647d2cd374ae5b2b8aa4ed46184b7b35

mutation-sweep (1..8)   all pass   248 216 209 227 179 225 218 248 seconds
mutation-sweep-complete pass 4s
verify                  pass 2m9s
schema-gates            pass 1m49s
prod-drift              skipping (scheduled only)
```

### 1.6 What I could NOT run — treat as NOT MEASURED

| Not measured | Why |
|---|---|
| unsharded `--mutate .` at the merging tree | instructed not to. ⚠ **I started one by accident** — `--shard ""` is not refused (finding L1), so the loop's empty-string case swept the whole manifest; I killed it at ~10 min. Its partial output is not evidence and is not cited. |
| shards 2, 3, 4, 6, 7 locally | CI measured all eight at `a5fcd951` (§1.5) |
| the pinned 3.12 interpreter locally | local is 3.14.4; `check-python-pin` is advisory locally by design (#56) |
| `actionlint` | not installed. Workflow parsed structurally with Ruby `YAML` instead (see *Structural parse* below) |
| PR #365's 183-entry load, directly | its branch is not checked out; modelled arithmetically in §4.4 from the committed per-suite costs |

---

## 2. Q4(b) — TREE IDENTITY. **Explicit statement.**

**Confirmed: this round reviews the tree that would merge, and it is the first round to do so.**
Three independent observations, all measured:

1. `a5fcd951` differs from the CI-green `a28c76be` by **review documents only** —
   `git diff a28c76be..a5fcd951 --stat -- scripts/ .github/ lib/ app/ worker/ supabase/ components/ tests/`
   returns **empty**. Zero executable bytes changed.
2. The branch is a **fast-forward** from the remote default branch:
   `git rev-list --count HEAD..origin/master` = **0**, and
   `git merge-base origin/master HEAD` = `0af517ce` = `origin/master`'s tip. So the merge result's
   tree *is* `a5fcd951`'s tree; there is no merge commit to introduce one.
   ⚠ Local `master` is stale at `2413b003`; `origin/master` is the authority and is an ancestor of
   `HEAD`.
3. CI ran on `a5fcd951` itself and is green (§1.5) — so this is stronger than the brief's claim of
   green at `a28c76be`.

The only uncommitted file is `docs/explainers/questions.md`, ignored per instruction.

---

## 3. Findings

Severity-ordered. **Every proposed fix is stated separately and marked UNVERIFIED** — I applied none.

### M1 — MEDIUM · The PR claims "Closes backlog #217" while **both** tracking layers still read OPEN, and no gate sees it

**Exhibit, measured at `a5fcd951`:**

```text
docs/backlog.md, row 217   marker: 🟠   count of "✅" in the row: 0
                           status cell: "🟠 OPEN - filed 2026-10-01."
docs/roadmap-to-launch.md:2227   "- [ ] **#217 — the sweep's subprocess cost.**"
PR #366 title: "… (backlog #217)"      PR #366 body: "Closes backlog **#217**."
```

`docs/dev-process.md` Phase 5 is explicit on both halves: *"Roadmap/backlog status ticks ride in the
**same PR** as the work they describe"* and *"**Write the merge tick BEFORE opening the PR**, and do
not chase the squash SHA — the PR number exists as soon as the PR does."* The *Roadmap & Task List*
section adds: *"A roadmap step is not done until its checkbox is ticked **and** its task entry is
`completed`."*

**Why no machine caught it, which is the half that matters.** `check-merge-ready.py` reports
**READY** — its dashboard-entry gate asks only whether an *entry block* was added, not whether a
closed row was ticked. `check-backlog-closure.py` is **WARN-ONLY by #56's measured verdict** and
reads **merged** subjects, so it cannot speak before the merge; post-merge it would add #217 to the
#117/#159 warnings it already emits. So the only guard aimed at this class is structurally unable to
fire until after the moment it would have helped.

**Consequence.** #217 merges with its row reading OPEN, which is precisely the state backlog **#219**
was filed about (*"two 🔴 rows, both fixed and merged in PR #360, both still reading LIVE … stale for
two days"*). This is that row's own failure mode, on the PR that closes the row next to it.

> **Proposed fix — UNVERIFIED.** Tick `docs/roadmap-to-launch.md:2227` to `- [x]`, and change row
> 217's marker and status cell to ✅ with the PR number — in this PR, per Phase 5. I did not apply
> it: the status prose is the author's to write, and I must not modify tracked files.

### M2 — MEDIUM · Three artifacts narrate counts the tree no longer has, and the attribution trail for +5 of the +22 is missing

The ratchet itself is **correct at every commit** — I derived the whole history rather than trusting
the comments:

| commit | sum | asserted | cpc | rc | sr |
|---|---|---|---|---|---|
| `0af517ce` (base) | 1178 | 1178 | 77 | 15 | 19 |
| `d74d1c2b` | 1193 | 1193 | 92 | 15 | 19 |
| `29fd2653` | **1196** | 1196 | **95** | 15 | 19 |
| `fcc46c01` | **1198** | 1198 | 95 | **16** | **20** |
| `8c1a207a` | **1200** | 1200 | 95 | **17** | **21** |
| `a5fcd951` | 1200 | 1200 | 95 | 17 | 21 |

Sum and assertion agree in all thirteen commits on the branch. **No false green exists here.** What
is wrong is the narration, in four places:

1. `scripts/check-plan-code.py:1028` — `"⟳ 2026-10-05, backlog #217: 77 -> 92"`, with the declared
   value on the next line being **95**. The `+3` from `29fd2653` is unnarrated.
2. `scripts/check-plan-code.py:4308` — `"1196 -> 1198, one entry each for check-rc-contract
   (15 -> 16) and check-surface-recall (19 -> 20)"`. Correct **for `fcc46c01`**; `8c1a207a` then took
   both to 17 and 21 and the sum to 1200 with **no narration line at all**. So the log describes
   `+1` each where the manifests carry `+2` each, and accounts for 1178→1193 and 1196→1198 while
   1193→1196 and 1198→1200 are unexplained.
3. `docs/dashboard-entries.md` — `"self-test 131 → 155; manifest 77 → 92; declared sum 1178 → 1193"`.
   Actual: **161**, **95**, **1200**. All three stale.
4. **PR #366's body** — `"declared sum 1178 → 1196"`, `"Self-test 131 → 160"`, `"the real
   1,193-entry manifest"`, and `"shard 3 of 8 … 149 mutations, 149 killed, 149 attributed"` (a
   1,193-manifest figure; at 1200 every shard holds exactly 150).

**Why this is a finding and not pedantry.** The comment at `:4307` states its own purpose: *"the sum
moves in the same commit as the per-file count, because the two numbers are the only things that make
coverage leaving visible, and **a sum that follows later is a sum nobody can attribute**."* A reader
auditing 1193 → 1200 finds a log accounting for 2 of the 7. And the PR body is the artifact the human
reads at the **merge gate**, which is a human gate.

`check-selftest-counts.py` passes because the script's *own docstring* says 161, which is right — the
ratchet that exists guards the docstring, and nothing reads these four narrative sites.

> **Proposed fix — UNVERIFIED.** Add one narration line for `29fd2653` (+3, `check-plan-code` 92→95)
> and one for `8c1a207a` (+2, `check-rc-contract` 16→17 and `check-surface-recall` 20→21); correct
> `:1028` to `77 -> 95`; refresh the dashboard entry's `counts` row to `161 / 95 / 1200`; refresh the
> PR body's four figures. Editorial only — per `review-method.md:118`, landing these *ahead
> of* the final round is the documented cheap path.

### L1 — LOW · `--shard ""` sweeps the whole manifest — **round 1's L1, still open, no recorded disposition**

**Exhibit, measured:**

```text
shard_mode_refusal("", ".")  -> None       # "" is falsy, so the mode refusal cannot see it
parse_shard("")              -> (None, "CANNOT RUN — --shard '' is not of the form I/N …")
main: `if a.shard:` is falsy -> shard stays None -> the WHOLE manifest is swept
shard_label(None)            -> "the WHOLE manifest"
```

`parse_shard` would refuse it; `if a.shard:` means that refusal is **unreachable for this input**. I
hit this by accident (§1.6) — it is the reason one of my loop iterations ran for ten minutes.

**Honest severity.** The outcome is *not* a false green: the run measures the whole manifest and the
verdict line says `the WHOLE manifest`. And it is unreachable from CI — `$((SHARD_INDEX + 1))/$SHARD_TOTAL`
cannot produce `""`; the nearest shape, `1/`, **is** refused (`rc=2`, measured §4.1). So: Low.

**What makes it worth reporting anyway** is not the defect but the ledger. Round 1 filed it as **L1**
(`shard-mutation-sweep-r1-claude.md:299`). It is unfixed at the merging tree, it is not mentioned in
r2, r3 or r4, and the coordinator record's statement — *"Two findings therefore remain open and are
NOT closed by this fold"* (`:179`) — names the probe duplication and r4's Low 1, **not this**.

> **Proposed fix — UNVERIFIED.** `if a.shard is not None:` in `main`, and
> `if shard_arg is not None and not mutate_arg:` in `shard_mode_refusal`, which routes `""` to
> `parse_shard`'s existing refusal. Two tokens. *Or* record it as accepted with the
> unreachable-from-CI reason — either closes the ledger; silence does not.

### L2 — LOW · The CI shell seam fails **silently** on the I side and loudly on the N side — round 1's M2(a), still open

**Exhibit** — the workflow's exact expression, run under hostile values:

```text
SHARD_INDEX=[0]   SHARD_TOTAL=[8]    -> 1/8      valid
SHARD_INDEX=[]    SHARD_TOTAL=[8]    -> 1/8      ⛔ silently a VALID shard 1
SHARD_INDEX=[abc] SHARD_TOTAL=[8]    -> 1/8      ⛔ silently a VALID shard 1
SHARD_INDEX=[0]   SHARD_TOTAL=[]     -> 1/       refused, rc=2 (measured)
SHARD_INDEX=[0]   SHARD_TOTAL=[abc]  -> 1/abc    refused, rc=2 (measured)
```

Bash arithmetic treats an unset or non-numeric name as `0`, so `$((SHARD_INDEX + 1))` is `1`. If
`strategy.job-index` were ever absent in every job, all eight would run **shard 1 of 8**, 7/8 of the
manifest would go unmeasured and **all eight would report green**. The ci.yml comment guards the N
side in writing (*"An absent N makes the spec `1/`, which `parse_shard` refuses"*) and is silent on
the I side.

**Honest severity.** `strategy.job-index` is GitHub-provided and always set, so this is not reachable
today — Low, and a rediscovery of r1's M2, which likewise has no recorded disposition.

> **Proposed fix — UNVERIFIED.** `[ -n "$SHARD_INDEX" ] || { echo "CANNOT RUN — no SHARD_INDEX"; exit 2; }`
> before the call, or `--shard "$((SHARD_INDEX + 1))/$SHARD_TOTAL"` replaced by a form that refuses a
> non-numeric index. Alternatively record it as accepted.

### L3 — LOW · The aggregator observes the job **result** and nothing else — round 1's M2(b), still open

I tried to refute this and could not, so it stands as round 1 left it. `mutation-sweep-complete`'s
only observation is `needs.mutation-sweep.result`. It therefore cannot see:

- that **eight distinct** shards ran (the L2 world (§3.4) is invisible to it);
- that the shards' slices **unioned** to the manifest;
- that the sweep **step** ran at all. There is no step-level `if` in `mutation-sweep` today
  (measured: all six steps have `if: nil`, see *Structural parse* in §5), so nothing is broken — but a step-level `if` added
  later would leave a green job and a green aggregator.

Round 1 proposed per-shard artifacts plus a union assertion (`r1-claude.md:292`). Not built; not
recorded as declined.

> **Proposed fix — UNVERIFIED.** As round 1 wrote it: each shard uploads its slice's entry names as
> an artifact; `mutation-sweep-complete` downloads all of them and asserts the union equals the
> manifest and that the shard indices are `1..N` distinct. Non-trivial, and reasonably deferrable —
> but then *recorded* as deferred.

### Informational · one of the four skip sites named by the cardinality comment is unreachable from the only production caller

`mutate_delivered:1774` calls `run_mutations(d, shard_muts, set(targets), …)` where
`targets = sorted({m["file"] for m in shard_muts})` (`:1740`) — derived from the same list. So every
mutation's file is in `known` **by construction**, sharded or not, and
`if fname not in known` (`:1849`) cannot fire from this entry point. The comment at `:1670` names it
as one of *"FOUR places"* `run_mutations` skips without appending, which the `len(ev["mutations"]) < declared`
arithmetic is said to catch. That arithmetic is still sound — it just has three live inputs here, not
four. The branch is exercised only by the suite (`:2502`, explicit mismatched `known`). Pre-existing,
not sharding; no action proposed.

---

## 4. The six questions

### 4.1 Q1 — The partition. Re-derived independently, boundaries attacked by running

I re-derived disjointness and union-completeness **without** using `shard_slice`'s own cases, over
`list(range(1200))`:

```text
N=    1  disjoint=True complete=True  min=1200 max=1200  empty=0
N=    2  disjoint=True complete=True  min= 600 max= 600  empty=0
N=    3  disjoint=True complete=True  min= 400 max= 400  empty=0
N=    7  disjoint=True complete=True  min= 171 max= 172  empty=0
N=    8  disjoint=True complete=True  min= 150 max= 150  empty=0
N=   16  disjoint=True complete=True  min=  75 max=  75  empty=0
N= 1193  disjoint=True complete=True  min=   1 max=   2  empty=0
N= 1198  disjoint=True complete=True  min=   1 max=   2  empty=0
N= 1199  disjoint=True complete=True  min=   1 max=   2  empty=0
N= 1200  disjoint=True complete=True  min=   1 max=   1  empty=0     ← N = length exactly
N= 1201  disjoint=True complete=True  min=   0 max=   1  empty=1     ← first empty shard
N= 1205  disjoint=True complete=True  min=   0 max=   1  empty=5
PARTITION FAILURES: []
```

`muts[i-1::N]` is a stride partition: index `k` belongs to shard `k mod N + 1`, exactly one value in
`1..N`, so disjointness and completeness hold for all `N ≥ 1` by construction — the measurement
agrees and found no boundary where it does not.

**Every boundary as a real process** (`rc` captured directly, not after a pipe):

| invocation | rc | refusal |
|---|---|---|
| `--shard 0/4` | **2** | names a shard that does not exist |
| `--shard 0/0` | **2** | " |
| `--shard 1/0` | **2** | " |
| `--shard 5/4` (I > N) | **2** | " |
| `--shard 9/8` (I > N) | **2** | " |
| `--shard -1/8` | **2** | not of the form I/N |
| `--shard 2.5/8` | **2** | " |
| `--shard x/5` | **2** | " |
| `--shard 3` (no N) | **2** | " |
| `--shard 1/` | **2** | " |
| `--shard /8` | **2** | " |
| `--shard +2/8` | **2** | " |
| `--shard 1201/1201` (N > length) | **2** | **shard 1201 of 1201 is EMPTY … NOTHING WAS MEASURED** |
| `--shard 1300/1300` | **2** | " |
| `--shard 2/8` with **no** `--mutate` | **2** | only means something with `--mutate ROOT` |
| `--self-test --shard 2/8` | **2** | " |
| `--self-test --shard garbage` | **2** | " |
| `--shard ""` with `--mutate .` | — | **not refused** → finding **L1** |

**I = N** (`8/8`) is valid and was measured green by CI (§1.5) and by the brief. **An empty shard is
rc=2 CANNOT RUN, verified by running, not by reading** — and the refusal derives emptiness from
`shard_slice` itself (`:1603`), not from a re-derived `index > count`, so it cannot drift from the
partition.

The `--self-test --shard` refusal — round 1's Codex finding — is real and fires at the **top of
`main`, before any mode dispatches**. Confirmed by running all three mode cases.

### 4.2 Q2 — Whole-manifest invariants in EVERY shard. Verified per-shard, including from shards that never touch the offending file

Code order first: everything above `:1731` runs on `muts` (the whole manifest) and returns before
`shard_refusal`, `shard_slice`, `stage_tree` or any suite. So the invariants are global *by
construction*. I measured it anyway, on a clone, and **sharpened it**: I perturbed
`scripts/check-theme-token-coverage.py`, which has 4 entries and is **absent from the target sets of
shards 2, 3, 4 and 5** at N=8 — so a shard-scoped check could not possibly see it.

| perturbation | shards run | result |
|---|---|---|
| entry deleted (`check-rc-contract` 17→16) | 1/8, 4/8, 7/8, 8/8 | **rc=1** all four — *manifest holds 16, expected 17* |
| `EXPECTED_MUTATIONS` lowered to 16, manifest 17 | 1/8, 4/8, 7/8, 8/8 | **rc=1** all four — opposite direction fires too |
| declared count **removed** entirely | 1/8, 7/8 | **rc=1** both — *no declared count* |
| entry deleted in a file **absent from the shard** | **2/8, 3/8, 5/8**, 1/8 | **rc=1** all four — *holds 3, expected 4* |
| duplicate mutation name + anchor, same absent file | **3/8**, 1/8 | **rc=1** both — *duplicate mutation name* |
| home escape in a **replacement**, same absent file | **3/8**, 1/8, 8/8 | **rc=1** all three — *pwd.getpwuid() … ignores $HOME* |
| home escape in a **target file**, same absent file | **3/8**, 1/8 | **rc=1** both — same refusal |

**All five global invariants fire in every shard tested, including shards whose own target set
excludes the offending file.** A 7/8-green sweep cannot be reporting on an unvalidated manifest.

⚠ One honest correction to my own method: my first home-escape payload was
`os.path.expanduser("~/explainers")`, which `home_escapes` does **not** flag — correctly, since under
a redirected `$HOME` that route follows `$HOME`. The rule targets `expanduser('~user')`. I re-ran with
`pwd.getpwuid`, a route the scanner does own. The first attempt measured nothing and is not cited as
evidence.

### 4.3 Q3 — Attribution under sharding. **Shard-invariant, by construction and by measurement**

> *"Can a mutation be counted `attributed` in one shard while its killing case lives in a file
> another shard mutates?"* — **No, and sharding does not interact with this at all.**

The attribution unit is wholly local to one mutation:

- `run_suite(d, fname)` (`:1879`) runs **only the mutated file's own suite**;
- `fails = parse_fail_names(out)` reads case names **from that one suite's output**;
- `attributed = caught and not unnamed` (`:1945`) requires each `expect` entry to equal **exactly
  one** name in that list.

A case in another file's suite is never in `fails`, in any shard — so a mutation whose `expect`
named a foreign case would be unattributable in **every** shard, uniformly, not shard-dependently.
And `targets` is derived from `shard_muts` (`:1740`), so the mutated file's control, its suite run
and its re-control all sit inside the same shard as the mutation. There is no cross-shard dependency
to exploit.

Empirically: all 1,200 entries are `attributed` across the eight CI shards at `a5fcd951`, so zero
such entries exist; my independent shard 1/8 reports **150 attributed of 150**.

What sharding *does* change is **adjacency** — round-robin makes different mutations neighbours than
the unsharded order did, so a residue class that depends on execution order would be exercised
differently. The bytecode race was exactly that, and its repair (nothing written, nothing carried in)
is adjacency-independent. **I have no exhibit for any other adjacency-sensitive residue class, and the
after-control is the catch-all for it; marked NOT MEASURED rather than asserted either way.**

### 4.4 Q4 — The timeout. It re-breaks **loudly**, and the margin is 7.3x measured

| | |
|---|---|
| `mutation-sweep` ceiling | `timeout-minutes: 30` = 1800 s (parsed, §5.5) |
| measured per-shard in CI at `a5fcd951` | 179–248 s → **7.3x margin on the slowest shard** |
| PR #365's worst case, modelled `214 + 4890/8` | 826 s → **2.2x** |
| ceiling reached at | `W = (1800−214)×8 = 12,688 s` of mutation work = **7.9x this branch's 1,606 s** |

**I refute the brief's framing that this "re-breaks silently".** A job killed by `timeout-minutes`
reports `failure`; `needs.mutation-sweep.result` over a matrix is the aggregate, so it becomes
`failure`; `mutation-sweep-complete` exits 1. The failure direction is loud and blocking. I verified
the aggregate mechanism against two real red runs in §4.6.

**The residual is real but is a cost, not a defect.** #217's trigger was *"a second timeout raise"*,
and the design replaces one unguarded 30-minute budget (`verify`'s) with another
(`mutation-sweep`'s). Nothing *measures* the margin — there is no guard that fails when a shard
crosses, say, 60% of the ceiling. The headroom is now 7.9x instead of ~1x, which is a real
improvement, and the ci.yml comment states the arithmetic honestly. I file no finding: the brief's
"silently" is the part that is wrong, and the shape is documented at the line.

⚠ One measured deviation worth the sentence: the PR body predicts a **1.15x** per-shard spread;
CI measured **1.39x** (179 s … 248 s). The prediction was per-suite cost modelling, the measurement
includes runner variance. The claim round-robin exists to support — that it beats contiguous's
**17.9x** — holds comfortably.

### 4.5 Q5 — The aggregator. Refutation **attempted**; the one hole is round 1's, not a new one

I did not reconfirm the brief's reading; I went looking for states it misses.

`needs.<job>.result` takes one of `success`, `failure`, `cancelled`, `skipped`. `!= "success"` → `exit 1`
covers the other three, and `if: always()` keeps the job reporting instead of being skipped. So on
*result values* the check is total. What I checked beyond that:

- **No `paths:` / `paths-ignore:` filter anywhere in `ci.yml`** (grep: zero hits; triggers parse to
  `{pull_request: {branches: [master]}, push: {branches: [master]}}`). So the context reports on
  **every** PR to master and the #137 *required-check-pending-forever* shape is avoided. This is the
  state I most expected to find broken, given #137's history, and it is not.
- **`concurrency` with `cancel-in-progress: true` exists** and is a genuine route to a cancelled
  matrix — which is how PR #365's sweep died. A cancelled run's `mutation-sweep-complete` reports
  `cancelled`, which GitHub does not count as success for a required context. Failure direction is
  safe; a superseding run then supplies the new context.
- **No step-level `if`** on any of `mutation-sweep`'s six steps, so there is no "job green, step
  skipped" hole today.

**The hole I can name is L3 (§3.5) and it is round 1's M2(b):** the aggregator trusts job *success*
and cannot observe that eight distinct shards ran, nor that their union was the manifest. I could not
turn that into a reachable false green at `a5fcd951` — `strategy.job-index`/`job-total` are
GitHub-provided — so it stays Low.

### 4.6 Q6 — `fail-fast: false`. Measured on two real red runs, not inferred

Parsed: `strategy.fail-fast: false`, `matrix.shard: [1,2,3,4,5,6,7,8]` (len 8).

**One red shard does not stop the others** — run `37390914914`:

```text
mutation-sweep (1)  failure  23:52:36-23:55:40
mutation-sweep (5)  success  23:52:40-23:56:20   ← finished 40s AFTER shard 1 went red
(2,3,4,6,7,8)       success
mutation-sweep-complete  failure  23:56:25-23:56:28   ← ran after all shards, went red
```

**A red shard cannot mask a second red one** — run `37403975285`:

```text
mutation-sweep (3)  failure  02:24:37-02:27:32
mutation-sweep (4)  failure  02:24:36-02:28:23   ← ran to completion 51s AFTER shard 3 failed
(1,2,5,6,7,8)       success
mutation-sweep-complete  failure
```

Both reds ran to completion and each reported its own conclusion; the aggregator went red in both.
That is Q6 answered by measurement on the shipped configuration.

⚠ The aggregator prints only the aggregate word, so *which* shards failed is readable from the matrix
and not from the required context — round 1's L4 diagnosability family, unchanged.

---

## 5. What I tried to refute and could not

1. **The partition.** Re-derived from scratch at twelve N values including `N = length`,
   `N = length ± 1` and `N = length + 5`. No N drops, duplicates or reorders an entry. §4.1.
2. **The empty-shard refusal.** Tried to make an empty shard *pass*. `1201/1201` and `1300/1300`
   both `rc=2` with `NOTHING WAS MEASURED`. Emptiness is derived from `shard_slice`, so the
   "two copies drift" attack has no second copy to attack. §4.1.
3. **Shard-scoped global invariants.** Tried hardest here, with the sharpest fixture I could build —
   a perturbation in a file whose entries land in **none** of shards 2–5, checked from shards 2, 3
   and 5. All five invariants fired in all of them. §4.2.
4. **Attribution.** Tried to construct a shard-dependent `attributed`. The mutation, its suite run
   and its control are co-located in one shard by construction; `fails` cannot contain a foreign
   file's case names. §4.3.
5. **The aggregator.** Hunted for a non-`success`/non-failure state, a missing report, and a path
   filter. Found none; the absent `paths:` filter is the thing that makes the context safe to
   require. §4.5.
6. **`fail-fast: false`.** Tried to show a red shard cancelling or masking a sibling. Two historical
   runs refute it directly, including a two-red run. §4.6.
7. **⭐ The bytecode fix, through the one route the brief invited.** My hypothesis was a
   **grandchild spawned with a constructed `env=` dict that drops `PYTHONDONTWRITEBYTECODE`** — a
   route `child_env`'s capture cannot reach, because it is a *different* dict built further down.
   There are exactly two env-narrowing sites in the staged tree, and **both carry the variable**:
   `check-rc-contract.py:339` and `check-surface-recall.py:56-58`, bound together by a
   sibling-agreement case (`check-surface-recall.py:567`) that compares the two tuples. Every other
   `env=` site derives from `os.environ` and inherits it (`page_chrome.py:375` `{**os.environ, …}`;
   `observer_log.py:382` `dict(os.environ, …)` popping only `PYTHONIOENCODING`). **I could not
   exhibit a route the env-capture misses.** The in-process `exec_module` route (r4's Low 1) is
   covered too, because the spawned child's interpreter reads the variable at startup and that
   governs its own in-process imports — which is what the coordinator's 2-`.pyc`-vs-0 measurement
   shows.
8. **`verify` still running the sweep.** Checked, because if true the whole deliverable would be
   void. `git diff` shows the step `- run: python3 scripts/check-plan-code.py --mutate .` **removed**
   from `verify`; exactly one `--mutate` invocation remains in all workflows (`ci.yml:687`); the
   parsed `verify` job contains no `--mutate` step.

### Structural parse of the workflow (no `actionlint`; Ruby `YAML`)

```text
jobs: ["verify", "mutation-sweep", "mutation-sweep-complete"]
matrix shard: [1,2,3,4,5,6,7,8] (len 8)      fail-fast: false      timeout-minutes: 30
step-level if in mutation-sweep: [nil,nil,nil,nil,nil,nil]
complete: needs="mutation-sweep"  if="always()"  timeout=5
triggers: {pull_request:{branches:[master]}, push:{branches:[master]}}   (no paths filter)
concurrency: {group:…, cancel-in-progress:true}
verify has a --mutate step: false
sweep step env: {SHARD_INDEX: "${{ strategy.job-index }}", SHARD_TOTAL: "${{ strategy.job-total }}"}
```

---

## 6. Findings table

| # | Severity | Deliverable or instrument | Caused by a previous fold? |
|---|---|---|---|
| M1 | Medium | **Deliverable's tracking artifacts** — `docs/backlog.md` row 217, `docs/roadmap-to-launch.md:2227`; both are tracked files this PR should have changed | **No.** Absent since the branch began; not introduced by any fold |
| M2 | Medium | **Both** — the in-code narration is the instrument's own attribution trail; the dashboard entry and PR body are the deliverable's merge-gate evidence | **Yes.** `29fd2653` and `8c1a207a` (the bytecode fold) moved the counts and no narration followed; the PR body and dashboard entry were written against earlier commits |
| L1 | Low | **Deliverable** — `--shard`'s refusal contract | **No.** Round 1's L1, unfixed and undispositioned |
| L2 | Low | **Deliverable** — the matrix↔flag shell seam | **No.** Round 1's M2(a), unfixed and undispositioned |
| L3 | Low | **Deliverable** — the aggregator's observational scope | **No.** Round 1's M2(b), unfixed and undispositioned |
| Info | — | Instrument — a dead skip site in `run_mutations` | **No.** Pre-existing, unrelated to sharding |

**Q5 · thrashing, per finding.** None of the six was caused by the *previous* round's fix. M2 was
caused by two earlier folds in this branch, but it is a narration omission, not a re-instance of the
bytecode class. **No component shows two consecutive rounds of fix-caused findings in this round**, so
the `dev-process.md:113` condition does not re-arm here. It was already met and answered during the
bytecode arc (`cbfb8ba3`).

---

## 7. Verdict

# NOT CONVERGED

**This is NOT the second consecutive clean round.** Round 4 was the first round with no Blocking, no
High, no deliverable finding and no non-trivial fixes. **Mine has no Blocking and no High — but it
has findings aimed at the deliverable** (M1, and L1/L2/L3), so by `review-method.md:108`'s *"a
finding in the deliverable → CONTINUE"*, judged by **aim rather than severity** as `:112` requires,
the clean streak restarts rather than completing.

⭐ **Read the reason precisely, because it is not "the sharding is defective".** I attacked the
sharding harder than any previous round — the partition at twelve N values, eighteen boundary
invocations as real processes, five global invariants from shards that cannot see their subject,
attribution, the aggregator, `fail-fast` on two real red runs — and **broke none of it**. The
mechanism is sound, and CI is green on the exact merging commit.

What is not finished is the **ledger and the bookkeeping**:

- **three round-1 findings about the shipped half are unfixed and have no recorded disposition.**
  The brief's own premise — that the shipped half got one round of attention while the instrument got
  four — turns out to understate it: part of that single round's output was dropped. L1/L2/L3 need
  either a two-token fix or a written "accepted because unreachable from CI"; both are cheap, and
  silence is the one option the method does not allow.
- **#217 merges reading OPEN** in both the backlog and the roadmap (M1), which is backlog #219's
  exact failure mode.
- **four narration sites disagree with the tree** (M2), including the PR body a human reads at the
  merge gate.

**Every one of these is editorial or bookkeeping — no code redesign is implied.** Per
`review-method.md:116-119`, the documented cheap path applies: land M1, M2 and a disposition for
L1/L2/L3 **ahead of** the next round, and the next round is a short confirmation rather than a sixth
pass at the design. If the human prefers, L3 is reasonably deferred to a backlog row — but *recorded*
either way.
