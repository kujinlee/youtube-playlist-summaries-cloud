Reviewed head: a329000287b74c34d5cd684baca8e21c0791beaf

# PR #606 — Running now sees a building worktree (backlog #672) — round 1, Claude half

- **Subject:** branch `running-now-worktree`, head `a3290002`, base `11d0568d` (`git diff 11d0568d..a3290002`)
- **Reviewer:** Claude (adversarial, `superpowers:requesting-code-review` standard), round 1, run concurrently with Codex
- **Fix-induced:** none. This is round 1, so no finding can come from an earlier round's fix.

## What was run

| Check | Result |
|---|---|
| `goal-tree.py --self-test` | 544/544 |
| `session-state.py --self-test` | 161/161 |
| `agent-watchdog.py --self-test` | 79/79 |
| `check-shipping-sets.py --self-test` | 140/140 (68 s) |
| The PR's own #672 mutations, on a `git archive` copy (manifests filtered to the `#672` entries; the 7+4 re-bound pre-existing ones were NOT run) | goal-tree 16/16, session-state 7/7, agent-watchdog 3/3 killed, each attributed to the case it names |
| Four hand mutants on the copy (listed under F3) | **4 survivors** |
| `measure_worktrees` on a real linked worktree (a `.git` FILE) and on the main checkout | 0.05 s and 1.35 s; both read |

The falsifiers in row 672 are what the cases assert. FALSIFIER 1 checks `nothing running` and `not started` are absent at +5 min. FALSIFIER 2 checks the item is not under Running now at +180 min. The 29/30 boundary is one case over one worktree. The cases build their worktrees as real directories and measure them with the watchdog's own function, against a fixed instant. I found no case that passes for an ambient reason.

## Findings

### F1 — MAJOR — the session-start *Owed and idle* block judges a build against the SNAPSHOT's time, not the time the report runs, so a dead builder hides its item for as long as no new snapshot is logged

`scripts/goal-tree.py` `owed_idle_lines` → `agenda_digest(snap, …)` → `_builds([u], snap.get("at"))` → `worktree_build(wt, at)`. The `running` flag is decided at the snapshot's `at`. `owed_reason(x, now)` counts idle days to `now`, as r1 Claude F4 requires. `owed_idle_lines` skips every item with `x["running"]` before it ever reaches `owed_reason`.

**Measured** on a copy. Inputs: a ledger entry (goal `g`, `after: PR #442` merged) that declares a worktree changed at `2026-11-20 10:00`, and a snapshot derived at `2026-11-20 10:05`.

| `now` given to `owed_idle_lines` | Output |
|---|---|
| `2026-11-20 10:05` | `OWED AND IDLE: none — every Owed item has a reason` (correct) |
| `2026-11-21 10:05` | the same `none — every Owed item has a reason` |
| `2026-11-27 10:05` | the same `none — every Owed item has a reason` |
| the same entry with no worktree declared, `now` = `2026-11-21 10:05` | `hse-d — blocker done 10-30 (PR #442), not started` (listed) |

So this PR takes an item the block used to list and hides it, and the block then says the false line *every Owed item has a reason*. The block is a SessionStart hook (`--owed-idle`), and it reads the newest LOGGED snapshot. That snapshot is only logged on a merge, a threads edit or a Refresh (`regen-pages.py:pages_for`). The live log has gaps of more than 2 days: `2026-11-17 10:45` → `2026-11-20 01:04`. A build signal has a 30-minute window, so judging it against a snapshot that old is a clock-source mixup.

An open PR in a stale snapshot has the same staleness, so that part of the problem is older than this PR. The difference is that a PR stays open across days, while a build reading is built to expire in 30 minutes.

**Fix:** in `owed_idle_lines`, judge builds against `now`. The entry already carries `worktree.changed`, so `worktree_build(wt, now)` works. Another option: treat an item as running only when `now − at < QUIET_MIN`. Add a case over one snapshot at two `now` values (+5 min, +1 day).

### F2 — MINOR — a worktree that was NOT READ still says `not started`, which is the false claim row 672 exists to remove

`owed_reason`: `started = any(w["state"] in ("building", "quiet", "ahead") …)`. `unread` and `gone` are left out, so `_finished(b, False)` still appends `, not started`.

**Measured:** builds `[{"unread": "CannotRun: x"}]` with a done blocker → `'blocker done 10-30 (PR #442), not started; worktree NOT READ (CannotRun: x)'`, and `idle=True`, so the item is listed at session start with that text. The source was not read, so `not started` is an assertion the page cannot make.

