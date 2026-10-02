# Round 3, coordinator — the two halves disagreed about thrashing, and the hand-measurement settles it

**This is not a third review.** It records (a) which half was right where they conflict, (b) the
thrashing determination, and (c) why the response is NOT another architecture review.

Subject: `explainer-emphasis-baseline` at `1c13190a`. Both halves reported START == END.

## The halves disagree, which is the signal

| half | thrashing determination | verdict |
|---|---|---|
| `docs/reviews/claude/emphasis-baseline-r3-claude.md` | **YES, recurred** | 0 Blocking · 2 High · 3 Medium · 3 Low |
| `docs/reviews/codex/emphasis-baseline-r3-codex.md` | **NO, did not recur** | 0 Blocking · 0 High · 0 Medium · 1 Low |

`dev-process.md`: *never treat a single CONVERGED as proof; prefer the reviewer that reports a
finding until you have traced the code yourself.* Traced.

**They measured different mutations, and that is the whole disagreement.**

- Codex mutated `self.send_response(code)` → `self.send_response(404, "200 OK")`. The suite went
  red, so it concluded the status is covered. ⚠ It went red in OLDER header-capture cases that
  stub `send_response` with a ONE-ARG lambda — a two-argument call raises TypeError there. That
  is an arity artefact, not an assertion about status.
- The Claude half named `self.send_response(code)` → `self.send_response(200)`, which is round 2's
  own severance M4.

**Hand-measured, control and mutant in the identical sandbox:**

| tree | result |
|---|---|
| control (unmutated) | `207/208` — one failure, `...and every declared source is a real file in the repo` |
| `send_response(code)` → `send_response(200)` | `207/208` — the SAME single failure |

The one failure is the known scripts-only-sandbox artefact, present on both sides. **The status
severance survives.** The Claude half is right.

## Thrashing: CONFIRMED, three consecutive rounds

| round | finding | caused by |
|---|---|---|
| 1 | Blocking — `do_GET` can drop the injection, suite green | the original change |
| 2 | High — the `_send` stub cannot see the body write, suite green at 206/206 | **round 1's fix** |
| 3 | High — the status severance survives; four other `_send` stubs untouched | **round 2's fix** |

`dev-process.md`'s arming condition — two consecutive rounds whose findings came from the previous
round's fix, in one component — was met at round 2 and is now exceeded.

⭐ **And in rounds 2 and 3 the failure was READING, not discovery.** Round 1 handed over the
stronger `BytesIO` driver and said the stub *"structurally cannot"* make the check; I built the
stub. Round 2 printed a FOUR-row severance table; its proposed fix listed three; I folded three
and wrote *"Falsified across all three severances"* above a four-row table. Neither instance
required finding anything new. Both required reading what was already written down.

## ⛔ The response is NOT another architecture review, and here is why

**Phase 6 already ran on this exact class, one day earlier**
(`docs/reviews/architecture-review-2026-10-01.md`). It produced **ADR-0014** and two
recommendations: **D1** (give `main` its world as a defaulted parameter) and **D2** (one bit per
guard: does the suite drive the real entry point over a constructed world?).

**D1 is being applied by hand and works.** It closed round 9's Blocking on
`check-ratchet-contract`, and it closed the `recent-backlog-fixes` HIGH 1 today.

**D2 was never built.** Nothing asks, mechanically, *does this suite observe what reaches the
wire?* — so each instance is found by a human reviewer, one at a time, after it ships.

⭐ **That review's own falsifier predicted today exactly:**

> fold r9's four findings per-instance without adding a `main`-driving case, and a twelfth
> instance appears in one of these three files within two rounds.

Three new instances appeared today, in code written AFTER the ADR. **The prediction held.** A
second architecture review would re-derive a conclusion that is already written down and already
correct. The gap is not analysis; it is that the recommended mechanism does not exist.

## Disposition — the loop STOPS here, and the fold is NOT applied

Round 3's findings are real and are recorded, **but folding them per-instance is what produced
instances 2 and 3.** The structural finding makes the point: this file has FIVE handler drivers;
four still stub `_send` (`:2226`, `:2478`, `:2488`, `:2733`) and the fold hardened one, hardcoding
`h.path = "/probe.html"` so it cannot be reused. That is ADR-0014's own origin story — a correct
repair that propagated to zero siblings — reproduced inside one file, in the commit citing the ADR.

Put to the human as a decision. The options are not "fold or don't": they are **build D2**,
**apply D1 uniformly inside this file**, or **close the branch and keep the evidence**.

## Corrections to the halves, recorded rather than silently fixed

1. **The Claude half calls High 1 a "live defect". It is not.** Shipped `/_rev` returns
   `HTTP/1.0 404 Not Found` — measured by driving it. The 404-reads-as-200 consequence occurs
   under the mutation, not on HEAD. It is a coverage hole, which is still serious and still real.
2. **It says three handler drivers stub `_send`. There are four** — `:2226`, `:2478`, `:2488`,
   `:2733`. The finding is understated, not overstated.
3. **Codex's thrash determination is wrong**, for the arity reason above. Its one Low — the
   status assertion's second disjunct is satisfied by `HTTP/1.0 404 200 OK` — is correct and
   independently reproduced.
