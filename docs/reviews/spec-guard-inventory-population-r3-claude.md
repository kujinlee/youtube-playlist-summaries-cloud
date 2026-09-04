# Spec review — `2026-09-02-guard-inventory-population-design.md` v3 (`abb4c2b5`)

**Round 3, Claude half.** Branch `fix/guard-inventory-population`. Reviewed 2026-09-02.
**Scope:** v3's own new material — §3's AST encoding, §3.4, §3.5, §4.1's re-derivation, §5 item 8,
§7, and the repaired falsifiers F3–F9.

**Method.** §5's ten in-file items plus the 17 `NOT_A_GUARD` assignments were implemented in a
throwaway copy at `/Users/kujinlee/.claude-tmp/gip-r3/repo`, with further copies per probe
(`.../mut`, `.../unp`, `.../ws`, `.../f34`). Every finding below is a `file:line` quote or executed
output. No `git` mutation, no Postgres, no schema gate; the live tree was read only.

**Reproduced before looking for defects:** 45 / 26 / 19 exactly; live run `guards discovered (26)`,
exit 0, `--self-test` 21/21. Implemented copy: `guards discovered (28)`, exit 0, `ratchet contract
OK`, self-test 27/27, and the 28 are the 26 `check-*` plus `gen-m4-manifest.py` and
`verify-exclusion-reasons.py`.

---

## Blocking

### B1 — §10's first mutation CANNOT go red: `main()` is unreachable from `--self-test`, and §5 lists no extraction

`§10`: *"`main`'s glob narrowed back to `check-*` → red via the payload case."*
`§5 item 1` calls that same line **"The load-bearing edit"**.

Every case §10 lists — *"the eight §3.2 rows, the payload case (non-`check-*`, no declaration → IN),
the rewritten `POPULATION_CASES`, and §3.5's self-inclusion case"* — drives `discover_guards`,
`check_contract` or `check_caller` **directly**. `main()` is driven by nothing. The glob at
`scripts/check-ratchet-contract.py:395` is inline in `main()` and has no other reader.

**Observation — the mutation applied to the implemented copy, exactly as §10 words it:**

```
$ python3 scripts/check-ratchet-contract.py --self-test
self-test: 27/27 passed          SELFTEST_EXIT=0

$ python3 scripts/check-ratchet-contract.py
guards discovered (26): scripts/check-anchors.py, … scripts/check-vocabulary-collisions.py
ratchet contract OK              RUN_EXIT=0
```

The population silently reverts to the 26 that §1 exists to widen, the run reports `ratchet contract
OK`, and **the suite stays green**. `check-plan-code.run_mutations` decides `caught = rc == 1`
(`scripts/check-plan-code.py:747`), so this is recorded as `mutation SURVIVED — …: the suite stayed
green, so no case can fail for what it names` (`:773-776`) and `--mutate .` goes red. `--mutate .`
is what CI runs (`docs/dev-process.md`), so the PR cannot be green — the same conclusion as round
2's B1, reached by a different route that §5 item 8 does not close.

Calling `main()` from a case is not an escape either: under `--mutate .`,
`check-plan-code.mutate_delivered:630` copies **only** `root/"scripts"` into the temp dir, so
`ROOT/".github/workflows/ci.yml"` is absent and `main:389-392` returns 1 before discovery — the
control run would be red and `mutate_delivered:643-648` would report `CANNOT RUN — control run of …
exited 1 BEFORE any mutation was applied`.

**The fix is an extraction §5 does not list:** the glob must move into a function the suite drives
(the shape §5 item 3 already applies to `discover_guards`). Until then the one edit the whole spec
turns on has no case and no reachable mutation.

**Why Blocking, and why it is a v3 regression.** This is verbatim the lesson recorded in the file
being changed — `scripts/check-ratchet-contract.py:163-171`: *"EXTRACTED FOR THE WIRING, not for
tidiness. With R1/R2/R3 applied inline in `main()`, deleting the `check_caller` call would have left
every caller case green — coverage of the function, none of its use."* §5's ⚠ header says it is
*"not labelled complete"*, which softens the framing but does not supply the edit; §10 states a
mutation outcome that cannot occur, which is a claim, not a caveat.

---

