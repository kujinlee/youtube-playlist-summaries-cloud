```yaml
round: 4
subject: decision-route-escalation
writer: claude
fixes_nontrivial: false
findings:
  - id: H1
    severity: High
    aim: instrument
    fix_induced: false
    component: transcript-reference-channel
    disposition: filed
  - id: H2
    severity: High
    aim: instrument
    fix_induced: false
    component: sweep-skip
    disposition: filed
  - id: H3
    severity: High
    aim: instrument
    fix_induced: true
    component: convergence-unreachable
    disposition: filed
  - id: M1
    severity: Medium
    aim: instrument
    fix_induced: false
    component: reference-scope
    disposition: filed
  - id: M2
    severity: Medium
    aim: instrument
    fix_induced: false
    component: transcript-reference-surface
    disposition: filed
  - id: M3
    severity: Medium
    aim: instrument
    fix_induced: false
    component: transcript-reference-baserate
    disposition: filed
  - id: L1
    severity: Low
    aim: instrument
    fix_induced: false
    component: reference-scope
    disposition: filed
  - id: L2
    severity: Low
    aim: instrument
    fix_induced: false
    component: reference-scope
    disposition: filed
```

# Adversarial review — `decision-route-escalation` r4 (CLAUDE half)

**Subject:** `git diff ea119c82..c8c3f226` — the implementation that followed rounds 1–3's design
document, reviewed by nobody until now (`check-review-recorded.py` exits 1 and names 17 files).

**Verdict: NOT CONVERGED.** Three High findings, all verified by execution, each one an instance of
a failure class this repository has already paid for by name:

| # | Severity | Finding | Class it belongs to |
|---|---|---|---|
| H1 | High | the new transcript guard's rc is discarded by its only caller, so **every** outcome — quiet, FIRED, CANNOT RUN, and an uncaught crash — produces hook `exit 0`, which the wrapper's own header defines as *"allows the stop silently"*; and every message is written to **stderr**, not the **stdout** its docstring argues for at length | `a-gates-channel-can-be-weaker-than-the-gate` — cited **by this docstring** as answered |
| H2 | High | `ci.yml:851`'s `\|\| true` makes *"the diff could not be taken"* indistinguishable from *"nothing changed"*, and `sweep_needed([])` is `False`, so the 1,641-mutation sweep is skipped while the step prints *"no scripts/ file changed"* and exits 0. The `None` arm written for exactly this condition is **unreachable from the only call site** | `unit-coverage-does-not-compose` — *mutate the CALL SITE* |
| H3 | High | `convergence_unreachable` re-derives `converged`'s clean-round rule **without** the `disposition` clause added in the same commit, so it reports `UNREACHABLE` — and demands evidence that is no longer the rule — for records `converged` already accepts | `a-second-implementation-of-one-rule-drifts` (17 prior instances) |

Negative results are in their own section at the end; six of the brief's claims held under attack,
including the whole of C6 (every anchor in all six manifests binds, and every `expect` names exactly
one real case).

---

## H1 — Blocking/High: the transcript guard cannot reach the actor it is addressed to

**Severity: High.**
**Files:** `.claude/hooks/block-idle-stop.sh:85` and `:170`; `scripts/check-transcript-references.py:50-54, 146, 156`.

### The claim under attack

`check-transcript-references.py:43-54` devotes a titled section to the channel question, and says it
answered it rather than assuming it:

> ⭐ HERE THE ANSWER INVERTS, AND THAT IS WHY **STDOUT** IS THE RIGHT CHANNEL. […] **The actor who
> must change is the ASSISTANT**, and hook stdout reaches exactly the assistant. The channel is
> matched to the actor rather than merely loud.

`block-idle-stop.sh:83` repeats it: *"The channel is hook stdout, which reaches the ASSISTANT."*

### What is actually true

Three facts, all executed:

**(a) It writes to stderr, never stdout.** Both prints in `run_decide` carry `file=sys.stderr`
(`:146` for CANNOT RUN, `:156` for a firing). There is no `print` to stdout anywhere in the module
outside `--self-test`.

