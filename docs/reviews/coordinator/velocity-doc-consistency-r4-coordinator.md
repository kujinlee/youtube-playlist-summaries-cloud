# Round 4 — `velocity-doc-consistency` — coordinator

```yaml
round: 4
fixes_nontrivial: true
subject: velocity-doc-consistency
halves:
  codex: ran
  claude: "GAP: alternation — Claude took r3, so r4 is the Codex half"
findings:
  - {id: H1, severity: High, aim: deliverable, fix_induced: true, component: exhaustiveness-claim, disposition: fixed}
```

REVIEW GAP: claude — alternation, per `review-method.md` -> Round topology step 4: Claude took r3, so r4 is the Codex half. Not a failure to run.

## ⛔ SCOPE was deliberately narrowed, by the user, and the reason is recorded

**This round reviewed `docs/development-velocity.md` ONLY.** The coordinator documents, review halves
and dashboard entries were explicitly out of scope.

**Why:** r3's High was in the *coordinator documents*, not in the document being fixed. **Reviewing
the review has no fixed point** — the artifact describing round N is always written after round N
ends, so it is always newer than the round that would check it. The user chose to cut that loop and
keep the protection where it matters. ⚠ **The cost is stated rather than hidden:** errors in the
coordinator documents are the project's memory of what happened, and a wrong round number there
misleads a future reader — which is this branch's own subject. They are not covered by any round.

## H1 — a repair that announced it was a narrowing and was a rewording

`:25` claimed *"Every number below was measured in that session"*. r3 (Low) caught it; **the r3
repair changed "every number" to "the numbers"** and presented that as *"what is true is narrower"*.

⛔ **It is not narrower. It is the same claim in softer words** — still a statement about everything
below it — and everything below now includes `⟳` notes carrying commit SHAs from days after the
source session. Codex named it precisely: *"the one repair that did not actually narrow enough."*

**Fixed by withdrawing the claim rather than softening it again** — the same move this branch made
for the sweep, for the same reason: nothing supports it. Each number now carries its own provenance,
and every `⟳` note is dated to the round that produced it.

⭐ **The lesson is distinct from the four before it.** Those were *patterns narrower than their
claim*. This one is **a sentence that announces its own narrowing and does not deliver it** — the
announcement is what makes it dangerous, because a reader who sees *"what is true is narrower"* stops
checking whether it is.

## What r4 verified rather than accepted

- ⭐ **The recoverability rule's worked example holds.** It re-derived it rather than taking it:
  `:60-61` names exactly two measurable signals — *fixes do not terminate* and *each fix ADDS code* —
  so `:315`'s *"two of them"* **is** recoverable in one jump. The rule adopted in r3 survives its
  first independent test.
- §3 and §4 have one live status each; the extra row is historical, **not** a second assignment.
- `process-checklists.md` really does carry rules 1, 1b, 2, 3, 4 at `:428`, and the side-job
  cross-reference to the seam signals is true against the four-item list.
- **Against `origin/master`, the banner, §6, §9 and §10 changes are improvements.** Only the
  `numbers below` repair fell short.
