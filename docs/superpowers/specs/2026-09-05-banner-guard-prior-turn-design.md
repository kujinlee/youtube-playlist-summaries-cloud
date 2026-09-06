# The banner guard judges a turn that has finished being written

> **Anchor:** `status-visibility` — **ADR:** none
> **Goal:** A person who was away can see the current state, what changed, and what needs them —
> without reading the chat transcript.

**Backlog #96.** **v2, 2026-09-05** — folds round 1 (both halves **NOT CONVERGED**: 3 Blocking,
3 High, 2 Medium, 2 Low across the two). Round files:
`docs/reviews/{claude,coordinator}/banner-guard-prior-turn-r1-*.md`. The structural half of #96,
deferred out of PR #225 when option B (retract the guard's precision claim in prose) shipped instead.
This is the half the row calls *"a spec, not a patch"*.

⚠ **v1 REJECTED THE SIMPLER DESIGN FOR A REASON THAT WAS FALSE.** See §3.2 — the Codex half refuted
it by reading `decide()`, and the refutation stands. The alternative is still rejected, but the
reason is now narrow and true instead of broad and wrong.

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
`records_since_last_user` sets `start = i + 1` (`:162`), *excluding* the boundary record — but §3.4's
journal is keyed on that record's `uuid`. A flat window either includes the opener, and the equality
with today's function is false, or excludes it and cannot supply the key. The pair resolves both: the
equality is asserted on `.body`, and the key comes from `.opener`.

⚠ **THE DEGENERATE CASE, which v1 asserted away** (r1 Claude, High). With **no** real-user boundary
at all, today's function returns **every** record — `start` stays `0` and `:163` returns `records[0:]`.
A naive split returns `[]`, and `[-1]` raises `IndexError` **inside a Stop hook**, turning a warn-only
observer into a traceback. Reachable: a transcript whose only `user` records are tool results and
injected `isMeta` records has no boundary, and both exclusions are documented as real at `:158-161`.
**`windows()` returns one window with `opener=None` and `body=`all records** in that case, preserving
today's semantics. A window with `opener=None` has no key and therefore can never be *journalled*,
only judged.

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
* **It desynchronises the journal.** A Stop hook fires for any assistant activity, so the journal is
  keyed to that turn; the *next* Stop skips it looking for text and judges an older turn, whose key
  does not match → CANNOT RUN until a text-bearing turn re-aligns things.

Two predicates for "a turn happened" is the *two mechanisms for one concern* shape that
`scripts/check-vocabulary-collisions.py` exists to catch. **One predicate: a window is judgable iff it
contains at least one `assistant` record.** That is exactly the population a Stop hook fires for, so
the selector and the journal cannot disagree.

The slash-command shells of §2.2 still drop out — they contain **zero** records, so they are excluded
because there is no assistant activity, not because there is no text.

If no such window exists — the first substantive turn of a session — there is **no subject**, which
is QUIET. That is categorically different from *cannot reach the subject*; §5 keeps them apart.

---

## 3. The per-turn state — why a journal, and what refutes the alternatives

`decide()` is pure and takes four inputs. After this change `texts` and `edited` come from the
**prior** turn, so `armed` and `steps` must too. `run_decide` samples them from *now*
(`:485`, `:490`), and mixing the two eras is how this fix would ship a subtler copy of the same bug.

### 3.1 The sample point is ALREADY correct — it just is not kept

`block-idle-stop.sh:62` runs this guard **ahead of** the blocking check, and the file says why:

> *"it is REQUIRED, because check-plan-progress.run_decide UNLINKS `.claude/executing-plan` when the
> last step is ticked, so running after it reads a deleted sentinel."*

Confirmed at `check-plan-progress.py:180-182`:

```python
if unticked == 0:
    SENTINEL.unlink(missing_ok=True)
    STATE.unlink(missing_ok=True)
```

So at the Stop of turn *T*, this guard already observes the sentinel exactly as turn *T* left it.
The defect is that the observation is **discarded**. It must be persisted for one turn.

### 3.2 ❌ REFUTED — judge at `UserPromptSubmit` and carry no state

The strongest alternative, and it is wrong. At `UserPromptSubmit` no turn is in flight, so the
sentinel read there *appears* to be the end-of-prior-turn state with no journal at all — the open
question dissolved rather than solved.

