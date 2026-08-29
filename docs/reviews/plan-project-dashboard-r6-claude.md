# Round 6 — Claude half. Subject: `scripts/check-plan-code.py`, round 5's fixes only

**Subject:** the eleven changes round 5 produced in `scripts/check-plan-code.py`. The TOOL, not the plan.
**Commit:** `7df38e3` (`docs/plan: v7 — round 5 found the checker reporting success over things it never measured`), branch `docs/dashboard-plan-review`.
**Read as input only:** `docs/reviews/plan-project-dashboard-r5-claude.md`, `docs/superpowers/plans/2026-08-28-project-dashboard-plan.md`.

## Method

Everything below was executed. Working copies in `…/scratchpad/r6c/`; no tracked file
was modified and no `git` state was touched (every mutant was written to its own
`TemporaryDirectory`, never to the repo — a second reviewer is running concurrently).

1. **Baseline.** `--self-test` → `92/92 passed`, rc 0. The plan → `OK — plan's copy only, NOT compared: 2 file(s), 34 mutation(s), 0 survivor(s)`, rc 0.
2. **Targeted fixtures**, one per changed item, driven by importing the module so I could
   read `ev` and `problems` directly rather than infer them from stdout.
3. **Mutation testing.** 62 undeclared mutants, one behaviour disabled per copy, each run
   against `--self-test`. **1 invalid** (my declared no-op control). **11 of the 60 valid
   mutants survived `92/92 passed`**; 2 of the 11 are provably equivalent, proven below by
   reading the path, leaving **9 genuine survivors**.
4. **Liveness.** For each finding I measured whether it bites the plan as committed, and say so.

Nothing blocked me. There is no CANNOT-RUN in this review.

---

## READY TO EXECUTE: NO

**Must change:**

1. **Give the `expect` LIST form at least one case** (H1). It has **zero**. Deleting the list
   handling outright, and checking only the first entry of a list, both leave `92/92 passed`
   **and** the real plan at `OK —`. The manifest uses the list form 4 times to declare 11
   named guards.
2. **Do not WRITE a file tag that `extract()` just refused** (H2). The rejection is in the
   report only; `check()` still writes the escaping path. An absolute tag aimed inside the
   `--compare` root still overwrites the delivered file — round 5's must-change 1, half done.
3. **Assert the `MISSING` compare verdict, not just the failure** (M1). Nothing pins it, and
   the evidence block will print `identical` for a file the checker could not open.
4. **Make the anchor-NOT-FOUND case distinguish itself from a survivor** (M2). It passes today
   via the wrong branch; with the guard removed, a multi-edit mutation with a typo'd first
   anchor is certified `caught`.
5. **Stop `INVISIBLE_FENCE` firing on a four-backtick fence** (M3) — the standard markdown
   idiom for quoting a fence, already present in this repo. It raises three problems for one
   legitimate construct, one of which asserts something false.
6. **Add the missing MUT_TAG anchoring case** (M4). Item 7 says "all four tag patterns
   anchored"; three of the four are pinned.
7. **Pin `count_drift`'s call site** (M5). The function now has three cases; deleting the call
   that makes it load-bearing still leaves `92/92`.

**0 Blocking · 2 High · 5 Medium · 5 Low**

---

## What reproduced exactly

The list above should not be read as a general indictment: **eight of the eleven changes are
real, and most are pinned in both directions.** What I could not break:

- **Item 1, `--compare` takes the repo root.** Reverting to `root / pathlib.Path(name).name`
  (round 5's H1, its surviving mutant `U37`) is now **caught**, `90/92`. So are forcing every
  file `identical`, and turning a missing target back into a silent skip. Two same-named files
  in different directories resolve correctly; a trailing slash on the root and a root
  containing `..` both behave.
- **Item 3, ambiguous anchors.** Removing the count check and moving it off by one are both
  caught. Round 5's `U20` (`replace(find, repl)` — all occurrences) now survives *because it is
  provably equivalent*; the proof is in Mutation results. That is the right kind of survivor.
- **Item 5, rc 2.** Reading a timeout as a catch again, returning 1 from the timeout path, and
  ignoring `SUITE_TIMEOUT` are all caught. The 2-second constant makes the path reachable and
  the fixture takes 2s, not 120.
- **Item 6, `INVISIBLE_FENCE` catches what it claims.** Deleting either half of the alternation
  is caught, and so is dropping `\s*` from the lookahead — `(?!\w*\s*$)` does do what the
  comment says, verified line by line on 18 fence shapes. An indented ` ``` ` inside a python
  block still does not close it.
- **Item 8, two evidence blocks.** All three ways I could disable the AMBIGUOUS verdict are caught.
- **Item 9, the mode line.** Both blanking it and mislabelling a compared run are caught.
- **Item 11, `main()`.** This is the strongest part of the fix. **All six** mutants I aimed at
  the CLI verdict are caught, including round 5's whole H3 trio: `return 0` unconditionally,
  `--verify-evidence` made advisory, and `--compare <not-a-dir>` reporting success. The nine
  new cases pin the exit **code**, not just the text — I mutated `main` to confirm they fail for
  the reason they name, and each does.
- **Round 5's M6 is closed.** Dropping the per-mutation roll-call from `evidence()` is now
  caught (`90/92`), where it survived last round.
- **The plan is clean under all of this.** Measured: 0 `INVISIBLE_FENCE` hits, 0 non-standalone
  `<!-- mutations -->` tags, 0 escaping file tags, and — the live half of round 5's M1 — **no
  `expect` is a substring of more than one case-name literal** in its own file. The
  `expect: "does NOT count"` that matched 7 case names is gone, replaced by 5 precise entries.

---

## High

### H1 — the `expect` LIST form, item 4's headline change, has **zero** coverage: deleting it entirely leaves both the suite and the plan green

**What I checked.** `:359-367`:

```python
want = mut.get("expect")
wants = [want] if isinstance(want, str) else list(want or [])
unnamed = [(w, [f for f in fails if w in f]) for w in wants]
unnamed = [(w, m) for w, m in unnamed if len(m) != 1]
```

Then I counted the forms actually exercised:

```
list-form expects in the self-test:  0
string-form expects in the self-test: 8
list-form expects in the PLAN's manifest: 4
```

**Actually true.** Two mutants, each disabling the list form in a different way, run against
both the suite and the real plan:

| mutant | effect | `--self-test` | the real plan |
|---|---|---|---|
| `E1` `else list(want or [])` → `else []` | a list `expect` is **silently ignored entirely** | `92/92 passed` rc 0 | `OK — … 34 mutation(s), 0 survivor(s)` rc 0 |
| `E5` `for w in wants` → `for w in wants[:1]` | only the **first** entry is checked | `92/92 passed` rc 0 | `OK — … 34 mutation(s), 0 survivor(s)` rc 0 |

Under `E1`, `wants` is empty, `unnamed` is empty, and every list-form mutation reduces to
"the suite stopped exiting 0, for any reason, via any case" — which is exactly the state round
5's M1 was filed to end. Neither the 92-case suite nor the document under review notices.

What is riding on it, measured from the manifest:

```
plan manifest: 34 mutations; 4 use the LIST form, declaring 11 named guards between them:
   'second [resolved:] dropped'            : 2 entries
   'glossary section removed'              : 2 entries
   'gate stops sharing the parser grammar' : 5 entries
   'indent rule removed entirely'          : 2 entries
```

The five-entry one is round 5's own example. Its `expect` used to be the single substring
`"does NOT count"`, which matched 7 case names; the fix replaced it with five precise entries.
`E5` verifies the first and discards the other four, invisibly.

**Verdict: High.** The shipped code is correct — I am not claiming a wrong verdict today. The
finding is that item 4 added a mode, put the plan's most important mutations on it, and asserted
nothing about it, so a regression in it cannot be observed by any mechanism this project runs.
That is round 5's H3 (`main()` had no cases) recurring one mechanism over, and it is the exact
question this round was asked to put to each of the eleven items. Fix: three cases — a list of
two where both match (passes), a list of two where one matches nothing (fails, naming *that*
entry), and a list whose second entry matches two red cases (fails).

### H2 — an escaping file tag is **reported and then written anyway**; the checker still overwrites its own `--compare` target

**What I checked.** `extract()` at `:181-193` appends a problem for an absolute or `..` tag, and
its comment states the intent:

```
# Reject rather than sanitise: a plan has no reason to name anything but a
# repo-relative path, and silently rewriting the tag would make the evidence
# describe a file the plan does not name.
```

But the name stays in `files`, and `check()` at `:265-267` writes every entry unconditionally:

```python
for name, blocks in files.items():
    (d / name).parent.mkdir(parents=True, exist_ok=True)
    (d / name).write_text("\n\n".join(blocks) + "\n", encoding="utf-8")
```

**Actually true.** All three of round 5's H2 reproductions still write:

```
ABS   ok= False  problems: 1
ABS   wrote OUTSIDE the sandbox to /tmp? True
TRAV  ok= False  problems: 1
TRAV  leaked file survives TemporaryDirectory cleanup? True   (/var/folders/…/T/r6c-traversal.py)

SHARP delivered BEFORE: '# THE DELIVERED FILE - deliberately different from the plan\n'
SHARP delivered AFTER : 'def f():\n    return 1\n\n\ndef _self_test():\n   '
SHARP overwritten by the checker? True
SHARP compared verdict: {'…/repo/scripts/m.py': 'identical'}
```

**What round 5's fix did buy, and it matters:** the verdict is now `ok=False`, so the false
green is gone — `--compare` no longer certifies the file it manufactured. `S2`, `S3`, `S4` and
`S5` (remove the check; refuse only absolutes; refuse only `..`; sanitise instead of reject) are
all **caught**.

**What it did not buy:** the destructive write. The CI invocation is
`check-plan-code.py <plan> --compare . --verify-evidence` with the repo root as `root`, so a
plan carrying an absolute tag into the repo overwrites a tracked file, and the run that did it
still prints `identical <path>` inside the evidence block beside the `FAILED —` line.

The reason nothing caught this is visible in the case that claims to cover it, `:700-703`:

```python
for bad_tag in ("../escape.py", "/tmp/abs.py"):
    _f, _m, esc, _t = extract(GOOD.replace("m.py", bad_tag, 1))
    case(f"a file tag of {bad_tag!r} is refused", any("escapes" in p for p in esc), True)
```

It asserts against `extract()` — the layer that *reports* — and never runs `check()`, the layer
that *acts*. Round 5's must-change 1 asked for two things ("reject a tag that is absolute or
contains `..`, **and assert the resolved path is under `d`**"); the first landed.

**Verdict: High.** Not live: the plan's two tags are ordinary repo-relative paths, and the
overall verdict is correct. But it is half of a must-change, in a tool whose stated premise at
`:41-43` is that "everything above happens inside a `TemporaryDirectory`", and the failure mode
is silent data loss in the repo rather than a bad verdict. Fix: drop escaping names from `files`
(or `return` before the write loop when `problems` contains one), and add a case that calls
`check()` and asserts the target does not exist afterwards.

---

## Medium

### M1 — the one compare verdict that means "not checked" is the one with no assertion

**What I checked.** `compare_delivered` at `:233` sets `seen[name] = "MISSING"`. The suite pins
`identical` (`:638`) and `DRIFTED` (`:644`) by value, but the missing-file case at `:646-649`
asserts only `miss_ok == False` and `any("NOT CHECKED" in r)`.

**Actually true.** `C3` (`seen[name] = "MISSING"` → `"identical"`) survives `92/92`, and the
block a human reads becomes:

```
  subject: the plan's blocks, DIFFED against the delivered files:
    identical  m.py          <- for a file that could not be opened
```

The run still exits 1, so this is not a false green — but the evidence block is the artifact
pasted into the plan and read later, and the docstring at `:47-48` promises "the evidence block
always records which of the two subjects was measured". One `case(... ev["compared"]["m.py"],
"MISSING")` closes it.

**Verdict: Medium.** Not live.

### M2 — the anchor-NOT-FOUND case passes via the wrong branch, and the guard it names is load-bearing

**What I checked.** `:313` `if find not in src:` and the case at `:561-564`, which declares a
single-edit mutation with a bogus anchor and asserts `ghost_ok == False`.

**Actually true.** `X11` (`if find not in src:` → `if False:`) survives `92/92` — because with
one edit the mutation simply no-ops, the suite stays green, and the run fails as
`mutation SURVIVED` instead. Same verdict, different reason; the case cannot tell them apart.

With **two** edits the two branches diverge, and the guard turns out to be the only thing
standing between a typo and a false green:

```
  WITH the guard (as shipped): ok= False
    ✗ mutation 'TWO edits, the first is a TYPO': anchor NOT FOUND — it was not applied…
  WITHOUT the guard (X11):     ok= True
     evidence: [{'name': 'TWO edits, the first is a TYPO', 'caught': True, 'fails': ['f returns one']}]
```

A mutation declaring two edits, the first misspelled, is recorded `caught` on the strength of
the second. The plan declares multi-edit mutations, so the shape is reachable.

**Verdict: Medium.** Not live — the guard is present and correct. Fix: assert the *message*
(`any("anchor NOT FOUND" in r)`), and add the two-edit fixture.

### M3 — `INVISIBLE_FENCE` rejects a four-backtick fence: three problems for one legitimate construct, and one of them is a false statement

**What I checked.** `:107`:

```python
INVISIBLE_FENCE = re.compile(r"^(?:\s+```\s*\w+\s*$|```(?!\w*\s*$).+$)")
```

The second alternative fires on any column-0 line beginning with ` ``` ` whose remainder is not
a bare language word. A four-backtick fence — the standard markdown way to wrap a block that
itself contains fences — leaves a fourth backtick as that remainder.

**Actually true**, on ` ````md ` … ` ```python ` … ` ``` ` … ` ```` `:

```
problems: 3
 ✗ a code fence this parser cannot see (line 17): '````md'. A fence must start at column 0…
 ✗ an UNTAGGED ```python block (near line 19) — the assembler cannot see it, so nothing proves it runs…
 ✗ a code fence this parser cannot see (line 21): '````'. A fence must start at column 0…
```

The middle problem is not true: that block is a *quoted example* inside the outer fence, and
demanding it be tagged or marked illustrative is advice that cannot be followed. The repo
already contains the construct — `docs/reviews/spec-blob-key-encoding-r12-codex.md:15,21`.
Also refused: any language tag containing a non-word character (` ```c++ `, ` ```objective-c `,
` ```{r} `) and ` ``` python ` with a leading space.

**Verdict: Medium.** Not live (0 hits on the plan; the CI step points at that one file only) and
it fails closed. But this is the class round 5's M4 named — *a document that quotes its own
conventions trips its own checker* — reintroduced for the idiom most likely to appear in a plan
about a markdown parser. Fix: require exactly three backticks (` ^```(?!`) `), and treat a
four-plus-backtick fence as an ordinary fence to be consumed rather than a defect.

### M4 — "all four tag patterns anchored" is three-of-four verified

**What I checked.** Item 7's claim, against the comment at `:72-76` and the four patterns.

**Actually true.** `G1` (FILE_TAG unanchored), `G3` (ILLUS_TAG), `G4` (ILLUS_BARE) are all
**caught** at `91/92`. **`G2` (MUT_TAG unanchored, `:95`) survives `92/92`.** Measured against
the plan: 1 occurrence of the mutations tag, standalone — so it is not live, exactly as
FILE_TAG's prose case was not live when round 5 filed it.

`G5` (FENCE, `:96`) also survives and is **provably equivalent** — see Mutation results.

**Verdict: Medium.** One case, mirroring `:950-952`.

### M5 — `count_drift` is covered; the call that makes it load-bearing is not

**What I checked.** Item 10 extracted `count_drift` to module level so a case could reach it,
and three cases at `:756-761` do. The call site is `:1010`.

**Actually true.** `D1` (never report a mismatch) and `D2` (a missing count is silently fine)
are both **caught** — the function is genuinely pinned. `D3` (`drift = count_drift(__doc__, ok + fail)`
→ `drift = None`) **survives `92/92`**. The docstring's `# 92 cases` is quoted in
`docs/dev-process.md`, and this is the guard that keeps it honest.

