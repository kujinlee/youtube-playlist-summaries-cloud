Reviewed head: fd1afef11b2afd980bbf27e18048f87bb30fa3cf

# goal-wait-derive (backlog #650, PR #592) — review round 4, Claude half

Adversarial mandate: break the Phase 6 redesign (`git diff 349ae323..fd1afef1`). An Owed item's prerequisite is
DECLARED in the ledger entry's `after` field, and the prose matcher and recorded-wait resolver are deleted. Read first:
`docs/reviews/coordinator/architecture-review-2026-11-15-goal-wait-derive.md` and
`docs/reviews/coordinator/goal-wait-derive-r3-coordinator.md`. This is round 4, so everything below BLOCKER is FILED
(`docs/review-method.md` §0 Q4c).

**No BLOCKER.** 4 findings, all MINOR, none fix-induced in the redesigned reader.

## What was run (at fd1afef1)

| Check | Result line |
|---|---|
| `python3 scripts/goal-tree.py --self-test` | `536/536 self-test cases passed`, rc 0 |
| `python3 scripts/session-state.py --self-test` | `144/144 self-test cases passed`, rc 0 |
| All-manifest anchor resolve: `check-plan-code.anchor_problems` (the harness's own rule) over every `scripts/mutations/*.json` | `manifests=96 entries=5232 problems=0` |
| Every `expect` in `goal-tree.json` (438) and `session-state.json` (127) equals exactly one case name the self-test ran (the names were captured by running the suite) | 0 problems in each |
| Pins in `scripts/mutations/expected_mutations.py` | `goal-tree.py: 438`, `session-state.py: 127`, both equal to the manifests |
| 10 of the new mutations, run by hand on an exec'd copy: the five `session-state.json` entries for `--add`/`after`, and five `goal-tree.json` Phase 6 entries (absent `after`, damaged element dropped, prose re-read, thread ignores declarations, prose wait expires) | each turns red, and every case its `expect` names is among the failures |
| 60 concurrent writers (30 `ledger_add`, 30 `ledger_set_after` on one entry, 12 processes) | 31 entries, 0 damaged lines, `base` keeps `at` `11-01 00:00` and holds one valid `after` |
| `grep` for `named_prerequisites`, `wait_blockers`, `AFTER_RE`, `_CLAUSE_RE`, `_NEGATED_RE`, `_WAIT_JOINERS` outside `docs/reviews/` | one hit, `scripts/goal-tree.py:3160`, the prose-invariance walker's sentinel key. It is meant to be there: it turns the case red if the key comes back. |

### Question 1: a wrong wait reason, or a hidden idle item

I drove `_declared_blockers` and `owed_reason` directly, with a hand-built `src` (now `2026-11-15 10:00`, since
`11-05 13:42`):

| `after` | Sources | (waits, alarm, idle) | Verdict |
|---|---|---|---|
| `PR #442` merged | normal | `None`, `blocker done 10-30 (PR #442), not started`, `True` | correct |
| `PR #451` open | normal | `PR #451 (open)`, `None`, `False` | correct |
| `PR #460` closed unmerged | normal | `None`, `prerequisite PR #460 closed unmerged — re-plan`, `True` | correct |
| `backlog #70` ✅, `#71` open, `#72` withdrawn | normal | done (date not read) / `(open)` / `withdrawn — re-plan` | correct |
| `PR #99999`, `backlog #99999` (no such ref) | normal | `… (state not read)`, `None`, `False` | **F2** |
| `[]` | normal | `None`, `no reason recorded — idle 9 days`, `True` | correct |
| no `after` key (written before the field existed) | normal | the same as `[]` | correct: it fails toward showing the item |
| `PR #442` merged + `PR #451` open | normal | `PR #451 (open)`, **`blocker done 10-30 (PR #442), not started`**, `False` | **F1** |
| `PR #451`, `PR #460` | `errors.gh` set | `(state not read)`, not idle | correct: it never says "ready" |
| `PR #442` | `errors.gh` set, git read | done | correct: master's subjects decide `merged` |
| `PR #442`, `PR #451` | `merged_by_pr=None`, `errors.merged` set | `(state not read)`, not idle | correct |
| `backlog #70` | backlog unread (`fates=None`) | `(state not read)`, not idle | correct |

### Question 2: input refusal and the ledger file

`parse_after` refuses `''`, `' none'`, `'None'`, `'PR #1,PR #2'`, `'pr #1'`, `'PR #1 '`, `'#1'`, `'PR #-1'` and
`'PR #1;backlog #2'`. `'PR #1, PR #1'` passes the parse and is refused by `_after_list`, before the lock. `--set-after`
validates inside the lock and writes nothing on a refusal. A self-test case asserts that the ledger stays
byte-identical. `_write` is a temp file plus `os.replace`, under the sidecar `flock`. The concurrency probe above lost
no write. Arabic-Indic digits (`PR #٤٤٢`) are read and normalised to `PR #442` by `int()`. That is harmless.

### Question 3: references to the deleted behaviour

None remain in the docs, the glossary (`CONTEXT.md` gains Owed, Prerequisite and Wait, consistent with the code), the
command doc, the case names or the mutation anchors. There are no `--add` callers without `--after` in scripts or
hooks. Older `--add` forms survive only in history (`docs/dashboard-entries.md:19226`, backlog rows).

### Question 4: the numbers

The code-side numbers hold: `536 cases`, `144 cases`, the 14 sentences in `_PROSE`, the three carrier entries
(`t1`/`p1`/`l1`), and the pins 438 and 127. The prose numbers about the live corpus do not all hold. See F3.

## Findings

### F1 — MINOR — the alarm says "blocker done, not started" while another declared prerequisite is still open

`scripts/goal-tree.py:550` (`owed_reason`: every finished blocker becomes an alarm, whether or not `pending` is empty).

- **Breaking input:** `after: ["PR #442", "PR #451"]`, with PR #442 merged and PR #451 open.
- **Wrong output:** the row reads `waits for: PR #451 (open)` and also, in the alarm style,
  `blocker done 10-30 (PR #442), not started`.
- **Why it is wrong:** the redesign makes a declared list mean ALL refs must finish (architecture review, Recommendation 3).
  The item cannot start, but the alarm says the blocker is done and the work has not started. `idle` is `False`, so the
  session-start block is correct. Only the page row is wrong.
- **Fix:** while `pending` is non-empty, render a `done` blocker as neutral detail (`PR #442 done 10-30`) inside `waits`.
  Keep an `abandoned` one as an alarm, because a re-plan is owed whatever else is open.
- **fix_induced: false.** This is the round-1 Codex 5 rule ("a listed item shows EVERY reason"). The redesign only
  made all-of the declared meaning.

### F2 — MINOR — a ref that does not exist reads `state not read` forever, so a typo hides an idle item

`scripts/goal-tree.py:462` (a backlog row absent from a fully read `fates` gives `unread`) and `:666` (`notfound` maps
to `unread` at `:460`). There is no existence check at write time either: `scripts/session-state.py:360` `parse_after`
checks grammar only.

- **Breaking input:** `session-state.py --set-after subdivide-tooling 'backlog #6500'` (a typo for #650), or
  `--after 'PR #99999'`.
- **Wrong output:** `waits for: backlog #6500 (state not read)`. The item is a live wait forever, never idle, and never
  listed at session start. The label is also false. `derive_thread`'s own comment says `fates` "holds EVERY Items row …
  so a row absent from it does not exist". The row was read and is absent.
- **Fix:** when `fates` and `closed_rows` were both read and `n not in fates`, return a distinct state, `missing`. Render
  it as an alarm (`prerequisite backlog #N does not exist — fix the declaration`) and count it as not pending. A PR
  number above the newest PR gh listed can take the same path. `notfound` below that bound stays `unread`.
  Optionally, `--add`/`--set-after` could warn when the backlog file has no such row.
- **fix_induced: false.** `_blocker` is unchanged by this round. The redesign makes the path more likely, because a ref
  is now typed rather than copied out of a sentence.

### F3 — MINOR — two live-corpus counts in the new prose do not hold

- `docs/reviews/coordinator/architecture-review-2026-11-15-goal-wait-derive.md:176` says "6 thread lines carry
  `· waits on …`", and backlog #653 (`docs/backlog.md:631`) uses it as its trigger base, "0 of 6".
  - **Measured:** `parse_thread_line` over `docs/goal-threads.md` finds **4** thread lines with a `waits` field
    (backlog #384, backlog #444, backlog #512, PR #392).
  - The 6 is the `grep -n "waits on"` line count. It includes the grammar bullet at line 24 and line 186, whose
    `; waits on` sits inside the `what` text.
- Backlog #652 (`docs/backlog.md:630`) says "3 of the 8 recorded waits **in the ledger** are a date (`the 11-20 weekly
  reset`, `the weekly reset (Fri 11-06 02:00)` twice)".
  - **Measured:** the live ledger, read-only at 10:35, holds 10 entries and **3** recorded waits, and only **1** of
    them carries a date (11-20). The 11-06 wait is the backlog #512 THREAD line, and it appears once.
  - The row's own headline example therefore lives in `docs/goal-threads.md`, not in the ledger, and its proposed fix
    (`--add --until`) would not reach it.
- **Fix:** restate both with a named set and the command that produced it: "4 thread lines (parse_thread_line)", "3 of
  7 recorded waits (3 ledger + 4 thread lines); 2 carry a date". Note in #652 that the 11-06 example is a thread line,
  so `--until` alone does not cover it.
- **fix_induced: false.**

### F4 — MINOR — the dashboard entry over-claims what the session-start block lists

`docs/dashboard-entries.md:20753`: "Each new session opens with a short list of these, and of items whose blocker is
done".

- **Breaking input:** `after: ["PR #442"]` (merged) plus any recorded `waits`. This is the real `subdivide-tooling`
  entry once the §4 migration runs, because its `waits` is non-empty.
- **Wrong output:** the item is NOT listed at session start (`idle` is `False`, because a recorded wait is a live reason
  forever). The goal-tree self-test pins that count at 0 (`idle_of([ent("x", after=["PR #442"], waits="the owner")])`).
  The page row still shows the alarm.
- So the motivating case, as the owner will see it after the migration, is on the page but not in the session-start
  list. The architecture review's §3 replay ("is listed at session start") assumes an entry with no recorded wait, and
  is tagged **[I]**.
- **Fix:** reword to "…and of items whose blocker is done and that carry no other recorded reason". Alternatively,
  decide that a finished declared prerequisite lists the item even beside a prose wait. That is a design change: file
  it rather than fold it.
- **fix_induced: false.**

## Bound of this review

- Mutations: 10 of the new or rebound entries were run by hand, on an exec'd copy of the source with the edit applied.
  This is not the harness's `--mutate`. The other entries were checked for anchor and `expect` binding only.
- The live ledger was read, never written. The two §4 `--set-after` migrations were not run.
- `--owed-idle` against the main checkout's snapshot log was not re-run. The log holds snapshots built by master's
  code, so it cannot exercise this branch until after the merge.

VERDICT: CONVERGED
