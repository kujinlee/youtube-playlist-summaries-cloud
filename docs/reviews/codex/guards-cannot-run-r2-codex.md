<!-- codex-review: model=gpt-6.1-sol -->

1. **Major — m2 introduces a silent pass over undecodable transcript records.**  
   `scripts/check-banner-armed.py:339–341`, `scripts/check-transcript-references.py:142`.  
   **Component:** transcript-read. **Fix-induced: yes.**

   Concrete transcript:

   ```text
   {"type":"user","uuid":"u1","message":{"role":"user","content":"go"}}
   <byte FF>
   <byte FE>
   ```

   With `session_id` supplied, pre-fold transcript-references returns **2**. After the fold, it returns **0**, and **`run-hook.sh block-idle-stop.sh` also returns 0 silently**. Separately, corrupting the judged assistant record changes a bare-reference warning from **1 to 0**. Skipping arbitrary undecodable lines extends beyond tolerating a torn final record.

2. **Major — deeply nested JSON still escapes as a traceback.**  
   `scripts/check-banner-armed.py:324–325`, `scripts/check-ci-watched.py:553–558`.  
   **Components:** payload-path, ci-watched. **Fix-induced: no.**

   Concrete stdin: `b"[" * 200000 + b"]" * 200000`.

   All three transcript guards’ real `--decide` entry points exit **1 with `RecursionError`**. The registered Stop hook returns **1 with tracebacks**. Replaying the same JSON as GitHub’s checks response also crashes ci-watched. The handlers omit `RecursionError`.

3. **Major — empty status strings still become WARN or QUIET.**  
   `scripts/check-ci-watched.py:239–240`.  
   **Component:** ci-watched. **Fix-induced: no.**

   Concrete checks response:

   ```json
   [{"name":"v","status":""}]
   ```

   Through the real CLI with controlled Git/`gh` boundaries: **rc 1**, claiming “CI is running.” With a watcher armed for HEAD: **rc 0**. The registered hook also surfaces the false CI-running warning. An empty status supplies no readable state; checking only its type leaves X2’s boundary incomplete.

4. **Major — a FIFO transcript path hangs the registered Stop hook.**  
   `scripts/check-banner-armed.py:333`.  
   **Component:** transcript-read. **Fix-induced: no.**

   Create a FIFO with no writer and supply its path as `transcript_path`. All three transcript guards and **`run-hook.sh block-idle-stop.sh` remained blocked until the external timeout**. The shared reader performs an unbounded blocking read instead of refusing a nonregular file.

Validation:

| Suite | Self-test | Mutation slice |
|---|---:|---:|
| banner-armed | 246/246 | 100/100 killed |
| ci-watched | 96/96 | 50/50 killed |
| closing-table | 159/159 | 51/51 killed |
| handoff-path | 23/23 | 7/7 killed |
| transcript-references | 25/25 | 9/9 killed |
| plan-code | 246/246 | **DID NOT RUN** |

The requested harness mutation command exited **2**, refusing an estimated **17.7-minute** run against its **10-minute** local budget: “NOTHING WAS MEASURED.” No survivors appeared in the five completed slices; all 217 kills were attributed.

Read-only comparison covered **50 real transcripts**: no branch/master return-code differences. **15 real PR check rows** also produced identical outcomes. NUL/non-string paths, scalar payloads, invalid payload UTF-8, directories, symlink loops, permission-denied files and unlistable arm directories were refused. **All-undecodable transcripts remain rc 2**, not QUIET. Unknown nonempty statuses retain the documented unresolved behavior; conclusion-only rows are refused. The legitimate vendored UTF-8 handoff skill passed the registered hook.

No files under `.claude/plans/` were read or quoted. Working tree unchanged.

**NOT CONVERGED**
