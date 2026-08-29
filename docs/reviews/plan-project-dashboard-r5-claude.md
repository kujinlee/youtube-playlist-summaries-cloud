# Round 5 — Claude half. Subject: `scripts/check-plan-code.py`

**Subject:** `scripts/check-plan-code.py` — the TOOL, not the plan it checks.
**Commit:** `a643df6` (`docs/plan: v6 — the checker was verifying the document, not the code it ships`), branch `docs/dashboard-plan-review`.
**Input read only as input:** `docs/superpowers/plans/2026-08-28-project-dashboard-plan.md`.

## Method

Everything below was executed. Working copy at
`…/scratchpad/r5c/cpc.py`; no tracked file was modified, no `git` state was touched.

1. **Baseline.** `--self-test` → `44/44 passed`, rc 0. The real plan → `OK — 2 file(s), 34 mutation(s), 0 survivor(s)`, rc 0. `--verify-evidence` on the real plan → rc 0.
2. **Adversarial inputs.** 12 hand-built fixtures aimed at `extract()`, `compare_delivered()`, `pasted_evidence()` and the `expect` matcher, driven by importing the module directly so I could read `ev` rather than infer it from stdout.
3. **Mutation testing of the checker.** 44 undeclared mutants, one behaviour disabled per copy, each run against `--self-test`. **2 were invalid** (one no-op, one provably equivalent — both are listed and excluded rather than counted as survivors). **18 of the remaining 42 survived `44/44 passed`.**
4. **Liveness check.** For every finding I measured whether it currently bites the plan on disk, and say so. Several do not, and I say that too.

Nothing blocked me. There is no CANNOT-RUN in this review.

---

## READY TO EXECUTE: NO

**Must change:**

1. **Sanitise the file tag before it is used as a path** (H2). `..` and absolute tags escape the `TemporaryDirectory`; an absolute tag aimed at the `--compare` root makes the checker overwrite the delivered file and then certify it `identical`.
2. **Resolve `--compare` targets by the tag's full relative path, not `pathlib.Path(name).name`** (H1), and record the *resolved target* in the evidence block, not the tag. Today two different tags can both be certified `identical` against one file, and a tag naming a path that does not exist anywhere reports `identical`.
3. **Give `main()` cases** (H3). It has none. Three separate mutants that gut the CLI verdict — including `return 0` unconditionally — leave the suite at `44/44`. The exit code is the only thing the CI step and acceptance criterion 5 read.
4. **Fix Step 5a's collateral: the plan's own two reproduce/falsifier commands go permanently red the moment 5a is done** (H4). Either update those two commands in the same step, or make `--verify-evidence` tolerant of the mode line.
5. **Make `expect` mean what the plan says it means** (M1). It is a substring test; `"does NOT count"` currently matches **7** case names. Combined with `replace(find, repl, 1)` this can certify an untouched guard as caught — demonstrated below.
6. **Stop reading a timeout as a caught mutation** (M2). `run_suite`'s own comment says rc 2 must not be readable as either verdict; the mutation loop reads it as red.
7. **Pin the parser's anchoring** (M3, M4). An indented or info-string ```` ```python ```` fence is invisible — not counted, not a problem, not accounted for as illustrative. And unanchoring `ILLUS_BARE` keeps the suite green while breaking the tool against the real plan.

**0 Blocking · 4 High · 6 Medium · 6 Low**

---

## What reproduced exactly

This matters, because the list above should not be read as a general indictment. The tool is good, and most of what it claims is true.

