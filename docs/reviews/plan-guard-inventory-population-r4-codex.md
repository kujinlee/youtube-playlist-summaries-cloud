# Post-Plan Gate — round 4 — Codex half

**Subject:** `docs/superpowers/plans/2026-09-02-guard-inventory-population.md` **v4**.
**Scoped tightly to v4's five changes.** Branch `fix/guard-inventory-population`. **Backlog:** #72, #73.
**Date:** 2026-09-03.

**Provenance.** `scripts/codex-review.py --prompt-file` → `gpt-5.5`; 2,439-char final message.
`verdicts/plan-r4-codex.verdict.json`, `gate_ran=true`.

**VERDICT: NOT CONVERGED** — 2 Blocking, 2 Medium.

> ✅ **Re-confirmed executable, with the new arithmetic:** `OK — delivered scripts mutated: 8 file(s),
> **167** mutation(s), 0 survivor(s)`. The five-entry manifest and the `167` sum are right.
>
> ⚠ **All four findings are consequences of v4's OWN fixes — the seventh consecutive round.**

---

## Blocking 1 — T4 promises a `read_population` mutation that T7 does not contain

v4's T4 says the CANNOT-RUN branch gets *"a manifest entry mutating the reason to `None`"*. T7's
manifest has five entries and **none targets `read_population`**. The branch gains a reachable case
and no mutation, so `EXPECTED_MUTATIONS = 5` / sum `167` is correct only for the *incomplete*
manifest.

**Executed** — the case works and the mutation is absent:
```
[FAIL] read_population refuses an unparseable script: got False
       expected True
self-test: 34/35 passed        mutated_rc=1
```

⛔ **This is exactly the defect v4's T4 was written to fix, one level up.** Round 3 found the branch
had *no case, no mutation, no falsifier*; v4 supplied the case and the promise, and forgot the
mutation. **v5 adds a sixth entry; `EXPECTED_MUTATIONS` becomes 6 and the sum 168.**

## Blocking 2 — T8's own F8 check cannot pass, because T9 does the fix

v4 added `docs/backlog.md` to F8's derived grep (round 3's fix) — but the row bodies are rewritten in
**T9 Step 0**, which runs later. T8 is therefore instructed to run a check it must fail.

**Executed at T8's point in the sequence:**
```
docs/backlog.md:101:| 73 | 🟢 **`discover_ratchets` is dead production code...
```
Also: T8's modify list (`:753-757`) does not include `docs/backlog.md` while F8 (`:782`) does — the
list and the grep diverged again, in the fix that was meant to stop them diverging.

**v5:** move the row-body rewrite into **T8** (it is a prose-correction, which is what T8 is), leaving
T9 to close the rows. Then F8 runs after its own subject is fixed, and T8's list and F8's paths are
the same set by construction.

## Medium — T9's `undescribed: [88]` is stale after v4 added Step 2b

`:842` tells the implementer to add a `GROUPS` tuple; `:846` still reports the end state as
`undescribed: [88]`. True *before* Step 2b, false after.

**Executed:**
```
after Step2 before Step2b:  coverage_errors []   undescribed [88]
after Step2b (end state):   coverage_errors []   undescribed []
```

## Medium — the fifth mutation is overbroad

Its `before` string matches, but applying it turns **three** cases red (`empty reason`,
`whitespace-only reason`, `non-string value`), not one. The harness accepts it because the named
`expect` matches exactly one of them — but the mutation is not isolated to the discriminator it
claims to guard, so a later regression in either of the other two would be masked by this entry's
success.

**v5:** narrow to `isinstance(value.value, str)` → `isinstance(value.value, (str, bool))`, which flips
only the non-string case.

---

## Disposition

All four accepted; all re-verified. None disputes the executed 167/0. Folding into v5.

Claude half: [`plan-guard-inventory-population-r4-claude.md`](plan-guard-inventory-population-r4-claude.md).