⛔ **v1's REFUTATION WAS FALSE, AND IS WITHDRAWN.** It said: *"every turn that finished a plan would
read `armed = False` and fire the `unarmed` warning wrongly."* The Codex half refuted it by reading
`decide()`, and the refutation is correct — verified at `scripts/check-banner-armed.py:325-329`:

```python
step, total = banner
if step >= total:
    return QUIET, ""        # :326-327 — BEFORE `armed` is consulted
if armed:
    return QUIET, ""
```

A turn that finished its plan **and emitted its closing `STEP n of n`** returns QUIET whatever the
sentinel says. Since prior-turn judging makes that closing banner *visible*, the commonest case is
QUIET, not a false positive. v1 asserted a failure over a population that mostly cannot reach the
branch — the same corpus error §1.2 warns about, committed one section later.

**The rejection SURVIVES, on a narrow and true reason.** The false positive needs **both**:

1. the plan finished during the turn (`unticked == 0`, so `check-plan-progress.py:180-182` unlinks),
   **and**
2. the highest banner visible in that turn is **below** its total.

Then `armed` reads `False`, `step < total`, and `:331` fires *"BANNER WITHOUT A PLAN"* about a turn
that had one.

⚠ **That residue is not incidental — it is this guard's own subject.** Condition 2 says the turn
*under-announced*: it ticked its last step without announcing it. Turns that under-announce are
exactly the population the guard exists to police, so `UserPromptSubmit` would be systematically
wrong on the cases that matter most, while being right on the easy ones. A design whose blind spot
coincides with its purpose is the *green check over the wrong subject* shape again.

**Also unavailable to it, and stated because §3.1 is no longer carrying the argument alone:** between
the end of a turn and the next prompt, nothing prevents the sentinel or the plan file from changing —
a human edit, or another session (§3.4 B1). Sampling at the Stop bounds that window to zero.

**Weighed honestly:** `UserPromptSubmit` dissolves all three Blockings this round raised against the
journal, and that is a real cost of choosing the journal. It is rejected because its residual error
lands on the guard's subject, and because it moves the guard out of `block-idle-stop.sh`'s
exit-code contract — not because it cannot work.

### 3.3 ❌ REJECTED — judge prior-turn text against the CURRENT sentinel

A plan armed during *T-1* and cleared during *T* reads as "never armed". Same false positive, shorter
route.

### 3.4 ✅ The journal

⛔ **v1 PUT THIS IN ONE SHARED FILE HOLDING ONE RECORD. Both are wrong, for different reasons, and
each was a Blocking.**

**(a) PER SESSION, not one file** (r1 Claude B1 / Codex High). v1's fixed
`.claude/banner-turn-state.json` is shared by every session in the working copy — and this project
runs concurrent sessions routinely, with a recorded incident where *"two reviewers on one Postgres
produced a FALSE BLOCKING"*. Distinct uuids do not help; the **storage** is shared:

```
session A, Stop of A1  -> writes {uA}
session B, Stop of B1  -> writes {uB}        ← clobbers A's record
session A, Stop of A2  -> judged turn is A1; stored key is uB -> MISMATCH -> CANNOT RUN
```

Both sessions then report CANNOT RUN for as long as they overlap. The keying prevents the *dangerous*
outcome — judging A1 against B's sentinel sample — but converts it into permanent noise, and a guard
that always says CANNOT RUN is one that gets ignored.

**One file per session: `.claude/banner-turn-state/<session_id>.json`.** `run_decide` already reads
`data.get("session_id")` for `log_line` (`:505`), so the identifier is in hand. A file per session is
preferable to a map: no read-modify-write, so two sessions cannot lose each other's records to a torn
update. Written atomically (temp file + `os.replace`). Stale files are prunable and harmless.

**(b) TWO KEYED FIELDS, not one record** (r1 Codex Blocking; r1 Claude had this as Medium and
**understated it** — I called it "judged twice", and the real outcome is CANNOT RUN).

A blocked stop re-fires the hook **inside the same turn**: `check-plan-progress` returns BLOCK, the
assistant continues, and stops again. The hook's own feedback is `isMeta` and not a boundary, so the
live turn is unchanged. With one record:

