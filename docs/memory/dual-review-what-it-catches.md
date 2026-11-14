---
name: dual-review-what-it-catches
description: "FIRES-WHEN: considering skipping a review half, the two halves disagree, one half came back CONVERGED first, or deciding whether more review rounds will help — ⭐ The two halves are NOT redundant, the finding-reviewer has been right in every split (4 of 4), and review is the wrong instrument for an input SURFACE"
metadata:
  type: feedback
---

**CURRENT RULE:**
1. **The two halves are not redundant — they fail in different directions.** Codex drifts toward precision inside
   the changed lines and runner internals; Claude toward fixtures, callers, and what the suite does NOT cover.
   A decaying severity curve from ONE reviewer is that reviewer running out of altitude, not convergence. Round 1
   runs both halves; rounds 2+ alternate one half per round, sent to the half that did not author the fix, under
   the round cap (`docs/review-method.md` → *Round topology*, §0 Q4c).
2. **On a split, the half reporting a FINDING has been right every time (4 of 4).** Adjudicate by reading the code
   and tracing the disputed value yourself; record the adjudication in the review doc. Never resolve by majority or
   by trusting CONVERGED — a CONVERGED verdict only covers the questions that reviewer asked.
3. **A clean half that arrives first is half a result.** Do not merge on it while the other half is running.
4. **Use review for CLAIMS and design; use a corpus for SURFACES.** Review samples an unbounded input space about
   one point per round.
5. **Stop on marginal information, not a count:** real defects → defects that cannot occur in real data → defects
   the author already fixed before the report. When all three appear, the reviewer is done.

**How to apply:** ask what the CONVERGED reviewer would have had to check to find the class of bug you most fear.
Reachability arguments are where reviewers most often err. Mutation-test every new guard. Fixes cause follow-on
defects at a high rate — point the next round at every *reader* of the state the fix changed.

> Merged 2 memories. Former names (still referenced by other memories): `dual-review-halves-are-not-redundant`, `dual-review-disagreement-is-the-signal`

## History

**Halves not redundant — 2026-08-13, M3.1 money guard (PR #98).** Rounds 2–4 ran Codex only (the Claude half was
silently skipped); severity decayed 2B/1H → 1B/1H → 0B/0H/1M → 0B/0H/0M/3L, reading exactly like convergence. The
Claude half then found a **Blocking** in one pass: the pre-seeded magazine envelope could never be fresh
(`sourceSections: ['2. Encoder']` vs `['Encoder']`), so the suite's only money protection was inert. Corollaries the
same session: a reviewer can be wrong toward MORE work (r4's L4 was false — `at_capacity` returns 503 and the rung
asserts 200 first — and its faithful fix raised the local money kill-switch tenfold to 5000, a free red made paid);
and the backlog is not a reviewer (backlog #43 held the right diagnosis the day before). See
[[gates-detect-defects-not-design]], [[hardcode-only-what-fails-loudly]].

**Splits 1–3 — `feat/stage3-cloud-sync`, 7 whole-branch rounds** ([[stage3-cloud-sync-branch-state]]). The halves
split 3 times; the finding-reporter was right all 3, twice while the other said CONVERGED on a live Blocking/High
that would have shipped silent user-data destruction. The losing verdicts reasoned plausibly about the adjacent thing
(cleared `companionTransfer` via `winnerMdHash` while the bug was in the envelope read one line earlier; assumed
`cHas === true` when `mdHash` derives from the blob body). A green suite hid one guard with ZERO coverage; about half
the rounds' defects came from fixes.

**Split 4 — 2026-09-08, backlog #91 r4 (PR #269).** Codex CONVERGED 0/0/0/1 with a correct enumeration of the parser;
Claude NOT CONVERGED, 1 High — a census printing `0 assembled` two lines above `1 blocks assembled`. Codex's question
("can the parser lose entries?") could not reach the census. Codex's half arrived FIRST and clean.

**Review vs corpus — 2026-09-20, six rounds on one warn-only guard (PR #325).** Findings 7 → 5 → 4 → 3 → 3 → 1;
Blockings 1,1,1,0,0,0; every round found its defect inside the previous repair. Three distinct causes: new mechanism,
new edges (~8); COUPLED FALSIFIERS — text-anchored mutations degraded by fixes while the code was fine (~7); revelation
— a fix turned 4 existing cases red whose fixtures had only passed via the bug. **All three Blockings were about the
evidence, never the guard misbehaving.** Confound: each round after r1 was told to look at the previous fixes, so 6/6
is weaker than it sounds. One corpus run over **5,287 unseen inputs** gave 456 fires and 2 discrepancies, both bugs in
the ground-truth rule — more coverage than six rounds (~7 edge cases). But review caught what no corpus could: a
safety property stated in a comment and never tested (r4 refuted "a veto can never introduce a miss"). See
[[a-measurement-is-only-as-good-as-its-corpus]], [[a-test-that-cannot-fail]] (former `removing-a-signal-hollows-out-its-falsifier`).
