---
name: dual-review-is-the-process-not-a-request
description: "FIRES-WHEN: about to ask permission to run a review half — Never ask permission to run the dual adversarial review — it is the standing Phase 3 gate; only a reviewer that CANNOT run is a decision"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: ac37cc3e-cd09-4b22-8dc7-6cf746dd0b48
  modified: 2026-09-17T03:18:14.629Z
---

**Do not ask the user whether to run the second half of a review round.** Dual adversarial review
(Codex + Claude) is this project's documented Phase 3 gate and is explicitly **autonomous** —
`docs/dev-process.md`: *"plan (Phase 2) and implementation (Phase 3) proceed autonomously — dual
adversarial review to convergence is the quality gate, not a human sign-off."* Running it is the
default path, not a spend decision and not a fork.

**Why:** the user, verbatim (2026-09-16, PR #315 / backlog #137): *"why do you ask about dual
adversarial reviews? It has been the dev-process unless one of them cannot be run."* I had run the
Codex half, `check-review-rounds.py` went red for the missing Claude half, and I raised a selection
card asking permission to spawn the reviewer — twice. The card was pure friction: the answer was
already written in the process doc I had loaded.

**The mistake underneath it, which is the part to avoid repeating.** A generic session instruction
("do not use the Agent tool unless the user requested it") got read as overriding a standing
project process. It does not. The user established this workflow; a subagent reviewer IS the
requested thing, standing, until they say otherwise. Treating a general tool-use default as stronger
than an explicit project gate turns an autonomous phase back into an AFK-blocking one, which is the
exact cost [[process-conventions]] exists to prevent.

**How to apply.** Round owed → dispatch BOTH halves and report findings. The only branch worth
raising is a reviewer that genuinely **cannot** run (not installed, auth failure, usage limit,
HTTP error) — and even then `docs/plugins.md` says do not wait or ask: fall back to the other
reviewer immediately and note the gap in the review doc. ⛔ A `REVIEW GAP:` marker is for a reviewer
that could not run, never one that was not asked. See [[dual-review-what-it-catches]] for
why skipping a half is expensive, and [[running-codex]] — a timeout is
usually mine, so DOUBLE it before calling Codex unavailable.

Related: [[putting-a-choice-to-the-user]] — same root, a card offered where the answer was already
settled.