```
Stop of T-1     -> journal {u1}
turn T opens (u2); first Stop of T -> judges u1 ✓, overwrites journal with {u2}
check-plan-progress BLOCKS; assistant continues
continuation Stop of T -> judged turn is STILL u1; journal says u2 -> CANNOT RUN
```

The guard loses a subject it had a moment earlier, on a path the system is *designed* to take.

**Fields, per session:**

| field | meaning |
|---|---|
| `sampled_turn_uuid` | `opener.uuid` of the turn the sample below describes (the live turn at write time) |
| `armed` | `_armed()` sampled at that turn's Stop — `true`, `false`, or `null` (unreadable) |
| `steps` | `[done, total]`, or `null` when the plan could not be measured |
| `prev_turn_uuid` | the previous `sampled_turn_uuid`, retained so a continuation Stop can still find it |
| `prev_armed`, `prev_steps` | that turn's sample |
| `last_judged_uuid` | the turn a verdict was last issued for — judged once, never twice |

A continuation Stop finds the judged turn under `prev_*` and proceeds. `last_judged_uuid` makes
"exactly one verdict per turn" an assertable property rather than an accident, so a blocked stop
cannot inflate `.claude/banner-warnings.log` — the evidence base §6 exists to make trustworthy.

**Measured across the WHOLE corpus, not a sample** — 524 transcripts, **2629 real-user boundaries,
0 without a string `uuid`**, in 0 files. An earlier draft of this section said "the sampled
transcripts" on the strength of **one** transcript; that is the recorded shape *a measurement is only
as good as its CORPUS*, and the journal key depends on it, so it was re-measured over the full
population before being relied on.

⚠ The corpus is live (§1.2), so a re-run may count 2630. What the key needs is the **absence of
exceptions**, not the total.

**Read the record for the judged turn; write the record for the live turn.** Both happen in the same
Stop, and the write happens **whatever the verdict** — a turn that warns is still the previous turn
next time.

**Keying is what makes a missed Stop visible.** If the stored `boundary_uuid` is not the judged
turn's, the guard holds no sentinel sample for that turn and must say so (§5) rather than fall back
to a sample from the wrong era.

---

## 4. Behaviour

Both warning classes judge the **same** window under one rule. Splitting them — prior-turn for
`unarmed`, live for `unbannered` — would be two mechanisms for one concern, which
`scripts/check-vocabulary-collisions.py` exists to discourage.

| judged turn | journal | verdict |
|---|---|---|
| none (first substantive turn) | — | **QUIET** — no subject |
| present | key matches | run `decide()` with the journalled `armed`/`steps` and the prior turn's `texts`/`edited` |
| present | key absent or mismatched | **CANNOT RUN** (§5) |
| present | key matches, `armed` is `null` | **CANNOT RUN** — unchanged meaning from `_armed()` |

`decide()` itself is **not modified**. Its inputs change era; its rules do not.

**The accepted loss, stated:** the `unbannered` nudge currently arrives mid-plan, where the assistant
can act on it, and will now arrive one turn later. The mitigation is that
`scripts/check-plan-progress.py` — the **blocking** guard — is untouched and still fires live. Only
the advisory moves.

---

## 5. Cannot-run is a failure, never a quiet pass

Three states that must never be collapsed:

| state | code | why |
|---|---|---|
| no prior non-empty turn | QUIET | there is genuinely nothing to judge |
| prior turn exists, no matching journal record | **CANNOT RUN** | the sentinel for that turn was never sampled; judging it against any other sample is a guess |
| journal unreadable / unwritable | **CANNOT RUN** | the check cannot reach what it measures |

The message must say **TREAT THIS AS NOT RUN**, matching the two CANNOT-RUN messages the module
already emits, and must name the journal path.

### 5.0 ORDER OF OPERATIONS, and the precedence between "no subject" and a failed write

Two round-1 findings meet here, and v1 answered neither.

**(a) The journal write is UNCONDITIONAL and precedes every early return** (r1 Claude, High). Today
the guard returns before doing anything else when the sentinel is unreadable:

```python
armed = _armed()
if armed is None:
    print("CANNOT RUN: …", file=sys.stderr)
    return CANNOT_RUN                      # :486-489
```

