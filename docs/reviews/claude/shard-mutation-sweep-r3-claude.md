# Round 3 — Claude adversarial half · `shard-mutation-sweep` (PR #366)

**Subject:** `git diff 77316edc..fcc46c01` — the fold of round 2's Codex Medium
(`SUBPROCESS_ENV_KEYS` dropped `PYTHONDONTWRITEBYTECODE`).
**Mandate:** refute. Run at `fcc46c01`, branch `shard-mutation-sweep`.
`docs/explainers/questions.md` was locally modified throughout and was ignored, never staged.
No tracked file was modified; every mutation experiment ran in a `copytree` under the scratchpad
with `$HOME` redirected.

---

## Verification

### Re-derived, in the live tree

```text
$ python3 scripts/check-rc-contract.py --self-test
rc contract OK — every defined code is handled or declared, and no arm is dead. …
56/56 self-test cases passed                                             rc=0

$ python3 scripts/check-surface-recall.py --self-test
surface-recall OK — every declared code renders exactly its approved sentence
59/59 self-test cases passed                                             rc=0

$ python3 scripts/check-plan-code.py --self-test
161/161 passed                                                           rc=0
```

```text
$ python3 scripts/check-plan-code.py --mutate . --shard 3/8
OK — delivered scripts mutated: 51 file(s), 150 mutation(s), 150 killed,
150 attributed to the case each names, 0 survivor(s) — measured over shard 3 of 8 (round-robin)
```

### ⚠ Shard 3 does not contain either new entry — so I ran the two that do

The brief's prescribed shard is blind to the fold. `shard_slice` is `muts[index - 1::total]`
(`check-plan-code.py:1587`), and loading the manifests from the repo root gives each new entry a
global position:

```text
scripts/check-rc-contract.py:      global 0-based index 620 -> shard 5 of 8
scripts/check-surface-recall.py:   global 0-based index 807 -> shard 8 of 8
total mutations loaded: 1198   problems: []    declared sum: 1198
```

Round 2's Codex half ran shard **6**, so neither half of round 2 nor the brief's shard 3 measured
the fold's own entries. I ran both:

```text
##### SHARD 5
OK — delivered scripts mutated: 53 file(s), 150 mutation(s), 150 killed,
150 attributed to the case each names, 0 survivor(s) — measured over shard 5 of 8 (round-robin)
RC5=0
##### SHARD 8
OK — delivered scripts mutated: 49 file(s), 149 mutation(s), 149 killed,
149 attributed to the case each names, 0 survivor(s) — measured over shard 8 of 8 (round-robin)
RC8=0
```

### Gates re-derived (the coordinator's list, re-run rather than reconfirmed from its report)

```text
check-docs                 rc=0 | Documentation integrity OK
check-anchors              rc=0 | anchors: 13 registered, all claimed; … floor 22 held
check-test-counts          rc=0 | roadmap test counts match the suite: 2,892 unit / 278 suites
check-selftest-counts      rc=0 | 50 script(s) declare a count, every one verified by running it
check-dashboard-entry      rc=0 | ok — an entry block was added
check-ratchet-contract     rc=0 | ratchet contract OK
check-features             rc=0 | 26 nodes (24 built, 2 declared absent); …
check-review-rounds        rc=0 | 370 parsed, 18 pre-existing exemptions, 0 silent gaps
check-guard-coverage       rc=0 | 37/37 self-test cases passed
```

Anchor resolution, computed independently over the delivered tree (every `find` string of every
entry of every manifest, counted in its target file):

```text
anchors: 1206 | not-exactly-once: 0 | duplicate (file,find) pairs: 2
```

The two duplicates are pre-existing, outside the delta, and are the **declared** limit of the
loader's refusal: dedup is exact tuple equality over an entry's whole anchor tuple
(`load_manifests`, `seen_anchors`), and `check-plan-code.py` already records that as r12 Low
("the message claims more than the test delivers"). Not a finding.

### CI, at the fold commit

`gh pr checks 366` with `headRefOid = fcc46c01`: `mutation-sweep (1)`–`(8)`, `mutation-sweep-complete`,
`schema-gates`, `verify` all **pass**. So all eight shards — including 5 and 8 — are green in CI on
Linux at this commit, not only at `77316edc`.

### Could not run / NOT MEASURED

- The unsharded `--mutate .`, per the brief's instruction. The dashboard entry's claim that it
  "**was** run tonight, over the whole manifest" is **NOT MEASURED** by me; no artefact of that run
  exists in the delta.