This is round 5's L5 one layer out: extracting the function bought *coverage of the function*,
and the wiring inherited the same blind spot the inline version had.

**Verdict: Medium.** Self-referential and awkward to test in place — the honest fix is to move
the decision into a helper (`_drift_rc(doc, ok, fail)`) and case that, rather than assert it is
untestable.

---

## Low

- **L1 — the evidence block's per-file result line has no assertion.** `X3` (drop
  `N blocks assembled -> tail` from `evidence()`) survives `92/92`. Round 5's M6 fix added
  content assertions for `SURVIVED`, `caught` and the compare verdict; the line carrying each
  suite's actual result was not among them.
- **L2 — a mutation that could not run is not counted on the final line.** `T5` (drop
  `ev["survivors"].append(name)` from the rc-2 branch) survives `92/92`; the run would print
  `FAILED — … 0 survivor(s)` for a mutation that was never checked. Related: `run_suite`'s rc 2
  sentinel is **not** distinct from a suite genuinely exiting 2 (python exits 2 on a bad
  argument or an unopenable file), so a real rc 2 is diagnosed as a timeout. Fails closed both
  ways; the self-test's timeout case monkeypatches `subprocess.run`, so it cannot see the collision.
- **L3 — malformed input crashes without printing a verdict line.** `<!-- file: . -->` →
  uncaught `IsADirectoryError`; `"expect": 5` → uncaught `TypeError: 'int' object is not
  iterable`. Both exit 1 with **empty stdout** — no `FAILED —` line at all, so a CI log shows a
  traceback where the tool's own contract says a verdict goes. The tag charset does at least
  make the platform question moot: `[A-Za-z0-9._/-]` excludes `\` and `:`, so a Windows drive
  path cannot be parsed as a tag and `PurePosixPath` is safe here. Accepted-but-odd tags:
  `foo/`, `./m.py`, `a//b.py`, `-rf`, `m.py.`.