**(b) Its rc is thrown away.** `block-idle-stop.sh:85` is

```bash
printf '%s' "$INPUT" | python3 "$REPO_ROOT/scripts/check-transcript-references.py" --decide || true
```

— no `RC=$?` capture — and the wrapper's exit-code collapsing rule at `:170` reads
`BANNER_RC`, `CI_RC`, `TABLE_RC`, `PROGRESS_RC` and **not** this guard. So a firing lands on
`exit 0`, which this very file's contract header (`:42`) defines as *"allows the stop **silently**"*,
with `exit 1` being the code documented as *"allows the stop, **shows stderr**"* (`:29`).

**(c) Verified by running the wrapper.** I copied `scripts/` and the hook into a scratch tree,
replaced the three observers whose rc *is* captured with `exit 0` stubs (in the **copy** — the
repository was not touched), and fed it a transcript whose completed turn carries two bare `#N`:

```
$ bash .claude/hooks/block-idle-stop.sh < payload.json > h3.out 2> h3.err
HOOK EXIT CODE = 0
--- stdout (       0 bytes) ---
--- stderr (     189 bytes) ---
⚠ [transcript-references] 2 bare reference(s) shown to the reader in the last turn — a number
alone does not say WHICH namespace: #378, #379 — write `backlog #N`, `PR #N`, `round N`.
--- log lines ---
       2
```

Zero bytes of stdout; the message on stderr; the hook exits **0**.

### Failure scenario

The assistant writes `#378` bare. The Stop hook fires. The guard detects it, logs it, and prints to
stderr. No other observer has anything to say, so the wrapper exits 0 — the code its own header
calls *silent*. The warning reaches nobody, and the nudge the guard exists for is never delivered.
The guard is audible **only when some unrelated observer independently fails**, forcing `exit 1`
(and `exit 1` shows stderr to the *human*, not to the assistant; only `exit 2` feeds stderr back to
Claude, and `:167` states as a design rule that the wrapper never surfaces a 2 on an observer's
behalf). So the actor the docstring names as the one who must change is the one actor the channel
structurally cannot reach.

This is reachable *today*: the very first time I ran the unmodified hook against the real
`scripts/` tree, `BANNER_RC` was 2 (`CANNOT RUN: … .claude/banner-turn-state`), which is why the
author could have watched the message arrive while developing it. Its audibility is an accident of
a sibling observer's state.

### And the "FAILS CLOSED ON ITS OWN BLINDNESS" claim is false of the composition

`check-transcript-references.py:63-66`:

> No transcript, an unreadable one, or a payload without `transcript_path` is CANNOT RUN (rc=2),
> never a quiet pass.

True of the script; false of the only thing that calls it. Executed, same copied tree:

```
$ echo '{"stop_hook_active": false}' | ... bash .claude/hooks/block-idle-stop.sh
CANNOT-RUN payload -> hook exit=0
stderr: [transcript-references] CANNOT RUN — the hook payload carries no `transcript_path`
```

And an uncaught crash is swallowed identically. I renamed `judged_window` to `judged_window_RENAMED`
in the **copy** — the shape of a vendor/owner API moving under it — and ran the hook on a *firing*
transcript:

```
A (nothing wrong):                  exit=0  stdout=0B  stderr=0B
B (guard CRASHED on a FIRING turn): exit=0  stdout=0B  stderr=1440B
   AttributeError: module 'check_banner_armed' has no attribute 'judged_window_RENAMED'
```

Both outcomes are `exit 0`. `|| true` plus the absent rc capture collapses four distinct states —
quiet, fired, cannot-run, crashed — into the one code the wrapper documents as silent.

### Why no gate caught it, measured

The call site has **zero** mutation coverage, and so does every other hook:

```
$ python3 -c "...count manifest entries whose file starts with .claude/..."
total hook-file mutation entries: 0
$ ls scripts/mutations/ | grep -i 'idle|stop'
(none named for block-idle-stop)
```

