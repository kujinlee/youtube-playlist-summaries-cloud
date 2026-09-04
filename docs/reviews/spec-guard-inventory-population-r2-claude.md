# Spec review — `2026-09-02-guard-inventory-population-design.md` v2 (`00981678`)

**Round 2, Claude half.** Branch `fix/guard-inventory-population`. Reviewed 2026-09-02.
**Scope:** round 1's own fixes — §3's grammar, §4's criterion, §5's change list, §7, §9's falsifiers.

**Method.** Every finding is a `file:line` quote or executed output. §5 was implemented in a
throwaway copy at `/Users/kujinlee/.claude-tmp/gip-r2/repo` (all ten in-file items, plus the 16
`NOT-A-GUARD:` docstring lines), and a second copy at `.../gip-r2/v1` identical except for v1's
unanchored `NOT_A_GUARD_RE`, so the two grammars could be run against the same probes. No `git`
mutation, no Postgres, no schema gate; the live tree was read only.

---

## Blocking

### B1 — §10's mutation manifest CANNOT go green: the contract prints `FAIL`, and the harness only parses `[FAIL] `

`scripts/check-plan-code.py:723-724` is the only place red case names come from:

```python
fails = [l.strip()[7:].rsplit(": got ", 1)[0].strip()
         for l in out.split("\n") if l.strip().startswith("[FAIL] ")]
```

`scripts/check-ratchet-contract.py` never emits that shape. All five of its failure prints are
`:343`, `:348`, `:353`, `:358`, `:375` — `print(f"  FAIL {name}\n       expected …")`. It contains
**zero** occurrences of `[FAIL] `; every one of the seven scripts already in the manifest contains
between 1 and 18.

**Observation — the parser run against the contract's real red output** (implemented copy, anchor
dropped, which is §10's third mutation):

```
  FAIL a docstring that DOCUMENTS the rule does not declare
       expected ['scripts/check-doc.py']
       got      []
self-test: 21/23 passed        rc=1
check-plan-code parses fails = []
```

So `caught` is True but every `expect` entry resolves to **0** red cases, and
`check-plan-code.py:778-786` fails the mutation with *"matched 0 red case(s) — it was caught by
something else: []"*. §10 specifies exactly this shape and underlines it: *"Each `expect` entry must
name **exactly one** red case (`check-plan-code.py:739-746`)"*. All three of §10's mutations land on
that branch. `--mutate .` is what CI runs (`dev-process.md`), so the PR cannot be green.

The only way through the tool without changing the contract is to omit `expect` entirely — `want =
mut.get("expect")` leaves `wants = []` and the check passes on the exit code alone. That is the
fail-open the round-5/round-6 comments above it were written to close, and §10 forbids it in its own
⚠ note.

**Why Blocking, and why it is a round-1 regression:** §5 is titled *"The complete change surface"*
and its ⛔ box says v1's §5 *"omitted the single line where the narrowing physically happens"*. v2
fixes that line and omits a different load-bearing edit — the self-test's output format — required by
the section of the same document that adds the mutation coverage. This is also the repo's recorded
`a-report-format-is-a-CONTRACT` failure verbatim: *"12 mutations reported '0 red cases' over a
failure LINE SHAPE the harness doesn't parse."*

### B2 — §4's criterion does not derive `build-m4-schema.py` IN; applied faithfully it gives 2 IN / 17 OUT and the count is **28**, not 29

The criterion (`spec:225`): *"A script is a guard if it has a mode whose only product is a VERDICT
about a subject other than itself"*, with the explicit exclusion (`spec:230-231`): *"Assertions that
protect a script's own output are **self-protection, not policing**."*

`build-m4-schema.py` fails both clauses, quoted:

- **No mode whose only product is a verdict.** Measured — its entire flag set is
  `--out`, `--schema`, `--self-test`, `--quiet` (`scripts/build-m4-schema.py:365-369`). Every
  non-self-test mode emits SQL, to a file or to stdout (`:394-398`). There is no `--check`.
- **The assertion's subject is its own output.** `scripts/build-m4-schema.py:245` —
  `errors += assert_end_state(sql)` — where `sql` is the string built two lines above. That is
  literally an assertion protecting the artefact the script just produced.
- **The "becoming a pure guard" quote is a future state.** `scripts/build-m4-schema.py:26-28`:
  *"⛔ EXPIRES when Tasks 1-2 land. At that point every edit reports `already` and this file **can
  be** reduced to its assertions."* §4's row cites it as evidence of what the file is; the file says
  what it may become, conditional on work that has not landed.

