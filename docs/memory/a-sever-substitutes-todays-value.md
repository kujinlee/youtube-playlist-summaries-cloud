---
name: a-sever-substitutes-todays-value
description: "FIRES-WHEN: about to sever, stub or replace a call site — or to REPRODUCE someone else's sever. Two ways it goes wrong: ⭐ the substituted value must be WHAT THE CALLEE RETURNS TODAY (else the red is your own bad literal and reads as good news), and ⭐⭐ PLACEMENT IS PART OF THE CLAIM — two indent levels moved my repro from 299/300 to 300/300, i.e. from refuting a finding to confirming it"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 677677e1-1461-4973-8c68-a7a7b2765493
  modified: 2026-10-02T02:03:31.162Z
---

**Measured 2026-10-01, round 9 of the `semantic-recall-replication` fold.** The Codex half reported
that `defined = _defined_codes()` could be severed to a literal with every case still green — the
eighth instance of the wiring class. I set out to reproduce it before filing, which is correct, and
got the opposite answer.

I replaced it with a six-code dict **typed from memory**:
`{'OK': 0, 'NO_MATCH': 1, 'STALE': 2, 'PAUSED': 3, 'NO_PLAN': 4, 'REFUSED': 5}`.
Suite went **red, 4 named `[FAIL]`s**. The obvious reading: *the wiring is tested, the reviewer is
wrong, H1 does not reproduce.*

The real value is
`{'OK': 0, 'CANNOT_RUN': 2, 'STALE_CACHE': 3, 'BAD_RESPONSE': 4, 'UNREADABLE_PLAN': 5, 'UNANSWERABLE': 6}`
— **every name wrong and four of six values wrong.** The guard's entire job is to notice that the
declared rc codes disagree with the matcher's, so it caught my bad data and was never asked the
wiring question at all. With the real value substituted: **58/58 green, live rc=0.** The defect was
live, and the reviewer was right.

## The rule

**A sever must be identical to the original in every respect except the one property under test.**
Change anything else and you measure that instead — and you will not notice, because the result
still looks like a measurement.

**Derive the substitute by RUNNING the callee, never by typing it:**

```bash
python3 -c "import importlib.util,sys; spec=importlib.util.spec_from_file_location('m','<guard>.py'); \
m=importlib.util.module_from_spec(spec); sys.modules['m']=m; spec.loader.exec_module(m); print(repr(m.<fn>()))"
```

## ⛔ Why this one is worse than an ordinary mistake

**It fails toward good news.** A red probe normally means the guard is working, so the natural
reading of four named `[FAIL]`s is *"protected."* I would have written "did not reproduce", closed a
live Blocking-adjacent defect, contradicted a correct reviewer, and had a green measurement to cite.
A sever that errs the other way (too-faithful substitute) merely fails to find something; this one
actively clears a defect that exists.

## What did NOT save me, and this is the point

The controls were green. The mutation was not masked. I *was* mutating the call site rather than the
function. I did everything [[unit-coverage-does-not-compose]], [[the-control-refuted-the-premise]]
and [[what-mutation-testing-proves]] require, and still got a false negative — because none of them
constrains the **value you substitute**. That gap is why this is its own memory and not a line in
one of those.

⚠ [[unit-coverage-does-not-compose]] is the closest and its trigger reads *"two well-tested pieces
are being joined"* — the AUTHORING moment. This is the VERIFYING moment, a step later, which is why
recall did not surface it when I needed it. The lesson was in the corpus; its trigger named a
different situation. Evidence for [[backlog-191-semantic-recall-replicated]]: a trigger is only as
good as the moment it describes.

Related: [[a-case-can-pass-for-an-ambient-reason]], [[quote-the-code-dont-characterise-it]],
[[a-retrospective-number-needs-provenance]] — the root error was recalling a value instead of
deriving one.

## ⭐⭐ PLACEMENT is part of a sever's claim — and reproducing someone else's needs the exact spot

**Measured 2026-10-14, round 18 of PR #371.** A review half reported: insert
`if len(heads) == 1 and len(se) <= DIAGNOSTIC_WINDOW: heads = []` *"immediately before the production
assignment"*, and the suite stays **300/300** — i.e. the case that claims to police one-head reports
is satisfied by something ambient.

I reproduced it and got **299/300**, with the named case FAILING. On that evidence the finding was
unreproducible and I nearly said so.

**The difference was two indent levels.** I inserted it before the `if not se.strip() / elif heads:`
DISPATCH, where emptying `heads` changes which BRANCH runs — the refusal never gets appended, and a
case catches it. The reviewer inserted it INSIDE `elif heads:`, where the branch is already chosen and
only the `" · ".join(heads)` empties. Same four lines, same file, opposite verdicts: one tests *"what
if this report takes the other branch"*, the other tests *"what if this branch renders nothing"*.

**How to apply:**
- ⭐ **When reproducing a reported sever, reproduce the SPOT, not the snippet.** Ask what the enclosing
  block is and what is already decided by the time control reaches it. If the report does not say, that
  is a finding about the report — ask, do not guess and conclude.
- ⭐ **When WRITING one, state the insertion point in words a reader can land on** — the enclosing
  `if`/`def`, and the line it goes immediately before.
- ⚠ **A near-miss sever fails toward "no defect here"**, which is the same direction as
  [[a-sever-substitutes-todays-value]]'s bad literal and
  [[the-control-refuted-the-premise]]: the comfortable answer. Treat your own failure to reproduce a
  specific, measured finding as a defect in your repro until you have varied the placement.

See [[printing-more-evidence-weakens-substring-cases]] — the finding this sever was testing for.
