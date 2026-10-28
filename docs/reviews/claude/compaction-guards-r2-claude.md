# PR #425 (backlog #361, compaction guards) — round 2, Claude half: WORDING vs CODE

Subject: worktree `pin-361c`, detached at `44ae10d9`, diff `origin/master...HEAD`.
Mandate: narrow. Does each sentence claim more than the code does? Every finding below names a sentence and an
input that makes it false. Probes ran on a `mktemp` copy of `scripts/` (`scratchpad/r2c.tOU6/`), importing
`compaction-state.py` by path. No mutation sweep and no CI suite were run (the coordinator runs those).

## Findings

### M1 (Major): "names" counts a BACKLOG row as the open PR with the same number
- **Sentences:** `scripts/compaction-state.py:670-672` — "the summary names everything in the snapshot (N items
  checked)"; `.claude/hooks/postcompact-audit.sh:2-3` "every open PR … the summary DROPPED"; PR body table row
  "every PR number … the `compact_summary` does NOT name"; docstring `:75-77` "The audit matches by NAME (`#410`,
  `PR 410` …) … a paraphrase is reported as dropping it — the safe direction."
- **Code:** `mentioned()` `:619` accepts `#\s?<n>` anywhere, so `backlog #410`, `issue #410` and `step #410` all
  count as naming PR #410. The documented failure direction is "safe" (a false DROPPED); this is the UNSAFE one
  (a false "named").
