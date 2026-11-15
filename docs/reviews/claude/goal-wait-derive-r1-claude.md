Reviewed head: 526d148ad9b701ea1edafdd3a19ec4fa70c4121e

# goal-wait-derive (backlog #650, PR #592) — review round 1, Claude half

Adversarial mandate: try to refute the seven claims. Diff: `git diff origin/master...HEAD`.

## What was run

- `python3 scripts/goal-tree.py --self-test` — 524/524 passed.
- `python3 scripts/goal-tree.py --owed-idle` against the real main-checkout log (17.4 MB, 297 lines): one
  line, `none — every Owed item has a reason (… 2026-11-15 05:35)`, 0.35 s. All five real Owed items carry a
  recorded wait, so the real data exercises none of the new derivation.
- `named_prerequisites` over the real ledger (10 entries): one hit, `subdivide-tooling` → PR #442. That is the
  motivating backlog #511 case, and it derives correctly.
- Every one of the 27 new or rebound mutations in `scripts/mutations/goal-tree.json` applied to a copy and the
  self-test run: all 27 turn their `expect` cases red. The copy's baseline has 3 unrelated failures (Ask-tray
  cases that need the repo path); none of them is an `expect` case, so no kill is ambient.
- Probes driving `derive`, `owed_reason`, `idle_days`, `owed_idle_lines`, `owed_idle_report` and `main
  --owed-idle` with my own inputs (below).

## Findings

### F1 — MAJOR — a RECORDED wait whose named PR has finished still says "waits for", and the session block says "none"

`scripts/goal-tree.py:487-495` (`owed_reason`): a recorded `waits` is shown as-is and returns `(waits, None)`
when no `after …` prerequisite is named; its own refs are never read. `scripts/goal-tree.py:2216-2229`
(`owed_idle_lines`) then lists nothing.

Breaking input: ledger entry `{"id": "sub", "what": "work on backlog #11", "waits": "PR #442", "at": "11-10
09:00"}` on thread `- fix · backlog #11 · split it` with PR #442 merged 10-30. Page: `waits for: PR #442`.
Session block: `=== OWED AND IDLE: none — every Owed item has a reason … ===`. Same with the thread-line form
`- fix · backlog #11 · split it · waits on PR #442`.

This is the motivating failure of backlog #650 in a different spelling: backlog #511 sat for two weeks after
PR #442 merged. A recorded `waits on PR #N` / `--waits "PR #N"` is the MOST explicit statement of a
prerequisite there is, and it is exactly the one that now goes stale silently, while claim 4's alarm fires only
when nothing is recorded. Fix shape: read the refs in a recorded wait too (any `PR #N` / `backlog #N`, not only
after `after`), and when every ref it names is done, add the `blocker done` alarm beside the recorded text (still
shown first, claim 5 intact).

### F2 — MINOR — a PR closed WITHOUT merging, and a superseded/withdrawn row, read "blocker done … not started"

`scripts/goal-tree.py:434-435` and `:440`. Breaking input: `start only after PR #460`, PR #460 CLOSED unmerged
→ session line `backlog #11 — blocker done 11-02 (PR #460), not started`. A row with fate `superseded by backlog
#41` → `blocker done, date not read (backlog #40), not started`. The spec row says merged/closed → done, so
this matches the spec; but the line tells the owner the work can start when its prerequisite was ABANDONED (or
moved to another row). Suggest distinct wording — `blocker closed unmerged <mm-dd> (PR #N)` / `blocker
superseded (backlog #N)` — still in the alarm style, since either way the item needs a decision.

### F3 — MINOR — a ledger time one minute after the snapshot's reads as "idle 364 days"

`scripts/goal-tree.py:463-478` (`idle_days`). `idle_days("11-15 09:01", "2026-11-15 09:00")` → 364. `main`
sets `now` before `collect` reads the ledger, after several seconds of `gh` calls, so an `--add` landing in that
window stores a `since` one minute past `at`, and the year-back rule turns it into a year. Rare, but the output
is a confident false alarm. Move the year back only when the gap is large (say over a day); a near-future time is
0 days.

### F4 — MINOR — the idle count is measured to the snapshot's FIRST-logged time, not to now

`owed_idle_lines` uses `snap["at"]` (`:2220`, via `owed_reason(x, snap.get("at"))`), and `append_if_changed`
(`:1301-1311`) logs a snapshot only when its fingerprint changes. A tree unchanged for five days keeps an `at`
five days old, so the session block says `idle 0 days` for an item idle five. The header names the snapshot
time, but the number is the one a reader scans. In `--owed-idle`, compute days against the session's clock (the
mode already reads no network; the clock is free).

### F5 — MINOR — a partly unread ledger reads "none — every Owed item has a reason"

`owed_idle_lines` (`:2228-2229`) never consults `snap["ledger_problems"]`. Breaking input: `derive(…,
ledger_problems=["3 line(s) not parsed"])` with no parsable entries → `none — every Owed item has a reason`.
(A wholly unread ledger cannot reach the log: `append_if_changed` refuses a snapshot with `cannot`, so that
variant is unreachable — verified, not a finding.) The IN FLIGHT block prints the ledger problems separately, so
this is MINOR; the `none` line should still say `none of the N entries read (K lines not read)`.

### F6 — MINOR — the hook prints CANNOT RUN twice when the main checkout cannot be found

`scripts/goal-tree.py:2738-2741` prints its own CANNOT RUN and returns 2; `.claude/hooks/session-state.sh:20`
`|| echo` then prints a second. Reproduced outside a git repo:
`=== OWED AND IDLE: CANNOT RUN — the log lives in the MAIN checkout, and git rev-parse … (treat as NOT RUN) ===`
followed by `=== OWED AND IDLE: CANNOT RUN — goal-tree.py exited 2 (treat as NOT RUN) ===`. Return a code the
hook does not echo for (or have the hook echo only on a code other than 2).

### F7 — MINOR — "no parse of the whole log" reads the whole log into memory

`scripts/goal-tree.py:2242`: `log_path.read_bytes()` loads all 17.4 MB on every session start to keep one line;
the log grows about 100 KB per snapshot without bound. 0.35 s today. The docstring's "its last line only" is true
of the parse, not the read; a seek from the end (read the last few hundred KB, widen if no newline) bounds it.

## Claims checked and not refuted

1. Thread text and ledger `what`/`on_done` both feed the matcher (thread line `split it; start only after PR
   #442` → `blocker done 10-30`); the item's own refs are excluded for threads. Matcher edges: `after PR #442's`,
   `after\nPR #442`, `after pr #442` match; `after PR#442`, `hereafter`, `after: PR #442` do not — consistent with
   the stated narrow rule.
3. `notfound` and `cannot` PR states, and an unread backlog, all render `(state not read)`.
4. Holds for items with nothing recorded and nothing named (but see F1, F3, F4).
5. Recorded wait precedes the derived one, beside open and finished prerequisites.
6. Bounded at 6 lines of ≤170 chars plus a count; a missing, empty-tailed or broken log is CANNOT READ. Hostile
   ids/whats with newlines and `=== END …` are flattened by `_one_line` (probed).
7. `.waits` no longer `nowrap`, `overflow-wrap:anywhere` (which also lowers min-content), `min-width:0` on the
   digest `ul`/`li`.

VERDICT: NOT CONVERGED
