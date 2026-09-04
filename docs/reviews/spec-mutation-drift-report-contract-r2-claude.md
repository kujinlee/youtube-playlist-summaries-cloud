# Spec review round 2 — Claude half — mutation drift report contract

**Subject:** spec **v2**, SCOPED to v2's own changes. **Date:** 2026-09-03.
**Verdict: NOT CONVERGED — 1 Blocking.**

> **METHOD.** Coordinator-written (standing session instruction: no subagent dispatch), findings
> produced by reading the code around the changed region, not by re-reading the spec. **Written to
> the scratchpad, not the repo**, so the concurrent Codex run cannot mis-attribute it — the concrete
> fix for round 1's wrapper false positive.

---

## B2 — 🔴 BLOCKING. R1's enumeration is still incomplete: `:663` can also be a NOT-CHECKED return

v2 restated R1 as *"when `run_mutations` has not returned — i.e. any return at `:586`, `:626` or
`:646`"*, and moved option (a)'s flip to `:648`. **That fixes B1 and introduces the same defect one
layer later.**

`:649-663` is the **after-control**, and its own comment states the problem:

```python
:647  ok, m_report, m_muts, m_survivors = run_mutations(d, muts, set(targets))
:648  ev["mutations"], ev["survivors"] = m_muts, m_survivors      # <-- v2 flips `ran` HERE
:654  for name in targets:
:655      rc, out = run_suite(d, name)
:656      if rc != 0:
:657          ok = False
:658          m_report.append(
:659              f"CANNOT RUN — {name} is no longer green AFTER the sequence (exit {rc}), "
:660              f"so the tree changed underneath it. Any 'caught' above may be an artefact "
:661              f"of that, not of its mutation. Treat this run as NOT CHECKED.")
:663  return ok, m_report, ev
```

So there is a return where `run_mutations` **did** return, the tally **is** populated, and the run is
**explicitly declared NOT CHECKED by the code itself**. Under v2, `ran` is already `True` at `:648`,
so the final line prints:

```
FAILED — delivered scripts mutated: 7 file(s), 162 mutation(s), 0 survivor(s)
```

**`0 survivor(s)` is precisely the claim the after-control has just invalidated.** The comment at
`:650-653` says every `caught` verdict above may be an environmental artefact. A tally whose headline
number is "everything was caught" is the single most misleading thing to print next to *"treat this
run as NOT CHECKED"*.

**This is the eighth consecutive round in this slice whose new defect is inside the previous round's
fix**, and it is the same class as B1: a landmark chosen for *when it happens* rather than for *what
it means*. B1's landmark was `copytree`; v2's is `run_mutations` returning. Neither is the property
that matters, which is **"is this tally a trustworthy measurement"**.

**Why "did `run_mutations` return" cannot be the predicate.** It is true at `:663` regardless of
whether the after-control passed. The trustworthiness of the tally is a *second axis*, and `ok` alone
cannot carry it — `ok=False` is also a genuine survivor result, which is why option (c) was refuted
in round 1. **There are three states, not two:**

| state | tally | reached |
|---|---|---|
| did not run | must be absent | `:586`, `:626`, `:646` |
| ran, trustworthy | present | `:663` with after-control green |
| **ran, NOT CHECKED** | **must not be presented as coverage** | **`:663` with after-control red** |

**Shape (not decided — this is the fork for v3):** either the sentinel is lowered again at `:657`
alongside `ok = False`, or the flag stops being boolean and names the state. The second is probably
right, because the first re-creates the "flag set in one place, meaning decided in another" split
that produced B1.

**Falsifier:** make a target's suite pass the control and fail *after* the sequence — e.g. a suite
that fails only when a marker file written during the run exists. The final line must not present a
mutation/survivor tally as a result.

### ✅ MEASURED after the Codex half landed — the caveat below is RESOLVED

This finding was first written as a **hypothesis**, explicitly labelled *"I have NOT run it"*. The
Codex half then pointed at an existing fixture — `:1918-1933`, where `thing.py` poisons itself on its
**third** run so only the after-control is red — and the path was measured by wrapping
`mutate_delivered` and running the suite:

```
call  (ok, after_control_red, files, mutations, survivors)
  1   (True,  False, 1, 1, 0)   normal green
  2   (False, False, 1, 0, 0)   :646 control failure  -> prints "1 file(s)"
3,4,5 (False, False, 0, 0, 0)   :586 / :626
  6   (False, TRUE,  1, 1, 0)   <-- AFTER-CONTROL RED, tally POPULATED
  7   (False, False, 0, 0, 0)
158/158 passed
```

**Call 6 confirms it:** `mutations=1, survivors=0` on a run the code declares NOT CHECKED. The final
line would read `FAILED — delivered scripts mutated: 1 file(s), 1 mutation(s), 0 survivor(s)` — which
is the numbers Codex predicted **exactly**, before either of us ran it.

**The whole return taxonomy is now empirical**, in one table, which is what R1 should have been
derived from in the first place.

---

## Checked and correct in v2

- **F2a/F2b/F2c reach distinct returns.** Verified by execution in round 1: F2a's clone trips `:562`
  in `load_manifests` → `:586`; F2b's distinct anchor trips the count check → `:626`; F2c's
  `raise SystemExit(1)` produces a control-run failure → `:646`. Three of four returns, all measured.
- **Call sites = 8.** Independently recounted by Codex in round 1.
- **§7's order-dependent arithmetic.** 162 + 1 (F4) = 163 for this spec; the sibling plan's six
  entries against a base that now includes this one gives **169** if this lands first. Consistent.
- **R1a is right and was the non-obvious part.** Suppressing only the mutation/survivor pair would
  leave `7 file(s)` asserting work on a control-failure run.

## Verdict

**NOT CONVERGED.** One Blocking, and it is in v2's own fix.

**Recommendation — and it is about the process, not the spec.** This is the eighth round of
fix-introduces-next-defect. The spec is now three states where it started as two, and each round has
discovered a state rather than a bug. **Consider writing the state machine down first** — enumerate
what the final line can truthfully claim, then derive the flag — instead of patching the flip point
a third time.