The same criterion cleanly derives the other two IN files (`verify-exclusion-reasons.py` — verdict
is the whole product; `gen-m4-manifest.py --check` — *"regenerate and FAIL if it differs"*), cleanly
derives every one of the 16 OUT files, and cleanly derives `codex-review.py` OUT per §4.1. It
derives `build-m4-schema.py` **OUT**.

**Consequence:** 26 + 2 = **28**. F2 pins **29**. §4's own ⛔ box says of v1: *"A count derived from
an unstated rule is not a measurement."* v2 states the rule and then reports a count the rule does
not produce, so F2 locks in a number reached the same way — by adopting round 1's reclassification
rather than by derivation. Either the criterion needs a clause that admits a builder whose
assertions read its inputs through its output, or `build-m4-schema.py` gets a 17th `NOT-A-GUARD:`
line; the document cannot have both as written.

This is the sharpest round-1 regression available: the criterion was **round 1's fix** for the
"assigned by feel" finding, and it contradicts **round 1's other fix** in the same section.
§12's *"They disagreed on `build-m4-schema.py` and the finding-half was right"* is not supported by
the criterion v2 wrote in order to settle exactly this kind of question.

---

## High

### H1 — F8 cannot pass, by construction

`spec:418` — *"`grep -rn discover_ratchets scripts/ .github/ .claude/ docs/` returns nothing | any
hit — #73 not closed, or §7 incomplete"*. §7 widened the search to `docs/` in response to round 1.

**Observation — that exact grep on the live tree, with the two files the change fixes or deletes
(`check-ratchet-contract.py`, `page_markup.py`) excluded: 18 hits remain.**

| Where | Hits | Can it be scrubbed? |
|---|---|---|
| the spec itself, `…/2026-09-02-guard-inventory-population-design.md` | 7 | No — §1, §2, §5.7, §7, §8 and F8 all name the function |
| `docs/reviews/spec-guard-inventory-population-r1-claude.md` | 7 | No — it is the round's evidence record |
| `docs/reviews/architecture-review-2026-08-30.md:73` | 1 | No — dated finding |
| `docs/backlog.md:101` | 1 | **No** — §8 keeps row 73 as a closed `✅ (was 🟢)` row, and its text quotes the function by name |
| `docs/superpowers/specs/2026-08-30-inline-renderer-seam-design.md:183` | 1 | Yes — §7 lists it |
| `docs/roadmap-to-launch.md` | 1 (via `:1692-1693`) | Yes — §7 lists it |

A falsifier that can never return its passing observation will be reinterpreted at implementation
time ("it only means live code"), and a reinterpreted falsifier is the *"confident but wrong
CONVERGED"* shape `docs/plugins.md` records. Bound it to the executable population — the same
`scripts/ .github/ .claude/` it had, plus the two prose sites §7 actually fixes — or state the
exclusions in the falsifier itself.

### H2 — §3.1's stated REASON for flush-left is false in general, and the anchor does not close the self-exclusion it was written to close

`spec:168-170`: *"`^[ \t]*` — the obvious anchor — still swallows the indented example, because
dedenting preserves *relative* indent: a real declaration ends up flush left, a demonstrated one does
not."*

`ast.get_docstring(clean=True)` dedents by the **minimum** indent of the body lines, so "relative
indent" is preserved only against whatever the minimum happens to be. Two executed counter-cases,
both against the implemented v2 copy:

```
probe docstring                                    v2 exit  in-population
X_indented_example_only_body                          0        False   ← EXCLUDED
X_rule_marker_at_line_start                           0        False   ← EXCLUDED
```

- **`X_indented_example_only_body`** — an indented example that is the docstring's only body content
  (`"""A probe.\n\n    NOT-A-GUARD: a page generator\n"""`). Margin is 4, the whole body dedents, and
  the example lands at column 0. Whether the flush-left anchor holds depends on an unrelated property
  of the *rest* of the docstring, which is not what §3.1 says.
- **`X_rule_marker_at_line_start`** — prose documenting the rule that puts the marker at the start of
  a line, i.e. the natural way to document a rule whose whole content is *"write it flush left"*.

The second one is the sharp one, because §5 item 6 still *instructs* the implementer to rewrite this
file's docstrings to describe the mechanism. Executed, by inserting that documentation into
`check-ratchet-contract.py`'s own module docstring in the implemented copy:

```
v2 flush-left  midline          run_exit=0 count=29 self_in_population=True   selftest 23/23
v2 flush-left  flushleft_demo   run_exit=0 count=28 self_in_population=False  selftest 22/23
```

