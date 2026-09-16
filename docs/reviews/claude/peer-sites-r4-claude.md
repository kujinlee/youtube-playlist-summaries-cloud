# peer-sites — round 4, Claude half

**Subject: the UNCOMMITTED working tree on `71378cd3`** — `git status` + `git diff HEAD`, snapshotted
before I touched anything and referred to below as **`R4T`**:

```
scripts/peer-sites.py             200766b1a8385b91b0ef60a32aae1219   71/71
scripts/mutations/peer-sites.json b0fbf3afa3a712e7e2fada3e25d0d62d   24 entries
scripts/check-plan-code.py        1a28a914e203c7b2f66503d525464829
scripts/check-fixture-variation.py d829a3d56b25fb6a50b2cc8c4d59c645  ← identical to 71378cd3
scripts/check-selftest-counts.py  508b3c24317732f70dc0b43d17940915  ← identical to 71378cd3
D .claude/hooks/peer-sites-advisory.sh    (staged deletion)
```

The tree did not move during this round. Every finding names `R4T` unless it says otherwise.

# Verdict: **CONVERGED.**

Four items to close before merge. **None is Blocking, none is High, all four are one-line changes,
and none of them is a reason to run round 5.** The delta is good work: the timeout cases are real,
the removal is clean, and the `else`-arm fix is the right fix and is ratcheted in both directions.

Trend: **19 → 14 → 2 → 4**, and the four are a parser edge with zero reach today, two
over-claiming test assertions, and two stale counts in a docstring. That is diminishing returns,
not a branch that is still moving.

---

## Your four delta items

### 1 · the r3 timeout work — **not theatre. But two of the four assertions claim more than they measure.**

**The good half, measured on `R4T`** (control 71/71, each mutation on a copy outside the repo).
Stripping `, timeout=30` from **each** call site individually now kills, via a named case:

```
line 368 (changed_lines)  KILLED 68/71  [FAIL] `changed_lines` bounds git at 30s: got [None, None] want [30, 30]
line 401 (_merge_base)    KILLED 68/71  [FAIL] …and so does `_merge_base`: got {None} want {30}
line 480 (main --diff)    KILLED 69/71  [FAIL] …and so does `main --diff`'s FIRST call…
```

r3's exact regression is closed. The fakes are captured per call site, so each case fails for its
own reason — that is the part I most expected to be weak and it is not.

**N2 (Low) — case 4's name is false.** It reads
*"…and there are no unbounded git calls left in this **module**"*, and its evidence is three
kwargs lists captured from three fakes. It cannot see a call site no case drives. Measured: I added
a fourth, unbounded `subprocess.run` to a copy —

```python
def _extra_git_call(ref):
    r = subprocess.run(["git", "-C", str(REPO), "rev-parse", ref],
                       capture_output=True, text=True)      # no timeout — the r2 R4 shape exactly
```

→ **SURVIVED, 71/71.** A case asserting a module-wide property is satisfied by three paths. This is
this project's *assert the PROPERTY, not the mechanism*, and the honest version is cheap: the file
already has `_src_of`, so `ast.parse` over its own source and assert every `subprocess.run` carries
`timeout` — which is exactly how Codex found the defect in the first place, and how I confirmed it.
*Falsifier:* the injection above turns the suite red.
*Siblings — searched.* I re-read every case name in the suite for the same "claims the module,
measures a path" shape. The other module-wide claim is *"exactly three container kinds are
implemented"*, which reads `containers()` over a fixture containing all three — that one is sound
because `containers` is the whole population. Case 4 is the only one.

**N3 (Low) — case 3's want is derived from its got.**

```python
case("…and so does `main --diff`'s FIRST call, the one that used to be unbounded",
     [k.get("timeout") for k in _kws], [30] * len(_kws))
```

`[30] * len(_kws)` is computed **from the subject**. Measured: the identical assertion over an empty
capture passes on zero evidence —

```
[30] * len([])  ==  []   ->  the probe case PASSED, suite still 71/71
```

Today it is rescued by siblings (`any("merge-base" in c for c in _calls)` requires the calls to have
happened), so nothing is wrong in the shipped tree. But `check-fixture-variation.py`'s own docstring
lists *"the WANT was derived from the subject"* as r2's finding on another file, and this is that
shape. A literal `[30, 30, 30]` costs nothing and removes it.
*Siblings — searched.* I checked the other two timeout cases: case 1 uses a literal `[30, 30]`
(sound, asserts cardinality too) and case 2 uses a set `{30}` (sound on value, silently loses
cardinality — a second `_merge_base` call would not be noticed). Case 3 is the only derived want.

### 2 · the removal — **clean. Verified rather than taken.**

| check | result |
|---|---|
| `check-fixture-variation.py` vs `71378cd3` | **byte-identical** — md5 `d829a3d5…` both sides |
| `check-selftest-counts.py` vs `71378cd3` | **byte-identical** — md5 `508b3c24…` both sides |
| `EXPECTED_MUTATIONS` keys whose file is gone | **none** (47 keys) |
| manifests on disk with no matching script | **none** (47 manifests, 47 keys) |
| declared total | `705 → 713`, matching `peer-sites.py: 16 → 24` |
| hook artefacts on disk | all three absent |
| `PEER_SITES_HOOK_DISABLE` / `PEER_SITES_BASE` / `peer_sites_hook` | **0 hits** anywhere |

