# work-lines-backfill — round 3 — Claude half

Range reviewed: `a7e5046b..1b8a6255` (whole change `cd7134f8..1b8a6255`), `scripts/backfill-work-lines.py`.

**The question: would any of the 36 links the dry run writes be WRONG?** No. I walked every one
against the real transcripts and found **36 confirmed, 0 doubtful, 0 wrong**. One of them
(`memory-index-budget-fold`) is confirmed only because I inspected a command the replay cannot
reason about (M1).

How I checked (read-only, nothing outside this file written):

- I re-ran the dry run (25 `keep` + 11 `keep-banner`, 87 no-marker, 2 untouched). I also re-ran
  `--ground-truth` (`agree 164, disagree 0`, OK) and `--self-test` (229/229).
- I ran `--write` against a COPY of `.claude/plans` + `.claude/last-plan`. It wrote 36 files: 22
  `parent: -` and 14 named parents, all 14 of which exist on disk. `last-plan` names
  `work-lines-always-on`, which is already untouched, so nothing was skipped.
- For each link I took the event that last set the checkout's state before the arm (from the
  replay's own `trail`). Then I listed EVERY tool use in EVERY stream (top level and subagents)
  between that event and the arm, including the SAFE commands that `parse_command` drops before
  they become events. I looked for anything that could reach `.claude/executing-plan` or
  `.claude/plans/`.
- Every turn-end clear a link depends on is backed by the Stop hook's own
  `Clearing .claude/executing-plan` attachment, which I grepped. Every in-command checkpoint is
  backed by its printed output (`cleared …` / `no plan is being executed`), or by an `&&` chain
  that proves `--finish` ran.
- Other channels:
  - The other 18 project dirs (worktree sessions): 0 Bash/Write calls run `begin-plan`,
    `check-plan-progress` or touch `executing-plan`.
  - Codex sessions in `~/.codex/sessions`: every sentinel write found is `root=Path(td)/'repo'`
    (a temp dir), and every begin-plan run is `--self-test`.
  - User `!` bash-input: 2 instances in the whole corpus, both `git show`.
  - User prompts: none reports a hand edit of the sentinel.
  - Hooks: in all of `.claude/hooks` + `settings.json` history, only `check-plan-progress
    --decide` (the Stop clear) writes the sentinel. `--session-start` is read-only and lives only
    on an unmerged branch.
  - Plugins: no plugin references `.claude/executing-plan`.

## Findings

### M1 — MEDIUM — an opaque command is poisoned at its START, but a background one is still running when the checkpoint after it "resyncs" the state

`backfill-work-lines.py` treats an opaque op as an instant at the command's timestamp:

- `replay`'s cmd branch poisons at `e.ts`.
- `checkpoint` then lets any later observation move UNKNOWN back to known.
- `overlapping` only sets `end` for events that contain a begin-plan call (`pending[...] = ev` at
  `read_transcripts`). So `(o.end or o.ts)` collapses every other command to its start, and
  same-stream commands are skipped entirely.

A `run_in_background` Bash call returns immediately and keeps running, so a checkpoint taken while
it runs proves nothing about the sentinel after the checkpoint. The docstring's residual-bound
section names invisible arms. It does not name this.

**It happens in the 36.** `memory-index-budget-fold`, session `e2d493ff`:

- 2026-10-20T04:04:06.983Z: `run_in_background: true`, `FAIL=0\nrun(){ out=$("$@" 2>&1); … }\nfor g in check-anchors … ; do run python3 scripts/$g.py; done …`
  This is opaque, because `run` and `scripts/$g.py` are both ad hoc to the parser. It completed
  at 04:07:25.557Z (`<status>completed</status>`).
- 04:06:48.047Z: `python3 scripts/begin-plan.py --status` → `no plan is being executed (no .claude/executing-plan)`.
  This is the checkpoint, taken while the sweep was still running.
- 04:06:56.458Z: `begin-plan.py memory-index-budget-fold …` → replay parent `-`.

**The link stands on inspection.** The background body runs only tracked `scripts/check-*.py`,
which the module's own history search says never write the real sentinel. The replay did not
reach that conclusion, though. It got there by an ordering accident.

I measured this across all 36 arms. There are no foreground straddlers. Four other background
tasks have no completion record, and I resolved all four by hand:

- three were `TaskStop`ped within minutes;
- one (`b5jlbn9qx`) was a mutation sweep inside `wt-364`.