**The guard still removes itself from its own population, and `check-ratchet-contract.py` still
exits 0 printing `ratchet contract OK`.** Only the `--self-test` notices — see H3. §3.1's verdict
*"Only flush-left gets all five"* is true of the five sampled docstrings and is presented as the
repair; the repair that actually catches this is §3.3's standing case. §6's second bullet discloses
the class in one clause (*"a flush-left `NOT-A-GUARD:` inside a docstring for some other purpose
would still exclude"*); §3.1's causal sentence and F6's wording do not.

### H3 — §3.3's "standing" self-inclusion case has no runner, and its cited precedent works for a reason this file does not have

`spec:189-192` calls the self-inclusion case *standing*, and cites `scripts/check-selftest-counts.py:20`
verbatim: *"⚠ IT CHECKS ITSELF. This script is in `POPULATION`, so its own declared count is verified
by the same **external run**."*

**Observation — nothing executes this contract's self-test.** Repo-wide
`grep -rn "check-ratchet-contract.py --self-test"` returns exactly two hits: its own usage line
(`scripts/check-ratchet-contract.py:25`) and a paragraph in
`docs/superpowers/plans/2026-08-31-dashboard-collapsed-cards.md:759`. CI runs the bare script only —
`.github/workflows/ci.yml:144`: `run: python3 scripts/check-ratchet-contract.py`.

So the one mechanism that detects H2's self-exclusion currently runs nowhere. The precedent's force
comes entirely from `check-selftest-counts.run_self_test` (`scripts/check-selftest-counts.py:183-186`)
spawning each `POPULATION` member as a subprocess, wired at `ci.yml:178`. §10's decision to add the
contract to that `POPULATION` **is** what would make §3.3 standing — but §10 sells it as *"a real
gain — the contract has never had its self-test count ratcheted"*, and neither section says §3.3
depends on it. An implementer who reads §10 as test-infra polish and defers it ships §3.3 as a case
nothing runs.

### H4 — §4's "no fourth surprise" sweep screens by a signal that misses two of the three files in its own IN set

`spec:241-242`: *"**Swept for others misclassified the same way:** `gen-m4-manifest.py` is the
**only** non-`check-*` script with a verdict-only mode flag (`--check`/`--verify`/`--assert`/
`--audit`). No fourth surprise."*

**Observation — that regex over all 19 non-`check-*` scripts returns exactly one file,
`gen-m4-manifest.py`.** Which is the problem: `verify-exclusion-reasons.py` and
`build-m4-schema.py`, the other two members of §4's own IN table, have **no** such flag (measured:
flag sets `[]` for both). A screen that finds 1 of the 3 files it is screening for cannot support
*"no fourth surprise"*.

This is `§4.3`'s own lesson — *"enumerating from **one reason** rather than from **the rule**"* —
committed two paragraphs after §4.3 corrects it. The rule is the criterion (a verdict-only *mode*,
flagged or default); the sweep used a proxy. I re-applied the criterion by hand to all 19 and found
no fourth IN file, so I believe the conclusion; the stated evidence does not establish it.

---

## Medium

### M1 — §7's "every site that states the old population as fact" omits `docs/backlog.md`, which this PR edits anyway

`docs/backlog.md:100` (row 72) states it three times, including *"the live path builds its population
at `:395` from `(ROOT / "scripts").glob("check-*.py")` and filters it through `GUARD_PATH_RE`"* and
*"the contract still reported **24 guards**, not 25"*. `docs/backlog.md:101` (row 73) states
*"`grep -rn discover_ratchets scripts/ .github/ .claude/` returns exactly two hits"*.

§8 keeps both rows (closed, leading `✅ (was 🟠)`), so the prose stays on a live page — the backlog
page renders every row, closed included. §7 lists nine sites and not these two, while §8 edits the
same file in the same PR. It is also the file the reader is most likely to arrive from.

### M2 — §3.4 ("unparseable is IN") and §5 item 9 ("a CANNOT-RUN exit") specify two different exits, and the widened population makes any broken `scripts/*.py` red

**Observation — implemented copy, a syntax error appended to `prior-art.py`, a file that carries a
`NOT-A-GUARD:` declaration:**

```
summary: 2 violation(s), baseline 0
RATCHET FAILED: a ratchet was added or changed without following the contract.
See docs/process-checklists.md → Writing a RATCHET.
EXIT=1
```

Three things follow, none stated:

1. A declaration that cannot be parsed cannot be honoured, so a **declared-out** file re-enters the
   population the moment it is mid-edit.
2. The blast radius widens from 26 files to 45 — breaking a research tool now turns the guard
   inventory red. Fail-closed, and arguably right, but §6 does not mention it.
