# banner-guard-prior-turn — round 2, Claude half

**Subject:** `docs/superpowers/specs/2026-09-05-banner-guard-prior-turn-design.md` **v3** at
`6e026d79` (branch `backlog-96-prior-turn`). Backlog #96, structural half. Spec only.

> ⚠ **NOT a scoped re-review.** v3 replaced the mechanism outright: round 1 reviewed *judge at Stop
> with a per-session journal*; v3 judges at `UserPromptSubmit` carrying no state. Round 1's three
> Blockings were **dissolved by the switch, not fixed**. This is a first review of an unreviewed
> design.

> ⚠ **INDEPENDENCE IS REDUCED — same constraint as round 1.** This half is normally a fresh
> subagent; this session is instructed not to invoke the Agent tool unless asked, so it is written by
> the spec's author. The Codex half is independent and carries the load.

**VERDICT: NOT CONVERGED** — 2 Blocking, 1 High, 2 Medium, 1 Low (one carried from round 1, never
folded).

---

## B1 — Blocking. "The last judgable window **before the live one**" is a Stop-shaped rule, and at `UserPromptSubmit` it can select the wrong turn

§2.2 defines the judged turn relative to *the live window*. That phrasing is inherited from the Stop
design, where the live window provably exists — the assistant has been running in it.

**At `UserPromptSubmit` it is unknown whether the new user record has been written to the transcript
yet**, and the answer changes which turn is judged:

| if the new user record IS already in the file | if it is NOT yet |
|---|---|
| `windows()[-1]` = the new, empty window | `windows()[-1]` = **the prior turn itself** |
| "last judgable before the live one" = **T-1** ✓ | "last judgable before the live one" = **T-2** ✗ |

So on one of these two paths the guard judges a turn **two turns back**, silently, and every verdict
is attributed to the wrong turn — including the log line, which §6 is busy making trustworthy. It
never errors; it just answers about the wrong subject. That is this project's most-recorded failure
shape, and v3 introduced it by carrying a phrase across a mechanism change.

**Fix, and it is simpler than the rule it replaces:** at `UserPromptSubmit` **no turn is in flight**,
which is the entire premise of §3.1. So the judged turn is **the last judgable window, full stop** —
no "before the live one" clause. That selection is correct whether or not the new user record has
landed, because an empty new window is not judgable (§2.2: it contains no `assistant` record).

**Falsifier:** run the selector against a transcript with, and without, a trailing bare user record.
Both must select the same turn. Under v3 as written they do not.

---

## B2 — Blocking. **F11 CANNOT FAIL.** It is a tautology, and it is the falsifier guarding the design's central assumption

Measured, because a falsifier that has never been run is a claim:

```
F11 as written, over the corpus: 1828 judgable windows checked, 0 violations
```

**Zero violations, and zero is the dangerous shape here.** F11 asserts that "the judged window's last
record precedes the live window's first". But `windows()` **splits on record order** — so the judged
window's records are, by construction, the ones before the next boundary. The assertion restates the
splitter's definition. It is true of any corpus, any transcript, any flush behaviour, including one
where the guard is completely broken.

**So the design's central assumption — that the prior turn is durably readable — is guarded by an
assertion that passes unconditionally.** §7 presents F11 as the answer to "this was argued but never
measured". It is not an answer; it is the same gap with a checkmark next to it. This project's
recorded rule applies exactly: *state the observation that would make it FAIL — if none can be named,
it is not a gate.*

**Fix:** delete F11 as written and replace it with the runtime self-check in H1. Flush timing is not a
property of a recorded transcript at all, so **no corpus assertion can ever be the falsifier here** —
only an observation taken at hook time can.

⚠ I wrote F11 in v2 and carried it into v3 believing it discharged the durability question. It never
could have. That is the *unfalsifiable guard* shape this repo has a memory note about, produced while
writing a spec that cites the same shape elsewhere.

**Also measured, and it corroborates §2.2 at scale:** 1828 of the corpus's windows contain an
assistant record and are judgable. The remainder — several hundred — are the empty slash-command
shells §2.2 describes. The predicate is not guarding a rare case.

---

## H1 — High. F11 has no method, and v3 needs it more than v2 did

§7 says F11 "must be measured before implementation is called done" and stops there. v2 could afford
that vagueness — its margin was a whole turn. **v3's margin is the gap between a turn ending and the
next prompt**, which in an automated or scripted loop can be milliseconds. If the prior turn's final
message is not flushed by then, **v3 has the same bug it is fixing**, one turn displaced, and the
whole design fails silently rather than loudly.

The spec asserts safety by comparison ("strictly safer than today's") and that comparison is no
longer obviously true.

**Fix — and the design can measure itself, which is better than a pre-flight check.** The wrapper
already reads the transcript. Have it record, per run, whether the judged window's final assistant
record was present, and compare against the same window on the *following* invocation. A discrepancy
means a flush arrived late and the guard says so. That converts F11 from an assumption checked once,
against a corpus that cannot reproduce hook timing, into a **runtime property with a falsifier that
keeps working**.

