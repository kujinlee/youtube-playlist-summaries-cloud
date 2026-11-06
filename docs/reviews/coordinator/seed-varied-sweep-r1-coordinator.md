# Round 1 — `seed-varied-sweep` (backlog #506, its last part) — coordinator — NOT CONVERGED (Codex), folded

Both halves ran on `8972ed35`: Claude CONVERGED with one MAJOR and two MINOR; Codex NOT CONVERGED with two MAJOR, each
with a runnable reproduction (`/tmp/svs-review-probes.py`, re-run against the fold: all five probes now fail closed).

```yaml
round: 1
fixes_nontrivial: true
subject: seed-varied-sweep
halves:
  codex: ran
  claude: ran
findings:
  - {id: CM1, severity: Medium, aim: instrument, fix_induced: false, component: seed-outcome, disposition: fixed}
  - {id: Cm2, severity: Low, aim: instrument, fix_induced: false, component: workflow, disposition: declined}
  - {id: Cm3, severity: Low, aim: instrument, fix_induced: false, component: report-text, disposition: fixed}
  - {id: XM1, severity: Medium, aim: instrument, fix_induced: false, component: seed-isolation, disposition: fixed}
  - {id: XM2, severity: Medium, aim: instrument, fix_induced: false, component: seed-outcome, disposition: fixed}
```

## Each finding

**CM1 (Claude MAJOR 1) — FIXED.** `seed_outcome(runs, wants=...)` now compares, across seeds, only the red cases the
mutation NAMES (its `expect` list); `run_mutations` hands it `mut.get("expect")`. With no `expect` it still compares the
whole red set (nothing narrower is claimed, so the stricter rule stands). The real shape Claude measured on #506's own
mutant — the expect case red under seeds 0 and 266, two incidental cases red only under 0 — is the adjacent negative.
Cases: `⭐ r1 M1: the expect case red under EVERY seed, an extra case under one, is an ordinary attributed kill`
(unit, built from the two real outputs), `⭐ r1 M1 END TO END: the named case red under every seed + an incidental one
under one seed is KILLED` (through `run_mutations`), and the positive `...but the NAMED case red under one seed and not
the other (both killed) is NONDETERMINISTIC`. The old disjoint-sets case still holds for the no-`expect` fallback.

**XM1 (Codex MAJOR 1) — FIXED.** New `seed_runs(d, name, seeds)`: every seed after the first runs in its own copy of
`d`, every copy taken BEFORE any seed runs, then deleted. Both the mutant runs (`run_mutations`) and the controls
(`control_parts`) go through it. A tree that cannot be copied is rc 2 (NOT CHECKED) for that seed, never a run in the
shared tree. A direct case runs three seeds and shows each under its own seed, none seeing another's marker
(`...seed_runs, three seeds: ...`). Case: `⛔ r1 Codex M1 END TO END: a seed never reads the files an EARLIER seed's run left —
NONDETERMINISTIC` (Codex's own cache fixture) and `⛔ r1 Codex M1: seed_runs cannot isolate a seed (the tree cannot be
copied) -> CANNOT RUN, never a run`. **Bound, stated in the docstring:** the seeds are independent of EACH OTHER; all
start from `d` as it stands, which still carries what earlier mutants' runs left there — the unseeded harness's own
pre-existing exposure, not introduced here and not fixed here. **Cost:** one copy of the staged tree (86 MB, ~3,700
files) measured 4.0 s on a Mac laptop, so one extra copy per mutant and per control on the scheduled sweep only; CI's
copy time is not measured.

**XM2 (Codex MAJOR 2) — FIXED, for the seed-introduced hole.** A mutant killed under every seed whose suite COMPLETED
(printed its `passed` summary — the token `control_is_green` already reads) under some seeds and not others is now rc 2,
NOT CHECKED, naming the seed that stopped. Case: `⛔ r1 Codex M2: a suite that COMPLETED under one seed and stopped early
under another is a cannot-run`; adjacent negative `...ADJACENT: a suite that stops at the same place under EVERY seed is
judged as the unseeded run judges it`. **Not done, deliberately:** a suite that stops early under EVERY seed (and under
the unseeded PR sweep) is still judged as the harness has always judged an rc 1. Making that NOT CHECKED changes the
PR sweep's verdict on every existing mutant that is killed by a crash, which needs a full-sweep measurement first. It is
a pre-existing property of the unseeded harness, not something `--seeds` introduced; reported to the coordinator as a
candidate backlog row rather than filed from this fold.

**Cm3 (Claude MINOR 3) — FIXED.** The NONDETERMINISTIC report now says the kill "is seed-dependent or timing-dependent",
and tells the reader to re-run `--seeds A,B` first: reproduces → the seed, else timing. Covered by the existing
`⭐ #506 END TO END` case's prefix check (wording only; no new guard clause, so no new mutation).

