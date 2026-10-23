<!-- claude-review: subagent, round 3 -->
# trigger3-lost-bet — round 3, Claude half (adversarial)

**Subject:** `4f09cf5d..583ad735` (the r2 fold), read against the whole change `753645a7..583ad735`.
**Verified against:** worktree HEAD `583ad735ef53438f8b214d451e4c11b60b6cde99`. I extracted it with `git archive` into a
scratch copy and ran everything there. Nothing in the worktree was written except this file.

**Summary: 1 Major, 0 Blocking, 3 Low.** The fold has the right structure. The corpus read is fast,
CANNOT RUN is honoured, the round-number comparisons are right, and all 128 mutations are caught.
The Major is the r2 Major again, through a different door. If one half of the final round says
NOT CONVERGED in the casing this repository actually uses, the regex cannot read that verdict. The
half is then *ignored* rather than counted against the acknowledgment, so the acknowledgment counts
on the other half's CONVERGED alone.

---

## M1 (Major): a final-round half that did NOT converge is ignored when its verdict line is mixed-case, so the acknowledgment counts

**Where:** `scripts/check-decision-scheme.py:984` and `:1028`.

```python
HALF_VERDICT_RE = re.compile(r"^\W*VERDICT\W*\s*(NOT CONVERGED|CONVERGED)\b", re.M)   # :984, case-sensitive
verdicts = [v for w, v in by_round[top] if w != "coordinator" and v is not None]      # :1028, None is DROPPED
```

There are two decisions here, and the defect needs both of them:
1. The regex is case-sensitive.
2. A half whose verdict reads as `None` is skipped. Per the docstring at `:1009`, such a half is
   "not evidence either way".

Together they mean "the regex could not read it" is treated as "this half says nothing". It does
not count as "this half has not shown CONVERGED".

**Constructed inputs (executed, `acknowledgment_rejection` over a temp corpus built by `review_rounds`).**
Codex half `VERDICT: CONVERGED`; the Claude half varies:

| Claude half's verdict text | parsed | result |
|---|---|---|
| `**Verdict: NOT CONVERGED**` | `None` | **COUNTS** |
| `## Verdict: **NOT CONVERGED**` | `None` | **COUNTS** |
| `VERDICT: **NOT** CONVERGED` | `None` | **COUNTS** |
| `VERDICT: NOT-CONVERGED` | `None` | **COUNTS** |
| `verdict: not converged` | `None` | **COUNTS** |
| `1 Blocking, not yet resolved.` (no verdict line) | `None` | **COUNTS** |
| `VERDICT: NOT CONVERGED` (the exact form) | `NOT CONVERGED` | rejected ✓ |

**End to end through `main()` (executed).** The test corpus had two halves for r3:
- Codex: `VERDICT: CONVERGED`.
- Claude: the **real** committed half `docs/reviews/claude/decision-route-escalation-r5-claude.md`,
  whose verdict is `## Verdict\n\n**NOT CONVERGED.**`.

The log was a valid pair: an accrete bet with `outcome: continued`, then an acknowledgment with
`rounds_at_termination: 3` (`invalid_rows` → `[]`). Output:

```
rc 0
  WARN  trigger 10 MISSED ESCALATION ACKNOWLEDGED: 1 bet(s) the stream continued past were closed by a
        missed-escalation acknowledgment (s/u) — ...
```

Trigger 3 does not fail, so an acknowledgment counts while one half of the final round says NOT
CONVERGED. That is the case r2 filed.

**This is not an edge case. It is how the corpus is written (measured over `check-review-rounds.corpus`):**
- All halves: the regex reads a verdict in **127 of 740**. Of the 613 it reads as `None`, **181**
  have a line containing both "verdict" and "converged" when case is ignored. The usual forms are
  `**Verdict: NOT CONVERGED**`, `## Verdict: **NOT CONVERGED**` and `## Verdict\n\n**NOT CONVERGED.**`.
- Halves added since 2026-10-10: **28 of 83** read.

The Claude-half house style, `## Verdict` followed by a bold verdict on its own line, is invisible
to the regex. Today the defect is hidden only because Codex halves are usually the ones written in
the exact uppercase form.

**Fix, both parts:**
1. Make the parse case-insensitive and tolerant of emphasis between the two words, for example
   `re.compile(r"^\W*VERDICT\W*(NOT[\W_]*CONVERGED|CONVERGED)\b", re.M | re.I)`, then normalise the
   match. I ran this candidate over the corpus. It reads **351 of 740** halves, and **0** of them
   disagree with the current regex where both produce a reading. `\W*` already spans the newline
   after a `## Verdict` heading.
