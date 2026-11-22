# Architecture review — `check-inventory.py`'s input-validation layer

- **Date:** 2026-11-22
- **Convened on:** THRASHING (backlog #699) — three review rounds on PR #618, each finding an input the previous
  round's fold did not anticipate, all in one component.
- **Subject:** `scripts/check-inventory.py` at commit `7157b391` (branch `marketplace-task19`): `_read_json`,
  `_read_text`, `ROW_SCHEMA` and `_shape_errors`, `_finite`, `_check_inputs`, the scan/map coverage checks in `load`,
  and every message that prints an input value.
- **Reviewer:** Claude (Fable 5.2), one agent, no second half.
- **Legend:** **[M]** = a command I ran at `7157b391` (Python 3.14.4, macOS). **[I]** = inferred, not run.
- **Prototypes, corpus and raw output:**
  `/Users/kujinlee/.claude-tmp/claude-501/-Users-kujinlee-code-agentic-ai-docs-youtube-playlist-summaries-cloud/b387c8e6-9003-42f5-a944-1d4eb1de0c9b/scratchpad/task19/p6/`
  (`build.py` builds `variants/{headN,a,b,c}.py` from `variants/head.py`; `variants/c2.py` is the recommended form;
  `attack.py` is the 66-case corpus, output in `attack-out.txt`; `fuzz2.py` is the fuzz).

---

## 1. Verdict

**A redesign removes the thrash. Fold candidate (c).** The hand-written check list is a floor: it missed a new
input class in every round, and it misses five more today that no round reported.

| Question | Answer |
|---|---|
| Can a redesign remove the thrash? | **Yes.** Candidate (c) passes all 66 corpus cases bar one mislabelled expectation, and a fuzz of 6,334 to 11,604 edits per tree reaches no traceback. [M] |
| Is the remaining risk a floor? | **Yes, for a list of checks.** HEAD has 13 tracebacks and 7 fail-open results on the corpus; 5 of the classes are new in this review. [M] |
| Smallest structural design | Three statements, each made once: a **bounded reader**, **one walker over a declared shape per file**, and **total output with a soundness net**. |
| Recommended | **Candidate (c)**, in the form of `variants/c2.py`. Candidate (b) is refused for this fold and filed as a follow-up. |

What "structural" buys: at HEAD the property "no input reaches a traceback" is the conjunction of 26 raise sites in
the layer and 17 `!r` renderings. In (c) it is three properties, and the fuzz asserts the third is never needed.

---

## 2. The arming evidence, re-run

Each round's reproducer, and what the same fuzz finds at each earlier commit. [M]

| Round | Finding | Fold | Result at HEAD |
|---|---|---|---|
| r1 | no shape check: a wrong type reaches a rule | `ROW_SCHEMA` + `_shape_errors` | closed |
| r2 X1 | `10**400` in a cost: `OverflowError` | `_finite` | closed |
| r2 X2 | a finding `{"id": []}`: `TypeError` | `_check_inputs` | closed |
| r3 C1 | deeply nested JSON parses, then `repr` in a message raises `RecursionError` | not folded | **10 traceback sites**, rc 1 |
| r3 C2 | a component's `package` names no package; duplicate ids | not folded | **rc 0, "OK: 46 rows, 0 errors"** |

The thin fuzz (12 values per JSON node, 2,054 runs, 1 second) run against each committed version of the file:

| Commit | What it was | Escaped exceptions |
|---|---|---|
| `209f4f62` … `c9b00d61` | before r1's fold | **255** (AttributeError, TypeError) |
| `96ac3fbd` | r1 fold | **105** (the r2 findings among them: `{"id": []}`, `10**39` cost) |
| `d56f267c` = HEAD's layer | r2 fold | **3** (`UnicodeEncodeError`, a lone surrogate in an id) |
| candidate (c) | — | **0** |

So one mechanical instrument would have reported r1's and r2's findings before either review round. It does not find
r3 C1 (a 40-deep value does not exhaust `repr`; that needs thousands of levels) and cannot find any fail-open, since
it has no oracle for "should have been refused". The corpus covers those. That bound is restated in section 6.

---

## 3. The mechanism — three causes, not one

**Cause 1 — the value domain is unbounded.** `_read_json` returns whatever `json.loads` accepts. Every downstream
function (`repr`, `==`, set membership, `print`) is assumed total over that, and none is.

- Depth: `RecursionError` "while getting the repr" at lines 516, 482, 478, 480, 476, 484, 219, 346, 354, 409. [M]
- A lone surrogate (`"\ud800"`) in a row id: `UnicodeEncodeError` at print. **New.** [M]
- A repeated JSON key: Python keeps the last and says nothing. A component with two `package` keys is rc 0; two
  `rows` keys is rc 1 "46 inventory error(s) over 0 rows". **New.** [M]
- Decoding follows the locale: a UTF-8 inventory with a non-ASCII character under `LC_ALL=C PYTHONUTF8=0` is rc 2 at
  HEAD (fail-closed, but the guard's answer depends on the caller's environment). **New.** [M]

**Cause 2 — a vocabulary is missing wherever a rule compares with a literal and a miss is silent.** `_check_inputs`
checks types only.

- Line 304: `ctx.channels.get(package) == "plugin"`. A channel spelled `Plugin` skips the SHIP-experiment rule: an
  unbacked SHIP is rc 0. **New.** [M]
- Line 260: `not any(v in ("fail", "CANNOT RUN") for v in pcs.values())`. A pass condition spelled `FAIL` or
  `failed` backs a SHIP: rc 0. Controls: all `pass` is rc 0, `fail` is rc 1 `[ship-experiment]`. **New.** [M]
- r3 C2 is the same shape: `.get(package)` on a name that resolves to nothing returns `None`, and `None != "plugin"`.

**Cause 3 — output is not total.** The messages contain `§`, `·` and `—`. Under `PYTHONIOENCODING=ascii` a
`[shape]` error and `--render` both end in `UnicodeEncodeError`, rc 1. **New.** [M]

A traceback is rc 1, and rc 1 is this guard's code for "row errors". So every cause-1 and cause-3 failure is read
by a caller as a verdict on the inventory.

Why the list cannot converge: each check in `_check_inputs` names one field and one wrong type. The set of fields is
finite; the set of ways a value can be unfit for `repr`, `print`, or a literal comparison is not enumerated anywhere,
so each round supplies a member. [I]

---

## 4. Candidates, measured

All five were built from the same HEAD file by exact-string patches. [M]

| | What it is | Self-test | Corpus (66): ok / traceback / fail-open / wrong | Fuzz over the Task-20-shaped tree (6,334 runs) |
|---|---|---|---|---|
| **head** | `7157b391` | 267/267 | 43 / 13 / 7 / 3 | 3 crashes |
| **headN** | head + net + total output only | 267/267 | 46 / 0 (10 caught by the net) / 7 / 3 | not run |
| **a** | bounded reader + two hand checks for C2 | 267/267 | 59 / 3 / 4 / 0 | 3 crashes |
| **b** | bounded reader + `check-shipping-sets.load_map` | **244/267** | 56 / 4 / 2 / 4 | 3 crashes |
| **c** | bounded reader + shapes + walker + reference rules + net | 267/267 | 65 / 0 / 1* / 0 | **0 crashes, 0 net** |

\* The one case is my own wrong expectation: a component `phase` outside the vocabulary in the **map**. No rule in
this script reads the map's `phase` (only `row["phase"]`), and `check-shipping-sets.py` owns that vocabulary. [M]

Further measurements on (c), in its `c2` form:

- Live tree (`r3-claude-work/live`): rc 1, exactly 34 `[missing]`, 35 lines. Task 20 trees `t20a`, `t20b`: rc 0. [M]
- Fuzz over the self-test-sized tree: 6,764 runs, two seeds, and 11,604 over a second fixture: zero crashes, zero
  net. [M]
- `check-ratchet-contract.py`'s `fail_open_handlers` returns `[]` for it; the control (a handler returning 0)
  returns `[5]`. The net is not a fail-open handler by the ratchet's own rule. [M]
- Layer size: head 110 lines, 26 raise sites, 17 `!r`. (c) 137 lines, 11 raise sites, 0 `!r` before the self-test
  in `c2`. [M]

**Why not (a).** It closes cause 1 only. Channel typo and both pass-condition typos stay rc 0, and the three output
tracebacks stay. It is the next round's finding list.

**Why not (b), in this fold.** [M] unless marked.
- `load_map` requires each component's `files` to exist under the root. 23 self-test cases build fixture trees whose
  components name no files, so they go rc 2. Every fixture would need a file tree.
- `load_map` is itself not total: a component `package` of `[]` is `TypeError: cannot use 'list' as a dict key`.
- It reads with the locale's encoding.
- It does nothing for the sidecar, the scan or the pass-condition vocabulary, so (c)'s walker is needed anyway.
- It does close the channel typo and the package typo, and it is the right owner of the map. That is a real
  argument, for a later slice: see 5.5.

**Why not headN alone.** The net turns 10 tracebacks into rc 2, which is honest, but all 7 fail-opens remain. A net
is the backstop for the property, not the property.

---

## 5. Recommendation — fold candidate (c)

The reference implementation is `variants/c2.py` in the prototype directory. The builder should port it, not
re-derive it.

### 5.1 Delete

- `_check_inputs` (lines 460–516), whole.
- The `shapes` loop in `load` and any helper only `_check_inputs` used (`_str_or_null` if nothing else reads it).
- Every `!r` on an input value before the self-test (23 sites: `row_errors` 18, `inventory_errors` 3,
  `_shape_errors` 1, the reader 1). Each becomes `_show(...)`.

`ROW_SCHEMA`, `_shape_errors` and `_finite` stay as they are. They are already declarative, their 18 mutations
resolve unchanged, and the row schema reports rc 1 per row where the file shapes report rc 2. [M]

### 5.2 Add

1. **The bounded reader.** `_read_json` reads bytes and decodes UTF-8; refuses NaN/Infinity (kept), a repeated key
   (`object_pairs_hook=_unique_keys`) and nesting deeper than `MAX_DEPTH = 32`, by an iterative walk. `_read_text`
   reads bytes and decodes UTF-8. The live inputs nest at most 6 deep. [M] (The prototype's comment says 7; fix it.)
2. **`FILE_SHAPES` and `_violations`.** One shape per input file, built from six constructors over five shape kinds (`_is`, `_one_of`,
   `_null_or`, `_list_of`, `_map_of`, `_obj`). `_violations(shape, value, at)` recurses on the shape, never on the
   data, and prints a value only through `_show`.
3. **Two vocabularies.** `CHANNELS = ("plugin", "reusable-workflow")` and
   `PASS_VALUES = ("pass", "fail", "argued", "CANNOT RUN")`, each used through `_one_of`, which matches by type and
   value. The live sidecar holds exactly `fail` 21, `pass` 27, `argued` 117; `CHANNELS` equals
   `check-shipping-sets.py` line 180. [M]
4. **`_reference_errors`.** The three rules a shape cannot state because each relates two places: a duplicate
   component id, a `package` that `packages` does not have, a map component the scan has no entry for.
5. **`_show(v)`.** A container prints as "a list of N" / "an object with N keys"; anything else as its `repr`, cut
   to 60 characters.
6. **Total output and the net.** `main` reconfigures stdout and stderr with `errors="backslashreplace"`, then calls
   `_main` inside `except Exception`, which prints
   `INTERNAL ERROR: check-inventory.py raised <Type> at line <n>; … CANNOT RUN — treat this check as NOT RUN.` and
   returns 2. The message deliberately does not start `CANNOT RUN: `, so a case asserting a named refusal cannot be
   satisfied by the net.

### 5.3 Self-test cases

All 267 existing cases pass unchanged against the prototype. [M] Add, each with its adjacent negative:

| Case | Negative beside it |
|---|---|
| a component whose `package` names no package is rc 2 | the same map with the package present |
| two components with one id is rc 2 (identical, and differing in effort) | distinct ids |
| channel `Plugin` is rc 2 | `plugin` |
| pass condition `FAIL` is rc 2; `failed` is rc 2 | `fail` is rc 1 `[ship-experiment]`; all `pass` is rc 0 |
| a repeated key in an object is rc 2 (in `components.json` and in `inventory.json`) | the key once |
| nesting of 33 is rc 2 | 32 is read |
| a lone surrogate in a row id prints escaped, with the row's rc | — |
| an ASCII-only stdout: a `[shape]` error and `--render` print, no traceback | — |
| a UTF-8 non-ASCII inventory is read under `LC_ALL=C` | — |
| an exception inside `_main` is rc 2 and prints `INTERNAL ERROR` | no `CANNOT RUN: ` prefix on that line |
| `CHANNELS` equals `check-shipping-sets.CHANNELS`, by import | — |
| **the fuzz**: every node of every fixture input replaced by each of 12 values, deleted, duplicated; no exception escapes `main` and no output contains `INTERNAL ERROR` | the same fuzz against a reader with the surrogate handling removed reports a crash (this is the mutation) |

The fuzz is 2,054 runs in 1 second on the fixture tree, against a self-test that takes 0.4 seconds. [M]

### 5.4 Mutations (`scripts/mutations/check-inventory.json`, a two-file edit)

- 124 mutations today, all resolving at HEAD. Against (c), **25 no longer resolve**: 24 of the 25 anchored in
  `_check_inputs` (all but "a scan missing a component is read as no findings") and "the JSON constants are
  numbers", whose reader line changed. Replacing `!r` with `_show` breaks none beyond those. [M]
- Re-anchor each of the 24 on its `FILE_SHAPES` entry (weaken the leaf: `_ID` to `_ANY`, drop a field), naming the
  same case it names today.
- Add one mutation per new rule: the depth bound removed; `_unique_keys` removed; `_one_of` matching by value only;
  each `_one_of(*CHANNELS)` and `_one_of(*PASS_VALUES)` weakened to `_STR`; each of the three reference rules
  removed; the net returning 1; `backslashreplace` removed; `read_bytes().decode("utf-8")` back to `read_text()`.
- Then run the all-manifest anchor resolve, since this edit unbinds anchors by construction.

### 5.5 File, do not fold

- **One map reader for both scripts.** `check-shipping-sets.load_map` and this layer both read `components.json`.
  The honest end state is one reader, total, with `files` existence as a separate step. It needs a `--root`-aware
  `load_map` and fixture trees with files: a slice, not a fold. Until then the `CHANNELS` equality case keeps the
  two from drifting.
- **`load_map` is not total** (`package: []` is a `TypeError`). A finding against `check-shipping-sets.py`.
- **A row's `phase` is not compared with the map's.** Flipping a row between `"1"` and `"later"` is accepted rc 0
  on the fixture tree. This is a rule-layer question for the spec, outside this subject. A lead, not a finding.

### 5.6 What the plan's Task 19 text should say

Replace the "inputs unreadable or absent → 2" clause of the exit-code paragraph with:

> **Inputs are read by one bounded reader and one walker.** `_read_json` returns a value that is UTF-8, free of
> NaN/Infinity and repeated keys, and at most `MAX_DEPTH` deep; `FILE_SHAPES` declares, per input file, every field
> a rule reads, and `_violations` is the only code that checks one. A field a rule compares with a literal is
> declared `_one_of` its vocabulary. A rule relating two places lives in `_reference_errors`. Any failure of these
> is **rc 2**. No message prints an input value except through `_show`. `main` is a net: an unanticipated exception
> is rc 2 with `INTERNAL ERROR`, never Python's exit 1. **Adding a rule that reads a new input field means adding
> that field to `FILE_SHAPES` in the same commit; a hand-written `isinstance` check in `load` is a defect.**

And add to the cases list: the table in 5.3.

---

## 6. FAILS IF, bounds, and the stop condition

**FAILS IF** (each is an observation, runnable after the fold):

- any of the 66 corpus cases in `attack.py` ends in a traceback, or any case returns rc 0 where the corpus expects a refusal;
- the self-test's fuzz case reports an escaped exception or an `INTERNAL ERROR` line;
- the live tree is anything other than rc 1 with exactly 34 `[missing]` (until Task 20 completes the rows);
- `grep -c '!r}'` over the file above `_self_test` is not 0;
- a function named `_check_inputs` exists, or `load` contains an `isinstance` call;
- the mutation manifest has an anchor that does not resolve.

**Bounds — what this design does not give:**

- The fuzz proves no escape **for the values it tries**. It found r1's and r2's classes and the surrogate class at
  the commits that had them; it did not find the depth class and cannot find a fail-open.
- `FILE_SHAPES` covers the fields rules read **today**. A new rule reading an undeclared field is caught only by the
  fuzz (as a crash) or not at all (as a silent `.get`). The plan sentence in 5.6 is a convention, not a machine.
- The net catches `Exception`. `MemoryError` on a huge input, `KeyboardInterrupt` and a killed process are not
  caught; none of them is exit 1 with a verdict's shape. [I]
- `_one_of` closes a vocabulary only where one is declared. Two are. A third literal comparison added later is
  cause 2 again.
- Message length is bounded per value (60 characters), not per run: 10,000 bad rows print 10,000 lines.

**Stop condition.** After this fold, one review round. If it finds an input that reaches a traceback or rc 0 where a
refusal was due, **and** the fix is another entry in a list (rather than a shape entry or a vocabulary), the design
has not held and the question returns here. A finding fixed by adding one line to `FILE_SHAPES` is the design
working, and is filed, not thrash.

---

## 7. What did we decide that is not written down

- **rc 1 means "row errors", so a traceback is a false verdict.** Nothing states that Python's own exit code
  collides with this guard's. The net makes it true by construction; the plan should say why it exists.
- **A typo in a vocabulary is unreadable input, not "the other value".** The spec gives the pass-condition values
  in prose; no document says an unlisted spelling must refuse. This review decides it does (rc 2).
- **The inventory guard trusts the map's own guard.** `check-shipping-sets.py --map` runs in CI (`ci.yml` lines
  937–944) [M], and this script re-checks only the map fields its own rules read. That division is nowhere stated;
  5.5's follow-up would remove the need to state it.
- **Depth 32 is a decision, not a measurement of need.** The live maximum is 6. [M] Any bound under a few hundred
  keeps `repr` total; 32 was chosen to be far above the data and far below the stack.

---

## 8. Not measured — treat as NOT RUN

- The full mutation sweep against candidate (c). Only anchor resolution was counted; no re-anchored mutation was
  run red.
- Linux, CI's Python version, and Windows consoles. Every [M] is macOS, Python 3.14.4.
- A second reviewer half. This is one agent's review.
- The fuzz over the Task-20-shaped tree for `headN` and `c2` (run for head, a, b, c only; `c2` was fuzzed on the two
  fixture trees).
- Spec §4/§4b/§4c against `ROW_SCHEMA`, field by field. `ROW_SCHEMA` was kept, not re-audited.
- `check-ratchet-contract.py` as a whole against the folded file; only its `fail_open_handlers` function was run.
- The row-`phase` lead in 5.5.
- Inputs too large for memory.
