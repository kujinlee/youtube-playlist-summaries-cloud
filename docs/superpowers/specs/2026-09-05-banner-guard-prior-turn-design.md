# The banner guard judges a turn that has finished being written

> **Anchor:** `status-visibility` — **ADR:** none
> **Goal:** A person who was away can see the current state, what changed, and what needs them —
> without reading the chat transcript.

**Backlog #96.** **v3.1, 2026-09-05 — BLOCKED, see the box below.** The structural half of #96, deferred out of PR #225 when
option B (retract the guard's precision claim in prose) shipped instead — the half the row calls
*"a spec, not a patch"*. v2 folded round 1 (both halves **NOT CONVERGED**: 3 Blocking, 3 High,
2 Medium, 2 Low). Round files:
`docs/reviews/{claude,coordinator}/banner-guard-prior-turn-r1-*.md`.

⛔ **v3 CHANGES THE MECHANISM, ON THE USER'S DECISION.** v1 and v2 judged the prior turn at **Stop**,
carrying `armed`/`steps` in a journal. v3 judges at **`UserPromptSubmit`**, carrying nothing.

The chain that got here is worth keeping, because each step was a correction of the last: v1 rejected
`UserPromptSubmit` on a claim that was **false**; the Codex half refuted it by reading `decide()`;
that left the rejection resting on a narrow case whose **rate cannot be measured from transcripts at
all** (§3.2); and all three of round 1's Blockings were consequences of the journal, so dropping it
drops them. **The user chose the simpler mechanism with the residual blind spot stated (§3.2).**

⚠ **Round 1 was reviewed against the JOURNAL design.** Its three Blockings are dissolved rather than
fixed, so round 2 reviews a mechanism no reviewer has yet seen.

⛔ **v3.1 — THE MECHANISM IS BLOCKED PENDING A DECISION. Round 2 refuted §3.1's central premise.**
Both halves NOT CONVERGED: 3 Blocking, 3 High, 1 Medium, 3 Low. Round files:
`docs/reviews/{claude,coordinator}/banner-guard-prior-turn-r2-*.md`. **Do not implement §3 as written.**

**What round 2 established, and it inverts the v2→v3 decision:**

1. **The sentinel race was never dissolved — it MOVED** (Codex, Blocking). §3.1 claims that at
   `UserPromptSubmit` the sentinel is "exactly as that turn left it". False.
   `.claude/executing-plan` is a **workspace-global mutable file**. Between turn T-1 ending and the
   next prompt it can be changed by the human (`--tick`, `--pause`, `rm`), by another session in the
   same working copy, or by another session's Stop hook. v3 deleted the journal file's race and
   inherited the sentinel's.
2. ⛔ **AND UNLIKE THE JOURNAL'S RACE, THIS ONE CANNOT BE FIXED WITHIN v3.** The journal's race was
   about *storage* and a per-session file repaired it. This one is about *time*: by the moment
   `UserPromptSubmit` reads the sentinel, the prior turn's armed state is **gone**. Recovering it
   requires sampling at the Stop of T-1 — which is §3.3, the design v3 rejected.
3. **The failure is a SILENT MISS, not a false alarm** (Codex, High — and it **corrects** the Claude
   half's H2, which walked only the plan-finished sub-case and wrongly concluded the class was safe).
   Verified: `steps = _plan_steps() if armed else _UNSET` (`:490`), so `armed=False` ⇒ `steps=_UNSET`
   ⇒ `unticked = 0` ⇒ the `armed and unticked > 0 and edited` guard at `:309` cannot fire. A turn
   that **was** armed, edited files, left steps unticked and emitted no banner returns **QUIET** if the
   sentinel vanished. That is the plan-without-a-banner class — the case backlog #95 exists for —
   missed in silence.
4. **F11 cannot fail** (both halves). Measured: 1828 judgable windows, 0 violations, and it is true by
   construction because `windows()` splits on file order. It asserts the splitter, not the flush.
5. **The "unmeasurable" claim in §3.2 is too strong** (Codex, High). Measured: **20** transcripts
   reference `begin-plan.py`, **63** reference `executing-plan`, **8** contain `--tick`. Plan
   lifecycle signals *are* recorded. A lower bound is derivable; §3.2 must say "not fully measurable"
   and mine the signals before quoting only a loose upper bound.
6. **Exit 1 on `UserPromptSubmit` shows only the FIRST stderr line** (Codex, Medium), so the
   multi-line CANNOT-RUN and hedging text — the part carrying the caveats — would not reach anyone.
   The advisory channel is degraded by the move, not merely relocated.

**Where that leaves the two designs, stated for the decision rather than assumed:**

| | §3.3 journal at Stop | §3.1 `UserPromptSubmit` |
|---|---|---|
| samples `armed` at the correct instant | ✅ | ❌ — reads it later, when it may have changed |
| concurrency defect | real, and **repairable** (per-session file) | real, and **not repairable without state** |
| failure mode | false CANNOT RUN (noisy, visible) | **silent miss of its own class** |
| machinery | 4 fields of per-session state | none |

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
`records_since_last_user` sets `start = i + 1` (`:162`), *excluding* the boundary record. The finding
was raised against v2's journal key, which needed that record's `uuid` — and it **survives the switch
to `UserPromptSubmit`**, because the opener is also what identifies a window for logging (§6) and for
the F3 selection falsifier. A flat window cannot both equal today's function and name its own turn.
The pair resolves it: equality is asserted on `.body`, identity comes from `.opener`.

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

⚠ This finding was raised against the journal design, where the mismatch also desynchronised a
persisted key. **The key half is gone with the journal; the coverage half above is not**, and it was
always the more serious of the two.

The slash-command shells of §2.2 still drop out — they contain **zero** records, so they are excluded
because there is no assistant activity, not because there is no text.

If no such window exists — the first substantive turn of a session — there is **no subject**, which
is QUIET. That is categorically different from *cannot reach the subject*; §5 keeps them apart.

---

## 3. Where the judgement happens — decided: `UserPromptSubmit`

`decide()` is pure and takes four inputs. After this change `texts` and `edited` come from the
**prior** turn, so `armed` and `steps` must describe that turn too. Everything below is about how to
make all four inputs come from the same era.

### 3.1 ✅ CHOSEN — judge at `UserPromptSubmit`, carrying NO state

When the next user prompt arrives, **no turn is in flight**. The prior turn is finished and flushed,
and `.claude/executing-plan` sits exactly as that turn left it. So `_armed()` and `_plan_steps()`,
called there, describe the turn being judged **without any journal, key, or persisted sample**.

The per-turn-state question is not solved. It is **dissolved** — there is no second era to reconcile.

```
UserPromptSubmit for turn T
  -> windows(transcript)                       ; T-1 is complete on disk
  -> judged = last judgable window             ; §2.2
  -> armed/steps read NOW = state at end of T-1
  -> decide(texts, armed, steps, edited)
```

**What this removes, and it is the whole reason for the switch.** Round 1 raised three Blockings
against the alternative (§3.3). Every one of them is a consequence of carrying state across turns,
and none of them exists here:

| round-1 Blocking | under `UserPromptSubmit` |
|---|---|
| one shared journal file breaks under concurrent sessions | **gone** — no file |
| a blocked stop re-fires and clobbers the still-needed sample | **gone** — not a Stop hook |
| a failed journal write must outrank "no subject" | **gone** — nothing is written |

### 3.2 ⚠ THE KNOWN BLIND SPOT — stated, bounded as far as it can be, and NOT measurable here

`check-plan-progress.py:180-182` unlinks the sentinel when the last step is ticked:

```python
if unticked == 0:
    SENTINEL.unlink(missing_ok=True)
    STATE.unlink(missing_ok=True)
```

So a plan that **finished during turn T-1** leaves no sentinel for `UserPromptSubmit` to read, and
`armed` comes back `False` for a turn that was armed.

**That is harmless in the common case, and v1 of this spec got that wrong.** `decide()` returns early:

```python
step, total = banner
if step >= total:
    return QUIET, ""        # :326-327 — BEFORE `armed` is consulted
```

A turn that finished its plan **and announced its last step** is QUIET whatever the sentinel says —
and prior-turn judging is precisely what makes that closing banner visible. v1 claimed *"every turn
that finished a plan would warn wrongly"*; that was false, and the Codex half refuted it by reading
the code.

**The residue, stated exactly.** A false `unarmed` warning needs **both**:

1. the plan finished during that turn (`unticked == 0`, so the sentinel is gone), **and**
2. the highest banner visible in that turn is **below** its total.

⛔ **HOW BIG IS IT? THIS CORPUS CANNOT SAY, AND THE OBVIOUS NUMBER IS MISLEADING.** Measured
2026-09-05: of **50** bannered completed turns, **26 ended below their total**. That is *not* the
error rate — it is an upper bound so loose it is nearly uninformative, because condition 1 is
invisible to a transcript. Sentinel state is a file, and files leave no trace in the JSONL. A turn
that ended below its total with **no plan ever armed** is the `unarmed` warning firing **correctly**,
which is this guard's entire purpose; those turns are inside the 26 and are indistinguishable from the
defective ones without sentinel history nobody kept.

**So the honest statement is: the blind spot is real, its rate is unknown, and it cannot be
established from recorded transcripts.** Anything narrower would be the recorded shape *a measurement
is only as good as its CORPUS* — a number quoted because it was available rather than because it
answers the question.

**Consequences that follow from not knowing:**

* the `unarmed` warning **must keep hedging**. `:335-339` already tells the reader the number may be
  low; that paragraph is rewritten, not deleted, and now names *this* limitation instead of the flush
  race;
* the promote-to-blocking decision (§8) stays out of scope, and the log alone cannot settle it;
* **F12** asserts the shape directly, so the blind spot is a tested boundary rather than a caveat.

⚠ **Where the residue lands is the uncomfortable part, and it is recorded rather than smoothed
over.** Condition 2 says the turn *under-announced* — it ticked its last step without announcing it.
Turns that under-announce are the population this guard exists to police, so the blind spot
correlates with the subject rather than falling somewhere harmless. **This was the argument for the
rejected alternative (§3.3), and it was not defeated by evidence — the user chose simplicity and a
smaller failure surface over it, knowing this.** If the warning is ever promoted toward blocking,
this paragraph is the first thing to re-open.

### 3.3 ❌ REJECTED — judge at Stop, carrying a per-session journal

The alternative this spec carried through v2. At each Stop the guard writes `{turn_uuid, armed,
steps}` and judges the previous turn against the record written last time. Its appeal is real and
should not be understated: `block-idle-stop.sh:62` already runs this guard **ahead of** the blocking
check, precisely so it samples the sentinel *before* the unlink — so the sample point is already
correct, and §3.2's blind spot does not exist.

**Rejected on cost, not correctness.** Round 1 found three Blockings in it (§3.1's table), all
arising from the persisted state itself, and each fix adds machinery: per-session files with atomic
replacement, a `prev_*` pair so a blocked stop does not lose its subject, `last_judged_uuid` for
exactly-once, and a write-ordering rule so a failed write outranks "no subject". That is a
distributed-state protocol inside a warn-only advisory.

**DECIDED 2026-09-05 by the user, with §3.2's trade explicit.** The simpler mechanism, and a stated
blind spot, in preference to a correct sample point defended by four pieces of state.

### 3.4 ❌ REJECTED — judge prior-turn text against the CURRENT sentinel at Stop

A plan armed during T-1 and cleared during T reads as "never armed". Same false positive as §3.2 but
**unbounded** — it fires whenever a plan ends, announced or not, because at Stop the closing banner is
also invisible. Strictly worse than both alternatives above.

### 3.5 The caller moves, and the exit-code contract changes with it

The guard leaves `block-idle-stop.sh` and gains its own `UserPromptSubmit` hook. Three consequences,
none of them cosmetic:

1. **`block-idle-stop.sh` loses its first observer.** Its `BANNER_RC` capture at `:62` and the
   `|| "$CI_RC" != "0"` arithmetic at the foot both change. The file's header documents three exit
   codes and *why the observer runs first* — that paragraph describes a guard that will no longer be
   there, and stale reasoning left in place is what this project keeps paying for. It is rewritten in
   the same commit.
2. **A `UserPromptSubmit` hook must not block the prompt.** Exit 2 there suppresses the user's turn.
   The wrapper exits **0 or 1 only**, and maps the guard's CANNOT-RUN `2` to `1` — the same
   "an observer may never wedge a turn it has no stake in" rule `block-idle-stop.sh:99-104` states,
   carried across deliberately rather than re-derived.
3. **`.claude/settings.json` gains a `UserPromptSubmit` entry.** There is none today — verified
   2026-09-05 across project, local and global settings.

---

## 4. Behaviour

Both warning classes judge the **same** window under one rule. Splitting them — prior-turn for
`unarmed`, live for `unbannered` — would be two mechanisms for one concern, which
`scripts/check-vocabulary-collisions.py` exists to discourage.

| judged turn | sentinel read now | verdict |
|---|---|---|
| none (first substantive turn) | — | **QUIET** — no subject |
| present | readable | run `decide()` with `armed`/`steps` read at prompt time and the prior turn's `texts`/`edited` |
| present | `_armed()` returns `None` | **CANNOT RUN** — unchanged meaning from `:486-489` |
| present | armed, plan unmeasurable | **CANNOT RUN** — unchanged meaning from `:298-304` |

All four inputs now describe the same era **without any reconciliation step**, which is the whole
benefit of §3.1: `texts`/`edited` come from a finished window, and `armed`/`steps` from a sentinel no
in-flight turn is touching.

`decide()` itself is **not modified**. Its inputs change era; its rules do not.

**The accepted loss, stated:** the `unbannered` nudge currently arrives mid-plan, where the assistant
can act on it, and will now arrive one turn later. The mitigation is that
`scripts/check-plan-progress.py` — the **blocking** guard — is untouched and still fires live. Only
the advisory moves.

---

## 5. Cannot-run is a failure, never a quiet pass

Choosing `UserPromptSubmit` (§3.1) deletes most of what this section had to arbitrate in v2: with no
persisted state there is no key to mismatch, no write to fail, and no precedence question between
"no subject" and a failed write. What remains is the existing taxonomy, applied one turn back.

| state | code | why |
|---|---|---|
| no judgable prior window (first substantive turn of a session) | QUIET | there is genuinely nothing to judge — *no subject*, not *cannot reach* |
| `_armed()` returns `None` (sentinel exists, unreadable) | **CANNOT RUN** | unchanged from `:486-489` — the check cannot reach what it measures |
| `armed` is true and `_plan_steps()` is `None` | **CANNOT RUN** | unchanged from `:298-304` |
| transcript unreadable or unparseable | **CANNOT RUN** | unchanged from `:291-294` |

The message must say **TREAT THIS AS NOT RUN**, matching the CANNOT-RUN messages the module already
emits.

⚠ **"No subject" and "cannot reach the subject" must not collapse into each other**, and the first
row is the one at risk: a bug in window selection that returns nothing would present as QUIET and be
indistinguishable from a genuinely first turn. **F5** and **F3** exist to hold those apart — F3 asserts
that a real prior turn *is* found when an empty slash-command window sits in front of it, which is the
only way the "nothing to judge" branch gets exercised against a case where something *should* have
been judged.

### 5.1 What the v2 journal design forced here, and why it is gone

Recorded because the deletion is the point, not an omission. v2 had to arbitrate a genuine conflict
between two precedents in the module — the warn-log write failure at `run_decide:506-510`, which is
**not** swallowed but keeps its `WARN` because losing the log costs only evidence; and `_armed()`
returning `None` at `:486-489`, which is CANNOT RUN because the guard cannot reach its subject. A
journal write failure sat between them, and v2 decided it ranked with the second.

**None of that arises now.** There is no journal, so there is no third precedent to place, no
ordering rule to state, and no failure mode to add. The two existing precedents keep their existing
meanings, untouched by this change.

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
| F3 | an empty slash-command window is **skipped**, and the substantive turn before it is judged | the empty window is judged, or the substantive one is never judged |
| F4 | the guard **never blocks a prompt** — the wrapper exits 0 or 1, mapping the guard's CANNOT-RUN `2` to `1` | an observer can suppress the user's turn |
| F5 | the first substantive turn of a session is **QUIET**, not CANNOT RUN | absence of a prior turn is reported as a failure |
| F6 | `windows(records)[-1].body` equals today's `records_since_last_user(lines)` on every transcript in the corpus, **including one with no real-user boundary at all** | the generalisation changed the live window, or raises on the degenerate case |
| F7 | removing the guard from `block-idle-stop.sh` leaves that hook's remaining exit-code arithmetic correct, and its header describing only guards it still runs | the caller keeps stale reasoning about a guard that moved |
| **F8** | a turn making **only tool calls** (no assistant text) is judged, not skipped — and its `unbannered` warning fires when it edited with unticked steps | the text-block predicate survives anywhere |
| **F9** | a **blocked** stop, which re-fires the Stop hook within one turn, changes **nothing** about this guard | the guard is still wired to Stop |
| **F10** | two concurrent sessions in one working copy each judge their own prior turn, with no shared file between them | any cross-session state was reintroduced |
| **F11** | for every completed window in the corpus, the judged window's last record precedes the live window's first | the durability assumption is asserted rather than measured |
| **F12** | ⚠ **the blind spot is a TESTED boundary:** a prior turn whose plan finished that turn and whose highest banner is below its total **does** produce the known-wrong `unarmed` warning — and the message hedges, naming this limitation | the blind spot is silently absent (so the model is wrong) or the message asserts a certainty it lacks |

F6 is the regression falsifier: this change must not alter what the boundary rule means.

⚠ **F9 and F10 now assert ABSENCES, and that is deliberate.** They were round 1's Blockings against
the journal. Dissolving a defect is cheap to claim and easy to un-dissolve later, so each is kept as a
falsifier that fails the moment cross-turn state comes back.

⚠ **F11 exists because the design's central assumption was never measured, only argued** (r1 Claude,
"what I could not check"). §1.1's two observations are hook-time evidence about the *live* turn;
nothing yet establishes that the prior turn is always durable when the next prompt arrives. Under
`UserPromptSubmit` this matters **more** than it did under the journal design — the margin is the gap
between a turn ending and the next prompt, which can be short, rather than a whole turn. F11 must be
measured before implementation is called done, not asserted.

⚠ **F12 is the one this spec would most like to be wrong about.** If it cannot be made to fire, the
model of §3.2 is incorrect and the blind spot is something other than described — which would be good
news, and must be investigated rather than quietly enjoyed.

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
* ⚠ **the CALLER CHANGES, and `check-ratchet-contract.py` checks that a guard has one.** The guard
  moves out of `.claude/hooks/block-idle-stop.sh` into a new `UserPromptSubmit` wrapper, registered in
  `.claude/settings.json` — which has **no** `UserPromptSubmit` entry today (verified 2026-09-05
  across project, local and global settings). Ship the registration in the same commit as the move, or
  the guard is on disk with nothing running it, which is precisely the state that ratchet exists to
  refuse and which it caught three times on 2026-08-30;
* the declared self-test count is updated in the canonical form — `check-selftest-counts.py` pins
  this file's count, and a stale declared count is itself a gate failure;
* a mutation manifest entry per new decision predicate, each killed **via the case it names**;
  `EXPECTED_MUTATIONS` rises and never falls.
