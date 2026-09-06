# The banner guard judges a turn that has finished being written

> **Anchor:** `status-visibility` — **ADR:** none
> **Goal:** A person who was away can see the current state, what changed, and what needs them —
> without reading the chat transcript.

**Backlog #96.** **v4, 2026-09-06.** The structural half of #96, deferred out of PR #225 when
option B (retract the guard's precision claim in prose) shipped instead — the half the row calls
*"a spec, not a patch"*.

**DECIDED 2026-09-06 by the user: the per-session journal at Stop (§3.1).** v3 had switched to
`UserPromptSubmit`; round 2 refuted that mechanism's premise and the user reverted. Both rounds, both
halves, NOT CONVERGED. Round files: `docs/reviews/{claude,coordinator}/banner-guard-prior-turn-r{1,2}-*.md`.

**The decision rests on one asymmetry, and it is worth stating once rather than re-deriving:**
`UserPromptSubmit` reads the sentinel *after* the turn it describes, and by then the state is gone —
so its race is about **time** and cannot be repaired without the very state it exists to avoid. The
journal's race is about **storage**, and a per-session file repairs it. Their failure modes differ in
the same direction: a **silent miss** of this guard's own class, versus a **noisy CANNOT RUN**.

⚠ **v4 IS NOT A REVERT TO v2.** v2 never saw round 2. Two round-2 findings apply to the journal design
as well and are folded here: the window-selection Blocking (§3.5) and the **unfalsifiable F11** (§7),
which was measured to pass unconditionally — 1828 windows, 0 violations, true by construction.

⚠ **Two claims made in earlier versions were WRONG and are corrected, not quietly dropped**, because
this spec's own §1.2 is about not doing that. v1 said `UserPromptSubmit` would misfire on *every* turn
that finished a plan — false (`:326-327` returns QUIET before `armed` is read). v3's review then said
the `unbannered` branch was safe under a missing sentinel — also false (§3.2).

⚠ **Header order is load-bearing** — `check-anchors.py:61` sets `HEAD_LINES = 10`.

---

## 1. The problem, measured

`scripts/check-banner-armed.py` reads the transcript of the turn **it is currently ending**:

```python
records = records_since_last_user(Path(path).read_text().splitlines())   # :480
```

At Stop time the turn's final assistant message has not been flushed, so the closing
`## ▶ STEP n of n` is invisible. A job that announced and completed every step reads as
partway-done.

### 1.1 What was already established (row #96, and it holds)

Two hook-time observations, taken from real runs and not from a model:

* session `f3ab79ef` — `highest_banner` over the first 60 transcript lines returns `(2, 3)`, which
  is exactly what the hook logged; over the first 62 lines it returns `(3, 3)`.
* session `2ace2045` — the hook record at line 1102 has `## ▶ STEP 6 of 6` sitting **earlier in the
  file**, yet the log line for 09:53:46 reads `STEP 5 of 6`. Record order in the JSONL is message
  sequence, **not** read-time visibility.

### 1.2 What this spec adds — the size of the class

Measured 2026-09-05 over **524 transcripts / 2628 windows / 2104 completed turns**, driving the
guard's own `records_since_last_user` boundary rule, `texts_of` and `highest_banner` by import.
The live reader is **modelled** by dropping the final assistant text block of a completed turn.

⚠ **THE CORPUS IS LIVE, AND THE COUNT MOVES — do not "correct" one of these numbers to the other.**
A second run ten minutes later counted **2629** boundaries over the same 524 files under the same
rule. The extra one is this session's own transcript gaining a user message *while the measurement
was being written*: the measurer is inside the population. Both numbers are right for their moment.
Any later re-run will differ again, so these are timestamps, not invariants — a re-run that reports
2628 is not a regression, and pinning either value in a gate would be pinning the clock.

| quantity | value |
|---|---|
| completed turns | 2104 |
| turns that used a banner at all | **48** |
| turns whose closing banner the live reader could not see | 9 |
| …of those, turns where the invisibility **changed the verdict** | **8** |
| turns that looked banner-less but were not (`unbannered` false positive) | 1 |

⚠ **The denominator is 48, not 2104.** A turn that never banners cannot hide a banner. Quoting
*9 of 2104* would render the defect as noise — the recorded shape *a measurement is only as good as
its CORPUS*.

**The two rates are DIFFERENT and are stated separately** (r1 Codex, Low — v1 collapsed them into a
single "one in six", which matched neither):

* **9 of 48 — 1 in 5.3** bannered turns hid their closing banner from the live reader;
* **8 of 48 — 1 in 6** had that invisibility *change the verdict*.

The second is the defect rate; the first is the exposure.

⚠ **The truncation is a MODEL, and bounds the CLASS, not the RATE.** It asserts what a reader
missing the final text block would conclude. It is not a capture of real hook-time file state; §1.1
supplies that, twice. No claim is made here about how often the flush actually loses the message.

### 1.3 ⛔ CORRECTION TO ROW #96 — the race is BIDIRECTIONAL

The row states: *"The race costs this guard precision, not the case it was built for."* **That is
incomplete.** Verified by hand in session `2ace2045`, whose banners across one turn are, in order:

```
(1,3) (2,3) (3,3) (1,5) (2,5) (3,5) (4,5)
```

* truncated (live) view → `highest_banner` = `(3, 3)` → `step >= total` → **QUIET**
* full (prior-turn) view → `highest_banner` = `(4, 5)` → `step < total` → **WARN**

So the race can also **silence a warning that was owed**. The guard loses recall, not only
precision. The row must be corrected when this lands; it currently understates its own defect.

⚠ **A latent second issue, named and DEFERRED.** That turn ran two sequences with different totals,
and `highest_banner` maximises on `step` alone across the whole window, so it compared a step from
one sequence against a total from another. This spec does **not** fix that — it is a separate defect
with a separate falsifier, and folding it in here would make one change answerable for two rules.
It is listed in §8.

---

## 2. What the guard must select — the judged turn

### 2.1 One boundary rule, not two

`records_since_last_user` already encodes the real-user boundary rule, with two measured exceptions
(tool results; `isMeta` records that are not genuine messages). That rule is **not duplicated**.
Instead it is generalised — but **not as a `list[list[dict]]`**, which r1 showed cannot work:

```
TurnWindow = (opener: dict | None, body: list[dict])
windows(records) -> list[TurnWindow]                  # pure; the SAME boundary rule
windows(records)[-1].body == records_since_last_user(lines)
```

⚠ **The window must carry its OPENER, and v1's flat form made that impossible** (r1 Codex, Medium).
`records_since_last_user` sets `start = i + 1` (`:162`), *excluding* the boundary record — but the
journal is keyed on that record's `uuid` (§3.4). A flat window either includes the opener, and the
equality with today's function is false, or excludes it and cannot supply the key. The pair resolves
both: equality is asserted on `.body`, identity comes from `.opener`.

⚠ The opener is load-bearing for **three** things, not just the key — it also identifies the window
for the log line (§6) and for F3. So this finding held through the v3 detour, when there was no
journal at all, and holds now that there is one again.

⚠ **THE DEGENERATE CASE, which v1 asserted away** (r1 Claude, High). With **no** real-user boundary
at all, today's function returns **every** record — `start` stays `0` and `:163` returns `records[0:]`.
A naive split returns `[]`, and `[-1]` raises `IndexError` **inside a Stop hook**, turning a warn-only
observer into a traceback. Reachable: a transcript whose only `user` records are tool results and
injected `isMeta` records has no boundary, and both exclusions are documented as real at `:158-161`.
**`windows()` returns one window with `opener=None` and `body=`all records** in that case, preserving
today's semantics.

A second implementation of one rule drifts — recorded, and paid for in this repo.

### 2.2 ⛔ The judged turn is the last NON-EMPTY window before the live one

Measured 2026-09-05 on this session's own transcript: a slash command emits **two consecutive real
user records** — the command, then its `<local-command-stdout>` reply — so the window between them
contains nothing:

```
window 3 opens at rec 107  '<command-name>/goal</command-name> …'
window 4 opens at rec 108  '<local-command-stdout>Goal set: fix backlog #96</local-command-stdout>'
```

Window 3 is empty and sits immediately before the live window.

**A naive "judge the second-to-last window" therefore judges nothing, stays QUIET, and reports
success** — the *green check over the wrong subject* shape, rebuilt inside the fix for it.

⛔ **THE PREDICATE IS "CONTAINS AN ASSISTANT RECORD", NOT "AN ASSISTANT TEXT BLOCK".** v1 said text
block; **both** review halves rejected it independently, which is the strongest signal round 1
produced.

A turn can make only tool calls and emit no text — `Edit`, tool_result, stop. Under v1's predicate
that window counts as empty, and two things break at once:

* **It is skipped, so the `unbannered` class becomes structurally unreachable for exactly the turns
  it targets.** That window has `edited=True`, unticked steps and no banner — the plan-without-a-banner
  branch at `:309-322` is *precisely* about it. v1 would have made the guard appear to cover its own
  subject while never seeing it.
* **It disagrees with every other notion of "a turn happened".** A turn exists when the assistant
  ran, which is what both the Stop hook and the transcript record — not when it happened to speak.

Two predicates for "a turn happened" is the *two mechanisms for one concern* shape that
`scripts/check-vocabulary-collisions.py` exists to catch. **One predicate: a window is judgable iff it
contains at least one `assistant` record.**

⚠ **Both consequences are live again.** This finding was raised against the journal design; the v3
detour removed the journal and with it the key-desynchronisation half, leaving only the coverage half.
v4 restores the journal, so **both** apply: a tool-only turn would be journalled but not selected, and
the coverage gap would make the plan-without-a-banner class unreachable. The coverage half was always
the more serious, and neither is optional now.

The slash-command shells of §2.2 still drop out — they contain **zero** records, so they are excluded
because there is no assistant activity, not because there is no text.

If no such window exists — the first substantive turn of a session — there is **no subject**, which
is QUIET. That is categorically different from *cannot reach the subject*; §5 keeps them apart.

---

## 3. Where the judgement happens — decided: at Stop, with a per-session journal

`decide()` is pure and takes four inputs. After this change `texts` and `edited` come from the
**prior** turn, so `armed` and `steps` must describe that turn too. Everything below is about making
all four inputs come from the same era.

### 3.1 ✅ CHOSEN — sample at the Stop of turn T, judge turn T at the Stop of T+1

**The sample point already exists and is already correct.** `block-idle-stop.sh:62` runs this guard
**ahead of** the blocking check, and the file says why:

> *"it is REQUIRED, because check-plan-progress.run_decide UNLINKS `.claude/executing-plan` when the
> last step is ticked, so running after it reads a deleted sentinel."*

So at the Stop of turn T this guard observes the sentinel exactly as turn T left it. **The defect is
that the observation is discarded.** It is kept for one turn, and nothing else about the sampling
changes.

```
Stop of turn T
  1. windows(transcript)            ; select the judged turn (§2.2)
  2. read journal                   ; armed/steps sampled at the judged turn's own Stop
  3. judge                          ; decide(texts, armed, steps, edited) — all four from turn T-1
  4. write journal for turn T       ; unconditional, before any early return (§5.0)
```

**The guard does NOT move.** It stays in `block-idle-stop.sh`, keeps its position ahead of the
blocking check, and keeps the exit-code contract that file already documents. No new hook event, no
`.claude/settings.json` change, no new wrapper.

### 3.2 ❌ REJECTED — `UserPromptSubmit`, carrying no state

Chosen in v3 and reverted in v4 **on the user's decision**, after round 2 refuted its premise. It is
recorded in full because it was live for a version and its appeal is genuine: it needs no state, and
it dissolves every concurrency problem the journal has.

**⛔ Its premise is false** (r2 Codex, Blocking). v3 claimed that at `UserPromptSubmit` the sentinel is
*"exactly as that turn left it"*. `.claude/executing-plan` is a **workspace-global mutable file**.
Between turn T-1 ending and the next prompt it can be changed by the human (`--tick`, `--pause`,
`rm`), by another session in the same working copy, or by another session's Stop hook. v3 deleted the
journal file's race and inherited the sentinel's.

**⛔ And the two races are NOT equivalent — this is what decided it.** The journal's race is about
**storage**, and a per-session file repairs it (§3.4a). This one is about **time**: by the moment
`UserPromptSubmit` reads the sentinel, the prior turn's armed state is *gone*. Recovering it requires
sampling at the Stop of T-1 — which is §3.1. **`UserPromptSubmit` cannot be repaired within
`UserPromptSubmit`.**

**⛔ Its failure mode is a SILENT MISS of this guard's own class** (r2 Codex, High). Verified:

```python
steps = _plan_steps() if armed else _UNSET     # :490
...
unticked = 0 if steps is _UNSET or steps is None else steps[1] - steps[0]
if armed and unticked > 0 and edited:          # :309 — cannot fire when armed is False
```

`armed=False` forces `steps=_UNSET`, hence `unticked=0`, hence the branch is unreachable. A turn that
**was** armed, edited files, left steps unticked and emitted no banner returns **QUIET** whenever the
sentinel vanished — paused, deleted, finished, or cleared by another session. That is the
plan-without-a-banner class, the case backlog #95 exists for, missed in silence. The journal's failure
mode is a **noisy CANNOT RUN**, which is strictly preferable: this project's rule is that a check
which cannot reach its subject must say so.

⚠ **A correction that belongs here, because the record should show how the reasoning moved.** v3's
§3.2 argued the residue was narrow but landed on turns that under-announce. The r2 Claude half then
walked the `unbannered` branch and concluded the class was *safe* — **that was wrong**, and the Codex
half found the paused/deleted/other-session cases it had missed. The blind spot is larger than v3
described, not smaller.

**Also lost in the move, and it is not cosmetic** (r2 Codex, Medium): a `UserPromptSubmit` hook exiting
non-zero surfaces only the **first stderr line**. Every warning this guard emits is multi-line, and the
lines after the first carry the hedging and the CANNOT-RUN instruction. The advisory channel is
degraded by the move, not merely relocated.

### 3.3 ❌ REJECTED — judge prior-turn text against the CURRENT sentinel at Stop

A plan armed during T-1 and cleared during T reads as "never armed". Same defect as §3.2 and
**unbounded** — at Stop the closing banner is invisible too, so it fires whenever a plan ends. Strictly
worse than both alternatives above.

### 3.4 The journal

One JSON object **per session** at `.claude/banner-turn-state/<session_id>.json`, rewritten at every
Stop.

**(a) PER SESSION, not one shared file** (r1, Blocking — both halves). A single fixed path is shared by
every session in the working copy, and this project runs concurrent sessions routinely:

```
session A, Stop of A1  -> writes {uA}
session B, Stop of B1  -> writes {uB}        ← clobbers A's record
session A, Stop of A2  -> judged turn is A1; stored key is uB -> MISMATCH -> CANNOT RUN
```

Both sessions then report CANNOT RUN for as long as they overlap. `run_decide` already reads
`data.get("session_id")` for `log_line` (`:505`), so the identifier is in hand. A file per session
needs no read-modify-write, so two sessions cannot lose each other's records to a torn update. Written
via temp file + `os.replace`. Stale files are prunable and harmless.

**(b) TWO KEYED SAMPLES, not one** (r1 Codex, Blocking). A blocked stop re-fires the hook **inside the
same turn** — `check-plan-progress` returns BLOCK, the assistant continues, and stops again. The hook's
own feedback is `isMeta` and not a boundary, so the live turn is unchanged. With one record the
still-needed sample is already overwritten:

```
Stop of T-1     -> journal {u1}
turn T opens (u2); first Stop of T -> judges u1 ✓, overwrites journal with {u2}
BLOCKED; assistant continues
continuation Stop of T -> judged turn is STILL u1; journal says u2 -> CANNOT RUN
```

**Fields:**

| field | meaning |
|---|---|
| `sampled_turn_uuid` | `opener.uuid` of the turn this sample describes (the live turn at write time) |
| `armed` | `_armed()` at that turn's Stop — `true`, `false`, or `null` (unreadable) |
| `steps` | `[done, total]`, or `null` when the plan could not be measured |
| `prev_turn_uuid`, `prev_armed`, `prev_steps` | the previous sample, retained so a continuation Stop still finds its subject |
| `last_judged_uuid` | the turn a verdict was last issued for — judged once, never twice |

`last_judged_uuid` makes "exactly one verdict per turn" assertable rather than accidental, so a blocked
stop cannot inflate `.claude/banner-warnings.log` — the evidence base §6 exists to make trustworthy.

### 3.5 ⛔ Selecting the judged turn — the round-2 Blocking that applies HERE TOO

r2 Claude raised this against `UserPromptSubmit`, but it is **not** specific to that mechanism and
must not be dropped with it.

§2.2 phrases the rule as *"the last judgable window **before the live one**"*. That clause invites an
implementation to locate the live window and step back from it — and the live window is exactly the
thing whose extent is uncertain while a turn is in progress.

**The rule is simply: the last window that is judgable AND is not the one currently being written.**
At a Stop, the live turn is the one containing the records emitted since the last real-user boundary,
so the judged turn is **the last judgable window excluding it**. Stated as an ordinal step-back from a
window whose boundaries are still moving, the same rule silently selects T-2 instead of T-1 whenever
the live window's extent is misjudged — and produces a verdict attributed to the wrong turn, with no
error.

**Falsifier F3 covers it**, and is strengthened: the selector must return the same turn whether or not
trailing records have arrived in the live window.

---

## 4. Behaviour

Both warning classes judge the **same** window under one rule. Splitting them — prior-turn for
`unarmed`, live for `unbannered` — would be two mechanisms for one concern, which
`scripts/check-vocabulary-collisions.py` exists to discourage.

| judged turn | journal | verdict |
|---|---|---|
| none (first judgable turn of a session) | — | **QUIET** — no subject |
| present | a sample matches it (`sampled_turn_uuid` or `prev_turn_uuid`) | run `decide()` with the journalled `armed`/`steps` and the judged turn's `texts`/`edited` |
| present | already in `last_judged_uuid` | **QUIET** — judged once, never twice (§3.4b) |
| present | no matching sample | **CANNOT RUN** (§5) |
| present | matching sample, `armed` is `null` | **CANNOT RUN** — unchanged meaning from `:486-489` |

`decide()` itself is **not modified**. Its inputs change era; its rules do not.

**The accepted loss, stated:** the `unbannered` nudge currently arrives mid-plan, where the assistant
can act on it, and will now arrive one turn later. The mitigation is that
`scripts/check-plan-progress.py` — the **blocking** guard — is untouched and still fires live. Only
the advisory moves.

---

## 5. Cannot-run is a failure, never a quiet pass

| state | code | why |
|---|---|---|
| no judgable prior window (first judgable turn of a session) | QUIET | *no subject*, not *cannot reach* |
| prior turn exists, no journal sample keyed to it | **CANNOT RUN** | its sentinel was never sampled; judging it against another turn's sample is a guess |
| journal unreadable, or unwritable (§5.0b) | **CANNOT RUN** | the check cannot reach what it measures |
| `_armed()` returns `None` | **CANNOT RUN** | unchanged from `:486-489` |
| armed, and `_plan_steps()` is `None` | **CANNOT RUN** | unchanged from `:298-304` |
| transcript unreadable | **CANNOT RUN** | unchanged from `:291-294` |

The message must say **TREAT THIS AS NOT RUN**, matching the messages the module already emits, and
must name the journal path.

⚠ **"No subject" and "cannot reach the subject" must not collapse.** A window-selection bug returning
nothing would present as QUIET, indistinguishable from a genuinely first turn. F3 and F5 hold them
apart: F3 asserts a real prior turn *is* found when an empty slash-command window sits in front of it,
which is the only way the "nothing to judge" branch is exercised against a case where something
should have been judged.

### 5.0 Order of operations, and two precedence rules

**(a) The journal write is UNCONDITIONAL and precedes every early return** (r1 Claude, High). Today
the guard returns before doing anything else when the sentinel is unreadable:

```python
armed = _armed()
if armed is None:
    print("CANNOT RUN: …", file=sys.stderr)
    return CANNOT_RUN                      # :486-489
```

A write after that point loses the record for the turn, so the *next* Stop finds no matching sample
and reports CANNOT RUN too — one transient fault becomes two dead turns with no path back. A CANNOT
RUN *about this turn* must still leave a usable sample for the next one, which is why `armed: null`
is a legal journalled value.

**(b) A failed write outranks "no subject"** (r1 Codex, Medium). On the first judgable Stop of a
session both hold at once: nothing to judge, *and* the journal must still be written. If "no subject
→ QUIET" returns first, a failed write becomes a **quiet pass**.

```
1. compute windows; select the judged turn          (may be: none)
2. sample armed / steps for the LIVE turn
3. judge, if there is a subject and a matching sample
4. WRITE the journal                                -> failure here overrides the verdict
5. return: write failed ? CANNOT RUN : verdict
```

### 5.1 Which precedent a failed journal write follows, since two disagree

The module holds two, pointing opposite ways: the warn-log write at `run_decide:506-510` is **not**
swallowed but keeps its `WARN`, because losing the log costs only *evidence*; `_armed()` returning
`None` at `:486-489` is CANNOT RUN, because the guard cannot reach its subject.

**DECIDED: a failed journal write is CANNOT RUN** — the second row. The journal is not evidence, it is
the next turn's only input, so losing it silently degrades the guard permanently and invisibly. The
verdict already reached is still printed; CANNOT RUN replaces the exit code, not the message. Both are
non-blocking at the hook (`block-idle-stop.sh:99-104` maps any observer non-zero to exit 1), so this
costs noise, never a wedged session.

---

---

## 6. Log grammar, and the re-baseline

`log_line(reason, detail, when, session)` writes `when` and `session` for the moment of judging. After
this change the judged turn is a **different** turn, so those fields would silently describe the
wrong one.

* `when` becomes the timestamp of **the turn being judged**, taken from the boundary record where
  available, and the header comment states which turn the fields describe.
* the tab-separated shape is otherwise unchanged — nothing parses this file, verified 2026-09-04.

⚠ **`.claude/banner-warnings.log` is re-baselined again.** It was re-baselined on 2026-09-05 for
option B and has accumulated entries under the old reader since. Entries produced by a reader that
could not see closing banners cannot be compared with entries from one that can, and mixing them
rebuilds the exact defect the row describes: *a false-alarm rate partly manufactured by the reader*.

---

## 7. Falsifiers

The corpus supplies **real** fixtures. Seven of the eight verdict flips are the row's own falsifier
shape — a turn that really ended `n of n` and is warned about today:

```
12fc2cc2  live saw (2,3)   truth (3,3)
12fc2cc2  live saw None    truth (2,2)     <- the `unbannered` false positive
2ace2045  live saw (5,6)   truth (6,6)
4b541d7d  live saw (5,6)   truth (6,6)
a8887f7b  live saw (2,3)   truth (3,3)
f3ab79ef  live saw (2,3)   truth (3,3)
f3ab79ef  live saw (4,5)   truth (5,5)
```

and the eighth is the bidirectional case of §1.3.

| # | falsifier | fails if |
|---|---|---|
| F1 | a turn ending `## ▶ STEP n of n` with nothing armed is **QUIET** | it WARNs with `STEP n-1 of n` |
| F2 | the `2ace2045` sequence `(1,3)…(4,5)` **WARNs** | it is QUIET — the silenced-warning direction |
| F3 | an empty slash-command window is skipped and the substantive turn before it is judged — **and the selector returns the same turn whether or not trailing records have arrived in the live window** | the empty window is judged, the substantive one is never judged, or the answer moves with the live window's extent (§3.5) |
| F4 | a journal sample that does not match the judged turn yields **CANNOT RUN** | it judges anyway, or stays quiet |
| F5 | the first judgable turn of a session is **QUIET**, not CANNOT RUN — **provided the write succeeded** | absence of a prior turn is reported as a failure, or a failed write is masked by it |
| F6 | `windows(records)[-1].body` equals today's `records_since_last_user(lines)` on every transcript in the corpus, **including one with no real-user boundary at all** | the generalisation changed the live window, or raises on the degenerate case |
| F7 | an unwritable journal produces CANNOT RUN, never silence | the write failure is swallowed |
| F8 | a turn making **only tool calls** (no assistant text) is judged, not skipped — and its `unbannered` warning fires when it edited with unticked steps | the text-block predicate survives anywhere |
| F9 | a **blocked** stop re-firing within one turn issues **exactly one** verdict for the judged turn, and never CANNOT RUN | the single-sample journal survives; `last_judged_uuid` is not consulted |
| F10 | two sessions stopping alternately in one working copy each judge their own prior turn | journal state is shared across sessions |
| **F11** | ⛔ **at hook time, the judged window's final assistant record is present** — recorded per run and compared against the same window on a later run; a discrepancy means a late flush and the guard says so | the check is a transcript-ORDER assertion (see below), or a late flush passes unnoticed |

F6 is the regression falsifier: this change must not alter what the boundary rule means.
F4/F7/F9/F10 are round 1's three Blockings plus the write-failure rule, each a falsifier rather than a
promise.

⛔ **F11 WAS A TAUTOLOGY IN v2 AND v3, AND BOTH REVIEW HALVES MISSED IT UNTIL IT WAS RUN.** It read:
*"for every completed window in the corpus, the judged window's last record precedes the live window's
first"*. **Measured: 1828 judgable windows, 0 violations** — and zero is the dangerous shape here,
because `windows()` **splits on record order**, so the assertion restates the splitter's definition.
It is true of any corpus and any flush behaviour, including one where the guard is completely broken.

**The design's central assumption was therefore guarded by a check that passes unconditionally.**
Recorded rule: *state the observation that would make it FAIL — if none can be named, it is not a
gate.* Flush timing is not a property of a finished transcript at all, so **no corpus assertion can
ever be this falsifier**; only an observation taken at hook time can, which is what F11 now is.

⚠ **This durability question is the one thing in the spec still resting on argument.** §1.1's two
observations are hook-time evidence about the *live* turn; nothing establishes that the prior turn is
always durable one Stop later. The journal design gives a full turn of margin — strictly more than
today's zero — but that is a comparison, not a proof, and F11 must actually run before this is called
done.

---

## 8. Out of scope — named, not hidden

* **`highest_banner` conflates sequences with different totals** (§1.3). Real, separate falsifier,
  separate fix. Belongs on the backlog when this lands.
* **A session's final turn is never judged.** Structural: a turn is only observable once finished.
  Accepted by the row.
* **The promote-to-blocking decision.** This restores the log's ability to serve as evidence; it does
  not spend it. The log needs a fresh population under the fixed reader first.
* **`decide()`'s rules.** Unchanged, deliberately.

---

## 9. Guard contract obligations

`scripts/check-ratchet-contract.py` requires every guard on disk to have a `--self-test`, no
fail-open handler, and a caller. This guard has all three and keeps them. In addition:

* new self-test cases for **F1–F12**, with the §7 fixtures recorded as data;
* ⚠ **the CALLER DOES NOT CHANGE — and that is a v4 property worth asserting, not assuming.** v3
  moved the guard to a new `UserPromptSubmit` hook; v4 keeps it in `.claude/hooks/block-idle-stop.sh`
  at `:62`, ahead of the blocking check, where its sampling is already correct (§3.1). No
  `.claude/settings.json` change, no new wrapper, no change to that hook's exit-code arithmetic. A
  diff touching either is a signal the revert was incomplete;
* the declared self-test count is updated in the canonical form — `check-selftest-counts.py` pins
  this file's count, and a stale declared count is itself a gate failure;
* a mutation manifest entry per new decision predicate, each killed **via the case it names**;
  `EXPECTED_MUTATIONS` rises and never falls.
