# Claude adversarial review — branch `mutation-coverage-gate`, round 1

PROOF OF SUBJECT

(1) The `expect` of the LAST entry in `scripts/mutations/check-ratchet-contract.json` (`:66`):

```
    "expect": "a guard that only DOCUMENTS the escape is not exempted by it"
```

(2) The new `NO_MUTATIONS_RE` (`scripts/check-ratchet-contract.py:241`):

```python
NO_MUTATIONS_RE = re.compile(r"NO-MUTATIONS:[ \t]+([A-Za-z][^\n]*)")
```

(3) The full `WIDENED_MANIFEST_DEBT` set (`scripts/check-ratchet-contract.py:305-314`):

```python
WIDENED_MANIFEST_DEBT: frozenset[str] = frozenset({
    "scripts/build-m4-schema.py",
    "scripts/codex-review.py",
    "scripts/explainer-serve.py",
    "scripts/gen-m4-manifest.py",
    "scripts/m4_catalog.py",
    "scripts/prior-art.py",
    "scripts/subject_status.py",
    "scripts/verify-exclusion-reasons.py",
})
```

STATUS: COMPLETE

Control established first: `check-ratchet-contract.py` gate rc=0 ("ratchet contract OK", 34 guards
discovered), `--self-test` 34/34, `check-selftest-counts.py` rc=0 (37 declare a count),
`check-fixture-variation.py` rc=0 (457 params / 49 files / 6 exempt), `check-fixture-variation.py
--self-test` 60/60, `check-plan-code.py --self-test` 128/128. Every mutation below was applied to a
**staged copy** under the scratch dir; the repo was never edited. Red case names were parsed with
`check-plan-code.parse_fail_names`, imported, not re-implemented.

---

## Findings

### Blocking — the self-exemption is RELOCATED, not removed: the guard still exempts itself from R4, now via its own ESCAPE_CASES fixture

**Where:** `scripts/check-ratchet-contract.py:261-274` (`check_manifest`, which searches the whole
file `text`) against `scripts/check-ratchet-contract.py:500`.

**What:** The branch's headline claim — commit message: *"`check-ratchet-contract.py` enforces that
rule and has never satisfied it … Now `NO-MUTATIONS:[ \t]+([A-Za-z][^\n]*)`"* — is not achieved. The
old match at docstring line 16 is indeed refused by the new pattern. But `check_manifest` searches
the **entire file**, and the branch added a new fixture at `:500` that the **new** pattern matches:

```python
    ("a real written reason exempts", "NO-MUTATIONS: a pure wrapper, no branches to weaken", True),
```