⚠ Corpus measurement alone **cannot** settle this: recorded transcripts show final file state, never
what was readable at hook time. Round 1's Claude half said the same thing about the prior-turn case
and it was recorded as "could not check". It is still not checked, and v3 raised the stakes.

---

## H2 — High. The blind-spot model (§3.2) is stated for `unarmed` only; the `unbannered` branch is not walked

§3.2 gives a two-condition conjunction for a false `unarmed` warning. It never checks the *other*
warning class against the same sentinel loss.

Walked here, and the result is favourable — which is exactly why it must be written down rather than
left to the reader:

```python
if banner is None:
    unticked = 0 if steps is _UNSET or steps is None else steps[1] - steps[0]
    if armed and unticked > 0 and edited:      # :309
        return WARN
    return QUIET
```

With the sentinel gone, `armed` is `False`, so `run_decide` sets `steps = _UNSET` (`:490`),
`unticked` is `0`, and the branch cannot fire. A turn that finished its plan and emitted no banner is
**QUIET** — and that is also the *correct* verdict, because `unticked == 0` means nothing was left
unannounced. **No false positive, and no false negative, on this class.**

**Fix:** state that in §3.2. A conjunction offered for one class and silently not evaluated for the
other reads as an oversight, and the next reader has to redo this walk to find out it is fine. An
asymmetry that turns out to be harmless is still worth one sentence.

---

## M1 — Medium. 48 and 50 describe the same population and the spec does not reconcile them

§1.2's table says **48** turns used a banner. §3.2 says **50** bannered completed turns. Same
definition, same corpus, no cross-reference — a reader must assume one is a typo.

Neither is. They were measured about forty minutes apart, and **the two extra bannered turns are this
session's own**: the measurer emits banners and is inside the corpus. §1.2 already documents exactly
this effect for the 2628/2629 boundary count and explicitly says not to "correct" one to the other —
**but that warning is scoped to the boundary count and does not cover the bannered count**, which
moves for the identical reason.

**Fix:** cross-reference §1.2's live-corpus warning from §3.2, and state both figures with their
moment. This is a small instance of a shape this repo takes seriously: a caveat attached to one
number that silently fails to cover its neighbour.

---

## M2 — Medium. §3.5 asserts what exit 2 does on `UserPromptSubmit` without citing anything

§3.5 states that exit 2 "suppresses the user's turn" and builds the wrapper contract on it. Nothing is
quoted. The analogous claim for Stop hooks *is* sourced — `block-idle-stop.sh:15` — and this one is
not, in a spec whose own §3.2 exists because v1 asserted a control-flow claim that turned out false.

Verified 2026-09-05 that the **event** is real and supported, with three working registrations
(`remember`, `security-guidance`, and `omc` plugins all register `UserPromptSubmit`). That confirms
registration is possible; it does **not** confirm the exit-code semantics.

**Fix:** cite the behaviour, or mark it explicitly as assumed-and-to-be-verified before the wrapper
relies on it. The safe implementation does not depend on the answer — exit 0 or 1 only, never 2 — so
this is a documentation defect, not a design one. Write it as an assumption rather than a fact.

---

## L1 — Low. **Carried from round 1 and never folded.** `/clear` does not start a new transcript

Filed as r1 Claude L1 against v1. v2 and v3 both went by without addressing it, and the spec's §5
still says "first substantive turn of a session" as though a session began the transcript.

Measured on this session: `/clear` sits at record 7 **inside** the file, with earlier windows ahead of
it. So the guard can judge a pre-`/clear` turn, and §5's first row does not mean what it says.

**Fix:** say plainly that windows span the whole transcript and `/clear` is not a boundary, or scope
the window set at the last `/clear`. Either is fine; leaving it implied is not.

⚠ **Recorded as a process point, not just a defect:** a round-1 Low survived two spec revisions
without being folded or dispositioned. `docs/dev-process.md` requires Medium/Low **dispositions** to
be recorded, not silently dropped. v4 should carry a disposition line for every round-1 finding,
including the ones the mechanism switch dissolved — otherwise "dissolved" and "forgotten" are
indistinguishable in the record.

---

## What I could NOT check

* **Whether `UserPromptSubmit` fires before or after the new user record is written.** This is B1's
  hinge. B1's fix makes the guard correct either way, which is why it is the fix — but the underlying
  fact is still unknown and is worth establishing during implementation.
* **Exit-code semantics on `UserPromptSubmit`** (M2).
* **Whether the event fires for every boundary the window rule recognises** — queued messages,
  resumed sessions, `/clear`. If the hook does not fire on some boundary, that turn is simply never
  judged; that is a coverage gap, not a wrong answer, but it is unmeasured.
