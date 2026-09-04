# Code review round 4 — Claude half — scoped to round 3's fix

**Subject:** `scripts/check-plan-code.py` and `scripts/mutations/check-plan-code.json`, as folded by
round 3 (`b9b635e2`, merged as `87ea0001`, PR #214). **Date:** 2026-09-03.
**Verdict:** 1 Blocking, 1 High, 1 Medium, 1 Low.

Every claim below names the command that produced it. Throwaway scripts were written outside the
repo; the only file this review created is itself.

> ### ⚠ Provenance — what every measurement here was taken against
>
> **The working tree changed underneath this review at 18:18:48**, while it was being written:
> `scripts/check-plan-code.py` acquired an uncommitted `control_is_green(rc, out)` helper whose
> docstring quotes M1 below verbatim. That is somebody's in-flight fix for a finding in this file,
> not the subject of this review, and it is **not** what anything below measured. Established rather
> than assumed:
>
> ```bash
> git show HEAD:scripts/check-plan-code.py | shasum      # 2bef2804…
> git show 87ea0001:scripts/check-plan-code.py | shasum  # 2bef2804…  (identical)
> # the working copy taken at 18:04, with this review's one patch reverted, == that blob byte for byte
> # scratchpad/mutate.log finished 18:17:39 — BEFORE 18:18:48, so --mutate . also ran on the pristine tree
> ```
>
> **One observation about the in-flight fix, offered unpriced because it is not finished:** with it
> applied, `--self-test` is still `177/177`, the manifest still holds 32 entries, and nothing names
> `control_is_green`. If it lands in that state it is the same missing-falsifier shape as B1 below,
> inside the fix for M1 below.

---

## 🔴 Blocking — B1. The `--mutate` printer's trustworthiness gate has NO falsifier, and it is the printer CI actually runs

Round 3's B2 was *"the r2 fix had no falsifier"*, rated **Blocking** by the round-3 Claude half. It
enumerated four ways to delete or invert the fix, each of which left `--self-test` at 164/164, and
closed them with 8 mutations and 13 cases — including
`case("plan mode refuses to print a tally it did not earn", …)` at `:1264`, added specifically
because reverting the **plan-mode** printer gate left the suite green.

There are **two** printers. Round 3 covered one.

```
scripts/check-plan-code.py:2361   if ev["trustworthy"]:                                    # --mutate mode
scripts/check-plan-code.py:2408   if ev.get("trustworthy") or ev.get("declared") is None:  # plan mode
```

`:2408` has mutation *"the plan-mode printer stops gating on trustworthiness (r3 B2)"* and the case
above. **`:2361` has neither.** Enumerated mechanically over the whole manifest — no entry names it:

```bash
python3 - <<'EOF'   # bind all 32 anchors to a line number in the delivered file
… src.index(find) → lineno …
EOF
#   30  the plan-mode printer stops gating on trustworthiness (r3 B2)   2408  main  prod
#   (no entry resolves to 2361)
```

**Falsified by execution.** On an out-of-repo copy, with the gate hardcoded open:

```bash
cp -R scripts $S/w1/scripts
# '        if ev["trustworthy"]:'  ->  '        if True:'
python3 scripts/check-plan-code.py --self-test
#   177/177 passed          <-- unchanged. Nothing sees it.
```

And the behaviour that buys, driven through `main(["--mutate", root])` on a tree whose after-control
goes red (the `runs.txt` self-poisoning fixture the suite already uses at `:2135`):

```
DELIVERED     rc=1  ✗ CANNOT RUN — scripts/thing.py is no longer green AFTER the sequence…
                    NOT MEASURED — the mutation harness produced no coverage verdict. Treat this as NOT CHECKED.

GATE OPEN     rc=1  ✗ CANNOT RUN — scripts/thing.py is no longer green AFTER the sequence…
                    FAILED — delivered scripts mutated: 1 file(s), 1 mutation(s), 0 survivor(s)
```

The second line is exactly what the code's own comment at `:2366-2369` says must never be printed:

> *NO tally — and that includes the FILE count. … "0 survivor(s)" beside it is this project's
> success sentence printed over a run that never produced a verdict.*

**Why Blocking rather than High.** Three things compound:

1. It is the *same construct in the sibling producer* — the defect class this slice has now
   reproduced seven rounds running, and the one round 3's own commit message names in capitals
   (*"a shared function that holds part of a contract is worse than two copies"*).
2. **CI runs `--mutate .` and `--self-test`, and does not run plan mode at all**
   (`.github/workflows/ci.yml:262`, `:268`; `docs/dev-process.md:156` — *"the `<plan> --compare
   --verify-evidence` mode … is **no longer in CI**"*). Round 3 built the falsifier for the printer
   CI never invokes and left the printer CI depends on uncovered.
3. It is the identical severity the project assigned to this property one round ago. Rating it lower
   here would be re-pricing the same defect because it is the second instance.

**Fix.** Add the mutation (anchor `        if ev["trustworthy"]:` → `        if True:`) and a case
that drives `main(["--mutate", …])` on the poisoned fixture and asserts
`("NOT MEASURED" in out, "survivor(s)" in out) == (True, False)` — the exact shape of the plan-mode
case at `:1264`. `EXPECTED_MUTATIONS["scripts/check-plan-code.py"]` 32 → 33, sum 173 → 174.

---

## 🟠 High — H1. The durable evidence block still prints `caught N`, and a `caught` line per entry, underneath its own NOT MEASURED refusal

Round 3's B4 fixed `evidence()`'s **header**. The two lines below it were not touched, and they make
the same claim in the same vocabulary.

`evidence()` `:998-1008`:

```python
if ev.get("declared") is not None and not ev.get("trustworthy"):
    out.append("  " + not_measured_line(ev))
    out.append(f"  mutation entries recorded: {len(ev['mutations'])}, caught {caught}")
else:
    out.append(f"  mutations declared and run: {len(ev['mutations'])}, caught {caught}")
for m in ev["mutations"]:
    verdict = ("caught  " if m["caught"] else …)
```

**Reproduced in round 3's own B1 scenario** — a suite that is red with or without the mutation, and a
mutation that edits **only a comment**, exactly the case the round-3 commit message describes:

```python
ok, rep, ev = m.check(pl)     # RED suite + a KEEPME-comment-only mutation
# ok = False   trustworthy = False   declared = 1
# entries = [{'name': 'a COMMENT-ONLY edit over an already-red suite', 'caught': True, …}]
print(m.evidence(ev))
```

```
  NOT MEASURED — the mutation harness produced no coverage verdict. Treat this as NOT CHECKED.
  mutation entries recorded: 1, caught 1
    caught   a COMMENT-ONLY edit over an already-red suite
```

At realistic scale the after-control path renders `mutation entries recorded: 5, caught 5` followed
by five `caught   <name>` lines (rendered on a synthetic `ev`; see *Checked and correct*).

Three reasons this is not cosmetic:

- **`caught` is precisely the word round 3 says is empty here.** `run_mutations`' after-control
  comment at `:733-737` and the emitted report both say *"Any 'caught' above may be an artefact"*.
  The block asserts it five times under a line saying it was not measured.
- **The two producers of one refusal now disagree, and the more permissive one is the durable one.**
  The console `--mutate` printer deliberately emits *no tally at all* on this path, with a comment
  explaining that a tally beside a refusal reads as coverage. The evidence block — which is pasted
  into a plan and, per the same B4 rationale, *"outlives the console line that carried the truth"* —
  keeps its tally.
- **`--verify-evidence` re-derives this block and certifies it FRESH** (`verify_evidence` `:1051-1053`
  compares pasted against `evidence(ev)`), so the overstatement is stable, not transient.

The case that guards this, `:2208`, asserts only `"NOT MEASURED" in …` and
`"mutations declared and run" not in …`. It says nothing about the count or the per-entry verdicts,
so it stays green over the output above — verified: the case passes on the delivered code, which
produces that block.

**Fix.** On the untrustworthy branch, render entries as `NOT RUN ` regardless of `m["caught"]`, or
drop the `caught {caught}` figure from the refusal header. Either way, add the assertion the current
case is missing: `"caught" not in evidence(_ev_ac)`.

---

## 🟡 Medium — M1. `controls_green` means two different things in the two producers, one round after the predicate was unified to stop exactly that

Round 3 widened `verdicts_are_trustworthy(m_muts, declared, controls_green)` so both producers hold
one contract. The *argument* they hand it was not unified.

`check()` `:937-945` — a control is green only if it exited 0 **and reported a result**:

```python
if rc != 0:                    ok = False; controls_green = False
elif "passed" not in out:      ok = False; controls_green = False   # "a script with no entrypoint exits 0 silently"
```

`mutate_delivered` `:718-727` and `:744-755` — a control is green if it exited 0. There is no second
clause in either the before- or the after-control.

**Executed.** A `scripts/thing.py` with no `__main__` entrypoint (exits 0, prints nothing):

```
--mutate over a SILENTLY-EXITING suite:
   ok = False   trustworthy = True
   control rc = {'scripts/thing.py': 0}   tail = {'scripts/thing.py': "''"}
   report = ['mutation SURVIVED — marker flipped: …']
```

`trustworthy = True` over a control that was never shown to execute anything.

**Priced Medium, not High, deliberately.** I tried and failed to construct a route where this yields
`ok = True`: a silent control makes every mutation a SURVIVOR (`caught = rc == 1` is False), and a
mutation that *does* make the file exit 1 produces no `[FAIL]` line, so the `expect` check fires. Every
route I could build ends in exit 1. So the harm today is a mislabelled flag, not a false green — but
it is the same clause, named the same thing, meaning two different things in the two producers of one
predicate, which is the shape this slice keeps paying for.

**Fix.** Give `mutate_delivered`'s controls `check()`'s second clause, or extract the
"is this control green" test into one function both call.

---

## 🟢 Low — L1. The design's "three skip sites" is four, stated in four places

The cardinality clause's justification is that nobody should have to re-enumerate the skip sites. The
enumeration written beside it is already off by one.

```bash
python3 - <<'EOF'   # AST-walk run_mutations for every branch that skips WITHOUT appending to ev_muts
EOF
#   guarding conditions:  fname not in known        (:780 → continue :783)
#                         src.count(find) > 1       (:793 → break :800 → continue :809)
#                         find not in src           (:801 → break :806 → continue :809)
#                         isinstance(want, list) and (not want)   (:860 → continue :866)
```

Four conditions; two of them share one `continue`, which is presumably how the count became three.
Stated as three at `:395` (round-3 text), `:661`, `:992` (round-3 text) and `:1277` (round-3 text).
The `len(m_muts) == declared` arithmetic covers all four, so nothing is broken — but the sentence
whose whole job is to bound a set gets the set's size wrong, and three of the four copies were
written by the round being reviewed.

**Fix.** Say four, and name the ambiguous anchor alongside the missing one.

---

## Checked and correct

Each of these was a named risk in the brief or a hypothesis of mine; each was probed and cleared.

**A THIRD orphaned mutation — none.** Round 3 touched exactly two files
(`git show b9b635e2 --stat`: `scripts/check-plan-code.py`, `scripts/mutations/check-plan-code.json`),
so orphan risk is confined to those 32 anchors. All 32 were bound mechanically to a line number and
classified by `ast` + `tokenize`:

```
 32 anchors:  32 bind, 32 match EXACTLY ONCE, 32 land in production code
              0 land inside _self_test (lines 1097-2316)
              0 land on a comment-only or docstring-only construct
```

The "binds but measures the wrong construct" class was the specific thing looked for: an anchor
resolving into the suite's own fixtures rather than the code it names. There are none. (The
classifier flagged several lines as "STRING" because the anchor text *contains* a string literal —
e.g. `and all(m.get("measured") is True …)` — which is a false positive of my classifier, not a
finding.)

**All 13 new cases are non-vacuous.** Each property was broken on a copy and the suite re-run; every
one reddened **via its own name**, with a legible message. Where a break reddened siblings too, the
named case was still among them, and I used discriminating breaks to separate paired cases (e.g.
`len == declared` → `len > declared` reddens *"…and the same entries at their declared count are"*
while leaving *"a SHORTFALL is not trustworthy"* green; `.get("measured", True)` reddens the
MISSING-key case while leaving the TRUTHY-non-True case green).

```
RED-via-case  a RED control makes check() withhold trust, whatever the tally says
RED-via-case  ...though every declared mutation still produced a verdict
RED-via-case  ...and a GREEN control with a complete run still earns it
RED-via-case  plan mode refuses to print a tally it did not earn
RED-via-case  a plan with NO tagged blocks reports no verdict, not a trustworthy zero
RED-via-case  a SHORTFALL is not trustworthy, however good the entries are
RED-via-case  ...and the same entries at their declared count are
RED-via-case  ...and a red control alone is disqualifying
RED-via-case  a TRUTHY-but-not-True `measured` is refused
RED-via-case  ...and a MISSING `measured` key is refused too
RED-via-case  the evidence block refuses a tally over an untrustworthy run
RED-via-case  ...and a SHORTFALL names how many of how many produced a verdict
RED-via-case  ...and a trustworthy run still prints the plain tally, unchanged
```

**All 8 new + 2 retargeted mutations redden via the case they NAME.** Applied by hand to copies
(not via `--mutate`), one at a time, checking the named case appears in the `[FAIL]` list:

```
the shared predicate stops holding the CONTROL clause (r3 B1)      -> ...and a red control alone is disqualifying                      ✓
the shared predicate stops holding the CARDINALITY clause (r3 B5)  -> a SHORTFALL is not trustworthy, however good the entries are     ✓
`measured` is read by truthiness … (r3 B6)                         -> a TRUTHY-but-not-True `measured` is refused                      ✓
check() stops passing its control result to the predicate (r3 B1)  -> a RED control makes check() withhold trust…                      ✓
check()'s evidence dict fails OPEN again (r3 B2)                   -> a plan with NO tagged blocks reports no verdict…                 ✓
the plan-mode printer stops gating on trustworthiness (r3 B2)      -> plan mode refuses to print a tally it did not earn               ✓
the evidence BLOCK stops gating … (r3 B4)                          -> the evidence block refuses a tally over an untrustworthy run     ✓
the NOT MEASURED sentence loses its shortfall arithmetic (r3 B4)   -> ...and a SHORTFALL names how many of how many produced a verdict ✓
[RETARGETED] the after-control stops invalidating the run          -> ...and it is NOT trustworthy, though every declared mutation ran  ✓
[RETARGETED] a cannot-run mutation counts as a verdict again       -> a TIMED-OUT mutation is counted but is NOT a verdict             ✓
```

The two retargets are correct: the old anchors (`ev["trustworthy"] = False` in the after-control
loop, and the one-line `return len(m_muts) == declared and all(…)`) no longer exist, and the new ones
bind to the constructs that replaced them.

**`controls_green` starting `True` in `mutate_delivered` is sound.** Every path reaching the
assignment at `:743` was enumerated. Three returns precede it — `:667` (`problems`), `:707` (`drift`),
`:727` (`report`, populated only by `rc != 0` in the before-control loop at `:718-725`). `run_suite`
returns 2 on timeout, which `rc != 0` covers. `targets` cannot be empty (an empty manifest set fails
at `load_manifests` and again at the `EXPECTED_MUTATIONS` drift check). So reaching `:743` implies
every before-control exited 0. The claim holds. (Whether "exited 0" is a strong enough definition of
green is M1 above — a different objection.)

**F2-S3 for `--mutate` mode — PROVEN BY EXECUTION, not diff inspection.** Driving
`main(["--mutate", root])` on a healthy tree and on the after-control-red tree:

```
HEALTHY                rc=0   OK — delivered scripts mutated: 1 file(s), 1 mutation(s), 0 survivor(s)
AFTER-CONTROL RED      rc=1   NOT MEASURED — the mutation harness produced no coverage verdict. Treat this as NOT CHECKED.
```

A trustworthy run prints exactly the line it printed before round 3 touched the printer. The gate is
invisible when earned.

**`not_measured_line`'s `subject` parameter introduces no sentence drift.** Both surviving call sites
render byte-identical text to their pre-round-3 originals
(`git show 'b9b635e2^:scripts/check-plan-code.py'` `:2191-2194`, `:2234-2237`):

```
--mutate   'NOT MEASURED — the mutation harness produced no coverage verdict. Treat this as NOT CHECKED.'
plan       "NOT MEASURED — plan's copy only, NOT compared: the mutation harness produced no coverage verdict. Treat this as NOT CHECKED."
shortfall  'NOT MEASURED — … verdict (1 of 3 declared mutation(s) produced a verdict). Treat this as NOT CHECKED.'
```

One real change, in the safe direction: the `--mutate` site now reads `ev.get("declared")` where it
read `ev["declared"]`.

**`check()` withholds trust but does not refuse — no caller can act on a run that should have been
refused, on the exit-code path.** `controls_green = False` in `check()` is always set alongside
`ok = False` (`:937-945`), so the process exits 1; `main` gates its final line at `:2408`; `--mutate`
refuses `--evidence` outright at `:2345-2352`. The one place a caller *can* still act on it is the
pasted evidence block — which is H1, and is why H1 is where the design question landed rather than
being left NOT CHECKED as it was in round 3.

**Counts agree with reality and with everything that quotes them.**

```bash
python3 scripts/check-plan-code.py --self-test        # 177/177 passed  (docstring :8 declares 177; count_drift derives it)
python3 scripts/check-selftest-counts.py              # 9 script(s) declare a count, every one verified by running it
# manifest entries on disk == EXPECTED_MUTATIONS, per file, all seven; sum = 173
```

Quoters: `docs/roadmap-to-launch.md:1760` (*"177 self-test cases, 32 mutations on this file,
EXPECTED_MUTATIONS sum 173"*) and `docs/dashboard-entries.md:3038-3039` — both correct.
`docs/dev-process.md:156` and `docs/roadmap-to-launch.md:1347` deliberately restate no live number.

**The delivered tree is green end-to-end.**

```bash
python3 scripts/check-plan-code.py --mutate .
#   OK — delivered scripts mutated: 7 file(s), 173 mutation(s), 0 survivor(s)   (exit 0)
```

Note what this does *not* say: it is the run that produces the printer output B1 is about, and on a
healthy tree the gate is satisfied, so this green tells you nothing about whether the gate would still
be there tomorrow. That is the whole point of B1.

**The repo's own gates on this script are green.**

```
rc=0  check-guard-coverage · check-vocabulary-collisions · check-ratchet-contract
rc=0  check-selftest-counts · check-docs · check-anchors · check-producer-enumeration
rc=1  check-review-rounds   — "round 4: only codex — claude neither ran nor recorded a REVIEW GAP"
                              i.e. this file. It goes green when this file lands.
```

---

## Not checked

Severity unpriced for each.

- **The Codex round-4 half.** Deliberately not read, to keep the halves independent. Adjudication is
  the coordinator's step.
- **The plan-assembling mode against a real plan document** (`<plan> --compare --verify-evidence` over
  `docs/superpowers/plans/…`). Exercised only through synthetic fixtures here. It is not in CI, and
  round 3 did not change `compare_delivered` or `pasted_evidence`.
- **The other six manifests' anchors** (`check-dashboard-entry`, `gen-dashboard`, `page_chrome`,
  `page_markup`, `check-selftest-counts`, `check-theme-token-coverage` — 141 entries). Round 3 edited
  neither those files nor those manifests, so no round-3 change can have orphaned them; I did not
  re-audit them for pre-existing drift.
- **Whether H1's fix should relabel the entries or drop the count.** Two defensible shapes; I state
  the property that must hold, not which one to pick.

---

## Verdict

Round 3 did the hard part correctly. Its central claim — that the streak's *cause* was a positional
proxy for a semantic property, and that `verdicts_are_trustworthy` replaced position with arithmetic —
holds up under attack: I could not break the predicate, could not find a path where
`controls_green = True` is unearned in `mutate_delivered`, could not find an orphaned or
mis-targeting anchor among the 32, and could not find a vacuous case among the 13. The retargets are
right, the sentences did not drift, and the counts are honest.

What it did not do is finish the sweep it started. Its own diagnosis is *one contract, two producers*;
it fixed `evidence()`'s header and the plan-mode printer and left the `--mutate` printer — the one in
CI — with no falsifier at all, and left the evidence block's body asserting `caught` under its own
refusal. Both are the reviewed round's stated defect class, one layer out from where it looked.

**NOT CONVERGED**