The file is passing R4 today only because `Path(path).stem in manifest_stems` is checked *first* and
the new manifest exists. Strip the manifest and the escape hatch fires exactly as before — from a
different line. The fixture that *proves the escape works* is itself a use of the escape. That is
verbatim the shape the branch's own comment at `:237-239` cites as the reason for the change
(*"`\"[FAIL] \" in source` is unfalsifiable because the comment explaining the contract QUOTES the
marker"*), reproduced in the commit that fixes it.

**Failing scenario:** someone deletes `scripts/mutations/check-ratchet-contract.json` (and its
`EXPECTED_MUTATIONS` entry, which is the paired edit `check-plan-code.py:988-994` would demand).
R4 should then fire on this file. It does not — silently.

**Evidence:**

```
check_manifest("scripts/check-ratchet-contract.py", text, {"check-ratchet-contract"})  ->  []
check_manifest("scripts/check-ratchet-contract.py", text, set())                       ->  []   # ⛔
NEW regex match in the file: 'NO-MUTATIONS: a pure wrapper, no branches to weaken", True),'  at line 500
```

The choice of *whole file* over *docstring* is also **unguarded**. I staged the minimal fix — scope
`check_manifest` to `ast.get_docstring`, matching `check_caller`'s existing shape at `:154` and the
contract as written at `:226` and `:273` (*"`NO-MUTATIONS: <why>` **in the docstring**"*) — and the
suite stayed fully green:

```
('check_manifest on docstring only', 'rc=0', [])      # no case notices the difference
```

Same fix, applied to the real file, produces the behaviour the branch claims:

```
NO_MUTATIONS_RE on the DOCSTRING                      -> None
docstring-scoped check_manifest, no manifest present  -> ['R4_no_mutation_manifest']
```

So the fix is one line, keeps all 34 cases green, and needs a case of its own
(*"a NO-MUTATIONS outside the docstring does not exempt"*) plus a manifest entry, since nothing
currently covers it.

---

### Blocking — `NO_CALLER_RE` has the IDENTICAL defect in the IDENTICAL docstring, one rule up, and the class was never searched

**Where:** `scripts/check-ratchet-contract.py:123` against its own docstring `:15`.

**What:** The branch tightened R4's escape and left R3's — the sibling it explicitly models itself on
(`:226-228`: *"exactly as NO-CALLER works above. Same rule, same shape, deliberately"*) — on the old
loose pattern:

```python
NO_CALLER_RE = re.compile(r"NO-CALLER:[ \t]*(\S[^\n]*)")
```

Docstring line 15 of the same file reads:

```
  R3  something EXECUTES it, or `NO-CALLER:`  ENFORCED
```

`[ \t]*` matches zero, `\S` takes the backtick, and the guard reads its own documentation of R3's
escape as a use of it — the same sentence the commit message uses to justify the R4 change. Measured
across all 34 guards: this is again **the only file affected**, and it is the same file.

**Failing scenario:** the `python3 scripts/check-ratchet-contract.py` step is dropped from
`.github/workflows/ci.yml:193` (its only real caller, confirmed below). R3 exists precisely to catch
"a guard nobody executes" — the failure the file's own comment at `:396-400` says this project has
recorded four times. It would stay silent.

**Evidence:**

```
NO_CALLER_RE on its OWN docstring          -> 'NO-CALLER:`  ENFORCED'
check_caller(rel, text, "")  [EMPTY blob]  -> []        # ⛔ no violation with no caller at all
every guard of 34 whose docstring self-matches NO-CALLER:
  scripts/check-ratchet-contract.py: 'NO-CALLER:`  ENFORCED'      (count: 1)

REAL INVOCATIONS, via the guard's own invocation_re("check-ratchet-contract.py"):
  .github/workflows/ci.yml:193: run: python3 scripts/check-ratchet-contract.py      (count: 1)
```

Latent today because ci.yml really runs it — but R3's protection *for this file* is vacuous, which
is the property the repo's own `check-gate-falsifiability.py` exists to refuse.

Verified fix — the symmetric tightening, which is what "same rule, same shape, deliberately" actually
implies:

```
tighten NO_CALLER_RE to r"NO-CALLER:[ \t]+([A-Za-z][^\n]*)"   -> self-test rc=0, 0 red cases
  check_caller(empty blob)   -> ['R3_no_caller']       # now fires
  check_caller(real ci.yml)  -> []                     # still correct
```

All three existing `NO-CALLER` cases (`OPTED_OUT`, `OPTED_OUT_BARE`, `OPTED_OUT_BARE_THEN_PROSE`)
still pass. This is the repo's recorded *after fixing, SEARCH for the class* lesson: the branch fixed
the instance it tripped over and the identical sibling sat four lines from the diff.

---

### High — "TENTH FILE TO PAY THE FAILURE-LINE TRAP" is false, and it resurrects a number PR #293 retired one commit earlier

**Where:** `scripts/check-ratchet-contract.py:566`, `scripts/check-plan-code.py:669-670`,
`docs/dashboard-entries.md:7874`, and the commit message.

**What:** Two problems. First, the number is wrong — by a lot. Second, `7674fe87` (PR #293, the
branch's own base) explicitly **retired** this ordinal after getting it wrong three times, and
prescribed a derivation. `docs/dashboard-entries.md:7741-7747`:

> ⟳⟳ **THE COUNT OF FILES THAT PAID THIS IS NO LONGER RECORDED, after three attempts got it wrong
> three ways.** v1 "third file" — wrong. v2 "ninth, third with this shape" — wrong again … Each
> correction was written from a reviewer's table rather than from git. The population is now DERIVED:
> `git log -S'[FAIL] ' --reverse --format='%h %as %s' -- scripts/<file>`.

The branch cites `#293`'s *body* ("the tenth is only a matter of time") as authority while its
*conclusion* was the opposite, and supplies no derivation of its own.

**Failing scenario:** a reader trusts a committed ordinal that three prior attempts already got
wrong, in three files.

**Evidence:** running #293's prescribed command over every `scripts/*.py` containing the marker, and
counting files whose first `[FAIL] `-adding commit also deleted a non-conforming printer:

```
2026-09-06  187e5a08  PAID#1   scripts/begin-plan.py
...
2026-09-07  d29898c6  PAID#13  scripts/check-ci-watched.py
...
2026-09-10  050913f6  PAID#21  scripts/gen-backlog-page.py
2026-09-12  7674fe87  PAID#22  scripts/gen-goals-page.py
2026-09-12  a5bfe9c5  PAID#23  scripts/check-ratchet-contract.py

TOTAL: 23
```

The single commit `d29898c6` settles it without any need to trust my predicate — its subject is
**"All eleven remaining guards now emit a parseable failure line (contract 1) (#252)"**, dated
2026-09-07. Eleven in one commit, five days before this branch. `gen-goals-page.py` (PR #293) is #22
here, not the ninth. Under any reading the number is ≥20; it is not ten. Delete it from all three
sites, per #293's own ruling.

---

### High — "Seven printers said `  FAIL {name}`" is false: there were FIVE

**Where:** `docs/dashboard-entries.md:7874` and the commit message ("Seven printers said
`  FAIL {name}`").

**What:** The base file has exactly **five** non-conforming printers. HEAD has **eight** `[FAIL] `
printers, because the branch added three *new* case loops (`WIDENED_POP_CASES`, `ESCAPE_CASES`,
`WIDENED_DRIFT_CASES`) each with its own printer. The claim counts three brand-new, never-broken
printers as pre-existing defects paid off.

**Failing scenario:** the same class the finding above names — a debt figure written from the
end-state rather than from the diff, inflating what was fixed.

**Evidence:**

```
BASE 7674fe87, printers in check-ratchet-contract.py:
  :407 :412 :417 :422 :447   print(f"  FAIL {name}\n ...")      -> FIVE
git diff, removed lines matching '^-.*FAIL'                     -> 5
HEAD, grep -c 'print(f"\[FAIL\] ' scripts/check-ratchet-contract.py -> 8
```

---

### Medium — `m4_catalog.py` has no self-test at all; the `rc=0` recorded as its evidence is the CANNOT-RUN-reads-as-success shape

**Where:** `scripts/check-ratchet-contract.py:283-290`.

**What:** That comment claims *"FOUR scripts outside it have a working self-test and no manifest,
**verified by RUNNING each rather than by reading it**"*, and lists:

```
#     m4_catalog.py              rc=0
```

`m4_catalog.py` is a pure library module — no `main()`, no `if __name__ == "__main__"`, no argv
dispatch anywhere. It exits 0 for *any* argument, including nonsense. `rc=0` here is the exit code of
importing a module and doing nothing, which proves nothing at all — precisely the *"'cannot run' is a
FAILURE, never a pass"* rule in `CLAUDE.md`. Its membership in the widened population comes from
prose alone: `m4_catalog.py:54` reads *"`check-live-schema.py --self-test` asserts each column…"*.

This is also the one concrete answer to the branch's attack-point-4 argument (`:293-297`: a
prose-swept file "fails CLOSED and names itself"). The argument is structurally sound and I confirm
it holds — but exactly **1 of the 16** widened files is there by prose, and the branch pinned it with
evidence asserting the opposite.

**Failing scenario:** the pin's stated reason ("it has a working self-test") is the thing a future
reader uses to decide what paying the debt means. Paying it would mean writing a mutation manifest
for a suite that does not exist.

**Evidence:**

```
grep -n "argv|__main__|def main|argparse" scripts/m4_catalog.py   -> 1 hit, prose at :496
python3 scripts/m4_catalog.py --self-test                 -> (no output) rc=0
python3 scripts/m4_catalog.py --this-flag-does-not-exist  -> (no output) rc=0    # ⛔ identical
```

The other three ARE real, verified by running them: `codex-review.py` 63/63, `verify-exclusion-
reasons.py` 11/11, `build-m4-schema.py` 22/22. The claim is 3-for-4; the fix is to change
`m4_catalog.py`'s line to say it is swept in by prose and has no suite, which `:293-297` already
argues is a perfectly good reason.

---

### Medium — the two sibling escapes now accept different things, undocumented, and the violation message cannot explain a rejection

**Where:** `scripts/check-ratchet-contract.py:123` vs `:241`; message at `:272-274`.

**What:** After this branch, `NO-MUTATIONS:` and `NO-CALLER:` — described at `:226-228` as *"Same
rule, same shape, deliberately"* — have materially different acceptance. In a repo that backticks
identifiers in every sentence, a backtick-led reason is a likely first spelling, and it is now
silently refused while the identical `NO-CALLER:` form is accepted. The R4 message says *"no written
`NO-MUTATIONS: <why>`"*, which reads as *you didn't write one* to an author who did.

**Failing scenario:** an author writes ``NO-MUTATIONS: `evaluate()` is pure; a mutation would only
restate the self-test``, the gate stays red, and the message points them at the one thing they have
already done.

**Evidence:**

```
REFUSE | NO-MUTATIONS: `evaluate()` is pure; a mutation would only restate the self-test
REFUSE | NO-MUTATIONS: 3 lines of glue, no branches to weaken
REFUSE | NO-MUTATIONS: "pure wrapper" - nothing to weaken
REFUSE | NO-MUTATIONS: ⚠ prose match only; there is no suite
REFUSE | NO-MUTATIONS: — the regex matched prose; there is no suite
ACCEPT | NO-MUTATIONS: the regex matched prose; there is no suite

--- the SAME strings under NO_CALLER_RE (unchanged by this branch) ---
ACCEPT | NO-CALLER: `evaluate()` is pure; a mutation would only restate the self-test
ACCEPT | NO-CALLER: 3 lines of glue, no branches to weaken
ACCEPT | NO-CALLER: ⚠ prose match only; there is no suite
```

Fixing the R3 finding above by the symmetric tightening resolves the divergence. Separately, the
refusal message should name the rule (*a reason must begin with a letter after a space*) — a guard
that rejects a correct-looking form without saying why is the failure mode `:229` is warning about,
one layer out.

---

### Low — no shipped mutation exercises the `R4W_debt_paid_not_recorded` arm

**Where:** `scripts/check-ratchet-contract.py:350-355`; `scripts/mutations/check-ratchet-contract.json`.

**What:** The six entries cover the first loop of `widened_debt_drift` in both directions, but nothing
deletes the *second* loop. Mutation 3 (`(WIDENED_MANIFEST_DEBT & examined)` → `WIDENED_MANIFEST_DEBT`)
leaves case *"a pinned entry that was EXAMINED and no longer violates fails"* green, so that arm's
existence is asserted by a case no mutation removes. The dashboard entry lists that falsifier under
"**Falsifiers, demonstrated**".

**Failing scenario:** a refactor deletes the paid-not-recorded arm; debt paid off silently stops
being reported, which is the exact ratchet-stops-ratcheting failure `:332-335` argues against.

**Evidence:** the case *is* falsifiable — my probe of the missing mutation:

```
delete paid-not-recorded arm -> rc=1, red: ['a pinned entry that was EXAMINED and no longer violates fails']
```

That mutation kills via exactly one named case and nothing else. It is a clean seventh entry
(`EXPECTED_MUTATIONS` 6 → 7, sum 555 → 556).

---

## Checked and found sound

- **All 6 shipped mutations die via the case each names, over a control proved green first.**
  Verified by staging the subject, applying each entry's edits, running `--self-test`, and parsing
  with the imported `check-plan-code.parse_fail_names`. Control: `rc=0`, zero red cases. All six:
  `rc=1` with the declared `expect` present in the red set. The commit's "6/6 … over a control proved
  green first" is accurate.
- **All 12 new cases are falsifiable.** Nine are killed by the shipped six (including collateral).
  The three that are not, I probed individually, and each reddens under a deletion of its own rule
  and nothing unrelated: *"a self-tested NON-guard is in the widened population"* (via
  `discover_self_tested_nonguards -> []`), *"a real written reason exempts"* (via `[A-Za-z]` →
  `[A-Z]`), *"a pinned entry that was EXAMINED and no longer violates fails"* (via deleting the arm).
  No vacuous case found.
- **"The only affected file of 34" is TRUE for R4, measured at the base commit.** I ran the OLD
  pattern `NO-MUTATIONS:[ \t]*(\S[^\n]*)` and the new one over every `scripts/*.py` at `7674fe87`:
  one file contains the token, `check-ratchet-contract.py`, `OLD=True NEW=False`, guard count 34. The
  claim as scoped is sound. (What is *not* sound is stopping the class search there — see Blocking 2.)
- **`WIDENED_MANIFEST_DEBT` is exactly right by identity.** Measured over the live tree: 55 scripts,
  34 guards, widened population 16, violating 8 — and `violating == WIDENED_MANIFEST_DEBT` is `True`,
  `WIDENED_MANIFEST_DEBT - widened` is empty. The commit's account of the set being wrong at FOUR on
  the first run is consistent with the code (a population excluding self-declared ratchets vs one
  excluding only guards), and the shipped eight are the tool's answer.
- **`examined` is genuinely load-bearing, and so is the pin.** Both mutation-verified, not taken on
  the branch's word: dropping `& examined` reddens *"a pinned entry NOT examined is silent, not
  'paid'"*; dropping `- WIDENED_MANIFEST_DEBT` reddens *"a pinned violator is silent — that is what
  the pin is for"*, and that one kills exactly one case. The `check-fixture-variation` exemption
  comments state this evidence and the evidence is real.
- **All four `check-fixture-variation.py` exemptions are NEEDED, and the guard proves it itself.**
  `dead_exemptions` (`:672-739`) removes each entry and re-analyses over the whole live population,
  refusing any that changes nothing. The gate runs green reporting "6 exempt with a written reason",
  which is that check passing on all six. Not taken from the diff's prose.
- **Only R4 is applied to the widened population.** `evaluate():192-197` calls `check_manifest` on
  the widened set and adds only `widened_debt_drift`'s output to `out`, so widened violations never
  reach the `R4_no_mutation_manifest` count that `MANIFEST_BASELINE` gates at `:716`. The commit's
  "widening four rules at once would be a different change wearing this one's name" is implemented as
  described, and the guard/non-guard sets are disjoint so no file is charged to two baselines.
- **Arithmetic and anchors are all consistent with disk.** `sum(EXPECTED_MUTATIONS.values()) == 555`
  (declared 555); manifest holds 6 entries and `EXPECTED_MUTATIONS["scripts/check-ratchet-contract.py"]
  == 6`; all 6 `before` anchors occur **exactly once** in the subject; no duplicate entry names, no
  duplicate anchor pairs; all 6 `expect` strings name a real case (five in module-level tables, the
  sixth in the local `wiring` list — confirmed by the mutation actually reddening it); the docstring's
  `# 34 cases` is right (30 table cases + 4 wiring) and the suite prints 34/34; `check-selftest-counts.py`
  runs green with the new POPULATION member; the membership list at `check-plan-code.py:2500` is sorted
  correctly in place.
- **"Suite 22 → 34 cases" is TRUE**, measured by running the base file: `self-test: 22/22 passed`.
- **The `[FAIL] ` printer fix works.** All eight printers emit the name alone on the line, and
  `parse_fail_names` parsed every red case in all nine of my mutation runs — it attributed correctly
  in every one, which is the property the rewrite was for.
- **The failure-line contract comment at `:561-566` is accurate about the mechanism** (`startswith("[FAIL] ")`
  then `[7:]`) — I read `parse_fail_names` rather than trusting the comment. Only its ordinal is wrong.
- **No fail-open handler, and the CANNOT-RUN paths are honest.** `main()` fails closed with "Treat
  this as NOT RUN" on a missing `ci.yml` (`:646`), an unreadable script (`:663`), zero guards
  discovered (`:670`) and too few caller sources (`:682`). R2's own `type(val) is int` refinement at
  `:104-109` is intact and its two negative cases (`RETURNS_NONE`, `RETURNS_FALSE`) still pass.
- **The `docs/` exclusion from `caller_sources` is intact** (`:673-680`), so a row in a
  "mechanically enforced" table still cannot satisfy R3 — the case at `:458-461` covers it.

---

## Verdict

NOT-CONVERGED

Two Blocking findings, and they are the same defect class as each other and as the one the branch
exists to fix. The branch correctly identifies that a rule documenting its own escape will match that
documentation — then ships a new fixture that re-grants the R4 exemption from line 500, and leaves
the character-identical R3 hole four lines above the diff in the same docstring. Both are one-line
fixes I have staged and verified keep all 34 cases green while making the guard actually subject to
its own rules; each needs a case and a manifest entry.

The engineering underneath is strong and I want to be clear about that: the widened population is
correctly disjoint, the debt set is exactly right by identity, `examined` is real and
mutation-proven, the exemptions are each proven needed by the guard itself, and 6/6 mutations kill
via the case they name over a green control. What repeatedly fails is the *prose*: the ordinal
(claimed tenth, derived ≥23, and retired by the base commit for being wrong three times), the printer
count (claimed seven, measured five), and one of four "verified by RUNNING" claims (`m4_catalog.py`
has no self-test; its `rc=0` is the cannot-run-reads-as-success shape). That is 2 of 5 load-bearing
historical claims sound — the pattern the review brief warned about, unchanged.
