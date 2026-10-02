# Round 2 convergence judgement — the LLM recall matcher (backlog #191)

**Verdict: NOT CONVERGED. Round 3 is required, and the architecture review does NOT arm.**

`docs/dev-process.md:108` is explicit that the arming condition is **thrashing, not a count**: it
fires when *"two consecutive rounds carry findings caused by the previous round's own fix, in one
component"*, and the round document must answer **thrashing or prose floor?** with per-finding
evidence. This is that answer.

## The inventory, per finding, by cause

| round | finding | caused by a previous round's fix? |
|---|---|---|
| 1 | B1 unreadable plan silent | ✗ original |
| 1 | H1 seven `exit 1` paths | ✗ original |
| 1 | H2 trigger text never re-checked | ✗ original |
| 1 | H3 duplicate step numbers | ✗ original |
| 1 | H4 hook's cross-file literal | ✗ original |
| 1 | M1–M5 | ✗ original |
| 1 | codex ×5 | ✗ original |
| — | the model call inheriting repo hooks | ✗ original — found by RUNNING, not by either half |
| **2** | codex #1 `live_trigger_for`'s `None` | ✅ **caused by round 1's H2 fix** |
| **2** | codex #2 undecodable cache at rc 2 | ✅ **caused by round 1's H1 fix** |
| **2** | codex #4 the H1(e) mutation unfaithful | ✅ **caused by round 1's H1 fix** |
| 2 | codex #3 `UNREADABLE_PLAN` only in `--fire` | ✅ caused by round 1's B1 fix |
| **2** | claude BLOCKING rc 5 at two sites only | ✅ **caused by round 1's B1 fix** |
| **2** | claude H1 `check-fixture-variation` red in CI | ✅ **caused by my round-2 fold** |
| 2 | claude H2 the mixed plan | ✗ original — round 1 NAMED it and the fold did not close it |
| 2 | claude H3 `do_arm` unwritable cache | ✗ original — H1 covered reads, never writes |
| 2 | claude H4 `LIVE_UNREADABLE` silent fallback | ✅ caused by round 2's own #1 fix |
| 2 | claude H5 dedupe covers 1 of 8 | ✅ caused by round 1's M4 fix |

## Thrashing? No — and the distinction is the whole judgement

**Round 2 is unambiguously a fix-caused round: nine of its fourteen findings were introduced by a
previous fix.** That is one round of the shape. The condition requires **two consecutive** such
rounds **in one component**, and neither half is met:

- **Round 1 cannot be fix-caused** — there was no round 0. So there is no consecutive pair.
- **The findings are spread across components, not concentrated in one.** The blob-addressing case
  that bought this rule had *one* component producing a Blocking or High in six consecutive rounds
  while everything else converged. Here the fix-caused findings land in five different places:
  `live_trigger_for`, `read_or_refuse`, `plan_verdict`/`read_armed_plan`, the mutation manifest, and
  the dedupe. **No component has been re-opened twice.**

## Prose floor? No — these are code defects with reproductions

Every round-2 finding was **reproduced by its reviewer before being reported**, and every one was
**re-reproduced here against the fix**. None is a wording preference. The test
`review-method.md` gives — *can a redesign remove it?* — is answered yes for all of them, and in
three cases the redesign is what was done: the dedupe moved from a branch to a boundary, the
refusal label moved from an `is` comparison to the class, and the rc-5 boundary moved from
`plan_verdict` to the sentinel's existence.

## Why round 3 is required rather than optional

⛔ **The round-2 fold added ~275 lines and 48 mutations that no reviewer has seen.** That includes a
new rc boundary, a new dedupe mechanism, a loose-box parser and a changed `plan_verdict` signature.
Convergence means a round that finds no Blocking and no High; round 2 found both, and its fixes are
unreviewed. Declaring convergence here would mean shipping the fold on my own word — and the record
of this fold is that **my own word has been wrong at every round**:

- round 1's H3 fix was **vacuous** (a comparison that cannot differ), caught by the sweep
- round 2's H2 and H1 fixes **failed inside their own fix**, caught by Codex
- round 2's B1 fix reached **one of five** paths, caught by Claude
- my round-2 fold **turned a CI gate red**, caught by Claude, invisible to both the self-test and the
  sweep
- two of my own cases **could not fail** — one asserting a return code both branches share, one
  building two worlds where one was needed

⭐ **Six times in this fold a mutation survived or a gate went red because a case tested the callee
while the defect sat at the call site.** That is the single recurring shape, it is not yet exhausted,
and it is exactly what a third round should hunt.

## Recommendation

Run round 3, **alternating again and starting with the half that did not go last** — the Claude half
went second in round 2 and found the Blocking, so Codex leads round 3. Brief it with this document
rather than with the diff: the useful instruction is *"nine of fourteen findings last round were
caused by the previous fix; find the tenth."*

⚠ **Not launch-blocking, and nothing here is pushed.** `master` is untouched at `446025ab`.
