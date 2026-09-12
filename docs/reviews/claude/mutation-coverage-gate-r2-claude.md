# Claude adversarial review — branch `mutation-coverage-gate`, round 2

**Subject:** `git diff a5bfe9c5..c6d62f6c` (the round-1 fixes), in the context of
`git diff 7674fe87..c6d62f6c`. Branch `mutation-coverage-gate`, head `c6d62f6c`, base `7674fe87`.
Working tree clean at review time.

PROOF OF SUBJECT

1. The current `NO_CALLER_RE`, `scripts/check-ratchet-contract.py:127`:

```python
NO_CALLER_RE = re.compile(r"NO-CALLER:[ \t]+([A-Za-z][^\n]*)")
```

2. The body of `self_exemption()`, `scripts/check-ratchet-contract.py:516-519`:

```python
def self_exemption() -> tuple[bool, bool]:
    """(exempt-from-R4, exempt-from-R3) for THIS file's own source."""
    own = Path(__file__).read_text(errors="ignore")
    return bool(NO_MUTATIONS_RE.search(own)), bool(NO_CALLER_RE.search(own))
```

3. `scripts/mutations/check-ratchet-contract.json` holds **8** entries
(`python3 -c "import json;print(len(json.load(open('scripts/mutations/check-ratchet-contract.json'))))"` → `8`),
matching `EXPECTED_MUTATIONS["scripts/check-ratchet-contract.py"] = 8` at `scripts/check-plan-code.py:675`.

STATUS: COMPLETE

---

## Findings

### High — R4's escape is satisfiable from a COMMENT or a string literal anywhere in the file; R3's is not. The self-exemption route is closed for this file only, by a bespoke case, and remains open for the other 33 guards

**Where:** `scripts/check-ratchet-contract.py:283` (`check_manifest`, searches the full file text)
vs `:166-170` (`check_caller`, searches the module docstring); `self_exemption()` at `:516-519`.

