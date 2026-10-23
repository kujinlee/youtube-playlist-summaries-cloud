# banner-thread-armed — round 1 — Claude half

Range: `cd7134f8..7651c914` (branch `feat/banner-thread-armed`, 2 commits: `ba47679f`, `7651c914`).

Method: everything below was executed against a temp copy (`git archive 7651c914` into a scratch
repo, `HOME` redirected) unless labelled UNVERIFIED. Replays read the real transcripts under
`~/.claude/projects/<slug>/*.jsonl` read-only, importing the delivered module from the copy.
Baseline of the delivered suites on the copy:

- `check-banner-armed.py --self-test` → `209/209 self-test cases passed`.
- `check-plan-code.py --mutate .` scoped to this file's manifest (other manifests and their
  `EXPECTED_MUTATIONS` rows removed in a second copy, `node_modules/typescript` copied in) →
  `65 mutation(s), 65 killed, 65 attributed to the case each names, 0 survivor(s)`.

So the cases are NOT ambient: each fails for the reason its name gives. The findings are about
what the cases choose to describe.

---

## F1 — Major — the thread class cannot read the Thread-row shape this repo actually writes

**Where:** `scripts/check-banner-armed.py`, `thread_name` (the three regexes `_SWITCH_TARGET_RE`,
`_RESUMED_RE`, `_PLAN_NAMED_RE`) and the self-test fixtures `_BAN` / `_SW`.

**Input:** every `> **Thread:**` row in the real transcripts modified since 2026-10-10, run
through the delivered `thread_rows` + `thread_name` (`rv-tools/shapes.py`). Row counts, and in
brackets how many were the LAST row of their turn (the only one judged):

```
175 [65]  step     backtick-first  UNREADABLE   `phase6-chrome-instrument` · 5 of 6 done
 55 [19]  switched other           readable     ⤳ SWITCHED from `(session start)` → `chrome-bar-reachable` …
 32 [10]  step     other           UNREADABLE   ↳ `afk-staleplan-and-two-folds` · step 6 of 7 · ▸ 3.1 …
 19  [6]  step     other           readable     ↳ RESUMED `chrome-bar-reachable` Phase 6 · 1 of 6 done
  8  [3]  switched other           UNREADABLE   ⤳ SWITCHED — fresh session after `/clear`; no plan armed yet
  3  [0]  switched plan-word       UNREADABLE   ⤳ SWITCHED to plan `afk-r6-lows-r7-and-r18-verdict` · 1 of 5 …
  2  [1]  switched backtick-first  UNREADABLE   `three-review-rounds` · step 4 of 6 · ⤳ SWITCHED back to `#371` …
  1  [1]  switched plan-word       readable     ⤳ SWITCHED from `afk-two-folds-and-r18` … → `afk-staleplan-and-two-folds` · p…