3. The message is wrong. `docs/process-checklists.md` rule 1 requires *"exit non-zero and say treat
   this as NOT RUN"*; this says a ratchet was added or changed without following the contract.
   §5 item 9 asks for the CANNOT-RUN exit, §3.4 routes the file through the violation path instead,
   and the spec does not say which wins.

### M3 — §3.3's case cannot detect an anchor regression, only a self-exclusion

**Observation — implemented copy with the contract's own docstring left unchanged, `(?m)^` dropped
from `NOT_A_GUARD_RE`:** `self-test: 21/23 passed` — the two red cases are the rule-documenting and
indented-example fixtures; **the self-inclusion case stays green.** It only goes red (20/23) once the
contract's docstring itself contains a mid-line `NOT-A-GUARD:` occurrence.

So §3.3's case is load-bearing for the thing §3.3 claims (self-exclusion) and is *incidentally*
coupled to the contract's own docstring text for §10's third mutation. That coupling is the
`a-refactor-ORPHANS-the-mutation-guarding-it` shape — anchors bind by text — and it means §10's
"anchor dropped → red via the rule-documenting case (F6)" is the only route, not a redundant one.
Worth stating so nobody later "tidies" the docstring and silently loses a mutation's second detector.

### M4 — §7's ⚠ note points at the wrong falsifier and the wrong section

`spec:384-385`: *"⚠ **F6's grep cannot see most of these** — it searches `scripts/ .github/ .claude/`
… Widened in §8."* In v2, **F6 is the grammar falsifier** (`spec:416`) and the grep is **F8**
(`spec:418`), in **§9**, not §8. v1's numbering is showing through the renumbering — the exact
cross-reference rot the spec exists to police.

---

## Low

- **L1 — two off-by-one citations.** `spec:172` cites `NO_CALLER_RE` at `:117`; `:117` is the comment
  line, the regex is `scripts/check-ratchet-contract.py:118`. §5 item 10 cites the stale sanity
  comment at `:404`; `:404` is `if not ratchets:`, the comment is `:405`. (Flagging under the round's
  "every number reproduces" rule; neither is load-bearing.)
- **L2 — §8 calls the coverage check "bidirectional".** `coverage_errors`'s own docstring says
  *"⚠ NO LONGER REPORTS MISSING ITEMS — see `undescribed`"*; it reports `extra` and `dupes` only. The
  half §8 relies on — *"GROUPS names items that are not open"* — is real and does refuse, so the
  instruction is right and the adjective is stale.
- **L3 — §7 row 2 merges two different claims.** `docs/process-checklists.md:283-288`'s *"There are
  EIGHT"* is a hand-listed set of **ratchets** (eight named scripts), not the guard population. §7's
  After column says it *"becomes 29"*. It does not; 29 is the guard count, and the eight-item ratchet
  list is a separate claim that also needs a decision.

---

## What I checked and found clean

- **45 / 26 / 19** reproduced exactly; the 19 named files are precisely §4's 3 IN + 16 OUT, no
  overlap, no omission.
