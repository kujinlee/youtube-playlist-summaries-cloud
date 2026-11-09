# Round 4 (PAST THE CAP, a scoped check) — `spec-586-redesign` (PR #552, backlog #586) — coordinator — Codex NOT CONVERGED; STOPPED, FINDINGS FILED

```yaml
round: 4
fixes_nontrivial: false
subject: spec-586-redesign
halves:
  codex: ran
  claude: gap
findings:
  - {id: R4-F1, severity: High, aim: deliverable, fix_induced: true, component: observed-reach-spec, disposition: filed}
  - {id: R4-F2, severity: High, aim: deliverable, fix_induced: true, component: observed-reach-spec, disposition: filed}
```

REVIEW GAP: claude — alternation

Subject: `docs/superpowers/specs/2026-11-09-observed-reach-selection-design.md` at `fbb89992` (the round-3 fold).

- Codex half: `docs/reviews/codex/spec-586-redesign-r4-codex.md` (F1, F2), with its verdict
  `docs/reviews/verdicts/spec-586-redesign-r4-codex.verdict.json`. NOT CONVERGED. Committed on its own.

Round 4 is past the cap (`docs/review-method.md` §0 Q4c): its findings are FILED, not folded. Neither is a
BLOCKER in the cap's sense (no shipped behaviour changes: the spec is unbuilt and shadow mode alone changes no
selection).

## Dispositions

| Finding | Severity | Caused by r3 fold? | Disposition | Spec section touched |
|---|---|---|---|---|
| **R4-F1** a pre-existing external symlink, unlinked during the trace, hides a probe made through it: the parse-time longest-existing-prefix test can no longer resolve it, so the target reads `complete` with a lost probe | High | **yes**: the r3 fold replaced unresolved-link handling with a parse-time-only test | FILED -> backlog #590 | §4 bound 6 (pointer only) |
| **R4-F2** `ioctl` is classed read-only, but `FS_IOC_SETFLAGS` modifies an inode without an `O_RDWR` open, so a cross-run write by one control goes unseen | High | **yes**: the r3 fold enumerated `ioctl` in the read-only class | FILED -> backlog #590 | §2 class text (one-line note); §4 bound 6 |

Both are filed as ONE row because they have one cure: classify trace events by a DEFAULT-DENY allowlist measured
from our own suites. Any syscall, any `ioctl` request code, and any unlink, rename or replace of a path component
outside the staged copy that is not on the allowlist makes the trace INCOMPLETE (today's rule). The build plan's
step 1 measures the suites' actual syscalls and ioctl requests. **Backlog #590 must close before any skip takes
effect; shadow mode alone does not.**

## Thrashing?

**YES, thrashing-shaped** (`docs/review-method.md` §0 Q4c: answer *thrashing or prose floor?* with per-finding
evidence). Round 2 (7 of 7 findings from the r1 fold), round 3 (F4 and F6 from the r2 fold) and round 4 (2 of 2
from the r3 fold) all came from HAND classification of syscall semantics, in one component
(`observed-reach-spec`'s syscall and path classification). Not a prose floor: R4-F1 and R4-F2 are constructed
counterexamples that read `complete` while a read is lost.

**Can a redesign remove it?** YES. A default-deny allowlist removes the class, because the classification is
MEASURED from our own suites, not authored, and an event nobody measured is INCOMPLETE. It changes how events are
classified, not the approach (the `strace -f` recorder, the comparison-set rules, shadow mode and the owner's
decisions are all unchanged), so it is NOT a second redesign of the subject. It is folded as a build
prerequisite (backlog #590), not as another review round, so the cap holds: no round 5 is convened.

## NEEDS THE OWNER

None. Backlog #590 is inside the owner's section 7 decisions (Q3's today's-rule fallback is what it uses).

## Verdict

**Codex: NOT CONVERGED. STOPPED PAST THE CAP; findings filed** (backlog #590). No fold, no round 5.