- An interpreter built with bytecode writing disabled, and a `sitecustomize.py` setting
  `sys.dont_write_bytecode` — I could not construct either without touching the machine's site
  directories. The ambient-pass bound in Q1 below is therefore over six routes, not all routes.
- `check-vocabulary-collisions.py` / `check-storage-independence.py` entry points (need the
  container Postgres). Not in the delta's path; **NOT MEASURED**, not a pass.

---

## Findings

### Medium — The property is asserted over the CONSTANT, and nothing asserts that the spawn which actually runs a hook uses that constant: decoupling the call site and dropping the key leaves both suites entirely green

**Finding.** The new case's subject is `SUBPROCESS_ENV_KEYS` itself —
`_scrubbed_spawn_writes_cache(SUBPROCESS_ENV_KEYS)`. The code whose behaviour matters is the scrub
at `check-rc-contract.py:295` and `check-surface-recall.py:168`, and nothing in either suite
asserts that those two expressions read the constant. Replacing the reference with an inline literal
that drops the bytecode key — the *exact* regression round 8 H1 was filed for, since this constant
exists only because the scrub had been hand-copied — survives both suites with no case failing.

**Exhibiting input, measured in a staged copy, each with `$HOME` redirected and
`PYTHONDONTWRITEBYTECODE=1` as `child_env` sets it:**

```text
scripts/check-rc-contract.py
  '_env = {k: v for k, v in os.environ.items() if k in SUBPROCESS_ENV_KEYS}'
→ '_env = {k: v for k, v in os.environ.items() if k in ("PATH", "HOME", "TMPDIR", "LANG")}'
   rc=0   fails: NONE  <-- MUTATION SURVIVED   ['56/56 self-test cases passed']

scripts/check-surface-recall.py
  'env = ({k: v for k, v in os.environ.items() if k in SUBPROCESS_ENV_KEYS} if scrub'
→ 'env = ({k: v for k, v in os.environ.items() if k in ("PATH","HOME","TMPDIR","LANG")} if scrub'
   rc=0   fails: NONE  <-- MUTATION SURVIVED   ['59/59 self-test cases passed']
```

Both the agreement case (round 8 H1) and the new property case read the constant, so moving the key
out of the call site's reach is invisible to both. The manifests cannot see it either:
`scripts/mutations/check-rc-contract.json` has **zero** entries anchored on its `_env` line (16
entries scanned, none touching `_env` or `os.environ`); `check-surface-recall.json` has exactly one
(entry 13, round 7 L1), and it covers only the *wholesale-inheritance* direction
(`→ dict(os.environ)`), not a narrower literal.

This is the fold diverging from the fix Codex r2 asked for, in the one direction that leaves the gap.
Codex's proposed fix was "a property-shaped case that **runs a scrubbed hook importing a helper
module** and asserts no `__pycache__` appears" — i.e. driven through the real observer. The fold
asserted the property over the constant with a synthetic `sys.executable` spawn instead. The
commit message, both file comments and the dashboard all say the property "is asserted directly
now"; what is asserted directly is a property *of the constant*.

Nothing is broken today: both constants carry the key, and the shipped hooks are the ones round 2
already found not to bite.

**Proposed fix — UNVERIFIED.** Drive the case through `observe()` (rc-contract) and `_render_once`
(surface-recall) with a stub hook that imports a module from the tree, asserting no `__pycache__`
appears — and add a manifest entry anchored on each `_env`/`env =` line that replaces the constant
reference with a literal. Either half alone leaves the other open.

---

### Low — The new `check-surface-recall` entry's kill is confounded: the pre-existing round-8 agreement case fails too, so that entry does not exercise the property case

**Finding.** The coordinator's claim "severing the key in either file goes red **via the case that
file's entry names**" is true, and in `check-surface-recall.py` it is not the whole picture. Running
each manifest entry's edit in a staged copy and reading the `[FAIL]` lines:

```text
check-rc-contract.json[15]  rc=1   EXPECT: a spawn scrubbed by THIS guard's allowlist writes no bytecode cache — r2 Medium
    [FAIL] a spawn scrubbed by THIS guard's allowlist writes no bytecode cache — r2 Medium
    55/56 self-test cases passed                      <- sole killer, clean attribution

check-surface-recall.json[19] rc=1  EXPECT: a spawn scrubbed by THIS guard's allowlist writes no bytecode cache — r2 Medium
    [FAIL] the subprocess env allowlist is the SAME in both guards — round 8 H1
    [FAIL] a spawn scrubbed by THIS guard's allowlist writes no bytecode cache — r2 Medium
    57/59 self-test cases passed                      <- round-8 case kills it too
```