- **The `44/44` is real and honest.** Twenty-four of my 42 valid mutants were caught, including every one of round 4's H3 trio (`ok = not problems`, `rc != 0`, unknown mutation target) and all five `--compare` behaviours I could think to break: dropped compare problems, a missing target silently skipped, every file forced to `identical`, a stale evidence block declared fresh, a missing evidence block skipped. The v6 additions are not decorative.
- **`--verify-evidence` works on the real plan.** rc 0 today; I confirmed the pasted block is byte-identical to a fresh no-compare run.
- **The colon fix is real.** `U21` (revert `rsplit(": got ", 1)` to `split(":", 1)`) is caught. So is `U22b` (widen the `[FAIL]` prefix to 8 and eat a character).
- **The illustrative-reason rule is real.** `U15` (accept a bare tag) and `U16` (make the reason optional) are both caught, and the two-problems-not-one behaviour is asserted.
- **The extractor's loud failures are loud.** A tag followed by a tag, a tag with no block, a non-python block under a file tag, unparseable mutation JSON, an untagged python block, an absent mutation anchor — all caught, all with the message they claim.
- **None of the parser holes below is live on the plan as committed.** I measured: 13 `^```python$` fences vs 13 lines containing ```` ```python ```` anywhere (no invisible fence); 0 indented fences of any language; 12 standalone `<!-- file: -->` tags and 0 written into prose; exactly 1 `GENERATED` marker; 0 mutation anchors occurring more than once in the assembled source. **These are latent, not active.** That is precisely why they survive review — and why the mutation results matter more than the current green.

---

## High

### H1 — `--compare` resolves the **basename**, so it can certify a file it never opened

**What I checked.** `compare_delivered` at `scripts/check-plan-code.py:171`:

```python
target = root / pathlib.Path(name).name
```

I built a plan tagging `worker/m.py`, and a `--compare` root containing `m.py` at its top level and **nothing** at `worker/m.py`.

**Actually true.**

```
does root/worker/m.py exist? False
F6 ok= True  compared= {'worker/m.py': 'identical'}  report= []
```

The evidence block would print `identical   worker/m.py` — naming a path the checker never opened and which does not exist. The verdict is recorded against the *tag*, so a reader cannot see the substitution.

Sharper, with two tags sharing a basename:

```
collision ok= True  compared= {'a/m.py': 'identical', 'b/m.py': 'identical'}
BOTH tags resolved to the SAME target: …/d4/m.py
```

Two distinct assembled files, one real file, two `identical` verdicts, and neither `a/m.py` nor `b/m.py` exists.

`U37` (resolve `root / name` instead) survives `44/44` — the basename decision is pinned in neither direction.

**Verdict: High.** Not live: this plan's two tags are `scripts/gen-dashboard.py` and `scripts/check-dashboard-entry.py` against `--compare scripts/`, where basename and full path coincide. But `--compare` exists *only* to stop a green over the wrong subject, and it contains a rule that silently substitutes a different subject. Round 4's H1 one layer in. Fix: `root / name` with the tag's directory preserved, plus a check that the resolved target is inside `root`.

### H2 — the file tag is used as a path with no sanitisation; an absolute tag makes the checker **overwrite** its own compare target and then report `identical`

**What I checked.** `FILE_TAG` at `:65` accepts `/` freely, and `check()` at `:208-210` does:

```python
(d / name).parent.mkdir(parents=True, exist_ok=True)
(d / name).write_text("\n\n".join(blocks) + "\n", encoding="utf-8")
```

`pathlib` makes `d / "/abs/path"` equal `/abs/path`, and `d / "../x.py"` escape the temp dir.

**Actually true.** Both escapes write, both survive `TemporaryDirectory` cleanup, and both return `ok=True` with an empty report:

```
F5 absolute: ok= True report= []
F5 /tmp/r5c-absolute.py exists AFTER the TemporaryDirectory closed: True
F4 traversal: ok= True report= []
F4 leaked file: ['/var/folders/tg/…/T/r5c-escaped.py']
```

The sharp version — a tag naming a file inside the `--compare` root:

```
delivered/m.py BEFORE: "# THE DELIVERED FILE — deliberately different from the plan'"
ok= True  report= []
compared verdict: {'…/delivered/m.py': 'identical'}
delivered/m.py AFTER : 'def f():\n    return 1\n\n\ndef _self_test():\n    bad = f() != 1'
```

The check **destroyed its own subject and then certified it**. `--compare` reported `identical` about a file it had itself just overwritten with the plan's copy, seconds earlier, in the same run.

**Verdict: High.** Low likelihood — nobody writes an absolute tag on purpose — but the impact is a green over a subject the tool manufactured, plus an unannounced write outside the sandbox, in a script that is otherwise scrupulous about staying inside a temp dir. Two lines fix it: reject a tag that is absolute or contains `..`, and assert the resolved path is under `d`.