**Fix:** give every opaque cmd event an end, either its `tool_result` time or, for a background
task, its `<task-notification>` status or `TaskStop`. If neither is found, the end is the
stream's last record. A checkpoint inside an open opaque window must not lift UNKNOWN for arms in
that window. Also set `end` for every cmd event so `overlapping` can see a long foreground opaque
command in another stream. **Cost:** this unlinks `memory-index-budget-fold`, giving 35 links.
**Self-test gap:** `_Fx.bash` has no `run_in_background` shape and never emits a task
notification, so no fixture resembles this.

### L1 — LOW (latent; 0 instances today) — any top-level `end_turn` is taken as a Stop-hook run, and 272 of the 315 top-level transcripts are hookless SDK sessions

`read_transcripts` emits `Event(kind="stop")` for any top-level assistant message with
`stop_reason == "end_turn"`. `replay` then clears a fully ticked plan as `certain` whenever the
record's `cwd == root`.

In this corpus:

- 272 top-level files are `"entrypoint":"sdk-py"`: security-review sessions launched by a plugin
  hook.
- Across all of them there are **0** `hookEvent` records and **0** `stop_hook_summary` records.
  They load only `MEMORY.md` (their `instructions` attachment lists AutoMem alone), so no project
  Stop hook runs there.
- Today none of them ends with `end_turn`. Each ends `stop_reason: tool_use` on
  `StructuredOutput`, so there is **no effect on the 36**.

The path to a wrong link is direct, though. One such session ending a turn while a fully ticked
plan is armed would be replayed as a clear. The next arm would get `parent: -` and
`cleared = X`, where the truth is `parent: X`.

These sessions also ended inside three of the intervals I checked: `8398bc59` (declared-skip-r8),
`81b2109c` (round5-364) and `4555d5e6` (velocity-r3-and-pr, 0.4 s before the arm). Those three
links are right only because the replay ignores those sessions, and the evidence that it may
ignore them is the zero-hook count above.

**Fix:** count a turn end as a Stop only for streams that ever record a hook event, or only
`entrypoint` `cli`/`sdk-cli`. The three `sdk-cli` sessions on 2026-09-30 do record Stop hooks.
Add a fixture with an `sdk-py` stream.

### L2 — LOW — `SAFE["git"]`'s reason states something false

The text reads: "`.claude/` is gitignored, so commit, push, merge, checkout and reset cannot touch
it."

`git ls-files .claude` lists tracked `hooks/*.sh`, `settings.json`, `skills/`, `commands/`, and
`.claude/last-plan` shows as untracked, not ignored. Only `.claude/executing-plan`
(`.gitignore:89`) and `.claude/plans/` (`:96`) are ignored. No commit on any branch ever tracked
either path (`git log --all -- .claude/executing-plan '.claude/plans/*'` is empty). So the
conclusion holds for the subject.

The part the reason misses: a `git checkout` CAN change `.claude/settings.json` and the hook
scripts, which means it can change which Stop hook runs. "Hooks are reviewed repository code"
covers that, but only implicitly.

**Fix:** cite the two `.gitignore` lines and the empty `git log`, not "`.claude/` is gitignored".

### I1 — INFO — real shapes the fixtures do not resemble, all handled correctly today

1. **`begin-plan.py` edited in place, then used.** At 2026-10-22T16:37:53Z and 16:38:06Z, inline
   `python3 -` heredocs rewrote the main checkout's `scripts/begin-plan.py` to add parent
   derivation and `--serving`. The `work-lines-page` arm at 16:38:16Z ran that edited copy.

   The replay judged both correctly: the heredocs name `begin-plan`, so it poisoned, and the
   `--status` in the same command resynced it. The edited copy itself is the strongest witness I
   found. It already derived the parent from the sentinel and wrote no marker, which is what that
   version did when nothing was armed.

   Stated bound worth adding: the replay models begin-plan's *output*. It does not verify the
   event semantics of a working-tree-modified copy.
2. **A birth time AFTER the first arm.** `finish-364`'s file was born 6,385 s after its only
   recorded arm, because of `sed -i '' 's/of 4\*\*/of 6**/g' .claude/plans/finish-364.md`
   (`cacb274e`, 2026-10-07T04:24:02Z). The birth check passes it, correctly here, since it is the
   same plan renumbered. This is a real instance of r1 F6's blind direction, caused by an in-place
   edit rather than a re-creation.