Removing the key from one file diverges it from its sibling, so the agreement case fires as well.
Only `check-rc-contract`'s entry independently demonstrates that the property case has power.
Partly mitigated already: deleting the property case would leave the mutation unattributed and the
harness red, so its existence is pinned even where its necessity is not.

**Proposed fix — UNVERIFIED.** Have the surface-recall entry sever the key in *both* files (the
agreement case then stays green and the property case is the sole killer), or accept the confound
explicitly in the entry's `name`.

---

### Low — Three new citations point at a comment that restates the claim, not at the code that produces it

**Finding.** The delta adds three citations of `check-plan-code.py:808` for "`run_suite` runs only
the mutated file's suite" — in `check-rc-contract.py`, in `check-surface-recall.py`, and in
`EXPECTED_MUTATIONS`'s annotation (`git diff | grep -c ':808'` → 3; a fourth copy is in the
dashboard entry). Line 808 is prose inside an `EXPECTED_MUTATIONS` comment block:

```text
808:    # the same reason #71 held its sum at 73. `run_suite(d, fname)` runs only the mutated
809:    # file's suite, so the killing cases moved too.
```

The claim is **true**; its producer is `run_suite_parts` at `:539`, whose body is
`subprocess.run([sys.executable, name, "--self-test"], cwd=d, …, env=child_env(d))` — one file,
named by argument — with `run_suite` at `:556` and the only mutate-path caller at `:1879`. The
commit whose subject is "assert the property, not the agreement" cites an assertion three times as
evidence for a code property.

**Proposed fix — UNVERIFIED.** Cite `run_suite_parts` by symbol (the repo's own rule: cite the
symbol, not the line); a line number in a 4,400-line file that is 100% comment at that offset is
also the first thing a refactor invalidates.

---

### Low — The anchor split makes `check-surface-recall`'s constant reflow-bait, and the site says nothing about it

**Finding.** `SUBPROCESS_ENV_KEYS` is now split across three lines in `check-surface-recall.py:56-59`
while its sibling keeps it on one line at `check-rc-contract.py:339`. The split exists only so the
two manifest entries own distinct anchors — and both of surface-recall's allowlist entries now bind
to the line breaks:

| entry | anchor |
|---|---|
| 18 (round 8 H1, retargeted) | `    "PATH", "HOME", "TMPDIR", "LANG",` |
| 19 (new) | `    "PYTHONDONTWRITEBYTECODE",` |

Measured: the reflowed one-liner is **83 characters**, which is exactly the length of
`check-rc-contract.py:339` as shipped — so unifying the two copies is formatting-legal, and
"make the two hand-copies look the same" is the obvious thing a reader of a file whose comment is
about hand-copy drift will do. Nothing at the site says the line breaks are load-bearing.

It fails **closed** (the harness reports `anchor NOT FOUND` → NOT MEASURED, which is how the fold
found the orphan it retargeted), hence Low rather than higher.

**Proposed fix — UNVERIFIED.** One line of comment at the constant saying two mutation entries
anchor on these breaks; or give the two entries distinct anchors that survive reflow (e.g. anchor
entry 19 on the key inside a one-line tuple and entry 18 on `"LANG")` ).

---

### Low — The copied comment says "the scrub above" in the file where the scrub is below

**Finding.** The identical paragraph is pasted into both guards: *"The scrub above is an
ALLOW-LIST, so it dropped the one variable…"*. In `check-rc-contract.py` it is correct — the scrub
is at `:295`, the comment at `:332`. In `check-surface-recall.py` the comment is at `:49-55` and
that file's scrub is at `:168`, **below** it. ⚠ A charitable reading is "the scrub [discussed]
above", since the paragraph directly above does mention a scrub; stated so the finding is not
overclaimed. Either way it is the hand-copy-drift class the paragraph is itself about, introduced by
the paste.

**Proposed fix — UNVERIFIED.** Say "this file's scrub" in both copies, which is true in both.

---

### Low — The dashboard entry quotes five commits' cumulative totals under a one-commit heading, and three of the day's defects reach the human nowhere

**Finding.** The entry is headed *"Round 2 of PR #366 (Codex half), folded. One Medium."* and all its
prose, tech and non-tech, is about the allow-list. Its `counts` row reads
`self-test 155 → 161` and `declared sum 1193 → 1198`. Measured per commit:

