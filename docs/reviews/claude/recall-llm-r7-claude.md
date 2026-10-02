# Round 7, Claude half — the option-C relocation: R3 moves to the hook's own guard (backlog #196/#201/#202)

**Mandate: adversarial. The claim under attack is that this fold is correct.**

Subject: the **working tree**, uncommitted, on `semantic-recall-replication`.

## ⚠ THE SUBJECT MOVED THREE TIMES DURING THIS REVIEW, SO THE VERDICT IS PINNED TO A HASH

`scripts/check-surface-recall.py` was edited at **11:09:33** and **11:12:17**, and
`scripts/mutations/check-surface-recall.json` at **11:13:25**, while this half was running. Two of
the findings I had measured were closed by those edits before I could file them (recorded under
*Closed mid-review* below, because a finding that was real at measurement time is evidence about the
round whether or not it survives to the document). Every finding below was **re-confirmed after
11:13:25** against:

| file | sha256 (first 16) |
|---|---|
| `scripts/check-surface-recall.py` | `c26fb10dcd0e345f` |
| `scripts/mutations/check-surface-recall.json` | `dca2eaf6281d9eb6` |
| `.claude/hooks/surface-recall.sh` | `2b0ae0685d75d3c6` |
| `scripts/check-rc-contract.py` | `fc97e556c865629f` |
| `scripts/check-plan-code.py` | `3cab117ead3d9d7c` |

The tree has been stable from 11:13:25 to 11:25:35. ⚠ **If any of those hashes has moved, the
BLOCKING below is the one to re-run first** — it is a three-minute measurement
(`drive3.py`, quoted in B1).

---

## Severity summary

| # | Severity | Title |
|---|---|---|
| B1 | **BLOCKING** | Mutation entry 10 leaves its fixture in the staged tree by design, so the AFTER-control for this file is RED and `--mutate .` reports NOT CHECKED over all 1163 entries |
| H1 | HIGH | The relocation DID lose a property: #201's literal shape is *approved* if declared, and nothing examines the six declared strings themselves |
| H2 | HIGH | Round 6 H1's stderr refusal landed in `render` and NOT in `observe` — R1/R2 still read a bash fatal error as silence, measured |
| H3 | HIGH | `DECLARED_RENDER[3] = ""` is justified by a sentence that misstates the dedupe's key: the key is the MESSAGE, so a stale cache is silent for the plan's whole remaining life |
| M1 | MEDIUM | The seam is an ENV VAR, so one ambient variable silently disables the hook or injects text into the model's context, tracelessly. `${1:-…}` is a closed alternative |
| M2 | MEDIUM | `check-rc-contract.observe` does not scrub `RECALL_MATCHER`, so an ambient value makes every observation an artefact — and the resulting red names the wrong cause |
| M3 | MEDIUM | The sibling import has a FAIL-OPEN: `SystemExit(0)` at `check-rc-contract.py`'s module level gives rc=0 with zero output; two other failure modes miss the documented rc=2 |
| M4 | MEDIUM | The two final cases glob the SHARED directory, so two concurrent `--self-test` runs give a false RED — reproduced at 2 of 6 stagger offsets |
| M5 | MEDIUM | A killed run leaves `_selftest-*.sh` and `_selftest-marker-*` in `.claude/hooks/`, which is not gitignored — reproduced at 3 of 13 SIGKILL offsets |
| L1 | LOW | `render` inherits the whole ambient environment and treats any stderr as a refusal: `PYTHONVERBOSE=1` turns the gate into rc=2 and blames the hook |
| L2 | LOW | `check-fixture-variation.py`'s comment names three retired keys the diff does not contain |
| L3 | LOW | Manifest entry 11 is an equivalent mutant, killed by a `__defaults__` identity rather than by the property it names |
| L4 | LOW | The r7 B2 corpus arm's second clause matches ANY marker, so the case is satisfied by a peer's or a stale one |

---

## BLOCKING

### B1 · Mutation entry 10 leaves its fixture hook in the staged tree **by design**, `run_mutations` restores only the mutated source file, and the AFTER-control therefore goes RED — turning `--mutate .` into NOT CHECKED for all 1163 entries

**What is wrong.** Manifest entry 10 disables the fixture cleanup in order to prove the suite
notices debris:

`scripts/mutations/check-surface-recall.json`, entry 10:

```json
{ "name": "the fixture hook stops being removed, so a self-test leaves debris in the repo it measures — an instrument that edits the repo corrupts its peers",
  "file": "scripts/check-surface-recall.py",
  "edits": [["        path.unlink(missing_ok=True)", "        pass"]],
  "expect": "...and no fixture hook survived the suite" }
```

The mutation is correctly caught. But its observable effect is **persistent state in the shared
staged tree**, and `run_mutations` restores only the file it mutated:

`scripts/check-plan-code.py:1691-1693`:

```python
        orig = (d / fname).read_text()
        (d / fname).write_text(src)
        rc, out = run_suite(d, fname)
        (d / fname).write_text(orig)
```

