# PR #425 (backlog #361, compaction guards) — round 3, Claude half: WORDING vs CODE

Subject: worktree `pin-361e`, detached at `3c282379`, diff `origin/master...HEAD`.
Mandate: narrow. Does each sentence claim more than the code does? Probes ran on a `mktemp` copy of `scripts/` and
`.claude/hooks/` (`scratchpad/r3c.djSW/`), importing `compaction-state.py` by path, with fake `gh`/`git` on `PATH`
where stated. No mutation sweep and no CI suite were run (the coordinator runs those).

## Findings

### M1 (Major): "no straggler survives the capture" is false at the 11 s kill — the r2 fix to `_run` CAUSES it
- **Sentences:**
  - commit `3c282379` subject: "No straggler survives the capture: every call's process group, and the child's, is
    killed when it ends";
  - backlog #361 row: "Every subprocess runs in its own process group, killed when it ends (a `gh` that was
    `sleep 60` left no straggler)";
  - PR body, session-state bullet: "60 cases, 32 mutations (each call in its own process group, killed when it ends)";
  - `scripts/session-state.py` `_run` docstring: "So a timed-out call, or one that backgrounded something and exited,
    leaves nothing behind";
  - `scripts/compaction-state.py:22` "that it KILLS, with its process group", and `run_capture`'s docstring
    (`:664-665`) "the WHOLE group is killed at `timeout`". Those two are literally true, but they read as "everything
    the capture started", and the next item shows that is not so.
- **Code:** `_run` now starts every call with `start_new_session=True`, so each `gh`/`git` call is in its OWN group,
  NOT in the capture child's. `run_capture` SIGKILLs the child's group at `CAPTURE_TIMEOUT`. SIGKILL cannot run
  `_run`'s `finally: kill_group(p.pid)`, so a call that is in flight at the kill is in a group nobody kills. The
  redesign moved each call out of the one group the parent kills.
- **Input:** the real defaults (`CAPTURE_TIMEOUT` 11, `GH_TIMEOUT` 8). A fake `git` that sleeps 5 s on
  `--git-common-dir`. That is the sequential `ss.main_checkout(root, run)` at `:576`, which is given 10 s. Then a fake
  `gh` that does `exec sleep 61`. So `gh` starts at about 5 s, and its own 8 s timeout would end it at about 13 s,
  after the kill.
- **Observed:** `elapsed 11s`; the snapshot says `CANNOT RUN — capture timed out after 11 s and was killed`; then
  `ps`: `48366… sleep 61`, `PGID == PID`, `PPID 1`. The straggler is alive and reparented to init, which is exactly
  the case the commit says cannot happen. It also reproduces with `capture_timeout=4` and a plain hung `gh`.
- **Not affected:** the HOOK still ends on time. The parent holds no pipe to the grandchild. So the bound sentences
  (`:27`, the hook comments) stay true. What is false is the "nothing left behind" claim.
- **Fix:** EITHER do not start a new session per call when inside the capture child (pass a flag, or use
  `process_group=os.getpgid(0)`), so that the parent's `killpg` reaches every call; OR have the child write each
  call's pgid to a file in its temp dir, and have the parent kill those too. OR reword all five sites to "killed when
  the call ends, unless its caller is itself killed — a call in flight at the capture's 11 s kill survives". Add the
  case above: a call in flight at the kill must be gone afterwards.

### M2 (Major): a bare `#N` in a LIST after "backlog" still counts as naming open PR #N
- **Sentences:** `scripts/compaction-state.py:64-68` "`#N` not preceded by backlog / row / issue / item / step … a
  coincidental `PR #N` or `[id]` written about something else would still count as named (unsafe)"; PR body r2 table
  "CM1 … `#N` not after backlog/row/issue/item/step".
- **Code:** `PR_BLOCKED_BY` (`:691`, used at `:703`) tests only the text IMMEDIATELY before each `#N`. In
  `backlog #364, #376 and #383` only `#364` is preceded by "backlog".
- **Input:** keys `prs: [376, 383]`, summary `"Docs: backlog #364, #376 and #383 filed."`
- **Observed:** `the summary names everything in the snapshot (2 items checked).` And with `"Closed backlog rows #376
  and #383."`, only #376 is DROPPED; #383 counts as named.