```text
0af517ce (branch base)  declared_sum=1178
eee31527                declared_sum=1193   <- the PREVIOUS entry's closing figure
29fd2653                declared_sum=1196
26661d75                declared_sum=1195
b1d059e9                declared_sum=1196
77316edc                declared_sum=1196
fcc46c01                declared_sum=1198   <- this fold
```

So `1193 → 1198` and `155 → 161` are correct as a *span since the last entry* — the previous entry
closed at "self-test 131 → **155**; declared sum 1178 → **1193**" — but this fold accounts for
`1196 → 1198` and for **none** of the self-test move. Both dashboard entries are dated `2026-10-05`,
and the four commits between them (`29fd2653` the `.claude/` restore, `26661d75` the mutant-`.pyc`
root cause, `b1d059e9` the staged-tree read half, `77316edc` the `expect`-rename orphan) have no
narrative in either entry. The mutant-`.pyc` commit is the root cause of the whole
nondeterministic-shard investigation, and a person who was away learns of it from no entry.
`check-dashboard-entry.py` is green because *an* entry was added — it cannot see this.

**Proposed fix — UNVERIFIED.** Either scope the counts row to this fold (`1196 → 1198`, self-test
unchanged at 161) or widen the entry's prose to the four commits whose numbers it is quoting.
The second is the one the dashboard exists for.

---

## Answers to the five questions

### 1. Is the property case falsifiable for the right reason, or can it pass for an ambient reason?

**Tried to refute; could not, over six constructed environments.** The probe builds its source
environment as `{**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}` and then filters by the live
constant, so the verdict does not depend on the caller's environment (`#56`'s shape avoided). I
severed the key in a staged copy and ran the suite six ways, checking each time whether the named
case still appears among the `[FAIL]` lines:

```text
baseline (as harness runs it)                 rc=1 ['55/56 self-test cases passed'] -> MUTATION CAUGHT
parent -B  (sys.flags.dont_write_bytecode)    rc=1 ['55/56 self-test cases passed'] -> MUTATION CAUGHT
parent PYTHONPYCACHEPREFIX set                rc=1 ['55/56 self-test cases passed'] -> MUTATION CAUGHT
parent has NO PYTHONDONTWRITEBYTECODE         rc=1 ['55/56 self-test cases passed'] -> MUTATION CAUGHT
parent -X pycache_prefix                      rc=1 ['55/56 self-test cases passed'] -> MUTATION CAUGHT
TMPDIR read-only                              rc=1 ['55/56 self-test cases passed'] -> MUTATION CAUGHT
```

Why each fails to confound: `-B` and `-X pycache_prefix` are parent-process flags and are not
propagated to a child spawned with an explicit `env`; `PYTHONPYCACHEPREFIX` is not in the allow-list
and is therefore scrubbed out of the child before it could redirect anything; a read-only `TMPDIR`
is neutralised by `tempfile`'s own writability probe, which falls back. **Bound: 0 false passes in
6 adjacent environments — this bounds nothing about an interpreter built with bytecode writing
disabled or a `sitecustomize` setting `sys.dont_write_bytecode`, neither of which I could construct;
those are NOT MEASURED.** The second would defeat any formulation of this case, including Codex's.

One further ambient hazard I expected and could not substantiate: the case is the first thing in
either suite to spawn `sys.executable` under a *scrubbed* environment (the pre-existing scrubbed
spawns run `bash`). A relocatable CI interpreter needing `PYTHONHOME`/`LD_LIBRARY_PATH` would die,
`check=True` would raise, and both suites would crash. Refuted by measurement: `verify` and all
eight `mutation-sweep` shards are green in CI **at `fcc46c01`**, on Linux.

The real falsifiability gap is not ambient — it is the subject. See the Medium.

### 2. Is the claimed completeness real?

**For allow-list and literal environments, yes — I could not find another.** Every `env=` in
`scripts/` and `.claude/hooks/`, judged:

