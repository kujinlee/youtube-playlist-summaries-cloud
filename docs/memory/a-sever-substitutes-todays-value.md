---
name: a-sever-substitutes-todays-value
description: "FIRES-WHEN: about to sever, stub or replace a call site to test whether its result is consumed — the substituted value must be WHAT THE CALLEE RETURNS TODAY, or the red you get is your own bad literal and it reads as good news"
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