**Cm2 (Claude MINOR 2) — DECLINED, with the path exercised locally instead.** A `workflow_dispatch` trigger is not cheap
here: `ci.yml` has none, so adding one opens a manual run of EVERY job in the file, and `check-merge-ready.py` audits
each event-keyed line. Instead: Codex's probe already ran the workflow's `run:` block under 16 event/run-id inputs
(scheduled runs get two distinct valid seeds; every other event none); this fold re-ran it green. And the seeded path
was run for real on the subject #506 is about — see *Measured on the real mutant* below. The doubled shard time on CI
stays PREDICTED until the first nightly; a timeout there still reaches `sweep-red-alert` (any non-success files).

## Measured on the real mutant

`python3 scripts/check-plan-code.py --mutate . --only scripts/check-review-decision.py --seeds 0,266` — the seeded
path, for real, over the 30 mutations of the script #506 was measured on:

- **First run, after the CM1 fix:** `FAILED — 30 mutation(s), 29 killed, 29 attributed, 1 NONDETERMINISTIC`. The one was
  #506's own mutant (`scope_lead's tied names lose their stable order...`), and the verdict was RIGHT: its `expect`
  list named TWO cases, and the second, `...and the tied names are reported in a stable order, because the reader prints
  them`, is itself hash-order dependent — red under seed 0, not under 266. So the unseeded PR sweep under seed 266 would
  also have failed attribution on it. Claude's measurement held for the #506 case it named, and missed that the entry's
  other named case varies. **Fixed in the manifest:** that entry's `expect` drops the hash-dependent case and keeps the
  #506 case, which is red under every seed (Claude measured 600/600). This is the class check finding its first real
  instance on its first real run.
- **Second run:** `OK — 30 mutation(s), 30 killed, 30 attributed to the case each names, 0 survivor(s) ... under
  PYTHONHASHSEED 0, 266`.
- **Time:** the same slice unseeded took 16 s; seeded, 201 s (Mac laptop, sys time 1m51s — the per-seed tree copies
  dominate). The CI runner's copy cost is NOT measured; `ci.yml`'s timeout comment now says so. ⚠ This is the main risk
  this fold adds: if a shard's copies on the runner are as slow as here, the 60-minute scheduled budget can be exceeded;
  a timeout files `sweep-red` and is visible, not silent.

## Mutations

`scripts/check-plan-code.py` pin 199 -> 205. Six new entries, one per new guard clause: the stopped-early comparison,
the named-case filter, its no-`expect` fallback, the `expect` wiring in `run_mutations`, the per-seed copy, and the
cannot-copy rc 2. Two existing entries (`the control runs under the FIRST seed only...`, `a red control's report stops
naming the seed...`) were re-bound to `control_parts`' new body. Each of the eight, applied to a temp COPY of the repo
(`scripts`, `docs`, `supabase`, `.github`, `.claude/hooks`, `node_modules/typescript`, `.agents/skills`, `.githooks`) with
`HOME` redirected, goes rc 1 with its named case red (8/8). The 19 other #506 entries re-run the same way: 19/19 still killed by their named case.
Every anchor in every manifest under `scripts/mutations/` binds exactly once (applied in sequence), 0 unbound.

