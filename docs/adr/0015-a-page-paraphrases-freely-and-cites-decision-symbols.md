---
status: accepted 2026-10-17 (architecture review `claim-propagation`, armed by THRASHING after four
  review rounds on `marketplace-inventory`; the owner chose candidate 1 of four, by selection card,
  and deferred the outstanding review round until the resulting tree settles).
  Records the decision the review named as this milestone's unwritten one — *that a reader-facing
  page may restate a spec's rules in its own words* — made deliberately, in one direction, for the
  first time. Supersedes `scripts/check-claim-propagation.py`'s copy-policing half.
  ⚠ ACCEPTED IS NOT IMPLEMENTED: one document pair is governed by it today. Widening the canon
  guard's population to `*.html` is backlog #282 and lands with this ADR; the corpus pass over the
  remaining 83 explainer pages is backlog #295 and is NOT done.
---

> **Anchor:** `harness-ships-elsewhere` — **ADR:** 0015
> **Goal:** The harness this project built can be installed and used by someone who has never seen this repository.

# ADR-0015 — A reader-facing page paraphrases freely, and cites the decision symbols it would otherwise reprint

## Context

The spec is [docs/superpowers/specs/2026-10-15-marketplace-inventory-design.md](../../docs/superpowers/specs/2026-10-15-marketplace-inventory-design.md); it is the **canon** this ADR creates, and the symbols named below are cited from it rather than restated.

A 1,136-line spec and the 1,045-line walkthrough page that explains it stated the same rules in
their own words, with nothing comparing them. Four adversarial review rounds tried to hold the two
prose copies in agreement with a hand-kept token registry (`scripts/check-claim-propagation.py`),
and **round 4 was THRASHING** by `review-method.md`'s definition — 8 of its 9 findings were
introduced by round 3's own fix. Rounds 3 and 4 together added **65 test cases** chasing `<em>`, a
whitespace text node and a `<br>`: shapes that exist only because a phrase must be matched across
two prose copies.