- **Why Major:** this is the repo's own commit-subject shape (`cdab7020`: "Docs: backlog #384 (…), #385 (…),
  #386 …"), and today's open PR numbers collide with backlog rows (r2 measured five of seven). The unsafe residue the
  docstring admits names only `PR #N` and `[id]`, so a reader believes a bare `#N` after "backlog" is handled. The r2
  fix closed the single-number case but not the list.
- **Fix:** carry the block across a run of `#\d+` separated by `,` / `and` / `or` / `/`, or require the word `PR`.
  At minimum, extend the docstring's unsafe sentence ("…or a bare `#N` in a list begun by backlog/row/…"). Add the
  list case.

### M3 (Major): the PR body's hook table still describes the shared slot the r2 REDESIGN removed
- **Sentences (`pr361.md`, the table under the title):** `precompact-snapshot.sh` writes
  "`.remember/precompact-snapshot.md`"; `postcompact-audit.sh` writes "`.remember/compaction-audit.md`"; the print's
  RECEIPT is "`.remember/compaction-receipt.json`". It also still says "every AskUserQuestion answer from
  `transcript_path`" and "every PR number, ledger id and decision the `compact_summary` does NOT name".
- **Code:** every file is `.remember/compaction/<session_id>/{receipt.json,snapshot.md,audit.md}` (`:116`,
  `session_dir`). Answers are "the newest … that fit" (`:386`). Dashboard asks beyond `RECENT_ASKS` are NOT CHECKED
  (`:641-642`).
- **Input:** read the PR body, then look for the files after a dry run. The three paths it names are never written.
  (Seen in the probe: only `root/.remember/compaction/S1/snapshot.md` appeared.)
- **Why Major:** this table is the PR's description of WHAT IT WRITES. It contradicts the same body's r2 table ("REDESIGN
  (B): `.remember/compaction/<session_id>/`") and its "Cm10 … the newest answers that fit". The r2 dispositions were
  folded into the code, the backlog row and the docstring, but not into this table.
- **Fix:** rewrite the three rows with the per-session paths, "the newest AskUserQuestion answers that fit", and "every
  … the summary does not name, among the items the snapshot's keys carry (the rest NOT CHECKED)".

### m4 (Minor): the print's first line still says "items the summary dropped are listed" when the audit is not shown
- **Sentence:** `scripts/compaction-state.py:807-808` "COMPACTION HAPPENED at … the state below is derived from disk;
  items the summary dropped are listed." This is r2 m7's residue: the fix covered only a failed GATE.
- **Input:** a valid receipt and snapshot, with `audit.md` missing (PostCompact did not run).
- **Observed:** that first line, then `AUDIT: CANNOT RUN — audit.md does not exist`. Nothing dropped is listed. The
  converse also happens (the snapshot is missing and the audit is shown): "the state below is derived from disk", and
  no state follows.
- **Fix:** add the clause only when the audit is shown ("…; items the summary dropped are listed"), and add "derived
  from disk" only when the snapshot is.

### m5 (Minor): "shows its audit and snapshot only when snapshot nonce == audit nonce == receipt nonce" — each is shown on its own
- **Sentences:** `:39-41` (docstring) and `render_print`'s docstring `:782-784`.
- **Code:** `:810-828` shows the snapshot when ITS nonce matches, and the audit when ITS nonce and epoch match, each
  independently.
- **Input:** the same as m4 (no audit). **Observed:** the snapshot body is printed although no audit nonce exists to be
  equal. That is reasonable behaviour, but not what the sentence says.
- **Fix:** "shows each of the audit and the snapshot only when its own nonce equals the receipt's (the audit's
  receipt epoch too)".

### m6 (Minor): `AUDIT: STALE — its nonce N is not this compaction's N` (`:822-824`)
- **Code:** the branch fires when the nonce differs OR when `receipt_epoch` differs. The message always names the
  nonce.
- **Input:** the audit has nonce `N` and `receipt_epoch` ≠ the receipt's epoch. The receipt has nonce `N`.
- **Observed:** `AUDIT: STALE — its nonce N is not this compaction's N; not shown.` It contradicts itself.
- **Fix:** name whichever of the two did not match.