### H3 — `main()` has **zero** coverage, and it is the only layer CI and criterion 5 read

**What I checked.** Counted calls inside `_self_test`:

```
occurrences of 'main(' inside _self_test: 0
occurrences of 'evidence(' inside _self_test: 5
```

Then mutated `main()` three ways.

**Actually true.** All three survive `44/44 passed`:

| mutant | effect | suite |
|---|---|---|
| `U42` `return 0 if ok else 1` → `return 0` | **the CLI always exits 0** | `44/44` |
| `U14` `if stale: ok = False` → no-op | `--verify-evidence` becomes advisory | `44/44` |
| `U30` `--compare <not-a-dir>` returns 0 instead of 2 | a CANNOT-RUN reports success | `44/44` |

Criterion 5 is *"`check-plan-code.py --compare scripts/ --verify-evidence` **exits 0**"*, and the Task 6 CI step reads nothing else. The proposition the whole gate rests on — that a non-zero exit follows from a failed check — is asserted nowhere. `check()` is well covered; the wrapper that converts its verdict into the observable is not.

This is round 4's H3 recurring one layer out: *the tool's single most important behaviour had no case.* The fix there added cases for `check()`. The same question was not asked of `main()`.

**Verdict: High.** Add cases that call `main([...])` and assert the return code: green plan → 0; red plan → 1; missing plan → 2; `--compare` at a non-directory → 2; stale evidence → 1.

### H4 — after Step 5a, the plan's own reproduce command and its stated falsifier are **permanently red**

**What I checked.** `verify_evidence` compares the pasted block to `evidence(ev)` **for the current invocation**, and `evidence()` emits a different subject stanza with and without `--compare` (`:293-299`). Task 4 Step 5a instructs regenerating the block in the compared form. The plan then still prints, at line 2576 and line 2587:

```
Reproduce with `python3 scripts/check-plan-code.py <this file> --evidence`.
python3 scripts/check-plan-code.py <this file> --verify-evidence   # exit 1 if this block is stale
```

Neither passes `--compare`.

**Actually true.** With a block generated in compared form:

```
--verify-evidence                              rc=1  FAILED — 1 file(s), 1 mutation(s), 0 survivor(s)
--compare <dir> --verify-evidence              rc=0  OK — 1 file(s), 1 mutation(s), 0 survivor(s)
```

So from the moment Step 5a lands, the command the plan advertises as its freshness falsifier exits 1 and prints *"the pasted evidence block is STALE"* — about a block that is not stale. A falsifier that fires unconditionally is worse than none: the first person to hit it learns the check lies, and stops reading it. That is the same failure mode round 4's B1 was about, inverted.

The plan is aware of the mechanism — line 2587's *"FAILS IF … the invocation's `--compare` mode changes"* — but Step 5a only says to paste the new block. It does not say to update the two commands printed beside it, and the `⛔` box calls the CI-vs-local disagreement resolved.

To be fair to the design: **the CI step itself is fine.** It is added in Task 6, after Task 4 creates both scripts, and it passes both flags. There is no ordering hole. The damage is confined to the plan's own two documented invocations and to any human who runs the bare command.

**Verdict: High.** Cheapest fix: exclude the subject stanza from the byte comparison and report the mode separately, so one pasted block satisfies both invocations. Alternative: Step 5a also rewrites those two command lines to carry `--compare scripts/`.

---

## Medium

### M1 — `expect` is a substring test, and edits apply to the first occurrence only; together they can certify an **untouched** guard as caught

**What I checked.** `:247` `src = src.replace(find, repl, 1)` — nothing counts occurrences. `:262` `named = (not want) or any(want in f for f in fails)` — substring, and any matching case satisfies it. I built a file with the same guard on a `head` path and an `in-place` path, and a suite with cases `"indent rule: head path"` and `"indent rule: in-place path"`, then declared a mutation named for the **in-place** path with `expect: "indent rule"`.

**Actually true.**

```
F7c ok = True   <-- the check PASSES
F7c evidence: [{"name": "THE IN-PLACE PATH stops skipping indented rows",
                "caught": true, "fails": ["indent rule: head path"]}]
```

