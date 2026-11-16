# Round 1 — `harness-ships-elsewhere-b` — coordinator — ⟳ NOT CONVERGED (both halves); every finding FIXED, one bound STATED

```yaml
round: 1
fixes_nontrivial: true
subject: harness-ships-elsewhere-b
halves:
  codex: ran
  claude: ran
findings:
  - {id: X1, severity: Medium, aim: deliverable, fix_induced: false, component: staging, disposition: fixed}
  - {id: X2, severity: Medium, aim: deliverable, fix_induced: false, component: isolation, disposition: fixed}
  - {id: X3, severity: Medium, aim: deliverable, fix_induced: false, component: isolation, disposition: fixed}
  - {id: X4, severity: Medium, aim: deliverable, fix_induced: false, component: isolation, disposition: fixed}
  - {id: CM1, severity: Medium, aim: deliverable, fix_induced: false, component: isolation, disposition: fixed}
  - {id: CM2, severity: Medium, aim: deliverable, fix_induced: false, component: isolation, disposition: fixed}
  - {id: CM3, severity: Medium, aim: deliverable, fix_induced: false, component: staging, disposition: fixed}
  - {id: Cm1, severity: Low, aim: deliverable, fix_induced: false, component: prose, disposition: fixed}
  - {id: Cm2, severity: Low, aim: deliverable, fix_induced: false, component: prose, disposition: fixed}
  - {id: Cm3, severity: Low, aim: deliverable, fix_induced: false, component: prose, disposition: fixed}
```

Reviewed: PR #594 (marketplace-inventory plan Tasks 1–4) at `f6b39fde`. Halves:
[`codex/harness-ships-elsewhere-b-r1-codex.md`](../codex/harness-ships-elsewhere-b-r1-codex.md) (4 MAJOR),
[`claude/harness-ships-elsewhere-b-r1-claude.md`](../claude/harness-ships-elsewhere-b-r1-claude.md) (3 MAJOR, 3 MINOR).
Every finding was reproduced by a red case before its fix; none was judged wrong. The two halves did not overlap
except Codex 3 / Claude m2(b), which name the same system git config from two sides.

## Dispositions

| Finding | Severity | Disposition | Commit |
|---|---|---|---|
| Codex 1 — `.claude/plans` reaches a package through a skill directory or a link | MAJOR | FIXED: `PRIVATE` refused where an entry sits and where it ends — file, skill directory, link inside a skill — even when force-tracked | `4690a362` |
| Codex 2 — host site-packages and `.pth` files apply in the world | MAJOR | FIXED: `pyvenv.cfg` (no system site-packages) at the world root; `preflight` probes each allowed Python's `sys.path` and refuses anything outside the world and its stdlib (`foreign_paths`, pure). macOS's `/usr/bin/python3` shim ignores the cfg, and is refused by that probe — measured | `03923871`, `c1ea5962` |
| Codex 3 — system git config, credential helpers, keychain | MAJOR | FIXED for git: `GIT_CONFIG_NOSYSTEM=1` in the world env; `preflight` asks the world's own git for any `credential.*` / `url.*.insteadof` key and refuses one. **STATED BOUND for the keychain** — a 4th `ALWAYS:` entry in every record and `isolation-baseline.md` bound (e), with the observation that would show it (a world run that succeeds at something needing the author's identity) | `03923871`, `58d35372` |
| Codex 4 — preflight checks env key names, not values | MAJOR | FIXED: `boundary(world)` compares the env with `world_env(root)` key by key and VALUE by value (PATH included) and the layout with `LAYOUT`; both `preflight` and `run_isolated` call it | `03923871` |
| Claude M1 — `run_isolated` truncates the audit log; a detached server's events are lost; spike record says git never ran | MAJOR | FIXED: the log is appended, never truncated; each event carries the run's token; a survivor is reported as "outlived the record". The spike record's claim is WITHDRAWN (git is reachable on the `GET /` path); GO stands on (i)–(iii), which do not use the log | `03923871`, `58d35372` |
| Claude M2 — preflight ignores the cwd | MAJOR | FIXED: `run_isolated` refuses a cwd that does not resolve under the world root; `preflight` refuses a world root inside any checkout (`_checkouts()`, worktrees via `commondir`) | `03923871` |
| Claude M3 — staging ships untracked and gitignored files | MAJOR | FIXED: `plan()` asks the repository's own git (no inherited `GIT_*`, no system/global config) what is tracked; an untracked or ignored file, or link, is CANNOT RUN and named; an unlistable repository is CANNOT RUN | `4690a362` |
| Claude m1 — spike record does not say it overrode the plan's literal routing | MINOR | FIXED: both clauses named, why the FAILS IF exception governs, and that the overruled result is NO-GO at run 1 | `58d35372` |
| Claude m2 — baseline's "by construction" claims; credential helper | MINOR | FIXED: package set is a measurement (`distributions()` = `[]` in a world, 11-15 11:27) verified per run; deviation (c) rewritten — the system file is switched off | `58d35372` |
| Claude m3 — no spend-log row for Task 3 | MINOR | FIXED: Task 3 row (agent count not recorded — said so) and a row for this fold | `58d35372` |

## Numbers

| Script | Cases before → after | Mutations (killed / total) |
|---|---|---|
| `scripts/mkt_isolate.py` | 49 → 67 | 50 / 50 (`--only`, diagnostic slice, at `03923871`; `c1ea5962` adds one pure case and no mutation) |
| `scripts/mkt_stage.py` | 63 → 72 (+1 live case, uncounted) | 54 / 54 (`--only`, run as two halves of 27 on the manifest — each half under the call bound — at the tree committed as `4690a362`) |

All-manifest anchor resolve after the last code commit: 5,285 entries, 0 unbound. Gates after commit (base
`65e6f562`): both `--self-test`s, `check-docs`, `check-reference-namespace --base`, `check-doc-citations --base`,
`check-fixture-git-isolation`, `check-fixture-variation` (red on `foreign_paths` until `c1ea5962`), `check-ratchet-contract`,
`check-rc-contract`, `check-selftest-counts`, `check-anchors`, `check-features`, `check-review-rounds`,
`check-decision-scheme` — all rc 0.

## Cost noted

`mkt_stage`'s self-test went 1.9 s → ~7 s: each fixture is now a git repository (`git init`, `git add`), and the
live `claude plugin validate` case runs too. A full `--only` sweep of its 54 mutations (~4 s each, ×2 sides) no
longer fits one ~270 s call; it was split. `git init --template=` trimmed the fixture cost.

## Round-2 bet

**Round 2 finds nothing caused by this fold in component `staging`** (`mkt_stage.py`'s tracked-only and `PRIVATE`
checks). Falsified by any round-2 finding whose cause is `_tracked`, `_real` or the fixture repository change.
