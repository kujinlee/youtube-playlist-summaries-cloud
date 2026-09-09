# retire-plan-mode — code review round 2, Claude half

**Subject:** r1's OWN FIXES — `git diff 71f86f9a..6e5b2b78` (commits `92b2b362`, `fceecdfa`,
`6e5b2b78`). Round 1 reviewed `71f86f9a` only; every fix written in response to it was unreviewed.

**Verdict:** NOT CONVERGED — 2 findings from this half, both in r1's fixes. Codex's half is at
`docs/reviews/coordinator/retire-plan-mode-r2-codex.md` (`gate_ran: true`, gpt-5.5) and raised a
third, a High, which is fixed here too.

⭐ **THE PREMISE OF THIS ROUND WAS BORNE OUT.** This project's record says fixes are where the next
defects live — backlog #91's r2 findings were all "R1-induced"; the ask-choices slice recorded every
Blocking in the following round as a regression from the previous one's machinery. Three fix commits
produced three more findings.

---

## H1 (this half) — the corpus guard reported the WRONG CAUSE, and suppressed the right one

`rglob("*.md")` counts PATHS; `scanned` counted documents READ. Any file `audit` could not open —
bad encoding, permissions, even a directory named `*.md` — made the counts disagree, so
`coverage_shortfall` fired with **"the corpus was NARROWED"**. Worse, `main()` returned on it
*before* printing findings, so the accurate line naming the file was never shown.

MEASURED end to end on a two-file tree (`ok.md` + invalid UTF-8 `bad.md`):

    rc=2   stdout: (empty)   stderr: "read 1 of 2 … The corpus was NARROWED"

Fail-closed, but the recorded cause is false — the exact "plausible and wrong" shape `stage_tree`'s
own docstring in this repo refuses ("say which path was absent instead").

**Fix:** `Finding.unreadable` — a typed discriminator, not a substring match on my own message
(#91 spent four rounds turning that shape into a type). Findings now print BEFORE the shortfall is
evaluated. After: `rc=1`, names `bad.md`, makes no narrowing claim.

## H2 (this half) — the r2 fix ORPHANED THREE r1 mutation anchors

The sweep caught it: my fix rewrote the exact lines three mutations bound to. Same shape as the CI
red earlier on this branch — recurring *inside the fix for it*. All re-bound and re-verified.
⚠ It happened a SECOND time when the Codex-H1 fix rewrote the same region again. Anchors bind by
TEXT; improving code breaks them, and only running the sweep can tell you.

## Cx-H1 (Codex) — CONFIRMED AND FIXED: cardinality is not identity

`coverage_shortfall` compared COUNTS. Codex broke it in one measurement: intended `docs/` holding
`a.md` + `has-tag.md` (a LIVE tag) versus a different root holding `x.md` + `y.md` — `scanned == 2`,
`total == 2`, verdict `None`. A false green over a corpus that was never the intended one.

My guard asserted a PROXY for "the right documents were read". **Fix:** set difference —
`missing = want - seen`, `stray = seen - want` — reported by name. Re-run of Codex's exact
construction: **REFUSES**, naming `a.md` as never visited.

⚠ Two things fell out of fixing it, both recorded because they are the interesting part:
* My first mutation for this property **survived** — the guard's `seen <= want` clause caught the
  stray even with cardinality restored, so the mutation was defeated by a clause it never touched.
  A mutation that does not isolate its property is not a falsifier.
* The next attempt **crashed the suite** instead of reddening a case (`0 red case(s) … caught by
  something else: []`), exposing a real latent flaw: an unreachable fall-through that indexed an
  empty list. Restructured so each branch reports its own condition and `None` is the final
  fallback — better code, and the mutation now produces a clean red.

## Cx-M1 (Codex) — the same unreadable defect as H1 above. Independent convergence, one fix.

## Cx-L1 (Codex) — ACCEPTED: a recorded measurement went stale

The docstring quoted `896` docs / `220` unread; the tree is now 1,117 / 897 and grows every time
this branch adds a review document. The delta holds but the quoted run is not reproducible. Left
as a DATED measurement rather than "corrected" to today's number — this repo's rule is that a count
pinned to a past event must not be silently updated — with the date made explicit.

## Codex's non-findings, verified and worth keeping

It re-ran the H1 splitter probe (CRLF, no trailing newline, empty file, CR-before-fence) against
the real file-read path and found **no regression**. It confirmed the retargeted `check-plan-code`
mutation genuinely exercises the `evidence()` line, with the verdict row naming the killing case.
It reported CANNOT RUN on the full `--mutate .` rather than inferring it.
