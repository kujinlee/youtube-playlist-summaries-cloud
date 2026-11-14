---
name: a-retrospective-number-needs-provenance
description: "FIRES-WHEN: about to write a number from recall into a document, report, commit or correction — or to patch a recorded figure after the world changed. DERIVE don't store; cite the SYMBOL not the line; record the CONDITIONS; corrections fail too (0 for 5)"
metadata:
  type: feedback
---

> Merged 2 memories. Former names (still referenced by other memories): `never-write-a-cost-table-from-memory`, `a-measurement-needs-its-context-not-just-its-value`

**The rule: any number describing what already happened — costs, counts, "took N rounds", "X caused Y", a measurement — is ENUMERATED FROM THE ARTIFACTS before it is written, never recalled. A correction is held to the same rule, because corrections written the same way fail the same way.**

**How to apply:**
- **Enumerate first.** Grep the reviews, count the findings, quote the verdict lines. If that is too expensive now, write the claim WITHOUT the number.
- **DERIVE, don't store.** Prefer the command over the figure, e.g. `git log -S'<token>' --reverse --format='%h %as %s' -- <file>`. A stored count is stale at the commit that adds it ([[a-document-inside-the-corpus-it-measures]]).
- **CITE THE SYMBOL, NOT THE LINE.** `check-plan-code.py:1395` went stale two commits later inside the same branch.
- **Record the CONDITIONS with every figure** — in-tree vs out-of-tree, which commit, which `$HOME`. Prefer delta plus both endpoints (`control 132/133 → mutant 131/133`) over a bare `133 → 131`.
- ⛔ **If the world changed, RE-RUN. Never patch a recorded number to match** — hand-editing a denominator is the tell.
- **Name your own measurement discrepancy** inline (e.g. a comment that quotes the token it counts makes `grep -c` return one more).
- **Split a verdict by SUBJECT before reading a round count**: code may have converged while only the RECORD kept failing — that is not a Phase-6 trigger ([[gates-detect-defects-not-design]]).

**Why:** recall reconstructs a STORY — one cause, escalating stakes — and the record mostly disagrees. The rule was already in `docs/portable-practices.md` (*"Write entries by ENUMERATING, not by recalling… A summary written at the end of a long session is the highest-risk artifact in the repo"*) and I violated it minutes after reading it: prose rules do not fire on someone confident and tired.

## History (condensed)

- **PR #102 (backlog #36), cost table from memory.** Five premises and their "costs", written at the end of a long session after seven dual rounds. Codex, a Claude reviewer and an enumeration agent over all 14 review documents refuted every row (e.g. "rounds 3–7 entirely" — first appeared round **2**; the readdir premise — **no review mentions it**). Premise defects were **5 of 34** Blocking+High findings (14.7%), presented as the account of all seven rounds; **zero of the 14 reviews** mention `review-method.md`, premise tags or VERIFIED/ASSUMPTION.
- **2026-09-12, `goal-page-mutations`: corrections 0 for 5.** v1 "the THIRD file"; v2 "the NINTH" (named a file that never had the printer, dropped `check-handoff-path.py`); v3 "both sites" (there were **four**); v4 an ADR-0006 shape it never had; v5 "`error = True` occurs exactly once" (true of the code, `grep -c` returns 2). v1–v4 each found by a different round; v5 caught by verifying my own fix. Code had converged at round 2; the record failed all four.
- **PR #310, measurements without context.** A mutation table's denominators were hand-bumped 149 → 150 without re-running (both terms should move). A correction "133 → 131" mixed contexts: in-tree control 133/133 → mutant 132/133; out-of-tree 132/133 → 131/133 (out-of-tree carries one pre-existing red). A reviewer's counter-claim was REFUTED because the other sentence named its context. Two of three corrections were wrong.

Related: [[check-the-assumption-not-just-the-code]] (premises going forward; this is claims about the past), [[quote-the-code-dont-characterise-it]], [[a-mutation-loses-its-binding]] (line numbers bind by position), [[a-guards-evidence-path-is-a-namespace-with-no-allocator]], [[after-fixing-search-for-the-class]], [[a-measurement-is-only-as-good-as-its-corpus]], [[measure-the-population-the-code-actually-sees]].
