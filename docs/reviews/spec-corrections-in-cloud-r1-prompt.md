# Adversarial review — corrections-in-cloud design spec (round 1)

You are an adversarial reviewer. Find defects, not reasons to approve. **Read the actual files; do
not reason from this prompt's summary.**

## What to review

`docs/superpowers/specs/2026-08-22-corrections-in-cloud-design.md` — a Phase 1 design spec, approved
section by section in dialogue and now written down. It is about to become an implementation plan,
so hold it to "an engineer with no context could build this and a reviewer could reject it".

## Context you must verify rather than accept

The spec claims corrections are a **local-only feature end to end** today: one apply path
(`app/api/videos/[id]/regenerate/route.ts:63`), filesystem-only, zero occurrences of `corrections`
in `lib/job-queue/summary-handler.ts`, UI gated at `components/VideoRow.tsx:19`, nothing in
`components/cloud/`.

It further claims **two statements in `docs/backlog.md` #23 are wrong**:
1. *"Carry-forward is unaffordable by construction"* → measured ≈0.6¢/generation.
2. *"A reworded heading orphans paid digs"* → the dig blob is keyed on `startSec`; titles are
   identity in two fallbacks only.

**Verify both.** They are load-bearing: if either is right as filed, the spec's central decision
(keep `fixSummary`, reject `{from,to}` pairs) may be wrong.

Relevant code: `lib/gemini.ts` (`fixSummary`), `lib/gemini-cost.ts:33-35`, `lib/cloud-sync/backfill.ts`,
`lib/cloud-sync/reconcile-class-a.ts`, `lib/job-queue/summary-handler.ts`,
`lib/storage/supabase/supabase-blob-store.ts:116-134`, `lib/storage/resolve.ts`,
`components/CorrectionsPanel.tsx`, `supabase/migrations/0021_cloud_sync_signals.sql:115-153`.
Design context: the stable-blob-addressing spec §4.2.1, §5.2.2; ADR-0006; ADR-0007.

## Press hardest here

1. **§4, the applicability check.** It is the only thing standing between "skip" and silently not
   applying a user's correction. Attack the extraction rules: quote styles, arrow forms, a clause
   with an arrow but no quotes, nested/mismatched quotes, a term that is a substring of another
   word, a term appearing only in a code fence, an empty corrections string, whitespace-only.
   Is "skip only on proof" actually what the stated rule computes?
2. **§5.2 step 7 and its warning.** Self-review caught that a skip must not stamp `mdGeneratedAt`.
   **Is that the only field of that class?** Enumerate everything a skip touches or could touch and
   check each against "the body did not change". `summaryHtml`, `tldr`, `takeaways`, `processedAt`,
   `docVersion`, `annotationsEditedAt`.
3. **§6, no lease.** Is ≤0.6¢ per duplicate right? Can anything other than a human button press
   reach the route — client retry, SSE reconnect, automation? Does "metering through the ledger"
   have a concrete mechanism, or is it an aspiration the plan cannot implement?
4. **§8, the bounded dependency.** Is the boundary honestly drawn? Specifically: is the *attended*
   path really fully honest, given it also writes a card? And does the unattended path's correction
   waste money when `promote` will skip — i.e. do we pay to correct a body that gets discarded?
5. **§9, the falsifiers.** Do they assert at the consumer, or do any of them measure the mechanism?
   The two prior plan reviews in this repo both found fixes "certified complete by tests that
   measure the mechanism instead of the outcome". Would any listed test pass on a broken
   implementation?

## Also assess

- Internal consistency. Two contradictions were caught in self-review; assume more remain.
- Anything ambiguous enough to be built two different ways.
- Scope: is this one implementable slice, or does it need decomposition?
- **What the spec does not cover but should.**
- The measured table in §1: re-run at least three of the derivations and report any that differ.

## Output

Findings as **Blocking / High / Medium / Low**, each with file:line, the concrete failure scenario
(inputs → wrong outcome), and a suggested fix. Mark anything you could not run **NOT VERIFIED** —
an unrun check must never read as a pass. End with `CONVERGED` or `NOT CONVERGED`.