```

The `· plan `slug` ·` form the class parses for step banners (copied from CLAUDE.md's example)
occurs **zero** times as a step row. The real step-row shape is the slug FIRST, in backticks.
Of the 81 judged step rows, **6 are readable (7%)** — all of them `↳ RESUMED`. Over the 25 most
recent transcripts (`rv-tools/replay.py`): 15 turns carried thread rows, **13 had an unreadable
last row**, 1 fired, 1 matched.

**What happens, executed end to end through `run_decide` (`rv-tools/scen.py`), sentinel armed on
`slice-a` at the judged turn's stop, the banner on a different thread `side-b`:**

```
[S2-backtick-first]     rc=0   > **Thread:** `side-b` · 0 of 3 done
[S4-switched-to-plan]   rc=0   > **Thread:** ⤳ SWITCHED to plan `side-b` · 1 of 3
[S5-arrow-no-RESUMED]   rc=0   > **Thread:** ↳ `side-b` · step 2 of 3
[S3-switch-then-step]   rc=0   ⤳ SWITCHED … → `side-b`  then, same turn, a step banner `side-b` · 1 of 3 done
[S6-control-switch-last] rc=1  ⚠ THREAD NOT ARMED — … thread `side-b` … names `slice-a`.
```

S2 is the motivating defect exactly — a side job bannered while ANOTHER plan is armed — and it is
silent. (The `unarmed` class does not cover it: a plan IS armed.) S3 matters most: the convention
puts the side job's first step banner in the same turn as the switch, so the readable switch row is
followed by an unreadable step row, the last row wins, and the class is quiet **without** falling
back. The docstring's stated miss ("followed IN THE SAME TURN by another switch") understates it:
it is followed by ANY step banner in today's shape.

The suite cannot see this because every step fixture (`_BAN.format("plan `s-one` · …")`, TE5's
`plan `solo-z``) is written in the one shape real transcripts do not use — *measure the population
the code sees*.

**Fix:** read a step row's slug when it is the row's first token (`^\s*`slug``), after `↳`
with or without `RESUMED`, and after `SWITCHED to (plan )?`; keep "several candidates → None".
Add cases whose literals are copied from the corpus rows above (at least the first, third and
sixth), plus S3 as an end-to-end case. ⚠ Fixing this makes F2 common, so the two must land
together.

---

## F2 — Major — "not armed at stop" is not "unknown to the work-lines page", and the warning's remedy destroys an existing plan

**Where:** `unarmed_thread` / `decide_thread` (compares against the sentinel stem only) and the
message text `python3 scripts/begin-plan.py {name} "title|doing|why" ...`.

The class justifies itself as *"the work-lines page knows a thread only once begin-plan.py has
armed it, so this thread's work is invisible there"*. But `gen-work-lines.py` reads
`.claude/plans/*.md` — a thread is known once its plan FILE exists, whether or not it is armed now.
The class asks something else: whether the sentinel names it at that stop. Those differ on
**correct** sequences:

- a parent thread resumed after its child plan completed (`check-plan-progress` unlinks the
  sentinel at zero; nothing re-arms the parent);
- a turn whose last banner is on thread X and which ends with `begin-plan.py --finish` (used in
  13 transcripts since 2026-10-01, often as `--finish && begin-plan.py <next>`).

**Executed** (`S7-resume-parent`: `.claude/plans/slice-a.md` exists, nothing armed at the judged
stop, last row `↳ RESUMED `slice-a` after the side job · 2 of 2 done`, banner `STEP 3 of 3` so no
original class fires):

```
[S7-resume-parent] rc=1 :: ⚠ THREAD NOT ARMED — the previous turn ended on thread `slice-a` …,
   and .claude/executing-plan names nothing.
      The work-lines page (scripts/gen-work-lines.py) knows a thread only once
      begin-plan.py has armed it, so this thread's work is invisible there. Arm it:
log: v1 …  S7-resume-parent  unarmed-thread  step slice-a
```

The message is false here (the page shows `slice-a`), and it is logged into the count the owner is
told to flip BLOCK from. Today this is rare only because of F1 (`RESUMED` is the one step shape
that IS readable — it is precisely the shape this false alarm uses).

**Worse, the remedy is destructive.** Executed in the temp copy: arm `slice-a` with three steps,
tick one, `--finish`, then run the command the warning prints:

```
BEFORE                                   AFTER following the warning
- [x] **Step 1 of 3** — one              - [ ] **Step 1 of 1** — title
- [ ] **Step 2 of 3** — two
- [ ] **Step 3 of 3** — three
```

`cmd_new` keeps `parent`/`serving` for an existing slug but rewrites its steps, so the ticked
history the page displays is erased. With `THREAD_BLOCK` on, this text is fed to Claude as the
instruction that clears the block.

**Fix:** when `.claude/plans/<slug>.md` exists, either stay quiet (the page knows the thread) or
emit a different message whose remedy is `begin-plan.py --plan .claude/plans/<slug>.md`; print the
`<slug> "title|doing|why"` form only when no plan file exists. Add S7 as a case (quiet, or the
`--plan` remedy), with a fixture plan file present — every current thread case runs with no plan
file for the named slug, so none can distinguish the two questions.

---

## F3 — Minor — the BANNER_RE comment states a blindness wider than measured

**Where:** comment above `BANNER_RE`, and the module docstring bullet "the three ORIGINAL classes
saw no current banner from 2026-10-16 until then".

**Executed** (`rv-tools/olddates.py`, assistant text blocks matching the OLD pattern):
`2026-10-16 a257f699 26`, `2026-10-17 239d5d35 3`, `2026-10-17 5a5d6b21 1`, `2026-10-18
154b7568 23`, `2026-10-19 014deb4c 2`, `2026-10-19 358872ec 14`. Across judgable turns since
10-16: 67 bannered turns under the new pattern, **21** under the old. The log's own `2026-10-18
unarmed` entry is one of those being seen. The direction of the claim (stamped banners were
invisible) is right; "no current banner" is not — unstamped banners were still emitted, and
seen, through 10-19.

**Fix:** "stamped banners were invisible; unstamped ones, last emitted 2026-10-19, were still
seen". (Separately noted, pre-existing, not this range: `STEP 4b of 6` and `## ▶ 12:10 PDT · STEP`
are still unmatched — 7 such lines since 10-16.)

---

## F4 — Minor — BLOCK mode blocks the NEXT turn's stop, which arming cannot clear, and double-counts with `unarmed`

**Where:** `run_decide` §5 + hook `BANNER_RC == 4 → exit 2`; owner-facing docstring "MODE".

**Executed** (`rv-tools/blk.py`, `THREAD_BLOCK=True` in the copy): stop 1 (turn b1 ends on the
switch) → `0`; stop 2, ending an UNRELATED turn b2 (`"unrelated answer"`) → `4`, message `⛔
THREAD NOT ARMED (BLOCKING) — the previous turn ended on thread side-b …`; stop 3, the continuation
→ `0`. So: no loop (good, the one-verdict-per-turn gate holds), but the block holds the user's
reply to b2 for something b1 did, and arming during the continuation cannot change the verdict
(it is fixed by the sample taken at b1's stop) — the block is a one-shot delay plus instruction,
not a gate the instruction satisfies. The owner flipping the switch should know that; the
docstring does not say it.

Also executed (`S8-double-log`: nothing armed, `STEP 2 of 3`, `↳ RESUMED `side-b``): one turn,
one root cause, two log rows — `unarmed-thread step side-b` and `unarmed STEP 2 of 3`. The count
the owner is told to read includes turns another class already reports.

**Fix:** state both in the MODE paragraph; consider logging the thread class only when no
original class fired, or have the owner's count exclude co-fired turns.

---

## Checked, no finding

- **(d) rc 4 with the switch off:** unreachable — `decide_thread` returns `THREAD_BLOCK_RC` only
  for `block=True`, `run_decide` passes the constant, and the remaining exits are 0/1/2 (an
  uncaught raise is 1). The new `if` precedes the `exit 1` arithmetic but follows every observer,
  so no sibling's stderr or verdict is lost; `PROGRESS_RC` blocking still exits 2 earlier.
  `"$CI_RC" != "0"||` (missing space) parses: `bash -n` clean and `[[ "1" != "0"|| … ]]` evaluates.
  F6d is structural only; the hook mapping has no mutation, as the manifest comment says.
- **(e) journal:** the upgrade turn (no `plan_slug`) is quiet (TE8 sound — its input would warn
  with the key present); the absent key survives both shifts; the continuation path overwrites
  `plan_slug` with the later sample exactly as `armed` is overwritten. No stale-slug path found.
- **(a) fences, `Line:` rows, prose mentions, subagent text:** fenced examples skipped; `Line:`
  never read; a Thread row outside a banner is read only if it contains `⤳ SWITCHED`;
  `texts_of` reads only `assistant` text blocks, so a subagent's report (a `tool_result`) is not
  read. A closing summary that repeats a `> **Thread:** ⤳ SWITCHED` row in a blockquote WOULD be
  judged (UNVERIFIED as occurring — no instance in the corpus rows above).
- **(c) widened BANNER_RE on today's turn shape:** `▸ [mm-dd hh:mm]` sub-steps and `⏳ Waiting`
  lines do not match (they lack `## ▶ … STEP n of N`); the three original classes now behave on
  stamped banners as they did on unstamped ones (ST1–ST7). `unarmed` will resume firing on
  unarmed bannered loops — its specified behaviour, not a wrong fire.

VERDICT: NOT CONVERGED
