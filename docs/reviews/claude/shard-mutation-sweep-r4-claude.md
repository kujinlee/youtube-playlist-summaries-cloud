# Round 4 — Claude adversarial half · `shard-mutation-sweep` (PR #366) at `fa7a6d73`

Subject: `git diff 8c1a207a..fa7a6d73` — the conjunction fold on `_production_spawn_writes_cache()`,
defined in both `scripts/check-rc-contract.py` and `scripts/check-surface-recall.py`.

Mandate: **REFUTE**. This component has thrashed three rounds on one probe, so the headline
deliverable of this half is the design judgement in §3, not a fourth instance of the class.

⚠ **It is a fourth instance anyway, and that is the argument of §3.** The fold asserted *one* of the
probe's two unstated preconditions. The other is still unasserted, and I reproduced it: under a
`python3` that does not write bytecode, **both** of the mutation entries that exist to carry r3's
finding survive, with `--self-test` reporting 56/56 and 59/59.

---

## 1. Verification

Working directory `/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud`, `HEAD` =
`fa7a6d7363497b5812f382f977194d3a47b50217`, tree clean apart from `docs/explainers/questions.md`
(ignored per instruction). **No tracked file was modified**; every mutation below was applied to a
`copytree` copy under `/Users/kujinlee/.claude-tmp/claude-501/`.

### 1.1 The four commands I was required to execute

```text
$ python3 scripts/check-rc-contract.py --self-test
rc contract: 6 code(s) defined, 4 handled by an arm, 2 declared unhandled
rc contract OK — every defined code is handled or declared, and no arm is dead. What the READER sees is check-surface-recall.py's rule, not this one
56/56 self-test cases passed

$ python3 scripts/check-surface-recall.py --self-test
surface-recall: 6 declared sentence(s), run against the REAL hook in the REAL repo
surface-recall OK — every declared code renders exactly its approved sentence
59/59 self-test cases passed

$ python3 scripts/check-plan-code.py --self-test
161/161 passed

$ python3 scripts/check-plan-code.py --mutate . --shard 5/8
OK — delivered scripts mutated: 54 file(s), 150 mutation(s), 150 killed, 150 attributed to the
case each names, 0 survivor(s) — measured over shard 5 of 8 (round-robin)
```

### 1.2 Coordinator claims I re-measured independently

| Claim | Result |
|---|---|
| `check-rc-contract --self-test` 56/56 | ✅ reproduced |
| `check-surface-recall --self-test` 59/59 | ✅ reproduced |
| `check-plan-code --self-test` 161/161 | ✅ reproduced |
| shard 5/8 — 0 survivors | ✅ reproduced (150 mutations, 150 killed, 150 attributed) |
| all four falsifiers red **via the named case** | ✅ reproduced, all four, see §1.3 |
| 1,208 anchors resolve exactly once, 0 unresolved | ✅ **independently recomputed: 1208 edits, 0 multi-match, 0 not-found** — using the harness's own rule (`check-plan-code.py:1860`, `src.count(find) > 1` over the sequentially-accumulated text), not a re-run of the harness |
| `check-review-rounds` rc=0 | ✅ rc=0 — "371 parsed, 18 pre-existing exemptions, 0 silent gaps; 218 codex-review verdict(s) read, none contradicted" |
| `check-docs` rc=0 | ✅ rc=0 |
| `check-selftest-counts` rc=0 | ✅ rc=0 — "50 script(s) declare a count, every one verified by running it" |
| `check-vocabulary-collisions` rc=0 | ✅ rc=0 |
| `check-ratchet-contract` rc=0 | ✅ rc=0, 43 guards discovered |
| CI green at `8c1a207a` | **NOT MEASURED** — I did not query GitHub; no finding either way |

**Nothing the coordinator reported is false.** Every number above held.

### 1.3 The staged control, and the four falsifiers