- **L4 — the tag patterns allow indentation; `FENCE` forbids it, and `INVISIBLE_FENCE` now
  punishes the combination.** `FILE_TAG` is `^\s*<!--…`, so a tag inside a numbered list step is
  accepted, but its block is not:
  ```
  ✗ a code fence this parser cannot see (line 4): '```python'…
  ✗ file tag for 'm.py' has no code block after it
  ```
  Two problems for one ordinary markdown shape. 17+ plan documents in this repo indent fences
  inside list steps. Fails loud, and the CI step targets one plan — but the `\s*` in the tag
  patterns now promises something the fence rule refuses.
- **L5 — `expect` is still weaker than the plan's stated rule, in two bounded ways.** Measured:
  `"expect": []` and `"expect": ""` both silently degrade to no-expect (`ok=True`); and the rule
  enforced is *exactly one **red** case*, not *exactly one case in the suite* — `expect: "guard"`
  against a suite with `guard: head path` and `guard: in-place path`, where only one goes red,
  **passes**. So a loose substring can still stand in for a name. Not live: no `expect` in the
  manifest is a substring of more than one case-name literal.

---

## Mutation results

**62 mutants run. 1 invalid and excluded** (`C2`, my declared no-op control). **11 of the 60
valid mutants survived `92/92 passed`.** Two are provably equivalent, proven by reading the
path, not asserted:

- **`A3`** — `src.replace(find, repl, 1)` → `src.replace(find, repl)`, round 5's surviving
  `U20`. **Equivalent as shipped.** The only path reaching `:319` passes both guards first:
  `:305` fails and breaks when `src.count(find) > 1`, and `:313` fails and breaks when
  `find not in src`. So at `:319` the count is exactly 1, and the two calls are identical.
  Item 3 converted a live gap into an equivalent mutant — that is the fix working.
- **`G5`** — `FENCE = re.compile(r"^```(\w*)\s*$")` → the same without `^`. **Equivalent.**
  `FENCE` is used only with `.match()` (`:147`, `:150`), which anchors at position 0 regardless
  of `^`. `FILE_TAG`, `ILLUS_*` and `MUT_TAG` use `.search()` (`:125`, `:129`, `:131`, `:137`),
  which is why the same edit to those is caught and this one cannot be.

**The 9 genuine survivors:**

| # | mutant | what it disables | finding |
|---|---|---|---|
| `E1` | a list `expect` is ignored entirely | the whole list form — **and the real plan stays green** | H1 |
| `E5` | only the first `expect` entry is checked | 4 mutations' 11 declared guards, minus 4 | H1 |
| `X11` | `if find not in src:` → `if False:` | a typo'd first anchor certified via a later edit | M2 |
| `C3` | a missing compare target records `identical` | the one compare verdict meaning "not checked" | M1 |
| `G2` | `MUT_TAG` unanchored | the fourth of item 7's "all four" | M4 |
| `D3` | `count_drift` is never called | the docstring-count guard's wiring | M5 |
| `X3` | `evidence()` drops the per-file result line | evidence content, the part M6 did not reach | L1 |
| `T5` | a hung mutation is not counted a survivor | the survivor count on the final line | L2 |
| `T2` | `caught = rc == 1` → `rc != 0` | round 5's original form | L2 |

`T2` deserves its own sentence, because it is *nearly* equivalent and I will not claim that it
is. After the `if rc == 2: continue` guard at `:340-347`, `rc == 1` and `rc != 0` can differ
only for rc ≥ 3, which no fixture produces. The shipped form is the stricter of the two and I am
not asking for a change; I am recording that the distinction is unasserted.

**Caught, 49 of 60** — including every mutant aimed at items 1, 3, 5, 6, 8, 9 and 11, all six
`main()` mutants, and both of round 5's remaining evidence-content survivors.

---

## Verdict: NOT CONVERGED

Eight of the eleven changes hold up under attack, and item 11 — the `main()` cases — closes
round 5's H3 completely, in both directions. Round 5's survivor count fell from 18/42 to 9/60,
and two former survivors are now equivalent mutants rather than gaps.

But the round was called to ask one question of each change — *does any new guard report success
over something it did not measure?* — and two of them answer yes. **H1 is the sharpest instance
this tool has produced**: the mechanism added to stop `expect` certifying via the wrong case has
a mode that carries 11 of the plan's declared guards and that can be deleted outright without
the suite, or the plan, or CI noticing. **H2 is a must-change implemented in the layer that
reports rather than the layer that acts**, which is the same distinction H1 turns on.

Both fixes are small and local, and neither changes a verdict the tool gives today. A round 7
scoped to the seven must-changes should converge.