| site | shape | verdict |
|---|---|---|
| `check-plan-code.py:549` | `env=child_env(d)` | sets the key — the source of truth |
| `check-selftest-counts.py:316` | env from `child_env(Path(td))`, borrowed from `check-plan-code` | inherits ✓ |
| `check-rc-contract.py:295` | allow-list filter | fixed by the fold ✓ |
| `check-surface-recall.py:168` | allow-list filter | fixed by the fold ✓ |
| `observer_log.py:381` | `dict(os.environ, LC_ALL=…, PYTHONUTF8="0", …)` | pass-through, inherits ✓. ⚠ it *does* spawn python and `import observer_log`, so this is the nearest remaining candidate — it only inherits because it never filters |
| `page_chrome.py:375` | `{**os.environ, GIT_*}` | git, inherits ✓ |
| `check-selection-card.py:485` | `dict(os.environ)` + PATH prefix | bash, inherits ✓ |
| `codex-review.py:743/806/2157` | `dict(os.environ …)` minus git redirect vars / plus one var | inherits ✓ |
| `check-anon-exposure.py:648`, `m4_catalog.py:521` | `psql_env` = `{**os.environ, PGU}` | psql, inherits ✓ |

`grep` for the filter shape (`os.environ.items()`) returns exactly the two sites the fold fixed, and
nothing else in the repo. I also looked for non-env write routes — `py_compile`, `compileall`,
`cache_from_source`, an assignment to `sys.dont_write_bytecode`, a hand-written `.pyc` — and found
none outside `check-plan-code.py`'s own fixtures and the two new probes.

So the allow-list half of the claim is complete. What is **not** complete is its enforcement: see
the Medium — the constants are right and nothing holds the call sites to them.

### 3. Attribution

**Verified by running, not by reading.** Each entry's edit applied in a fresh staged copy, then
that file's `--self-test` run and the `[FAIL]` lines read (full output in the Low above):

- `check-rc-contract.json[15]` (new) → `55/56`, one `[FAIL]`, the named case. Clean.
- `check-surface-recall.json[19]` (new) → `57/59`, two `[FAIL]`, the named case among them.
  Attributed, but confounded by the round-8 case — filed as a Low.
- `check-surface-recall.json[18]` (the **retargeted round-8 entry**) → `58/59`, one `[FAIL]`:
  `the subprocess env allowlist is the SAME in both guards — round 8 H1`. **Its original subject is
  intact**: the new anchor still drops `LANG` from this file only, so it still produces a
  *divergence* from the sibling and still dies by the divergence case. It does not accidentally
  measure the bytecode property, which is what a careless retarget would have done.
- `check-surface-recall.json[13]` (round 7 L1, adjacent and untouched) → `57/59`, still dies via
  its own named case. The fold did not disturb it.

Independently, the harness's own verdict on both new entries: shards 5 and 8, locally
`150/150` and `149/149` killed and attributed, 0 survivors; and green in CI at `fcc46c01`.

### 4. The anchor split

**No reader outside the two manifests.** `SUBPROCESS_ENV_KEYS` appears, repo-wide, only in the two
guards, the two manifests, and review/dashboard prose. `check-producer-enumeration.py`'s subject is
a spec document plus `.ts/.tsx` citations; `check-guard-coverage.py`'s `GUARDS` is the *database*
guard inventory, not scripts; no guard in `scripts/` regexes Python constant assignments. `check-docs`,
`check-features`, `check-anchors`, `check-selftest-counts` are all rc=0 after the reformat, re-run above.