## Coordinator addition after the fold

**Cost finding.** The fold's `seed_runs` copied the whole staged tree for EVERY mutant and EVERY control, once per
extra seed. Measured on this Mac: the 30-mutant `check-review-decision.py` slice went 16 s unseeded → 201 s with
`--seeds 0,266`. The nightly shards run ~20-27 min unseeded, so a ~12x factor would pass the 60-minute shard timeout
every night (a `sweep-red` every night, for a cost, not a defect).

**Design, as built.** ONE tree per extra seed PER RUN (per shard). `seed_trees(d, seeds, cleanup)` copies `d` once
for each seed after the first — in `mutate_delivered`, after the redirected home exists and before the first control
— and the run's `ExitStack` deletes them. Every control, mutant and re-control under a seed runs in that seed's tree
(`control_parts(..., trees)`, `run_mutations(..., trees=trees)`, `seed_runs(..., trees)`). Each mutation is written
to every seed's tree (`seed_apply`) and restored in every seed's tree with a read-back (`seed_revert`), exactly as in
`d`, so a seed's tree differs from `d` only by what that seed's own runs left. Seeds stay isolated from EACH OTHER
(Codex r1 M1; its cache fixture end-to-end case stays red under the shared-tree mutation). Cross-mutant leftovers
within one seed's tree are the unseeded sweep's existing exposure and stay out of scope. Fail closed: a tree that
cannot be copied, or that the mutant cannot be written to, is that seed's rc 2 (NOT CHECKED, never killed); a tree
that cannot be restored STOPS the run before the mutant is credited, so the declared count cannot balance and no
tally is built. A direct `run_mutations` call with seeds and no trees makes its own, once for all its mutants.

**Measured** (`python3 scripts/check-plan-code.py --mutate . --only scripts/check-review-decision.py`, Mac laptop,
other agents running, so absolute times are noisy):

| Run | Wall time | Result |
|---|---|---|
| unseeded, before | 20.8 s | 30 killed, 30 attributed |
| `--seeds 0,266`, before (the fold, `dc961453`) | 414.2 s (sys 153 s; the fold's own measurement was 201 s) | 30 killed, 30 attributed |
| `--seeds 0,266`, after | 57.6 s (sys 11.9 s) | 30 killed, 30 attributed |
| unseeded, after (same load as the line above) | 32.5 s | 30 killed, 30 attributed |

Seeded now costs about two suites per mutant — 1.8x the unseeded run measured beside it — instead of ~12-20x. The
nightly shard estimate is therefore ~2x its unseeded 20-27 min, still PREDICTED until the first scheduled run.

**Cases and mutations.** Nine new self-test cases (343 → 352): the trees persist across calls and each holds only its
own leftovers; `seed_trees` copies the `d` it is given and its cleanup deletes the copy; `seed_apply` writes every
seed's tree but `d`, and a tree it cannot write is a CANNOT RUN; `seed_revert` restores, and a tree it cannot restore
names the seed and says STOPS; `run_mutations` uses the trees it is handed; end to end, an unrestored tree stops the
run before crediting the mutant (0 entries, NOT MEASURED); and through `mutate_delivered`,
a suite that reds on another seed's leftovers and skips its check in a tree it has never run in stays Measured and
green — the fold's per-call copies make its mutant survive under seed 7 only (NONDETERMINISTIC), which is the failing
case for this change, shown by the mutation that restores the per-mutant copy. Mutation pin 205 → 215: ten new
entries, six re-bound to the new text; each of the sixteen applied to a temp COPY of the repo is killed by its named
case. Every anchor in every manifest binds exactly once.
The `ci.yml` timeout comment, which priced the per-mutant copies, now carries these numbers.