The only live references to the removed component outside `docs/reviews/` are the two deliberate
ones — `docs/backlog.md:162` (#134, carrying the measurements) and the `peer-sites.py` docstring
citing the withdrawn caller. Nothing dangling.

### 3 · the docstring — **N4 (Low): two counts are stale, and they are stale in the section whose stated point is that the claims are measured.**

I re-ran every number the docstring states, against `R4T`, over the same 200-commit corpus:

| docstring claim | measured on `R4T` | |
|---|---|---|
| "4 of 12 `branches` containers are ONE idiom" | 4 of 12 | ✅ |
| "the tail runs to **32** lines" | 32 | ✅ |
| "**10** single containers print 9+ on their own" | 10 | ✅ |
| "**79** were silent and **5** spoke" | 79 / 5 | ✅ |
| "~22k lines of `.ts`/`.tsx`", "0 of the last 60 commits touched one" | 21,923 / 0 | ✅ |
| "0 `match` statements in the repo today" | 0 | ✅ |
| "**96** of 138 commits print NOTHING" | **93** of 138 | ❌ stale |
| "`exits`, which produced **61 of the 73** containers" | **67 of 79** | ❌ stale |

Both stale numbers are **my r1 measurements, taken against `52010914`** — and the thing that moved
them is the fix for my own r1 H1: `_span` + range intersection recovered 6 `exits` containers
(73 → 79) and made 3 more commits speak (96 → 93 silent). The docstring updated the *conclusion*
and kept the *counts*. `"70% of commits silent"` now rounds from 67%, which I would leave alone.

This is the project's *a measurement needs its CONTEXT, not just its value* — the numbers are
labelled "measured over 138 python-touching commits" with no subject, so nothing marks them as
belonging to a tree three rewrites ago.
*Siblings — searched.* I checked every other number in the file, listed above; those are the only
two that moved. I also checked the three places the r1 bounds were copied to
(`docs/review-method.md`, `docs/dashboard-entries.md`, the commit message) — they carry the
*bounds*, not these counts, so the fix is one file.

### 4 · the `else`-arm fix — **shut, and the cases die in both directions.**

All measured on `R4T`. The r2 asymmetry is gone — every arm is now its head:

```
 touch  3 (the `if` TEST)              -> SPEAKS
 touch  4 (INSIDE the if arm)          -> SILENT
 touch  6 (the else's 1st stmt HEAD)   -> SPEAKS
 touch  7 (INSIDE the else's 1st stmt) -> SILENT     <- r2 measured SPEAKS here
 touch 10 (the else's 2nd statement)   -> SILENT
```

The fused peer is gone. On B1's own fixture, touching line 8 now yields **only** the inner chain;
the outer `if x:` is no longer offered, and the outer members are `[(3,3), (6,6)]` rather than
`[(3,3), (6,9)]`.

**And the r2 "silencing" is no longer a defect — I checked the fair case rather than assuming.**
Touching `{3, 6}` still filters the outer chain, but now because both its members genuinely were
edited. Touching only line 3 makes it speak:

```
if/elif chain: you changed 1 of 2 branches
  > :3        if x == 1:
    :6        if x == 2:
```

Restoring `_span(cur.orelse[0])` kills **two** cases — one on behaviour, one on representation:

```
KILLED 69/71
  [FAIL] an edit to the INNER chain never offers the OUTER `if` as a peer: got True want False
  [FAIL] …because the `else` member is its head LINE, not its whole first statement
```

and the edit is shipped as a manifest entry (*"the `else` arm spans its whole first statement,
swallowing a nested container"*). Both directions covered.

---

## N1 (Medium class, Low reach) — the only new defect: `parse_hunks` drops a real `+` after a no-newline marker

`R4T`, `parse_hunks`. The counted walk is the right design and it closed r2's R5 properly — I
re-checked the two-file case and it now returns `[5, 50]`. But `\ No newline at end of file` falls
through to the **context** branch, and a context line spends one line of *both* budgets. Real `git
diff -U0`, where the old side had no trailing newline:

```
@@ -3 +3 @@ b
-c
\ No newline at end of file
+C

parse_hunks -> []        correct: [3]
```

```
@@ -3 +3 @@   ->  old_left=1, new_left=1, cursor=3
'-c'                  -> old_left=0
'\ No newline...'     -> else-branch: cursor=4, old_left=-1, NEW_LEFT=0
'+C'                  -> new_left > 0 is False  ->  NOT COUNTED
```

The docstring anticipates `\ No newline` and says it *"can never be counted as an added line however
much it looks like one"* — true, and the wrong failure mode. It is not counted; it **spends the
budget that the next real `+` needs**. A silent false negative, in the newly rewritten core, from
output git produces unprompted.

**Reach, measured: 0 of 59 `.py` files in this repo lack a trailing newline**, so this is latent, not
live. That is why it is not High.

**Candidate fix, verified — one line, no regressions:**

```python
if line.startswith("\\"):
    continue                       # `\ No newline at end of file` annotates; it spends nothing
```

| case | shipped | with the fix |
|---|---|---|
| old side no newline (**real git**) | `[]` | `[3]` |
| both sides no newline | `[]` | `[3]` |
| plain | `[3]` | `[3]` |
| two-file (r2 R5 regression check) | `[5, 50]` | `[5, 50]` |
| deletion-only | `[]` | `[]` |
| combined `@@@` | `[]` | `[]` |

⚠ **The suite is 71/71 both with and without the fix**, so it needs a case as well as the line.
*Falsifier:* `parse_hunks('@@ -3 +3 @@\n-c\n\\ No newline at end of file\n+C\n') == {3}`.
*Siblings — searched.* I enumerated every line shape the body walk can meet and asked which spend
budget they should not: `\` annotations (broken, above), `diff --git` / `index` / `+++` / `---`
**outside** a hunk (correctly unreachable now — the budget is spent), and a trailing `""` from
`split("\n")` (harmless, budgets already spent). The `\` line is the only one that lands *inside* a
live hunk. One instance, one fix.

---

## Carried, unchanged, and not worth another round

- **the `except` handler is its head, and that decision has no case** — mutating it to the handler's
  full body still **SURVIVES 71/71** on `R4T`. This is the backlog #131 design question (a member
  is its head), deliberately filed, and the docstring now states it as bound 2 with the 79/5
  measurement. Correctly parked.
- **`_span`'s `None` fallback is unfalsifiable** — still survives. I re-measured reach: `end_lineno`
  is `None` on **0 of 128,887** stmt/expr nodes. Belt-and-braces over an unreachable branch; leave it.

## Green on `R4T`, verified rather than taken

| check | result |
|---|---|
| `peer-sites.py --self-test` | **71/71**, rc=0 (matches the declared count) |
| `scripts/mutations/peer-sites.json` | **24 entries, 0 problematic** — unique name, anchor ×1, red, via the case each names |
| `check-fixture-variation` / `check-selftest-counts` / `check-docs` / `check-ratchet-contract` | rc=0 |
| `check-review-rounds` / `check-dashboard-entry` / `check-backlog-closure` | rc=0 |
| `check-plan-code --self-test` | **128/128**, rc=0; declared sum **713** over 47 files |

I did not re-run a full `--mutate .`; yours is in flight and the branch-specific half — the 24
peer-sites entries — I verified directly, which is the stronger measurement for this subject.

## Why `check-review-recorded` fails, and what will and will not fix it

Not a defect in the subject — but you asked, and the mechanism matters because the obvious fix is
the wrong one. `branch_verdicts()` (`:333-345`) returns *"the Codex verdicts THIS branch **ADDED**"*,
computed with `--diff-filter=A`. Measured:

```
committed additions to docs/reviews/verdicts/ : peer-sites-r1-codex.verdict.json
uncommitted (??)                              : peer-sites-r3-codex.verdict.json
```

The r3 verdict records `gate_ran: true`, `head: 71378cd3`, and a `dirty` list that **does** include
`scripts/peer-sites.py` and the other five guarded files. It is invisible solely because it is
untracked — so the guard falls back to r1's and correctly reports that r1 never saw those files.

**The uncommitted-until-both-halves-finish discipline and this guard's ADDED rule are in direct
tension: obeying one makes the other fail.** That is worth a backlog row on its own, independent of
this branch. ⚠ I am *not* predicting the gate goes green on commit — committing moves `HEAD` past
`71378cd3`, and I did not measure how the rule treats a verdict whose head is now the parent. Check
it rather than assume it; running a fifth round will not help if that is what is happening.

---

## Recommendation

**Ship it, after four one-line changes and two cases:**

1. N1 — skip `\` lines in `parse_hunks`, plus a case (the falsifier above).
2. N2 — make case 4 an AST sweep over `_src_of`, so its name becomes true.
3. N3 — replace `[30] * len(_kws)` with a literal.
4. N4 — correct `96 → 93` and `61 of 73 → 67 of 79`, and say which tree they were measured on.

None of these needs a reviewer to look again. N2 and N3 are in test code and cannot change delivered
behaviour; N4 is prose; N1 has a verified fix and a stated falsifier. **Do not run round 5 for them.**

⚠ **One shape worth naming before you stop, because it is the only argument against stopping.**
r2's R4 was *"a git call is unbounded"*; r3's finding was *"the fix for R4 was not ratcheted"*; r4's
N2/N3 are *"the ratchet r3 added over-claims"*. Three consecutive rounds, each finding a defect in
the previous round's fix, in one component. That is the literal shape of the thrashing trigger. **I
do not think it fires, and here is the test, applied:** thrashing is findings that come *back*; this
is one assertion being tightened, and each step is strictly smaller than the last — an unbounded
call in production code, then an unprotected fix, then a case name that overstates its evidence.
A redesign cannot remove N2 or N3; they are two literals. The trend is convergent, not oscillating,
and the right response is to close them and merge — which is what I am recommending.