3. **Clearing messages arrive as `hook_non_blocking_error` as well as `hook_success`.** Examples:
   20fc6768 2026-10-15T05:33:53Z and 161aad51 2026-10-22T10:04:52Z. The parser keys on
   `hookEvent == "Stop"` and the text, never the type, so it is correct. The `_Fx.clearing`
   fixture emits only `hook_success`.
4. **A non-canonical banner heading.** `rc-contract-reconciled`'s banner sits under
   `## ▶ Arming the fold`, with no `STEP n of N` and no timestamp. `live_banners` accepts any
   `## ▶`. It is genuine live text (not sidechain, not fenced), so the link is right. Note that
   "canonical shape" is not what the code checks.
5. **Two interactive sessions working one plan.** `1e3f81fb`→`2e11564a` on
   `velocity-single-owner`; `dad7f9f7`/`cacb274e` on `finish-364`. Handled, because each call is
   attributed by checkout, not by session.

### I2 — INFO — where the backfill rule and today's live rule part (owner-decided, not a defect)

Nine of the 22 `-` links are `--finish … && begin-plan <next>` in one command, in one session:

- afk-two-folds-and-r18, arch-review-marketplace, backlog-117-r3
- fold-q3-q4-then-r3, fold-r3-claude, fold-r3-codex, fold-r3-mediums, fold-r4-claude
- velocity-single-owner

Under `cd7134f8`'s `_parent_from_last_finished`, several of these would continue the finished
plan's line if its PR was open. Example: the `fold-r3-*` chain on PR #376. The backfill writes `-`
by the owner's stated rule ("nothing armed -> `-`"; module docstring, "ONE DIVERGENCE"). These
links are correct under that rule and are listed only so the owner knows which roots are
rule-made rather than observed beginnings.

## The 36 links

The "basis" column is the event that fixed the state the parent was derived from, plus what the
interval up to the arm contained. Every turn-end "Clearing" below was grepped as the Stop hook's
own attachment text.

