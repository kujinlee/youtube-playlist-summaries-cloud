# PR #425 (backlog #361, compaction guards) — round 4, Claude half: WORDING vs CODE

Subject: worktree `pin-361g`, detached at `6c837787`, diff `origin/master...HEAD`. I read the architecture review
(`docs/reviews/architecture-review-2026-10-28-compaction-guards.md`, decision SPLIT) and the round-3 Claude half first.
Mandate: narrow. I checked whether each sentence the split KEEPS or adds claims more than the code does.
Probes ran in a `mktemp` copy (`scratchpad/r4c.1aQm/`, with `scripts/`, `.claude/` and `docs/dashboard-entries.md`).
They used the REAL hook scripts on stdin JSON, with a fake `gh`/`git` on `PATH`, and the pure functions imported by path.
I ran no mutation sweep and no CI suite. The self-tests ran in the copy: compaction-state `113/113`, session-state `62/62`.

## Findings

### F1 (Major): the dashboard entry for this PR still states, to the owner, both claims the split withdrew. Partly caused by 218b9582
- **File:** `docs/dashboard-entries.md:18048-18079`, the `## 2026-10-28` entry. It is owner-facing: `/dashboard` renders it.
- **False sentences:**
  - `:18051-18052` "a second hook compares the summary with that file and lists everything the summary left out".
    This is the completeness claim the split withdrew.
  - `:18052` "both are shown first, with a line saying a compaction happened". The `COMPACTION HAPPENED` line is
    deleted, and the heading is now `NEWEST CAPTURE for this session…`.
  - `:18057` "writes `.remember/precompact-snapshot.md`". The file is `.remember/compaction/<sid>/snapshot.md`.
  - `:18062` "`--audit` … lists every PR number, ledger id and pending decision the `compact_summary` does not name".
  - `:18064` "STALE when the snapshot is over 30 minutes old or the audit is of another snapshot". No STALE message
    exists any more.
  - `:18073` "an old or another session's snapshot is never shown as this compaction's". This is the identity claim
    the split withdrew.
  - `:18077` "100 cases, 59 mutations". The real figures are 113 and 69. `:18058` "51/51 and its 25 mutations": the real
    figures are 62 and 34.
  - `:18078` "a summary leaving out PR #392 was reported as dropping exactly that". No audit says "dropping" now.
- **Input:** read the entry, then run the hooks. **Observed:** the audit I ran (S2) printed only "Not found explicitly …
  / Found explicitly …". No "left out", "dropped" or "COMPACTION HAPPENED" text appears in any output. The only file
  written was `.remember/compaction/S2/{receipt.json,snapshot.md,audit.md}`.
- **Caused by 218b9582:** partly. That commit edited this paragraph to add "A third review withdrew two claims…" at
  `:18075-18077`. It left the contradicting sentences on both sides, so the entry now asserts both claims and their
  withdrawal.
- **Fix:** rewrite the entry from the final code, the same way the PR body was rewritten. Keep "None of this has run
  on a real compaction yet".

### F2 (Major): the PR body still calls the falsifier "the owner's", which 6c837787 corrected everywhere else
- **File:** `pr361.md:60`. The false sentence: "The owner's falsifier, recorded in backlog #361's row: grade the first
  real compaction…".
- **Code / record:** commit `6c837787` ("credited to the coordinator who wrote it, not to the owner"). The backlog row
  now says "written by the coordinator … the owner did not write these criteria", and so does the architecture
  review's last section. The PR body was not changed with them.
- **Why Major:** the PR's whole subject is that words attributed to the owner must be labelled RECORDED, not proven.
  This body attributes acceptance criteria to the owner that the owner did not write.
- **Caused by 218b9582:** no. The body was written alongside that commit, and `6c837787` did not update it.
- **Fix:** "The falsifier, written by the coordinator at the owner's request and recorded in backlog #361's row: …".

### F3 (Minor): `tag_uncaptured` marks CAPTURED lines as NOT CAPTURED, which makes CLAUDE.md's one rule false. Caused by 218b9582
- **Sentences:**
  - `CLAUDE.md:10` "Any line carrying **NOT CAPTURED** means that part was not captured."
  - `scripts/compaction-state.py:50-52` "Every line about something not captured … carries NC".
- **Code:** `:655-662`. NC is appended to ANY line of the in-flight block that CONTAINS one of `CANNOT RUN`,
  `UNREADABLE`, `TRUNCATED`, `NOT READ` or `⚠`, and that includes text that comes from the data itself.
