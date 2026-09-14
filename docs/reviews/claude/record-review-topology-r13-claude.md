# record-review-topology — round 13, Claude half

Subject: worktree `/Users/kujinlee/code/agentic-ai-docs/.yps-worktrees/review-topology`, branch
`record-review-topology`, HEAD `dc9fe107` **plus the uncommitted delta**, which is the shipping
state. All execution was done in isolated `cp -R` copies with the `.git` pointer file deleted and
asserted gone (`git rev-parse` inside each returns *not a git repository*). No `GIT_DIR`,
`GIT_WORK_TREE`, `GIT_COMMON_DIR` or `GIT_INDEX_FILE` was ever set or exported. No mutating git ran
anywhere; every git call against the worktree was `show` / `diff` / `log` / `merge-base`. Nothing was
written under `docs/reviews/`.

**The r12 repair is correct, and I verified it by execution rather than by reading: all 79 of
`codex-review.py`'s case names — including the 17 `classify` cases that were the subject of r12's
High — now round-trip exactly through the real printer into the real `parse_fail_names`, with zero
mismatches and zero duplicates.** The r12 class sweep's conclusion also holds; I re-derived it by
forcing every `[FAIL]` printer in all 44 manifest targets red and parsing the real output, and found
no second broken printer anywhere.

**The defect I found is that the repair cannot fail.** Reverting `:907` to the exact broken shape r12
filed leaves the entire 618-mutation gate green — `618 killed, 618 attributed, 0 survivors`, rc=0.
This file has now shipped that same contract break twice; a third time would be equally silent.

---

## Blocking

None.

---

## High

### H1 — the round-12 repair has **no falsifier**: the full `--mutate .` gate passes with `:907` reverted to the broken shape, so the identical regression can recur silently a third time

**Claim.** Not one of the nine `scripts/mutations/codex-review.json` entries exercises the `:907`
printer. All nine name `chk` cases. So the r12 fix — the whole subject of the round — is invisible to
the only mechanism that measures this file, and reverting it is undetectable.

**Evidence (derivation).** The two printers and the population each serves:

`scripts/codex-review.py:916` — the repaired printer, serving the 17 `classify` cases:
```python
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}: got {got!r} want {want!r} ({reason})")
```
`scripts/codex-review.py:936` — `chk`'s printer, serving 62 cases (repaired at r11).

Partitioning every `expect` in the manifest against the two authored case-name sets:

```
classify-printer (:916) cases: 17   chk-printer (:936) cases: 62
manifest entries by which printer their expect belongs to: {'classify': 0, 'chk': 9, '???': 0}

=> entries exercising the :916 printer: 0
```

**Evidence (execution — this is the claim that matters).** Reverting only that one line to the shape
r12 filed as a High, in an isolated copy, and running the real gate:

```
$ # revert :907/:916 to  print(f"  [{'PASS' if ok else 'FAIL'}] {name}: got={got} ({reason})")
$ python3 scripts/codex-review.py --self-test | tail -2
79/79 passed

$ python3 scripts/check-plan-code.py --mutate .
OK — delivered scripts mutated: 44 file(s), 618 mutation(s), 618 killed, 618 attributed to the
case each names, 0 survivor(s)
RC=0
```

And the targeted control/experiment pair over the nine entries alone, through the real
`load_manifests` + `run_suite` + `run_mutations`:

```
entries for codex-review.py: 9 | load problems: none

--- CONTROL (shipping :916) ---
  control green: True
  ok: True | killed: 9 | attributed: 9 of 9
  report: none

--- REVERTED :916 to got={got} ---
  control green: True
  ok: True | killed: 9 | attributed: 9 of 9
  report: none
```

Byte-identical verdicts. The gate cannot distinguish the repaired file from the broken one.

**Concrete failure scenario.** Someone reformats that print line — to add a field, to shorten it, to
make the two printers consistent, or by reverting a merge hunk. `--self-test` stays 79/79 (the line
is cosmetic to the suite), `--mutate .` stays 618/618, CI stays green, and all 17 `classify` cases —
the half that decides whether an adversarial review gate RAN — go silently unattributable again. That
is exactly how the `chk` break survived until r11 and how the `:907` break survived until r12: *"it
went unnoticed because nothing had tried"*, in the file's own comment at `:927-935`. The comment
records the cause and the repair does not remove it.