- **Live run `guards discovered (26)`, exit 0; `--self-test` 21/21.** Reproduced exactly.
- **§3.1's five-row table reproduces exactly as printed**, including the two ❌ columns. Only
  flush-left gets all five of *those five*. (H2 is about a sixth and seventh case, not about the
  table's arithmetic.)
- **F6 is not decoration.** Executed on both grammars: `F6a_documents_rule` and
  `F6b_indented_example` are `in-population=True, exit 1` under v2 and `in-population=False, exit 0`
  under v1. It genuinely discriminates. **F7 likewise** — v1's grammar drops the contract from its own
  population (count 28) and turns the self-test red.
- **F3 ✅** — `zz-probe.py` appears in the discovered list *and* the run exits 1, so r1's
  wrong-reason trap is closed. **F4 ✅**, **F5 ✅** (bare colon + prose on the next line stays IN), and
  the `[ \t]`-vs-`\s` distinction is inherited correctly.
- **F1 ✅ / F2 ✅ / F9 ✅ against the implemented copy** — `guards discovered (29)` containing all three
  of `build-m4-schema.py`, `gen-m4-manifest.py`, `verify-exclusion-reasons.py`; `ratchet contract OK`;
  `BASELINE` untouched at 0. (F2's *29* is the number §4's classification produces; see B2 for
  whether the criterion produces it.)
- **"Zero code repairs" holds.** Ten non-`check-*` scripts fail R1/R2/R3 today —
  `brief-compose, codex-frontier-model, codex-review, m4_base_db, m4_catalog, prior-art,
  regen-skills-doc, session-skill-report, skill-usage-audit, subject_status` — and every one is in
  §4's OUT table. **All three IN files conform on R1+R2+R3**, measured with the live caller blob.
- **§4.3's eight → seven** reproduced exactly: `gen-backlog-page, gen-dashboard, gen-goals-page,
  regen-skills-doc, page_markup, page_chrome, explainer-serve` satisfy R3 in the OUT set, plus
  `build-m4-schema` which moved IN.
- **§4.2's importer counts** — `page_markup` 4, `m4_catalog` 5, `subject_status` 3, `m4_base_db` 3.
  All four correct.
- **§3.2's "zero of the current guards carry a `NO-CALLER:` declaration"** — reproduced, and I widened
  it: **zero across all 45**, unanchored or anchored. Anchoring `NO_CALLER_RE` is free, as claimed.
- **§10's "no mutation coverage today"** — no `scripts/mutations/*.json` names the file and
  `EXPECTED_MUTATIONS` has no key for it. Correct.
- **The gap round 1 left open, now closed: the 16 docstring insertions break NO existing mutation
  anchor.** Every `edits` anchor in all seven manifests still matches exactly once against the
  implemented copy — including all 73 in `gen-dashboard.json`, 14 in `page_markup.json` and 11 in
  `page_chrome.json`, the three files the insertions touch.
- **§7's nine rows all verified against their files** — `process-checklists.md:283-288/294-296/298`,
  `dev-process.md:145`, `page_markup.py:42-45`, `explainer-serve.py:68-73`, `ci.yml:212-215` and
  `:220-223`, `roadmap-to-launch.md:1693/1530/1599`, `inline-renderer-seam-design.md:176,183`.
- **§8's backlog mechanics.** `gen-backlog-page.GROUPS` carries rows 72 (`:237`) and 73 (`:240`), and
  `coverage_errors` refuses with *"GROUPS names items that are not open"* — so closing without
  deleting the tuples does fail the page build, as §8 says.
- **§12's "sixteen" reproduces**: 15 Claude findings + `build-m4-schema.py`, the one Codex finding
  with no Claude counterpart; the other four Codex findings each pair with a Claude one.
- **§6's `gen-m4-manifest.py` R1 gap** — its `--self-test` is not in
  `check-selftest-counts.POPULATION` and nothing runs it. Correctly recorded as a gap, not a fix.
- **The criterion is decidable for 18 of the 19** — I applied it by hand to each file and got §4's
  answer everywhere except `build-m4-schema.py` (B2). No hidden verdict-only mode among the 16 OUT
  files: their full flag sets are argument/output options only, and `codex-review.py --verdict`
  (`:469`) is an output path, not a mode, so §4.1 stands.

### Gaps in my coverage

- I did **not** run `check-plan-code.py --mutate .` end to end, because the manifest §10 specifies
  does not exist yet. B1 is established from the parser source, the contract's five print sites, and
  the parser executed against the contract's real red output — not from a full harness run.
- I did not run `check-docs.py`, `check-anchors.py`, or the CI suite against the implemented copy, so
  I have not measured whether §7's edits to `dev-process.md` and `process-checklists.md` stay inside
  their line budgets.
- My implemented copy is *my* reading of §5's ten items — in particular the shape of the
  `SyntaxError` repair (item 9) and the exact set of rewritten `POPULATION_CASES` (item 8). M2's
  message text is implementation-dependent; the two-exits ambiguity in the spec is not.
- I did not test CRLF or form-feed docstrings beyond reasoning that `cleandoc` expands tabs and
  `lstrip` consumes `\f`; the two counter-cases in H2 are plain spaces and were executed.
- No Postgres, no schema gates, no `.claude/hooks` behaviour beyond reading them as caller sources.
- I did not check whether `check-guard-coverage.py` maintains a second notion of "the guard
  population" — round 1's Codex half reported it does not (schema objects), and I did not re-verify.

---

**VERDICT: NOT CONVERGED** — two Blocking (§10's mutation manifest cannot go green against a suite
that prints `FAIL` rather than `[FAIL] `, and §5 does not list the fix; §4's stated criterion derives
`build-m4-schema.py` OUT, making the count 28 and F2's 29 unearned by the same route §4 condemns in
v1), four High (F8 cannot pass; §3.1's reason for flush-left is false in general and the guard can
still self-exclude while reporting OK; §3.3's standing case has no runner; §4's sweep screens by a
signal that misses two of its own three IN files), four Medium and three Low.
