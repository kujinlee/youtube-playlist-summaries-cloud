Reviewed head: 9f6918618114700fbb2431535ce66d52819ec32c

# Round 2 — `boundary-compaction-440` — Claude half (adversarial)

Subject: PR #463 (backlog #440), the fold `cfdcf659..9f691861`, then the PR as a whole.
Codex: `REVIEW GAP: codex — alternation` (round cap, r2 is one half).

Claim under refutation: *"Every r1 finding is fixed or soundly declined; the hook never wedges a session or defers
compaction past a safe margin below the model's hard limit; it fails open on every error path; a paused plan or
another session's plan is not a mid-work signal; and the fold introduced no new defect."*

**Result: the last clause is refuted three times, all Low, none a Q4c BLOCKER.** The safety clauses (no wedge,
never past the limit, fail-open) held under every input I constructed.

## Gates run (foreground, on 9f691861)

| Check | Result |
|---|---|
| `check-compaction-boundary.py --self-test` | 77/77 |
| `check-plan-code.py --mutate . --only scripts/check-compaction-boundary.py` | 41 killed, 41 attributed, 0 survivors (34 s) |
| My own reverts, on a throwaway copy of `scripts/` (deleted after) | 5 of 5 red — see *Reverts* |

## Findings

### R2-1 — Low — FILE — fix-induced (C1's fix): a foreground agent whose REPORT quotes "agent launched" stays open for 3 h

`scripts/check-compaction-boundary.py:202` tests `"agent launched" in text` over the WHOLE tool result. A completed
foreground agent's result is its final report plus the `agentId:` footer, so a report that merely contains the
phrase is read as a background launch, gets a task id, and waits for a `<task-notification>` that never comes.

Ran (`scan` on two records):

```
assistant tool_use Agent id=t1
user tool_result t1: "Review done. The rule keys on 'Async agent launched successfully.'\nVERDICT: CONVERGED\nagentId: abc123 (use SendMessage)"
-> agents[t1].open == True; signals(...) == ['agent']
```

Not hypothetical: every reviewer of this PR writes that phrase (this document does). Same shape for
`Spawned successfully … \nname: x` in a report (ran: `open == True`). Bounded by the 3 h lease and the 5-min idle
test, so it defers, never wedges. **Fix:** anchor to the measured launch shape — the coordinator's note says all 65
launches BEGIN `Async agent launched successfully.` and all 189 spawns BEGIN `Spawned successfully.` — e.g.
`text.lstrip().startswith(...)`, plus a case with the phrase inside a completed report.

### R2-2 — Low — FILE — fix-induced (F1's fix): a cwd inside a NESTED git repo misses the live plan

`:385`/`:399` now read the sentinel from `checkout_of(cwd)` and fall back to the project dir only when no checkout
holds the cwd. `.remember/` in the main checkout is its own git repository (`.remember/.git` exists), and the
coordinator's transcript records `"cwd": ".../.remember"` 32 times (of ~39k cwd stamps; `docs/memory` and
`docs/explainers` have no `.git` and walk up correctly). Ran:

```
checkout_of(<main>/.remember) -> <main>/.remember
```

so a live, unpaused coordinator plan reads as absent while the cwd is there. Pre-fold, `:323` read
`any(... for r in (checkout, project))`, so this is new. Direction is the safe one (allow), but it is the miss the
docstring calls "the defect this hook exists for". Related, NOT fix-induced: `log_path` (`:432`) routes the log to
`<main>/.remember/.claude/compaction-boundary.log`, which `git check-ignore` reports NOT ignored in that repo, and
`--summary` from the main checkout never sees those rows. **Fix:** when `CLAUDE_PROJECT_DIR` is set, prefer the
checkout only if it is the project's own main checkout or a linked worktree of it (`main_checkout(checkout) ==
main_checkout(project)`); otherwise use the project.

### R2-3 — Low — FILE — fix-induced (C2/F2 clamp): the ceiling falls BELOW W for W in (180k, 200k] and (900k, 1M]

`ceiling()` (`:286`) returns `min(1.5W, 0.9L)`. Ran:

```
W=190000 -> (180000, 200000)  BELOW W     W=950000  -> (900000, 1000000)  BELOW W
W=200000 -> (180000, 200000)  BELOW W     W=1000000 -> (900000, 1000000)  BELOW W
```

It is never LATE (the clause the brief asked about holds) and never earlier than the harness itself, since a
PreCompact only fires at W — but in those bands the hook can never defer, and every compaction logs
`allow-ceiling`. That feeds `--summary`'s drop metric ("the share of allowed auto compactions the ceiling forced")
with 100% by construction, i.e. it argues for dropping the hook for a reason unrelated to its value. The live
setting (`modelSettings["claude-opus-5-5"].autoCompactWindow = 300000` in `~/.claude/settings.json`) gives
ceiling 450k against L = 1M — unaffected. **Fix:** log `ceiling_by: "below-W"` (or exclude such rows from the
share) and state the bands in the docstring.

## The brief's specific questions

- **Window table vs models in use.** The transcript records `claude-opus-5-5` (no `[1m]` suffix); the coordinator's
  peak of 966,673 shows a ≥1M window, so L = 1M for W = 300k is right. A Sonnet teammate has no
  `modelSettings` entry and no top-level `autoCompactWindow`, so `window()` raises CannotRun → `allow-cannot-run`
  (fails open, never defers). The table is unmeasured per model, as stated; I found no model in use it gets wrong.
- **Shared `CLAUDE_CODE_BRIDGE_SESSION_ID`.** Confirmed in my own env: `session_01Fqufju9EfJUZ74r5EX25ff`, the same
  id as the coordinator's live sentinel. Sized: an Opus teammate whose payload cwd is the main checkout (the
  transcript's dominant cwd) reads the coordinator's plan as its own while it is armed and unpaused, and defers
  300k → 450k. Today the sentinel is `paused:`, so the impact is 0; bounded by the ceiling. Soundly declined as a
  `begin-plan.py` change.
- **Missing `session:` field** → armed (ran: `'plan: x\n'` → True; `'session: \n'` → True). Documented and
  consistent with `begin-plan.py:411`, which writes the field whenever the id is known.
- **Lease.** A still-running agent past 3 h is wrongly closed — by design, bounded, and the measured longest was
  ~1.2 h. A finished agent wrongly kept open: R2-1. Agent ids in the transcript are hex (`afc92b3d3a4e0049d`), so
  `agentId: (\w+)` does not truncate them.
- **O_NONBLOCK / regular-file.** No escaping raise found: a log FIFO with no reader gives ENXIO (seen in the
  self-test's stderr) and is caught; a 5,000-char cwd makes `log_path` return None on Python 3.14 and
  `evaluate` returns `allow-cannot-run`; anything else that raises in `hook()` exits non-zero and the shell wrapper
  runs the snapshot itself and exits 0.

## Reverts (throwaway copy; each turned the suite red via the case naming it)

| Reverted | Result |
|---|---|
| `paused` → not armed | 75/77 — both PAUSED cases red |
| foreign `session:` → not armed | 75/77 — both ANOTHER-session cases red |
| `if "agent launched" in text` | 76/77 — the completed-foreground-footer case red |
| `ACTIVITY_TYPES` → assistant only | 74/77 — the three C4 cases red |
| lease clause | red (4 cases) |

## Summary

No BLOCKER under Q4c; R2-1..R2-3 are Low, each with a constructed input above, and each fix-induced. R2-2's log
half is pre-existing. The safety properties hold; the "no new defect" clause does not.

VERDICT: NOT CONVERGED
