# Code review round 2 — Claude half — scoped to round 1's fix

**Subject:** `HEAD` (`measured` marking + the `all(...)` conjunct), SCOPED to what round 1 changed.
**Date:** 2026-09-03. **Verdict: 0 Blocking, 0 High, 1 Low — and the Low is pre-existing.**

> ⚠ **I am the author, and last round I returned CONVERGED on this same code while it carried a
> Blocking.** Everything below is stated as a claim that can be contradicted, with the command that
> produced it, because that is the distinction that separated what survived round 1 from what did
> not. The Codex half is the real check.

---

## L1 — 🟢 A timeout is still counted as a SURVIVOR, and one printer is ungated

**MEASURED.** Two `ev_survivors.append` sites: `:762` (the cannot-run path) and `:805` (a real
survivor). A timed-out mutation therefore lands in `ev_survivors` as well as `ev_muts`.

**On `--mutate` this cannot leak** — a timeout sets `measured: False`, so `trustworthy` is False and
`:2139` prints no tally at all. Verified end-to-end in round 1 against Codex's own fixture.

**On `check()`'s path it can.** `:2188` prints `len(ev['survivors'])` **unconditionally**, and
`check()` calls `run_mutations` too. A timeout there would inflate the survivor count on a line that
claims to be a result.

**⚠ PRE-EXISTING, not introduced by round 1's fix.** `git log -S 'ev_survivors.append(name)'` traces
it to **`da5cd27e` (PR #176, 2026-08-29)**. Round 1's fix neither caused nor worsened it; it
*narrowed* the exposure from two printers to one.

**Why 🟢 and not filed as work:** `ci.yml:261-262` runs only `--mutate .`, so `check()` is out of CI —
the same scoping the Codex half of spec round 3 rated Low and which was accepted. **Stated rather
than omitted**, because the criticism of the spec's §8 was precisely that it described the CI status
instead of naming the defect. The defect is: *a cannot-run is counted as a survivor, and one printer
does not gate on trustworthiness.*

## Checked and correct

- **Every `ev_muts.append` carries `measured`, and there are exactly two.** Enumerated with `ast`:
  `:760` `measured=False` (cannot-run), `:801` `measured=True` (normal). No third site, so
  `.get("measured") is True` has nothing to silently distrust today — and if a third is added
  tomorrow it fails **closed**, which is the point of `.get(...) is True` over `.get(..., True)`.
- **The stubbed cases are NOT vacuous — falsified deliberately.** Changing the stub from
  `len(_calls) == 2` to `== 1` (landing on the before-control instead of the mutation) makes **both**
  new cases go red with legible messages:
  ```
  [FAIL] a TIMED-OUT mutation is counted but is NOT a verdict: got (False, False) want (True, False)
  [FAIL] ...and it is reported as a cannot-run, not as a catch: got False want True
  160/162 passed
  ```
  So the fragility I was worried about (a fixture gaining a file and shifting the call index) **fails
  loudly rather than silently passing**. That is the property that matters; the index itself is not.
- **Counts.** docstring `162`, `EXPECTED_MUTATIONS["scripts/check-plan-code.py"]` `23`, sum `164`;
  `--self-test` **162/162**; `--mutate .` **164 mutations, 0 survivors, exit 0**.
- **The new mutation is caught via its named case** — 0 survivors with no expect-mismatch report
  means `run_mutations` verified the named case actually reddened.

## Not checked

- **`check()` / `--compare` end-to-end with a timeout.** I reasoned about `:2188` from the code and
  did not construct the run. L1's *mechanism* is measured (`:762`, `:2188`, the git provenance); its
  *end-to-end consequence on that path* is *not*. Labelled, not assumed.

## Verdict

**No Blocking, no High.** One Low, pre-existing, out of the CI path, stated rather than filed.

⚠ **This is the same verdict shape I gave last round and it was wrong then.** The difference I can
point to: round 1's failure was a *characterisation* ("both append sites record a real verdict")
asserted without reading the branch. This round's claims are enumerations and executions, each with
its command. That is a reason to weight them higher — **not** a reason to treat this as convergence
before the Codex half lands.

---

# CORRECTION — the severity was wrong, and the reason is that I did not run it

**Codex rated this Blocking. I rated it Low. Codex was right, and the gap is exactly the thing I
labelled NOT CHECKED.**

My §*Not checked* says: *"`check()` / `--compare` end-to-end with a timeout — I reasoned about
`:2188` from the code and did not construct the run."* Codex constructed it:

```
main([plan])               FAILED — plan's copy only, NOT compared: 1 file(s), 1 mutation(s), 1 survivor(s)
main([plan, "--evidence"]) mutations declared and run: 1, caught 0
                             SURVIVED timeout mutation
```

**The evidence block names a timeout `SURVIVED`.** I could not see that from reading `:2188`, because
it is a different function (`evidence()`), and my Low was priced on a count being off by one rather
than on a false claim that a guard was exercised and lost. **Severity that rests on unrun code is a
guess wearing a number.**

## Fixed — one contract, two producers

`check()` now carries the same default-deny `trustworthy`; `evidence()` renders `NOT RUN` for an
unmeasured entry; the plan-mode printer gates identically, with `declared is None` as the escape for
assemble/compare-only runs that legitimately have a zero tally.

⚠ **And the duplication that fix introduced was caught by the harness itself.** Copying the predicate
into `check()` made the mutation anchor match **twice**, and `--mutate .` went red:
`anchor matches 2 times … only the FIRST is replaced … Tighten it`. **164 of 165.** The right fix was
not a tighter anchor but removing the duplicate: `verdicts_are_trustworthy(m_muts, declared)`, one
function with two callers — which is what `check-vocabulary-collisions.py` exists to enforce.

**Verified after the extraction:** `--self-test` **164/164**; `--mutate .` **165 mutations, 0
survivors, exit 0**; both of Codex's observations reversed —
`NOT MEASURED — plan's copy only, NOT compared: …` and `NOT RUN  timeout mutation`.

## Verdict, corrected

**NOT CONVERGED — 1 Blocking (Codex), folded.** Round 3 of the code review is owed.
