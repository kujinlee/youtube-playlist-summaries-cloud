# work-lines-backfill — round 1 — Claude half

Range: `cd7134f8..0d448b67` (`feat/work-lines-backfill`, HEAD `0d448b67`).

Mandate: refute. Can it write a WRONG parent link into the owner's real plans? **Yes. I ran it on
a copy of `.claude/plans/` with `--write`, and it writes at least two wrong `transcript` links and
one link whose label is false.** Everything below was executed against the real transcripts
(read-only) and a copy of the plans (`cp -p` into my scratchpad). Nothing in the repo, the worktree
or the real `.claude/` was written. Each claim is labelled with what I ran. Anything not executed
is marked UNVERIFIED.

Baseline: `--self-test` 70/70. `--ground-truth` gives `OK`. On the copy, the dry run reproduces the
brief's totals exactly (`keep 56, keep-banner 24, no-marker 43, untouched 2 (of 125 plans)`).

---

## F1 — BLOCKING — a `begin-plan.py` call inside a shell loop is invisible, so the replay keeps a finished plan armed and gives it as a later plan's parent

**Where:** `scripts/backfill-work-lines.py:297`, in `find_calls.finish`:

```python
lead = words[:k]
if not all(_INTERP.match(w) or w.startswith("$") or w == "env" for w in lead):
    return
```

**Input:** `for i in 1 2 3 4; do python3 scripts/begin-plan.py --tick >/dev/null 2>&1; done`. The
simple command is `do python3 scripts/begin-plan.py --tick`. `do` is not an interpreter, so the
function returns and records no call. The same thing happens to `then`, `else`, `!`, `time` and `{`
in front of the script. The tool also never models a loop: once `do` is stripped, a loop that runs
four ticks still counts as one.

