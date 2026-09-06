# banner-guard-prior-turn — round 1, Claude half

**Subject:** `docs/superpowers/specs/2026-09-05-banner-guard-prior-turn-design.md` at `9453bd03`
(branch `backlog-96-prior-turn`). Backlog #96, structural half. Spec only — no implementation exists.

> ⚠ **INDEPENDENCE IS REDUCED, AND THAT IS RECORDED RATHER THAN HIDDEN.** This half is normally a
> **fresh subagent** with no memory of authoring the spec; that is the whole point of the dual gate.
> This session carries an explicit instruction not to invoke the Agent tool unless the user asks, so
> this half was written **by the same agent that wrote the spec**. It is a self-review wearing the
> reviewer's hat, and self-review is measurably weaker at finding framing errors than a fresh reader
> — this project has the record to prove it. The Codex half (`coordinator/`) IS independent and
> carries the load here. **If any finding below is thin, prefer the Codex half's verdict.**

**VERDICT: NOT CONVERGED** — 2 Blocking, 2 High, 1 Medium, 1 Low.

---

## B1 — Blocking. One journal file, shared by every concurrent session in the repo

**§3.4** puts the journal at a single fixed path, `.claude/banner-turn-state.json`. Nothing in the
spec scopes it to a session.

This project runs concurrent sessions in one working copy routinely, and has a recorded incident
where *"two reviewers on one Postgres produced a FALSE BLOCKING"*. Here the interleaving is worse
than a false blocking, because it is **stable**:

```
session A, Stop of turn A1  -> writes {key: uuid(A1), armed: …}
session B, Stop of turn B1  -> writes {key: uuid(B1), …}     ← clobbers A's record
session A, Stop of turn A2  -> judged turn is A1; stored key is uuid(B1) -> MISMATCH
```