⛔ **The deciding finding was that the repository had already decided the opposite remedy, two days
earlier, and the guard was built anyway.** `scripts/check-canonical-source.py` — *"a mechanism
described in more than one place drifts. This refuses the second copy"* — landed 2026-10-14 for the
same defect class, this repository's most-measured one (`a second implementation of one rule
drifts`, 17 recorded instances). Backlog **#282/#288** already named this document pair as its
uncovered gap. The propagation guard required *every site to agree*; the canon guard *refuses the
second copy*. Those are opposite architectures for one concern.

**The question this ADR answers, which no document stated and nobody had ever decided:** how much
of a spec may a reader-facing page restate? Every round's findings followed from the unstated answer
*"all of it, in its own words"* — which is simply how the first page was written.

## Decision

**A page may paraphrase and explain without limit. It may not reprint the spec's DECISION SYMBOLS
without citing the canon.**

The line is drawn by **symbol, not by semantic category** — and that is taken from the existing
mechanism's own design rather than from taste. `check-canonical-source.py` deliberately holds
*stable strings* and not prose, because (its `CANONS` comment, measured at round 6 of
`plugins-handoff-citations`) *"the sub-claims are PARAPHRASED at every site … a case-sensitive,
markup-literal matcher returns 0 for a claim written at five sites. The SYMBOL and the BANNER are
stable strings, so they are what a token oracle can actually hold, and holding them forces the
paraphrases to one file."*

Three consequences of drawing it there:

1. **The review's honest objection is fully answered.** A walkthrough exists *to* paraphrase a
   1,136-line spec for a reader; had the line been drawn at "explanation", the page would have
   stopped being readable. Paraphrase stays free. What the page loses is reprinted decision
   symbols, and it gains a citation in their place.
2. **The page becomes a CITING SITE, not an exemption** — a category that already exists and
   already has a precedent of the same shape. `docs/process-rationale.md` is a retrospective that
   must *discuss* a mechanism without handing the reader the mechanism again. So the question
   *"is a walkthrough a record, or does it state rules?"* — which the review posed, and whose two
   answers were the reason the choice was the owner's — **does not have to be answered at all.**
   The guard's `EXEMPT` principle (*"a record, not a rule a reader follows"*, covering
   `docs/reviews/**` and `docs/dashboard-entries.md`) is for files exempted wholesale, and the
   walkthrough is not one of those.
3. **The tokens cannot be the bare symbols.** MEASURED on the widened population: `D1` occurs in
   **121** files, `C1` in 94, `SHIP` in 105, and the explainer CSS carries `#c5c1b9` **232** times
   and `#c4ab72` 120 times — a substring oracle over two-character symbols fires on hex colours.
   The tokens are therefore distinctive multi-word forms (`DON'T-SHIP`, `harvest: practice`,
   `SHIP /`, `BEST-EFFORT, VERSIONED`, `harvest: none`, `C4 is STRUCK`), each measured to occur in
   the spec and in **0 NON-CITING files** — which is what the guard establishes, and is not the
   same claim as *0 files*.

   ⟳ ⛔ **THIS SENTENCE SAID "0 files outside the governed pair" AND THAT WAS FALSE AT THIS ADR'S
   OWN COMMIT (r5 CLAUDE M3).** Measured: each token occurs in 2–5 further files — `CONTEXT.md`
   (which cites), `scripts/check-canonical-source.py` (the registry that *declares* the tokens),
   this ADR itself, and `docs/reviews/**` (exempt, but files nonetheless). ⭐ **The mechanism was
   never wrong** — the guard is green because every one of those sites cites the canon, which is the
   design working exactly as described below. The defect was the sentence: `0` was an inference
   stated as a measurement, in the decision of record, which is this repository's
   `an-inference-stated-as-measured` shape. ⚠ **And it tripped one of this ADR's own four
   falsifiers** (*"the token set stops being distinctive … the measurement in Decision (3) must be
   re-run rather than assumed"*), which is the falsifier doing its job one commit after landing.

## Rejected alternatives

**Candidate 3 — keep the page restating, and only harden the figures** (name a producer instead of
carrying a count). Rejected as the *primary* remedy, and partial by construction: §3's nine-file
total has **no** producer, and inventing one duplicates an enumeration that lives in prose, which
is the defect under review. ⭐ **Its precedent is adopted anyway, not discarded** — `CONTEXT.md:119`
had its guard count *removed rather than corrected* on 2026-09-21 (*"this file is inside the corpus
it describes, so any figure here is stale at the commit that writes it"*), and that rule continues
to govern derived figures. This ADR keeps `check-claim-propagation.py`'s `DERIVED` half, which has
caught the spec's own line count three times and has no equivalent anywhere else.

**Candidate 4 — fix the fragment → composed-page seam** (62 composed pages, 21 with a fragment
sibling, guard over one pair). Not rejected on merit — it is a **different concern**, it remains
filed, and it leaves the restatement question exactly where it was.

**Requiring every site to agree** — the propagation guard's own architecture. Rejected because it
was measured failing at the moment of decision: **three claims were drifted between the spec and
the page while that guard was green over all three** (backlog #297). A check that is green over the
drift it exists to catch is worse than none, because it creates a belief that something is covered.

## Consequences

⛔ **THE MARKER DOES NOT ENFORCE AGREEMENT, AND BELIEVING IT DOES WOULD REBUILD #297 IN A NEW
GUARD.** `check-canonical-source.py:322` is `if hit and not _cites(...)`: **a citing site may
restate the mechanism AND CONTRADICT it, and the guard returns `[]`.** Measured in its own history —
round 6's correction reached the canon and three reader-facing sites kept the superseded recital for
a full round while `audit()` returned `[]` (backlog **#289**). Measured again here: the walkthrough
fragment **already cites the spec path twice**, so a `CANONS` entry added with no other change would
be **green on day one over a page carrying all 17 decision symbols and three known-drifted claims.**

> **So the enforcement this ADR buys is prospective only: a NEW site that reprints a decision symbol
> without citing is refused. The remedy for a site that already restates is to DELETE the recital
> and keep the citation.** A citation cannot drift; a recital can.

What is given up, stated plainly rather than discovered later: a *machine* check over the existing
pair is traded for a *human* discipline. #297 is the evidence that the machine check was not working
— it was green over all three live drifts — so what is actually lost is the **appearance** of
enforcement plus 65 cases of maintenance, and what is gained is locality (the rule has one home) and
a suite that stops growing one case per discovered prose spelling.

**Prerequisite, and it is load-bearing:** the canon guard could not see the page at all. MEASURED by
importing `_walked_textfiles`: population **1,937** files, of which **0** are HTML; the spec is in
it, the walkthrough is not. `SEARCHED` is `("*.md", "*.py", "*.sh")`. Widening it to `*.html` is
backlog #282's subject and lands with this ADR. Measured safe: **0** HTML files in the population
carry either existing canon's tokens (verified against a known positive, which found 10+ `.md`
sites, so the zero is a true negative and not a broken search).

## Falsifier

This ADR is wrong, and should be reopened, if any of these is observed:

- **A reader cannot follow the walkthrough without opening the spec.** The decision claims
  paraphrase is sufficient for explanation and only symbols need citing. If the page's rule
  passages become unreadable once the recitals are citations, the line is drawn in the wrong place.
- **A decision symbol drifts again between the two files while the canon guard is green.** That is
  #297 reproduced under the new mechanism, and would mean the prospective-only bound above is not
  an acceptable price.
- **The token set stops being distinctive** — any token here reaching a file outside the governed
  pair means the oracle has become a false-positive generator, and the measurement in *Decision* (3)
  must be re-run rather than assumed.
- **A `*.html` page outside this pair is refused for carrying a decision symbol it legitimately
  needs.** The widening was measured safe over today's 84 explainer pages; it is not proven safe
  over pages not yet written.