Nothing removes `d/.claude/hooks/_selftest-<pid>.sh`. The after-control then runs the same suite in
the same tree — `scripts/check-plan-code.py:1607-1613`:

```python
        for position, name in enumerate(targets, 1):
            ...
            rc, so, se = run_suite_parts(d, name)
            out = merged_output(so, se)
            if not control_is_green(rc, out):
                ok = False
                controls_green = False
```

and `controls_green = False` makes `Measured(...)` raise `VerdictContractError`, so the run returns
`NotMeasured` — no tally, the whole sweep reported as NOT CHECKED (`:1630-1635`).

**Reproduction (run against the current hashes, in my own staged tree — no repo file touched).**
I used the harness's own `stage_tree`, `run_suite`, `control_is_green` and `run_mutations`:

```text
BEFORE-control rc=0 green=True '36/36 self-test cases passed'
  [1/11] … [11/11]
all caught+attributed: True
survivors: []
AFTER-control rc=1 green=False
tail: [FAIL] ...and no fixture hook survived the suite
       expected []
       got      ['_selftest-97643.sh']
```

Isolated to entry 10 alone on a freshly staged tree:

```text
BEFORE-control rc=0 green=True '36/36 self-test cases passed'
mutation ok=True ev=[(True, True)]
debris now: ['_selftest-82355.sh']
AFTER-control rc=1 green=False
```

**And it contaminates every entry ordered after it.** Entry 11 run on a clean tree vs. after entry
10, same tree:

```text
clean  -> fails: ['render defaults to the SHIPPED hook, …']
after  -> fails: ['render defaults to the SHIPPED hook, …', '...and no fixture hook survived the suite']
```

Attribution survives by the letter of the rule (each `expect` still matches exactly one red case),
so this is **not** a false green — but the measurement is no longer single-cause, and the
after-control message blames *"the tree changed underneath it … disk, OOM, a peer process"*, which
is the wrong cause. That is the "plausible and wrong" shape `stage_tree`'s own docstring refuses
one layer up.

**Why this is Blocking rather than High.** `scripts/check-plan-code.py --mutate .` is what CI runs
and is the only gate over the 1163 declared mutations. It now returns NOT CHECKED deterministically,
on every invocation, for a reason that has nothing to do with any mutation. The in-flight partial
sweep will report it.

**Verified fix direction** — scope the two final globs to the current pid. Applied to a staged copy
only:

```python
    case("...and no fixture hook survived the suite",
         sorted(q.name for q in HOOK.parent.glob(f"_selftest-{_os.getpid()}.sh")), [])
    case("...nor any fixture MARKER — the file the corpus arm branches on",
         sorted(q.name for q in HOOK.parent.glob(f"_selftest-marker-{_os.getpid()}")), [])
```

```text
BEFORE-control rc=0 green=True '36/36 self-test cases passed'
all caught+attributed: True
survivors: []
AFTER-control rc=0 green=True
tail: 36/36 self-test cases passed
```