`gone` is arguable: a removed worktree most often means the work was finished and cleaned up, not that it never started. **Fix:** for `unread`, drop `not started` (an unread source makes no claim). For `gone`, consider dropping it too.

### F3 — MINOR — four behaviours the PR states have no witness (hand mutants, all survived 544/544)

| Hand mutant | Behaviour it breaks | Result |
|---|---|---|
| `if mins < -1:` → `if mins < 0:` | the one-minute tolerance that the `worktree_build` docstring calls load-bearing ("one minute ahead is this moment"). The only `ahead` case uses −10 min. | survived |
| `started` without `"ahead"` | the `ahead` item's `not started` | survived |
| `_run_if_building` without `and not x.get("waits")` | "a declared wait holds it as Owed". It is redundant on every path measured: `_fold_item` re-gates `running` on waits, and every consumer goes through `agenda_now_items`. So it is not a live defect, but no case states the rule for a building item. | survived |
| `_ledger_worktree` fallback `{"unread": "not measured in this snapshot"}` → a `changed` stamp | a declared path with no reading in the sources | survived |

**Fix:** add a case for the −1/−2 boundary, an `ahead` item with a done blocker, a building item with a declared wait staying Owed, and a source with no `worktrees` key reading NOT READ. Each can be one case over two inputs.

### F4 — MINOR — `session-state.py`'s count note says `os.path.abspath` cannot be witnessed; it can

`scripts/mutations/expected_mutations.py`, the session-state comment says: "Not mutated: `os.path.abspath` (every caller passes an absolute path, so no case can witness it)". A case that calls `main(["--add", …, "--worktree", "rel"])` after `chdir` into a temp dir would witness it.

Without abspath, the relative path is stored as given. The served goal tree is built in `regen-pages.py`'s private clone, with a different cwd, so it would read `worktree gone` for a worktree that exists. So the dropped line is load-bearing, and the stated reason for not mutating it is wrong.

### F5 — MINOR — the snapshot's clock is read BEFORE `collect`'s network calls, so a slow fetch turns an active builder into `ahead` (Owed)

`main`: `now = … datetime.now()` comes before `collect(root, run)`. `collect` runs `git fetch` (60 s timeout) and three `gh` calls (30 s each), and only then runs `measure_worktrees`. `--record-agenda` and `--snapshot` together call `collect` twice.

**Measured** (pure part): `worktree_build({"changed": "…10:02"}, "…10:00")` → `ahead` → Owed with `worktree change stamped 2 min AFTER this snapshot`. A builder writing continuously crosses that line once collect runs past about 61 s. Normal runs take about 7 s (explainer-serve's measurement), and the Refresh path kills a run at 60 s. So this is inferred to be rare, and the page does say so rather than hide it.

**Fix:** read the measure's reference clock after the measure. Or treat a change after `at` as evidence of activity (building) and keep `ahead` only for stamps far in the future.

### F6 — MINOR — `--worktree` accepts the main checkout, which the watchdog's own docstring says never to watch

`declared_worktree` checks only `isdir`. The `agent-watchdog.py` docstring says: "A worktree nested inside a watched directory counts as that directory's activity, so watch builder worktrees, not the main checkout". Hooks also write under `.claude/` on every turn.

**Measured:** `measure_worktrees` on the main checkout reads (1.35 s; it walks every nested `.claude/worktrees/*`). Any entry declared with `--worktree .` from the main session would read `building` permanently. **Fix:** refuse a path equal to `session-state.main_checkout`, or one that contains another git worktree.

### Notes (not findings)

- **Snapshot-log growth.** `fingerprint` includes `worktree.changed`, so every regen during a build logs a new snapshot. The newest is about 118 KB, and the log is 20.8 MB over 328 lines today. Regen runs only on a merge, a threads edit or a Refresh, so the growth is bounded by those events. Not filed.
- **The index is rewritten by others' `git status`.** A reviewer's or orchestrator's `git status` in a finished builder's worktree rewrites `index` and reads as `building` for 30 minutes. This is inherited from the watchdog and stated in its docstring. In practice the PR is usually open then anyway.
- **`os.path.isdir` returns False on a permission error**, so `measure_worktrees` says `gone` rather than NOT READ for an unsearchable parent. Inferred, rare.

VERDICT: NOT CONVERGED