- **Input:** a PR with branch `fix-TRUNCATED-keys`, and a ledger entry whose `what` is "Codex r2 CANNOT RUN fallback:
  Claude half running" (`tag_uncaptured(ss.render(...))`).
- **Observed:**
  `PR #12 \`fix-TRUNCATED-keys\` head abc · CLEAN · checks: NO CHECKS — NOT CAPTURED` and
  `[codex-r2] Codex r2 CANNOT RUN fallback: Claude half running — when done: fold (since None) — NOT CAPTURED`.
  Both items were captured in full.
- **Severity:** Minor. The error goes the cautious way, since it sends the reader to verify. The real ledger holds 0
  of 7 such entries today, but this repo's ledger text routinely quotes "CANNOT RUN".
- **Fix:** tag by the render's own line SHAPES (the `OPEN PRS: CANNOT RUN`, `MAY BE TRUNCATED` and `⚠ gh omitted`
  prefixes, and the problem lines), not by substring over the whole line. Or soften CLAUDE.md to "…means that part
  may not have been captured". Add a case with a ledger `what` that contains `CANNOT RUN`.

### F4 (Minor): three not-captured lines do not carry the one word. Not caused by 218b9582 (pre-existing), but the claim that they do is new there
- **Sentences:**
  - `scripts/compaction-state.py:50` "Every line about something not captured … carries NC".
  - PR body `:25` "Every line about something not captured carries **NOT CAPTURED**".
  - backlog #361 row "Every not-captured line carries **NOT CAPTURED**".
- **Code:** the hook fallbacks:
  - `.claude/hooks/compaction-print.sh:10` `=== COMPACTION STATE: CANNOT RUN — compaction-state.py exited $? ===`;
  - `precompact-snapshot.sh:11` and `postcompact-audit.sh:8` `compaction-state --…: CANNOT RUN — exited $?`.
  None of them carries `NOT CAPTURED`. The print one is injected into the new context window, so it is exactly the
  line CLAUDE.md tells the reader to look for.
- **Input:** a `compaction-state.py` that fails before `main`, for example a syntax error or a missing `python3`
  module (any non-zero exit). **Observed:** by reading the code. `main` returns 0 in every mode, so this fires only
  on a crash at import time.
