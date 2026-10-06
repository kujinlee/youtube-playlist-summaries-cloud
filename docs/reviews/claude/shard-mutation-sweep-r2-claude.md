# shard-mutation-sweep — round 2, Claude half (standing in for Codex)

REVIEW GAP: codex — refused to start with `no visible, API-supported model with a priority found in cache`, which is a model-resolution failure and NOT a timeout, so `docs/plugins.md`'s immediate-fallback rule applies rather than its double-the-timeout-and-retry rule. `scripts/codex-frontier-model.py --write-config` was run once and reported the same error, so the one sanctioned retry is spent. This Claude half ran a full adversarial review in its place. ⛔ THE CODEX-SPECIFIC PASS IS STILL OWED BEFORE MERGE — and it is not a formality here: round 1's Codex half found the `--self-test` ordering defect that this fold repairs, and the Claude half did not independently find it.


**Subject:** `git diff eee31527..26661d75` — `scripts/check-plan-code.py`,
`scripts/mutations/check-plan-code.json`, `.github/workflows/ci.yml` (backlog #217).
**Branch:** `shard-mutation-sweep` · **PR** #366 · **commit** `26661d75` · **date** 2026-10-05.
**Mandate:** refute, not confirm. Rounds 2+ are scoped to the fold.

**VERDICT: NOT CONVERGED.** 1 High · 2 Medium · 2 Low.

The fold's root-cause trace is **right**, and I reproduced it independently rather than taking it
from the brief (V7 below): without the one-line fix, mutating `observer_log.py` and restoring its
source leaves `check-banner-armed.py`'s after-control at **155/160 with the same five failing
cases** CI reported in round 1; with the fix, **160/160**. Two wrong attempts were deleted and the
right one is three lines of code and twenty of reason.

It is not converged because **the fix closes one half of the mechanism and the code comment claims
it closes the whole thing.** `PYTHONDONTWRITEBYTECODE=1` stops the harness's children *writing* a
bytecode cache. It does nothing about *reading* one — and `stage_tree` copies the real repo's
`scripts/__pycache__/` into **every** staged tree: 89 files today, 55 of them for modules that are
mutation targets. I reproduced H1's exact symptom at
`26661d75`, with the fix in force, through that route.

---

## ⛔ CODEX GAP — THE CODEX-SPECIFIC PASS IS OWED BEFORE MERGE

This document is the **Claude half standing in for Codex**, written under
[`docs/plugins.md`](../../plugins.md) → *Fallback — Codex unavailable for ANY reason → never block*.

**Why Codex could not run.** The wrapper refused with
`no visible, API-supported model with a priority found in cache`, and
`python3 scripts/codex-frontier-model.py --write-config` did not change the outcome. That is an
auth/model-availability answer, not a timeout, so the timeout rule (*double `--timeout` and re-run
once*) does not apply and the fallback is immediate and correct.

**What is owed.** Round 2's **Codex-specific** adversarial pass has NOT run. This half satisfies
the gate for proceeding; it does not discharge the Codex pass. Re-attempt
`python3 scripts/codex-review.py --prompt-file <path> --review-id shard-mutation-sweep-r2-codex`
before merge if access returns. ⚠ Round 1's Codex half found the one defect this fold's `main`
retarget repairs (`--self-test --shard garbage` exiting 0) and **this half did not independently
find it** — the two halves are not redundant here, measured on this very branch.

---

## Verification — what I ran

Everything is output from this machine or the live CI run, re-derived rather than quoted.

### Executed

| # | Command / experiment | Result |
|---|---|---|
| V1 | `python3 scripts/check-plan-code.py --self-test` | **`160/160 passed`** — re-derived, matches the docstring |
| V2 | `python3 scripts/check-plan-code.py --mutate . --shard 6/8` | **rc=0** — `OK — delivered scripts mutated: 52 file(s), 149 mutation(s), 149 killed, 149 attributed to the case each names, 0 survivor(s) — measured over shard 6 of 8 (round-robin)` |
| V3 | `load_manifests(ROOT)` driven directly | **1,195** entries · **0** problems · `EXPECTED_MUTATIONS` sum **1,195** · `check-plan-code.py` **94 == 94** · 0 per-file mismatches · 0 declared-but-absent · **0 duplicate `(file,name)` ids** |
| V4 | every anchor of all 1,195 entries counted in the delivered tree | **0 orphaned, 0 ambiguous** |
| V5 | partition over the real 1,195 at N = 1,2,3,7,8,16 | exact union, zero duplicates, sizes 149..150 at N=8 |
| V6 | the 3 new + 1 changed manifest entries applied by hand in a **staged** tree (control **160/160**) | all four rc=1, and **each died via the case its `expect` names** — table in Q3 |
| V7 | ⭐ the H1 sequence reproduced twice, with and without the fix, from a cache-free staged tree | `unset` → after-control **rc=1, 155/160, 5 fails**; `=1` → **rc=0, 160/160** |
| V8 | ⭐ a mutant `.pyc` planted so its `(mtime, size)` match the **original** source, fix in force | `check-banner-armed.py` → **rc=1, 155/160**, the same five case names. Finding **H1** |
| V9 | write-side control pair: one suite run with / without the env line, `__pycache__` wiped first | `unset` → `observer_log.cpython-314.pyc` **written**; `=1` → **NONE**. The fix works on the write half |
| V10 | all 57 manifest target suites run **twice** in one staged tree (171 suite runs total) | 0 reds either pass, **0 rc changes**, and **zero bytes written anywhere under `.claude/`** |
| V11 | the `check-surface-recall` cleanup-sever mutation applied, source restored, all 57 suites re-run | residue `_selftest-36613.sh` **does** survive the restore; **57 of 57 suites still green**. Finding: the deletion was right |
| V12 | `scripts/__pycache__` after V10's 171 runs | **0** files written after the tree was staged — the fix holds over a realistic load |
| V13 | `python3 scripts/check-fixture-variation.py` | **rc=0** — `767 parameter(s) across 62 file(s); 117 ratcheted, 7 exempt` |
| V14 | `python3 scripts/check-docs.py` | `Documentation integrity OK` |
| V15 | `gh pr checks 366` + `gh run view 37406337840 --json headSha` | headSha **`26661d75`**; `mutation-sweep (1..8)` **all pass**, `mutation-sweep-complete` **pass**, `schema-gates` **pass**, `verify` **fail** |
| V16 | `gh run view --job 112084643686 --log-failed` | `verify`'s only failure is `check-review-recorded` demanding **this round**. Not a defect |
| V17 | exposure set: mutation targets ∩ modules with a cached `.pyc` in the real repo | **55 of 57** |

### Could not run — treat these as NOT MEASURED

- **`--mutate .` unsharded.** Forbidden by the brief (~29 min). I have no independent whole-manifest
  verdict, and no independent confirmation of the 1,758s baseline.
- **"39 of 39 document guards green."** I ran `check-docs.py` and `check-fixture-variation.py`; I did
  not enumerate the coordinator's 39-guard population, so that line is **NOT MEASURED** by me.
- **A naturally-occurring poisoned cache in the real repo.** H1's *mechanism* is measured (V8); its
  *arrival path* in ordinary use is reasoned, not constructed. Stated as such in the finding.
- **`python3` here is 3.14; CI pins 3.12.** Every local result is PROVISIONAL in this repo's sense.
  ⚠ For H1 this cuts the other way: the staged cache carries **both** `cpython-312` and
  `cpython-314` files, so the hazard exists under either pin.

---

## Findings

Findings and proposed fixes are stated **separately**. **Every proposed fix is UNVERIFIED** — I
wrote no fix and ran no fix.

---

### H1 — HIGH · The one-line fix closes the WRITE half of the race; the READ half is open, and the comment asserts there is no window

**Finding.** `child_env` now sets `PYTHONDONTWRITEBYTECODE=1`, and the comment defending it says:

> ⚠ WHY NOT "DELETE `__pycache__` AFTER EACH RUN": that is the same restore-the-damage shape one
> directory over, and it leaves the window open for anything that reads the cache DURING a run.
> **Not writing it has no window.**

The last sentence is false as written. *Not writing* has no window **for caches this run creates**.
It has the same window as before for **a cache the run did not create** — and the harness imports
one on purpose. `stage_tree` is:

```python
shutil.copytree(src, dst)        # scripts/check-plan-code.py:260 — no `ignore=`
```

so `scripts/__pycache__/` is copied into every staged tree. Measured in a tree I staged with the
shipped `stage_tree`:

```
staged pyc count: 89
mtime/size, source vs staged, observer_log:
  1790217558 25368  scripts/observer_log.py
  1790217558 25368  <staged>/scripts/observer_log.py
  1790217578 24099  scripts/__pycache__/observer_log.cpython-314.pyc
  1790217578 24099  <staged>/scripts/__pycache__/observer_log.cpython-314.pyc
```

`copytree` uses `copy2`, so **both** the sources and the caches arrive with their mtimes preserved —
which means a cache that looks current in the real repo looks current in the staged tree too, and
`PYTHONDONTWRITEBYTECODE` does not make Python ignore it.

**Exhibiting input (V8), and it reproduces H1 exactly.** In a staged tree with `__pycache__`
emptied so the start state is unambiguous:

1. control: `check-banner-armed.py --self-test` → **rc=0, 160/160**;
2. write the mutant `observer_log.py` (`path.open("a", …)` → `path.open("w", …)`, a **1-for-1
   character swap, so the size is identical by construction** — the same shape the fold's own
   analysis identifies as why `(mtime, size)` validation fails);
3. `py_compile` it → `scripts/__pycache__/observer_log.cpython-314.pyc`;
4. restore the source **byte-for-byte** and `os.utime` its mtime back to the compile mtime;
5. assert the source is the original: `src.read_bytes() == O` → `True`;
6. re-run the suite **through `child_env`, fix in force**:

```
AFTER POISON (cache OFF for writes) rc= 1 155/160 self-test
fails: 5
   [FAIL] F97a an unarmed BANNERLESS turn whose text grew adds NO warn-log line …
   [FAIL] F97b a real warning and a late flush coexist …
   [FAIL] R5-1051 the LATE FLUSH note reports the counts it MEASURED …
   [FAIL] H2b ...and the mirror — pausing AFTER that turn ended does not retroactively excuse it …
   [FAIL] H-A2 ...and the mirror — arming a plan AFTER that turn ended does not retroactively excuse it …
```

**155/160, five cases — the number and the shape round 1's CI log reported.** The delivered fix is
in force throughout.

**Why this is High rather than a note.**

1. It is the **same defect class** as the one the fold's headline fix was written for, left
   half-closed, in the instrument every other guard's evidence rests on.
2. The code comment states completeness (*"Not writing it has no window"*), so the next reader has
   no reason to look. This repository's own recorded failure is *a gate's claim outliving its
   subject*; here the claim was never true of the whole subject.
3. ⭐ **The new self-test case asserts the MECHANISM, not the property** — this file's own recorded
   rule, `assert the property, not the mechanism`:

```python
case("⛔ every suite the harness spawns runs with the bytecode cache OFF, or a mutant "
     "outlives the restore of its own source and the next importer silently gets it",
     (_e1.get("PYTHONDONTWRITEBYTECODE"), _e2.get("PYTHONDONTWRITEBYTECODE")), ("1", "1"))
```

   The case's *sentence* is the property (*"a mutant outlives the restore … and the next importer
   silently gets it"*). Its *assertion* is two dictionary lookups. A property-shaped case is
   literally V8 — plant a mutant cache for a module, restore the source, assert the importer sees
   the source — and **it fails on the shipped tree**. So the suite cannot tell this fix from a
   complete one, which is why the gap shipped.
4. **Exposure is wide, not narrow:** 55 of the 57 mutation targets already have a `.pyc` in the real
   repo (V17), and the importers that consult one include `observer_log` (3 importers),
   `page_chrome` (6), `page_markup` (5), `m4_catalog` (5), `m4_base_db` (7), `subject_status` (3),
   `coverage_verdict` (1 — `check-plan-code.py` itself), plus 14 scripts loading siblings through
   `spec_from_file_location`.

**What I could NOT show, stated rather than implied.** I did not construct a *naturally occurring*
poisoned cache. `git checkout`/`switch` always stamps a new mtime, which invalidates a cache
correctly, and `run_mutations`' restore is `write_text(orig)` — content only, new mtime — so the
harness's own restore cannot revive a staged cache. **The hazard is latent, not live today.** My
reasoning for how it arrives (labelled as reasoning): a peer process editing a `scripts/` module in
the real repo while another imports it leaves a cache for a version that is then reverted, and a
same-size revert inside one mtime tick is the H1 race one directory up. This session has 50+ named
concurrent agents and the repo's own memory records *a live agent's file is not static* costing it
twice in one night. ⚠ And I am an instance of the writer: my first measurement imported
`check-plan-code.py` and wrote `scripts/__pycache__/check-plan-code.cpython-314.pyc` into the real
repo at 19:51, which `stage_tree` then copied into every tree I staged. `git status` stayed clean —
`.gitignore:73` is `__pycache__/`.

**Proposed fix — UNVERIFIED, and it removes the class rather than the instance.** Give `stage_tree`
an ignore: `shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__"))`. Then the
staged tree has no cache to read, the env line keeps one from being created, and the two halves
together are closed. ⚠ Do **not** replace the env line with this — a child can still create a cache
for a module it imports mid-run, which is the window the comment correctly objects to. Both, or the
fix stays half. And **re-shape the case to the property**: V8 is the experiment; its falsifier is
that removing *either* half makes it red.

---

### M1 — MEDIUM · Two nested spawns build an allow-listed environment that silently drops the variable

**Finding.** The harness has exactly **one** spawn point —
`run_suite_parts` at `scripts/check-plan-code.py:535`, `env=child_env(d)` — and I found no
`os.system`, `os.popen`, `os.exec*` or second `subprocess.run` on any live path. Nested spawns
inherit the environment, so the fix propagates. **With two exceptions**, both of which construct a
fresh environment from an allow-list:

```python
SUBPROCESS_ENV_KEYS = ("PATH", "HOME", "TMPDIR", "LANG")     # check-rc-contract.py:332
_env = {k: v for k, v in os.environ.items() if k in SUBPROCESS_ENV_KEYS}
```

- `scripts/check-rc-contract.py:295` (in `observe`)
- `scripts/check-surface-recall.py:158` (in `_render_once`) — which *borrows* the same tuple from
  `check-rc-contract` at `:552-564`, so the tuple is single-sourced and the fix is one edit

`PYTHONDONTWRITEBYTECODE` is not in the tuple, so inside those two spawns bytecode writing is back
on. **It does not bite today**, and I checked rather than assumed: both spawn `bash <hook>`, and the
python those hooks reach is `python3 "$MATCHER" --fire` (a stub in a temp dir) and `python3 -c` —
a `__main__` script is never byte-cached, and neither stub imports anything from `scripts/`. V12
confirms it empirically: **zero** `.pyc` written across 171 suite runs.

So this is the one real bypass path of `child_env`, and what makes it harmless is a property of
today's hook arms, not of the harness. The moment any arm invokes a `scripts/` script that imports
a sibling, bytecode writing resumes inside the staged tree and H1's race returns **with nothing in
a diff to show it** — the allow-list drops the variable silently, by design.

**Exhibiting input.** `SUBPROCESS_ENV_KEYS` at `check-rc-contract.py:332` versus `child_env` at
`check-plan-code.py:160-183`: one sets the variable, the other filters it out, and no check
compares them.

**Proposed fix — UNVERIFIED.** Add `"PYTHONDONTWRITEBYTECODE"` to `SUBPROCESS_ENV_KEYS` (one place,
borrowed by the sibling). The scrub exists to stop *ambient noise* reaching a hook's stderr —
round 8 H2's `PYTHONVERBOSE` incident — and this variable produces no output, so keeping it costs
the scrub nothing. The alternative, and arguably the better one because it is not a list anyone can
forget: have `child_env` be the thing that is asserted, by giving the scrub an explicit
`PASS_THROUGH` set with a written reason per member.

---

### M2 — MEDIUM · The ci.yml comment shipped at this commit tells the superseded story, and points the reader at a mechanism this commit deleted

**Finding.** `.github/workflows/ci.yml` gained 17 lines in this fold. Its last paragraph, as
shipped at `26661d75`:

> ⭐ THIS IS NOT HYPOTHETICAL — IT FIRED ON THE FIRST CI RUN OF THIS VERY CHANGE. Shard 1 of 8
> reported `CANNOT RUN — scripts/check-banner-armed.py is no longer green AFTER the sequence` …
> The defect is upstream of it — a mutation's EXECUTION can leave state in the shared staged tree
> that the next control then reads. **See `run_mutations`, which restores the mutated FILE and,
> before this change, nothing else.**

Two problems, both in the record rather than the code.

1. **"before this change, nothing else" is false at this commit.** The `.claude/` snapshot/restore
   that sentence refers to was added in `29fd2653` and **deleted in `26661d75`**, the same commit
   that shipped this comment. Measured: `run_mutations` at HEAD writes the mutant
   (`write_text(src)`) and the original (`write_text(orig)`) and touches nothing else. So the
   comment tells a reader the harness now restores more than the file, and it does not.
2. **It cites H1 as the realisation of round 1's H2 amplification claim, which this commit's own
   message retracts.** The comment's story is a probabilistic flake sampled 7.21x more often; the
   commit's story — and V7's reproduction — is a bytecode cache, which is deterministic once the
   mutant compiles and whose per-shard incidence turns on an mtime tick, not on control count. A
   reader cannot believe both. And the words `PYTHONDONTWRITEBYTECODE`, `__pycache__` and
   `child_env` appear **nowhere** in the workflow — so the file a future N-retune will open
   describes the wrong cause and names none of the fix.

The 7.21x amplification claim itself is **sound and worth keeping** — round 1 measured it and I did
not attempt to re-derive it, so I treat it as standing. What is wrong is the instance it is pinned
to.

**Exhibiting input.** `git diff eee31527..26661d75 -- .github/workflows/ci.yml` beside
`git show 26661d75 --format=%B | head -40`, and `run_mutations` at `scripts/check-plan-code.py:1813`.

**Proposed fix — UNVERIFIED, prose only.** Keep the amplification paragraph; replace the
`⭐ NOT HYPOTHETICAL` paragraph with the traced cause — a mutant `.pyc` outliving the restore of its
own source, `child_env`'s `PYTHONDONTWRITEBYTECODE`, and (if H1 is accepted) `stage_tree`'s ignore —
and say explicitly that shard 1's red was the gate behaving correctly over a cause that was **not**
the control amplification. If the author still believes H1 was an instance of H2, the round document
should carry the per-finding evidence for that, because the commit message argues the opposite.

---

### L1 — LOW · "The two retargeted anchors" is one retarget and one `expect` re-encoding; the record is wrong, both bind

**Finding.** The brief (and the fold's framing) describe two manifest entries orphaned by the
coordinator's own refactor. Compared semantically against `eee31527`, the manifest shows:

| | What actually changed |
|---|---|
| `#217: --shard without --mutate is accepted silently instead of refused` | **renamed and retargeted** to `#217: main stops obeying the shard mode refusal, …`; anchor moved from `if not a.mutate:` inside the `if a.shard:` block to `_mode_why = shard_mode_refusal(a.shard, a.mutate)\n    if _mode_why:` — the call site. A genuine retarget, correct, forced by the lift-out |
| `mutate_delivered keeps the reporter to itself …` | **anchor UNCHANGED** — `progress=progress)` → `progress=None)` in both versions. Its `expect` went from a one-element **list** to a **string**. Occurrences of `progress=progress)`: **1 at `29fd2653`, 1 at `26661d75`** — it was never ambiguous and never orphaned |

So one anchor was retargeted and one `expect` was re-encoded. Both bind, both die correctly (V6).
Low, and filed only because this repo's recorded cost for mis-stating what a mutation entry is about
is *an anchor is unbound by ANY nearby edit* — a record that says "retargeted" where nothing moved
is the same error with the sign flipped, and it is how a future orphan gets explained away.

**Proposed fix — UNVERIFIED.** State it as one retarget plus one `expect` normalisation in the PR
body and the round record.

---

### L2 — LOW · The call-site entry kills a strict subset of the pure-function entry's cases

**Finding.** Measured (V6): severing `shard_mode_refusal`'s own predicate reddens **two** cases;
severing `main`'s `if _mode_why:` reddens **one** — and that one is a subset of the two. So the
call-site entry adds no case the function entry does not already reach. It *is* attributed, so the
harness's contract holds, and the pair is still worth having: the function entry cannot distinguish
*the rule is gone* from *nobody obeys it*, which is exactly the defect round 1's Codex half found
(an ORDER defect — the rule existed and `--self-test` ran before it). But a reader counting
coverage will read two entries as two independent guards and they are nested.

**Proposed fix — UNVERIFIED.** Either note the nesting in the entry name, or give the call-site
entry a case that only it can kill — e.g. `main(["--self-test", "--shard", "2/8"]) == 2` asserted
through a subprocess rather than in-process (the suite cannot call `main` re-entrantly, which is
exactly why `shard_mode_refusal` was lifted out, and a subprocess sidesteps that).

---

## The four questions, answered whether or not they yielded a finding

### Q1 — Is the one-line fix complete? Does every suite the harness spawns receive that env?

**For the WRITE half: yes, and measured.** `run_suite_parts` at `:535` is the only spawn in the
harness (no `os.system` / `popen` / `exec` / second `subprocess.run` on a live path), and it passes
`env=child_env(d)`. Nested children inherit it. Control pair (V9): with the line, a suite run writes
**no** `.pyc`; without it, `observer_log.cpython-314.pyc` appears. Over 171 suite runs in one staged
tree (V12), **zero** `.pyc` were written.

**One bypass path exists and does not bite today — M1.** `SUBPROCESS_ENV_KEYS` in
`check-rc-contract.py:332`, borrowed by `check-surface-recall.py`, builds a fresh environment that
drops the variable. Both uses spawn `bash`, whose python is a `__main__` stub importing nothing from
`scripts/`, so no cache is produced. It is a silent drop, not a visible one.

**But the fix is NOT COMPLETE as a fix for the mechanism — H1.** It governs writing only, and
`stage_tree` hands every run 89 cache files it never validates. I reproduced H1's exact symptom
with the fix in force.

### Q2 — Was deleting the `.claude/` restore right?

**Yes, and I could not make it load-bearing. The deletion is better supported than the bisect
argues for it.** Three measurements:

1. **No suite writes into `.claude/` at all.** All 57 manifest target suites, run **twice** in one
   staged tree (171 runs): `.claude/` additions **0**, removals **0**, size changes **0**; every
   suite green in both passes; **0** rc changes between passes (V10).
2. **The residue IS real, and it still survives the restore — and nothing reads it.** I applied the
   shipped manifest entry *"the fixture hook stops being removed …"* to
   `scripts/check-surface-recall.py`. The mutant left `_selftest-36613.sh` in the staged
   `.claude/hooks/`; the source restore did not remove it; I then ran **all 57** suites with the
   residue in place → **0 reds** (V11). That is the case the brief asked me to construct, and it
   does not break a control.
3. **Why, structurally.** The sole enumerator of `.claude/hooks/` in the whole `scripts/`
   population is `check-ratchet-contract.py:192`, which excludes `FIXTURE_PREFIX` by name and has
   three dedicated cases for it (`:854-856`). The writer cleans up in a `finally`
   (`check-surface-recall.py:440-442`) and asserts the removal in two of its own cases
   (`:741-743`) — which is what makes the sever a *caught* mutation. The fixture is **pid-scoped**,
   so another run's residue cannot satisfy or break it. And both ends of that mechanism already
   have manifest entries: the cleanup sever, and *"the `_selftest-` exclusion is removed"* on the
   reader. `check-banner-armed.py` redirects `WARN_LOG` to a fixture dir for the whole block that
   writes it (`:1798-1801`, restored `:2389`), so round 1's H1 hypothesis about
   `.claude/banner-warnings.log` is also refuted: nothing is written there.

The two `_selftest-47908` files the coordinator found in the working tree are consistent with an
**interrupted** run — a `finally` does not run under SIGKILL, and the round-1 commit records
exactly such an interruption. That is debris from a killed process, not a mechanism a control
depends on.

⚠ **The honest residual:** what makes residue harmless is one `startswith(FIXTURE_PREFIX)` in one
file. A future writer that leaves a file in `.claude/hooks/` **without** that prefix would be read
as R3 caller evidence — the precise false green R3 exists to catch, arriving through the directory
R3 trusts most, which `check-ratchet-contract.py:182-190` already says in its own words. That is an
argument for keeping that exclusion mutation-covered (it is), not for restoring the snapshot.

### Q3 — The two retargeted anchors: still bound, still dying via the named case?

**Yes, all of them, verified by applying them in a staged tree whose control is 160/160.** And the
"two retargeted" framing is wrong — see L1.

| Entry | rc | fails | `expect` satisfied | Named case reddened |
|---|---|---|---|---|
| `mutate_delivered keeps the reporter to itself …` (`progress=progress)`) | 1 | 4 | 1/1 | `every phase of --mutate reports its position when a caller asks` |
| `#217: main stops obeying the shard mode refusal …` (`if _mode_why:`) | 1 | 1 | 1/1 | `--shard without --mutate is CANNOT RUN, not a silent whole-manifest run` |
| `the shard mode refusal stops firing …` (the pure predicate) | 1 | 2 | 1/1 | `⛔ a shard alongside --self-test is refused, not silently accepted …` |
| `#217: the bytecode cache is left ON …` | 1 | 1 | 1/1 | `⛔ every suite the harness spawns runs with the bytecode cache OFF …` |

The `main` entry's anchor includes the assignment line above the `if`, which is what keeps it bound
to the **call site** rather than to any `if _mode_why:` elsewhere; there is exactly one occurrence.
The subset relation between the last two is L2.

### Q4 — Is anything else order-dependent through `__pycache__`?

**Yes — and it is the round's main finding, H1.** The fix stops *this* harness writing bytecode. It
does not stop a guard importing a module whose `.pyc` something else wrote earlier, and
`stage_tree`'s unfiltered `copytree` makes that *something else* the developer's or runner's own
repo, on every single run: 89 files, 55 of them for mutation targets, delivered with mtimes
preserved so they validate. Reproduced at `26661d75` with the fix in force (V8).

Secondary, and **refuted**: the harness's own restore cannot revive a staged cache, because
`run_mutations` restores content with `write_text` and the new mtime invalidates the entry. The
in-process `importlib` loaders (14 scripts using `spec_from_file_location`) respect
`sys.dont_write_bytecode`, so they are covered by the env too. The exposure is the **inbound** copy,
not the harness's own behaviour during a run.

---

## What I tried to refute and could not

- **The root cause and the fix.** Independently reproduced both directions from a cache-free staged
  tree: without the env line the after-control is **155/160 with five fails**, with it **160/160**
  (V7). The five case names match round 1's CI log. This is the strongest thing in the fold and I
  attacked it first.
- **The write-side completeness.** One spawn point, env inherited by children, zero `.pyc` across
  171 suite runs, and a control pair proving the observation is not ambient (V9, V12).
- **Every declared number.** 1,195 entries · sum 1,195 · 94 for `check-plan-code.py` · 0 problems ·
  **0 orphaned, 0 ambiguous** anchors over all 1,195 · 0 duplicate ids · self-test **160/160** ·
  `check-fixture-variation` rc=0. All re-derived (V1, V3, V4, V13).
- **Shard 6 of 8**, run end to end: `149 mutation(s), 149 killed, 149 attributed to the case each
  names, 0 survivor(s)` (V2).
- **The partition**, again, over the new 1,195: exact union and zero duplicates at
  N = 1, 2, 3, 7, 8, 16 (V5).
- **The deleted `.claude/` restore.** Three independent attempts to make it matter, including
  constructing the residue through the shipped mutation that produces it, then running every suite
  in the population against it: **0 reds** (V10, V11). I wanted this to be the round's finding and
  it is not.
- **The CI claim.** All 8 shards pass and `mutation-sweep-complete` passes at headSha `26661d75`;
  `verify`'s only failure is `check-review-recorded` asking for this document (V15, V16).
- **An attribution hole in the new entries.** Each of the four dies via the case its `expect` names,
  in a tree whose control is 160/160 (V6).
- **`check-banner-armed.py` writing `.claude/banner-warnings.log` in the staged tree** — round 1's
  own H1 hypothesis. `WARN_LOG` is redirected to a fixture for the block that writes it; nothing
  lands in `.claude/` (V10).

---

## Q4(a)

| # | Severity | Aim: deliverable or instrument | Caused by the fold itself? |
|---|---|---|---|
| H1 | High | **Instrument** — the harness's own correctness, and the suite's inability to falsify its new claim | **Yes, half.** The `__pycache__` read route is pre-existing; what is new is a fix that closes only the write half, a comment asserting *"no window"*, and a case that asserts the mechanism instead of the property it states |
| M1 | Medium | **Instrument** — the single bypass path of `child_env` | **No, surfaced by it.** `SUBPROCESS_ENV_KEYS` predates this fold; the fold is what made a dropped `PYTHON*` variable matter |
| M2 | Medium | **Instrument** — the record a future N-retune reads | **Yes.** Both the stale `run_mutations` pointer and the H1-as-H2 attribution were written in `26661d75`, and the second is contradicted by that commit's own message |
| L1 | Low | Instrument — what the round record says changed | **Yes** |
| L2 | Low | Instrument — two manifest entries read as independent and are nested | **Yes** (both entries are new) |

---

## Verdict

### NOT CONVERGED

Round 1's two Highs are **both resolved, and resolved correctly**. H1's root cause was traced to
file evidence rather than guessed, the two wrong attempts were deleted rather than layered, and I
reproduced the fix's effect in both directions from a clean tree — which is a better outcome than
most folds in this repository's record. Round 1's M1, M2, L1–L4 are out of this round's scope and I
did not re-open them.

It is not converged for one reason and one only: **the fix is half of the mechanism and the code
says it is all of it.** `PYTHONDONTWRITEBYTECODE=1` governs writing; `stage_tree` copies in 89
cache files, 55 of them for mutation targets, that it never validates; and I reproduced H1's exact
symptom — 155/160, the same five cases — at `26661d75` with the fix in force. The suite cannot see
the gap because its new case asserts two dictionary lookups under a sentence that states a property.
Given the subject is the instrument every other guard's evidence rests on, a verdict of converged
here would be this repository's own `a check result is not the claim`, applied to the check that
checks the checks.

M2 is a prose repair in the same commit and should ride with it. M1 is one tuple member. L1 and L2
are records, not code.

⛔ **And the Codex-specific pass for round 2 has not run** — see the CODEX GAP note above. It is
owed before merge, and round 1 is the measured reason to care: the Codex half found a defect this
half did not, on this branch.

**Document:**
`/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/reviews/claude/shard-mutation-sweep-r2-claude.md`