**Why this is High and not a Medium.** The shipping behaviour is correct — I am not claiming a live
break. I am claiming the branch shipped a repair for a Blocking-class contract defect with no
regression signal, in the file where that contract has broken twice, on a branch whose thesis is that
a guard must be falsifiable. `scripts/check-ratchet-contract.py` exists to enforce precisely the
analogous property one level up (*every guard has a `--self-test`, a caller, and no fail-open*), and
`docs/dev-process.md` states the standard as *"State the observation that would make it FAIL."* There
is no such observation for this fix. r12's own Claude half saw the fact — *"The nine entries shipped
today all target `chk` cases, so this is latent"* — and used it to argue H1's severity rather than
filing it, so it is not on the do-not-refile list.

**This is NOT the abandoned static pre-flight** (`check-plan-code.py:3088-3136`), which I am not
re-proposing. The fix is one manifest entry inside the mechanism that already exists:

```json
{ "name": "the classify printer stops naming its case, so the whole classify half goes unattributable",
  "file": "scripts/codex-review.py",
  "edits": [["{name}: got {got!r} want {want!r} ({reason})", "{name}: got={got} ({reason})"]],
  "expect": "successful review" }
```
plus `EXPECTED_MUTATIONS["scripts/codex-review.py"]` 9 → 10. Checked before proposing it: the anchor
occurs **exactly once** in `codex-review.py` (so L1's hazard does not apply to it), `successful
review` is one of the 17 `classify` cases, and it is **not** a substring of any other case name (so
`w == f` resolves to exactly one). Under the mutation that `expect` matches 0 red cases, so
`run_mutations` reds with the report-format message at `check-plan-code.py:1289-1295`.

---

## Medium

### M1 — the r13 comment at `check-plan-code.py:966-972` — the delta's **only** change to that file — states a mechanism that does not exist, and 30 live entries prove it cannot exist

**Claim.** The comment repairs r12's Low by re-attributing the property to a rule that does not carry
it. Nothing anywhere refuses two entries that name the same case.

**Evidence.** `scripts/check-plan-code.py:970-972`:

```
            # anchor to a different substring of the same line, which is exactly what r11's repair
            # did (legitimately — both halves of `tail_candidates` are genuinely different
            # behaviours, verified by attribution). "It measures nothing new" is really carried by
            # the exact-`expect` rule below: a duplicate-in-substance entry names the same case and
            # is refused there. Stated so this rule is not read as doing work it does not do.
```

The exact-`expect` rule is `scripts/check-plan-code.py:1261-1262`:
```python
        unnamed = [(w, [f for f in fails if w == f]) for w in wants]
        unnamed = [(w, m) for w, m in unnamed if len(m) != 1]
```
It is evaluated **per mutation**, inside the per-entry loop. Two entries whose `expect` is the same
string are each evaluated independently, each matches exactly one red case, and each is attributed.
There is no cross-entry comparison of `expect` at either layer — `load_manifests` tracks only
`seen_names` and `seen_anchors` (`:952`, `:961`, `:973`).

**Verified by execution**, both layers, with two entries that are duplicates in substance — different
names, different non-overlapping anchors on the *same* line, identical `expect`:

```
run_mutations ok      : True
report lines          : NONE — nothing was refused
attributed per entry  : [('entry A — th', True), ('entry B — a ', True)]

load_manifests entries: 2
load_manifests problems: NONE — duplicate `expect` is not refused
```

**And the rule the comment describes could not be added, which makes the claim doubly wrong.**
Sharing an `expect` is legitimate and common — several distinct mutations can each be caught by one
case. Measured across the shipping manifests:

```
begin-plan.json           x2  'the refused tick leaves the plan BYTE-IDENTICAL on disk'
check-fixture-variation   x4  'main() surfaces a dead exemption as a failure'   (+3 more pairs)
check-plan-code.json      x7  'every phase of --mutate reports its position when a caller asks'
                          x2  'the caller is told once per mutation, with the running position'  (+8 more)
check-review-rounds.json  x2  'malformed and field-less verdicts are reported, not skipped'
gen-dashboard.json        x4  'every --out / --fragment-only path the suite PASSES is absolute'  (+2 more)
page_markup.json          x2  'url: bare scheme after a cut is not a link'

total entries: 618; manifests with a duplicated expect-set: 6
```

A rule refusing duplicate `expect` would red six manifests today. So the property the comment
attributes to the exact-`expect` rule is one the design deliberately does not have.

**Concrete failure scenario.** The comment's stated purpose is *"so this rule is not read as doing
work it does not do."* A future reviewer asking "is coverage inflation by duplicate entries caught?"
reads this comment, believes the answer is yes, and does not look. That is the branch's signature
pattern — a comment asserting a property the code lacks — landed in the repair for the finding about
a comment asserting a property the code lacks. The honest sentence is that **nothing** catches a
duplicate-in-substance entry; `EXPECTED_MUTATIONS` keeps the count and the duplicate-name and
duplicate-anchor rules catch only the two literal forms.

**Severity.** Medium, not High: no behaviour changes, the AST of the file is unchanged (proved
below), and the gate is neither weakened nor strengthened. It is a false statement in the one place a
future maintainer will consult.

### M2 — this branch moved `codex-review.py`'s case count 63 → 79 and left `docs/plugins.md:185` declaring **63**, inside the sentence that claims a gate now prevents exactly this drift

**Claim.** The prose copy of the count was *correct at the merge-base* and is wrong now because of
this branch. `docs/plugins.md` is imported by `CLAUDE.md`, so it is loaded into every session.

**Evidence.** `docs/plugins.md:185`:

```
never stdout text. Run `--self-test` (63 cases) after touching it. ⟳ 2026-09-04: this said **35**
while the suite ran **51** — measured, not noticed, for an unknown span. `codex-review.py` now
declares its count in the canonical form and is pinned in `check-selftest-counts.POPULATION`, so
the next drift fails a gate instead of sitting in prose.
```

Attribution, by read-only git against the merge-base `31fc8a72`:

```
=== scripts/codex-review.py ===
  merge-base docstring: --self-test  # 63 cases
  branch-HEAD+dirty   : --self-test  # 79 cases
```

and the branch *did* edit `docs/plugins.md` — one line, the Code Review section — without touching
the number. The suite runs 79 (measured). No gate observes the prose: `check-selftest-counts.py`
reads only `scripts/*.py` (`:72`, `:258`), and `docs/plugins.md` appears in it solely inside a
comment at `:126` describing this very failure (*"docs/plugins.md claimed 35 while the suite ran
51"*). Both `check-docs.py` and `check-selftest-counts.py` are **rc=0** on this tree, so nothing is
red.

**Concrete failure scenario.** The sentence promises *"the next drift fails a gate instead of sitting
in prose"*, and the next drift is sitting in prose in that sentence. A reader who trusts it stops
checking. Note this is a distinct defect from the known limit recorded in the r12 adjudication
(`check-selftest-counts.py` cannot see a self-authored inflation *inside* the script) — this is an
external second copy, which the pin was explicitly claimed to have solved.

**Pre-existing, NOT this branch, reported so the fix can be batched:** three more prose counts in
`docs/dev-process.md` are stale, all already stale at the merge-base —
`check-ratchet-contract` declares 21 / runs 41 (`:146`), `check-review-rounds` declares 27 / runs 29
(`:151`), `check-plan-file-tags` declares 21 / runs 44 (`:159`). Only the `plugins.md` 63 is this
branch's doing.

---

## Low

### L1 — the harness never checks that a mutation anchor is **unique** in its target, while the duplicate-anchor rule actively pressures authors toward shorter anchors

`scripts/check-plan-code.py:1190-1196` tests membership and then replaces the first occurrence:

```python
            if find not in src:
                ...
            src = src.replace(find, repl, 1)
```

`load_manifests` refuses a repeated anchor *tuple* (`:973`), so the r11 repair legitimately shortened
two anchors into disjoint substrings of one line — `"(set(after) | set(reviewed))"` and
`" & set(branch_delta))"` — and the r13 delta narrows two more in `codex-review.json`
(`f"{parts[1]} {parts[3]}"`). Shorter anchors are likelier to be non-unique, and a non-unique anchor
mutates a site the entry does not name while still reporting `attributed: True`.

**Measured, and it is clean today:** every one of the 618 anchors occurs exactly once in its target.

```
--- scan done ---     (0 anchors with count != 1, across all 44 manifests)
```

So this is latent, not live. Cost to close is one `src.count(find) != 1` refusal in `load_manifests`
with the existing message style. I am flagging the direction of pressure, not asking for a round.

---

## What I verified by execution, and what I only read

**Everything in the findings above was executed.** Full coverage:

| Question (brief) | How answered | Result |
|---|---|---|
| **1.** Can any `classify()` `reason` contain `": got "`? | Enumerated all 7 reason producers, then **executed** all 17 cases through the real printer (`OUT` is a fixed literal at `:903`, so every reason is deterministic) | **No.** All 17 parse to their exact authored name |
| **1.** Does any case NAME contain `": got "`? | AST-extracted all 79 authored names | **No**, zero |
| **1.** Is the trailing `({reason})` safe? | Forced all 79 red, ran the real suite, parsed with the real `parse_fail_names` | **Yes.** 79 parsed, **0** mismatches against the authored set, **0** authored names never parsed, **0** duplicates — so `w == f` and `len(m) == 1` hold for every case in the file |
| **1.** Is debugging information lost with `expected {want}` removed? | Read the delta | **No** — `want` moved onto the same line, `got` is now a repr rather than a bare str, `reason` retained |
| **2.** Is 79 right? | Independent AST count, not the printed tally: `len(cases)` = **17**, `chk` call sites = **62**, sum **79**; runtime prints 79/79 | **Yes** |
| **2.** Assertions that print nothing / silently skipped paths? | AST-checked every `chk` call for an enclosing `If`/`For`/`While`/`Try` | **None** — all 62 are unconditional; the only `return` before the total is inside the nested `_git` helper |
| **2.** Is `failures` incremented anywhere but the two printers? | grep over the file | **No** — `:918` and `:938` only |
| **2.** Does `check-selftest-counts.py` agree, and is the agreement meaningful? | Ran it | Agrees (38 scripts verified). **Circular for inflation** (known limit, not re-filed) but **not** circular here: I derived 79 from the AST independently and it matches |
| **3. THE CLASS — re-derived, not spot-checked** | Built an execution sweep: AST-force every one-sided `[FAIL]` branch in each target, run via the harness's own `run_suite` (same `child_env` HOME redirect and timeout), parse with the real `parse_fail_names` | **44/44 targets swept. Zero broken printers.** Incl. the assembled markers (`check-handoff-path.py` 10/10, `check-storage-grant-pin.py` 6/6), append-then-print (`page_markup.py` 74/74), `coverage_verdict.py` 18/18, continuation-line (`check-ratchet-contract.py` 41/41), comma variants, name-only |
| **3.** Could an `expect` have been written to match a *garbled* name (attribution passing over a broken printer)? | Scanned all 649 `expect` values for `": got "`, `"got="`, `" want "`, `"expected "` | **0 contaminated** — so 618/618 attribution is genuine evidence, not self-fulfilling |
| **4. Regression** | **AST comparison against HEAD**, not a diff reading | `check-plan-code.py`: whole-module AST **identical** → the change is provably comment-only. `codex-review.py`: exactly two module-body statements differ — the docstring (`92` → `79`) and `self_test`. The 17-entry `cases` list is AST-identical; `classify`, `reviewed_state`, `unredirected`, `verdict_record`, `tail_candidates`, `classify_verdict`, `second_question` and all 12 module-level constants untouched |

### Suites and gates run on the shipping tree (isolated copy)

```
codex-review            --self-test   79/79        check-review-recorded  --self-test  117/117
check-plan-code         --self-test  128/128       check-ratchet-contract --self-test   41/41
check-fixture-variation  OK — 506 parameter(s) across 50 file(s), 127 ratcheted, 7 exempt
check-selftest-counts    38 script(s) declare a count, every one verified by running it
check-review-rounds      232 parsed, 18 exemptions, 0 silent gaps, 98 verdicts, none contradicted

live: check-docs rc=0 · check-ratchet-contract rc=0 · check-guard-coverage rc=0
      check-selftest-counts rc=0 · check-fixture-variation rc=0 · check-review-rounds rc=0
      check-anchors rc=0
```

### Mutation gate — my own runs, in two isolated copies

```
shipping tree      44 file(s), 618 mutation(s), 618 killed, 618 attributed, 0 survivor(s)   rc=0
:907 REVERTED      44 file(s), 618 mutation(s), 618 killed, 618 attributed, 0 survivor(s)   rc=0   ← H1
```

The first reproduces the coordinator's and Codex's numbers, which makes four independent agreeing
runs. **The second is the finding.**

### Claims I did NOT verify by execution

* That the two `scripts/mutations/*.json` files are unchanged *since r12 reviewed them*. I have no
  snapshot of r12's tree, so I verified them on their merits instead — anchor uniqueness (618/618),
  no `expect` contamination (649/649), full attribution — rather than by differencing against a
  state I cannot observe. The brief's statement that only the three named things changed is
  consistent with everything I measured.
* The sweep's forcing transform for `begin-plan.py` and `check-plan-progress.py` needed a relaxed
  rule (their printers sit *below* an early-returning PASS guard, which the strict transform cannot
  reach). `check-plan-progress.py` was then forced by a single surgical edit to its `case()` guard
  and gave **35 raw `[FAIL]` lines, 35 parsed, 0 residue**. Stated because the relaxed rule applied
  tree-wide destroys control flow and its output must not be read as evidence — I discarded that run.
* One sweep hit flagged `check-anon-exposure.py`. Executed and confirmed a **false positive of my own
  heuristic**: the case name legitimately contains the word "expected" —
  `[FAIL] main() passes the out-of-reach list and the expected roles: got True want True` parses to
  `main() passes the out-of-reach list and the expected roles`, which is correct.

---

## 5. The frame — what thirteen rounds have been doing

Asked to say whether the accumulated documents have talked everyone into a frame, I think they have,
and it is visible in the shape of my own work here.

Every round from r11 on has attacked the `[FAIL] <case>` contract **by reading printers**. r11 read
one and fixed it. r12 read the other 43 files' printers, classified them into six shapes in prose,
and found the one r11 missed — in the same function, 21 lines away. The r12 coordinator called that
sweep *"the class question actually answered, and it is worth more than the fix."* It was a careful
human sweep, and it was right. But it is the thing this branch exists to argue against: the branch's
whole thesis is that a review must see what ships and that reading is the most expensive way to find
defects, and the class question was answered by reading, twice, after reading had already missed it
once.

The mechanised version is about forty lines — force every one-sided `[FAIL]` branch, run the real
suite through the harness's own `run_suite`, parse with the real `parse_fail_names`, assert the
parsed name is an authored name. Run against this tree it reproduces r12's conclusion in one command
and would have caught both r11's and r12's defects the day they landed. I am not proposing it as a
deliverable — it is a reviewer's instrument, and the do-not-refile list rightly bars the *static*
pre-flight, which is a different and unfalsifiable thing. I raise it because H1 and M1 are both the
same shape as the frame: **the rounds keep re-deriving by hand a property that the manifest mechanism
could hold**, and then recording in a comment that it is held. H1 is that gap for the printer; M1 is
that gap for entry distinctness. Both are cheap to close inside the mechanism that already exists.

The second thing worth saying plainly: twelve rounds and roughly 1,800 lines of review documents have
now been spent almost entirely on the **instrument** — the mutation harness, printer formats,
declared case counts — rather than on `check-review-recorded.py`, the gate this branch actually
ships. That gate was reviewed in r1–r10 and I found nothing new in it; its 117 cases pass and its 35
mutations are all attributed. I do not think it is under-reviewed. I do think the ratio is worth
noticing before round 14, because the remaining findings are getting further from the deliverable,
and M2 is the small measurable proof that attention has drifted to the instrument: the branch updated
the script's declared count twice while the number a reader actually sees went stale.

---

## Verdict

The r12 repair is correct and I proved it by execution rather than accepting it. The class sweep
holds under independent re-derivation, by a stronger method than the one that produced it. Regression
is clean at the AST level.

H1 blocks convergence: the branch is shipping a fix for a contract defect that has now broken twice
in this file, with a gate that measurably cannot tell the fix from the break. The repair is one
manifest entry and one count bump, and it is inside the existing mechanism — not the abandoned
pre-flight. M1 and M2 are one comment sentence and one number.

VERDICT: NOT CONVERGED