2. **Refuse rather than skip.** In the final round, a `codex`/`claude` half whose verdict is
   `None` should refute the acknowledgment ("r3's claude half carries no readable verdict, so its
   convergence is unshown"). That matches the stated philosophy of this function: "an
   acknowledgment needs evidence". It also matches the per-subject conservatism, which accepts a
   FAIL that waits over a WARN that hides.

The live acknowledgment survives part 2: `work-lines-always-on` r4 is `[codex CONVERGED, coordinator]`.

**Missing tests:**
- A case pairing one `CONVERGED` half with one `None` half. Today only the *all-None* case exists
  (`:2004`), so nothing pins the mixed case in either direction.
- Fixtures in the corpus's real forms (`**Verdict: NOT CONVERGED**`, and a heading with the verdict
  on the next line), varied by two distinct inputs per the fixture-variation rule.

---

## L1 (Low): a half that is ABSENT, as opposed to verdict-less, still lets the acknowledgment count

Input (executed): r3 holds only `codex/s-r3-codex.md` saying `VERDICT: CONVERGED`. Result:
**COUNTS**.

Round completeness (both halves, or a `REVIEW GAP:`) belongs to `check-review-rounds.py`, which
runs in CI. So in practice a missing half on a new round turns CI red elsewhere. Not reproducing
that check here is correct ("one rule, one place").

The docstring should say that this check relies on that one, though. Rounds listed in `KNOWN` are
exempt there, so there the only thing standing behind an acknowledgment is a single half.

UNVERIFIED: whether CI orders the two checks so that this one never reports first. That ordering
does not change correctness.

## L2 (Low): `half_verdict` reads a verdict quoted in a trailing code fence, and one with a qualifier

Executed:
- `VERDICT: NOT CONVERGED` followed later by a fenced block containing `VERDICT: CONVERGED` → `CONVERGED` → **COUNTS**.
- `VERDICT: CONVERGED only if H1 fixed — currently NOT` → `CONVERGED` → **COUNTS**.

A bullet that quotes the token mid-line (`- r4 must reach \`VERDICT: CONVERGED\``) is correctly
*not* read.

Fix: skip lines inside fences. Optionally require the verdict word to be followed by end of line,
`.`, `*` or `—`. This is low-frequency, because halves end with their own verdict by convention.

## L3 (Low): the half's writer comes from the FILENAME, not the directory, so the coordinator can file a "half"

Executed:
- `coordinator/s-r3-codex.md` saying `VERDICT: CONVERGED` → counted as a **codex** half → **COUNTS**.
- `codex/s-r3-claude.md` → counted as a claude half.

The docstring argues that the coordinator "cannot vouch" for an acknowledgment. In fact the only
thing separating the coordinator from a half is the file's suffix. The real corpus already has
`docs/reviews/coordinator/backlog-106-idempotence-r5-codex.md`.

This is inherited from `check-review-rounds.parse`, so it is not new, and it is not a fail-open
against an honest writer. Recording it because the docstring claims an authority the code does not
enforce. Fix: soften the claim, or require `path.parent.name == writer` for a verdict to be read.

---

## What I tried that HELD (executed)

| Probe | Result |
|---|---|
| Later round, coordinator-only (`s-r4-coordinator.md`) | rejected, "still being reviewed" ✓ |
| Later round in the alternate grammar (`s-codex-r4.md`) | rejected ✓ |
| Final round coordinator-only | rejected, "no review half carrying a VERDICT line" ✓ |
| Prefix subject: `s-backfill-r4-codex.md` NOT CONVERGED beside `s` r3 CONVERGED | `s` counts, `s-backfill` is a separate subject ✓ (greedy `.+` parses correctly) |
| Round gap r1, r3 (no r2); r3 both CONVERGED | counts. Correct: the highest round is the claim |
| Last verdict line wins over a quoted earlier one | ✓ |
| Corpus under an unrecognised directory (`archive/s-r4-codex.md`) | not seen, so counts. Same corpus definition `check-review-rounds` uses; not a new hole |
| **(b) Speed:** full CLI run on the real repo | **0.39 s** wall, rc=0; `--self-test` 273/273 in 0.83 s. Reading ~740 halves costs nothing measurable |
| **(b) Fail-open:** missing dir, `chmod 0` subtree, `chmod 0` half | all CANNOT RUN (self-test cases, run green; not running as root here, so each case is real rather than ambient) |
| **(c) Second implementation?** `grep -rn CONVERGED scripts/ .claude/hooks/` | No other script parses a half's `VERDICT:` line. `check-review-decision` reads a structured header, `codex-review.py` only has test strings, and the rest is prose. `half_verdict` is the sole owner ✓ |
| **(d) Mutations:** scoped run of `scripts/mutations/check-decision-scheme.json` through `check-plan-code.mutate_delivered` on the copy | **128/128 caught**, controls green, declared count matches |
| Live log on the real corpus | trigger 10 WARN for `work-lines-always-on` (r4: codex CONVERGED), which is correct |

The "two candidates rejected as equivalent" note (`w != "coordinator"`) is accurate today: a
coordinator entry's verdict is always `None`, so the `v is not None` clause does the excluding. Both
halves of that clause become live under M1's fix part 2, so the coordinator exclusion needs its own
case then.

VERDICT: NOT CONVERGED
