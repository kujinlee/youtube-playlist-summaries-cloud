---
name: a-retrospective-number-needs-provenance
description: "FIRES-WHEN: about to write a number from recall into a document, report or commit — ⭐⭐ A number written from recall is fiction, and THE CORRECTIONS FAIL TOO (0 for 5 on one branch). DERIVE don't store; cite the SYMBOL not the line; record the CONDITIONS a figure was taken under, because patching a denominator to match a changed world is the tell"
metadata:
  type: feedback
---

> Merged 2 memories, bodies kept VERBATIM. Former names (still referenced by other memories): `never-write-a-cost-table-from-memory`, `a-measurement-needs-its-context-not-just-its-value`

## never write a cost table from memory

**What happened.** After seven dual review rounds on backlog #36, I opened PR #102 proposing a
process fix, justified by a table of five premises and what each had cost. I wrote that table **from
memory, at the end of a very long session.** Three independent checks — Codex, a Claude reviewer, and
a dedicated enumeration agent that read all 14 review documents — found:

| My claim | The record |
|---|---|
| 267-char premise: "~2 rounds, eliminated 3 alternatives" | caught round 1; the reviewer said explicitly it did **not** invalidate the design |
| `list()` inversion: "~1 round" | **zero** Blocking/High findings — one Medium, one Low |
| readdir premise: "wrong fix to a Blocking" | **no review mentions it**; the `readdir` fact appears only as reviewer-supplied supporting evidence |
| ASCII premise: "rounds 3–7 entirely" | first appeared round **2**; rounds 5–7 name their own causes |
| branded type: cost "the whole scope decision" | it was a **reviewer's** suggestion, refuted in the first round it existed |

And the thesis itself: **zero of the 14 reviews mention `review-method.md`, premise tags, or
VERIFIED/ASSUMPTION.** I verified that one by hand. Premise defects were **5 of 34** Blocking+High
findings — 14.7%. I had presented them as the account of all seven rounds.