### m7 (Minor): CLAUDE.md's not-captured word list is said to be complete, and it is not
- **Sentences:** backlog #361 row "`CLAUDE.md`'s *After a compaction* … lists every not-captured word"; PR body r2 table
  "CLAUDE.md lists every not-captured word"; `CLAUDE.md` (*After a compaction*, first bullet).
- **The block also prints:** `checks: UNREADABLE` and "this PR's state is UNREADABLE" (session-state `render`,
  `:307`, `:310`, inside the snapshot's in-flight section); `⚠ hook payload: UNREADABLE` (`:610`);
  `MISSING (prunable)` (`:418`); "N more cut for size" (`:395`); `… N more (all clean ones come last)` (`:450`).
  Each of these is also "not captured". `UNREADABLE` is the important one. A PR whose checks are UNREADABLE is not
  among the listed words, so a reader following the rule takes its state as captured.
- **Fix:** add `UNREADABLE` and `MISSING`, plus "a line saying something is cut or more"; or drop "every" from the
  backlog row and the PR body.

### m8 (Minor): "never 'names everything'" for a category not captured completely — a TRUNCATED PR list audits as complete
- **Sentence:** `:36-38` "A category the snapshot could not capture COMPLETELY is UNAVAILABLE in its keys, so the audit
  says NOT CHECKED and never 'names everything'."
- **Code:** `fetch` returns `truncated` when `len(prs) >= LIMIT` (100), and `render` prints `MAY BE TRUNCATED`. But
  `keys["prs"]` (`:634`) is the list as returned, with nothing in `omitted`.
- **Input:** a fake gh returning 100 open PRs, and a summary naming all 100.
- **Observed:** the snapshot contains `TRUNCATED`, and the audit says `the summary names everything in the snapshot
  (100 items checked).` A 101st open PR would be unaudited and unreported. This is unlikely at today's 7 open PRs,
  but the sentence is absolute.
- **Fix:** when `truncated`, set `keys["omitted"]["prs"] = "≥1 (gh list capped at 100)"` (or `prs: None`). Add a case.

### m9 (Minor): a timed-out capture audits as "the summary names every item that COULD be checked (0)"
- **Sentence:** `:759`, printed when nothing was checked at all.
- **Input:** `audit("PR #7", cannot_run_snapshot("capture timed out…", R, 0), None, 0, R)`.
- **Observed:** `the summary names every item that COULD be checked (0) — NOT a complete check:` followed by four
  UNAVAILABLE lines. The four NOT CHECKED lines make it honest. But the lead sentence is a vacuous positive, and it is
  the line a skimming reader takes in.
- **Fix:** when `checked == 0`, print `AUDIT: NOTHING COULD BE CHECKED — the snapshot captured no category:`.

### m10 (Minor): two hook header comments still overclaim
- `.claude/hooks/postcompact-audit.sh:3` "every open PR, ledger id and pending decision the summary DROPPED". This
  sentence was cited in r2 M3. Only the newest `RECENT_ASKS` dashboard asks are checked, and the rest are NOT
  CHECKED. **Fix:** "… among those the snapshot's keys carry; the rest are reported NOT CHECKED".
- `.claude/hooks/compaction-print.sh:3-4` "opening with 'COMPACTION HAPPENED at …'. A missing or stale file is printed
  as CANNOT RUN / STALE". A failed gate opens with `COMPACTION: no verified capture to show` (`:800`), and a bad
  session id prints `UNVERIFIED` (`:789`). That was the r2 Cm7 change, and this comment did not follow it. **Fix:**
  "opening with `COMPACTION HAPPENED at …`, or `COMPACTION: no verified capture …` naming the failed check
  (CANNOT RUN / STALE / UNVERIFIED)".

## Round-2 findings, re-run against `3c282379`

| r2 | Input reproduced | Now | Verdict |
|---|---|---|---|
| M1 backlog #410 = PR #410 | `prs:[410]`, "Filed backlog #410 …" | `DROPPED … PR #410` | fixed for one number; the list form survives (M2 above) |
| m2 bare-word ledger ids | `ledger:["a","fold"]`, "Resumed a fold …" | both DROPPED | fixed, wording true |
| M3 5 of 37 asks "everything" | `omitted.decisions=32` | "names every item that COULD be checked (2) — NOT a complete check" + `NOT CHECKED: 32 decisions` | fixed; the hook comment is a residue (m10) |
| M4 failed main-checkout lookup | fake rev-parse → 124 | ledger ids + owner waits `UNAVAILABLE` → NOT CHECKED | fixed |
| M5 "ONE 10 s deadline" | hung `gh`; the real 11 s timeout | hook `elapsed 11s`, snapshot CANNOT RUN; no "10 s deadline" sentence remains in the docstring, the backlog row or the hooks | fixed (the bound is now true), but the kill leaves a straggler (M1 above) |
| M6 answers mask lost prompts | prompt without `origin` + an answer pair | `Prompts: NOT EXTRACTED — 1 user turns …` | fixed |
| m7 gate first line | receipt of session OTHER | `COMPACTION: no verified capture to show …` | fixed for the gate; the non-gate residue is m4 |
| m8 "can NEVER match" | — | docstring `:82-85` now states the residue (STALE_AFTER is the only bound) | fixed (residue documented) |
| m9 CLAUDE.md words | — | list extended | partly; `UNREADABLE` / `MISSING` missing, and "every" is claimed (m7 above) |
| m10 "every answer" | — | header `The newest AskUserQuestion answers that fit (N of M paired in the last X MB …)`; backlog row matches | fixed in the code and the row; the PR body table is stale (M3 above) |
| m11 NO-REVIEW line | — | gone; "Review state" line is accurate | fixed |
| m12 "trust" | — | backlog row says RECORDED, not proven | fixed |
| m13 `goal-tree.py` cite | — | cites `check-ci-watched.py`'s `sentinel_for`; present on `origin/master` (`:63`, the `--git-common-dir` rule) | fixed |

## Checked and found TRUE
- Counts: `compaction-state.py --self-test` gives `101/101`, and `session-state.py --self-test` gives `60/60` (both run
  in the temp copy). The manifests hold 59 and 32 entries. `EXPECTED_MUTATIONS` sum 2361 → 2427 = +7
  (session-state 25 → 32) + 59: correct.
- "the WHOLE hook ends within STDIN_WAIT + CAPTURE_TIMEOUT + a fraction of a second" (`:27`), and "this hook ends
  under its 15 s timeout" (precompact-snapshot.sh). Measured 11 s with a hung `gh`. The parent holds no pipe to any
  grandchild. The registered timeout is 15 (`settings.json`).
- `CANNOT RUN — capture timed out after N s` (`:26`): the real text is `capture timed out after 11 s and was killed`.
- "a `session_id` that does not match SESSION_ID gets NOTHING written, and the print says UNVERIFIED" (`:15`): this is
  the `sdir is None` branches at `:874-885`.
- The provenance sentences (`:49-55`): the session binding (`:288`), `_off` on all three flags for answers via
  `eligible` and for prompts (`:312`), task notifications excluded, and `consumed` preventing a reopened id. Each is
  in the code as worded.
- `names every item that COULD be checked … NOT a complete check` is printed exactly when `unchecked` is non-empty.
  NOT CHECKED lines go before the dropped list (`:763`), as the comment says.
- `RECORDED in the transcript, not proven` heading (`:368`). It matches CLAUDE.md's third bullet and the backlog row.
- `main_checkout`'s docstring: a non-absolute or non-directory answer is refused (the code at the `os.path.isabs` /
  `isdir` test). The cited `sentinel_for` exists on master.
- `kill_group`'s docstring ("ignoring one that is already gone") is true. `_run`'s "A process that left the group
  itself (a daemon calling setsid) is out of reach, by design" is true. The defect in M1 is a DIFFERENT escape: the
  caller is killed, not the callee.
- The fail-closed paste sentence (`:57-60`, `withhold_pasted`): it counts first, and anchors only for 1 opener + 1
  closer with equal ids.

## Summary
Blocking 0 · Major 3 (M1, M2, M3) · Minor 7 (m4–m10).
M1 is new and was caused by the last fold: `_run`'s per-call session takes each call out of the group the capture's
kill reaches, so the commit's headline claim is false exactly at the timeout it was written for. M2 is r2 CM1's list
form. M3 is a stale table in the PR body that names files the redesign no longer writes.

VERDICT: NOT CONVERGED