The one reader that *is* sensitive is the manifest itself, and that is the Low: two entries now bind
to the line breaks, the reflowed form is 83 characters (identical to the sibling's shipped one-liner),
and nothing at the site says so.

### 5. The two new backlog rows (#228, #229)

**I tried to refute both by reading and running the code. Both are correct; I could not refute
either.** This was the most likely place to find a wrong claim and it is not there.

**#228** — `codex-frontier-model.py:66-70` filters on `m.get("visibility") == "list"` **and**
`m.get("supported_in_api")`. Replicated against the live cache (mtime `Oct 5 20:56`):

```text
model count: 2
{'slug': 'gpt-5.5',           'visibility': 'hide', 'supported_in_api': True, 'priority': 13}
{'slug': 'codex-auto-review', 'visibility': 'hide', 'supported_in_api': True, 'priority': 43}

$ python3 scripts/codex-frontier-model.py
error: no visible, API-supported model with a priority found in cache
rc=1
```

And the counter-evidence the row relies on is in this branch's own artefacts:
`docs/reviews/verdicts/shard-mutation-sweep-r2-codex.verdict.json` records
`"model": "gpt-5.5"`, `"gate_ran": true`, `"attempts": ["  gpt-5.5: ok — 7058 chars"]`. A slug the
selector calls unavailable produced a full review. The row's severity reasoning — that
"unavailable" is exactly the documented trigger for a legitimate `REVIEW GAP:` — is the part worth
keeping; it is a gate that downgrades itself and reports success.

**#229** — the two populations are as stated, and I read them rather than the row:
`discover_guards` is `sorted(p for p in script_paths if GUARD_PATH_RE.fullmatch(p))` with
`GUARD_PATH_RE = re.compile(r"scripts/check-[\w.-]+\.py")` (`:116`, `:172`) — a filename rule;
`discover_self_tested_nonguards` is `p not in guards and SELF_TEST_RE.search(texts.get(p, ""))`
(`:441`) — opt-in by self-testedness. Measured against `scripts/codex-frontier-model.py`:

```text
SELF_TEST_RE hits: []            (SELF_TEST_RE = r"--self.test", IGNORECASE)
GUARD_PATH_RE match: False
scripts/mutations/ entries: none
```

It is in neither population, nor in `WIDENED_MANIFEST_DEBT`, and it is imported by
`scripts/codex-review.py:102` (`_frontier = import_module("codex-frontier-model");
resolve_candidates = _frontier.resolve_candidates`) — the adversarial-review gate's entry point.
`check-ratchet-contract.py` is rc=0 over it. I also checked whether some *other* guard sees it:
the only files in the repo that name it are itself and `codex-review.py`. The row's framing — a
bootstrap hole, not a filename hole, and R4's own recorded hole one layer in (`:356`) — holds, and
its preference for (a) import-graph reachability over (b) hand-pinning the instance is the right
way round for this repo.

---

## What I tried to refute and could not

- **All six pre-measured claims the brief listed are true**, each re-derived rather than read:
  `56/56`, `59/59`, `161/161`; severing goes red via the named case in both files; 1,206 anchors
  resolve exactly once with 0 unresolved; `EXPECTED_MUTATIONS` 15→16 and 19→20 with the declared
  sum 1198 = `sum(EXPECTED_MUTATIONS.values())` = the 1,198 entries actually loaded; and all the
  listed gates rc=0.
- **The ambient-pass hypothesis**, over six adjacent environments — the case holds (Q1).
- **The completeness claim for allow-list environments** — the two fixed sites are the only filters
  in the repo, and there is no non-env bytecode-write route (Q2).
- **The retargeted round-8 entry still measuring its original subject** — it does, by one case (Q3).
- **Both backlog rows** — read the code, ran the selector, replicated the cache; neither is wrong (Q5).
- **A CI-only crash from the new scrubbed `sys.executable` spawn** — refuted: all 11 reporting
  checks are green at `fcc46c01`, not at the parent commit.
- **The residue hypothesis**: the new probes write their `__pycache__` inside a
  `TemporaryDirectory`, and `git status` after running all three suites in the live tree showed only
  the pre-existing `docs/explainers/questions.md`. No repo residue, which matters given this
  branch's own history.

---

## Summary

| # | Severity | Aims at | Caused by the fold itself? |
|---|---|---|---|
| 1 | **Medium** | **Instrument** — the property is over the constant; the call sites can drop the key with both suites green | **Partly.** The call sites predate the fold; the fold introduced the completeness claim and chose the constant over the real observer path that Codex r2's fix named |
| 2 | Low | **Instrument** — the surface-recall entry's kill is confounded by the round-8 agreement case | **Yes.** Introduced with the entry |
| 3 | Low | **Instrument** — three new `:808` citations point at prose, not at `run_suite_parts:539` | **Yes.** All three added by the fold |
| 4 | Low | **Instrument** — the split constant is reflow-bait; two anchors bind to the line breaks, unwarned | **Yes.** The split is the fold's |
| 5 | Low | Instrument (comment) — "the scrub above" is false in the file where the scrub is below | **Yes.** Introduced by the paste |
| 6 | Low | **Deliverable (the human's status surface)** — five commits' totals under a one-commit heading; the mutant-`.pyc` root cause reaches no entry | **Yes.** The entry is the fold's |

---

## Verdict

**NOT CONVERGED**

The shipped code is correct, every gate and all eight CI shards are green at this commit, and both
new backlog rows survived a direct attempt to refute them. The reason this is not converged is the
Medium, and it is the same shape one layer in from the defect the fold exists to close: round 2
found a case that asserted *agreement* where the property was what mattered; this fold replaced it
with a case that asserts the property *of the constant*, where the spawn is what matters — and a
decoupling mutation, the regression that already happened once to this exact constant, survives both
suites at 56/56 and 59/59. That is the fold's own completeness claim being weaker than its wording,
in the measurement instrument, and it is small to fix.