The generated evidence block prints `caught   THE IN-PLACE PATH stops skipping indented rows`. The in-place guard was never modified. The `[FAIL]` line that satisfied `expect` names the *other* path.

Measured against the real 34-mutation manifest — the exposure is partly live:

```
=== anchors occurring MORE THAN ONCE in the assembled file ===
  total multi-occurrence anchors: 0

=== `expect` substrings matching MORE THAN ONE case-name literal ===
  expect='two [resolved'   matches 2 case names
  expect='glossary'        matches 2 case names
  expect='does NOT count'  matches 7 case names
```

So the compound failure is **not** live: no anchor is ambiguous today. But three mutations do not test what the plan says they test. `gate stops sharing the parser grammar` declares `expect: "does NOT count"` and goes red via five different cases, any one of which would satisfy it alone. The plan's rule is *"Each must go **red via the case it names**"*; the tool enforces "red via any case whose name contains this substring."

`U20` (`replace(find, repl)` — all occurrences) survives `44/44`, so neither direction of the first-occurrence rule is pinned.

**Verdict: Medium** — latent for the compound, live but harmless for the three loose `expect`s. Fix: fail when `src.count(find) > 1` unless the manifest says which occurrence, and require `expect` to match exactly one case name.

### M2 — a mutation that makes the suite **hang** is recorded as `caught`

**What I checked.** `run_suite` at `:156-158` carries the comment *"A hung suite is a CANNOT RUN, not a traceback. rc 2 is distinct from both the green 0 and the red 1, so a caller cannot read a timeout as either verdict."* The very next caller, at `:260`, is `caught = rc != 0`.

**Actually true.** A mutation whose only effect is an infinite loop, with no `expect`:

```
F9 ok= True  (120s)  mutation: [{'name': 'hangs instead of failing', 'caught': True, 'fails': []}]
F9 report: []
    caught   hangs instead of failing     <- in the GENERATED evidence block
```

Two minutes of NOT CHECKED, recorded as proof that a guard works.

`U25` (timeout returns 1) and `U33` (`caught = rc == 1`) both survive `44/44` — there is no timeout fixture at all.

**Verdict: Medium, not High**, because `expect` narrows it: with an `expect` the empty `fails` list makes `named` false and the run fails loudly — though with the wrong message (*"went red, but not via a case matching …"*, describing a timeout as a wrong-case catch). All 34 of this plan's mutations declare `expect`, so the silent form is unreachable here. But the docstring says `expect` is **optional**, and for a mutation without it, `caught` means only "the file stopped exiting 0" — which also covers a syntax error and a hang.

### M3 — an indented or info-string ```` ```python ```` fence is invisible: no count, no problem, no illustrative account

**What I checked.** `FENCE = re.compile(r"^```(\w*)\s*$")` at `:84`. The tool's stated core promise is at `:90` — *"A tag with no block that follows is a problem, not a silent skip — that is how a plan loses a function to prose."*

**Actually true.**

```
--- F2 indented python fence
   tally: {'python_fences': 1, 'tagged': 1, 'illustrative': 0, ...}
   problems: []
--- F3 info-string fence
   tally: {'python_fences': 1, 'tagged': 1, 'illustrative': 0, ...}
   problems: []
```

In both fixtures a second `python` block containing `1/0` is present and is not counted, not reported, and not excused. A fence indented four spaces — the ordinary shape inside a nested list step — takes a code block out of the checker's sight entirely, and the `illustrative` reason rule, which exists precisely so that every exclusion states itself, is bypassed with no trace. `U19` (unanchor `FENCE`) survives `44/44`.

An info-string fence is worse in one respect: the opening line does not match, so its *closing* fence is read as an opening one and swallows the rest of the document to the next fence.

**Verdict: Medium.** Not live (measured: 13 = 13 python fences, 0 indented fences anywhere in the plan). Fix: match indented fences and info strings, and treat a fence the parser cannot classify as a problem.

### M4 — the anchoring the v6 comment argues for is not pinned, and unanchoring it breaks the tool against the real plan while the suite stays green