| # | plan | parent | verdict | basis (real transcript) | result |
|---|---|---|---|---|---|
| 1 | afk-two-folds-and-r18 | `-` | keep | same command: `--finish </dev/null 2>&1 \| tail -3` → `cleared .claude/executing-plan`, then the arm (ee774183 2026-10-14T17:45:25Z). Concurrent subagent `agent-ap…` ad-hoc commands all returned before it (0 straddlers); the 17:45:13Z `rm -f .claude/executing-plan` ran after `cd …/wt-staleplan`, another checkout, and the next result says `Shell cwd was reset` | confirmed |
| 2 | approved-329-328-173 | qualify-bare-refs | keep-banner | Clearing `qualify-bare-refs` (6/6) 2026-10-21T04:41:36Z; to 05:13:37Z only read-only commands, all in 55e544f6. Banner 05:13:42Z under `## ▶ [10-20 22:13] STEP 1 of 5`: "⤳ SWITCHED from `qualify-bare-refs` (6/6 done, `837101fa`) → `approved-329-328-173`" | confirmed |
| 3 | arch-review-marketplace | `-` | keep | `--resume >/dev/null && for … --tick; done && --finish >/dev/null && <arm>`: the arm ran, so `--finish` exited 0 (5a5d6b21 2026-10-17T05:15:44Z) | confirmed |
| 4 | backfill-177-spec-plan | `-` | keep | 2026-09-26T03:36:35Z `--finish` → `cleared .claude/executing-plan`; to 03:46:06Z only grep/sed plus an AskUserQuestion | confirmed |
| 5 | backlog-117-r3 | `-` | keep | same command: `--finish 2>&1 \| tail -2` → `cleared .claude/executing-plan`, then the arm | confirmed |
| 6 | build-291-string-diff | fold-r4-codex | keep-banner | same command: tick → "✅ every step in .claude/plans/fold-r4-codex.md is ticked", `--finish` → `cleared …`, then the arm. Banner 13:04:10Z: "SWITCHED from `fold-r4-codex` (6/6 done, `80bdb8ba`) → `build-291-string-diff`" | confirmed |
| 7 | candidate-1-page-cites | `-` | keep | 5a5d6b21 2026-10-17T12:48:40Z `--finish` → `cleared` (arch-review-marketplace). Independent witness: 239d5d35 15:23:30Z `cat .claude/executing-plan` → `No such file or directory`, 16 s before the arm | confirmed |
| 8 | corpus-pass-295 | `-` | keep | Clearing `candidate-1-page-cites` (6/6) 17:00:46Z; to 17:26:15Z only `gh` | confirmed |
| 9 | decision-log-model-r1-fold | `-` | keep | Clearing `decision-log-model-redesign` (5/5) 2026-10-20T22:55:09Z; no command before the arm at 22:55:46Z | confirmed |
| 10 | decision-log-model-r2 | decision-log-model-r1-fold | keep-banner | Clearing `decision-log-model-r1-fold` (7/7) 23:07:56Z; no command until the arm. Banner 23:18:00Z: "SWITCHED from `decision-log-model-r1-fold` (7/7 done, `ae61136d` pushed)" | confirmed |
| 11 | decision-log-model-redesign | `-` | keep | Clearing `fix-322-unrunnable-gate` (4/4), session e87cc09f, 22:15:38Z; 55e544f6's interval is read-only (git status, sed, gh, `--help`) | confirmed |
| 12 | declare-all-statuses | goals-page-status | keep-banner | Clearing `goals-page-status` (4/4) 2026-10-22T02:32:46Z; over the 7.4 h interval, only inline Python reading `goals.html` and importing tracked scripts (no INLINE_UNSAFE token). Banner 09:58:30Z: "SWITCHED from `goals-page-status` (shipped, pushed)" | confirmed |
| 13 | declared-skip-r8 | declared-skip-r7 | keep | 2026-10-21T22:58:33Z ticks + `--status` show `declared-skip-r7` 5/5, still armed mid-turn. 46 s interval: no end_turn or Stop in any cli stream; sdk-py `8398bc59` ended (no hooks, L1). The arm command's `cat > <scratchpad>/r8-prompt.md <<'EOF'` reaches no checkout. Banner agrees | confirmed |
| 14 | finish-291-branch | fold-r5-codex | keep-banner | Clearing `fold-r5-codex` (5/5) 2026-10-16T14:49:38Z. Banner 14:54:05Z: "SWITCHED from `fold-r5-codex` (5/5, `6ccc23cf`)" | confirmed |
| 15 | finish-364 | finish-365 | keep-banner | same command: `--status` → `no plan is being executed`, then the arm (dad7f9f7 2026-10-07T02:37:37Z). Banner 02:37:42Z: "SWITCHED from `finish-365` (done — #365 merged `f8ae6d5d`)". Birth +6,385 s comes from the `sed -i` (I1.2) | confirmed |
| 16 | finish-365 | `-` | keep | 2026-10-06T23:06:01Z `--finish` → `cleared` (d2-main-drivable, 6/7 paused); the arm follows 9 s later | confirmed |
| 17 | fold-q3-q4-then-r3 | `-` | keep | `--finish >/dev/null && <arm>` | confirmed |
| 18 | fold-r3-claude | `-` | keep | `--finish >/dev/null && <arm>` | confirmed |
| 19 | fold-r3-codex | `-` | keep | `--finish >/dev/null && <arm>` | confirmed |
| 20 | fold-r3-mediums | `-` | keep | Clearing `fold-r3-claude` 02:52Z, then `--finish >/dev/null && <arm>` | confirmed |
| 21 | fold-r4-claude | `-` | keep | same command: `--status` → `fold-r3-mediums.md: 7/7 steps ticked`, then `--finish >/dev/null && <arm>` | confirmed |
| 22 | fold-r4-codex | fold-r4-citations | keep-banner | same command: `--finish 2>&1 \| tail -1` → `cleared`. Banner 03:43:15Z: "SWITCHED from `fold-r4-citations` (8/8, Codex half returned …)". The replay last saw 7/8 paused, which is immaterial: it is the same plan | confirmed |
| 23 | memory-index-budget-fold | `-` | keep | 04:06:48Z `--status` → `no plan is being executed`; arm 04:06:56Z. ⚠ A background guard sweep (04:04:06Z→04:07:25Z) straddles the checkpoint (M1); its body runs only tracked `scripts/check-*.py` | confirmed (by inspection) |
| 24 | memory-index-budget-r2 | `-` | keep | 04:44:52Z `--finish` → `cleared`; arm 04:45:07Z | confirmed |
| 25 | namespace-token-guard | `-` | keep | Clearing `afk-r6-lows-r7-and-r18-verdict` (5/5) 2026-10-15T05:33:53Z; nothing in any stream up to the arm reaches the sentinel or the plans | confirmed |
| 26 | phase6-fold-addendum | phase6-chrome-instrument | keep-banner | Clearing `phase6-chrome-instrument` (6/6) 2026-10-19T19:45Z. Banner 19:46:32Z: "SWITCHED from `phase6-chrome-instrument` (6/6 done, pushed `9ef6c43e`)" | confirmed |
| 27 | post-merge-360-reconcile | `-` | keep | Clearing `ship-recall-fold` (6/6) 2026-10-02T05:32:06Z. The arm command's `git checkout -q -b` cannot touch the sentinel: it is ignored (`.gitignore:89`) and never tracked | confirmed |
| 28 | r7-fold | chrome-bar-converge | keep-banner | Clearing `chrome-bar-converge` (7/7) 15:51:58Z. Banner 15:54:46Z: "SWITCHED from `chrome-bar-converge` (7/7, PR #378 open)" | confirmed |
| 29 | rc-contract-reconciled | correct-arch-review-verdict | keep-banner | Clearing `correct-arch-review-verdict` (5/5) 2026-09-30T20:34:25Z. Banner 20:48:21Z: "SWITCHED from `correct-arch-review-verdict` (5/5 done, `d3480bfc` pushed)", under the non-canonical `## ▶ Arming the fold` (I1.4) | confirmed |
| 30 | round5-364 | finish-364 | keep | 05:03:35Z `--tick` shows `finish-364` fully ticked, still armed. 2 min interval: no end_turn in any cli stream (the two `queued_command` prompts do not end a turn); sdk-py `81b2109c` (no hooks); `check-ci-watched.py` writes its own marker. Banner agrees | confirmed |
| 31 | ship-recall-fold | d1-ratchet-main-world | keep-banner | Clearing `d1-ratchet-main-world` 03:00:50Z. Banner 04:14:33Z: "SWITCHED from `d1-ratchet-main-world` (5/5 done, gate 1178 green)" | confirmed |
| 32 | split-177-from-117 | `-` | keep | 2026-09-26T04:19:34Z `--finish` → `cleared` (`velocity-single-owner`, taken over from session 1e3f81fb); arm 04:19:43Z | confirmed |
| 33 | velocity-r3-and-pr | split-177-from-117 | keep | 04:28:37Z state line shows `split-177-from-117` fully ticked, still armed. 39 s interval: no Stop in any cli stream; sdk-py `4555d5e6` ended 0.4 s before the arm (no hooks, L1) | confirmed |
| 34 | velocity-single-owner | `-` | keep | `--finish >/dev/null 2>&1; <arm>`: chained with `;`, so the finish is INFERRED (`cmd_finish`, 7958ba9e:563–568, unlinks with `missing_ok` and returns OK unconditionally) | confirmed (inference) |
| 35 | work-lines-page | `-` | keep | 16:38:06Z `--status` → `no plan is being executed`; arm 16:38:16Z, run by the edited `begin-plan.py`, which itself derived "nothing armed" and wrote no marker (I1.1) | confirmed |
| 36 | wrap-for-arch-review | `-` | keep | Clearing `fold-recall-llm-r1` (5/5) 2026-09-30T16:54:30Z | confirmed |

