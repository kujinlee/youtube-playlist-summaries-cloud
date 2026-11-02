# Round 3 — guards-cannot-run — claude

Reviewer: Claude (refuting mandate), against `c3f820bc` (branch `guards-cannot-run`, PR #440). The fold diff
`ca757a7b..c3f820bc` was read first. Nothing in the worktree was edited. Every run below used COPIES of the
scripts (`root-branch` = the worktree's `scripts/`, `root-master` = `git archive` of the merge base `b6c3c0bb`), so
no journal or warn log was written into either checkout.

**The bet under test:** "round 3 finds no unreadable input, through a real entry point, that yields rc 0, a WARN, a
traceback or a hang." **It is LOST, by finding 1.** That input is not in the redesigned reader. It is in a second
payload field, which the reader never sees, one step beside `transcript_path`.

## Findings

### 1. Major — the payload's `session_id` is a PATH, read outside `bounded_read`: a FIFO hangs the registered Stop hook, deep JSON or a NUL byte gives a traceback with rc 1

- **Where:** `scripts/check-banner-armed.py:1271` (`_read_journal`: `json.loads((JOURNAL_DIR / f"{session_id}.json").read_text())`, which catches only `(OSError, ValueError, TypeError)`), reached unconditionally from `run_decide` at `:1356`. The write side is `_write_journal`, whose cleanup `tmp.unlink(missing_ok=True)` at `:1296` sits inside an `except` and catches only `OSError`.
- **Why the reader misses it:** `bounded_read.stop_transcript` validates `transcript_path` only. `session_id` comes out of the same untrusted payload. `pathlib` drops `JOURNAL_DIR` when the right-hand operand is absolute, and does not normalise `..`, so the payload chooses which file is read. That read is a blocking `read_text()` with no regular-file check and no byte bound. It is the r2 X4 / X2 / r1 X1 class, on the second path the payload names.
- **Inputs, all with a valid transcript (`t-good.jsonl`, four records):**
  - (a) `session_id` = `<dir>/sess-fifo`, where `<dir>/sess-fifo.json` is a FIFO with no writer;
  - (b) `session_id` = `<dir>/sess-deep`, where `<dir>/sess-deep.json` holds `"[" * 200000 + "]" * 200000`;
  - (c) `session_id` = `"a\u0000b"`.
- **Evidence, RAN:**

  | Input | `check-banner-armed.py --decide`, branch | same, master | `run-hook.sh block-idle-stop.sh` (branch copy, fake checkout) |
  |---|---|---|---|
  | (a) FIFO | **HUNG** (killed at 15 s) | HUNG (10 s) | **HUNG** (killed at 25 s) |
  | (b) deep | **rc 1, Traceback** `RecursionError` | rc 1, Traceback | rc 1, 1 traceback |
  | (c) NUL | **rc 1, Traceback** `ValueError: unlink: embedded null character in path` (chained from `write_text`'s `embedded null byte`) | rc 1, Traceback | rc 1, traceback |

  The other three guards answered (a)–(c) normally: closing-table 0, transcript-references 1 (a real bare `#291`), ci-watched 0. Only banner-armed uses `session_id` as a path.
- **Not caught by the suite:** every payload in `bounded_read.hostile_payloads` carries `session_id: "s"` or none, so no hostile case varies this field.
- **Fix-induced:** no. Master behaves identically. It still breaks the bet as written ("through a real entry point … a traceback or a hang").
- **Component:** payload-path (banner-armed's journal).
- **Fix shape:**
  - Refuse a `session_id` that is not one safe path segment, in the shared reader, so all three guards get it (a CANNOT RUN reason, with the payload object still returned).
  - Read the journal through `bounded_read.read_file` + `parse_json`.
  - Widen the cleanup catch in `_write_journal`.
  - Add (a)–(c) to `hostile_payloads`.

### 2. Major — a record whose `message` is not an object is SKIPPED mid-transcript, and the verdict flips WARN → QUIET

- **Where:** `scripts/check-banner-armed.py:291` (`_turn_records`), borrowed by all three transcript guards through `transcript_records`.
- **Input:** the firing transcript (`user "go"`, `assistant "see #291"`, `user "again"`, `assistant "x"`), with the JUDGED assistant record's `message` replaced by the string `"see #291"` (also tried: `5`).
- **Evidence, RAN:**
  - `check-transcript-references --decide`: control **rc 1**, mutated **rc 0**, silent, on branch and master alike.
  - The same file with the LIVE user record's `message` a string (so the turn boundary is lost): rc 0 on all three guards.
- **What the fold says:** this is the r2 X1 shape that the fold reverted for undecodable bytes, a record the guard cannot read, dropped, and rc 0. Here it sits one layer up, in the turn filter, which `bounded_read`'s docstring carves out explicitly ("it does not decide what a record MEANS").
- **Cost of refusing it, MEASURED:** over all **618** real transcripts under `~/.claude/projects/*/*.jsonl`, **0** records carry a `message` that is present and not an object. Refusing it (CANNOT RUN, as `parse_jsonl` now refuses a non-object record) changes no real verdict.
- **Fix-induced:** no. The filter predates PR #440 (backlog #152 r1), and master gives the same 1 → 0. It is still the bet's named failure observation.
- **Component:** transcript-read (turn filter).

### 3. Minor — three surviving mutants: the stdin bound's VALUES and its exact-cap edge are unpinned

My own mutants, applied to a copy of `scripts/bounded_read.py` and run against all six changed suites (`bounded_read`, transcript-references, banner-armed, closing-table, handoff-path, ci-watched). Each survived, all six green:

- (a) `MAX_STDIN = 4 * 1024` (from 1 MiB). With it, any real payload over 4 KiB is CANNOT RUN in the three transcript guards. `MAX_FILE` has a pinning case ("the file bound is 256 MiB"); `MAX_STDIN` has none.
- (b) `STDIN_WAIT = 0.05` (from 2.0). Every CLI case writes its stdin at once, so nothing exercises the default wait.
- (c) In `read_stream`'s descriptor path, `if total > cap` → `if total >= cap`: a payload of exactly `cap` bytes is refused. `read_file` has an exact-`cap` case; `read_stream` does not, on either path. (`read_stream`'s own off-by-one at exactly 1 MiB was checked through the real CLIs: 1,048,576 bytes is read and 1,048,577 is CANNOT RUN. The code is correct; only the case is missing.)

Also unmeasured: the docstring's "a Stop payload is a few hundred bytes" (`bounded_read.py:28`) is stated, not measured. The largest assistant text block in the 618 transcripts is 8,489 bytes, so 1 MiB has ample margin if the harness ever adds message text to the payload. What is missing is a pinning case, not a different value.

- **Fix-induced:** yes (new code). **Component:** mutation-manifest (`bounded_read`).

### 4. Minor — the guard-level FIFO cases pass for an AMBIENT reason

- **Mutant:** drop the `S_ISREG` check in `read_file` (`if not stat.S_ISREG(...)` → `if False`), keeping `O_NONBLOCK`.
- **Result, RAN:** only `bounded_read`'s two unit cases go red. These stay green:
  - all three guards' "every hostile payload … FIFO … no hang" CLI cases;
  - `check-handoff-path`'s "a FIFO SKILL.md is CANNOT RUN through the plain CLI, never a hang".
- **Why:** a non-blocking read of a writer-less FIFO returns `b""`. The guards then refuse it as "no record in the transcript" or "SKILL.md is empty". So the right outcome comes from a different refusal than the one the case names.
- **Not a coverage loss:** the unit case in `bounded_read` pins the check. But under that mutant a character device (`/dev/zero`) as `transcript_path` would be read to the 256 MiB cap before refusal, and the guard-level case names cannot see it.
- **Cheapest repair:** a FIFO-with-a-writer, or `/dev/zero`, in `hostile_payloads`. Either one distinguishes "refused as non-regular" from "read as empty".
- **Fix-induced:** yes. **Component:** mutation-manifest / hostile-payload fixture.

### 5. Minor — the registered hook's own `INPUT=$(cat)` is unbounded, so its stdin bound is not on the hook path

- **Where:** `.claude/hooks/block-idle-stop.sh:49`.
- **Evidence, RAN:** a complete, valid payload with stdin held open: the registered hook was **still running at 12 s**, and exited 1 at 12.8 s only once stdin closed. `read_stream`'s byte and time bounds protect each guard's direct `--decide`; through the hook, `cat` reads without either bound, and every guard then gets a closed `printf` pipe.
- **Fix-induced:** no. It is pre-existing, and Claude Code closes the pipe, which `check-ci-watched`'s own `payload_from` docstring already records.
- **Why it is here:** a statement that the redesign makes the Stop hook hang-proof would be true of the guards and not of the hook. The PR text should not imply it.
- **Component:** payload-path (hook wrapper).

### 6. Minor — the three older readers are a duplicate rule acknowledged only in prose, not filed

- **Readers:** `session-state._read_whole` (`scripts/session-state.py:212`), `compaction-state._open_regular` (`scripts/compaction-state.py:334`) and `read_in` (`:539`).
- **What they do:** each already implements the rule correctly: `O_NONBLOCK`, `fstat` on the descriptor, `S_ISREG`, a cap, and `O_NOFOLLOW` where it matters.
- **Callers:** SessionStart and PreCompact hooks, not the five guards' Stop/PreToolUse input. Leaving them is **not a defect in this PR**; it is outside #357 / #331(a).
- **Not filed:** `bounded_read.py:44-46` says they are "the same rule in three more places", but `grep` over `docs/backlog.md` for `bounded_read`, `_read_whole`, `_open_regular` and `read_in` finds **0** rows. A discovered step that lives only in a docstring is lost. File it as a follow-up (migrate or explicitly exempt). Note that `O_NOFOLLOW` is a real difference: `bounded_read` follows symlinks, as a `transcript_path` may need.
- **Fix-induced:** no (bookkeeping). **Component:** backlog.

## What held (each RAN)

- **Hostile neighbours through every real `--decide` (four guards), branch copy.** Each was CANNOT RUN (rc 2, no traceback, no hang), read correctly, or, for ci-watched, a lost session column only:
  - **Valid input, read correctly:**
    - CRLF records;
    - a payload with a trailing CRLF;
    - a final record with no newline;
    - a torn final record after whole ones (dropped, verdict unchanged: transcript-references still 1);
    - a 1.5 s trickle (read, 1.7–1.8 s);
    - **exactly 1,048,576** stdin bytes (read).
  - **Refused as CANNOT RUN:**
    - a BOM on the first or a middle record;
    - a payload BOM;
    - a NUL byte record mid-file;
    - CR-only separators;
    - an array record mid-file;
    - a torn record that is the ONLY record;
    - a 3 s trickle (refused at 2.1–2.2 s);
    - **1,048,577** bytes;
    - `/dev/zero` as stdin.
  - **`/dev/null` and a closed stdin** are CANNOT RUN in the three transcript guards; ci-watched returns 0 there.
  - A FIFO swapped in after a `stat` cannot be exploited: `read_file` checks the type with `fstat` on the descriptor it reads.
- **Valid input not wrongly refused, master vs branch.** 80 real transcripts (77 random under 40 MB plus the 3 largest, up to ~100 MB), SNAPSHOTTED first so a live file could not differ between runs. 240 pairs across banner-armed, closing-table and transcript-references: **0 rc differences.** Separately, `bounded_read.read_file` + `parse_jsonl` over **all 618** real transcripts: **618 read**, 0 refused.
- **ci-watched over real check rows.** 60 PRs, **913** real `statusCheckRollup` rows (`gh pr list --state all`, read-only). The rows are all CheckRuns: COMPLETED/SUCCESS 826, COMPLETED/SKIPPED 58, IN_PROGRESS 20, QUEUED 6, COMPLETED/FAILURE 3. Branch refused **0**, and the unresolved set equals master's on **60/60**. The new rule refuses `STARTUP_FAILURE` as a status and a trailing-space `"completed "`, and reads lower or mixed case. `EXPECTED` and `ERROR` keep master's resolution. No real row exercises an unknown status, so the WARN → CANNOT RUN move costs nothing measured.
- **Self-tests, all green:** `bounded_read` 45/45, banner-armed 246/246, ci-watched 101/101, closing-table 159/159, handoff-path 24/24, transcript-references 25/25.
- **Mutation slices** (`check-plan-code.py --mutate . --only scripts/<x>.py`, one at a time; every kill attributed to the case it names):

  | Slice | Killed | Survivors |
  |---|---|---|
  | `bounded_read` | 22/22 | 0 |
  | transcript-references | 7/7 | 0 |
  | closing-table | 51/51 | 0 |
  | handoff-path | 8/8 | 0 |
  | ci-watched | 52/52 | 0 |
  | banner-armed | BANNER_RESULT | |

## Counts

Blocking 0 · Major 2 (both pre-existing, not fix-induced) · Minor 4 (two fix-induced, in the new reader's instrument).

**NOT CONVERGED.** The redesign's reader holds everywhere I could reach it. The bet is lost one field over, at `session_id`. That points to widening the reader's scope to every path the payload names. It does not call for a split: one validation in `stop_transcript` closes finding 1 for all three guards.

No plan text was read or quoted; `.claude/plans/` was not opened.