If the write sits after that, one transient unreadable sentinel loses the record for that turn, so
the *next* Stop finds a mismatched key and reports CANNOT RUN too — a single fault becomes two dead
turns with no path back. A CANNOT RUN *about this turn* must still leave a usable sample for the next
one, which is why `armed: null` is a legal journalled value.

**(b) A failed write outranks "no subject"** (r1 Codex, Medium). On the first substantive Stop of a
session both conditions hold at once: there is no prior turn to judge, *and* the journal must still be
written for next time. If "no subject → QUIET" returns first, a failed write becomes a **quiet pass** —
the failure mode this project treats as the most serious there is.

**The fixed order, stated so it cannot be re-derived differently:**

```
1. compute windows; select the judged turn        (may be: none)
2. sample armed / steps for the LIVE turn
3. judge, if there is a subject and a matching sample   -> verdict
4. WRITE the journal                                     -> failure here overrides the verdict
5. return: write failed ? CANNOT RUN : verdict
```

F5 is amended accordingly: the first substantive turn is QUIET **only when the write succeeds**.

### 5.1 A failed journal WRITE — the ambiguity resolved, because two precedents disagree

A failed write does not spoil *this* Stop's judgement; it disables the *next* one. The spec must
still say what this Stop returns, and the module contains two precedents pointing opposite ways:

| precedent | behaviour | why it fits there |
|---|---|---|
| the warn-log write, `run_decide:506-510` | **not** swallowed, but the code stays `WARN` — the failure is appended to the message | losing the log costs *evidence*; the guard still works |
| `_armed()` returning `None`, `:486-489` | **CANNOT RUN** | the guard cannot reach its subject |

**DECIDED: a failed journal write returns CANNOT RUN.** The journal is not evidence — it is the
guard's only input for the next turn, so losing it silently means every later Stop finds a mismatched
key and the guard degrades permanently and invisibly. That is the second row, not the first.

The verdict this Stop had already reached is still printed alongside it; CANNOT RUN replaces the exit
code, not the message. Both are non-blocking at the hook — `block-idle-stop.sh` maps an observer's
`2` to exit `1` — so this costs noise, never a wedged session.

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
| F4 | a journal key that does not match the judged turn yields **CANNOT RUN** | it judges anyway, or stays quiet |
| F5 | the first substantive turn of a session is **QUIET**, not CANNOT RUN | absence of a prior turn is reported as a failure |
| F6 | `windows(records)[-1].body` equals today's `records_since_last_user(lines)` on every transcript in the corpus, **including one with no real-user boundary at all** | the generalisation changed the live window, or raises on the degenerate case |
| F7 | an unwritable journal produces CANNOT RUN, never silence — **including on the first substantive turn**, where "no subject" would otherwise return QUIET first | the write failure is swallowed |
| **F8** | a turn making **only tool calls** (no assistant text) is judged, not skipped — and its `unbannered` warning fires when it edited with unticked steps | the text-block predicate survives anywhere |
| **F9** | a **blocked** stop that re-fires within one turn issues **exactly one** verdict for the judged turn, and never CANNOT RUN | the single-record journal survives; `last_judged_uuid` is not consulted |
| **F10** | two sessions stopping alternately in one working copy each judge their own prior turn | journal state is shared across sessions |
| **F11** | for every completed window in the corpus, the judged window's last record precedes the live window's first | the durability assumption is asserted rather than measured |

F6 is the regression falsifier: this change must not alter what the boundary rule means.
F8–F10 are round 1's three Blockings, each turned into a falsifier rather than a promise.

⚠ **F11 exists because the design's central assumption was never measured, only argued** (r1 Claude,
"what I could not check"). §1.1's two observations are hook-time evidence about the *live* turn;
nothing yet establishes that the *prior* turn is always durable at the next Stop. The design is
strictly safer than today's — a full turn of margin instead of none — but that is a comparison, not a
proof, and the spec must not be read as supplying one.

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

* new self-test cases for F1–F7, with the §7 fixtures recorded as data;
* the declared self-test count is updated in the canonical form — `check-selftest-counts.py` pins
  this file's count, and a stale declared count is itself a gate failure;
* a mutation manifest entry per new decision predicate, each killed **via the case it names**;
  `EXPECTED_MUTATIONS` rises and never falls.