**Measured on the real corpus:** about 18 top-level commands run at the main checkout use
`for i in …; do python3 scripts/begin-plan.py --tick …; done` (my `missed.py` scan; the count
includes a few false positives that my scan's regex let in). This is the project's normal way of
ticking several steps at once.

**What it writes. Two wrong links, confirmed with direct witnesses in the transcripts:**

1. **`phase6-chrome-instrument` ← `r8-codex-fold`, verdict `keep`, labelled
   `transcript 014deb4c 2026-10-19T19:07:15.411Z`.**
   - At 17:47:56Z the plan was ticked by `for i in 1 2 3 4; do … --tick …; done; … --status`. That
     command's own result reads `.claude/plans/r8-codex-fold.md: 4/4 steps ticked, 0 remaining`.
   - At 17:48:11Z the Stop hook wrote `✅ every step in .claude/plans/r8-codex-fold.md is ticked
     (4/4). Clearing …`.
   - At 19:04:43Z, three minutes before the arm, session 014deb4c ran `cat .claude/executing-plan`
     and saw `(no sentinel armed)`.
   - The replay still holds `.claude/plans/r8-codex-fold.md 0/4` (the `--explain` output reads
     `sentinel at that arm: .claude/plans/r8-codex-fold.md 0/4`).
   - The live code would have recorded `-`. There is no banner, so nothing catches it.
2. **`backlog-249-260` ← `round5-364`, verdict `keep`, labelled `transcript fdb027d3
   2026-10-08T00:35:19.342Z`.**
   - At 10-07T09:13:18Z the command `--resume …; for i in 1 2 3; do … --tick 2>&1 | head -1; done;
     … --status` printed `ticked step 4 of 4 in .claude/plans/round5-364.md` and then
     `.claude/plans/round5-364.md: 4/4 steps ticked, 0 remaining`.
   - The turn ended 8 seconds later.
   - The replay ignores that output and keeps `round5-364.md 1/4` armed for 15 hours, through every
     other session's turn ends, until another session arms `backlog-249-260`.
   - The parent should be `-`.

A third case is the same defect with a false label. `r8-codex-fold` ← `r8-fold` is labelled
`transcript`, but the Stop hook cleared `r8-fold` at 17:00:14Z (`…r8-fold.md is ticked … Clearing`,
after the 16:59:50Z loop tick). So the replay's "armed" is wrong. The link only survives because the
banner happens to name `r8-fold`. Under the owner's option A this would be `keep-banner`, never
`transcript`, and the label exists to tell those two apart.

**I wrote them:** `--write --plans <copy>` produced

```
<!-- parent: r8-codex-fold -->
<!-- parent-source: transcript 014deb4c 2026-10-19T19:07:15.411Z -->
```

in `phase6-chrome-instrument.md`, and `<!-- parent: round5-364 -->` in `backlog-249-260.md`.

**Minimal construction** (my `repro.py`, using the script's own `_Fx`): arm `one` (2 steps), then
`for i in 1 2; do python3 scripts/begin-plan.py --tick …; done` whose result is `ticked step 2 of 2
in .claude/plans/one.md`, then a turn end, then arm `two`. Output: `{'one': '-', 'two': 'one'}`.
The live answer is `two <- -`.

**Effect of the fix, measured.** In a scratch copy I stripped leading shell keywords and treated a
call inside `for/while/until … done` as having unknown multiplicity (10 copies, so each unread tick
pushes `hi` up to `n`). Diffing the dry runs, exactly the three rows above change. `backlog-249-260`
becomes `-`. `phase6-chrome-instrument` and `r8-codex-fold` become no-marker.

**Fix:**
1. Strip the reserved words (`do then else elif ! time { if while until`) before matching the
   interpreter.
2. Treat a call inside a loop body as unknown multiplicity: a tick moves `hi` to `n`, or the state
   becomes UNKNOWN. Never "one tick".
3. Add self-test cases for a loop with and without readable output, and a mutation for each.

---

## F2 — BLOCKING — a hand edit of the sentinel is not seen when the same command also names `begin-plan.py`

**Where:** `scripts/backfill-work-lines.py:533` and `:541`:

```python
if "begin-plan.py" in cmd:
    ...
elif "executing-plan" in cmd or ".claude/plans/" in cmd:
    what = bash_mutation(cmd, cwd, root)
```

`bash_mutation` only runs when the command does **not** name `begin-plan.py`. But the project's
idiom for pausing and un-pausing is `sed -i '' '/^paused:/d' .claude/executing-plan && printf
'paused: …' >> .claude/executing-plan && python3 scripts/begin-plan.py --status`. Arming is often
done as `rm -f .claude/executing-plan … && begin-plan.py <new>` too.

**Measured:** my `mutskip.py` ran the script's own `bash_mutation` over every command that names
`begin-plan.py`. **About 60 top-level commands at the main root write the sentinel and are
skipped.** That covers pause lines appended or deleted, `rm -f .claude/executing-plan`, and
`mv /tmp/ep .claude/executing-plan`.

**Effects:**
- A missed `paused:` append leaves the replay thinking the plan is un-paused, so it clears it at the
  next turn end while the live Stop hook kept it. The next arm then gets `-` (or a banner link) that
  live code would not have recorded.
- A missed `/^paused:/d` does the reverse.
- A missed `rm` before an arm makes the replay give a parent where live recorded `-`.

Example: on 10-13T01:52:38Z (fdb027d3) the command was `rm -f .claude/executing-plan
.claude/plans/backlog-249-260-r10-review.md` followed by `python3.12 scripts/begin-plan.py
backlog-267-parser-swap …`. Live: nothing armed, so `-`. The replay gives `backlog-249-260-r10-review`
with verdict `keep` and a `transcript` label. The banner agrees on the slug, so the thread may be
right. But the label says the sentinel replay found it armed, which is false, and the owner's rule
does not allow a banner to rescue a `-` that came from a hand `rm`.

**Minimal construction:** arm `one`, then `rm -f .claude/executing-plan && python3
scripts/begin-plan.py two 'a|b|c'`. Output: `{'one': '-', 'two': 'one'}`.

**Effect of the fix, measured.** In a scratch copy I called `bash_mutation` for these commands too
and emitted the `mut` event BEFORE the `bp` event, which is conservative. The dry-run totals move to
`keep 52, keep-banner 21, no-marker 50`. The rows that lose their link include
`backlog-267-parser-swap` and `correct-arch-review-verdict`. Some of those are probably
over-inclusive hits from `bash_mutation`, which matches step text quoted inside the arm. That
over-inclusion is the safe direction the docstring itself picks.

**Fix:**
1. Always run `bash_mutation` on the command. Where a write and a call share a command, either
   order them by position in the token stream, or make the state UNKNOWN before the first call.
2. The self-test's only hand-`rm` case (`f.bash("rm -f .claude/executing-plan", "")`, near
   `:1236`) never names `begin-plan.py`. That is why it passes over this gap. Add the compound form.

---

## F3 — MAJOR — the replay starts as "nothing armed", which is a guess

**Where:** `:636`, `state: object = None`.

The corpus begins mid-history (2026-09-22T16:24Z, the oldest transcript file still on disk). The
first session in it starts with `SessionStart:clear`, so it continues a session whose transcript is
gone. Plan `merge-331-and-handoff.md` was created at 16:02Z, is not fully ticked (4 `[x]`, 1
`[ ]`), and no transcript shows how it ended.

The first arm in the corpus is `banner-blind-spot` at 16:27Z. It gets `-` and verdict `keep` purely
from the starting assumption. That breaks the docstring's "WHERE THE STATE CANNOT BE DETERMINED, NO
PARENT IS RECORDED — never a guess."

**Today it happens to be right.** That session ran `cat .claude/executing-plan … || echo "(no
armed plan)"` at 16:25:14Z and got `(no armed plan)`. I verified this; the replay did not use it.

It is still a latent wrong-link generator. The transcripts age out, so on any later re-run the
corpus starts somewhere else and the first arm inherits the same guess.

**Fix:** start in `UNKNOWN("before the first transcript")`. Resync only on positive evidence: a
`--finish` that prints `nothing was armed.`, a Stop-hook `Clearing` line, or a sentinel `cat` /
`--status` observation (see F4).

---

## F4 — MAJOR — `--ground-truth` checks one easy link, and two stronger witnesses already in the transcripts go unused

**Where:** `:90` and `:925`.

The one link it reproduces, `work-lines-backfill ← banner-thread-armed`, is an arm-while-armed 3
minutes apart in one session. It involves no turn end, no tick counting and no cross-session hand-off.
A replay that ignored every tick and every stop would pass it. So would the code with F1, F2 and F3
present, and it does. The other live link, `work-lines-always-on ← -`, is also reproduced and is
equally easy.

I ran two stronger checks.

1. **Direct sentinel observations.** This was my `obs.py`, an instrumented copy of `replay`, run
   over every `cat .claude/executing-plan` and `check-plan-progress.py --status` result at the root.
   - 28 parsed observations agree with the replay's state.
   - 1 disagreement is my filter's fault: a subagent reading a temp stage.
   - Of the ~15 unparsed "none" variants, one is a **real disagreement**: 10-19T19:04:43Z
     `(no sentinel armed)` against the replay's `r8-codex-fold 0/4`. That is F1's wrong link.
2. **The Stop hook's own clear message.** These are `attachment.hookEvent == "Stop"` records
   containing `every step in `X` is ticked (d/n). Clearing`. There are 32 since 09-23T01:56Z.
   - **The replay misses 5 of them** (`stopcmp.py`): `velocity-goal-spec` and
     `decision-route-r2-fold` (the replay state was UNKNOWN, so these are harmless), `fold-r3-claude`
     (the replay believed `0-4/6`), `r8-fold` (believed `0/6`) and `r8-codex-fold` (believed `0/4`).
   - The last two produce the F1 rows.
   - The witness is positive-only. The hook leaves an empty `hook_success` on many clears, so the 20
     replay clears with no witness are NOT shown to be wrong. I checked one: 10-22T18:14:44Z agrees
     with the live `work-lines-always-on ← -`.

**Fix:**
1. Make `--ground-truth` fail when the replay state disagrees with any witnessed observation, or
   with any `Clearing` line, at its timestamp.
2. Better, feed both in as resync events, and parse `--status` output too. Both F1 commands printed
   `4/4 steps ticked, 0 remaining` and the replay threw it away because `classify` maps `--status`
   to `ro` (`:332`, `:537`).

---

## F5 — MINOR — `--write` is not atomic

**Where:** `:906`. `p.write_text(...)` truncates and then writes, so an interrupted run leaves a
truncated plan file. Write to a temp file in the same directory, `os.replace` it, then `utime`.

The rest of `--write` checks out, all executed on a copy:
- Only plans with no marker are touched (`untouched` rows).
- mtime is preserved: a stat diff before and after showed `MTIME-PRESERVED`.
- A second `--write` run wrote 0 files, so it is idempotent.
- The real plans directory was unchanged afterwards (`diff -rq` against my snapshot).

Preserving mtime does hide the write from the page's "last touched" date. That is intended, and
nothing else I found keys on plan mtime. The `.claude/last-plan` skip reads `plan_dir.parent /
"last-plan"`. That is correct for the real layout. Today the fingerprinted plan
(`work-lines-always-on`) already carries a marker, so the skip is moot.

---

## F6 — MINOR (UNVERIFIED on real data) — "first recorded arm" is not always "creation"

`seen` keeps a slug's first arm. If the plan file was later deleted and re-armed (`rm -f
.claude/plans/X.md … && begin-plan.py X …`, a pattern that occurs, for example on 10-20T21:07:27Z),
the file on disk came from the LATER arm. Its live parent was derived then. The birth-time check
cannot catch this, because the recreated file is born after the first arm.

In the instance I looked at, both arms give `-`, so I have no wrong row to show. Treat a plan-file
`rm` as resetting `seen[slug]`, or take the parent from the arm closest to the file's birth time.

---

## Checked and not a finding

- **Other transcript directories.** No Bash `begin-plan.py` call in any other
  `~/.claude/projects/*` directory targets the main root. Their mentions are attachments and
  prompts only; I checked a known positive.
- **Banners.** Only the assistant's own `text` blocks are read, never tool results. The
  zero-banner case cannot produce `keep-banner` (`named != [cleared]`).
- **`cleared` going stale.** I traced every transition into "nothing armed" and each one sets
  `cleared`, so a stale value is never read.
- **Rendering.** The three kinds differ without colour (line style plus the text labels
  "reconstructed" and "from banner"), and the caveat sentence is accurate.

---

VERDICT: NOT CONVERGED
