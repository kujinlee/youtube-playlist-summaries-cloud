---
name: a-stated-bound-outlives-its-hole
description: "FIRES-WHEN: writing a test that asserts a known gap still exists — ⭐ A test that ASSERTS a known gap ('this case still PASSES') expires when the gap closes — and the expiry looks exactly like debt. A 2-week red in the schema suite was the alarm firing, not a bug. Before triaging a long-standing red, ask whether the assertion's PREMISE is still true"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 62196080-8a63-4c8f-a689-80aa431a832f
  modified: 2026-09-13T05:56:19.137Z
---

**Measured 2026-09-12, PR #296.** `scripts/mutate-live-schema-check.sh` asserted, as an expected
**pass**: *"BOUND: a bare INDEX on an M4 relation still PASSES — `idx:` carries no relation name."*
It scored ✗ and took the whole fifteen-gate schema suite red for two weeks. It was triaged to me as
a choice between *mis-scored* (small fix) and *genuinely unguarded* (a big project). **It was
neither.** The gap had CLOSED on 2026-08-28 — `CATALOG_SQL` joined `x.indrelid`, `idx` entered
`ATTRIBUTABLE_KINDS`, the manifest was regenerated — and the assertion documenting it was never
inverted. The block's own comment predicted this in as many words: *"if a later change silently
widens the scope, these turn red and the widening is a decision instead of an accident."*

**Why this class is nasty.** Every other test breaks when the code gets WORSE. A stated bound breaks
when the code gets BETTER, so the signal arrives wearing the costume of the thing it is not: a stale
red that everyone learns to step over. Two weeks of "known-red, pre-existing debt" is the expected
lifetime, not an anomaly.

**How to apply — three checks, in this order.**

1. **Before triaging any long-standing red, read the assertion's PREMISE and ask whether it is still
   true today.** Not "is the code broken" — *"is the sentence this test asserts still a fact?"* Here
   the premise was one grep away: the manifest's 12 `idx:` entries already read
   `idx:<relation>.<index>`, falsifying the bound's own words on disk.
2. **When you close a hole, grep for everything that ASSERTS the hole** — the code comment recording
   it, the backlog row, and the test that pins it. Backlog #65 had run this exact inversion once for
   the sibling added-COLUMN case; only the index half was missed, so the repair was already
   precedented and simply not carried through. See [[after-fixing-search-for-the-class]].
3. **A closed hole's description must change TENSE.** `docs/backlog.md` row 65 still said *"`idx:`
   renders as `idx:<indexname>` … this hole is on the money path"* in the present tense, and that
   sentence was what the triage brief quoted as evidence the hole was open. Keep the old sentence as
   a dated record if it earned one — but never leave it in the voice of a current fact.

**Inverting the polarity can SUBSUME a guard, and saying so is part of the fix.** The old case
carried a `landed` postcondition a Codex round had paid for — it defends an expected-**pass** from
SQL that never ran. Re-cast as an expected-**red** matched on a drift sentence only the guard can
emit, there is no green left for an unapplied mutation to earn, so `landed` goes. Write the argument
down at the deletion site; a reviewer's first question is why a paid-for guard is gone.

⭐ **THE SAME DEFECT THEN APPEARED TWICE MORE, EACH TIME INTRODUCED BY THE PREVIOUS FIX** — MERGED as
PR #296, squash `1e966b62`, suite `73 ✓ / 0 ✗` on master.

| where | the sentence | what the code did |
|---|---|---|
| the original bound | *"a bare INDEX still PASSES — `idx:` carries no relation name"* | `idx:` had carried its relation since 2026-08-28 |
| my r1 fix | *"there is no green left for an unapplied mutation to earn"* | `probe_kind` emits **two** assertions; the undo half is an expected-PASS |
| my r2 fix | *"a downstream expected-pass reports NOT RUN"* | the flag had **one** writer and **one** reader, so three sibling probes still died for a leftover |

Each sentence was true of the thing I was looking at and false of the code it justified. **The
correction is not "write more carefully" — it is to construct the world where the sentence should
fail and run it.** The reviewer's sharpest move was neutering `unexpected()` to `return set()` so the
gate detected nothing: the old harness printed **four cheerful greens**; the fixed one printed four
NOT RUNs over the same five reds. No amount of re-reading produces that.

⚠ And validate the sabotage before trusting what it shows — the neutered copy's own `--self-test`
went `119/119 → 104/119`, which is how you know the neuter bit. A mutation that does not bite makes
every downstream measurement meaningless while looking like evidence.

Related: [[a-filed-finding-s-proposed-fix-is-a-hypothesis]] (both rounds' proposed fixes were weaker
than their findings), [[a-costbenefit-finding-expires-when-the-denominator-moves]] (a finding expiring
when its basis moves), [[a-test-that-cannot-fail]], [[a-check-result-is-not-the-claim]] (the
opposite error — stepping over a red you "recognise"), [[check-the-assumption-not-just-the-code]].