- **Also:** `compaction-print.sh:2-4` names two headings and omits this third one (r3 m10's residue).
- **Fix:** add `NOT CAPTURED` to all three echoes.

### F5 (Minor): the snapshot's "where the ledger was read" line can contradict the ledger it heads. Not caused by 218b9582
- **Sentence:** `scripts/compaction-state.py:679` + `:707-713`. "ledger read from the MAIN checkout, <main>/…", or
  "⚠ NOT CAPTURED — ledger read from THIS checkout … the real ledger is elsewhere and was NOT READ".
  `session-state.py:322` `main_checkout`'s docstring calls itself "THE one copy of this rule". It is one copy of the
  RULE, but the capture CALLS it twice: once at `compaction-state.py:679`, and again inside `ss.fetch`
  (`session-state.py:387`). The `where` line describes the first call, while the ledger shown came from the second.
- **Input:** a `git` whose `rev-parse --git-common-dir` answers once and then exits 128 (S3), or the reverse (S4). The
  main ledger at `mainrepo/.claude/inflight.jsonl` holds `real-job`.
- **Observed:**
  - S3: "ledger read from the MAIN checkout, …/mainrepo/.claude/inflight.jsonl". Yet the ledger block shows the
    fallback problem "this checkout's ledger was read", with no `real-job`.
  - S4: "ledger read from THIS checkout … the real ledger is elsewhere and was NOT READ". Yet the block lists
    `[real-job] WAITS-ON-OWNER: pick A or B`, and "Pending OWNER decisions" shows it too, beside "in-flight ledger:
    NOT CAPTURED — it was not read completely".
- **Severity:** Minor. The input is a flaky git, and in both cases an NC or ⚠ line is nearby.
- **Fix:** have `fetch` return the `(main, main_err)` it used (or accept them as an argument), and build `where` from
  that one answer.

### F6 (Minor): `_run` reports "timed out" for a call that EXITED, and "can no longer hold this call open" overstates. Wording new in 218b9582
- **Sentences:**
  - `scripts/session-state.py:125` "it can no longer hold this call open";
  - `:154` `timed out after {timeout:.0f}s`;
  - the PR body `:29` "each call runs in its own process group, killed when it ends".
- **Input:**
  - `ss._run(["sh","-c","sleep 4 & echo '[]'; exit 0"], ".", 1.5)`: the call exits at about 0 s, and its background
    child keeps stdout.
  - The same with `own_group=False`.
  - A `setsid` grandchild that keeps stdout while its parent prints `[]` and exits.
- **Observed:** `(124, 'timed out after 2s')` in 1.5 s, 2.5 s and 2.5 s.
  - The call's own output `[]` is DISCARDED. It is reported as a timeout of a call that did not time out, so the
    SessionStart block says `OPEN PRS: CANNOT RUN — timed out after 30s` about a `gh` that answered.
  - The holder DOES hold the call open, for its whole timeout plus DRAIN. What changed is that the hold is now
    bounded.
  - "1.5" also prints as "2s".
  - With `own_group=False` (the capture), the call is NOT in its own group. The PR-body bullet says "each call",
    which contradicts its own previous bullet.
- **Fix:**
  - At `:125`, say "…it can hold this call for at most `timeout` + DRAIN, never past it".
  - When `p.poll()` is already set at the timeout, return its status and output, or say "exited N, but a process it
    started kept the pipe open".
  - Print the timeout with `:g`.
  - In the PR body, write "each call runs in its own process group (the capture's calls excepted), killed when it
    ends".

### F7 (Minor): the printed bound lists two ways a wrong capture is shown and omits the third, which the docstring names
- **Sentence:** `SESSION_NOT_COMPACTION`, printed at `:804-805`: "a delayed or overlapping compaction in this session can
  be shown here."
- **Code / docstring:** `:83-84` "If a compaction's PreCompact did not run at all, the previous receipt of the same
  session still matches, bounded only by STALE_AFTER". The PR body `:37-38` says the same. That case is neither
  delayed nor overlapping. Example: compaction 1 runs PreCompact; compaction 2, 20 min later, has no PreCompact (its
  hook failed before `new_receipt`). The print for 2 shows capture 1 under the line above.
- **Input:** by reading the code. `render_print` checks only the receipt's age and the nonces.
- **Fix:** "…a delayed or overlapping compaction in this session, or an earlier one whose successor's PreCompact did
  not run, can be shown here."

### F8 (Minor): small sentences that are printed false
- **`:896` at age 1810 s:** the print says `the receipt is 30 min old, over 30.` (observed), and the heading says
  "(30 min before this session start)". **Fix:** compare and print in the same unit (seconds, or `ceil`).
- **`:911`:** "the audit is missing: <err> (the PostCompact hook did not write it)". When `<err>` is `audit.md is not a
  regular file — NOT READ`, or is over the cap, or is a symlink (each from `read_in`), PostCompact may well have written
  it. **Fix:** add the parenthetical only for `does not exist`.
- **`audit` heading:** "Not found explicitly in the summary". For "Merged PRs #410 and #411" and for "pull request
  #411" (observed), `PR #411` is listed as NOT found explicitly, although the writer named it explicitly in English.
  The disclaimer covers the consequence, but the label states a fact about the summary that is false. **Fix:** "Not
  found as `PR #N`, `[id]` or an ask id (N):", and the same for Found.
- **Leftover comments that claim compaction identity:**
  - `:122` "is not this compaction's";
  - `:757` "this compaction's nonce";
  - `:121` "a receipt older than this is from an earlier one".
  **Fix:** say "this receipt's", or "this capture's".
- **Leftover "dropped" outside Python:**
  - `.claude/settings.json:165` `statusMessage` "Auditing what the compaction summary dropped..." (shown in the UI on
    every compaction);
  - `.github/workflows/ci.yml:399` "the PostCompact audit of what the summary dropped".
  **Fix:** "Listing which snapshot items the summary names…".
- **backlog #361 row:** "**FALSIFIER (the written by the coordinator at the owner's…**". This garbled phrase comes from
  6c837787's edit. **Fix:** "FALSIFIER (written by the coordinator…".
- **PR body `:51`:** "CI runs both `--self-test` steps". Only `compaction-state` has a named step (`ci.yml:401`).
  session-state's suite runs in CI only through `check-selftest-counts.py` (its POPULATION, `:93`) and the mutation
  sweep. True that it RUNS, false that there are two steps. **Fix:** "CI runs both suites".

### F9 (Minor, r3 m8's residue): a truncated PR list carries no NOT CAPTURED line in the audit
- **Code:** `keys["prs"]` (`:699`) is the list as returned, even when `fetch` says `truncated` (100 or more). Nothing
  lands in `omitted`, so the audit's "N … item(s) are not in the snapshot's keys" line never fires for PRs.
- **The sentence that was false** ("never 'names everything'") is gone, so nothing in the audit is now false. But the
  audit, which is printed ABOVE the snapshot, lists 100 PRs with no NC line. A PR beyond the 100 is neither found nor
  not found. The NC is visible only in the snapshot's `MAY BE TRUNCATED` line.
- **Fix:** set `keys["omitted"]["prs"] = "≥1 (gh list capped at 100)"`, and print that in the audit's NC block (the
  loop now skips non-int values).