## High

### H1 — `NOT_A_GUARD = "   "` silently removes a real guard; §3.2's *"Every failure mode fails closed"* is false, and the sibling rule in the same file refuses exactly this

`§3`: *"whose value is a **non-empty** string constant"*. `§3.2` tabulates `NOT_A_GUARD = ""` → IN
and concludes *"Every failure mode fails **closed** — toward being policed."*

Python truthiness makes `""` the only empty value that fails closed. A whitespace-only string is
non-empty.

**Observation — `NOT_A_GUARD = "   "` inserted into `scripts/check-docs.py`, a real guard, in the
implemented copy:**

```
guards discovered (27)
check-docs ABSENT from the population
EXIT=0                      ← "ratchet contract OK"
self-test: 27/27 passed
```

A live guard leaves the inventory, the run reports OK, and the suite notices nothing.

The same file already solved this for the sibling opt-out. `NO_CALLER_RE`
(`scripts/check-ratchet-contract.py:118`) is `r"NO-CALLER:[ \t]*(\S[^\n]*)"` — the `\S` is
deliberate — and `OPTED_OUT_BARE` (`:249-257`) is a standing case named *"a BARE NO-CALLER with no
reason is still a violation — **the opt-out is not a rubber stamp**"*. §3.3 discusses `NO-CALLER:`
at length and does not carry that property across to the new opt-out it is modelled on.

§6's *"it does not make lying impossible … it is a reviewable claim"* does not cover this: `"   "`
is not a lie, it is an **absence**, and the whole argument of §2 is that absence must not be an exit.
Require `value.strip()`, and add the case.

### H2 — §3.2's eight-case table is a FIFTH instance of the corpus error §12 counts four of, and it is inside v3's own new material

§12 lists four instances of *"enumerate the dimensions from the RULE, then measure"* and closes
*"**Enumerate the dimensions from the RULE, then measure.**"* §3.2's table is enumerated from the
**previous grammar's** failure modes — docstring documenting, docstring demonstrating, comment,
nesting — plus two value-shape rows. The AST rule's own dimensions are (a) the assignment **node
type**, (b) what *"module-level"* means, and (c) the **boundary** of *"non-empty"*. None is swept.

