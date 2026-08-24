# Adversarial review — corrections-in-cloud spec **v3** (round 3)

You are an adversarial reviewer. Find defects. **Read the actual files.**

## What to review

`docs/superpowers/specs/2026-08-22-corrections-in-cloud-design.md` — **v3**.

Prior rounds are on disk; read them before starting:
`docs/reviews/spec-corrections-in-cloud-r1-{codex,claude}.md` (26 findings),
`…-r2-{codex,claude}.md` (33 findings). Both rounds, both halves: NOT CONVERGED.

## What changed, and the question that matters

v3's thesis is **deletion**. Two optional features were removed because between them they caused
over half of round 2's findings and four Blockings, all false-negative-shaped:

1. **Term extraction** — parsing the corrections prose to decide whether a Gemini call was needed.
2. **The `exists(finalKey)` publication pre-check** — avoiding spend on a body `promote` would discard.

**The primary question: did deleting them actually remove those findings, or leave the spec
incoherent?** Look specifically for:

- Dangling references to the deleted machinery — a falsifier, a data-flow step, a field enumeration
  or an outcome name that only made sense with the optimisations present.
- **New costs the deletion introduced.** Every unattended generation for a video with corrections now
  runs `fixSummary` unconditionally. Is that affordable under §6.2's arithmetic in the *aggregate*,
  not just per run? What about a playlist-wide doc-version bump?
- Whether §4's one-line rule is genuinely total. It claims no input class can produce a false
  negative — try to find one.

## Verify these independently

**§6.2's arithmetic is now stated in the spec rather than deferred, so it is reviewable:**
summary worst 115¢ at the live 1800s cap, `summary_est_cents` 150¢, slack 35¢, correction worst
17.4¢, and the fit holding while `max_duration_seconds ≤ 4,416s`. **Recompute all five** from
`lib/gemini-cost.ts` and `supabase/migrations/0011_cost_guardrails.sql:29,33`. Report any that differ.

**§9 claims the seven existing local tests pass unmodified** because v3 preserves attended
semantics. Find those tests (`tests/api/regenerate.test.ts`,
`tests/lib/cloud-sync/regenerate-stamp.test.ts`) and check whether that is true — v2 claimed two and
a reviewer found seven.

**§6.1 claims the cap must apply through `withCaps`** (`lib/gemini.ts:36`) rather than as loose
options, because `fixSummary` never used it. Verify.

**§3's new structural-validation requirement** — is it specified precisely enough to build, or is it
the same prose-rule problem the deleted extraction had, relocated?

## Also assess

- Round-2 findings **not** about the two optimisations: are they actually fixed? Produce an explicit
  fixed / partly / made-worse table.
- Internal consistency; citation accuracy (round 2 found several drifted by one line).
- Whether v3 is now a single implementable slice or still needs decomposition.
- **What v3 still does not cover.**

## Output

**Blocking / High / Medium / Low**, each with file:line, the concrete failure scenario, and a
suggested fix. Mark anything you could not run **NOT VERIFIED**. End with `CONVERGED` or
`NOT CONVERGED`.

⚠ If this round does not converge it is the **third** on this spec and the fifth today across two
artifacts, which fires `docs/dev-process.md`'s Phase 6 trigger. If you believe the right answer is
that the design needs a different shape rather than another revision, **say so explicitly** rather
than filing more findings against this one.
