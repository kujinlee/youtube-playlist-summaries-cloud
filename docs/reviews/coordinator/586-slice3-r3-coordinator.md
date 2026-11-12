# Round 3 — `586-slice3` — coordinator — Claude NOT CONVERGED on one Major; fixed by removing the SHADOW exemption as a class

REVIEW GAP: codex — alternation (round 3 runs ONE half; Codex ran in rounds 1 and 2).

Subject: PR #567 (DRAFT), branch `586-slice3`, reviewed head `aa5c4d78`.
Half: `docs/reviews/claude/586-slice3-r3-claude.md`, one Major (R3-1). Every round-1 and round-2 input still refuses,
and every control is still accepted. Self-test 284/284 and 206/206 mutations at the reviewed head.

```yaml
round: 3
fixes_nontrivial: true
subject: 586-slice3
halves:
  claude: ran
  codex: gap
findings:
  - {id: R3-1, severity: Major, aim: deliverable, fix_induced: true, component: cross-run-record, disposition: fixed}
```

## R3-1: a SHADOW argument still skipped both link checks

Round 1's fold added the SHADOW argument: a labelled open's own path text, kept for the cross-run comparison. That fold
exempted it from every check an unlabelled path gets. Round 2 restored two of those checks (`..` and `/proc`).
Round 3 shows the other two, the runtime-link and pre-existing-link refusals, were still exempt.

Example: the target plants `a -> .home` and opens `a/cur`. The kernel labels the open `docs/b.md`. The peer wrote
`.home/cur`. The text `a/cur` never meets `.home/cur`, so both runs were `complete` and the flow was lost. The
pre-existing-link form (`alias -> cT`) has the same gap.

**THRASHING is armed (conservative reading).** Round 2's finding and round 3's both come from one fold decision:
the SHADOW exemption in round 1. Strictly, R3-1 was caused by round 1's fix, not round 2's. But two consecutive
rounds each found a check missing from the same exemption, in the same component. That is the pattern the arming
condition exists to catch: fixing a class one instance at a time.

## The fix removes the class, not the instance

The two branches are now one. `elif from_label is False or cross:` sends an unlabelled path, and (when `cross`) a
SHADOW argument, through the same checks. The SHADOW-only `..` and `/proc` refusals run first, because `_cwd_pass`
skips them for a labelled open. After that, both link checks run for both kinds of path. A check added to that branch
later applies to SHADOW automatically, so there is no exemption left to fix piecemeal. The read view (`cross` False)
is unchanged.

## How the fix was proved

- **Before → after.** Three new cases: R3-1's runtime-link input, the pre-existing-link input, and a control (the same
  labelled open named directly stays `complete`). With the new cases on the reviewed code: **285/287**, and the two
  failures are exactly the R3-1 cases. After the fix: **287/287** (288 with the read-view socket case below).
- **Mutations.** 206 → **207**. Two anchors were re-bound (the SHADOW `..` and `/proc` lines moved into the shared
  branch). One was added: SHADOW excluded from the shared branch, which the runtime-link case kills. One was
  re-targeted: "a socket path skips the link checks (taken for a shadow)" SURVIVED the first sweep, because the
  link checks now run for SHADOW too. I first deleted it as equivalent. A probe refuted that: tagging a socket SHADOW
  drops it from the READ view (`resolve_log` gives `connect → []` instead of `['/t/docs/state']`), and no case
  asserted the read view kept a socket. Case added ("r3: a socket path in the copy is kept in the read view"), and
  the mutation renamed "a socket path is taken for a shadow" to name it. Self-test **288/288**; pin 207.

## Phase 6, and the round cap

Round 3 is the last full round under the cap. The architecture review that THRASHING calls for is filed as backlog
#626, to run after the weekly reset (usage is at 95%). Its question is whether the cross-run view should be built
from paths resolved ONCE, so that a "kept for comparison" path never has its own resolution rules. This round's fix
does that inside `_resolve`; the review checks `_cwd_pass` and `_named` for the same split.

## Next

PR #567 goes ready, master (now holding slice 2, PR #565) is merged in, and it merges on `check-merge-ready` READY.
