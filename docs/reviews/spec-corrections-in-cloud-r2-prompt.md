# Adversarial review — corrections-in-cloud spec **v2** (round 2)

You are an adversarial reviewer. Find defects. **Read the actual files.**

## What to review

`docs/superpowers/specs/2026-08-22-corrections-in-cloud-design.md` — **v2**, rewritten after round 1
returned NOT CONVERGED from both halves (26 findings).

Round 1 is on disk and you should read it first:
`docs/reviews/spec-corrections-in-cloud-r1-codex.md`, `…-r1-claude.md`.

## The primary question

**Not "were the findings addressed" — "did addressing them break something new?"**

This repo's standing count of *"a fix that moved or reintroduced a defect"* is **seven, three of them
caused by a review's own fixes**. Weight your effort there. For each round-1 finding, state whether
v2 fixed it, partly fixed it, or introduced a new problem while fixing it.

## Attack these hardest

1. **§4's ordered decision procedure**, which replaced a rule that inverted on the empty case.
   Does rule 1 catch everything it must? Corrections that are only punctuation, only `;`, only an
   arrow, only quotes with nothing inside. Does the ordering itself create a new inversion?
2. **§4's apostrophe rule** — *"a single `'` not followed by a closing `'` on the same clause makes
   the clause irreducible"*. Consider a legitimate quoted term that **contains** an apostrophe:
   `'Clawcode's' → 'Claude Code's'`. Does the rule mis-extract, over-run, or produce a false skip?
   A false skip silently discards a user's correction — the worst outcome in this design.
3. **§6.1's cap on `fixSummary`.** It reaches the **local** path. Is the measured maximum
   (8,961 chars) a sound basis? What happens to a document above the cap —
   `assertNotTruncated` (`lib/gemini.ts`) is claimed to make it fail loudly; verify that. Is
   `thinkingBudget: 0` safe for this task, or does it degrade correction quality?
4. **§8's `exists(finalKey)` pre-check.** Is it TOCTOU? If the key is deleted between the check and
   `promote`, we skipped correcting but the generation publishes — an uncorrected body, unstamped.
   Is that safe or is it a new silent defect? And is `exists` even the right predicate for
   "will promote publish"?
5. **§5.1's deliberate behaviour change** — apply now uses *effective* corrections, so a bare pass
   re-applies stored corrections. Find the tests that encode the old behaviour. Is the change
   actually required by decision 3, or is it scope creep? Does it interact badly with the local
   `/regenerate` UX?
6. **§6.3's arithmetic requirement.** `summary_est_cents = 150` is documented as a worst case
   *derived from enforced caps* (`supabase/migrations/0011_cost_guardrails.sql:29`). Read
   `lib/gemini-cost.ts`'s bound functions and judge whether a capped correction can fit existing
   headroom, or whether the reservation must rise. The spec defers this to the plan — is that
   deferral legitimate or is it the spec dodging its own load-bearing question?

## Also assess

- Internal consistency. Two contradictions were caught in v1's self-review and more in round 1;
  assume some remain.
- §9's falsifiers: do any still measure the mechanism rather than the consumer?
- Anything ambiguous enough to be built two ways.
- **What v2 still does not cover.**
- Re-run at least three derivations in §1 and report differences. Note that the summary-sizes row
  cites a path **outside this repo** — the spec flags this as a follow-up; confirm it is unreproducible.

## Output

**Blocking / High / Medium / Low**, each with file:line, the concrete failure scenario, and a
suggested fix. Mark anything you could not run **NOT VERIFIED**. End with `CONVERGED` or
`NOT CONVERGED`.
