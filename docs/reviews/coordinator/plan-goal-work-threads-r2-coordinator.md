# Plan review — goal work threads — round 2 — coordinator adjudication

Adjudicates `docs/reviews/codex/plan-goal-work-threads-r2-codex.md`.
Subject: plan v2 + spec v4 at `c460f015`.

**REVIEW GAP: claude** — the Claude half was dispatched, ran, and **never filed**. It was prompted
twice, including once with an explicit "write what you have, even partial" and a summary of what was
already found so it could spend its budget on new ground. It returned nothing. This is the fourth
recorded instance in this repo of a fork doing work and going idle without reporting.

⚠ **What this costs, stated rather than glossed.** Round 1's three Blockings all came from the
Claude half, and it found them by **transcribing the plan's code into a runnable harness and
executing it** — Codex reasoned about the same code and got one of them backwards. The half that
executes is the one that catches contradictions between a plan's tests and its own implementation.
Round 2 therefore has a **weaker instrument than round 1**, and its CONVERGED/NOT-CONVERGED verdict
should be read accordingly. The coordinator's own pass (below) partially substitutes and is
structurally weaker than an independent reviewer, because it cannot surprise itself.

---

## Codex findings — all confirmed, all remediated

| id | sev | finding | disposition |
|---|---|---|---|
| — | **Blocking** | Spec §5's bullet still specified the retracted tri-state *shipped / in flight / not started* | **CONFIRMED, FIXED.** The v4 retraction edited §3.2a and the card mockup and left the bullet. An implementer reading the spec rather than the plan would have rebuilt the defect verbatim |
| — | High | `pr_fanout` counts **threads** while the rendered label says **documents** | **CONFIRMED, FIXED.** `thread_prs` dedupes a PR touching both a spec and its plan, so the count under-reported by one for every such PR. It now consumes `collect`'s per-document history cache, before any thread-level dedupe |
| — | High | `DOC_PATH` over-matches: unanchored `README` also matches `README-generator.ts` | **CONFIRMED, FIXED.** Each literal is now `$`-anchored. Verified 0 wrong over 14 adversarial paths; **latent**, no such path exists in repo history |
| — | Med | `head` is the only new git call with no `try`/`except` | **CONFIRMED, FIXED.** Its two siblings guard `OSError`/`SubprocessError`; this one would have aborted the whole page build |
| — | Med | Stale rendered strings (`[code]`, `⚠ no code PR yet`) in the §5 card sketch | **CONFIRMED, FIXED** — same root as the Blocking |
| — | Med | `eq("...", "implement" in _h.lower(), False)` is too literal — passes for *shipped*, *done*, *landed* | **CONFIRMED, FIXED.** Replaced with a case pinning the **set** of renderable tag texts, which fails on any label outside the three measured states |
| — | Low | `"on 1 documents"` does not catch `"on 1 document"` | **CONFIRMED, FIXED.** Now counts fan-out spans, which no wording evades |
| — | Low | `d["rel"]` raises `KeyError` on a doc record without one | **CONFIRMED, FIXED** — `.get` throughout, plus a case |

**Codex cleared two things the coordinator had queried**, and both hold on re-check: `pr_fanout`
being computed after `out.sort(...)` is not ordering-sensitive, and the case-count arithmetic was
correct as written.

## The coordinator's own pass — what it added

Run because the Claude half did not arrive. Recorded as coordinator work, not as a review half.

1. **`DOC_PATH` over-match — found independently before Codex reported it**, by running the regex
   against adversarial inputs rather than re-reading it. `README-generator.ts`, `CONTEXT.md.ts`,
   `CLAUDE.md.backup.ts`, `READMEs.tsx` all mis-tagged. ⚠ **This was round 1's own fix creating the
   inverse defect** — the repo's most-recorded review pattern, and it happened on the first fix
   written.
2. **The unguarded `head` call — found independently**, by comparing it to `last_touched`'s guard.
3. ⛔ **A tautology the coordinator wrote while fixing a weak case.** The replacement for the fan-out
   assertion was `eq(label, X, X)` — the unfalsifiable-case class this whole review exists to hunt.
   Caught on re-read and deleted. Recorded because writing the rule down did not prevent breaking it.
4. **The case-count chain was recounted from the file, not from arithmetic**, after the fixes changed
   it: **15 → 25 → 34 → 38 → 45 → 59 → 62**. Every declared count in the plan is updated, so
   `check-selftest-counts` stays green at each of the six commits rather than going red at the first.
5. **A retraction sweep by CLAIM, not by phrase.** One borderline survivor: spec `:176` read *"the PR
   is the atomic implementation unit"*. That is a statement about granularity, but the wording let a
   reader carry it back to the retracted claim. Reworded to *"the atomic unit of CHANGE"* with the
   scope said explicitly. ⚠ **The Blocking above and this both exist because the v4 retraction was
   swept for the words it had changed rather than for the claim** — the exact failure recorded in
   this project's memory one day earlier.

## Verdict

**NOT-CONVERGED.** Round 2 raised a Blocking and two Highs; `dev-process.md` requires a full round
adding no new Blocking or High. Round 3 is required, and its first job is the standard one for this
repo: **were round 2's fixes themselves defective?** Two of the four code fixes here changed
function signatures (`pr_fanout`) or regex semantics (`DOC_PATH`), which is where this project's
review rounds most often find the next Blocking.

⚠ **Round 3 must have a working Claude half.** Two rounds with only one executing reviewer is the
condition `docs/dev-process.md` names for escalating, and the memory note *"dual review halves are
not redundant"* records a money guard cleared by a Codex-only round that the skipped Claude half
caught in one pass.
