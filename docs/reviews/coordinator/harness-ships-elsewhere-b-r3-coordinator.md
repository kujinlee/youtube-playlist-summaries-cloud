# Round 3 — `harness-ships-elsewhere-b` — coordinator — ⟳ NOT CONVERGED (Claude); 1 BLOCKER; the round-2 bet LOST; Phase 6 convened

```yaml
round: 3
fixes_nontrivial: true
subject: harness-ships-elsewhere-b
halves:
  claude: ran
  codex: gap
findings:
  - {id: F1, severity: Blocking, aim: deliverable, fix_induced: false, component: staging, disposition: fixed}
  - {id: F2, severity: Low, aim: deliverable, fix_induced: true, component: staging, disposition: fixed}
  - {id: F3, severity: Low, aim: deliverable, fix_induced: false, component: staging, disposition: fixed}
  - {id: F4, severity: Low, aim: deliverable, fix_induced: false, component: staging, disposition: fixed}
  - {id: F5, severity: Low, aim: deliverable, fix_induced: true, component: isolation, disposition: fixed}
  - {id: F6, severity: Low, aim: deliverable, fix_induced: true, component: prose, disposition: fixed}
```

REVIEW GAP: codex — alternation

Reviewed: PR #594 at `3bd59f0d`, after the round-2 fold. Half:
[`claude/harness-ships-elsewhere-b-r3-claude.md`](../claude/harness-ships-elsewhere-b-r3-claude.md) (1 BLOCKER,
0 MAJOR, 5 MINOR). No code was changed in this round: every finding is OPEN, and `filed` above is the one
disposition value that reads as open. None was judged wrong. F1 to F4 were reproduced again by the Phase 6 review
at `4a957e0d`.

**The round-2 bet LOST.** It said round 3 would find nothing caused by the round-2 fold in `staging`. F2 is caused
by that fold's `fold` (NFKC + casefold, wider than the filesystem): it refuses `x².md` + `x2.md`, two distinct
files. F5 and F6 are fold-induced too, in `isolation` and `prose`. F1, F3 and F4 are older holes in the same walk,
not caused by a fix.

**Thrashing: ARMED → Phase 6.** Round 2 carried X3 and round 3 carries F2, each caused by the previous round's fold,
both in component `staging`. The review:
[`architecture-review-2026-11-15-harness-ships-elsewhere-b.md`](architecture-review-2026-11-15-harness-ships-elsewhere-b.md).
Its answer: a mechanism defect (path checks done on spellings), and a redesign removes the question. No accreting
fold of this round is to be written.

## Dispositions

| Finding | Severity | Disposition |
|---|---|---|
| F1 — a tracked link `.claude -> dot` lets `.claude/plans/secret` stage | BLOCKER, not fold-induced | **fixed** in `3e0fc963`: the private root is an object identity, tested on every object the walk steps on (red cases 1 and 2) |
| F2 — `fold` (NFKC) refuses distinct files `x².md` + `x2.md` | MINOR, fold-induced | **fixed** in `3e0fc963`: `fold` is deleted; the source side compares identities; the destination uses one canonical key NFC(casefold(NFD)) (red cases 3 and 9) |
| F3 — an NFD name on disk, NFC in git's index, is refused as untracked | MINOR | **fixed** in `3e0fc963`, by the coordinator's override rather than the review's open decision: a declared path must equal a tracked name after NFC of BOTH sides, case exact (red case 4, plus `DOCS/a.md` vs tracked `docs/a.md` → refused, naming the tracked spelling) |
| F4 — a tracked link `.agents -> ag` bypasses the `.agents/skills` exclusion | MINOR | **fixed** in `3e0fc963`: the skills home is an identity too (red case 5) |
| F5 — the probes' fixed 60 s timeouts outrun the caller's `timeout` | MINOR, fold-induced | **fixed** in `3e0fc963`: `run_isolated` passes `min(timeout, 60)` to the probes |
| F6 — `isolation-baseline.md:27` states a stricter check than the code runs | MINOR, fold-induced | **fixed** in `3e0fc963`: `isolation-baseline.md:27` states the check the code runs |

The build's fold rewrote each row above to `fixed` with its commit (`3e0fc963`); nothing was left to file. The two
Phase 6 findings below were fixed in the same commit: P6-N1 is refused at `plan()`, and the private root as a tracked
link is refused by identity.

## Numbers (Phase 6, measured at `4a957e0d` on the default APFS volume)

| Measurement | Committed rule | Round 3's fixes patched on | Identity |
|---|---|---|---|
| Wrong answers on 30 fixtures | 10 | 2 | 1 (an absolute link, refused by rule) |
| 12 filesystem aliases of `.claude/plans`: staged (a leak) | 0 | 0 | 0 |
| 403 distinct directories holding a tracked file: refused | 403 | 26 | 0 |
| Real repository, 25 declarations: same plan as the committed rule | — | — | 25 of 25 |

Sweep corpus: 14,456,794 substitutions and 15,568,868 insertions; NFKC wrong refusals 402 + 1, misses 0; canonical
fold 0 and 0. Destination rule on 11 sets: committed rule wrong on 5, prefix policy wrong on 0.

## Found by the Phase 6 review, not by round 3

- P6-N1 — a tracked file named `skills` in `files` plus any skill passes `plan()`; `stage()` then raises an
  uncaught `IsADirectoryError` after writing a file. In the build brief as red case 10.
- The private root ITSELF a tracked link (`.claude/plans -> ../dot`): `files=dot/secret` stages. Red case 2.

## Round-4 bet

**Round 4 finds no input where the source decision differs between two paths the filesystem resolves to one
object**, and nothing caused by the redesign in component `staging`. Falsified by one such input. The stated bounds
(another filesystem, a tree changed during staging, a destination alias beyond case and canonical form) are not
falsifiers. If lost, the next route is `split`: staging stops accepting links.