**What I checked.** `:77-80` explains at length why `ILLUS_TAG`/`ILLUS_BARE` must be `^…$`: *"Measured while adding this rule: the checker failed on the paragraph explaining it."* I unanchored `ILLUS_BARE` and ran both the suite and the real plan.

**Actually true.**

```
U18 ILLUS_BARE unanchored
   --self-test rc=0  44/44 passed
   against the REAL plan rc=1
      ✗ a bare `<!-- illustrative -->` — the tag must carry a REASON …
      FAILED — 2 file(s), 34 mutation(s), 0 survivor(s)
```

Lines 102 and 2488 of the plan quote `` `<!-- illustrative -->` `` in prose. They are the live payload. The suite reports `44/44 passed` over a tool that is broken against its own input. `U17` (unanchor `ILLUS_TAG`) also survives; it happens not to bite the plan today because no illustrative *reason* tag is quoted in prose.

Note the asymmetry the fix left behind: `ILLUS_*` are anchored, but `FILE_TAG` and `MUT_TAG` at `:65`/`:83` still use `.search()`. A `<!-- file: gen-dashboard.py -->` written into a sentence is parsed as a tag (fixture F1 produced `file tag for 'gen-dashboard.py' was followed by another tag, not a block`). `U36` (anchor `FILE_TAG`) survives `44/44`. It fails loudly today rather than misattributing, and the plan has 0 prose file tags — but the class the v6 comment identifies was fixed in one of three places.

**Verdict: Medium.** Add a case with the convention quoted in prose, for all three tag families.

### M5 — block concatenation order and the per-mutation source restore are both unpinned

**What I checked.** The contract at `:50` — *"Blocks with the same tag are concatenated in document order"* — and the restore at `:253`.

**Actually true.** `U40` (concatenate `reversed(blocks)`) survives `44/44`. `U38` (drop `(d / fname).write_text(orig)`) survives `44/44`. Every multi-block fixture in the suite has exactly one block, so ordering is never observed; and no fixture declares two mutations, so accumulation across mutations is never observed.

The second is the one with teeth: without the restore, mutation *N* is applied to a source already carrying mutations 1…N−1, and a `caught` verdict stops meaning anything about the mutation it names. On this plan that is 34 compounding edits. The behaviour is correct today; nothing would tell you if it stopped being.

**Verdict: Medium.** A two-block fixture and a two-mutation fixture close both.

### M6 — `--verify-evidence` compares `evidence()` to itself, so it can never detect that the evidence reports the **wrong thing**

**What I checked.** `verify_evidence` regenerates via `evidence(ev)` and diffs against a block that `evidence(ev)` also produced. Any change to `evidence()` changes both sides identically.

**Actually true.** `U39` (drop the per-mutation roll-call from the evidence block) survives `44/44` — and would survive `--verify-evidence` against a plan whose block was regenerated after the change. The mechanism detects *staleness* only. That is what it was built for and the docstring is honest about it; but the roll-call it prints, which is what a human reads, has no independent assertion. `U35` (`RESULT` matches anything, so `tail` records an arbitrary line) also survives.

**Verdict: Medium.** Assert the *content* of `evidence()` in at least one case — that a survivor appears as `SURVIVED`, that `compared` verdicts appear per file — rather than only round-tripping it.

---

## Low

