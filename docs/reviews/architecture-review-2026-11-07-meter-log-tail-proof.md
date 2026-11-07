Reviewed head: f9f62589

> **For the r4 fold of `meter-log-tail` (PR #531, backlog #501).** Triggered by **THRASHING** in one component, the
> cut-tail completeness proof in `pace_line` (`scripts/check-usage-pace.py`): r2's two findings were caused by r1's
> fix, and r3's R3-F1 by r2's fix (`docs/dev-process.md` → *Phases*).
>
> **Verdict: redesign.** Replace the ORDER-based proof (no disorder among horizon rows, plus "an earlier window's row
> precedes this window's first row") with a TIME-based proof over a stated **writer contract**: rows are stamped at
> append time, within a skew `S` = 1 h. The part read answers only when its OLDEST row is more than `S` older than the
> time it must reach back to, and a part that itself breaks the contract by more than `S` is refused. This is candidate
> (d) below, a corrected form of the brief's (a). It deletes the horizon, the `resets_at` order check, `earlier_window`
> and `this_window_seen`. **BLOCKERs: none.** Three items are filed, not built (§7).

# Phase 6 architecture review (narrow, triggered by thrashing): the cut-tail proof in `pace_line`

Scope: `pace_line`, `read_meter`, `_read_tail`, `TAIL_MISSES_MIDNIGHT` and `TAIL_OUT_OF_ORDER` in
`scripts/check-usage-pace.py`, and the writer, `~/.claude/statusline.sh` (read only). Nothing was changed or committed.

Read first:
- `CONTEXT.md` (*Soundness check*: "a hand-rolled parser CANNOT be made correct. It CAN be made unable to be silently
  wrong");
- `docs/adr/`: no ADR covers the meter log, the pace line or the statusline, so none is re-litigated;
- backlog row 501;
- `docs/reviews/codex/meter-log-tail-r1-codex.md`, `claude/meter-log-tail-r1-claude.md`,
  `coordinator/meter-log-tail-r1-coordinator.md`, `claude/meter-log-tail-r2-claude.md`,
  `coordinator/meter-log-tail-r2-coordinator.md`, `codex/meter-log-tail-r3-codex.md`, and the decision-log row;
- `docs/review-method.md` → *Can a redesign remove it?*

Nothing under `.claude/plans/` was read. Every experiment ran in a `git archive HEAD` copy, or on a COPY of the real log
(`~/.claude/meter/log.jsonl` was only read, once, by `cp`). The scripts are outside the repository, in
`/Users/kujinlee/.claude-tmp/claude-501/-Users-kujinlee-code-agentic-ai-docs-youtube-playlist-summaries-cloud/f7c144b8-1b6c-4db3-8ef1-932d4e701b12/scratchpad/arch/`:
`proto.py` (the options, as functions beside HEAD's `pace_line`), `extra.py`, `xcut.py`, `real.py`, `scale.py`,
`sweep.py`, `sweep_d.py`, `stale1.py` and `analyse.py`.

## 1. Thrashing or prose floor?

**Thrashing, and design-caused.** Each finding is a behavioural defect with an input that was run:

| Round | Finding | Caused by | What it does |
|---|---|---|---|
| r1 | C1 (Codex), Medium | (the PR itself) | A row stamped 1 h before midnight, appended after a later row, gives the wrong 55 (the whole log gives 92.5) |
| r1 | R1-F3 (Claude), Low | (the PR itself) | A reset between midnight and the part's first row is refused needlessly |
| r2 | R2-F1 (Claude), Medium | r1's C1 fix | The order check spans the whole ~280-day part, so one 1 s inversion refuses the line for ~280 days |
| r2 | R2-F2 (Claude), Low | r1's F3 fix | A stale `resets_at` after this window's rows sets `earlier_window`, giving the wrong 94 |
| r3 | R3-F1 (Codex), Low | r2's horizon | Disorder that crosses the horizon is not checked; the wrong 94 again |

**The cause, in one sentence: the proof needs a property of the rows that were NOT read, and every fold tried to check
it with a proxy computed from the rows that WERE read.** Under a cut, the only thing that can put a wrong start into
the answer is an unseen row. Its relation to the seen rows cannot be observed. So each in-part proxy is either too
broad (r1's whole-part order check, which refuses for months on harmless disorder) or leaves a hole (r2's horizon). The
next fold would add a clause to the horizon, and the round after that would cross the new clause.

Two measurements make this concrete.

**R3-F1's wrong answer does not need the horizon at all.** It needs only one earlier-window row appended late, with the
part itself in perfect order (`xcut.py`):

```
unseen: (M−1h, 85, R)      seen, in order: (M−5d, 30, R−7d), (M+60, 88, R), (M+180, 89, R)      now = M+10h
f645d4bd (PR's first head)  whole (92.5, '')  cut (94.0, '')
302625b4 (r1 fold)          whole (92.5, '')  cut (94.0, '')
f9f62589 (HEAD)             whole (92.5, '')  cut (94.0, '')
```

So R3-F1 is an instance of the blind spot the docstring already states ("disorder that CROSSES THE WINDOW EDGE cannot
be seen"), present on every head of the PR. The horizon did not create it; the r2 fold only moved one specific set of
rows from "refused" to "answered".

**HEAD is also wrong on logs the writer really produces.** A seeded sweep (`sweep.py`: 300 random worlds of 10 to 80
rows, every cut position, each cut answer compared with the same log read whole):

| Generated logs | HEAD: ok / refused / **WRONG** | (d): ok / refused / **WRONG** |
|---|---|---|
| Strict time order, no stale rows | 10,785 / 2,484 / **0** | 10,321 / 2,948 / **0** |
| Strict time order, 5% stale old-window readings | 4,227 / 9,119 / **32** | 10,348 / 3,030 / **0** |
| Disorder up to 1 h (in contract), 5% stale | 2,263 / 10,821 / **23** | 10,404 / 2,703 / **0** |
| Disorder up to 4 h (contract broken), 5% stale | 991 / 12,310 / **24** | 2,025 / 11,300 / **0** |
| Disorder up to 1 day (contract broken), 5% stale | 390 / 12,925 / **95** | 306 / 13,093 / **11** |

The second row is the one that matters: **in strict time order**, a stale session's old-window row that happens to be
the part's first row sets `earlier_window`, and HEAD answers from a later row. Deterministic form (`stale1.py`):

```
unseen: (M−30m, 75, R)   seen: (M+24m, 97, R−7d), (M+50m, 70, R), (M+55m, 78, R)   now = M+3h
whole (87.5, '')   HEAD cut (85.0, '')   (d) cut (None, TAIL_TOO_SHORT)
```

HEAD's `resets_at` decrease check cannot see it, because the decrease (R, then R−7d) crosses the cut. Stale readings are
real here: the writer stamps the time of the APPEND, but the reading is the session's last API response, and the real
log holds one five-hour `used_percentage` that goes DOWN (7 → 6, rows 334–335, 12 s apart), which only two sessions
with different readings can write.

## 2. The writer, verified

`~/.claude/statusline.sh` lines 48–55 (read at 2026-11-07 04:29):

```sh
if [ -n "$RL" ]; then
  {
    MDIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/meter"; mkdir -p "$MDIR"
    KEY=$(printf '%s' "$RL" | jq -c '[...]')
    LASTKEY=$(tail -n 1 "$MDIR/log.jsonl" 2>/dev/null | jq -c '...')
    [ -n "$KEY" ] && [ "$KEY" != "$LASTKEY" ] && printf '{"at":%s,"rate_limits":%s}\n' "$(date +%s)" "$RL" >> "$MDIR/log.jsonl"
  } 2>/dev/null || true
fi
```

- **It is the only writer found.** `grep` over `~/.claude/*.sh`, `~/.claude/hooks`, `~/.claude/*.json`, crontab and the
  repository's `scripts/` and `.claude/hooks` finds no other append. `~/.claude/meter/regress.py` only reads it. The
  self-test writes one under a fake `HOME`.
- **`at` is `$(date +%s)`, evaluated in the same command as the `>>` append.** The gap between the stamp and the append
  is the time between a command substitution and the next `write(2)` in one shell: milliseconds, or seconds under
  memory pressure. A process stopped in that window (SIGSTOP) is the only way to stretch it to hours.
- **It runs once per session, with no lock.** Concurrent sessions can therefore interleave by that gap: the brief's
  observation holds.
- **The reading `RL` is NOT stamped at append time.** It is the session's last rate-limit response. So a row's `at` is
  the append time, but its `used_percentage` and `resets_at` can be stale. This is why any proof that depends on
  `resets_at` being in file order is unsound against this writer (§1).

**The real log** (a copy taken 2026-11-07 04:29, `analyse.py`): 613 lines, 612 rows with a `seven_day` window (line 441
has only `five_hour`), 2026-11-01 02:13 to 2026-11-07 04:28 (6.09 days), 147.2 bytes a row, 50 to **159** rows a day
(median 83). **0** inversions of `at`, 0 equal `at`, smallest gap 2 s (5 gaps ≤ 3 s, 16 ≤ 10 s). **0** decreases of the
weekly `resets_at`, across the one reset in the sample (2026-11-06 02:00 PST to 2026-11-13 02:00 PST). Every row is
stamped at least **185 s** after its window's start (`resets_at` − 7 d); the first row of the new window came 185 s
after the reset.

## 3. The writer contract

Two clauses. The proof in §5 uses nothing else about rows that were not read.

- **W1 (append-time stamps, bounded skew).** A row appended after another is stamped no more than `S` before it.
  `S` = `METER_SKEW_S` = 3600 s. It covers concurrent sessions (milliseconds to seconds) and clock steps after
  sleep or NTP (seconds), with three orders of magnitude to spare. It is broken only by a clock that is wrong by more
  than an hour, a process stopped between `date` and `>>`, or a change to the writer.
- **W2 (a reading is stamped inside its window).** A row whose reading has `resets_at` R is stamped no earlier than
  R − `SEVEN_DAY_S` − `HORIZON_SLACK_S`. This is the bound `window()` already enforces on the cache ("a reset is at most
  one window ahead"). A stale reading only makes `at` LATER than the response, which is the safe direction. Measured
  margin on the real log: 185 s past R − 7 d, so 3,785 s past the bound.

W1 can be CHECKED inside the part read (the canary, §5), and only there. Across the cut it is assumed. **No rule that
reads only the part can detect a breach of W1 that lies entirely across the cut:** a row appended 11 days late is
byte-for-byte a legitimately old row unless the rows before it are read. That is the honest bound, and it is a property
of the writer, not a seam in the checker.

## 4. The options

For each option: which finding's shape it handles soundly, its needless-refusal risk, its size, and whether a self-test
can exercise it. "In contract" means the repro satisfies W1 and W2. All results are from `proto.py`/`extra.py`, which run
every review's repro through HEAD and the option prototypes.

| | Option | C1 | R2-F1 | R2-F2 | R3-F1 | Needless refusal (measured) | Size | Self-test can exercise it? |
|---|---|---|---|---|---|---|---|---|
| — | **HEAD** (horizon + `resets_at` order + `earlier_window`) | literal repro refused; **in-contract variant (30 min) WRONG 55**; **0.5 h variant WRONG 75** | old inversion ok; **a 1 s inversion inside 2 weeks refuses up to 2 weeks** (projection: 112/112 sampled hours refused at 1 inversion per 200 rows) | refused, but a stale row that is the part's FIRST row is **WRONG** even in strict order (32 in the sweep) | **WRONG 94** (and the in-order variant, on every head) | inversions and stale rows inside 2 weeks; projection 8/112 hours refused from one stale row | as now | only the cases each fold added; the sweep shows the class |
| (a) | **As briefed:** canary over the whole part + "the start row sits ≥ S before midnight" | refused (canary) | ok | refused | refused | **refuses every reset day**: the real reset is Fri 02:00 PST, so no this-window row exists before midnight on ~22 h of each week once the log is cut; R1-F3 refused | small | yes, but the rule is UNSOUND in contract: unseen (M−1.5 h, 85), seen (M−2 h, 50), (M+60, 88) → **WRONG 75**. "S before midnight" bounds the start row, not the rows before the part |
| (b) | **Drop the proof:** cut → newest row ≤ midnight in the part, else refuse | **WRONG 55** (literal repro) | ok | refused | refused | **refuses every reset day** (~22 h a week), and R1-F3 | smallest (≈ −15 lines) | yes, but the blind spot is not one sentence: any unseen newer row ≤ midnight gives a wrong start, in contract (the 0.5 h variant → 75) |
| (c) | **Rotation by the writer** (the statusline keeps the log under the bound) | n/a: never cut | n/a | n/a | n/a | none | outside the repo (`~/.claude/statusline.sh`); `regress.py` reads the full history, so rotation must keep it (a second file) | no: the self-test cannot reach `~/.claude`. The original brief forbade it |
| **(d)** | **Writer contract + time witness + canary** (§5) | refused, in and out of contract (literal: canary, 3,660 s late > S; 30 min: witness) | **ok** (≤ S disorder is never refused; no horizon) | **refused** (no proof from `resets_at` at all; stale rows are ignored as the whole-log rule ignores them, and the stale-first-row case is refused) | **WRONG 94: out of contract** (11-day late append across the cut; §3 says why no rule over the part can see it). Moved inside S of the unseen row, it is refused | **0 on the real log at any part longer than 28.2 h; 0 in the 300-day projection, with or without 1–3 s inversions or stale rows** (below) | ≈ −12 lines of proof, +6; one constant, one reason renamed | **yes**: the rule is pure, and a seeded sweep over in-contract logs (0 wrong) with an out-of-contract control (goes red) runs in 0.5 s |

**Why not the others.** (a) as briefed and (b) both refuse every reset day once the log is cut, and both give a wrong
answer in contract. (c) removes the problem but lives outside the repository, and it does not need to be built for the
guide to be correct; it is filed. HEAD continues the thrash: its proof depends on file order of `resets_at`, which this
writer does not guarantee.

### The needless-refusal risk of (d), measured

1. **The real log, every cut** (`real.py`). For every hour of the 6.09 days and every cut size in 1 KiB steps, each
   cut answer was compared with the log read whole at that hour (TZ `America/Los_Angeles`): 6,173 cuts. HEAD:
   5,159 ok, 1,014 refused, **0 wrong**. (d): 5,119 ok, 1,054 refused, **0 wrong**. **Every part longer than 28.2 h
   answered under (d)** (HEAD: 22.6 h). The refusals are parts too short to prove anything.
2. **The threshold, derived.** (d) refuses a contract-keeping part only when its oldest row is less than `S` older than
   the start row, or, when no this-window row is at or before midnight, newer than R − 7 d − 2 h, which is at most
   7 d 2 h before now. At 4 MiB ÷ 147.2 B = 28,498 rows, that needs ≥ 28,498 rows in 7 d 2 h, i.e. **≥ 4,020 rows a
   day: 25× the busiest measured day (159)**.
3. **The projection** (`scale.py`). The real log's own gaps were tiled back 300 days with weekly Friday 02:00 resets:
   30,094 rows, 4,841,960 bytes. It was read through the real `_read_tail` at the real 4 MiB bound (the part spans
   260.6 days), every 3 h over the last 14 days (112 samples):

   | Log | HEAD: ok / refused / wrong | (d): ok / refused / wrong |
   |---|---|---|
   | clean | 112 / 0 / 0 | 112 / 0 / 0 |
   | a row stamped 1–3 s before the row above it, 1 row in 200 (≈ 0.5 a day) | **0 / 112 / 0** | 112 / 0 / 0 |
   | one stale old-window row 10 min after each reset | 104 / **8** / 0 | 112 / 0 / 0 |

   ⚠ The injected rates are ASSUMED, not measured: the real log shows 0 inversions in 611 pairs, which bounds the rate
   at about 0.5 % a pair (95 %), not at zero. The point is the shape: HEAD refuses on any such event for up to two
   weeks; (d) never does.
4. **What (d) does refuse for a long time.** A breach of W1 by more than an hour inside the part refuses until it
   leaves the part (~280 days at the bound). That is a genuine clock fault, where NOT RUN is the correct answer, and the
   message names the two rows, so deleting the late row clears it.

## 5. The rule, for a test-first implementer

**Constants.** Add `METER_SKEW_S = 3600` with a comment naming W1. Do not reuse `HORIZON_SLACK_S` for it: that constant
means reset rounding, and one constant means one thing. Rename `TAIL_MISSES_MIDNIGHT` to `TAIL_TOO_SHORT` ("the part
read does not reach back far enough to prove today's start%") and `TAIL_OUT_OF_ORDER` to `TAIL_CONTRACT_BROKEN` ("the
part read holds a row stamped more than an hour before an earlier row, so the log's rows are not stamped as they are
appended"). Neither old name describes its new condition.

**`pace_line(text, now, resets, why, cut)`:**

1. Walk every line, oldest first, with today's skip and parse. For each row that parses, if `is_number(at)`:
   - if `max_at` is set and `at < max_at − METER_SKEW_S`, set `breach` (keep the first such pair for the message);
   - `max_at = max(max_at, at)`, `min_at = min(min_at, at)`.
   This covers rows of every window, rows with an out-of-range `used_percentage`, and rows stamped after `now`.
2. The selection of `before` and `after` is UNCHANGED (this window, `0 <= p <= 100`, `at <= now`; newest `at <=
   midnight` with `>=` for ties, else oldest after midnight).
3. If `cut and breach`: return `(None, TAIL_CONTRACT_BROKEN)`.
4. If `cut`: `needed = before[0]` if `before` else `resets − SEVEN_DAY_S − HORIZON_SLACK_S`. If `min_at is None` or
   `not min_at < needed − METER_SKEW_S`: return `(None, TAIL_TOO_SHORT)`. **Strict `<`.**
5. Otherwise as today. Uncut, steps 3 and 4 are skipped, so the whole-log answer is unchanged.

**Delete** `horizon`, `prev_at`, `prev_r`, `earlier_window`, `this_window_seen` and `out_of_order`, and the docstring
paragraphs about the horizon and the `resets_at` order. The docstring states W1 and W2, the proof below, and the bound
in one sentence: *a row appended more than an hour late, with the lateness lying entirely before the part read, is
outside the contract and cannot be seen by any rule that reads only the part.* Backlog row 501's ⚠ BOUND text is
replaced the same way.

**The proof** (for the docstring, briefly). Let `u` be any unseen row; it precedes every seen row in the file, so by W1
`at_u ≤ min_at + S`.
- With `before` present, step 4 gives `min_at < at_B − S`, so `at_u < at_B`, and `u` cannot be a newer row at or before
  midnight. Ties cannot reach `u` either, since `at_u < at_B` strictly.
- With `before` absent, step 4 gives `at_u < R − 7 d − 1 h`, so by W2 `u` is not a row of this window, and neither
  `before` nor `after` of the whole log can be unseen.
- The order of SEEN rows never matters, because the selection does not depend on file order.

**R1-F5 stays declined.** `min_at` and the canary need every row, so the walk stays whole (0.21 s at the bound, r2).

**Verified in a scratch copy.** Patching this rule into `git archive HEAD` (`treed/`; the old reason names kept so the
diff isolates the rule) leaves **369/379** passing. The 10 that flip are exactly the fixtures listed in §6 under
*re-pinned* and *deleted*; the 4 MiB FALSIFIER case, the C1 case and every read/arity case still pass.

## 6. The cases that must exist

Use `NOW` (local midnight), `WR = NOW + 3 d`, `LAST = WR − 7 d`, `HZ = WR − 14 d` and `S = METER_SKEW_S`, as the suite
does. "At scale" means the part also holds an old row (for example `NOW − 280 d`), as every real part at the bound
does. Each case below was run against the prototype; "red on HEAD" means HEAD's answer differs.

**New (write first):**

1. **⭐ R3-F1, the review's exact rows, as the BOUND case.** Unseen `(NOW−3600, 85, WR)`; part `(HZ+1, 30, WR−7d)`,
   `(HZ−1, 20, WR−14d)`, `(NOW+60, 88, WR)`, `(NOW+180, 89, WR)`; `now = NOW + 10 h`. Whole 92.5; cut **94.0**, not
   refused. The case name says it is a W1 breach across the cut (rows appended 11 days late) and so outside the
   contract. ⚠ It pins the stated bound: a later change that detects it goes red and must update the bound sentence.
2. **⭐ R3-F1 in contract:** the same, with the two old rows restamped `NOW − 5400` and `NOW − 5760` (within S of the
   unseen row) → `TAIL_TOO_SHORT`.
3. **⭐ C1 in contract (30 min):** unseen `(NOW−1, 85, WR)`; part `(NOW−1800, 10, WR)`, `(NOW+60, 88, WR)`;
   `now = NOW+600` → `TAIL_TOO_SHORT`. **Red on HEAD (55).**
4. **⭐ The (a)-as-briefed counterexample:** unseen `(NOW−7200, 50, WR)`, `(NOW−5400, 85, WR)`; part `(NOW−7200, 50, WR)`,
   `(NOW+60, 88, WR)` → `TAIL_TOO_SHORT`. **Red on HEAD (75).**
5. **⭐ A stale first row in strict order:** unseen `(NOW−1800, 75, WR)`; part `(NOW+1440, 97, LAST)`,
   `(NOW+3000, 70, WR)`, `(NOW+3300, 78, WR)`; `now = NOW + 3 h` → `TAIL_TOO_SHORT`. **Red on HEAD (85.0; whole 87.5).**
6. **⭐ A stale old-window row after the reset, at scale:** part = old row, `(NOW−3600, 85, WR)`, `(NOW+60, 88, WR)`,
   `(NOW+120, 97, LAST)`, `(NOW+180, 89, WR)`; `now = NOW+10h` → 92.5. **Red on HEAD (refused).**
7. **⭐ A 1 s inversion inside two weeks, at scale:** part = old row, `(NOW−3600, 85, WR)`, `(NOW+61, 88, WR)`,
   `(NOW+60, 88, WR)` → 92.5. **Red on HEAD (refused).**
8. **Witness boundaries, both branches.** Part `(B0−S, 40, LAST)`, `(B0, 85, WR)` with `B0 = NOW−3600` → refused;
   `(B0−S−1, …)` → 92.5. Part `(W0−S, 40, LAST)`, `(NOW+60, 88, WR)` with `W0 = WR − 7d − HORIZON_SLACK_S`,
   `now = NOW+10h` → refused; `W0−S−1` → 94.0.
9. **Canary boundaries, on rows of an EARLIER window** (so the selection is not involved): a row exactly `S` before the
   running maximum → answers; `S+1` before it → `TAIL_CONTRACT_BROKEN`; and a row `S+1` before an EARLIER row but not
   before its immediate predecessor → `TAIL_CONTRACT_BROKEN` (pins the running maximum against a pairwise check).
10. **Reset day, at scale:** the window began at 02:00 after midnight (`resets = NOW + 2h + 7d`), part = old row,
    `(NOW−3600, 99, NOW+2h)`, `(NOW+2h+60, 1, resets)`, `(NOW+2h+600, 2, resets)`; `now = NOW+10h` → 21.96. (Pins
    against a regression to (a) or (b).)
11. **R1-F3 at scale:** the r1 rows with an old row in front → answers 22.99 (the r1 repro's own value).
12. **⭐ The soundness sweep.** A seeded generator (as `sweep_d.py`: 60 worlds, 10 to 80 rows each, disorder up to `S`,
    5 % stale old-window readings, resets from 2 h to 6 d after midnight) and every cut position: **0** cut answers that
    differ from the whole log. Its CONTROL, the same generator with disorder up to one day, must produce **at least one**
    differing answer, so the sweep is shown able to go red (measured: 3 wrong of 2,623; 0.5 s for both).

**Re-pinned (the 10 that flip on the prototype; each must keep what it protects):**
- *a tail that starts MID-LINE*, *one invalid byte in the tail*, *two rows with the SAME time*, *a cut part that reaches
  back through LAST week's row* (51.5) and *R1-F3* (51): each part is too short in time to prove anything under (d).
  Add an old row at the front so each still tests its own subject (the line drop, the byte, `<` against `<=`, the
  earlier window, the reset). R1-F3's 3-row form becomes a refusal case.
- *disorder among rows of an EARLIER window counts too* (3,600 s): within S, so it no longer breaches; move the second
  row to 3,601 s earlier, or let case 9 replace it.
- *R2-F2's three variants* and *the earlier window's row PRECEDES* case: still refused, now `TAIL_TOO_SHORT`. Keep the
  rows; change the expected reason.

**Deleted:** *an inversion INSIDE the horizon … still refuses* and *the horizon's boundary*: the horizon no longer
exists. Their r2 mutations go with them (§8).

**Unchanged and still required:** the 4 MiB FALSIFIER, the C1 literal repro (now refused by the canary, 3,660 s > S),
the *read WHOLE* controls, every read, arity, deadline, FIFO and UTF-8 case.

## 7. Filed, not built

- **The writer contract has no guard in the repository.** W1 and W2 rest on `~/.claude/statusline.sh`, which is outside
  the repo. An edit that stamps the API response time, batches appends, or adds a second writer would break the proof
  silently. Proposed: track the statusline in the repo (or a local-only check that reads it and asserts the stamp and
  the append are one command), so a change to the writer is a reviewed change. ⟦kind: defect⟧
- **Rotation by the writer (option c).** It removes the cut entirely. It must keep the history `regress.py` reads.
  Outside the repo; the PR's brief forbade it. ⟦kind: improvement⟧
- **Stale readings also reach the WHOLE-log rule.** The newest row at or before midnight may be a stale session's reading
  of this window (a lower `used_percentage`). That is the #500 rule, not the cut, and the line is a guide. Observed once
  in the five-hour window (7 → 6), never yet in the weekly one. ⟦kind: observation⟧

## 8. Mutations the fold needs

Remove the r2 entries for the horizon (widened, `>=` → `>`, narrowed to one week), the `resets_at` decrease check (removed,
never advancing), the file-order condition on the earlier window, and "this window's first row never marked", plus the
r1 F3 entry bound to the earlier-window line. Add at least: the canary removed (killed by case 9 and the C1 literal); `<`
→ `<=` in step 4 (case 8); `needed − S` → `needed` (case 3); `before[0]` → the window bound in the B-present branch
(case 4); the window bound loses `HORIZON_SLACK_S` (case 8b); the running maximum replaced by the previous row (case 9c);
`min_at` taken only over this-window rows (case 10 or 11). Re-pin `expected_mutations.py`.

## 9. Stop condition for later rounds

A later finding in this component is **admissible** only if it gives one of:
1. a log that satisfies W1 (skew ≤ 1 h, everywhere, including across the cut) and W2, where a cut answer differs from
   the whole log's without a refusal;
2. a needless refusal of a part that keeps the contract and spans more than 7 d 2 h + S;
3. a defect in the reading, wiring, message, or a case that cannot fail.

A repro that needs rows appended more than an hour late, with the lateness lying before the part read, is the **stated
bound** (case 1). It is answered by citing this document and is neither folded nor filed again.

**FAILS IF:** after the fold, the sweep (case 12) finds any in-contract cut answer that differs from the whole log; or
its control finds none; or the real log, cut at any size whose part spans more than 28.2 h, is refused; or HEAD's
`pace_line` still reads `resets_at` order or a horizon. If two consecutive rounds after the fold again bring
fix-induced, admissible findings in this component, stop folding and take option (c): remove the cut, rather than
prove anything about it.
