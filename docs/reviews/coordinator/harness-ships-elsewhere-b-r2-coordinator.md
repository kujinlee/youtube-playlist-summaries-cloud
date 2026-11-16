# Round 2 — `harness-ships-elsewhere-b` — coordinator — ⟳ NOT CONVERGED (Codex); every finding FIXED; the round-1 bet LOST

```yaml
round: 2
fixes_nontrivial: true
subject: harness-ships-elsewhere-b
halves:
  codex: ran
  claude: gap
findings:
  - {id: X1, severity: Medium, aim: deliverable, fix_induced: false, component: staging, disposition: fixed}
  - {id: X2, severity: Medium, aim: deliverable, fix_induced: false, component: staging, disposition: fixed}
  - {id: X3, severity: Low, aim: deliverable, fix_induced: true, component: staging, disposition: fixed}
  - {id: X4, severity: Low, aim: deliverable, fix_induced: true, component: isolation, disposition: fixed}
  - {id: X5, severity: Low, aim: deliverable, fix_induced: true, component: prose, disposition: fixed}
```

REVIEW GAP: claude — alternation

Reviewed: PR #594 at `08dc620b`, after the round-1 fold. Half:
[`codex/harness-ships-elsewhere-b-r2-codex.md`](../codex/harness-ships-elsewhere-b-r2-codex.md) (2 MAJOR, 3 MINOR;
model `gpt-6.1-sol`). Every code finding was reproduced by a red case before its fix; none was judged wrong.

**The round-1 bet LOST.** It said round 2 would find nothing caused by the round-1 fold in `staging`. Codex 3 is
caused by that fold's `_tracked` (it decoded git's index names as strict UTF-8). Codex 4 and 5 are fold-induced
too, in `isolation` and `prose`: the round-1 fold wrote "VERIFIED per run" and "neither tool reads it today", and
neither sentence was true as written. Codex 1 and 2 are holes in the round-1 rule, not caused by its fix.

**Thrashing: NOT armed.** This is the first round with fold-induced findings. A round-3 finding caused by THIS
fold in `staging` would be the second consecutive one in that component and arms Phase 6.

## Dispositions

| Finding | Severity | Disposition | Commit |
|---|---|---|---|
| Codex 1 — a case alias of `.claude/plans` (`.CLAUDE/PLANS`) bypasses the private-path exclusion | MAJOR | FIXED by one rule: a comparison that EXCLUDES compares FOLDED (NFKC + casefold), one that INCLUDES compares EXACT, so both err towards refusing. `_under` carries it. The alias is refused declared in `files`, as a skill directory, and reached through a link | `f065e2ea` |
| Codex 2 — an untracked or gitignored directory link in a declared path's parents is hidden by `parent.resolve()` | MAJOR | FIXED: `_real` no longer resolves in one step. It walks the path one component at a time; every link on the way must be tracked, no component may sit under a private directory (so a target that passes THROUGH `.claude/plans` and back out is refused), a `..` may not leave the repository, an absolute target must spell a path below the repository root, and a loop ends at 40 links | `f065e2ea` |
| Codex 3 — a tracked name that is not UTF-8 crashes `_tracked()` | MINOR, fold-induced | FIXED: names are decoded with `os.fsdecode`; an unrelated non-UTF-8 name no longer stops a declared file from staging | `f065e2ea` |
| Codex 4 — "VERIFIED per run" is not true through `run_isolated()` | MINOR, fold-induced | FIXED at the execution boundary, not in prose: `measured(world)` (each allow-listed Python's `sys.path`, git's credential config) is called by `preflight` AND by `run_isolated`. The baseline now says which checks `run_isolated` repeats and which stay `preflight`'s alone (HOME and bindir entries, the explainer port) | `f065e2ea`, `1196ae9d` |
| Codex 5 — "neither tool reads [the keychain] today" is inferred from auth status | MINOR, fold-induced | FIXED: bound (e) states only what was measured (neither tool reported an identity) and says keychain access is UNVERIFIED | `1196ae9d` |

**Class search** (the same defect in the other path checks of both scripts): the exact-compare exclusion was also
at `.agents/skills`, at `.claude-plugin`, at the destination collision (two declarations differing only in case
would overwrite one another on a case-insensitive volume), at the out-directory-inside-the-repository check, and
at `mkt_isolate`'s three "inside a checkout" sites (world root, HOME entry, allow-listed command). All seven are
fixed, each with its own red case and its own mutation. Inclusions (`cwd` inside the world, a program path inside
the world) stay exact on purpose: folding an inclusion would ACCEPT more.

**Bounds stated, not fixed** (in `mkt_stage.py`'s docstring): a hard link to a private file is indistinguishable
from a tracked file; HFS+ ignores some code points that NFKC does not fold; the bytes that ship are the working
tree's, not the index's.

## Numbers

| Script | Cases before → after | Mutations (killed / total) |
|---|---|---|
| `scripts/mkt_isolate.py` | 67 → 73 | 57 / 57 (pin 50 → 57: 7 added, 4 re-bound). `--only`, diagnostic, 4 slices of 15/14/14/14 |
| `scripts/mkt_stage.py` | 72 → 89 (+1 live case, uncounted) | 67 / 67 (pin 54 → 67: 13 added, 12 re-bound onto the walk). `--only`, diagnostic, 5 slices of 14/14/13/13/13 |

Every slice: rc 0, every mutation killed AND attributed to the case it names, at the tree committed as `f065e2ea`.
Each slice ran on a temp copy of the tracked tree whose manifest and pin held that slice only; the repository's
own manifest and pin were never cut. All-manifest anchor resolve: 5,342 entries, 0 unbound.

## Cost noted

A slice of ~14 `mkt_stage` mutations takes ~160 s; the manifest no longer fits two calls under the ~270 s bound
and took five. `check-plan-code.py` has no flag for a slice of one manifest, so the slice was cut by hand on a
copy. `run_isolated` now starts one extra process per allow-listed Python and one for git on every run.

## Filed

- backlog #656 — `check-review-decision.py` names its subject after the branch, so this slice-qualified subject
  reads as `rounds=0` (measured on this branch).
- backlog #657 — the agent watchdog becomes a repository script (owner, 11-15 10:30).

## Round-3 bet

**Round 3 finds nothing caused by this fold in component `staging`** — `mkt_stage.py`'s `_real` walk, `_under`
and `_tracked`. Falsified by any round-3 finding whose cause is the component walk (a link shape it mis-walks or
a tracked path it wrongly refuses), the folded compare, or the `os.fsdecode` decoding. A second fold-induced
finding there arms Phase 6 (THRASHING), per `docs/review-method.md`.