Staged a harness-shaped tree (`HARNESS_TREE`'s six entries, `__pycache__` excluded, exactly
`check-plan-code.stage_tree`'s rule) and proved the control green there first:

```text
[E0 control] check-rc-contract.py:   rc=0  56/56
[E0 control] check-surface-recall.py: rc=0  59/59
```

Then, each in a fresh copy of that control:

```text
[E1 key removed (rc)]                 rc=1  55/56  FAIL> a spawn scrubbed by THIS guard's allowlist writes no bytecode cache — r2 Medium
[E2 key removed (sr)]                 rc=1  57/59  FAIL> the subprocess env allowlist is the SAME in both guards — round 8 H1
                                                   FAIL> a spawn scrubbed by THIS guard's allowlist writes no bytecode cache — r2 Medium
[E3 import broken only (rc)]          rc=1  55/56  FAIL> a spawn scrubbed … — r2 Medium
[E4 import broken only (sr)]          rc=1  58/59  FAIL> a spawn scrubbed … — r2 Medium
[E5 key removed + import broken (rc)] rc=1  55/56  FAIL> a spawn scrubbed … — r2 Medium
[E6 key removed + import broken (sr)] rc=1  57/59  FAIL> agreement + a spawn scrubbed … — r2 Medium
[m16 rc call-site inline]             rc=1  55/56  FAIL> a spawn scrubbed … — r2 Medium
[m20 sr call-site inline]             rc=1  58/59  FAIL> a spawn scrubbed … — r2 Medium
```

E5/E6 are r3-codex's exact false pass and they are now red. The fold **does** fix the finding it
claims to fix, and the three-row table in its own comment
(`[] → RED`, `["ran","<pyc>"] → RED`, `["ran"] → GREEN`) is accurate as far as it goes.

### 1.4 The fold's historical "Measured:" claim, checked rather than believed

The new comment asserts: *"Measured: with the key REMOVED and the probe importing
`_missing_pycprobe`, both suites passed."* I reproduced that against the **pre-fold** files
(`git show 8c1a207a:` for both scripts, dropped into the same staged tree, control green at 56/56
and 59/59 first):

```text
check-rc-contract.py   rc=0  ['56/56 self-test cases passed']
check-surface-recall.py rc=0  ['59/59 self-test cases passed']
```

The claim is a real measurement, not an inference stated as one.

### 1.5 r3-codex's Low (leaked temp dirs) — fixed

```text
TMPDIR entries before=33604 after=33604  (delta=0)   # both suites run back-to-back
.claude/hooks/_selftest-*                            # (no residue)
```
Residue from before the fold survives on this machine (34 directories still carrying
`_pycprobe.py`), which corroborates that the Low was real. New runs leak nothing. Closed.

### 1.6 What I could not run

* **CI state at `8c1a207a`** — NOT MEASURED (no GitHub query made).
* **Unsharded `--mutate .`** — not run, per instruction. Shard 8 — **NOT MEASURED**; I applied the
  relevant entries directly in staged copies instead (§1.3). `check-plan-code.json` entry 93 (the
  sibling instrument discussed in §3) is **NOT MEASURED** by me — it was not in shard 5.
* **A read-only or `noexec` probe directory** — NOT MEASURED. I could not inject one: the directory
  is created by `tempfile.TemporaryDirectory()` *inside* the probe, after which the probe's own
  `write_text` is the first write. Reasoned only (and so marked): a read-only parent would make
  `TemporaryDirectory()` itself raise, which is loud; an unwritable probe dir would make
  `open(…,'w')` raise inside the import, yielding `[]`, which is now red.
* **`codex exec -m gpt-5.5` actually completing a prompt** (half of backlog #228's falsifier) —
  NOT RUN. Corroborated from repo artefacts instead; see §5.

---

## 2. Findings

### 2.1 MEDIUM — the probe asserts the absence of a cache without asserting its own second precondition: that the spawn *would* write one. Both call-site mutation entries then survive.

**Finding.** The conjunction closes r3-codex's precondition (*did the import run?*) and leaves the
other one open (*would bytecode be written here at all?*). The probe observes
`(witness exists) ∧ (no .pyc in _probe/__pycache__)` and nothing establishes that a `.pyc` is the
counterfactual. So any mechanism that suppresses bytecode for an unrelated reason satisfies the case
**with the key absent** — and the suppression route need not be exotic, because it arrives through
`PATH`, which is itself one of the five allow-listed keys the probe is measuring.

**Concrete exhibiting input.** A `python3` earlier on `PATH` that execs the real interpreter with
`-B`:

```sh
#!/bin/sh
exec /usr/local/bin/python3 -B "$@"
```

Applied to fresh copies of the green control, with `PATH` prefixed by that shim's directory:

```text
# the allow-list loses the key (manifest entries rc#15 / sr#19)
[A rc] check-rc-contract.py:   rc=0  56/56 self-test cases passed        ← GREEN, key absent
[A sr] check-surface-recall.py: rc=1  58/59
    FAIL> the subprocess env allowlist is the SAME in both guards — round 8 H1
            ^ the ONLY failure. The bytecode case passed.

# the CALL SITE stops consulting the constant (manifest entries rc#16 / sr#20 — r3's own finding)
[m16+shim] check-rc-contract.py:   rc=0  56/56 self-test cases passed    ← MUTANT SURVIVES
[m20+shim] check-surface-recall.py: rc=0  59/59 self-test cases passed    ← MUTANT SURVIVES
```

Those last two lines are the finding. `check-rc-contract.json` entry 16 and
`check-surface-recall.json` entry 20 exist for exactly one purpose — to prove the production spawn
reads `SUBPROCESS_ENV_KEYS` rather than an inline hand-copy, which is round 8 H1's original defect
and r3-claude's finding. Under the shim both are **unkillable**, and in `check-surface-recall.py`
there is not even a sibling case to mask it: 59/59, clean green, call site inlined.

In the allow-list direction (A), note the asymmetry that makes this easy to miss: the rc half goes
green outright, and the surface half goes red **for an unrelated reason** — the round-8 H1 agreement
case, which fires because the two constants diverged. A reader seeing `57/59`/`58/59` would conclude
the property case is doing work it is not doing. r3-codex already flagged that entry 19 is
confounded by the agreement case; this is the same confound hiding a *different* defect.

**The fold's own three-row table is missing a fourth row:**

```
    key absent AND bytecode suppressed for any other reason -> ["ran"] ..... GREEN (unearned)
```

**Scope, stated so this is not read as bigger than it is.** On this machine and on a stock CI
runner, bytecode *is* written — E1–E4 prove it, so the green at `fa7a6d73` is earned *today*, and
the entries are killable *today*. What is missing is any assertion that keeps it that way:
nothing in either suite would notice the precondition evaporating. Partial backstop: if it did
evaporate, `--mutate .` would report 2 survivors and go red — loudly, but naming the wrong cause
("the call site no longer reads the constant is undetected" rather than "the probe's precondition
is gone"). `--self-test` — which is what CI's `verify` job and the documented developer invocation
run — goes silently green.

**This is the repo's own recorded class, and it is the class that has thrashed.** r2 asserted a
constant and the call site was unasserted. r3 asserted the spawn and the import was unasserted. r4
asserts the import and the counterfactual is unasserted. Each round found one more precondition of
the same negative observation. That is `a-case-can-pass-for-an-ambient-reason` (4× recorded) and
`proving-a-negative-by-interception-cannot-terminate` (five unearned passes recorded) in the same
probe — and "cannot terminate" is a statement about the instrument, not about the diligence of any
round. See §3.

**Proposed fix — UNVERIFIED.** Do not widen the probe a fourth time. Two options, in order of
preference, both developed in §3:

(a) Replace the observation with a **positive** one: extract the inline scrub into one named
   producer and assert the env dict it returns contains the key — which is *already how the sibling
   guard asserts this exact property*; or
(b) if an end-to-end witness is kept, make it **two-sided**: run the same spawn a second time with
   the key deliberately dropped and require a `.pyc` to appear. A missing `.pyc` there is the
   precondition failing, and must be **CANNOT RUN**, never a pass. This is the control-before-verdict
   discipline `check-plan-code.py --mutate` already applies to itself; the probe is the one place in
   this repo that accepts a green with no control.

### 2.2 MEDIUM — the fold multiplied the duplicated surface by six and left the justification for tolerating duplication unrevised.

**Finding.** `_production_spawn_writes_cache()` is now defined twice. Normalising both definitions
(from `def` to the following `case(`) and diffing them:

```text
rc lines: 31   sr lines: 32
--- rc
+++ sr
@@ -23 +23,2 @@
-                observe(_hook_src, 5, _PROBE)
+                with _fixture_hook(_hook_src) as _fx:
+                    _render_once(_fx, 5, "probe-detail", True)
```

**30 of 31 lines are a verbatim second copy** — docstring, witness construction, hook source,
`os.environ` set/restore, the `finally`, the return expression. The one differing statement is the
spawn call, which is the only thing that *should* differ.

`check-surface-recall.py:40-44` carries the standing justification:

> *"The scrub was hand-copied into `check-rc-contract.observe` with nothing comparing the two, so
> the fix for a DRIFT defect was itself a second copy. **A shared module would be heavier than the
> problem**; a case that REFUSES a divergence is the remedy this repo uses where one place is
> impractical."*

That cost-benefit was written when the duplicated surface was a **5-element tuple**. It is now a
5-element tuple **plus a 31-line function**, and the sentence was not revisited. This is the
recorded shape `a-costbenefit-finding-expires-when-the-denominator-moves`, and
`a-second-implementation-of-one-rule-drifts` (17× recorded) is what it buys. The fold also added no
case refusing a *divergence between the two probes* — the remedy the comment names for the tuple
was not extended to the much larger thing copied beside it.

Note also what the duplication costs the evidence: because the two probes are independent copies,
every finding in this component has had to be measured twice, and §2.1's exhibit shows one copy
masking in one file (agreement case fires) and not the other (clean 59/59).

**Proposed fix — UNVERIFIED.** The same extraction as §2.1(a) collapses both: one named
`scrub_env()` (or `subprocess_env()`) owning the allow-list and the comprehension, imported by the
sibling — the two files already import each other in-process (`check-surface-recall.py:323, 561,
615`), so no new coupling is introduced. The allow-list duplication, the round-8 H1 agreement case
that exists only to police that duplication, and the 31-line probe duplication all disappear
together.

### 2.3 LOW — the bytecode this suite actually deposits in its own tree arrives by a route the fold's property does not cover, and nothing asserts that route. *(Pre-existing, not caused by the fold.)*

**Finding.** The fold's subject is the environment handed to **subprocesses**. Measured: when the
variable is unset, the bytecode `check-surface-recall.py --self-test` leaves in its tree does not
come from a subprocess at all.

```text
# staged tree, no __pycache__ anywhere, var UNSET
$ env -u PYTHONDONTWRITEBYTECODE python3 <tree>/scripts/check-surface-recall.py --self-test
59/59 self-test cases passed

$ find <tree> -name '*.pyc'
<tree>/scripts/__pycache__/check-rc-contract.cpython-314.pyc
<tree>/scripts/__pycache__/check-ratchet-contract.cpython-314.pyc

# the same run for check-rc-contract.py alone:
(no .pyc written)
```

Two files, and they are exactly the two siblings this suite loads **in process** via
`spec_from_file_location` + `exec_module` (`check-surface-recall.py:561` and `:615`). No allow-list
governs that route; `SUBPROCESS_ENV_KEYS` cannot reach it by construction. `check-rc-contract.py`
has no such import and writes nothing.

**Why LOW and not higher, argued rather than asserted.** Inside the mutation harness the route is
covered — `check-plan-code.child_env` sets `PYTHONDONTWRITEBYTECODE=1` in the spawned suite's own
process, so `exec_module` writes nothing and #217's stale-mutant-`.pyc` hazard cannot fire there.
`__pycache__/` and `*.pyc` are gitignored (`.gitignore:72-74`), so it never dirties `git status`.
What remains is that the documented developer invocation (*"Run `--self-test` after touching it"*)
silently creates `scripts/__pycache__/` — which exists in the live repo right now — and that **no
case, in any file, observes this route**. Being gitignored is what made #217 expensive
(`26661d75`: *"the residue was never in `.claude/` — it was a mutant `.pyc` outliving the restore of
its own source"*), so "invisible and covered only by a sibling's env var" is worth writing down
rather than leaving implied.

**Proposed fix — UNVERIFIED.** Nothing in the deliverable. Either state the scope on the property
case (the allow-list governs the subprocess route; the in-process `exec_module` route is governed by
the *suite's own* interpreter environment and by `child_env` alone), or set
`sys.dont_write_bytecode = True` once at suite entry so the suite cannot pollute whatever tree it
runs in. The first is free and honest; the second changes behaviour and needs its own falsifier.

### 2.4 LOW — the import's stderr is still discarded, so the red the fold introduced arrives with no diagnosis. *(Caused by the fold — it kept the redirect r3-codex proposed removing.)*

**Finding.** `python3 -c 'import _pycprobe' >/dev/null 2>&1` is unchanged. Before the fold a failed
import was a silent **pass**; after it, a silent **fail** — strictly better, and the reason the
redirect is no longer a correctness defect. But the reader now gets `got [] want ['ran']` and no
statement of why the import did not run. r3-codex's proposed fix explicitly included *"remove the
import stderr redirection"*; the fold took the witness and not that half, and does not say it
declined it.

Keeping `>/dev/null` and dropping `2>&1` would route an import failure into `observe`'s / `render`'s
existing stderr refusal, which raises `CannotRun` **with the message** — the repo's own rule that a
question that could not be asked must not look like an answer. Measured precondition for that
change: a *successful* import under this probe writes nothing to stderr, so the refusal costs
nothing in the green case (E0 at 56/56 and 59/59 is that measurement).

**Proposed fix — UNVERIFIED.** Drop `2>&1` from the import line in both copies (or, after §2.2's
extraction, in the one copy).

---

## 3. The design question — sound, salvageable, or replace?

**Verdict: the current design should be REPLACED, and the replacement already exists in this
repository under a different name.**

### 3.1 Why the current instrument cannot terminate

The probe's assertion is a **negative observation on the filesystem**: *no `.pyc` appeared.* A
negative observation is meaningless without its preconditions, and this one has at least three, each
of which must be separately asserted:

1. the spawn happened — asserted since r3 (the real `observe` / `_render_once` call);
2. the import happened — asserted by r4 (the `ran` witness);
3. bytecode **would** have been written here but for the key — **still unasserted** (§2.1).

Each round discovered the next one in that list. There is no principled reason to believe the list
is now exhausted: a fourth candidate is *"and the `.pyc` would have landed in the directory I
globbed"*, which is already false if anything ever sets `sys.pycache_prefix` for the child. I
measured that the env route to it is closed — `PYTHONPYCACHEPREFIX` is not allow-listed, and with
the key removed plus that variable set ambiently the case stays **red** (§4, B) — but closed *by the
allow-list the case is supposed to be testing*, which is circular, and open again the moment
someone widens the allow-list (§4, C: swap the key for `PYTHONPYCACHEPREFIX`, set it ambiently,
56/56 green).

So the shape is: every round pays for one precondition, the enumeration is not bounded by anything,
and the probe's verdict is a function of the caller's environment. That last part is worth saying
plainly, because r3's comment claimed the opposite and the fold inherited the claim: *"It SETS the
variable rather than reading the caller's, so the verdict cannot depend on how the guard was
invoked (backlog #56's shape)."* It **does** depend on how the guard was invoked — via `PATH`
(§2.1). Setting one variable did not remove the dependence; it moved it.

### 3.2 The instrument that settles it — and it is already in the repo

`scripts/check-plan-code.py:3842-3850`, for the *same* variable, the *same* hazard (#217), with a
mutation entry of its own (`check-plan-code.json` #93):

```python
_e1, _e2 = child_env(pathlib.Path(_bd)), child_env(pathlib.Path(_bd2))
case("...and the other half of the race: no suite the harness spawns may WRITE a cache "
     "either, or this run poisons the next one",
     (_e1.get("PYTHONDONTWRITEBYTECODE"), _e2.get("PYTHONDONTWRITEBYTECODE")),
     ("1", "1"))
```

Two lines. It asserts a **positive** fact about a value this repository owns — the env dict the
spawn will be given — and it has:

* **no precondition.** Nothing has to *happen* for the assertion to mean something, so there is no
  list for a future round to extend;
* **no ambient dependence.** No `PATH`, no bash, no second interpreter, no CPython behaviour, no
  filesystem. `check-plan-code.py --self-test` cannot be made to pass this case by changing the
  machine;
* **two distinct inputs**, satisfying `check-fixture-variation` — the recorded
  `exercise-the-producer-at-two-distinct-inputs` rule;
* the right **altitude**. The repository owns the construction of the env dict. CPython owns whether
  `PYTHONDONTWRITEBYTECODE` suppresses bytecode. The filesystem probe tries to own both, and every
  defect across r2–r4 lives in the half the repository does not own.

**Why that instrument was not available to these two guards is the actual root cause, and it is one
line of structure:** in `check-rc-contract.py:295` and `check-surface-recall.py:168` the scrub is an
**inline dict comprehension**, not a named producer. There is no `child_env` to call, so there is
nothing a two-line case can assert — which is precisely how r2 ended up asserting the constant
instead, and how r3 was forced out to an end-to-end probe to recover the call site. The three rounds
are downstream of a missing function.

`it-already-exists-under-a-name-i-didnt-search` is a recorded failure here (3× in one day). The
sibling guard solved this property in two lines while this component spent three rounds, two
reviewers and ~60 lines of duplicated probe on it.

### 3.3 The one honest objection, and the answer

The env-dict assertion proves the dict **contains** the key; it does not prove the call site
**passes that dict** to `subprocess.run`. That is exactly r3-claude's finding, and it is the reason
r3 pushed out to an end-to-end probe — so the two reviewers' findings pull in opposite directions,
and patching toward either one re-opens the other. That is the thrashing, stated mechanically.

The resolution is not to choose. It is to make the defect **unrepresentable** rather than detected:

* extract `scrub_env()` as the single producer, used by both spawn sites;
* the "call site inlines a hand-copy" mutation then has to *delete the call to the helper*, which is
  visible to the ordinary machinery (an unused producer, and the helper's own case) rather than
  needing a filesystem probe to notice;
* `check-plan-code.py`'s own case has the identical residual gap (it asserts `child_env`'s output,
  not that `run_suite` passes it) and the repository has accepted that altitude for the sibling, on
  the same reasoning, for the whole life of #217.

If a belt-and-braces end-to-end witness is still wanted, keep **one** — not two copies — and make it
**two-sided** per §2.1(b): the key-dropped spawn must produce a `.pyc`, or the run is CANNOT RUN.
A two-sided probe detects every precondition failure in the whole enumerated class at once, including
ones nobody has thought of, because a vanished counterfactual shows up as a red control rather than
a green verdict. I checked this direction holds for the exhibit I found: under the `-B` shim the
key-dropped spawn produces no `.pyc`, so the control would be red and the run would refuse — which
is the correct outcome and the one the current probe cannot reach.

### 3.4 Answer, in one line

**Replace.** Extract the scrub into one named producer shared by both files; assert its output the
way `check-plan-code.py` already does; retire the duplicated filesystem probe, or keep exactly one
copy of it with a key-dropped control whose failure is CANNOT RUN. That single change answers
§2.1, §2.2 and §3.3 together, and is the only proposal here that removes a *class* rather than the
instance the round in front of it happened to find.

---

## 4. Answers to questions 2–5

### Q2 — can the conjunction still be satisfied vacuously?

**Yes — one route, reproduced, and it is §2.1.** Everything I tried is listed, pass and fail:

| Attack | Result |
|---|---|
| **`python3` on `PATH` that adds `-B`, key removed** | ✅ **VACUOUS PASS.** rc half 56/56 green; sr half green on the property case (its only failure is the unrelated agreement case). Both call-site entries survive |
| `PYTHONPYCACHEPREFIX` set ambiently, key removed | ❌ refuted — stays **red** (55/56, named case). The variable is not allow-listed, so the scrub removes it. The allow-list genuinely protects here |
| `PYTHONPYCACHEPREFIX` *swapped into* the allow-list in place of the key, set ambiently | ✅ **56/56 green.** The load-bearing key is gone and the case passes. Arguably a different correct implementation (caches land outside the tree) — but the green is then a property of the caller's environment, not of the code, and nothing declares that |
| Parent started `-B` (parent `sys.dont_write_bytecode`), key removed | ❌ refuted — **red** (55/56). Not inherited across `subprocess`. Independently confirms r3-codex |
| `PYTHONDONTWRITEBYTECODE` unset in the caller's env | ❌ refuted — the probe sets it itself and restores in `finally`; verdict unchanged |
| Stale witness / path collision across runs | ❌ refuted — fresh `TemporaryDirectory()` per call, and the witness is read before the `with` exits |
| Hook whose first `python3` fails, second succeeds | ❌ refuted — the witness is written by the *first*; its failure gives `[]`, now red (E3/E4) |
| Witness written without the import running | ❌ refuted — `open(...)` lives only in `_pycprobe.py`; the hook's second `python3` reads stdin and prints JSON, touching nothing in `_probe` |
| `.pyc` written then removed before the glob | ❌ refuted — the return expression is evaluated inside the `with`, before cleanup |
| `__pycache__` absent → glob raises | ❌ refuted — `Path.glob` on a missing directory yields nothing, no exception |
| Read-only / `noexec` probe dir | **NOT MEASURED** (§1.6). Reasoned: both plausible shapes raise, and a raise aborts the suite rather than passing it |
| `TMPDIR` unusual | see Q3 |

### Q3 — does the witness survive the scrub it is supposed to test?

**It is insensitive to `TMPDIR`, and that insensitivity does not read as a pass.** Measured: dropping
`TMPDIR` from the allow-list leaves the suite at **56/56 green**. The reason is structural rather
than lucky — `_probe` is produced by `tempfile.TemporaryDirectory()` in the **parent** and
interpolated into the hook source as a **literal absolute path**, so the child never needs `TMPDIR`
to find it. If `TMPDIR` were de-allow-listed the probe would keep working and keep measuring its
own subject; it would simply say nothing about `TMPDIR`, which it does not claim to.

Corollary worth recording: the property case covers **one of the five** allow-listed keys. That is
honest (`PATH`/`HOME`/`TMPDIR`/`LANG` have no such property), but it means the case name — *"a spawn
scrubbed by THIS guard's allowlist writes no bytecode cache"* — is the narrowest true reading of a
sentence that scans broader. Not a finding; a scope note.

If `TMPDIR` pointed at a read-only filesystem, `TemporaryDirectory()` would raise in the parent and
the suite would abort — loud, not a pass. NOT MEASURED, reasoned.

### Q4 — attribution, and does either entry subsume the other?

All four entries applied individually to fresh copies of a green control (§1.3). **Each is killed,
and the named case is among the `[FAIL]` lines in every one.**

| Entry | rc | tally | `[FAIL]` lines |
|---|---|---|---|
| `check-rc-contract.json` #15 — constant loses the key | 1 | 55/56 | the named bytecode case **only** |
| `check-rc-contract.json` #16 — call site inlines a literal | 1 | 55/56 | the named bytecode case **only** |
| `check-surface-recall.json` #19 — constant loses the key | 1 | 57/59 | round-8 H1 agreement **+** the named bytecode case |
| `check-surface-recall.json` #20 — call site inlines a literal | 1 | 58/59 | the named bytecode case **only** |

**Neither subsumes the other, in either file.** #15/#19 can be killed by the constant's value alone;
#16/#20 cannot — they leave the constant intact and change only the production line, so only an
assertion that reaches the call site can see them. Conversely #16/#20 leave the two constants in
agreement, so nothing about the constant can see them. They are genuinely two different claims
(*the value is right* vs *the production code reads the value*), which is precisely the r2→r3
progression made mechanical.

**One qualification, which is r3-codex's and still stands:** #19 is **confounded**. The agreement
case fires on it independently, so #19 would report `caught` even if the bytecode property were
entirely vacuous. #20 is the clean one in that file — and §2.1 shows #20 is the one that survives
under the shim, with nothing else to catch it. So in `check-surface-recall.py` the only unconfounded
carrier of r3's finding is also the one with the open precondition.

Anchor integrity, recomputed independently with the harness's own rule over the whole manifest:
**1208 edits, 0 multi-match, 0 not-found.** The four anchors here each resolve exactly once, no
anchor is a substring of another, and I found no order dependence between the paired entries (each
was applied to a fresh copy).

### Q5 — backlog #228 and #229

Both verified **from the code they cite**, not from the rows. Neither is refuted; one half of #228's
falsifier I could not execute.

**#228 — `codex-frontier-model.py` selects on `visibility`.** CONFIRMED.

```python
# scripts/codex-frontier-model.py:65-69
candidates = [
    m for m in data.get("models", [])
    if m.get("visibility") == "list"
    and m.get("supported_in_api")
    ...
```

```text
# live ~/.codex/models_cache.json, read this session
{'slug': 'gpt-5.5',           'visibility': 'hide', 'supported_in_api': True, 'priority': 13}
{'slug': 'codex-auto-review', 'visibility': 'hide', 'supported_in_api': True, 'priority': 43}

$ python3 scripts/codex-frontier-model.py
error: no visible, API-supported model with a priority found in cache
rc=1
```

Every element of the row holds: the conjunction, both models `hide` + `supported_in_api: true`, the
priorities 13 and 43, and the exact error string. The second half of its falsifier — that
`codex exec -m gpt-5.5` completes — I did **not** run (NOT MEASURED); it is corroborated from a repo
artefact instead: `docs/reviews/codex/shard-mutation-sweep-r3-codex.md` opens
`<!-- codex-review: model=gpt-5.5 -->`, i.e. a full review was produced on the very slug the
selector calls unavailable. The row's own honesty holds up too — it declines to apply the fix
because `visibility`'s semantics are OpenAI's and are asserted from one snapshot, which is the
correct refusal. **No refutation.**

**#229 — the ratchet's widened population is opt-in by self-testedness.** CONFIRMED, all four
claims:

* `discover_guards` (`:161-172`) filters on `GUARD_PATH_RE.fullmatch(p)` — a **filename** rule;
  `codex-frontier-model.py` does not match `check-*`.
* `discover_self_tested_nonguards` (`:433-440`) requires `SELF_TEST_RE.search(texts[p])`;
  measured **0** occurrences of `self-test`/`self_test` in `codex-frontier-model.py`.
* **0** entries naming it in `scripts/mutations/*.json`.
* Imported by the review gate's own entry point: `scripts/codex-review.py:102`,
  `_frontier = import_module("codex-frontier-model")`.

And the claim the row makes about the pinned debt set is stronger than it states:
`grep -n codex-frontier-model scripts/check-ratchet-contract.py` returns **nothing** — the script is
absent from that file entirely. `check-ratchet-contract.py` runs rc=0 over 43 guards with the live
defect sitting in a file it never examines. Its preference for fix (a), an import-graph population,
over (b), hand-adding one name, is the right call by this repo's own 17× record on
instance-not-class fixes. **No refutation.**

---

## 5. What I tried to refute and could not

* **All four falsifiers.** Constant sever, call-site inline, key-removed-plus-missing-import, and
  import-broken-alone each go red via the named case, in both files, over a control proved green
  first. The r3-codex false pass is genuinely closed.
* **The three-row table in the fold's own comment.** All three rows reproduced exactly.
* **The fold's historical "Measured:" claim** about the pre-fix false pass — reproduced against
  `8c1a207a`'s files, 56/56 and 59/59 with rc=0 (§1.4). It is a measurement.
* **Every coordinator number** (§1.2), including the anchor count, which I recomputed from the
  manifests rather than re-running the harness.
* **The leaked-temp-dir Low.** Delta 0 over both suites. Fixed.
* **The witness itself.** I could not write `ran` without the import running, could not make it
  survive from a previous run, could not make the hook's second `python3` produce it, and could not
  get a `.pyc` created and then hidden from the glob by any route reachable through the current
  allow-list.
* **The env route to `sys.pycache_prefix`.** `PYTHONPYCACHEPREFIX` set ambiently with the key removed
  stays **red**; the scrub really does remove it. Parent `-B` also fails to create a false pass.
* **Residue in the live repo.** No `_selftest-*` left behind; `_fixture_hook`'s `finally` holds.

The one thing I could break is the one thing the fold does not assert, and it is the subject of
§2.1 and §3.

---

## 6. Findings table

| Severity | Aims at | Deliverable or instrument | Caused by the fold itself? |
|---|---|---|---|
| **Medium** | The probe's third precondition — *bytecode would be written absent the key* — is unasserted, so under a bytecode-suppressing `python3` both call-site mutation entries survive (56/56, 59/59) | Instrument | **Yes** — it is the precondition this fold's own fix pattern did not extend to |
| **Medium** | 30 of 31 probe lines duplicated across two files, while the standing "a shared module would be heavier than the problem" justification — written for a 5-element tuple — is unrevised, and no case refuses a probe divergence | Instrument | **Yes** |
| **Low** | The bytecode this suite actually writes into its tree comes from three in-process `exec_module` sibling imports, a route no allow-list governs and no case observes (measured: 2 `.pyc`) | Instrument | No — pre-existing; surfaced by the fold's subject |
| **Low** | `2>&1` retained, so an import failure now yields an undiagnosed `got [] want ['ran']` instead of a `CannotRun` carrying the reason | Instrument | **Yes** — r3-codex proposed removing it; the fold took the other half of that fix without saying it declined this one |
| — | Design: the instrument is a negative filesystem observation with an unbounded precondition list; the positive instrument already exists at `check-plan-code.py:3842-3850` and is unavailable here only because the scrub was never extracted into a named producer | Instrument (design) | The *thrashing* is, yes — three rounds are downstream of one missing function |

No finding touches a shipped product deliverable. Every one is in the instrument, which is what this
component is.

---

## 7. Verdict

The fold does what it claims: r3-codex's false pass is closed, measured, in both files, over a green
control. Nothing the coordinator reported is false.

But the class has now recurred a fourth time in the same probe, and I can exhibit it: the two
mutation entries that exist to carry r3's finding are killable only because this machine's `python3`
happens to write bytecode, and `--self-test` reports 56/56 and 59/59 when it does not. A mutation
entry that can survive for an ambient reason is, by this repository's own standard, a gate that is
not yet earning its green.

⛔ **The recommended response is NOT a fifth patch to this probe.** §3 is the deliverable of this
half: extract the scrub into one named producer, assert its output as `check-plan-code.py` has done
for this exact variable all along, and retire or halve-and-control the filesystem probe. That is the
only proposal here that ends the sequence instead of advancing it by one.

**VERDICT: NOT CONVERGED**