Totals: **36 confirmed, 0 doubtful, 0 wrong.** All 11 banner links are the assistant's own live
text: `isSidechain: false`, outside fences, and within the arm's turn. Each names exactly the plan
the replay saw cleared, and each `from` slug exists in `.claude/plans/`.

## Thrashing or prose floor?

**Neither.** This round's findings are not caused by the round-2 fold:

- **M1** sits in the checkpoint/resync model introduced in round 1 (r1 Claude F3/F4). The r2
  fold's allow-list changed what counts as opaque, not when an opaque op is assumed to act.
- **L1** dates from the first version's turn-end rule.
- **L2** is a reason string.

None of the three is a consequence of the redesign, so the thrashing condition (two consecutive
rounds of fix-induced findings in one component) is not met.

It is also not a prose floor. M1 is a real soundness gap with a real instance in the output, but
the 36 links survive it, and nothing found here makes a link wrong. The redesign's premise (an
accident must NAME the sentinel or a plan tool, or delete a whole tree) held on every interval I
walked. The only command in the 36 intervals that names the sentinel and runs in the main
checkout is a `cat` of it (`candidate-1-page-cites`), and that one corroborates the link.

M1 and L1 should be folded or filed before `--write` runs. Each is a few lines and a fixture, and
M1 costs one link. They do not block the 36 as they stand.

VERDICT: CONVERGED