- **L1 — the three modes are indistinguishable from stdout and the exit code.** Measured: `(plain)`, `--compare <dir>`, and `--compare <dir> --verify-evidence` all end in `OK — 1 file(s), 1 mutation(s), 0 survivor(s)`, rc 0. The subject is named only inside the evidence block, which requires `--evidence`, which CI does not pass. A CI log therefore cannot show which subject was measured. Partly mitigated after Step 5a: dropping `--compare` alone would then fail via `--verify-evidence`. Dropping both flags would not. One word on the final line (`OK — compared 2 file(s) …`) closes it.
- **L2 — the `[FAIL]` parse mangles a case name when the marker is not at the start of the line.** `:258` does `l.strip()[7:]` under the guard `"[FAIL]" in l`. A reporter that prefixes its lines yields `fails: ['L] f returns one']` — recorded verbatim into the evidence. It can only truncate from the left, so it produces a false red or a corrupt record, never a false green. (`U22`, narrowing the slice to `[6:]`, is an **equivalent mutant** — the trailing `.strip()` absorbs it — and I have not counted it as a survivor.)
- **L3 — a second, stale evidence block later in the file is never read.** `pasted_evidence` takes `md.find(EV_MARK)`, the first. Measured: stale-then-fresh → 1 problem; fresh-then-stale → **0 problems**, the stale block unexamined. Not live (the plan has exactly 1 marker).
- **L4 — the marker quoted in prose produces a misleading verdict.** With the `GENERATED …` line mentioned in a sentence above the real block, `--verify-evidence` reports *"the pasted evidence block is STALE"* and diffs the prose. It fails closed, so this is only a bad message — but it is the same prose-matches-the-convention class as M4, in the one locator that was not anchored.
- **L5 — the docstring case-count check is unpinned.** `U26` (`if False:`) survives `44/44`. Self-referential and low-stakes, but the guard exists because `# 12 cases` once drifted against a 19-case suite.
- **L6 — `if not files: return False` is unpinned.** `U32` (return `True`) survives `44/44`. A plan whose tags stopped matching would print `OK — 0 file(s), 0 mutation(s), 0 survivor(s)`.

---

## The undeclared mutations that SURVIVED

44 mutants run. **2 invalid and excluded:** `U12` (`return [] or [...]` is a no-op — the corrected `U12b` is caught, so a missing evidence block *is* pinned) and `U22` (`[6:]` is equivalent under the trailing `.strip()`; `U22b` at `[8:]` is caught). **18 of the 42 valid mutants survived `44/44 passed`.**

| # | mutant | what it disables |
|---|---|---|
| U42 | `main`: `return 0 if ok else 1` → `return 0` | **the CLI always exits 0** — H3 |
| U14 | `main`: `if stale: ok = False` → no-op | `--verify-evidence` becomes advisory — H3 |
| U30 | `main`: `--compare <not-a-dir>` → `return 0` | a CANNOT-RUN reports success — H3 |
| U37 | `target = root / name` instead of the basename | the `--compare` resolution rule — H1 |
| U20 | `replace(find, repl, 1)` → `replace(find, repl)` | first-occurrence-only edits — M1 |
| U25 | `run_suite` timeout returns 1, not 2 | the cannot-run/red distinction — M2 |
| U33 | `caught = rc != 0` → `caught = rc == 1` | …the other direction of the same gap — M2 |
| U19 | `FENCE` unanchored from column 0 | fence anchoring — M3 |
| U17 | `ILLUS_TAG` unanchored | prose-matches-convention — M4 |
| U18 | `ILLUS_BARE` unanchored | …and this one **breaks the real plan** while the suite stays green — M4 |
| U36 | `FILE_TAG` anchored to a standalone line | the tag families are inconsistent — M4 |
| U40 | blocks concatenated in reverse document order | the stated concatenation contract — M5 |
| U38 | the mutated file is never restored between mutations | mutation independence — M5 |
| U39 | `evidence()` drops the mutation roll-call | evidence content is round-tripped, never asserted — M6 |
| U23 | only the last result line is recorded | v6's result-line collector — M6 |
| U35 | `RESULT` matches any line | which line becomes the evidence `tail` — M6 |
| U26 | the docstring case-count drift check | L5 |
| U32 | a plan with no tagged blocks passes | L6 |

Three clusters account for all eighteen: **`main()` is untested** (3), **the parser's regexes are untested in both directions** (4), and **the evidence block's *content* is only ever compared to itself** (4). The remaining seven are individual behaviours added in v6 with a mechanism but no case — the same shape round 4 filed as H3, which is what makes this a pattern rather than an oversight.

---

## Verdict: NOT CONVERGED

Four High findings, all in mechanisms added in v6 and none of them read by anyone before now. None produces a wrong verdict on the plan as committed at `a643df6` — I checked each one against the real file and said so — but three of the four (H1, H2, H4) are cases where the tool can print `OK —` over a subject it did not measure, or a `FAILED —` over one that is fine, which is the exact defect class v6 was written to close. H3 is the reason none of them was caught: the layer CI reads has no tests.

The tool is close. The fixes are small and local, and I would expect a round 6 scoped to them to converge.
