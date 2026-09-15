# Round 1 — `explainer-src-root-self-configures` (PR #295) — coordinator

```yaml
round: 1
fixes_nontrivial: true
subject: explainer-src-root-self-configures
halves:
  codex: ran
  claude: ran
findings:
  - {id: B1, severity: Blocking, aim: deliverable, fix_induced: false, component: pasteable-commands, disposition: fixed}
  - {id: H1, severity: High, aim: instrument, fix_induced: false, component: repo-root, disposition: fixed}
  - {id: M1, severity: Medium, aim: deliverable, fix_induced: false, component: src-root-help, disposition: fixed}
  - {id: M2, severity: Medium, aim: deliverable, fix_induced: false, component: repo-root, disposition: filed}
  - {id: M3, severity: Medium, aim: deliverable, fix_induced: false, component: restart-lifecycle, disposition: filed}
  - {id: M4, severity: Medium, aim: deliverable, fix_induced: false, component: src-root-docs, disposition: fixed}
  - {id: L1, severity: Low, aim: deliverable, fix_induced: false, component: restart-endpoint, disposition: filed}
  - {id: L2, severity: Low, aim: deliverable, fix_induced: false, component: restart-log, disposition: filed}
  - {id: L3, severity: Low, aim: deliverable, fix_induced: false, component: chrome-layout, disposition: filed}
  - {id: C1, severity: Low, aim: deliverable, fix_induced: false, component: repo-root, disposition: declined}
```

## The round in one line

**Both halves ran, both found the same Blocking by different routes, and the Claude half's
version is strictly better — which is the case for running two.**

## Halves

| Half | Verdict | Findings | File |
|---|---|---|---|
| Codex (`gpt-5.5`) | FINDINGS | 1 Blocking, 1 High, 1 Low | `docs/reviews/codex/explainer-src-root-self-configures-r1-codex.md` |
| Claude | FINDINGS | 1 Blocking, 1 High, 4 Medium, 3 Low | `docs/reviews/claude/explainer-src-root-self-configures-r1-claude.md` |

⚠ **The Codex half was run TWICE and the second run is the filed one.** The first used
`--out r1-codex.md`, whose basename the wrapper also uses to name the verdict — so it wrote
`docs/reviews/verdicts/r1-codex.verdict.json`, **overwriting PR #302's committed round-1
evidence**. Restored by `git checkout --` (verified: `head bb265c08`, 4259 chars) and re-run
under an explicit `--verdict`. Recorded here because the evidence path has no allocator and
this is its **third** measured occurrence. The two runs are not identical — same prompt, same
model, 2123 vs 4112 chars, two findings vs three — which is itself worth noting: **one
reviewer pass is a sample, not a measurement.**

## Disposition, per finding, by `review-method.md` Q3

### B1 — Blocking — pasteable commands are not shell-quoted → **FIXED**

Both halves found it; the Claude half's failure mode is the one that makes it Blocking rather
than High. `cd /tmp/some repo` fails, **the shell continues**, and the second line is a
*relative* invocation — so the paste silently restarts **whatever checkout the reader was
standing in**. Verified independently by the coordinator: `bash -c 'cd /tmp/some repo'` → rc=1.

That is the outcome `repo_root`'s own docstring names as worse than saying nothing, reached
through the quoting axis instead of the worktree axis.

⭐ **The fixtures walked past it, and so did mine.** `page_chrome.py:562` already used
`/tmp/some repo` and `explainer-serve.py:1650` `/tmp/another checkout` — adversarial values,
asserted only with `in`. **A test can use a hostile input and assert nothing hostile about
it.** The fix therefore cannot be another substring case.

### H1 — High — the worktree fix is unguarded → **FIXED**

Mutation-proven by the Claude half: inserting `return here` to delete the whole git resolution
in `repo_root` leaves **68/68 green**. Neither guarding case can distinguish the broken value
from the fixed one — a linked worktree *does* contain `scripts/explainer-serve.py`, and its
path does *not* contain `.git`. `scripts/mutations/page_chrome.json` has 11 entries and none
touches `repo_root`, `restart_commands` or `restart_control`, so `--mutate .` does not cover it
either. Aim is `instrument`: the shipped behaviour is right, the guard around it is vacuous.

### M1 — Medium — the no-fallback arm is unrunnable and reintroduces a placeholder → **FIXED**

Contained, inside the delta, touches only a file already in the diff, adds no mechanism.
Both halves found it (Codex filed it Low).

### M4 — Medium — a module comment documents `/src/` as off by default → **FIXED**

A comment edit in a file already in the diff. Cheapest possible fix and it is stale prose
about the branch's own change.

### M2 — Medium — `repo_root()` and `REPO` are two answers to "which checkout" → **FILED**

Q3: needs a **policy call** — whether the restart button should target the durable main
checkout or the server's own copy. Both are defensible and the docstring argues for durability
with measured evidence. Not a mechanical repair, so it is filed rather than guessed at.

### M3 — Medium — `--restart` with a stale pidfile → **FILED**

Needs a new mechanism (liveness detection distinct from pidfile presence). Q3 files those.

### L1, L2, L3 → **FILED**

`POST /_restart` unauthenticated (a security-policy call), `.restart.log` has no reader, and a
flex-layout shift the reviewer itself labelled **UNVERIFIED**. None is contained-and-mechanical.

### C1 — Codex's Blocking → **DECLINED, and the residual kept**

Codex filed *"restart command abandons the worktree branch"* as Blocking, proposing that the
worktree root be embedded instead. **That is the behaviour `page_chrome.py:111-116` records as
measured and rejected:** embedding `/…/scratchpad/wt` gave *"a dead path within the hour, which
is worse than no instruction, because it fails after the reader has already trusted it."*
Codex quoted the lines around that docstring without engaging with it.

⚠ **Declined as filed, not dismissed.** The residual — the page never says *which* checkout it
will restart — is real, and is carried as **M2**, where it belongs as a policy question rather
than as a Blocking defect.

## Q4 — is another round owed?

**(a) Convergence: CONTINUE.** A Blocking and findings in the deliverable; `fixes_nontrivial:
true`. Not close to a stop.

**(b) Tree identity:** the fixes for B1/H1/M1/M4 are code no round has seen, so round 2 is owed
on that axis as well as this one. Cheapest-first per `review-method.md:90`: the fixes land
**before** the next round rather than after it.

## Q5 — thrashing?

**No.** Round 1: no finding here was introduced by a previous round's fix. Nothing to arm.
