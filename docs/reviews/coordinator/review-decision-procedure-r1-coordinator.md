# review-decision-procedure — round 1, coordinator adjudication

```yaml
round: 1
subject: review-decision-procedure
halves:
  codex: ran
  claude: "GAP: this session spawns no subagents"
findings:
  - {id: B1, severity: Blocking, aim: deliverable, fix_induced: false, component: parse-header, disposition: fixed}
  - {id: B2, severity: Blocking, aim: deliverable, fix_induced: false, component: scope-for, disposition: fixed}
  - {id: M1, severity: Medium, aim: deliverable, fix_induced: false, component: review-method-card, disposition: fixed}
  - {id: M2, severity: Medium, aim: deliverable, fix_induced: false, component: review-method-card, disposition: fixed}
```

**REVIEW GAP: claude** — this session does not spawn subagents. Recorded, not hidden. A
Codex-only round has cleared a live defect on this repository before, so treat the verdict
as weaker than a dual one.

* Codex: `docs/reviews/codex/review-decision-procedure-r1-codex.md` (`gpt-5.5`) —
  **2 Blocking, 2 Medium. NOT CONVERGED.**
* Verdict: `docs/reviews/verdicts/review-decision-procedure-r1-codex.verdict.json`.

⭐ **The round was dispatched because the branch's own new tool said so**, from evidence
rather than recall — `ROUND_OWED — no round recorded; a one-round change needs at least
one`. It also derived the scope itself. That is the first decision on this branch that came
from the record instead of a judgement, and it was right.

## B1 — the parser dropped ordinary YAML, and a recorded High reached STOP

**ACCEPTED AND FIXED.** `parse_header` matched only `{...}` flow mappings, so an ordinary
block-style item —

```yaml
findings:
  - id: H1
    severity: High
```

— parsed to `findings: []`. An empty round is clean; two clean rounds are CONVERGED. **A
recorded High could therefore produce STOP.** Codex executed the case rather than reasoning
about it, and reported STOP for both one-round and full-loop histories.

⛔ **This is "cannot parse reads as a pass" INSIDE THE TOOL BUILT TO REFUSE IT.** The
docstring already says an empty round must never be returned; the parser did it anyway
through a shape nobody tested.

**Fixed in two parts, and the second matters more:** block-style items are now parsed, and
the parser **counts the list-item markers and refuses unless every one produced a finding**.
Best-effort parsing of a safety record is the defect; parity is the repair. A lone `- ` with
nothing under it now raises rather than shrinking the round.

## B2 — an allowlist of risky prefixes silently downgraded a money path

**ACCEPTED AND FIXED, AS A CLASS.** `RISK_PREFIXES` listed `supabase/`, some `lib/*` stems
and `middleware`. Codex verified against the repository that `app/api/pdf/[id]/route.ts`
documents itself as where *"money is charged"*, and that its sibling carries a *"D4 money
invariant"* — and `scope_for` scored that path **one-round**.

⭐ **The instance is the money route; the class is the allowlist.** A list of risky prefixes
is inherently incomplete and fails **silently**, and the two errors are not symmetric:

| wrong answer | cost |
|---|---|
| `full-loop` when contained | one review round |
| `one-round` when risky | unreviewed risky code merges |

**So the default is inverted.** A path is contained only if it is *named* contained
(`docs/`, `scripts/`, `tests/`, `.claude/`, `.agents/`); anything unrecognised is full-loop.
`app/api/`, `worker/` and `.github/workflows/` are additionally named risky, so a risky path
inside a contained root is still caught. Measured after the fix: an **unlisted** `lib/` path
and a top-level `package.json` both now score full-loop.

## M1 — the card said it replaced a rule that was still stated as live

**ACCEPTED AND FIXED.** §0 Q3 announced it replaces the instruction to present every Medium
to the user — and that sentence remained live prose in two places in this same file. The
contradiction had moved *inside* the document. Both are now marked **SUPERSEDED**, in place,
and kept because merged review documents cite them.

## M2 — the count-trigger contradiction moved rather than being resolved

**ACCEPTED AND FIXED, and this is the sharpest finding of the round.** `dev-process.md` was
corrected to arm on thrashing — and `review-method.md` still *described* the spine as arming
on four non-converging rounds. **The contradiction left the file it was reported in and
survived in the file that reported it.**

That is the **stale cross-reference** shape this very document names: *"when a decision is
reversed, grep for every place that stated the old one — a rewritten section does not
rewrite its own cross-references."* The rule was in the room and was not applied.

## ⚠ A defect the fixes themselves caused, caught by the check built for it

M2's repair replaced two lines with four, which shifted every line below it — and the card's
citation to *"How to record the call"* drifted from `:439` to `:441`. Caught by the
verification step the plan flagged as the most likely defect in the whole branch, and
repaired. **Every one of the 13 citations was re-verified after the edit, not assumed.**

## Verified on this tree

```
check-review-decision --self-test  38/38   (30 before; 8 added for B1 and B2)
check-plan-code       --self-test 128/128
check-docs · check-anchors · check-fixture-variation · check-selftest-counts ·
check-ratchet-contract · check-review-rounds · check-dashboard-entry      all rc=0
card citations: 13, drifted 0
```

**NOT CONVERGED — round 2 owed.** Two Blocking findings were fixed, and `:396` arms a
re-review on any round that returned a Blocking. The repairs are unreviewed code, and they
are the most suspicious code on the branch.