## Round-3 Claude findings, re-run against `6c837787`

The team lead's CR1–Cr10 are, in that file, M1–M3 and m4–m10.

| r3 | Input reproduced | Now | Verdict |
|---|---|---|---|
| M1/CR1 straggler at the 11 s kill | REAL hook, fake `git` sleeps 5 s on `--git-common-dir`, then `gh` = `sleep 62 & exec sleep 61` | `elapsed 11s`, snapshot `NOT CAPTURED — CANNOT RUN, capture timed out after 11 s and was killed`; `ps` shows **no** `sleep 61`/`62` | **fixed**; wording (`:23-26`, hook header, PR body, backlog row) matches. Also the normal path: `gh` backgrounds `sleep 63` and exits → 1 s, no straggler |
| M2 `backlog #364, #376 and #383` | `PR_EXPLICIT` requires the word PR | no PR found, all listed under "Not found explicitly" | **dissolved** (the claim is deleted); F8 is the wording residue of the label |
| M3 PR-body table, old paths | rewritten body | per-session paths, "newest … answers that fit", "never says … kept or dropped" | **fixed** |
| m4 "items the summary dropped are listed" | — | `grep COMPACTION HAPPENED` → 0 hits in the script, hooks, CLAUDE.md and the PR body | **fixed** (the dashboard still says it — F1) |
| m5 three-way nonce sentence | no audit, valid snapshot | docstring `:47-49` and `render_print` say "snapshot when nonce = receipt's …; audit only when nonce = shown snapshot's", which is what `:898-915` do | **fixed** |
| m6 STALE names only the nonce | — | the audit now compares the nonce only, and the message names `nonce` | **fixed** |
| m7 CLAUDE.md "every word" | — | one word, NOT CAPTURED | **fixed** as a list; the new rule is falsified two ways (F3, F4) |
| m8 truncated list "names everything" | — | the sentence is gone | **dissolved**; the behavioural residue is F9 |
| m9 "COULD be checked (0)" | — | gone; a CANNOT RUN snapshot yields four `NOT CAPTURED — … UNAVAILABLE` lines and two empty lists | **fixed** |
| m10 hook header comments | — | `postcompact-audit.sh:2-3` is accurate; `compaction-print.sh:2-4` names two of the three headings | **fixed** but for the F4 residue |

## Checked and found TRUE

- **The AUDIT_DISCLAIMER line.** It is printed as the second line of every audit, CANNOT RUN included. It claims
  nothing that an input could falsify: both halves are negations of an inference.
- **The "Found explicitly" list.**
  - I tried inputs to put an item there that the summary does not name in an explicit form: `APR 410`,
    `pr-review-toolkit 2`, `PR #4251` for item 425, an ask id preceded by `/`, and `PR` then a newline then `#425`.
  - None of them matched. `\b`, `(?!\d)`, `[ \t]` (no newline) and `(?<![\d/])` each hold.
  - Found / not-found counts equal the list lengths.
- **The print's "NEWEST CAPTURE for this session, taken at T (N min before this session start)".**
  - T is the receipt's epoch. The receipt is rewritten by every PreCompact of the session, so it IS the newest one
    recorded.
  - N is computed against the print hook's own `now`. It is observed as `0 min before` on a fresh capture (S2).
  - A negative age prints "AFTER", and below −60 s it prints "dated in the FUTURE".
- **"session identity is not compaction identity"** is printed on every heading that shows anything. F7 is about its
  enumeration, not its truth.
