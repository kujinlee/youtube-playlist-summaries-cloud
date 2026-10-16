# Round 3 — `doc-citations-guard` (backlog #49) — coordinator

⚠ **Header reconstructed 2026-10-15 from the two filed halves; the round-4 call below was written
at the time it was made**, with the owner, after they chose the redesign over a fourth defect hunt.

```yaml
round: 3
fixes_nontrivial: true
subject: doc-citations-guard
halves:
  codex: ran
  claude: ran
findings:
  - {id: H1, severity: High, aim: instrument, fix_induced: true, component: suite, disposition: fixed}
  - {id: M1, severity: Medium, aim: deliverable, fix_induced: true, component: diff-extraction, disposition: fixed}
  - {id: CH1, severity: High, aim: deliverable, fix_induced: true, component: diff-extraction, disposition: fixed}
  - {id: CM1, severity: Medium, aim: deliverable, fix_induced: true, component: diff-extraction, disposition: fixed}
  - {id: CM2, severity: Medium, aim: instrument, fix_induced: true, component: suite, disposition: fixed}
  - {id: CM3, severity: Medium, aim: instrument, fix_induced: true, component: suite, disposition: fixed}
```

## Verdict: NOT CONVERGED — 2 High

**The redesign's claim held.** Both halves attacked the class that produced the previous three
fail-opens, and neither could make the guard judge a document under the wrong name. What they broke
was the *new* load-bearing mechanism.

## 6 of 6 findings were caused by round 2's own redesign

| id | Finding | Caused by |
|---|---|---|
| H1 | `-z` is the entire premise of the redesign and **nothing in the suite was watching it** — removing the flag silently disables the guard | the redesign |
| M1 | glob metacharacters in a scoped filename made the per-file pathspec over-match, so findings were misattributed and duplicated | the redesign's per-file diff |
| CH1 | added content beginning `++` was discarded as a header — `startswith("+++")` is not a header test | the redesign's marker parser |
| CM1 | per-file diffing turned a pure rename into newly added citations, contradicting the added-lines-only contract | the redesign's per-file pathspec |
| CM2 | `_nul_witness()` inherited Git configuration and crashed on an ordinary signing requirement | H1's own fix, same round |
| CM3 | the literal-pathspec fix had no regression witness | M1's own fix, same round |

---

# The round-4 call — THRASHING, and the redesign is owed again

`dev-process.md`: *"Reaching four rounds OBLIGES ASKING, and does not fire."* Asked and answered
2026-10-15; the owner chose to redesign the component. The evidence that framed the question:

⚠ **`check-review-decision.py` independently returns `ARCHITECTURE_REVIEW` on this branch** —
*"thrashing: 'diff-extraction' carried fix-induced findings in r2 and r3"* — once the three round
documents exist for it to read, which until 2026-10-15 they did not (it reported `rounds=0` while
six halves sat committed). Its verdict names the Phase 6 instrument. **The owner was offered that
explicitly and chose the narrower subject**: a design review of this one component, which is what
`review-method.md:171` prescribes for thrashing confined to one unit. The signal is not disputed —
the scope is. If the redesign below thrashes in turn, the wider review is the next step and this
paragraph is the reason it was deferred rather than missed.

**The arming condition is met, literally.** Rounds 2 and 3, consecutively, carried findings caused
by the previous round's own fix, in one component: **15 of 15**, 9 then 6, with `diff-extraction`
present in both (3 of 9, then 3 of 6) and the supporting `suite` findings existing only to witness
it. The per-finding evidence is the two tables above.

**Prose floor was not available as a reading.** That shape is defined as the limit of reviewing
*without an executable subject*; this subject executes, and the halves ran it.

**The test that decided what round 4 should be — *can a redesign remove it?*** (`review-method.md:200`)

| r3 finding | Redesign removes it? | Kind |
|---|---|---|
| CH1 `++` bypasses checking | **Yes** — nothing would read content out of diff text | mechanism |
| CM1 rename reports new citations | **Yes** — one diff invocation, no per-file pathspec | mechanism |
| M1 glob pathspec over-match | **Yes** — same | mechanism |
| CM2 `_nul_witness` git-config crash | **Yes** — the probe exists only to prove `-z` plumbing | mechanism |
| H1 `-z` has no witness | No — coverage of a mechanism that would be gone | branch-coverage |
| CM3 pathspec fix has no witness | No — same | branch-coverage |

Four of six are mechanism defects dissolved by **one** reshaping, and the two that are not are
witnesses for mechanisms the reshaping deletes.

**The reshaping, named before the code.** Stop reading content out of the diff. Take the changed
line *numbers* from the `@@` hunk headers, and read the lines themselves from the file. `violations()`
then receives a path, a set of added line numbers, and the document's own lines — no `+` marker, no
`---`, no `\ No newline at end of file`, one git invocation for the whole diff instead of one per
file plus a rename pathspec.

**⭐ And it collapses a DECLINED finding into the same guard.** r1 L2 (fenced code blocks, measured
at 40 of 896 living citations, 4.5%) was declined with the reason *"Fixing it means reading the file
rather than the diff, which is a different guard."* Reading the file is what this reshaping does, so
the fence exemption becomes available here rather than in a hypothetical successor. That is the
strongest evidence that the shape, not the patches, was the problem: the same change closes the
fail-open class *and* the stated false-positive class.

**The one new fail-open this creates, stated before it is built.** A malformed or unparsed `@@`
header would yield no added line numbers, which reads as *"nothing to check"* — the same failure
direction as the three header defects. It must be CANNOT RUN, and its falsifier is the first case
written, not the last.
