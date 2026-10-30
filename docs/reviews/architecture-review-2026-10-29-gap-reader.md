# Architecture review — the review-gap reader (backlog #182), armed by THRASHING on PR #439

**Armed by:** fix-induced findings in the gap-reader component in two consecutive rounds of `review-tooling-121-182`:
- round 2, X2: collecting every prose match promoted a quoted gap;
- round 3, M2, m5 and m6: the preamble rule's own edges.

Per `docs/dev-process.md`, that is the arming condition. The rounds' documents are under `docs/reviews/{codex,claude,coordinator}/review-tooling-121-182-r*`.

## What kept failing, and why

Backlog #182 asked the rounds gate to accept the YAML `halves.<x>: "GAP: <reason>"` form that `docs/round-header-template.md` recommends. Each attempt read gap declarations out of the round's documents, **including the review halves**:

| Round | Rule | Defeated by |
|---|---|---|
| 1 | any `GAP:` anywhere | a gap for the wrong half; nested block text; a comment as the reason; a later yaml fence |
| 2 | one exact spelling, two-space child of `halves:` | an example fence that is the document's first; a quoted prose gap promoted to a waiver |
| 3 | position: only before the first `## ` | 431 of 887 halves have no `## `, so the whole document is the preamble. Measured on this subject's own r2 Codex half: its quoted input reads as `codex: example only` |

**The cause is the corpus, not the rules.** A review half's job is to quote inputs, gap lines included, as evidence. So every rule over a half's text meets a half that quotes exactly what the rule accepts. This is the repository's recurring wall: a check that infers a property of arbitrary input that the input can defeat. It can't be fixed by a better rule, only by not reading that input.

## Decision

1. **SPLIT PR #439.** Backlog #121 (the wrapper records the tree it reviewed) does not depend on the reader and ships alone.
2. **Backlog #182's direction:** a gap is declared in ONE structured place written by the coordinator: the yaml header of the round's coordinator document. That is the first fence after the title of `docs/reviews/coordinator/<subject>-r<N>-coordinator.md`. Review halves are NEVER read for declarations. A round without a coordinator document keeps today's behaviour, the prose `REVIEW GAP:` line, unchanged. Moving every round onto the header is a separate, later decision.
   - **Falsifier:** a quoted gap inside any review half changes no round's verdict.
   - **Bound:** the coordinator's own header is trusted, so a coordinator can still declare a false gap. That is a statement, not an inference, and it is reviewed like any other line.
3. **Measured before building:** how many rounds have a coordinator document today, and how many of those already carry `halves:`. This is the step that sizes #182. It is not done in this review.

## What was decided this milestone and is not written down elsewhere

The one-reviewer-per-round alternation (backlog #339) means a coordinator document exists for every round 2+. So the structured place #182 needs is already produced for most rounds; it just isn't read.
