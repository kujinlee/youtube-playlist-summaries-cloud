---
name: a-guard-can-mandate-the-duplication-it-audits
description: "FIRES-WHEN: a guard reports a drift between two copies of one rule and I am about to fix it by re-wording one copy — ⭐ ASK FIRST whether the guard REQUIRES the claim at both sites, because then DELETING the stale copy (the real fix) turns it RED, and re-wording is the only move the gate permits. Also fires when I am designing a guard whose rule is 'present at every declared site'"
metadata:
  node_type: memory
  type: project
---

**A guard that requires one rule to be present at several sites has made duplication MANDATORY.
It can then detect drift between the copies and simultaneously forbid the only fix that removes
it.** The fix for a drifted copy is to delete it and cite the source; that deletion is exactly what
such a guard refuses.

**MEASURED 2026-10-17, `marketplace-inventory` / backlog #297.**

⛔ **LOCATOR — CORRECTED 2026-10-19 BY r1 CODEX #8, AND THE FIRST FIX WAS THE SAME BUG AGAIN.** The script is **not on `master`** *(as of 2026-10-19; if PR #376 is squash-merged this sentence stops being true and a live copy exists — re-check before relying on it)*.
- **Immutable identity:** `d06da80c62da50973e55bec956bc0d8215266b94:scripts/check-claim-propagation.py`. A full SHA names one object forever.
- **Retrieval route, not an identity:** PR #376 — `git fetch origin refs/pull/376/head`, then read the SHA above.
- ⚠ **`refs/pull/376/head` is NOT a pin and citing it alone was wrong.** It FOLLOWS the PR head: measured 2026-10-19 it was `2e0ad1ef`, already moved past the `d06da80c` the finding below was measured on. A bare path, a branch name and a pull ref are all MOVING locators; only the SHA is not.
- ⚠ **Residual risk, stated rather than hidden:** GitHub's retention of pull refs is documented practice, not a guaranteed archive. If PR #376 is closed unmerged and the ref is reaped, the SHA still names the object but nothing may serve it.

`scripts/check-claim-propagation.py`'s `LIVE` registry registered `d5-ship-plus-argued` and
`d8-corrections-land-here` at `[SPEC, PAGE]`. Its rule: a token present at some declared sites and
absent at others is a problem (*"reached only some of its sites"*). So:

- three claims were drifted between the spec and the page, and the gate was **green over all three**
  — because each token was *present* at both sites, and presence is all it could see;
- deleting the stale sentence from the page — the remedy the architecture review then mandated —
  would have made `absent` non-empty and smaller than `auditable`, and turned the gate **RED**.

⭐ **THIS IS THE MECHANISM BEHIND FOUR ROUNDS OF THRASHING, and I could not see it from inside
them.** Every round re-worded a copy and created the next finding. Rewording was the only move the
gate allowed. Rounds 3 and 4 added **65 test cases** chasing `<em>`, a whitespace text node and a
`<br>` — all of them artefacts of matching a phrase across two prose copies that the guard was
insisting continue to exist.

## The question to ask

**Not** *"is this guard correct?"* — it was correct, on its own terms, every round. Ask:

> **What fix does this guard FORBID?** And is that fix the right one?

A guard whose rule is *present at every declared site* forbids deletion. A guard whose rule is
*refuse the second copy* forbids duplication. Those are opposite architectures for one concern, and
this repository had **already decided the second** (`check-canonical-source.py`, 2026-10-14) three
days before I finished building the first. See [[a-second-implementation-of-one-rule-drifts]] —
this is that defect applied to the guards themselves rather than to code.

## What it cost, and the generalisation

⚠ **The drift was not the damage; the inability to fix it was.** A green guard over a live defect
([[a-check-result-is-not-the-claim]]) is the familiar failure. This is worse and rarer: the guard
was **the reason the defect persisted**, and nothing in four rounds of adversarial review named it,
because every round was asking whether the latest wording was right.

⛔ **And note which direction it failed in.** It did not block the fix with an error a human would
read and question. It would have gone red *after* the correct edit, so the edit reads as the thing
that broke the build — [[a-sever-substitutes-todays-value]]'s shape, one level up: **the gate fails
toward making the correct action look wrong.**

The replacement bound is now written down: a citation-based guard proves *one place*, never *one
claim* — a citing site may restate and contradict and the audit returns empty. That is ADR-0015's
accepted price, and it is stated there rather than discovered later.