- **Input:** keys `prs: [410]`, summary `"Filed backlog #410 for later; nothing else open."`
- **Observed:** `the summary names everything in the snapshot (1 items checked).`
- **This is the usual case here, not a rare one:** the open PRs right now are #425, #392, #383, #376, #371, #364 and
  #341 (`gh pr list`). Backlog rows go up to #386, so FIVE of the seven open PR numbers are also backlog row numbers
  (#383, #376, #371, #364, #341). The summaries in this repo cite backlog rows by `#N` all the time. Example: a
  summary that says "backlog #376 shipped in PR #422" makes the audit count the still-open PR #376 as named.
- **Fix:** take as a PR mention only `PR #?N` or `#N` NOT preceded by `backlog`, `row`, `issue` or `item`, or else
  require the `PR` word. Add a case: `"backlog #410"` with `prs:[410]` gives DROPPED. Change the docstring so it
  says that this matching can fail in BOTH directions.

### m2 (Minor): a ledger id that is an ordinary word is "named" by any use of that word
- **Sentence:** the same audit line `:672`, and "every … ledger id … the summary does NOT name".
- **Code:** `:621`, a whole-word match on the bare id.
- **Input:** keys `ledger: ["a", "fold"]`, summary `"Resumed a fold on the branch."`
- **Observed:** `the summary names everything in the snapshot (2 items checked).`
- The real ledger ids are hyphenated (`build-361`, `r2-361`, `paused-363` …), so this is unlikely today. But
  `--add` does not restrict the id. **Fix:** match a ledger id only inside a bracket or backtick (`[id]`, `` `id` ``),
  or say in the docstring that a short or ordinary-word id cannot be audited.

### M3 (Major): the audit says "names everything" when it checked only 5 of 37 dashboard asks
- **Sentences:** `scripts/compaction-state.py:672` "the summary names everything in the snapshot (N items checked)";
  `.claude/hooks/postcompact-audit.sh:2-3` "every … pending decision the summary DROPPED"; PR body "every … decision
  the `compact_summary` does NOT name". The docstring at `:77-78` admits "older ones are counted, not audited",
  but the AUDIT FILE, which is the thing the next window reads, never says so.
- **Code:** `snapshot()` `:601` keys only `recent`, which is `need[-RECENT_ASKS:]` (`:445`), and puts nothing in
  `omitted` for the remaining asks. So `audit()` `:663-672` has nothing to put on a NOT CHECKED line. This is the
  same defect class that r1 Xm6 fixed for the keys cap. The fix there did not reach this cut.
- **Input:** `asks` returns `(37, <5 newest>, None)`, `prs:[7]`, summary `"PR #7 open. Asks <the 5 ids>"`.
- **Observed:** `the summary names everything in the snapshot (6 items checked).` No NOT CHECKED line appears.
- **This is today's state, not a rare one:** memory `nothing-needs-you-must-read-the-dashboard` records 37
  unresolved asks on 10-27. Every real compaction would audit 5 of them and report a complete check.
- **Fix:** record `omitted["decisions"] = count - len(recent)` in the keys, so the audit gives
  `NOT CHECKED: 32 decisions item(s) …` and the "names every item that COULD be checked" form. Add a case with
  count > RECENT_ASKS.

### M4 (Major): an UNREAD ledger is audited as an empty one ("names everything"), which r1 XM5 said was fixed
- **Sentences:** backlog #361 row "an unread ledger is UNAVAILABLE, never \"all named\""; docstring `:28-30` "A
  category the snapshot could not capture is UNAVAILABLE in its keys, so the audit says NOT CHECKED and never
  \"names everything\""; PR body r1 table "XM5 … never a completeness claim".
- **Code:** `ledger_ok` `:564` is false only for a problem that starts with `LEDGER_REL`. When `main_checkout` fails,
  `fetch` (session-state `:154-156`) reads THIS checkout's ledger and adds a problem that starts "the main checkout
  could not be found". That does not start with `LEDGER_REL`, so `ledger_ok` stays True and the keys carry
  `ledger: []`, not None. One way to get there is the snapshot's own deadline: `bounded` returns
  `124 "the snapshot's deadline had passed — NOT RUN"` (`:367-368`), and in `fetch` the rev-parse runs AFTER the gh
  call of up to 8 s.
- **Input:** a fake `run` whose `git rev-parse` returns that 124. Then `snapshot(...)` and
  `audit("PR #7 open.", …)`.
- **Observed:** the snapshot itself does warn ("⚠ ledger read from THIS checkout … the real ledger is elsewhere and
  was NOT READ"), but the audit prints `the summary names everything in the snapshot (1 items checked).`, with no
  NOT CHECKED line for the ledger.
- **Fix:** when `main_err` is set and `main.resolve()` cannot be shown to equal the real main checkout, put
  `ledger: None` and `ledger_decisions: None` in the keys (UNAVAILABLE). Add a case: main_err plus an empty ledger
  gives `NOT CHECKED: ledger ids — UNAVAILABLE`.

### M5 (Major): "ONE 10 s deadline bounds PreCompact" is false. Only the SUBPROCESSES are bounded; a run took 19.6 s
- **Sentences:** backlog #361 row "ONE 10 s deadline bounds PreCompact"; docstring `:18` "all by ONE deadline
  (SNAPSHOT_BUDGET)"; `:115` "ONE deadline for the whole PreCompact run, under its registered 15 s timeout"; `:766`
  "stdin included: the whole hook, under its 15 s timeout"; `:113` "every hook stays well under 10 s"; PR body r1
  table "XM3 … one 10 s deadline for the whole hook".
- **Code:** the deadline reaches only `bounded(run)` (the subprocesses) and the two `future.result` waits. Three
  steps never look at it, and all of them run AFTER the subprocess phase: `asks(root)` `:561` (it loads and parses
  `gen-dashboard.py` and `dashboard-entries.md`), `transcript(...)` `:571` (it reads up to MAX_TRANSCRIPT = 256 MB and
  `json.loads` every user line), and `owner_items`.
- **Input:** `main(["--snapshot"], stdin_text={transcript_path: a 250 MB JSONL of human prompts})`, with a fake gh
  that takes 7.9 s (under its own 8 s cap).
- **Observed:** with an instant fake run, `elapsed 6.0s` for the transcript alone. With the 7.9 s gh,
  `rc 0 elapsed 19.6s (SNAPSHOT_BUDGET 10.0, hook timeout 15)`. In the real hook the harness kills it at 15 s, after
  the receipt was written (first) and before the snapshot. The print then says "SNAPSHOT: STALE" or
  "CANNOT RUN — the PreCompact hook did not write it". That is honest, but it is the very loss the deadline was
  claimed to prevent. The real transcript here is already 79 MB (docstring `:37`).
- **Fix:** EITHER check the deadline in `read_transcript` and the record loop, with a MAX_TRANSCRIPT sized to the
  time that is left, and the section then says `NOT EXTRACTED (deadline)` (the true bound, and a case to pin it);
  OR reword every sentence above to "every SUBPROCESS ends by one 10 s deadline; the transcript read is bounded only
  by MAX_TRANSCRIPT".

### M6 (Major): the "never 'the owner said nothing'" promise fails when answers survive but prompts do not
- **Sentence:** docstring `:57-58` "If the transcript has user entries and NONE is `origin.kind == \"human\"`, the
  section says the format may have changed — NOT EXTRACTED, never \"the owner said nothing\"."
- **Code:** `owner_section` `:332` gives NOT EXTRACTED only when `not prompts and not answers`. Answer turns are
  `origin: null` (`:281-282`), so they do not depend on the field whose loss the guard is about.
- **Input:** a human prompt with NO `origin` field (the format change the guard exists for), followed by an
  AskUserQuestion pair.
- **Observed:** `### Prompts (last 0 of 0, newest last)` / `- none in the transcript`. That is exactly "the owner said
  nothing", and it sits under a heading the next window is told to prefer to the summary.
- **Fix:** test the condition on prompts alone. If there are user entries that are neither answers nor tool
  results, and none of them is human, the PROMPTS sub-section says NOT EXTRACTED, whatever the answers say. Add that
  case.

### m7 (Minor): the print's first line dates and describes a compaction it then refuses to show
- **Sentence:** `:700-701` "COMPACTION HAPPENED at <receipt time> — … the state below is derived from disk; items the
  summary dropped are listed."
- **Input:** `render_print` with a receipt from session OTHER, 3 days old, and SessionStart session `S`.
- **Observed:** `COMPACTION HAPPENED at 10-25 06:46 PDT — … items the summary dropped are listed.` and then
  `RECEIPT: STALE … NOT shown.` The date belongs to another session's compaction, and nothing is listed.
- **Fix:** when `gate` is set, print `COMPACTION HAPPENED (time unknown: <gate reason>)` and leave out the
  "derived/listed" clause.

### m8 (Minor): "can NEVER match the compaction that follows" (`:498-499`, and `:16-17` "can never pass for this one")
- **Input:** the same session, a receipt plus a snapshot and an audit from a compaction 20 minutes earlier, where
  this compaction's PreCompact never ran (the launcher NOT RUN, python dying before `:774`, a hook disabled).
- **Observed:** both OLD files print as this compaction's, under `COMPACTION HAPPENED at 06:26`. The receipt
  supersedes only when the NEXT PreCompact writes one. **Fix:** say "unless this compaction's PreCompact did not
  run; the 30-min STALE_AFTER is the only bound then". Or have PostCompact write the receipt's epoch into the audit
  and require it to be newer than the receipt.

### m9 (Minor): CLAUDE.md names only two of the failure words the block prints
- **Sentence:** `CLAUDE.md:63` "a CANNOT RUN or STALE line there means that part was not captured".
- The block also prints `NOT CHECKED` (`:398`, `:674`), `UNAVAILABLE` (`:646`), `NOT EXTRACTED` (`:333`), `NOT READ`
  (`:545`), `TRUNCATED` (`fit`, `:176`) and `status UNKNOWN` (`:403`), and each of them also means "not captured".
  A reader who follows the rule as written treats those as captured. **Fix:** "any CANNOT RUN, STALE, NOT CHECKED,
  UNAVAILABLE, NOT EXTRACTED, NOT READ or TRUNCATED line", or a single shared word.

### m10 (Minor): "every AskUserQuestion answer" (backlog row; PR body hook table) overclaims
- `owner_section` gives answers at most `room // 2` characters (`:348`) and says the rest are "older not shown".
  `read_transcript` reads only the last 256 MB, so an answer from before that window is not counted at all. Even
  then the header says "(N in the transcript …)" (`:350`). **Fix:** "the newest AskUserQuestion answers that fit",
  with the header "N in the last <size> read".

### m11 (Minor): the PR body says the review has not run, while also saying round 1 was folded
- `pr361.md`: "NO-REVIEW: … the dual review is still to run" next to "## Review round 1 (Codex) — folded". The
  `NO-REVIEW:` line also makes `check-merge-ready` HOLD. **Fix:** replace it with the real state (the r1 Codex half
  is folded; the Claude half is this round), or drop it.

### m12 (Minor): the backlog row still says "trust" after r1 narrowed it to RECORDED
- Backlog row: "says to read them first and to trust the owner's quoted answers over the summary". `CLAUDE.md:65-66`
  now says "RECORDED, not proven … Prefer them to the summary's paraphrase, and verify one". **Fix:** use the
  CLAUDE.md wording.

### m13 (Minor): `main_checkout`'s docstring cites a rule source that is not on this branch or on master
- `scripts/session-state.py` (the `main_checkout` docstring): "The rule is backlog #363's (`goal-tree.py`)". Neither
  `HEAD` nor `origin/master` has `scripts/goal-tree.py`. It exists only on the unmerged commit `420cbe05`, and
  backlog #363 is OPEN. The PR body repeats "backlog #363's rule". **Fix:** cite a copy that exists, such as
  `check-ci-watched.py:64-93` or `backfill-work-lines.py:197`, which use the same `--git-common-dir` rule, or say
  "the same rule as the unmerged backlog #363 branch".

## Checked and found TRUE (stated so the reader can see what was looked at)
- "82 cases": `compaction-state.py --self-test` gives `82/82` (run in the temp copy). "57 cases":
  `session-state.py --self-test` gives `57/57`. Mutations: the manifests hold 39 and 30, which matches
  `EXPECTED_MUTATIONS` (`check-plan-code.py:1920,1934`).
- `RECORDED in the transcript, not proven` (`:328`): the code only pairs ids and checks fields, and claims no
  authorship, so the heading is accurate. The XB1 provenance checks are present in the code (`:270`, `:283`, `:289`).
- `names every item that COULD be checked … NOT a complete check` (`:670`): this form is printed exactly when
  `unchecked` is non-empty, so it is accurate where it fires. The defect is the inputs that never reach it (M3, M4).
- Ledger refusals (symlink, not a regular file, oversized) all start with `LEDGER_REL` (session-state `_read_whole`),
  so the `ledger_ok` test at `:564` does catch them. The gap is only the main-checkout fallback (M4).
- The `--add` help and `waits_on_owner` agree (an exact prefix on `what`).
- Every hook script uses the `|| echo … $?` form. `$?` there expands to python's status, which is correct.

## Summary
Blocking 0 · Major 5 (M1, M3, M4, M5, M6) · Minor 8 (m2, m7–m13).
M1 and M3 make the audit's completeness claim false on TODAY's real state (five of the seven open PR numbers collide
with backlog rows; 37 unresolved asks against 5 audited). M5 is a bound stated as covering the whole hook while it
covers only the subprocesses.

VERDICT: NOT CONVERGED