**Observation — §3.2's rule implemented and driven over shapes enumerated from those three
dimensions** (all eight of §3.2's own rows reproduce exactly; only the unlisted ones are shown):

| Input | Result | §3.2 |
|---|---|---|
| `NOT_A_GUARD: str = "…"` (annotated) | **IN** — a genuine declaration refused | silent |
| `NOT_A_GUARD: Final[str] = "…"` | **IN** — refused | silent |
| `if True:` / `try:` block at module level | **IN** — refused | silent |
| `(NOT_A_GUARD := "…")` walrus | **IN** — refused | silent |
| `NOT_A_GUARD = f"…"` | **IN** — refused | silent |
| `NOT_A_GUARD = "   "` | **EXCLUDED** — fails open (H1) | silent |
| `NOT_A_GUARD = "real"` then `= ""` | **EXCLUDED** — effective value is `""` | silent |
| `NOT_A_GUARD = "real"` then `del NOT_A_GUARD` | **EXCLUDED** — name is unbound at runtime | silent |

Three of these fail **open**, so *"Every failure mode fails closed"* is not a property of the rule as
written; it is a property of the eight shapes chosen.

**The sharpest one is (b), because it decides the implementation and §3.2 cannot adjudicate it.**
*"Module-level"* reads two ways. Syntactically it means a direct child of `Module.body` → the
implementer writes `for node in tree.body`. In Python's own binding-scope sense an assignment inside
a module-level `if` **is** a module-level binding → the implementer writes `ast.walk`. The two agree
on all eight of §3.2's rows except one: **under `ast.walk`, §3.2's row 5 (`assignment nested inside a
function` → IN) breaks**, because `walk` reaches into function bodies. So §3.2's table is satisfiable
by one reading and self-contradictory under the other, and the document never says which. F5 pins the
function-nested case and therefore does discriminate the two implementations — but only by accident,
since the spec never identifies the fork.

Also unstated, and it is the one an implementer meets first: `NOT_A_GUARD, X = "a", 1` (tuple target)
is refused, while `NOT_A_GUARD = X = "a"` (chained) is accepted. Both are defensible; neither is
decided.

### H3 — §7's remediation for `process-checklists.md:283-288` writes a NEW false claim, and §8 removes the mechanism that row depends on with no successor

`§7` row 2: *"`docs/process-checklists.md:283-288` | *"There are EIGHT"*, *"two independent
sources"* — stale; **becomes 28, one source**"*.

**Quoted, `docs/process-checklists.md:283-288`:**

```
**There are EIGHT**, and each invented these independently, differently:
`check-arch-findings.py`, `check-guard-coverage.py`, `check-sentinel-meanings.py`,
`check-vocabulary-collisions.py`, `check-gate-falsifiability.py`, `check-ratchet-contract.py`,
`check-storage-grant-pin.py`, `check-test-counts.py`.
**Do not maintain this list by hand — `python3 scripts/check-ratchet-contract.py` prints it**, from
two independent sources, and is the reason the count below was ever corrected.
```

"EIGHT" is a hand-list of **ratchets**, not the guard population. 28 is the guard count. Substituting
one for the other, as §7 instructs, puts "There are 28" over a list of eight names — a false
statement in the process document, produced by the section whose stated job is *"Every site that
states the old population as fact"*.

Worse, the sentence in bold is a **maintenance instruction** resting on `discover_ratchets`, and §8
deletes `discover_ratchets` outright. After this PR the script prints guards, not ratchets, so the
eight-item list becomes hand-maintained with **no mechanism at all** — the "rule that depends on
remembering" shape §2 rejects. Neither §6 ("What this does NOT do") nor §8 records that the ratchet
inventory is being retired along with its implementation.

This is round 2's L3 (*"the eight-item ratchet list is a separate claim that also needs a
decision"*), carried forward with the number changed from 29 to 28 and the decision still not made —
while §12 states all 30 findings were *"re-verified against the code by the author before
acceptance; none disputed."*

---

## Medium

### M1 — the declaration's PLACEMENT is unspecified, and the obvious placement is a `SyntaxError` in 17 of 17 files

§3's worked example is a bare line with no context, and §5's *"Outside it: 17 `NOT_A_GUARD`
assignments"* gives no placement rule. The natural spot — directly under the module docstring, where
v1/v2's `NOT-A-GUARD:` marker lived and where the declaration is most visible — is illegal in every
file that opens with `from __future__ import annotations`.

**Observation — measured across the OUT set: 17 of 17.** `brief-compose, build-m4-schema,
codex-frontier-model, codex-review, explainer-serve, gen-backlog-page, gen-dashboard, gen-goals-page,
m4_base_db, m4_catalog, page_chrome, page_markup, prior-art, regen-skills-doc, session-skill-report,
skill-usage-audit, subject_status` — all carry a `__future__` import, and the naive insertion gave
`SyntaxError: from __future__ imports must occur at the beginning of the file` in each.

The failure compounds with §3.4 + §5 item 9: an unparseable file no longer yields a message about
placement, it aborts the **whole** inventory. Executed on the copy with a mis-placed declaration in
one file: `FAILED: scripts/… does not parse … Treat this as NOT RUN`, exit 1, no guard checked.
Fail-closed and therefore not dangerous, but it is a 100 %-hit-rate footgun on the one mechanical
step §5 delegates entirely to the implementer. One sentence — *"immediately after `from __future__`"*
— removes it.

### M2 — §3.5's runner is a hand-pinned ROSTER, which is the mechanism §2 rejects; it is not a cycle, but the contract's only self-test runner is evadable by omission

Answering the circularity question directly: **it is not a cycle.**
`check-ratchet-contract.py` judges `check-selftest-counts.py` on R1/R2/R3 (does it have a
`--self-test`, no fail-open handler, a caller); `check-selftest-counts.py` judges
`check-ratchet-contract.py` on whether its printed case total matches its declared one. Different
properties, neither derived from the other. Nothing vouches for itself through the other.

The real defect is a different one. §6 states *"Only `check-ratchet-contract.py`'s own membership is
re-verified after merge (§3.5)"* — so §3.5 is the spec's **single** standing assertion, and §3.5
makes it depend on `check-selftest-counts.POPULATION`, which its own docstring calls **pinned, not
derived**: *"the population is PINNED rather than derived"* (`scripts/check-selftest-counts.py:78-82`).

`population_errors` (`:171-178`) catches half the evasion — dropping the POPULATION entry while the
declaration remains, or vice versa. **Dropping both together passes silently**, and nothing else runs
this contract's self-test. Verified on the live tree: `grep -rn check-ratchet-contract .github/
.claude/ scripts/*.sh` returns only `ci.yml:144` (the bare script) and two prose comments at `:212`
and `:221`.

§2 rejects exactly this shape for the guard population — *"Declare-in via a central roster
(rejected). Evadable by omission: a guard nobody adds is a guard nobody polices"* — and §3.5 adopts
it for the guard that polices the guards, without naming the trade. Worth one sentence in §6, or a
`NO-CALLER:`-style refusal if the contract stops appearing in POPULATION.

### M3 — §7 says *"Ten."* and lists ELEVEN rows

`spec:298` — *"Ten. v1 corrected two."* The table beneath it (`:302-312`) has **eleven** rows:
`process-checklists.md` ×3, `dev-process.md:145`, `check-test-counts.py:31-33`, `page_markup.py`,
`explainer-serve.py`, `ci.yml:213`, `roadmap-to-launch.md`, `inline-renderer-seam-design.md`,
`docs/backlog.md`. Counted mechanically:

```
$ awk '/^## §7/,/^## §8/' <spec> | grep -c '^| `'
11
```

v2 had nine rows and said "Nine"; v3 added `docs/backlog.md` (round 2's M1) and moved the header to
"Ten". A stale count in the section whose entire subject is stale counts, in the sentence that
asserts completeness.

### M4 — round 2's M2(2) is still not in §6: any unparseable `scripts/*.py` now turns the guard inventory into a CANNOT-RUN

Round 2's M2 raised three consequences of the widened population; §3.4 answers the first (a
declared-out file mid-edit re-enters) and the third (the message). The second — *"the blast radius
widens from 26 files to 45 — breaking a research tool now turns the guard inventory red … §6 does not
mention it"* — is unaddressed, and §5 item 9 makes it sharper than it was, because the outcome moved
from "1 violation" to "the whole run reports NOT RUN".

**Observation — a syntax error appended to `prior-art.py`, a research tool that carries a
declaration, in the implemented copy:**

```
FAILED: scripts/prior-art.py does not parse (invalid syntax …). The inventory could not be
computed. Treat this as NOT RUN.
EXIT=1
```

Correct behaviour, and arguably the right call — but it is a new coupling between the CI guard gate
and every unrelated script under `scripts/`, and §6 is the section that exists to state exactly this
kind of consequence. §12's *"none disputed"* implies it was accepted.

---

## Low

- **L1 — §4.1's three citations are each off by one.** `errors += assert_end_state(sql)` is
  `scripts/build-m4-schema.py:244`, not `:245`; `sql = s01 + s03 + s04` is `:243`, i.e. **one** line
  above, not *"two lines above"*; the flag block is `:366-369` (`:365` is `formatter_class=…`), not
  `:365-369`. Every one of §4.1's substantive claims **reproduces** — zero `--check` in the flag set,
  the assertion's subject is the script's own `sql`, and the *"can be reduced to its assertions"*
  quote is under `⛔ EXPIRES when Tasks 1-2 land` (`:28`). Only the line numbers slipped.
- **L2 — §5 item 10's `:404` is `:405`.** `:404` is `if not ratchets:`; the stale
  `# This project has 24.` comment is `:405`. Reported as round 2's L1 and not corrected.
- **L3 — §12's "30 findings" reproduces only under an unstated convention.** Summing the header
  table's own severities gives **38** (r1 codex 5, r1 claude 15, r2 codex 5, r2 claude 13 —
  each verified by counting headings in the four review docs). 30 is reachable only by
  de-duplicating paired halves, which §12 does elsewhere in prose but does not say here.
- **L4 — F8 excludes `docs/backlog.md`, which §7's own last row flags.** `docs/backlog.md:100-101`
  contains `discover_ratchets` and §7 says those rows *"must not be left describing the old
  mechanism"*. F8 names six paths and not that one, so the falsifier cannot observe the site its own
  §7 requires changing. (F8 is otherwise sound — see below.)
- **L5 — F5 passes vacuously on v1 and v2.** Its three shapes are AST *value* properties, and v1/v2's
  grammar had no notion of a value, so `NOT_A_GUARD = ""` leaves a file IN under all three versions.
  It is **not** decoration — it discriminates the `ast.walk`-vs-`tree.body` fork (H2) — but it does
  not distinguish spec versions, and the ⛔ box's framing implies the repaired falsifiers do.

---

## What I checked and found clean

- **45 / 26 / 19 reproduced exactly**, and the 19 named non-`check-*` files are precisely §4's
  2 IN + 17 OUT — no overlap, no omission. Live run `guards discovered (26)`, exit 0, self-test 21/21.
- **The count is 28.** Implemented copy: `guards discovered (28)`, `ratchet contract OK`, exit 0,
  containing both `gen-m4-manifest.py` and `verify-exclusion-reasons.py`. **F1 ✅ F2 ✅ F9 ✅**
  (`BASELINE` untouched at 0, run green).
- **§4.1 is right and v2 was wrong.** I applied §4's criterion independently to all 19 and got
  **2 IN / 17 OUT**, agreeing with v3 on every file including `build-m4-schema.py`. Its full flag set
  is `--out/--schema/--self-test/--quiet` with **zero** `--check`; `assert_end_state(sql)` takes the
  string the script itself just built; the *"reduced to its assertions"* line is under an `EXPIRES`
  marker. The two closest calls are `gen-backlog-page.py` (its `coverage_errors` refusal is a
  precondition on its **own** page, so self-protection → OUT) and `skill-usage-audit.py` (the word
  "audit" is in the name, but the product is `--json` information for a human → OUT). Neither moves.
- **§4.4's arithmetic.** Exactly **eight** OUT files satisfy R3 today — the seven named plus
  `build-m4-schema` — and exactly **ten** non-`check-*` scripts fail R1/R2/R3, **all ten OUT**
  (`brief-compose, codex-frontier-model, codex-review, m4_base_db, m4_catalog, prior-art,
  regen-skills-doc, session-skill-report, skill-usage-audit, subject_status`). Both IN files conform
  on R1+R2+R3 against the live caller blob. *"Zero code repairs"* holds.
- **All eight rows of §3.2's table reproduce exactly**, including the two docstring rows. §3.1's ⛔
  defect is structurally closed: the implemented contract's own docstring quotes
  `NOT_A_GUARD = "<reason>"` and the file stays in its own population.
- **F6 is load-bearing, not decoration.** Executed against the most plausible wrong v3 implementation
  — a regex over source text, `(?m)^NOT_A_GUARD\s*=` — the rule-documenting docstring is **EXCLUDED**,
  reproducing v2's Blocking; the AST rule leaves it IN. F6 catches it.
- **F3 ✅ / F4 ✅.** `zz-probe.py` with no `--self-test` and no declaration appears in the discovered
  list *and* the run exits 1; adding `NOT_A_GUARD = "a probe"` drops it from the list and the run
  exits 0. Round 1's wrong-reason trap stays closed.
- **F7 ✅ and it fires.** With a real module-level `NOT_A_GUARD` on the contract itself: count 27, the
  contract absent from its own list, **bare run still exits 0 printing `ratchet contract OK`**, and
  the self-test goes red — `[FAIL] check-ratchet-contract.py is in its OWN discovered population`,
  26/27, exit 1. §3.5's premise is also correct: nothing runs this script's `--self-test` today.
- **F8 ✅ satisfiable, and it distinguishes versions.** The exact grep on the live tree returns hits in
  only two files — `scripts/check-ratchet-contract.py` (the deleted function) and `scripts/page_markup.py`
  (a §7 site) — both of which this change edits. v2's all-of-`docs/` form returned 18. Repaired, not
  renumbered, as the ⛔ box claims.
- **§5 item 8 works end-to-end.** With `[FAIL] {name}: got … want …`,
  `check-plan-code.py:723-724`'s parser extracts exactly one red case name from the contract's real
  red output, and `check-selftest-counts.printed_total` still reads 27 from the summary line. No other
  reader of this script's output exists: `ci.yml:144` runs it bare, and the format change is confined
  to `self_test()`. §10's supporting citations (`check-plan-code.py:723-724`, `:739-746`, `:778-786`;
  `check-selftest-counts.py:176-179`, `:183-186`; `ci.yml:144`, `:178`) all verify.
- **§10's anchor claim reproduces.** Across all seven manifests, **165 anchors, 0** matching other
  than exactly once after the 17 declarations. The only files both OUT and manifested are
  `gen-dashboard.py`, `page_chrome.py`, `page_markup.py` — exactly the three §10 names.
- **§7 is complete on an independent sweep.** I enumerated the dimensions from the rule — (a) states
  the glob is `check-*`, (b) claims *"two independent sources"*, (c) attributes a guard count to the
  contract, (d) asserts a named file is not seen — and grepped each across the repo. Every live hit is
  a §7 row. The only non-row hits are the review archive and `docs/dashboard-entries.md:741`
  (*"clean over 24 guards"*), a dated entry that is legitimately historical. §7's ten rows and their
  quoted line ranges all verify against their files, including `ci.yml:213` vs the `page_chrome` step
  at `:220-223`.
- **§5 items 1–7 and 9–10 all land on the right lines** — `:395` glob, `:108` `GUARD_PATH_RE`,
  `:174` and `:403` `list(texts)`, `:296-304` `POPULATION_CASES`, `:343/:348/:353/:358/:375` the five
  `FAIL` prints. The third `POPULATION_CASE` does assert the opposite of the new payload case, as
  item 7 says.
- **No collateral breakage.** On the implemented copy, `check-docs.py`, `check-anchors.py`,
  `check-explainer-delivery.py`, `check-vocabulary-collisions.py`, `check-producer-enumeration.py`,
  `check-guard-coverage.py`, `check-gate-falsifiability.py`, `check-test-counts.py`,
  `check-roadmap-consistency.py` and `check-selftest-counts.py` all exit 0 — same as the live tree.
  The 17 declarations trip no vocabulary-collision, producer-enumeration or docs-integrity rule.

### Gaps in my coverage

- **I did not run `check-plan-code.py --mutate .` end to end.** B1 is established by applying §10's
  first mutation by hand and observing the suite stay green, plus reading `run_mutations`' `caught =
  rc == 1` and `mutate_delivered`'s `copytree(root/"scripts")`. The full harness run would take the
  whole 165-anchor battery and the manifest §10 specifies does not exist yet.
- **My implemented copy is *my* reading of §5.** In particular the shape of the `SyntaxError` repair
  (item 9, which I put as a pre-pass in `main`), the exact `POPULATION_CASES` payloads, and the choice
  of `tree.body` over `ast.walk` — which is H2's whole point, so the copy cannot settle it.
- **H2's "should count?" column is my judgement, not a measurement.** I report what the rule *does*
  for each shape (executed) and that v3 is silent (quoted); which of them ought to count is the
  author's call.
- I did not verify §12's round-2 de-duplication file by file — L3 reports the header-table sum (38)
  and that 30 is reachable only under an unstated convention, not which findings pair.
- No Postgres, no schema gates, no `--mutate`, no CI run. `.claude/hooks/` files were read only as
  caller sources. I did not check line budgets for the §7 edits to `dev-process.md` and
  `process-checklists.md` (`check-docs.py` passes on the copy, but the copy does not contain those
  edits).
- I did not re-derive round 1's findings; I read both r1 halves for what was claimed fixed and judged
  v3 on its own evidence, per the scope.

---

**VERDICT: NOT CONVERGED** — one Blocking (§10's load-bearing mutation survives, because `main()`'s
glob is unreachable from `--self-test` and §5 lists no extraction), three High (a whitespace-only
reason silently unregisters a live guard, and §3.2's *"fails closed"* claim is false for it; §3.2's
eight-case table is a fifth instance of the corpus error, and leaves the `tree.body`-vs-`ast.walk`
fork undecided; §7's remediation for the eight-ratchet paragraph prescribes a new false claim while
§8 deletes its mechanism), four Medium and five Low.