Every Stop in both sessions then reports **CANNOT RUN**, forever, for as long as two sessions run.
The keying prevents the *dangerous* outcome (judging A1 against B's sentinel sample) but converts it
into permanent noise, and a guard that always says CANNOT RUN is one that gets ignored — which is the
failure mode `docs/dev-process.md` names when it says an unread rule is worse than no rule.

**Fix:** scope by session. `run_decide` already reads `data.get("session_id")` for `log_line`
(`:505`), so the identifier is in hand. Either one file per session under
`.claude/banner-turn-state/<session_id>.json`, or a `{session_id: record}` map. A per-session file is
preferable — it needs no read-modify-write, so two sessions cannot lose each other's records through
a torn update, and stale files are trivially prunable.

**Falsifier:** two sessions stopping alternately in one repo must each judge their own prior turn.
Under the spec as written, both report CANNOT RUN.

---

## B2 — Blocking. "Non-empty" uses a different predicate than "a Stop fired", and the key desynchronises

**§2.2** defines the judged turn as the last window that *"contains at least one assistant **text**
block"*. **§3.4** writes the journal at every Stop, keyed to the live turn.

Those are two different notions of "a turn happened", and they disagree on a real case: **a turn that
makes only tool calls and emits no text.** A Stop hook fires for it (the assistant ran), so the
journal is keyed to it. The next Stop looks for the last window with a *text* block, skips it, and
judges an **earlier** turn whose uuid does not match the stored key → **CANNOT RUN**, and the guard
stays desynchronised until a text-bearing turn re-aligns it.

This is the *two mechanisms for one concern* shape that
`scripts/check-vocabulary-collisions.py` exists to catch, and it is in the seam between two sections
of the same spec.

**Fix:** define non-empty as **"contains at least one assistant record"**, not one text block. That
is exactly the population a Stop hook fires for, so the two predicates become one.

⚠ **The fix also removes a coverage hole, which is the tell that it is the right predicate.** A turn
with assistant records and no text is a turn that *did work and announced nothing* — precisely the
`unbannered` class this guard exists to catch. The spec's predicate would have made that class
structurally unreachable while appearing to cover it.

**Note the empty-window case survives either way:** §2.2's slash-command windows contain **zero**
records, so they are skipped under both predicates. B2 is not an argument against §2.2's finding.

---

## H1 — High. `windows(records)[-1] == records_since_last_user(lines)` is FALSE when there is no boundary

**§2.1** asserts the equality as the regression property (F6). It does not hold on the empty-boundary
branch:

```python
start = 0                                    # :154
for i, rec in enumerate(records):
    …                                        # no real-user record matches
return records[start:]                       # :163 -> ALL records
```

With no real-user boundary, today's function returns **every record**. A `windows()` that splits on
boundaries returns **`[]`**, and `[-1]` raises `IndexError` — inside a Stop hook, which turns a
warn-only observer into a traceback.

This is reachable: a transcript whose only user records are tool results and injected `isMeta`
records has no boundary at all, and both exclusions are documented as real at `:158-161`.

**Fix:** state the degenerate case explicitly — `windows()` returns a single window containing all
records when no boundary is found, preserving today's semantics — and make F6 assert it over the
corpus rather than assuming it.

---

## H2 — High. The journal is never written on the early CANNOT RUN return, so the failure cascades

`run_decide` returns before doing any other work when the sentinel is unreadable:

```python
armed = _armed()
if armed is None:
    print("CANNOT RUN: …", file=sys.stderr)
    return CANNOT_RUN                        # :486-489
```

The spec's §4 table allows a journalled `armed` of `null`, but never says **when** the journal is
written relative to this return. If the write sits after it, a single unreadable sentinel loses the
record for that turn, so the *next* Stop finds a mismatched key and reports CANNOT RUN too — one
transient fault becomes two failed turns, and there is no path back until a clean Stop re-aligns it.

**Fix:** the journal write is unconditional and happens **before** any early return. Order it
explicitly in the spec: read journal → judge → write journal → return. A CANNOT RUN about *this*
turn must still leave a usable record for the next one.

---

## M1 — Medium. A blocked stop re-fires the hook and judges the same turn twice

`block-idle-stop.sh` passes `stop_hook_active`, and `check-plan-progress` can block a stop, after
which the assistant continues and stops again — **within the same window**. On the second Stop the
live turn is unchanged, so the last non-empty prior window is the same one, and it is judged again:
a second identical entry in `.claude/banner-warnings.log` for one turn.

That matters more than it would have before this change. Today's guard warns about the turn in
progress, so a repeat is a fresh nudge about a live situation. After this change it is a repeat
verdict about a turn that is already over and cannot be acted on — and the log is the evidence base
for the promote-to-blocking decision, so duplicates inflate it exactly where §6 is trying to make it
trustworthy.

**Fix:** carry `last_judged_uuid` in the journal and return QUIET when the judged turn already has a
verdict. Cheap, and it makes the "judged exactly once" property assertable.

---

## L1 — Low. `/clear` does not start a new transcript, so "first turn of a session" is not what §5 means

§5 maps "no prior non-empty turn" to QUIET, describing it as the first substantive turn of a session.
Measured on this session's own transcript: `/clear` appears **inside** the file at record 7, with
earlier windows still present ahead of it. So after a `/clear` the guard will find and judge a
pre-`/clear` turn.

That is arguably correct — it is a real turn that really happened — but it is not what the spec says,
and a reader implementing §5 from its prose would expect the window set to reset. Either scope the
window set at the last `/clear`, or say plainly that windows span the whole transcript and `/clear`
is not a boundary. Do not leave it implied.

---

## What I could NOT check, stated rather than assumed

* **Real flush timing.** §1.2's truncation is a model. Whether the prior turn is *always* durable at
  the next Stop is not established by anything in this spec; §1.1's two hook-time observations are
  the only real evidence, and neither measures the prior-turn case. The design is strictly safer than
  today's (a full turn of margin instead of none), but the spec should not be read as proving
  durability. **Recommend F8: an assertion that the judged window's final record predates the live
  window's first, measured over the corpus.**
* **`uuid` stability across `--resume` and compaction.** The 2629/0 measurement covers files as they
  exist now, not identity across a resume.