All five of the new `check-transcript-references.json` entries mutate the **callee**. The brief's own
instruction — *mutate the CALL SITE, not just the callee* — names this exactly.

### What would fix it

Capture the rc and add it to `:170`'s condition (warn-only is preserved: `exit 1` does not block),
and either print to stdout as the docstring says or change the docstring to say stderr. Pick one;
right now the code and three separate prose passages disagree.

---

## H2 — High: a failed `git diff` reads as "nothing changed" and silently disables the mutation sweep

**Severity: High.**
**File:** `.github/workflows/ci.yml:851` (the `mutated_code` step), with `scripts/check-plan-code.py:1717` (`sweep_needed`).

### The claim under attack (brief C1/C2)

`ci.yml:826-829`:

> ⛔ AND IT FAILS TOWARD RUNNING. If the base ref cannot be resolved the answer is `true`, because
> an undetermined diff must not silently skip a gate — "cannot run is a failure, never a pass"
> applies to the DECISION to skip just as much as to the sweep itself.

And `check-plan-code.py:1711-1713`:

> ⛔ `None` MEANS THE DIFF COULD NOT BE TAKEN, AND THAT RUNS THE SWEEP.

### What is actually true

The guarantee holds for the **rev-parse** failure the block explicitly tests, and fails for the
**diff** failure it swallows:

```bash
git diff --name-only "$BASE"...HEAD > /tmp/changed.txt || true     # ci.yml:851
```

`>` truncates the file before git runs, so on any git failure the file exists and is **empty**, and
`|| true` discards the error. The Python then reads `[]`, and:

```python
def sweep_needed(changed):          # check-plan-code.py:1717
    if changed is None: return True
    return any(path.startswith("scripts/") for path in changed if path.strip())
```

`sweep_needed([])` is `False` → `SKIP` → `changed=false` → the `if:` on the sweep step is false and
all eight shards are skipped, with the job green.