- **No print shows a snapshot whose nonce differs from the receipt's, or an audit whose nonce differs from the shown
  snapshot's** (`:898-915`).
  - Race traced: an audit written after a newer PreCompact's `new_receipt` carries the old nonce → `the audit is not
    shown: field nonce differs`.
  - A forged keys line in a prompt cannot match: the nonce is `pid-urandom(6)`, `clean` makes each item one line, and
    `_keys` reads the LAST keys line, which is the one appended after `fit`.
  - The architecture review's own falsifier ("a print that shows a capture whose nonce does not match") was NOT
    triggered.
- **NOT CAPTURED / CANNOT RUN messages.**
  - The receipt's (`:890`), the gate's (`:876-885`), the audit's four CANNOT RUN branches (`:826-834`), the worktree
    `status UNKNOWN` line, the cuts in `owner_section`/`worktree_section`/`decision_section`, and `fit`'s note all carry
    NC.
  - session-state `render`'s own not-captured lines (`:320` CANNOT RUN, `:324` MAY BE TRUNCATED, `:335` UNREADABLE,
    `:347` ⚠) all get NC through `tag_uncaptured`.
  - F3 is the over-match; F4 lists the three it misses.
- **`compaction-state.py` docstring.**
  - "Every component … opened … with O_NOFOLLOW" (`open_session_dir`).
  - "Every artifact is read by ONE reader, `read_in`" is true for receipt, snapshot, audit and the child's out file.
    The transcript and the dashboard go through `_open_regular`, but the docstring does not call them artifacts.
  - "each hook ends within STDIN_WAIT + its child's timeout + a fraction": 11 s measured on the kill path.
  - "the parent SIGKILLs that whole group after the child ends, for ANY reason": `run_capture`'s `finally`.
  - "The snapshot is shown when … under STALE_AFTER old and not in the future" (`age > STALE_AFTER`, `age < -FUTURE_SKEW`).
  - The provenance paragraph: `_off` is `is False`, as worded.
- **session-state.**
  - `kill_group`: "ignoring one that is already gone". It also swallows `PermissionError`, which is not "gone" (a
    nit, not filed).
  - `main_checkout`: an answer that is not an absolute, existing directory is refused.
  - The `_run` own_group paragraph: the self-test case `own_group=False keeps the call in the CALLER's process group`
    passes, and the 11 s kill test above confirms the effect.
- **Hook headers.**
  - `precompact-snapshot.sh:2-5`: "killed at 11 s and again after it exits … nothing the capture started outlives it
    (a self-`setsid` process excepted)". Reproduced.
  - `postcompact-audit.sh`: "never whether one was kept or dropped".
  - `compaction-print.sh`: "under 10,000 characters" (`fit` to PRINT_CAP 9800, including END).
- **CLAUDE.md *After a compaction*.**
  - "prints this session's NEWEST CAPTURE (`.remember/compaction/<session_id>/`)", "the audit of which of its items the
    summary names explicitly", and "RECORDED, not proven" all match the code.
  - "Any line carrying NOT CAPTURED means…" is falsified by F3.
- **Backlog #361 row.**
  - Paths, modes, "never whether it kept or dropped them", "NEWEST CAPTURE", "nothing the capture starts outlives it
    except a self-`setsid` process" (reproduced), "113 cases, 69 mutations; session-state 62 cases, 34 mutations".
  - Falsifier criteria (1)–(4) match what the code prints; criterion (3) correctly drops "names everything".
  - The garbled phrase is in F8.
- **Counts.**
  - `--self-test`: 113/113 and 62/62.
  - Manifests: 69 and 34 entries.
  - `EXPECTED_MUTATIONS` has `compaction-state.py: 69` and `session-state.py: 34`, with the pinned sum 2439
    (`check-plan-code.py:6166`).
  - Docstring `# 113 cases` / `# 62 cases`.
- **PR body (apart from F2, F6 and F8).**
  - The table rows, "Every artifact is read by one reader", "Nothing the capture starts outlives the hook", the
    "What it does not claim" section and the test bullets all match the code.
  - "Round 4 has not run" was true when the body was written.
- **Words checked.** No kept sentence in the script, the hooks, CLAUDE.md, the backlog row or the PR body claims
  "names everything", "COMPACTION HAPPENED", "this compaction" as an identity claim (outside the comments in F8), or a
  "bounded" property the code lacks. "bounded only by 30 minutes" / "STALE_AFTER" is true.

## Summary

Blocking 0 · Major 2 (F1, F2) · Minor 7 (F3–F9).

Neither Major is in the code. F1 is the owner-facing dashboard entry, which still states both withdrawn claims, the old
file path and stale counts. 218b9582 appended the withdrawal to that paragraph without removing what it withdrew. F2 is
the PR body, which still credits the falsifier to the owner after 6c837787 corrected that everywhere else.

The split's own kept sentences survive. No input I built made the print show a mismatched nonce, or made the audit
claim kept or dropped. The architecture review's falsifier is not triggered, so DEFER is not indicated. The new rule
"one word, NOT CAPTURED" is false in both directions: it over-tags captured data (F3) and misses the three hook
fallbacks (F4). F3 is new in 218b9582.

VERDICT: NOT CONVERGED
