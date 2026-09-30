---
name: dual-review-what-it-catches
description: "FIRES-WHEN: considering skipping one half of the dual review — ⭐ The two review halves are NOT redundant — a Codex-only round cleared a money guard the skipped Claude half caught in one pass — and when they disagree the finding-reviewer has been right 3 of 3 times"
metadata:
  type: feedback
---

> Merged 2 memories, bodies kept VERBATIM. Former names (still referenced by other memories): `dual-review-halves-are-not-redundant`, `dual-review-disagreement-is-the-signal`

## dual review halves are not redundant

**Measured 2026-08-13 on the M3.1 money guard (PR #98).** Rounds 2, 3 and 4 were **Codex only** —
`docs/plugins.md` requires both halves and the Claude half was silently skipped. Severity decayed
round over round (2B/1H → 1B/1H → 0B/0H/1M → 0B/0H/0M/3L) and read exactly like convergence.

Then the Claude half ran once and found a **Blocking**: the pre-seeded magazine envelope could never
be accepted as fresh (`sourceSections: ['2. Encoder']` vs the parser's `['Encoder']`), so the suite's
only stated money protection was inert and every HTML render regenerated through Gemini.

**Why: the two halves fail in different directions.**

| | drifts toward | missed |
|---|---|---|
| Codex | comment precision *inside the changed lines*; runner/library internals | the fixture the guard exists to make unnecessary |
| Claude | the fixture, the callers, what the suite does NOT cover | (round 5) got one of its own Lows wrong and the fix implemented it faithfully |

So a decaying severity curve from ONE reviewer is not evidence of convergence — it is evidence that
one reviewer is running out of altitude. **Convergence requires a COMPLETE round** (both halves, no
new Blocking/High) — `docs/process-checklists.md:20`.

**Two corollaries measured in the same session:**

- **A reviewer can be wrong in the direction of MORE work, and that is not safe either.** Round 4's
  L4 said an ambient tight `guardrail_config` would make a render rung "go green having proved
  nothing". False — `at_capacity` returns 503 and the rung asserts 200 first. The fix implemented it
  faithfully and pinned the cap to 5000, permanently raising the local stack's money kill-switch
  tenfold and converting a *free red* into a *paid red*. The round-5 reviewer caught its own error.
- **The backlog is not a reviewer.** Backlog #43 already contained the correct diagnosis, in writing,
  the day before. Filing a good diagnosis is not acting on one.

See [[dual-review-what-it-catches]], [[gates-detect-defects-not-design]],
[[hardcode-only-what-fails-loudly]].

## dual review disagreement is the signal

When Codex and Claude disagree in a dual adversarial review, treat the disagreement as the most
valuable output of the round — not as noise to average away.

**Why:** across 7 whole-branch review rounds on `feat/stage3-cloud-sync` (see
[[stage3-cloud-sync-branch-state]]) the two reviewers split 3 times. The reviewer reporting a
*finding* was correct all 3 times — twice while the other returned **CONVERGED** on a live
Blocking/High. A majority vote, a "two clean-ish rounds" heuristic, or trusting the CONVERGED verdict
would each have shipped silent, unrecoverable user-data destruction.

The losing verdicts were never lazy — they were *plausible reasoning about the adjacent thing*:
- One cleared `companionTransfer` because it uses a precomputed `winnerMdHash` — true, but the bug
  was in the envelope read one line earlier.
- One downgraded a defect to Low by assuming `cHas === true`, when `mdHash` is derived from the blob
  BODY, so an unreadable blob made it false.

**How to apply:**
1. On any split, adjudicate by reading the code yourself and tracing the disputed value. Record the
   adjudication *in the review doc* — an uncorrected wrong verdict in `docs/reviews/` gets cited later.
2. Never accept CONVERGED as proof of clean; ask what the reviewer would have had to check to find
   the class of bug you most fear.
3. Reachability arguments are where reviewers most often err — they need knowledge of the deployed
   system's steady state, not just the code path.
4. Mutation-test every new guard (reintroduce the bug, confirm the test goes red). A fully green
   suite concealed one guard with ZERO coverage.
5. Fixes cause follow-on defects at a high rate (~half the rounds here). A fix's blast radius extends
   to every *reader* of the state it changes — point the next round explicitly at those consumers.


---

## ⟳ 2026-09-08 — 4th instance, and the FIRST where Codex said CONVERGED and was wrong

Backlog #91 round 4 (PR #269). Codex: **CONVERGED**, 0/0/0/1, with a correct measured enumeration of the parser's routes. Claude: **NOT CONVERGED**, 1 High — a census that printed `0 assembled` two lines above `1 blocks assembled` on the real CLI.

**Neither reviewer was sloppy, and that is the point.** Codex asked *"can the parser lose entries silently?"* and answered it correctly (no). The defect was in the **census**, which that question cannot reach. A CONVERGED verdict is only ever a statement about the questions that reviewer asked.

⚠ **Codex's half arrived FIRST and was clean.** Merging on it would have shipped the High. When one half is clean and the other is still running, the clean one is not a result — it is half a result. See [[dual-review-what-it-catches]].

---

## ⭐ WHAT REVIEW IS THE WRONG INSTRUMENT FOR — measured over six rounds, 2026-09-20

Six adversarial rounds on one warn-only guard (PR #325). Findings: 7 → 5 → 4 → 3 → 3 → 1;
Blockings 1,1,1,0,0,0. Every round found its defect inside the previous round's repair — six for
six, the pattern never broke.

**⛔ THAT PHRASE HIDES THREE DIFFERENT THINGS, and conflating them is how "thrashing" gets
misdiagnosed:**

1. **New mechanism, new edges** — a real regression. Each fix added machinery (7 mechanisms by the
   end), and every new rule is an untested claim about an unbounded space. ~8 instances.
2. **COUPLED FALSIFIERS — evidence damage, not behaviour damage.** Mutations anchor by TEXT; cases
   discriminate by CURRENT behaviour. So a fix mechanically degrades the apparatus proving it
   correct while the code is fine. ~7 instances: orphaned anchors, a mutation MASKED by a newly
   added sibling rule, a mutation DISARMED because a later fix rescued the mutated path.
3. **Revelation, not regression** — a fix turned 4 EXISTING cases red because their fixtures had
   only ever passed via the bug being fixed. The fix did not break them; it stopped hiding them.

**⭐ ALL THREE BLOCKINGS WERE ABOUT THE EVIDENCE, NEVER ABOUT THE GUARD MISBEHAVING** — an
unparseable failure-line format, duplicate mutation anchors, an unreproducible clean-copy run. And
Blockings STOPPED exactly when the apparatus became sound. The severity curve measures
**measurement quality improving first, then code quality**.

**⚠ THE CONFOUND, which I stated as a clean finding before noticing it:** every round after r1 was
explicitly told to look at the previous round's fixes. A reviewer told where to look finds things
there. 6/6 is weaker evidence than it sounds.

**THE INSTRUMENT MISMATCH — the part worth carrying to other work.** Review samples an unbounded
input space about ONE POINT PER ROUND: six rounds yielded ~7 lexical edge cases. One corpus run
over **5,287 unseen inputs** produced 456 fires and 2 discrepancies — **both of which were bugs in
the ground-truth rule, not the code**. One measurement covered more of the space than six rounds.
⛔ But review caught the thing no corpus could: a **safety property stated in a comment and never
tested** (r4 refuted "a veto can never introduce a miss"). Use review for CLAIMS and design; use a
corpus for SURFACES.

**⭐ A BETTER STOPPING RULE THAN A ROUND COUNT.** Stop when the reviewer's marginal information
reaches zero, visible as a progression: real defects → defects that cannot occur in real data
(a duplicate tool id) → defects the author already fixed before the reviewer reported. All three
appeared by r5-r6. That is observable per-round, unlike "four rounds obliges asking".

See [[a-measurement-is-only-as-good-as-its-corpus]] and
[[removing-a-signal-hollows-out-its-falsifier]] (cause 2 is that, mechanised).