Entry 10 is **still killed** (the debris during that run *is* the current pid's file), and M4 below
is closed by the same two lines. ⚠ The trade, stated: the cases then assert "no fixture *of mine*
survived", which is a weaker claim than they make today. That is the correct weaker claim — the
cross-run question belongs to the lagging check the plugins doc already names (*if a resume ever
finds debris, something wrote one anyway*), not to a case that a peer can redden.

**What would refute B1.** An after-control that comes back green with entry 10 in the manifest; or
a cleanup step in `mutate_delivered`/`run_mutations` that restores the tree and not just the file.

---

## HIGH

### H1 · The relocation lost the one property R3 was filed for: #201's literal shape is now *approved* if `DECLARED_RENDER` declares it, and nothing examines the declared strings themselves

**What is wrong.** The new rule is an equality against a hand-typed sentence, and the file says so
honestly (`scripts/check-surface-recall.py:73-76`):

```
# ⚠ WHAT THIS DOES NOT DO: it detects DRIFT, not BADNESS. Edit a message, update the string here in
# the same commit, and the gate passes saying nothing about whether the NEW sentence is good.
```

The disclosure is accurate; the **consequence** is a property HEAD enforced and nothing now does.
`git show HEAD:scripts/check-rc-contract.py:274-291` (`dangling_detail`) asked a question about the
payload itself, not about drift:

```python
        for label in ("Detail:", "detail:"):
            head, sep, tail = payload.partition(label)
            if sep and not tail.strip():
                bad.append(rc)
```

**Reproduction.** I reintroduced #201 verbatim — the `5)` arm appending `Detail: $OUT`
unconditionally — in a fixture hook at a real repo path, then declared exactly what it renders:

```text
render of the reintroduced #201 arm, no detail:
  "recall-llm: a plan IS armed and the matcher cannot read it, so NO memory entry was\n
   surfaced for this step — this is not 'nothing applies'. Detail: \n"

NEW guard, with that render DECLARED  -> []      (empty list = PASSES)
OLD dangling_detail predicate, same payload -> True  (the old rule FLAGS it)
```

So a commit that reintroduces the exact reader-visible defect of backlog #201 and updates
`DECLARED_RENDER` in the same diff is green under both guards. The stated protection — *"both
sentences appear in a PR diff where a reader judges again"* — is a human gate, and the fold's own
argument is that this component's four previous failures all survived human reading.

**The cheap retained form was not taken.** `dangling_detail`'s predicate applied to the six
**declared strings** is pure, needs no execution, and has none of the proxy problem that defeated it
four times — because the strings are literals *in this file*, not an open set of shell renders. The
enumeration trap was in reading the HOOK; it does not exist when reading the declaration. Measured:
nothing in `check-surface-recall.py` reads `DECLARED_RENDER`'s values except `undeclared_render`'s
equality — `grep` for `Detail` in that file hits only `_CORPUS` entries and case names.

**What would refute H1.** A rule anywhere in the tree that refuses a `DECLARED_RENDER` value ending
in a label with nothing after it; or a demonstration that the old predicate also passes the payload
above.

### H2 · Round 6 H1's stderr refusal landed in `render` and NOT in `observe`, so R1 and R2 still read a bash fatal error as silence — the defect H1 was filed against

**What is wrong.** Round 6 H1 was filed against `observe` in `check-rc-contract.py`
(`docs/reviews/claude/recall-llm-r6-claude.md:197`: *"`observe` reads a bash FATAL ERROR as silence,
and its documented refusal is unreachable by construction"*), with the fix direction *"`observe`
already has `proc.stderr`; refusing when stderr is non-empty"*. The fix exists in the repo — in the
**new** file:

`scripts/check-surface-recall.py:130-134`:

```python
    if proc.stderr.strip():
        raise CannotRun(
            f"the hook wrote to STDERR at rc {rc}, which it cannot report through its exit status: "
            f"{proc.stderr.strip()[:200]!r}. Round 6 H1 — treat this as NOT RUN."
        )
```

`scripts/check-rc-contract.py:276-301` (`observe`, still the observer for `handled_codes` and
`dead_arms`) has no such clause. Derived rather than read: `"proc.stderr" in` the source of
`observe` → **False**; in the source of `render` → **True**.

**Reproduction** — round 6 H1's own arm, through the surviving observer:

```text
observe() on an arm with a MISSING COMMAND ->
  "recall-llm: a plan IS armed … is not 'nothing applies'. Detail: \n"
observe raised CannotRun? NO — it returned a payload
```

So the hollow promise is forwarded, `handled_codes` records rc 5 as handled, and with R3 gone from
that file nothing there notices the dangling `Detail:` either. Codex's B1 ⑵ reproduced the same
shape for a *dead* arm (`observe rc7: ''`, `dead arms: []`).

**This is also a one-rule-two-places defect**, which is this repository's most-measured failure (17
instances). Two sibling observers of the same subject now have divergent refusal sets — `observe`
refuses on non-zero exit and a bad envelope; `render` refuses on those plus stderr, a missing hook,
no bash and a timeout — and the weaker one is the one two of the three rules use.

⚠ **Partly filed, and the filing does not cover this.** Backlog #209 names `dead_arms`' single
polarity and the staged tree, and its ⑵ mentions an arm that "dies inside command substitution". It
does **not** say that the repair for that class already exists 400 lines away and was not ported. The
port is a four-line copy.

**What would refute H2.** `observe` raising `CannotRun` for the missing-command arm; or evidence
that the pre-fold `observe` never had the clause and round 6 H1 was closed some other way. (I
checked the second: Codex's r7 repro shows the pre-fold `observe` returning `''` rather than
raising, so this is an **unfixed finding carried forward**, not a regression introduced by the
relocation.)

### H3 · `DECLARED_RENDER[3] = ""` records a silence whose written justification misstates the dedupe's key — the key is the MESSAGE, so a stale cache is silent for the plan's whole remaining life

**What is wrong.** The hook treats rc 3 as its siblings and rc 5/6 deliberately not:

`.claude/hooks/surface-recall.sh:70-76`:

```bash
  0) [ -n "$OUT" ] && PAYLOAD="$OUT" ;;
  # ⛔ M4: `-n "$OUT"` because the matcher now deduplicates the NAG's message while keeping rc 3
  # every time — the contract must not lie about the outcome, but the reader should not be told to
  # run `--arm` on every single begin-plan.py call for the same step.
  3) [ -n "$OUT" ] && PAYLOAD="recall-llm: the recall cache for this plan is absent or stale, …
```

and `:86-91`, for rc 5, argues the opposite for the same situation:

```bash
  # ⛔ AND NOT `[ -n "$OUT" ] && PAYLOAD=…` LIKE ITS SIBLINGS: that makes a deduped rc=5 SILENT,
  # which is the conflation B1 split this code out of rc=2 to end. rc=5 IS NOT SILENCE. So the
  # static sentence always goes, and only the detail is conditional.
```

**The load-bearing clause is "for the same step", and it is false of the mechanism.**
`scripts/recall-llm.py:1086-1090` (`do_fire`'s docstring):

> ⭐ SO THE DEDUPE MOVED FROM A BRANCH TO THE BOUNDARY, and **its key is the MESSAGE rather than
> (plan, step)**

`:1108`: `if msg and not nag_once(CACHE_DIR / ".last-said", hashlib.sha256(msg.encode("utf-8")).hexdigest()[:16])`.

**Reproduction** — `nag_once` with the same message three times, then a different one:

```text
1st firing (step 1), same message -> True   (emit)
2nd firing (step 2), same message -> False  (SUPPRESSED)
3rd firing (step 3), same message -> False  (SUPPRESSED)
a DIFFERENT message              -> True
```

And both stale-cache producers build a step-independent message —
`scripts/recall-llm.py:703` (`f"STALE CACHE: armed against {got}, the plan on disk is {want}. …"`)
and `:779` (`f"STALE CACHE: the cache names {entry!r}, …"`): the interpolations are fingerprints and
an entry name, never a step.

**So the behaviour is:** a stale cache tells the reader once, then goes **silent at every remaining
step of the plan** while `--fire` keeps returning rc 3 and no memory entry is surfaced. That is
backlog #202's shape — a code the hook received and dropped — and `DECLARED_RENDER[3]` approves it
with the reason *"a stale-cache note with nothing to report stays quiet instead of nagging"*
(`scripts/check-surface-recall.py:84-85`), which is the reason the rc 5 comment calls a conflation.
`do_fire`'s own docstring names a stale fingerprint, *"produced by editing any `Doing:` line after
arming"*, as one of **"the two most reachable stale states"** — so this is live, not latent.

⚠ A distinction *could* justify the asymmetry — rc 3 is an **action request** (*run `--arm`*) and
rc 5/6 are **state reports** — and repeating an action request is nagging while repeating a state
report is not. That distinction is written nowhere, and `DECLARED_RENDER` is the one place the
project has decided a human judgement about reader-visible text gets recorded.

**Fix direction (two options, both cheap):** give rc 3 the rc 5/6 treatment — a short static
sentence that always goes, with only the detail conditional, and declare it; **or** write the
action-request/state-report distinction into `DECLARED_RENDER[3]`'s comment and correct the hook's
"for the same step" to "for the rest of this plan". The second is bookkeeping; the first is the one
that matches what the fold argues everywhere else.

**What would refute H3.** A dedupe keyed on `(plan, step)` for the rc 3 path; or a stale-cache
message that varies by step.

---

## MEDIUM

### M1 · The seam is an ENV VAR, so one ambient variable silently disables the hook or injects arbitrary text into the model's context — and leaves no trace in the repo

This is the one change to production code, so here is the worst case I can actually construct.

`.claude/hooks/surface-recall.sh:53-54`:

```bash
MATCHER="${RECALL_MATCHER:-$REPO_ROOT/scripts/recall-llm.py}"
[ -f "$MATCHER" ] || exit 0
```

**It is unset in configuration.** Derived: `.claude/settings.json`'s only top-level key is `hooks`;
there is no `env` block. ✅

**Two reachable consequences, both measured.**

```text
$ RECALL_MATCHER=/nonexistent/x.py bash .claude/hooks/surface-recall.sh
  rc=0, stdout EMPTY
```

A non-file value silently disables recall surfacing for the whole session, with **no diagnostic** —
which is #191's original failure (an inert matcher) returning through a new door, and the one failure
mode this hook's header insists it will report (*"When the cache is absent it says so in one line"*).

```text
$ RECALL_MATCHER=<any file> bash .claude/hooks/surface-recall.sh
{"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext":
 "recall-llm: a plan IS armed … Detail: INJECTED TEXT\n"}}
```

Arbitrary text reaches `additionalContext` — i.e. the model's context — at every `begin-plan.py`
Bash call.

**Why this is a weakening and not merely a restatement of existing privilege.** Before the change,
both outcomes required editing a tracked file: visible to `git status`, to `check-rc-contract.py` and
to CI. Now a single environment variable does either one, and **an environment variable is not in
the diff**. A PostToolUse hook inherits the session's environment, so an `export` in the shell that
launched `claude` persists for the session. The guard cannot see it: `render` sets `RECALL_MATCHER`
itself, so it observes the override path and never the default.

**Verified closed form — make the seam ARGV, not ENV.** `settings.json:57` is
`"command": "bash .claude/hooks/surface-recall.sh"`, with no arguments, so `${1:-…}` is unreachable
in production **by construction** rather than by convention. Measured on a scratch copy of the hook:

```text
MATCHER="${1:-$REPO_ROOT/scripts/recall-llm.py}"

no argv + RECALL_MATCHER exported -> "…Detail: ARGV-STUB\n"   (the env var is IGNORED)
with argv                         -> "…Detail: OVERRIDE\n"    (the guard's path still works)
```

`${1:-…}` is safe under `set -u`. The guard changes by one line (`["bash", str(target), str(stub)]`),
and M2 below disappears with it.

**What would refute M1.** A mechanism that asserts `RECALL_MATCHER` is unset in production; or a
demonstration that a hook does not inherit the session environment.

### M2 · `check-rc-contract.observe` does not scrub `RECALL_MATCHER`, so an ambient value makes every observation an artefact — and the resulting red names the wrong cause

`scripts/check-rc-contract.py:286` runs the staged hook with no `env=`, so the child inherits
everything:

```python
            proc = subprocess.run(["bash", str(hook)], capture_output=True, text=True, timeout=30)
```

With the seam in place, an ambient `RECALL_MATCHER` overrides the stub `_stub_tree` just wrote, and
`observe`'s `rc`/`out` arguments stop having any effect. **Measured** against a stub that exits 5
printing `HIJACKED`:

```text
$ RECALL_MATCHER=…/hijack.py python3 scripts/check-rc-contract.py
rc contract: 6 code(s) defined, 6 handled by an arm, 2 declared unhandled
FAILED — 1 disagreement(s) between the matcher and the hook:
  ✗ the hook ACTS on 250 different codes the matcher cannot emit (e.g. [1, 7, 8, 9] … [254, 255])
    — at this volume the cause is a catch-all that FORWARDS rather than one that is silent …
    Fix the `*)` arm, not the codes.
rc=1
```

It **fails closed** — I found no constant-response matcher that yields rc=0, because a non-empty
response makes all 250 undefined codes look like dead arms and an empty one makes `handled` empty
and triggers the inert-hook refusal at `:429-432`. So this is a false RED, not a fail-open. But the
red asserts a specific wrong cause about a correct hook, and the repo's recorded verdict on a gate
that is red for an ambient reason is that it gets switched off (backlog #56). One line fixes it
(`env` with `RECALL_MATCHER` popped) — or M1's argv seam removes the possibility.

**What would refute M2.** `observe` returning the stub's response with `RECALL_MATCHER` set.

### M3 · The sibling import has a FAIL-OPEN, and two further failure modes miss the documented rc=2

`scripts/check-surface-recall.py:172-177` loads `check-rc-contract.py` and guards only
`spec is None`, `OSError` on reading the matcher, and `mod.CannotRun`:

```python
    spec = importlib.util.spec_from_file_location("_rc_contract_for_hook", src)
    if spec is None or spec.loader is None:
        raise CannotRun(...)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_rc_contract_for_hook"] = mod
    spec.loader.exec_module(mod)
```

`exec_module` **runs** the sibling, and `main` catches only `CannotRun`. Measured on staged copies
(the file's own FAILS-IF promises exit 2, and the project rule is *"cannot run" is a FAILURE, never
a pass*):

| what I did to the sibling | rc | output |
|---|---|---|
| appended `def broken(:` (unparseable) | **1** | raw `SyntaxError` traceback, no `FAILED:` line |
| deleted it | **1** | raw `FileNotFoundError` traceback |
| appended `raise SystemExit(7)` | **7** | stdout empty, stderr empty |
| appended `raise SystemExit(0)` | **0** | **stdout 0 bytes, stderr 0 bytes** |

The last row is a **fail-open**: the gate exits success having measured nothing, and a CI step is
green. `check-ratchet-contract.py`'s R-rule is *"no fail-open handler"*, and it cannot see this one
because the hole is in what the handler does **not** catch. rc=1 is also wrong in kind, not just in
number — in this repo rc=1 means *the gate ran and found a problem*, so an unparseable sibling is
reported as a finding about the hook.

Latent today: `check-rc-contract.py` has a `if __name__ == "__main__"` guard, so nothing at its
module level exits. The class is live — any exception that is not `CannotRun` escapes.

**Fix.** Wrap `exec_module` in `except BaseException as exc: raise CannotRun(...)` — `BaseException`
specifically, because `SystemExit` is the row that fails open.

**What would refute M3.** rc=2 and a `FAILED: … Treat this as NOT RUN.` line in all four rows.

### M4 · The two final cases glob the SHARED directory, so two concurrent `--self-test` runs give a false RED

`scripts/check-surface-recall.py:393-396`:

```python
    case("...and no fixture hook survived the suite",
         sorted(q.name for q in HOOK.parent.glob("_selftest-*.sh")), [])
    case("...nor any fixture MARKER — the file the corpus arm branches on",
         sorted(q.name for q in HOOK.parent.glob("_selftest-marker-*")), [])
```

The filenames carry the pid, so two runs never *collide on a path*; the **assertions** are over the
whole directory, so each run can see the other's live files. **Reproduced** — run A started, run B
started after a stagger, both in one tree:

```text
offset 0.5s  A: rc=1 | 34/36 | fails=['...and no fixture hook survived the suite',
                                      '...nor any fixture MARKER — …']
             B: rc=0 | 36/36
offset 1.0s  A: rc=1 | 34/36 | fails=[same two]
offset 1.5s … 3.0s  both rc=0
```

2 of 6 offsets. `run_mutations` is a sequential `for` loop (`:1653`), so the mutation harness does
not trigger it — but this session has ~50 named agents, and *concurrent agents go wrong* is a
recorded, twice-paid lesson here. B1's pid-scoped fix closes this too.

**What would refute M4.** Both runs green at every stagger offset over a reasonable sweep.

### M5 · A killed run leaves two untracked files in `.claude/hooks/`, which is not gitignored

`_fixture_hook`'s removal is in a `finally` (`:271-273`), which covers exceptions and
`KeyboardInterrupt` and cannot cover `SIGKILL`. **Reproduced** — `SIGKILL` at 13 offsets:

```text
offsets that left debris: [(2.2, ['_selftest-12645.sh', '_selftest-marker-12645']),
                           (2.6, [...]), (3.0, [...])]
```

3 of 13. And:

```text
$ git check-ignore -v .claude/hooks/_selftest-1.sh
  NOT ignored -> debris shows as untracked and 'git add -A' would stage it
```

This repo has already paid for that exact sequence (`git add -A`'d a live agent's file, twice in one
night). `check-ratchet-contract.py:870` globs `.claude/hooks/*` for caller sources, so debris is
also silently added to that population. Cheapest mitigations, in order: add
`.claude/hooks/_selftest-*` to `.gitignore`; or write fixtures to a single `.claude/hooks/_selftest/`
subdirectory that is ignored as a unit; or install a `signal` handler. I did **not** reproduce
debris under `SIGTERM` or `SIGINT` at the offsets I tried (see *Could Not Establish*).

**What would refute M5.** No debris across a full offset sweep under `SIGKILL`.

---

## LOW

### L1 · `render` inherits the whole ambient environment while treating any stderr as a refusal, so an ambient variable turns the gate into rc=2 and blames the hook

`scripts/check-surface-recall.py:121-125` copies `os.environ` wholesale into the child, and
`:130-134` makes any stderr a `CannotRun`. The hook's `python3` invocations are inside that child, so
anything that makes python chatty on stderr is read as the hook misbehaving. Measured:

```text
$ PYTHONVERBOSE=1 python3 scripts/check-surface-recall.py
rc=2
FAILED: the hook wrote to STDERR at rc 0, which it cannot report through its exit status:
"import _frozen_importlib # frozen\nimport _imp # builtin\n…". Round 6 H1 — treat this as NOT RUN.
```

`PYTHONWARNINGS=always` and `PYTHONDEVMODE=1` are both clean (rc=0), so the exposure is narrow and
CI is protected by `check-python-pin.py`. The honest statement is that the refusal's **message
attributes to the hook something the environment caused**; a minimal explicitly-constructed child
env (the shape `check-plan-code`'s `child_env` already uses) removes the class.

**What would refute L1.** `render` constructing its child environment rather than inheriting it.

### L2 · `check-fixture-variation.py`'s comment names three retired keys that the diff does not contain

The new comment says the three keys retired from `check-rc-contract.py` are
`undeclared_render.declared`, `undeclared_render.hook_src` and `verdict.undeclared`. What
`git diff scripts/check-fixture-variation.py` actually removes is `dangling_detail.codes`,
`dangling_detail.hook_src` and `verdict.dangling`. Both sentences are true of *some* tree — the
comment's is true of the pre-fold **uncommitted** state — but the only baseline a reviewer or CI can
diff against is `HEAD`, so the provenance trail names keys that were never in the file being
changed. (The new file's own 7 keys are correct: I confirmed `render.hook`, not `hook_src`, is the
parameter's name.) This is the recorded *a-document-inside-the-corpus-it-measures* shape; round 6 M2
filed the same class against `EXPECTED_MUTATIONS`' trail.

### L3 · Manifest entry 11 is an equivalent mutant, killed by a `__defaults__` identity rather than by the property it names

Entry 11 changes `def render(rc, out, hook: Path | None = None)` to `hook: Path = HOOK`. That is
**behaviourally identical** for every caller in the tree — `render(5, "")` observes the shipped hook
either way — and it is killed by `case("render defaults to the SHIPPED hook …", render.__defaults__,
(None,))`, an assertion about the sentinel token rather than about the property the case names. The
repo's recorded rule is *assert the PROPERTY, not the mechanism — naming the fix's own tokens
defends only its deletion*. The case does also catch the real hazard (a default pointing at a
fixture path would fail the same comparison), so the coverage is not absent — but the mutation
proves only that the token is read, and `attributed=True` over an equivalent mutant is a weaker
claim than the entry's name makes.

### L4 · The r7 B2 corpus arm's second clause matches ANY marker, so the case is satisfied by a peer's or a stale one

`scripts/check-surface-recall.py:364-366`:

```bash
     if [ -f "$REPO_ROOT/.claude/hooks/_selftest-marker-$PPID" ] \
     || [ -n "$(ls "$REPO_ROOT/.claude/hooks/"_selftest-marker-* 2>/dev/null)" ]; then …
```

Only the first clause is about *this* run. The `||` glob makes the arm take its Detail branch
whenever any marker exists — a concurrent run's, or M5's debris — so the case can pass for the very
kind of ambient reason the comment above it says it was rewritten to stop. Dropping the second clause
leaves the case falsifiable (removing `marker.write_text` still reddens it) and removes the ambient
dependency; `$PPID` is correct here because `subprocess.run(["bash", …])` makes the guard process
bash's parent, which I confirmed by the case passing at all.

---

## Does the production seam weaken the hook, and did the relocation lose coverage?

**The seam: yes, modestly, and the weakening is cheaply closable.** The seam itself is inert in
production — `settings.json` has no `env` block, and the hook's rc=0 with `RECALL_MATCHER` unset. But
the *channel* is now the ambient environment, where before it was a tracked file, and two outcomes
follow from one variable: **silent total disablement** (`[ -f "$MATCHER" ] || exit 0` → rc=0, no
output, no diagnostic) and **arbitrary text in `additionalContext`** at every step transition. Both
measured. The difference from the old state is not the privilege required — anyone who can set the
session's environment can already do worse — it is that an env var **leaves no trace in the diff**,
so the repo's usual detectors (`git status`, `check-rc-contract.py`, CI) are all blind to it. The
closed form is argv: `settings.json` passes no arguments, so `${1:-…}` is unreachable in production
by construction, it costs one line in the hook and one in the guard, and it deletes M2 as well. I
would take it (M1).

The *second* way the seam weakens things is that the guard now always travels the override path, so
the **default expression is never observed by the guard that owns the hook**. It is still observed —
by `check-rc-contract.observe`, through the staged tree this fold argues is a proxy. So the one line
the fold changed in production is covered only by the observer it was changed to get away from. Not a
finding on its own; worth knowing when #209 deletes `_stub_tree`.

**The relocation: yes, one property, and it is the property #201 names** (H1). The equality is
strictly better at what it replaced — I re-derived the central numbers myself over the file's own
`_CORPUS`, parsed by AST: the label vocabulary catches **5 of 11**, the equality **11 of 11**,
exactly as claimed. And the r7 B2 arm still discriminates: the new guard returns `[5]` while
`check-rc-contract.observe` returns the clean sentence on the same source, so the marker rewrite
preserved the arm's evidentiary value while removing its dependency on `.claude/settings.json`. But
the equality answers *"is this the sentence a human approved?"*, and nothing answers *"is the
approved sentence a broken promise?"* — so the literal defect of backlog #201 passes both guards if
declared, which I reproduced. The remedy is not a return to proxies: applied to the six **declared
literals** rather than to an open set of shell renders, `dangling_detail`'s predicate has no boundary
to escape. That is the one thing I would add before merge.

Two further losses that are **not** the relocation's fault but are carried by it: round 6 H1's
stderr refusal exists only on the new side (H2), and `observe` keeps the staged-tree fidelity gap for
R1/R2 (filed, #209).

---

## Verified

| What I ran | Result | Bearing |
|---|---|---|
| `check-surface-recall.py --self-test`, real repo | **36/36**, rc=0 | docstring claims 36 ✓ (it said 34 when this half started) |
| `check-surface-recall.py`, real repo | rc=0, `6 declared sentence(s)` | live run green |
| `check-rc-contract.py --self-test` | **54/54**, rc=0 | docstring claims 54 ✓ |
| `check-rc-contract.py` | rc=0, `6 defined, 4 handled, 2 declared unhandled` | live run green |
| `sum(EXPECTED_MUTATIONS.values())`, imported | **1163** | matches the declared 1163 ✓ |
| per-file manifest lengths vs `EXPECTED_MUTATIONS`, all 40+ | **zero mismatches** | 11 and 14 both ✓ |
| anchor uniqueness, all 11 new entries | every anchor occurs **exactly once**; no replacement text already present | no ambiguous-anchor refusal |
| all 11 new entries through the harness's own `run_mutations` | **11 caught, 11 attributed, 0 survivors** | after the 11:13:25 manifest edit |
| …the same, before that edit | entry 7 **SURVIVED** | closed mid-review (below) |
| the AFTER-control after those 11 | **rc=1, NOT GREEN** | **B1** |
| entry 10 alone, fresh tree, then after-control | caught+attributed, then after-control red | **B1**, isolated |
| entry 11, clean tree vs after entry 10 | 1 red case vs **2** red cases | **B1**, contamination |
| B1's pid-scoped fix on a staged copy | 11/11 caught+attributed, after-control **green** | fix verified, not asserted |
| `_CORPUS` parsed by AST; old label predicate vs the equality | **5 of 11** vs **11 of 11** | the fold's central claim ✓ |
| `observe()` on the r7 B2 arm's source | returns the clean sentence; new guard returns `[5]` | the marker rewrite kept the arm discriminating |
| `observe()` on round 6 H1's missing-command arm | returns `"… Detail: \n"`, no refusal | **H2** |
| #201 reintroduced and declared | new guard `[]`; old predicate `True` | **H1** |
| `nag_once` ×3 same message, then a different one | `True, False, False, True` | **H3** |
| `RECALL_MATCHER` ambient → `check-rc-contract.py` | rc=1, false verdict naming the `*)` arm | **M2** |
| sibling unparseable / missing / `SystemExit(7)` / `SystemExit(0)` | rc 1 / 1 / 7 / **0 with no output** | **M3** |
| two `--self-test` runs, 6 stagger offsets | false RED at **2 of 6** | **M4** |
| `SIGKILL` at 13 offsets | debris at **3 of 13**; `.claude/hooks/` not gitignored | **M5** |
| `PYTHONVERBOSE=1` / `PYTHONWARNINGS=always` / `PYTHONDEVMODE=1` | rc **2** / 0 / 0 | **L1** |
| `${1:-…}` scratch hook, with and without argv | env var ignored; argv honoured | **M1** fix verified |
| `check-ratchet-contract.py` | rc=0, 43 guards, new file discovered | R1–R4 satisfied |
| `check-selftest-counts.py` | rc=0, 50 counts verified by running them | 36 and 54 mechanically pinned |
| `check-docs.py` | rc=0 | — |
| `.claude/settings.json` | only key is `hooks`; no `env` block | **M1**, the seam is unset |
| `HARNESS_TREE` | `('scripts','supabase','docs','node_modules/typescript','.claude/hooks','.github/workflows')` | `.claude/settings.json` not staged — the reason for the 11:09 fix |

**Repo hygiene — the question item 2 is about.** I wrote fixtures into `.claude/hooks/` three times
(`_r7review-probe.sh`, `_r7probe2.sh`, and `_selftest-marker-<pid>` files), each in a `try/finally`,
and I verified removal after every experiment: `ls .claude/hooks/ | grep -E "_selftest|_r7"` →
**none**, checked three separate times including last. `git status --short` is identical to the
session's opening snapshot apart from this review document. Every mutation experiment ran in
`…/scratchpad/{h2..h7,harness,tree}`, staged by the harness's own `stage_tree`; **no tracked file was
modified and no writing `git` command was run.**

---

## Closed mid-review

Recorded because they are evidence about this round, not about the final tree.

1. **The r7 B2 corpus case failed in the mutation harness's staged tree** (measured 11:08, before
   the 11:09:33 edit): the arm branched on `$REPO_ROOT/.claude/settings.json`, which `HARNESS_TREE`
   does **not** stage — *"It is `.claude/hooks`, not `.claude`"*, `check-plan-code.py:190-193`. The
   suite went **33/34** in a staged tree, so the control was red and all 11 entries were
   unmeasurable. Fixed at 11:09:33 by giving the fixture its own marker file; I re-verified **36/36
   with `.claude/settings.json` absent**. ⚠ The case that proved round 7 B2 was closed had itself
   reproduced B2's shape — a case whose outcome was a property of the environment.
2. **Manifest entry 7 survived** (measured 11:05, before the 11:13:25 edit): the envelope mutation
   `doc["…"]["…"]` → `doc.get("…", {}).get("…", "")` was unreachable, because the only probe fed
   **invalid** JSON (`echo "not json at all"`), so `json.loads` raised and the `except` branch still
   refused. Harness verdict: `caught=False`, `survivors=['malformed output is read as silence…']`.
   Fixed at 11:12:17 by adding a probe that feeds **valid** JSON lacking the envelope
   (`echo '{"other": 1}'`), which is exactly the missing case; re-verified caught and attributed.

---

## Could Not Establish

- **Whether the in-flight partial sweep has already observed B1.** I did not read any sweep output
  file; B1 is derived from the harness's own functions in my own staged trees.
- **Whether `SIGTERM`/`SIGINT` can leave debris.** Both ran `finally` at the one offset I tried
  (1.2s) and left nothing. The `finally` *should* cover them, so I expect no debris; I did not sweep
  offsets for them as I did for `SIGKILL`.
- **The "render comparison caught 3 of 11" figure.** I re-derived the label vocabulary's 5 and the
  equality's 11 over the file's own `_CORPUS`, but I did not reconstruct round 6's render-invariance
  rule faithfully enough to measure it, so I am not confirming or disputing the 3.
- **Whether any legitimate *shell* path in the hook writes to stderr.** I found an ambient-env path
  (L1) but no path arising from the hook's own logic; the hook's only uninsulated command is the
  `python3 -c` envelope line, whose stderr is a genuine failure.
- **Whether the six declared sentences are semantically wrong.** I judged rc 3 (H3). rc 5 and rc 6
  read correctly to me: each ends in a full stop, makes a whole claim, and promises nothing. I have
  no basis to dispute rc 0, 2 or 4.
- **Whether B1 is reachable in CI as well as locally.** `ci.yml` runs the two new
  `check-surface-recall` steps, not `--mutate .`; I did not establish which workflow invokes the
  full sweep.

---

## What I would do before merge

B1 is one line (pid-scope the two globs) and closes M4 with it — and it is the difference between a
1163-mutation ratchet that reports and one that reports NOT CHECKED. H1 is a handful of lines
reusing a predicate that already exists in `git history`, applied where it has no boundary to
escape. M1's argv seam is one line in the hook and one in the guard, and deletes M2. H2 is a
four-line copy of a clause already written 400 lines away. H3 is either a declaration change or a
corrected sentence; the sentence is wrong either way.

NOT CONVERGED