The `None` arm exists, has its own self-test case (`:5253`, *"⛔ a diff that could NOT be taken runs
the sweep rather than guessing"*) and presumably a manifest entry — and **nothing can reach it**:

```
$ grep -rn "sweep_needed" --include=*.py --include=*.yml .
scripts/check-plan-code.py:1717: def sweep_needed(...)
scripts/check-plan-code.py:5245-5256:  (seven self-test cases)
.github/workflows/ci.yml:859:  print("RUN" if mod.sweep_needed(changed) else "SKIP")
```

One non-test caller, and it can only ever pass a `list`. The protection is unit-tested on an arm the
composition does not use, while the composition routes the same condition to SKIP.

### Failure scenario, executed end to end

`git diff A...B` **does** fail — rc 128 — when the two refs have no merge base:

```
$ git diff --name-only orph...master
fatal: orph...master: no merge base
  rc=128
```

So I built that world with `scripts/check-docs.py` genuinely changed (the sweep *must* run), extracted
the step's `run:` block verbatim with `js-yaml` (no guessing at the block-scalar dedent), substituted
only the two `${{ }}` expressions, and ran it:

```
$ EVENT_NAME=pull_request BASE_REF=master bash block_run.sh
fatal: origin/master...HEAD: no merge base
no scripts/ file changed against origin/master — the sweep would mutate unchanged
code against unchanged suites, which can only reproduce the previous result.
  step rc=0
  >>> GITHUB_OUTPUT: changed=false
```

The step asserts a falsehood about the tree (`scripts/check-docs.py` *was* changed), reports
`changed=false`, and exits 0. The gate the whole branch's mutation coverage rests on is off, and the
log line reads like a healthy skip.

**Reachability, stated honestly.** `actions/checkout@v4` runs with `fetch-depth: 0` in this job (I
read the parsed YAML), which rules out the shallow-clone merge-base failure. What remains: a base
branch whose history was rewritten/force-pushed out from under the PR, a PR across unrelated
histories, and git erroring for environmental reasons (corrupt pack, ENOMEM). Narrow, but these are
exactly the conditions under which someone most wants the sweep to have run — and the failure is
*silent and green*, which is the property that makes it High rather than Low.

I also enumerated the other arms, and they do fail toward running:

| state | result | verified |
|---|---|---|
| `HEAD^` / `origin/<base_ref>` unresolvable | `changed=true` | by reading the explicit branch; the self-test's own case |
| docs-only change, push | `changed=false` | ✅ ran it |
| `scripts/` change, push | `changed=true` | ✅ ran it |
| python raises (import failure, missing `/tmp/changed.txt`) | non-zero → `ERROR` → `*)` → `changed=true` | ✅ reasoned + the `|| echo "ERROR"` is inside the substitution |
| **git diff fails, file truncated to empty** | **`changed=false`** | ✅ ran it |

### What would fix it

One line — read git's status instead of discarding it:

```bash
if ! git diff --name-only "$BASE"...HEAD > /tmp/changed.txt; then
  echo "changed=true" >> "$GITHUB_OUTPUT"; exit 0
fi
```

or delete `/tmp/changed.txt` first and let the Python's `FileNotFoundError` take the `ERROR` path —
which is already correct. Either way, the `None` arm then needs a caller or a `NO-CALLER:` reason.

---

## H3 — High: `convergence_unreachable` drifted from `converged` in the commit that created it

**Severity: High.** **Fix-induced: yes** (both halves were written by backlog #329 in `c8c3f226`).
**File:** `scripts/check-review-decision.py:263-290`, called from `:348`.

### The claim under attack (brief C5)

`converged` (`:248`) now skips a finding whose `disposition` is `fixed` or `declined` — "reads the
record that exists". `convergence_unreachable` (`:277-281`) computes "is any round clean?" with the
**old** rule:

```python
clean = [r for r in rounds
         if not r.get("fixes_nontrivial")
         and not any(f.get("severity") in ("Blocking", "High")
                     or f.get("aim") == "deliverable"
                     for f in r.get("findings", []))]
```

No `disposition` clause. Two implementations of one predicate, 30 lines apart, in one commit.

### Failure scenario, executed

One round, one `Blocking`/`deliverable` finding with `disposition: fixed`, `fixes_nontrivial: false`:

```
$ python3 (importing the module, calling both predicates)
converged([r1 only], one-round) -> (True, '1 round(s) with every Blocking/High and every
                                    deliverable finding dispositioned, and trivial fixes')
convergence_unreachable([r1 only]) -> no round recorded for this subject is clean, so convergence
                                      is UNREACHABLE from this record, not merely unmet: it needs
                                      rounds with no Blocking/High, nothing aimed at the
                                      deliverable, and fixes_nontrivial false
```

The same record, in the same module, at the same moment: **converged** and **UNREACHABLE**.

It escapes to a reader through `decide`. Two rounds, r1's Blocking `fixed`, r2's `filed`, scope
`full-loop`:

```
decide -> ROUND_OWED
reason -> r2's Blocking is still open (disposition 'filed') — ⚠ no round recorded for this subject
          is clean, so convergence is UNREACHABLE from this record, not merely unmet: it needs
          rounds with no Blocking/High, nothing aimed at the deliverable, and fixes_nontrivial
          false. ⚠ A round that found nothing still has to be RECORDED (`findings: []`) to count
```

Everything after the em-dash is false. Convergence is one `filed` → `fixed` away; it does not need a
round with "no Blocking/High" (that is precisely the demand #329 removed); and it does not need a
round that "found nothing" (the artifact #329 established the workflow never produces). The whole
purpose of this function per its own docstring is that *"a gate that cannot be reached, and does not
say what would reach it, reads as a verdict about the work when it is a verdict about the record"* —
and it now misdirects the reader toward the unreachable evidence the same commit abolished.

### Why its cases cannot catch it

`:781-791` has six new cases. The clean-round positive uses `two_inst` — findings aimed at
`instrument`, so neither severity nor aim triggers, and `disposition` is never varied. The negatives
use `deliv`/`high`, also without a disposition. **No case in the suite constructs a round whose only
finding is a dispositioned Blocking** — the one input that distinguishes the two predicates. The
case that would redden: `convergence_unreachable([_R(1, [dict(high, disposition="fixed")])]) is None`.

### What would fix it

`convergence_unreachable` should ask `converged` (or a shared `_is_clean(round)` helper) rather than
restate it, and its remedy sentence should name the evidence `converged` now wants: *findings
dispositioned `fixed`/`declined`, and `fixes_nontrivial` false*.

---

## M1 — Medium: C3, the surface list is incomplete — `docs/review-method.md` is in neither list

**Severity: Medium.** **File:** `scripts/check-reference-namespace.py:90-106` (`SCOPE`).

`docs/review-method.md` is **not** in `SCOPE`, and — unlike every other exclusion, each of which the
docstring names with a reason — it is **not** in the "⛔ OUT OF SCOPE BY CONSTRUCTION" list either.
It is excluded by the same OMISSION that `check-transcript-references.py:9-13` identifies as the
defect it exists to close.

It is unambiguously a reader-facing spine document: `docs/dev-process.md:12` names it in the
read-trigger table (*"a review round is starting — adversarial review, convergence, the
classification passes"*), and `:122` cites it as the owner of the thrashing measurement.

**Measured hole.** I ran the guard's own predicates (`BARE`, `QUALIFIER`, `in_inline_code`,
`in_scope`) over `git diff --unified=0 HEAD~40 HEAD` and bucketed every firing:

```
last 40 commits, firings by bucket:
  IN SCOPE (would fire):              0
  excluded by a STATED decision:      185
  ⚠ NEITHER in scope NOR stated-out:  4
          3  docs/review-method.md
          1  .github/workflows/ci.yml
```

The three in `review-method.md`:

```
  #136  ::  | **REDESIGN** | restructure it | the unit still carried findings after a restructuring…
  #56   ::  switched off (#56). The triggers, their observations and their verdicts are declared…
  #314  ::  what #314 says a hindsight label cannot be.
```

All three are genuine cross-namespace references, not ordinals.

**The sharpest evidence is in this branch's own untracked log.** `.claude/transcript-reference-warnings.log`
line 3 — a firing the new guard recorded during the session that built it:

> ``review-method.md:461` labels them *"backlog #296, #297"* — but **no backlog rows 296/297 exist,
> while PR #296 and PR #297 are both merged**`

Confirmed on disk (`docs/review-method.md:461,465,466,476,484`). So the exact ambiguity class this
guard was widened to catch was found **by hand, in `review-method.md`, in this session** — and that
file is still outside the file guard's scope. A surface that produced the motivating defect and is in
neither list is the same defect wearing a fix.

---

## M2 — Medium: C4, a reachable false negative on the highest-attention human surface

**Severity: Medium.** **File:** `scripts/check-transcript-references.py:130` → `check-banner-armed.py:468-475` (`_text_blocks`).

`texts_of` keeps only content blocks with `type == "text"`. A bare `#N` the human reads inside a
**tool input** is invisible — and the highest-stakes such surface is `AskUserQuestion`, the blocking
selection card the user must read to answer.

Measured over the 40 most recent transcripts for this project, using the guard's own
`bare_references`:

```
bare `#N` the guard CANNOT see, in human-facing TOOL INPUTS: 13
 by tool: {'AskUserQuestion': 13}
  AskUserQuestion #327 | {"questions": [{"question": "The decision mechanism (#327) is blocked on
                          your call. Given that its two signals turned ou…
  AskUserQuestion #328 | …
  AskUserQuestion #329 | …
  AskUserQuestion #321 | …
```

The owner's stated complaint is *"when I see bare `#N`, it is confusing to me"*, and the docstring
records that they *"had already had to ask twice in one session which namespace a number belonged
to"*. A selection card is exactly where that question is most expensive, and it is the one surface
the reader cannot scroll past. `0 of 13` are reported.

This is a bounded, cheap fix (extend `texts_of`, or read `tool_use` inputs for a named set of
human-facing tools) and it is not covered by any stated exclusion — the docstring's blindness
section lists only the one-turn latency and the warning channel.

---

## M3 — Medium: C4, the base rate — 52.7% of turns fire, and the ordinal class is not absent

**Severity: Medium.** **File:** `scripts/check-transcript-references.py:15-28`.

### Base rate

The brief's through-line is *"what does this return when nothing is wrong?"*. Measured over the 40
most recent transcripts, judging every completed judgable window exactly as the guard does:

```
transcripts=40 sidechain_records=0
judgable completed turns=148  turns that FIRE=78  (52.7%)
total findings=351   distinct tokens=59
most common: #378×65  #379×43  #322×22  #136×20  #328×17  #329×13  #321×10  #56×10 …
```

I classified a random sample of 30 and the large majority are genuine bare cross-namespace
references, so this is substantially a **violation** rate rather than a false-positive rate — the
same defence `check-reference-namespace.py:53-55` makes for its own 2.00/commit. But that defence
rests on a mechanism this guard does not have: *"since only ADDED lines are read it falls as soon as
it is enforced rather than accumulating."* The transcript guard re-judges every turn from scratch and
cannot prevent a first occurrence (its own documented latency). Combined with **H1**, the only
channel is silent, so the rate cannot fall and cannot be observed falling. Fixing H1 makes this
measurable; until then "52.7% of turns" is what the nudge would land on, and a warning on every
other turn is the cry-wolf shape the file explicitly says it must not ship.

### The ordinal class is present, not absent

`:26-28` states the load-bearing argument for inverting the 2026-08-27 verdict on this surface:

> Prose written to a human contains almost none of those: the first five firings in the measured
> sample were `#321 #323 #324 #325`, every one a real cross-namespace reference. The false-positive
> population that killed the idea for documents is largely absent here.

That is an argument from five. Over 351 firings, **16 (4.6%) are review-finding or list ordinals** —
the exact class:

```
low-numbered tokens (<=20): #4×4  #8×3  #1×3  #3×2  #6×2  #2×1  #7×1   (16 total)
  #2  | Three distinct issues, and **#2 is a real regression from my `ci.yml` edit**…
  #8  | Codex #8 confirmed by direct measurement: the pull ref is now `2e0ad1ef`…
  #3  | Codex #3 confirmed exactly. My "161 triggered / 2 trigger-less" measured the wrong…
  #1  | | r2 Codex #1 | banning the literal total still lets `1,007` through…
  #4  | > *r2 CODEX #4's fix for the CRLF under-count — the round-2 repair became the round-3…
```

One of them is already in the **live** log (`{"token": "#2", "line": "Three distinct issues, and
**#2 is a real regression from my `ci.yml` edit**…"}`), i.e. 1 of the 9 real firings to date is a
false positive — not the zero the prose implies. The honest bound is *"16 ordinal false positives in
351 firings over 40 transcripts (4.6%)"*, and the vocabulary fix is one word (`codex`, as
`deliverable` was), not a notch.

Also worth recording: the `fenced code block` worry does **not** materialise — only 2 of 351 firings
sit inside a ``` fence, and both are legitimately bare (`pull request : #378`). That attack held.

---

## L1 — Low: the docstring lists `docs/roadmap-to-launch.md` as both in and out of scope

**File:** `scripts/check-reference-namespace.py:49` vs `:63`.

Fourteen lines apart in one docstring:

```
:49   * ⟳ `docs/backlog.md` and `docs/roadmap-to-launch.md` are now IN SCOPE (2026-10-20).
…
:62-63  * `scripts/**`, `docs/memory/**`, `docs/superpowers/**`, `docs/explainers/**`, `docs/adr/**`,
          `docs/roadmap-to-launch.md` -- measured above, or read by someone already in context.
```

The code is right (`SCOPE` includes it at `:105`, and the self-test pins it at `:276`); the second
list was not updated when the first was. In a guard whose entire subject is *"a reference a reader
has to guess at"*, a docstring that contradicts itself about its own scope is the same defect
one level up. One-line deletion.

## L2 — Low: `in_scope` matches file entries by prefix, so sibling paths are swept in

**File:** `scripts/check-reference-namespace.py:144.**

```python
return any(path == s or path.startswith(s) for s in scope if s)
```

`startswith` is needed for the two directory entries (`.agents/skills/`, `.claude/hooks/`) but is
applied to the twelve file entries too. Verified:

```
  in_scope('docs/backlog.md.bak')    = True
  in_scope('CLAUDE.md.orig')         = True
  in_scope('docs/backlog.md~')       = True
  in_scope('docs/dev-process.md.rej')= True
  violations(_d('docs/backlog.md.bak','see #291')) ->
      ['docs/backlog.md.bak: bare `#291` with no namespace — …']
```

Low because it fails toward a **firing**, which `:113-115` names as the safe direction, and because
such files are rarely tracked. The clean form is to end directory entries with `/` and test
`path == s or (s.endswith("/") and path.startswith(s))`.

---

## NEGATIVE RESULTS — claims I attacked that held, with the input I used

1. **C6, anchor binding — HELD, both directions.** Every `edits[*][0]` in all six changed manifests
   (`check-decision-scheme`, `check-plan-code`, `check-reference-namespace`, `check-review-decision`,
   `check-review-rounds`, `check-transcript-references`) occurs **exactly once** in its delivered
   file: `ANCHOR/EXPECT problems: 0` over 219 entries. And every `expect` string equals exactly one
   real case name — harvested from the AST (`ast.Constant` first arguments of `case`/`check`, which
   handles implicit string concatenation correctly, where a naive substring test gave 11 false
   alarms): `TOTAL expect problems: 0`. Independently cross-checked for `check-review-rounds` against
   the 87 case names its suite actually **prints** (`✓ …` lines): 0 mismatches.

2. **C6, kills — HELD on everything new.** Scoped mutation run on a copied `scripts/` tree (control
   green first: `18/18 passed`, `26/26 passed`), each mutation applied to the copy and reverted:

   ```
   check-transcript-references  [0..4] rc=1 caught=True attributed=True   (all five new entries)
   check-reference-namespace    [6] [7] [8] rc=1 caught=True attributed=True   (the three new entries)
   ```
   Every one reddens via the case it names.

3. **C1, `sweep_needed`'s own cases — HELD.** Called at inputs of my own choosing, not its fixtures':
   `["scripts/check-docs.py","docs/backlog.md"]`→True, `["scripts/mutations/x.json"]`→True,
   `["docs/explainers/about-scripts/x.md"]`→False, `["","  "]`→False, `None`→True. The predicate is
   correct; the defect (H2) is entirely at the call site.

4. **C2, the YAML block scalar — HELD.** Extracted with `node -e` + `js-yaml` and executed: the
   heredoc body and the `PYEOF` terminator both dedent to column 0, the `|| echo "ERROR"` sits
   inside the command substitution so a python failure does reach the `*)` arm, and both happy paths
   produce the right answer (`changed=false` docs-only, `changed=true` on a `scripts/` change). The
   step-level `if:` is on the sweep step only, so the job still reports and the check stays
   requireable (backlog #137's distinction is respected).

5. **C3, dead entries — HELD.** All 14 `SCOPE` entries resolve to tracked files (`.agents/skills/`
   → 43 files, `.claude/hooks/` → 14 files, the other twelve each tracked). No listed surface is
   unreachable by the walker; the gap is an absent entry (M1), not an inert one.

6. **C4, CANNOT RUN and the reader's subtleties — HELD at the script level.** `judge("{}")`→2,
   `judge("not json")`→2, `judge({"transcript_path":"/nonexistent"})`→2, a session with only a live
   turn→0 (NO SUBJECT, distinct from CANNOT RUN). Thinking blocks are **not** judged (`_text_blocks`
   filters `type == "text"`), and `isSidechain` records are genuinely absent — I re-measured the
   inherited claim rather than trusting it: **0 sidechain records across the 40 transcripts**, so
   subagent prose is not being judged as the main session's.

7. **C5, disposition validation — HELD.** `disposition` is enum-constrained at `:431`
   (`{"fixed","filed","declined"}`), so `parse_header` refuses a typo. And the predicate fails safe
   on near-misses: `"Fixed"`, `"FIXED"`, `"fixed "`, `"fixed\n"`, `"resolved"`, `"wontfix"` and an
   absent field all leave the finding **open** → refuses convergence. No casing/whitespace hole.

8. **C4/#328, one rule one place — HELD.** `check-decision-scheme.py` really does delegate: both
   `_round_docs` (`:458`) and `_corpus_now` (`:820`) call `mod.corpus(reviews)` from
   `check-review-rounds.py` and propagate its refusal (`raise ValueError(why)` / `raise OSError(why)`
   → rc 2). The duplicate `rglob` walk is gone, not merely documented as gone.

9. **The hook is wired.** `check-transcript-references.py` is genuinely invoked:
   `.claude/settings.json` → `Stop` → `bash .claude/hooks/block-idle-stop.sh` → `:85`. Not a
   declaration-without-the-act. (What it cannot do once invoked is H1.)

10. **Entry points on the real tree.** `check-reference-namespace` rc=0 (*"no bare `#N` added in 14
    reader-facing surface(s)"*), `check-fixture-variation` rc=0 (946 parameters across 70 files),
    `check-selftest-counts` rc=0 (56 scripts, every declared count verified by running it),
    `check-review-rounds --self-test` 87/87. `check-merge-ready` rc=2 CANNOT RUN (no PR for this
    branch — correct, loud). `check-decision-scheme`'s red entry point is the brief's documented
    by-design trigger 1 and is not filed.

11. **An observation, not a finding.** On this branch `check-review-decision` returns
    `ARCHITECTURE_REVIEW — thrashing` *before* `converged` is consulted, so **none of the #329 code
    this commit added executes on the branch that added it**. H3 was found by driving the predicates
    directly, which is the only way it could have been found.

---

## Verdict

**NOT CONVERGED.**

The justification is specific, not atmospheric. **H1** means the 302-line guard this branch's
headline change delivers cannot reach the actor its own docstring identifies as the one who must
act, and its CANNOT-RUN contract is void at the only call site — verified by running the wrapper and
reading `exit 0` with 0 bytes of stdout. **H2** means a `git diff` failure disables the entire
1,641-mutation gate while the step prints the opposite and exits green — verified end to end in a
world where `scripts/` genuinely changed. **H3** means the refusal reason this branch added to the
convergence decision is false for the records the same commit made convergeable — verified by calling
both predicates on one record and getting `converged=True` and `UNREACHABLE` simultaneously.

**What would make it CONVERGED:** H1 fixed by capturing the guard's rc into
`block-idle-stop.sh:170` and reconciling stdout-vs-stderr in one direction, with a mutation entry on
the hook line (the population currently has zero); H2 fixed by reading `git diff`'s exit status at
`ci.yml:851` (and then giving `sweep_needed(None)` a caller or a written `NO-CALLER:` reason); H3
fixed by having `convergence_unreachable` call the clean-round rule instead of restating it, plus the
one case that distinguishes them (`convergence_unreachable([round with a fixed Blocking]) is None`).
M1 is a two-line `SCOPE` addition. M2 and M3 are honest-bound corrections plus one vocabulary word,
and could legitimately be filed to the backlog rather than fixed on this branch — but M3's claim
*"the false-positive population … is largely absent here"* should not ship as written, because it is
the whole argument for inverting a measured verdict and it is contradicted by the guard's own log.

### REVIEW GAP
None. Every finding above was produced by execution; nothing in this document is UNVERIFIED. All
mutation runs, hook runs and workflow-block runs were performed on copies under
`$SCRATCH/claude-half/`; the repository working tree was not written to.