**Why:** recall reconstructs a *story*, and a story wants a single cause with escalating stakes. The
record is messier and mostly disagrees. The reviews name their own dominant causes — four vacuous
falsifiers (each version's test written against the version being replaced), three cases of a round's
fix creating the next round's defect, targeted edits leaving stale restatements — none of which is
what I remembered.

**How to apply:** any retrospective claim with a number in it — costs, counts, "this took N rounds",
"X caused Y" — gets **enumerated from the artifacts before it is written**, not after. Grep the
reviews, count the findings, quote the verdict lines. If enumerating is too expensive for the moment,
write the claim without the numbers rather than with remembered ones.

⚠ **The rule was already written down and I had just read it.** `docs/portable-practices.md`'s
admission criteria say: *"Write entries by ENUMERATING, not by recalling… A summary written at the
end of a long session is the highest-risk artifact in the repo."* I read that paragraph minutes
before violating it, **in an entry I was adding to that same file.**

That matters beyond the embarrassment: it is evidence against the "wrong read-trigger" theory I was
proposing in the same PR. The rule was in the right document, open, at the right moment, and it still
did not fire. Prose rules do not fire on someone who is confident and tired, wherever they live.

---

## ⭐⭐ 2026-09-12 — THE CORRECTIONS FAIL TOO. **0 for 5** on one branch (`goal-page-mutations`)

The rule above says enumerate instead of recalling. What it did not say is that **a correction
written the same way fails the same way**, and that this repeats until you change the *mechanism*
rather than the *number*. Measured over four dual review rounds, every version wrong in a new way:

| v | claim | how it was wrong |
|---|---|---|
| 1 | "the THIRD file to pay this trap" | not third by any measure |
| 2 | "the NINTH, third with this shape" | named a file that never had the printer (`check-gate-falsifiability.py` printed `FAIL`); dropped `check-handoff-path.py`, named in the subject line of a commit v2 itself cites |
| 3 | "both sites now carry the derivation" | there were **four** sites; the 4th (the PR body) was left as the verbatim uncorrected text |
| 4 | "the shape ADR-0006 actually had" | ADR-0006 **never** had a `⟳` in front matter — both are in its BODY, and the branch's own docstring says so four lines away. It is the INVERSE case |
| 5 | "`error = True` occurs exactly once" | true of the CODE, false of `grep -c` (returns 2) — **the comment quotes the token it counts** |

Every one was written from a reviewer's table or from recollection, never from `git`. v1–v4 were each
found by a *different* review round; v5 I caught by verifying my own fix instead of asserting it.

⛔ **THE FIX IS NOT A BETTER NUMBER — IT IS REMOVING THE STORED CLAIM.** Three mechanisms worked
where four re-countings had failed:

- **DERIVE, don't store.** Replace the figure with the command:
  `git log -S'<token>' --reverse --format='%h %as %s' -- <file>`. The corpus moves; a stored count
  is stale at the commit that adds it ([[a-document-inside-the-corpus-it-measures]]).
- **CITE THE SYMBOL, NOT THE LINE.** `check-plan-code.py:1395` was accurate when written and went
  stale **two commits later inside the same branch**, because that branch's own edits moved the
  function. A line number binds by position; the symbol survives the edit — the citation-layer
  version of [[a-mutation-loses-its-binding]].
- **NAME YOUR OWN MEASUREMENT DISCREPANCY.** If the comment quotes the token it counts, say so
  inline. Otherwise the claim is true and the obvious check refutes it — the unfalsifiable shape
  `check-plan-code.py` already records for `"[FAIL] " in source`.

⚠ **Split the verdict by SUBJECT before concluding anything from a round count.** On that branch the
CODE converged at round 2 and two reviewers × two further rounds found **zero** code defects, while
the RECORD failed all four. Reading the four-round Phase-6 trigger off the count would have convened
an architecture review for a prose problem. [[gates-detect-defects-not-design]].

Sibling of [[check-the-assumption-not-just-the-code]] — that one is about premises for a design
*going forward*; this one is about claims describing what *already happened*, where the artifacts
exist and checking is cheap. See also [[quote-the-code-dont-characterise-it]],
[[a-guards-evidence-path-is-a-namespace-with-no-allocator]] (the overwritten review that produced
the fabricated attribution v2 inherited), and [[after-fixing-search-for-the-class]] (v3 was
instance-not-class, committed while fixing an instance-not-class defect).

## a measurement needs its context not just its value

On PR #310, three recorded measurements were wrong, and the corrections were wrong too. One habit
explains all of it: **a number was written down without the conditions it was taken under.**

**① The whole mutation table was uniformly ONE LOW.** Raw runs were taken at 149 cases; a floor case
was then added (149 → 150) and I updated the table's **denominators by hand without re-running it**,
leaving the numerators. Adding an always-passing case increments **both**. No verdict changed — every
row was still killed — but the evidence for an architecture review was fiction in the last digit.

**② A CORRECTION I wrote was also wrong**, and it was a correction *about wrong measurements*. It
said "re-measured cleanly: 133 → 131". Measured properly, with the context named:

| where the suite runs | control | mutant |
|---|---|---|
| in-tree | 133/133 | 132/133 |
| out-of-tree (a copy beside its imports) | 132/133 | 131/133 |

"133 → 131" occurs in **neither** — it took the in-tree control and the out-of-tree mutant. ⭐ **An
out-of-tree run carries one pre-existing red** (a case asserting a declared source is a real file in
the repo), so numbers from the two contexts are not comparable.

**③ A reviewer then filed the OTHER corrected sentence as also wrong, and that was REFUTED** — it
named its context (out-of-tree) while the reviewer measured in-tree. Both right. **Same defect from
the other side:** only a number carrying its context can be checked at all.

**Why:** this is [[a-retrospective-number-needs-provenance]] broken in the most literal available way —
not misremembering, but *editing a stored measurement to match a changed world*. And
[[a-document-inside-the-corpus-it-measures]]: the suite size moved under the table.

**How to apply:**
- ⛔ **If the world changed, RE-RUN. Never patch a recorded number to match.** Updating a denominator
  by hand is the tell.
- **Record the CONDITIONS with every figure** — in-tree vs out-of-tree, which commit, which `$HOME`.
  A bare `131/133` is unverifiable and, worse, looks verifiable.
- Prefer the **delta plus both endpoints** over a single number: `control 132/133 → mutant 131/133`
  survives a context mismatch; `133 → 131` does not.
- ⚠ **Assume corrections fail too** — two of three here did. Re-measure the correction.

See also [[a-measurement-is-only-as-good-as-its-corpus]],
[[measure-the-population-the-code-actually-sees]], [[quote-the-code-dont-characterise-it]].