**What:** Round 1's two Blockings had one root cause: **a non-declaration in a guard's source
satisfied R4's escape.** The first was the file's own docstring; the second was a *test fixture*
that spelled the marker out. The fix addressed both instances — tighten the pattern, assemble the
markers, add `self_exemption()` — but the mechanism that made them possible is untouched:
`check_manifest` applies `NO_MUTATIONS_RE` to `text`, the **whole file**, so a code comment, a
string constant, a docstring of any nested function, or a fixture grants the exemption. R3, the
rule this one is explicitly modelled on (`:239-240`: *"NO-CALLER works above… Same rule, same
shape, deliberately"*), parses the module docstring and accepts only a declaration there.

`self_exemption()` covers exactly one file — it reads `Path(__file__)`. Nothing asks the same
question of the other 33 guards.

**Failing scenario:** a guard author writes, in a comment explaining the mechanism,
`# NO-MUTATIONS: a pure wrapper, no branches to weaken` — not as a declaration, as prose about the
rule, which is precisely how the a5bfe9c5 defect was authored. That file is exempt from R4
permanently and silently. The same sentence written for R3 is correctly ignored.

**Evidence:** measured against the shipped functions (both fixtures carry a `--self-test` so they
are in-population; neither has a manifest and neither has a caller):

```
R4, escape in a COMMENT (no manifest): EXEMPTED — no violation
R3, escape in a COMMENT (no caller):  ['R3_no_caller']

R4, marker inside an unrelated STRING LITERAL: EXEMPTED — no violation
```

How close this sits to live code: `scripts/check-plan-code.py:664-665` carries, in a comment,
both ``NO-MUTATIONS: <why>`` and ``NO-MUTATIONS:` ``. Under the OLD pattern that file matched —
I re-ran old-vs-new across all 55 `scripts/*.py` and `check-plan-code.py` is one of only three
files whose match status changed:

```
('R4-fulltext', 'scripts/check-plan-code.py',      True, False)
('R3-doc',      'scripts/check-ratchet-contract.py', True, False)
('R4-fulltext', 'scripts/check-ratchet-contract.py', True, False)
```

It stops matching today only because the next character is `<` or a backtick. Had the comment read
`NO-MUTATIONS: a placeholder, see below`, `check-plan-code.py` would be exempt from R4 right now.
That file has a manifest, so the effect is masked — the same masking round 1 recorded for
`check-ratchet-contract.py` itself.

**Measured blast radius today: zero.** With the new patterns, no file under `scripts/` matches
either escape at all. This is a hole, not a live defect — which is why it is High and not Blocking.

**The fix is one line and makes the two siblings actually the same rule:** parse the docstring in
`check_manifest` as `check_caller` already does, and make `self_exemption()`'s R4 arm read the
docstring too so the case and the rule agree. No current escape declaration is lost — there are
none.

---

### Medium — round 1's Medium is half-closed: the acceptance divergence is gone, but both refusal messages now print an example the guard itself refuses

**Where:** messages at `scripts/check-ratchet-contract.py:177-178` (R3), `:286-287` (R4),
`:374-375` (widened R4).

**What:** Round 1 raised two things under one heading. The first — the siblings accepting different
strings — **is closed**; tightening `NO_CALLER_RE` identically brings them to parity (measured
below: 0 divergent rows over round 1's own probe set). The second was *"the refusal message should
name the rule (a reason must begin with a letter after a space)"*, and nothing in the round-1 fix
touched any of the three messages. The tightening doubled the surface: both escapes now refuse five
of seven plausible spellings, and each message's own worked example is one of the refused forms —
R4 says write ``NO-MUTATIONS: <why>`` and R3 says declare ``NO-CALLER: <reason>``, both of which
start with `<` and are rejected by `[A-Za-z]`.

**Failing scenario:** an author of a new guard reads the R4 violation, writes
``NO-MUTATIONS: `evaluate()` is pure; a mutation would only restate the self-test`` — backticked
identifiers are this repo's house style in every sentence — the gate stays red, and the message
says *"no written `NO-MUTATIONS: <why>`"* to someone who just wrote one. This repo's own recorded
rule is that a guard which BLOCKS is judged on its false positives
(`docs/plugins.md` / the selection-card guard's two rounds).

**Evidence:**

```
R4      R3       reason
REFUSE  REFUSE   `evaluate()` is pure; a mutation would only restate the self-test
REFUSE  REFUSE   3 lines of glue, no branches to weaken
REFUSE  REFUSE   "pure wrapper" - nothing to weaken
REFUSE  REFUSE   ⚠ prose match only; there is no suite
REFUSE  REFUSE   — the regex matched prose; there is no suite
ACCEPT  ACCEPT   the regex matched prose; there is no suite
REFUSE  REFUSE   <why>

divergent rows: 0
```

A one-clause addition to each message (*"the reason must begin with a letter after a space —
`NO-MUTATIONS: pure wrapper…`, not a backtick, a dash or a placeholder"*) closes it.

---

### Low — `check-plan-code.py:2988` says "The six cover …" while eight entries exist, and the enumeration lists only the original six

**Where:** `scripts/check-plan-code.py:2986-2991`.

**What:** The round-1 fix updated two numbers in this paragraph (`549 -> 557`, `SIX` → `EIGHT`) and
left a third stale one sentence later. The enumeration that follows describes exactly entries 1–6;
neither of the two entries the fix ADDED — *"R3's escape accepts prose again…"* and *"the debt-PAID
arm is dropped…"* — appears in it.

**Failing scenario:** a reader auditing coverage counts the enumerated mechanisms, gets six, and
concludes two entries are undocumented duplicates — or deletes one believing the list is complete.
Nothing mechanical reads this prose, so it stays wrong indefinitely.

**Evidence:** verbatim, `scripts/check-plan-code.py:2986-2991`:

```
    # ⟳ 2026-09-12, SAME DAY, second slice: 549 -> 557. `check-ratchet-contract.py` joins with
    # EIGHT — the guard enforcing R4 had exempted itself since it was written, because the regex for
    # the written escape matched its own documentation of that escape. The six cover the widened
    # population (guards excluded, self-test required), the debt pin in both directions, the
    # NOT-EXAMINED clause that keeps an empty corpus from reading as paid, the evaluate() wiring,
    # and the escape regex itself.
```

This is the paragraph whose *subject* is a number that was wrong three times. Base `7674fe87`
declared 549, `a5bfe9c5` declared 555 with six entries, head declares 557 with eight — all
verified; only the sentence is stale.

---

### Low — `self_test()`'s `total` adds a hand-written `+1`, so deleting the self-exemption assertion leaves the suite printing "35/35 passed" over 34 cases

**Where:** `scripts/check-ratchet-contract.py:687-689`.

**What:** Every other term in `total` is a `len(...)` of the table it counts. The self-exemption
case is counted by a literal `+ 1`. Remove the assertion and leave the `+1` and the suite is
internally consistent, green, and reports a case count that includes a case that no longer exists —
and `check-selftest-counts.py` compares the docstring's `# 35 cases` against that same printed
total, so it stays green too. This is the shape the branch exists to close, one layer out: a suite
reporting success about work it did not do.

**Failing scenario:** a refactor drops the ad-hoc block (it is the only non-table case in the file
and reads like a stray). `--self-test` says 35/35, `check-selftest-counts.py` says verified, and
the round-1 Blocking's only durable guard is gone from every direct check.

**Evidence:** measured on a staged copy with the five-line assertion removed and `+1` untouched:

```
after deleting the assertion (keeping +1): rc=0  self-test: 35/35 passed
```

**Defence in depth holds, and that is why this is Low, not High.** On the same tree, manifest
entry 7 stops being killed:

```
  mut 7: rc=0 attributed=False fails=[]      # SURVIVED
```

so `check-plan-code.py --mutate .` goes red. The suggested fix is to make the case table-driven (or
count it via a counter) so the arithmetic cannot outlive the case.

---

### Low — two comments authored by the same fix contradict each other about where `_NC` is defined

**Where:** `scripts/check-ratchet-contract.py:433-435` vs `:129-136`.

**What:** `:434-435` says *"`_NC` is defined near the escape cases; this f-string keeps the literal
out of the source"*. `_NC` is at `:136`, ~400 lines earlier, and `:129-131` says it is deliberately
there: *"defined HERE, beside the patterns they mirror, because the first fixture that needs them
appears long before the escape cases do."* A reader who follows the first comment looks in the
wrong place for the definition of the mechanism the whole round-1 fix rests on.

**Evidence:** `grep -n "_NM\b\|_NC\b" scripts/check-ratchet-contract.py` → definitions at `:135-136`;
`ESCAPE_CASES` at `:547`.

---

## Round 1 findings — closed or not

| # | Round 1 finding | Status |
|---|---|---|
| 1 | **Blocking** — self-exemption relocated into `ESCAPE_CASES` | **CLOSED.** Verified at `a5bfe9c5` the new regex matched its own fixture at line 500 (`NO-MUTATIONS: a pure wrapper, no branches to weaken`). At head, `self_exemption()` returns `(False, False)`, and neither pattern matches anywhere in the source (`findall` → `[]`, `[]`). Falsified in both directions on a staged copy: appending an R4 escape → `got (True, False)`, `34/35`; an R3 escape → `got (False, True)`, `34/35`; restored → `35/35`. It reads the STAGED file — proven by mutation 7, which reddens only that case |
| 2 | **Blocking** — `NO_CALLER_RE` had the identical hole | **CLOSED.** `:127` now `NO-CALLER:[ \t]+([A-Za-z][^\n]*)`; the old pattern matched the module docstring at `a5bfe9c5` (`R3 old-regex docstring match: True`), the new one does not. Old-vs-new across all 55 scripts: the only docstring-level status change is this file's own. `gen-backlog-page.py` changes at full-text level only and R3 reads the docstring, so no other file's verdict moves |
| 3 | **High** — "TENTH file" ordinal; "seven printers" | **CLOSED.** The ordinal is gone from both the dashboard entry and `check-plan-code.py:672-674`, replaced by a derivation command that works (`git log -S'[FAIL] ' --reverse … -- scripts/check-ratchet-contract.py` → `a5bfe9c5`, `c6d62f6c`). "Seven" → "**Five**", and five is right: `git diff 7674fe87..a5bfe9c5` removes exactly five `print(f"  FAIL {name}"…)` lines |
| 4 | **Medium** — `m4_catalog.py rc=0` was CANNOT-RUN read as success | **CLOSED.** All eight re-run by me, one at a time; every recorded result matches the comment at `:305-313` exactly: `explainer-serve 88/88`, `codex-review 63/63`, `build-m4-schema 22/22`, `verify-exclusion-reasons 11/11`, `prior-art PASS`, `m4_catalog rc=0 and **0 bytes**`, `gen-m4-manifest rc=1 CANNOT RUN`, `subject_status rc=1 16/17`. The "FOUR" → EIGHT correction is right: `WIDENED_MANIFEST_DEBT` at `:331-340` lists exactly those eight |
| 5 | **Medium** — sibling escapes diverge / message cannot explain a rejection | **HALF-CLOSED.** Parity fixed (0 divergent rows); the messages are untouched. Carried forward as the Medium above |
| 6 | **Low** — no mutation exercises the `R4W_debt_paid_not_recorded` arm | **CLOSED.** Entry 8 does, and kills via exactly the named case |

Round 1's own added claims, re-measured (this session's 0-for-6 on historical claims did not
extend to a seventh — all checked out):

- *"hide the manifest and the gate goes red on itself"* — **true.** On a clean `git archive HEAD`
  tree with `scripts/mutations/check-ratchet-contract.json` deleted:
  `scripts/check-ratchet-contract.py [R4_no_mutation_manifest] … RATCHET FAILED … 1 vs baseline 0`, rc=1.
- *"`subject_status.py --self-test` is RED on master (16/17)"* — **true.** The branch does not touch
  that file (`git diff --name-only 7674fe87..HEAD` has no hit) and it is byte-identical to `master`.

---

## Checked and found sound

- **All 8 mutations kill via the case each names, over a control proved green first.** Staged
  `git archive HEAD`, applied each entry's edits, ran `--self-test`, parsed with the *imported*
  `check-plan-code.parse_fail_names` (not a re-implementation). Control `rc=0`, `35/35 passed`;
  every entry `rc=1`, `attributed=True`. Every anchor occurs exactly **once** (checked with
  `src.count(find)`, the same predicate `run_mutations` uses at `check-plan-code.py:1144`).
- **Entry 8's `for path in []:` is not a readability hazard.** Mutations are applied to a `copytree`
  of `HARNESS_TREE` and reverted line-by-line in `run_mutations`; the text never exists in the repo.
  It is also the weakest edit that reddens only the named case — it deletes the arm without touching
  the `Violation` construction a reader would need to understand.
- **Assembled literals survive a formatter.** No Python formatter is configured in this repo (no
  `pyproject.toml`, `setup.cfg`, `ruff.toml`, `.pre-commit-config.yaml`; no `ruff`/`black` reference
  in `package.json` or `.github/workflows/`). And joining them is harmless anyway: I rewrote
  `_NM = "NO-" "MUTATIONS:"` → `_NM = "NO-MUTATIONS:"` (and `_NC` likewise) on a staged copy and
  measured `NM match in joined source: False  NC: False`, suite `35/35 passed` — because the joined
  literal is followed by `"`, not by a space and a letter. The `ESCAPE_CASES` f-strings reference
  `{_NM}`, so they hold no literal either way.
- **`__file__` resolution is not a route back in.** `stage_tree` (`check-plan-code.py:207-216`) uses
  `shutil.copytree` with default `symlinks=False`, so the staged tree holds real copies, not links
  that would send `read_text()` back to the repo original. The `.pyc` is irrelevant —
  `self_exemption` reads source text, and a directly-run script's `__file__` is the `.py` path.
- **The self-exemption case IS reached by CI**, by three independent routes, none of which is a
  direct `--self-test` step (there isn't one in `ci.yml` for this file): `check-selftest-counts.py`
  at `ci.yml:274` *runs* each declared-count suite ("37 script(s) declare a count, every one
  verified by running it", and `check-ratchet-contract.py` is in `POPULATION`); `check-plan-code.py
  --mutate .` at `ci.yml:379` proves a green control per target and hard-fails otherwise
  (`control_is_green`, `:1055-1061`); and the gate itself runs at `ci.yml:193`.
- **Arithmetic, all consistent with disk:** manifest length 8; `EXPECTED_MUTATIONS[…] == 8`;
  `sum(EXPECTED_MUTATIONS.values()) == 557` and the pinned case asserts 557; docstring `# 35 cases`
  and the suite prints `35/35`; `check-ratchet-contract.py` is in `check-selftest-counts.POPULATION`
  (`:89`). Cross-checked **every** manifest on disk against `EXPECTED_MUTATIONS`: 42 files, zero
  mismatches, zero keys without a manifest. `549 → 555 → 557` traced through `7674fe87`, `a5bfe9c5`,
  head.
- **The four new `check-fixture-variation` exemptions are non-vacuous.** Spot-checked two by
  deleting them on a staged copy; each reintroduces exactly its own named finding
  (`widened_debt_drift(examined=…) is passed the SAME value at every call site`;
  `discover_self_tested_nonguards(texts=…) …`), rc=1 both times.
- **Every gate I was asked to run is green** on the working tree: `check-ratchet-contract.py`
  (34 guards, OK), `--self-test` 35/35, `check-fixture-variation.py` (457 params / 49 files) and
  its 60/60, `check-selftest-counts.py` and its 18/18, `check-plan-code.py --self-test` 128/128.
  Also green: `check-docs.py`, `check-review-rounds.py`, `check-dashboard-entry.py`,
  `check-gate-falsifiability.py`. Per instruction I did **not** run `--mutate .`.
- **`self_exemption()`'s R3 arm is deliberately broader than R3 itself** — it searches the full
  source where `check_caller` parses the docstring. That is the fail-CLOSED direction and the
  comment at `:510-515` claims it on purpose (*"by ANY route: prose, fixture, or a comment"*). The
  docstring's `(exempt-from-R4, exempt-from-R3)` is loose about it, but nothing is weakened.
  Note the asymmetry it exposes, which is the High above: the R4 arm is broad because the RULE is
  broad, not because the case chose to be.
- **The dashboard entry's factual claims check out**: five pre-existing broken printers, 8/8
  mutations, suite 35 cases, `549 → 557`, "hide the manifest and the gate goes red on itself".

---

## Verdict

NOT-CONVERGED

Both round-1 Blockings are genuinely closed, and closed with a mechanism rather than a convention —
`self_exemption()` is falsifiable in both directions, reads the staged copy, and has a manifest
entry that survives if it is deleted. The branch's arithmetic is clean and every historical claim I
re-measured held.

What blocks convergence is the class the fix stopped one step short of: after this branch a guard
can still exempt itself from R4 by writing a sentence in a comment, because R4 reads the whole file
where its declared twin R3 reads the docstring. Zero files are affected today, so it is a hole
rather than a defect — but it is the same hole, in the same rule, that produced both round-1
Blockings, and the guard that now catches it catches it for one file by name.
