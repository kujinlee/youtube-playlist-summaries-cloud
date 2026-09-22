# banner-unheralded — round 4, Codex half (the round-3 FIXES)

Subject: `832ddda2` — the round-3 fold. Model: gpt-5.5 via `scripts/codex-review.py`.
Verdict file: `docs/reviews/verdicts/banner-unheralded-r4-codex.verdict.json`.

REVIEW GAP: claude — rounds 2+ ALTERNATE by design; the Claude half was round 3 and its findings are this round's subject

<!-- codex-review: model=gpt-5.5 -->

**Findings**

High: H-A4 still allows a one-edit survivor in the log detail path. In [scripts/check-banner-armed.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-banner-armed.py:1137), changing only the log-block calculation’s second occurrence:

```python
unticked = 0 if steps is _UNSET or steps is None else steps[1] - steps[0]
```

to:

```python
unticked = 3
```

leaves the full self-test green:

```text
$ python3 <temp mutated check-banner-armed.py> --self-test
rc 0 fails 0 summary 149/149 self-test cases passed
```

Concrete wrong behavior: a sampled plan with 2 unticked boxes logs `3 unticked` under the mutant.

```text
# original
seed rc 0
judge rc 1
warn log: ...	s	unbannered	2 unticked

# mutant: log-block unticked = 3
mutated self-test: 147/147 self-test cases passed rc 0
seed rc 0
judge rc 1
warn log: ...	s	unbannered	3 unticked
```

So H-A4 proves “not the current plan’s 1 unticked,” but not “computed from the sampled plan.” F4 and H-A4 both expect `3 unticked`, so hardcoding `3` survives. Add an end-to-end unbannered log case where the sampled plan has a non-3 count, or change H-A4 so the sampled value is neither the old ambient fixture’s `3` nor the current value.

**Attacks Run**

`_drive_prev_slot` really uses the previous slot. I instrumented `sample_for`; stop C judged `Wa` with `sampled=Wb`, `prev=Wa`:

```text
A rc 0
B rc 0
C rc 0
sample_for calls
1 turn= Wa slot= previous result= (False, <object object at ...>, True) sampled= Wb prev= Wa
warn_log_exists False
```

Ordering/state leakage looked sound. H-A/H-B twice and reordered in one temp fixture stayed green:

```text
order HA1,HB1,HA2,HB2 pass True checks 16 failures [] log_lines 6
order HB1,HA1,HB2,HA2 pass True checks 16 failures [] log_lines 6
order HA4ish,HAagain pass True checks 8 failures [] log_lines 4
```

Nine new manifest entries all killed through their named expected case, but three also redden extra cases:

```text
armed reread -> H-A1, H-A2, H-B2
steps reread -> H-A4 only
prev pause dropped -> H-B1, H-B3
prev armed dropped -> H-B2 only
prev steps dropped -> H-B2 only
continuation prev_paused false -> H-B3 only
continuation current pause -> H-B3 only
continuation test inverted -> H-B1, H-B1 control, H-B2, H-B3
armed key loosened -> P10b only
```

The harness allows this: each `expect` must match exactly one red case, not be the only red case.

Duplicate case name is pre-existing and not manifest-ambiguous:

```text
case_count 149 duplicates 1
2 ...and it says TREAT THIS AS NOT RUN

manifest_entries 36 ambiguous_or_missing_expects 0
```

`run_decide` value flow: sentinel-derived `armed_now`, `paused_now`, `steps_now` are sampled only for the live turn and journaled. The judged verdict receives `armed_then`, `steps_then`, `paused_then` from `sample_for`; `texts`, `edited`, and `tool_uses` come from `judged.body`; the log block’s unbannered detail reads the local `steps = steps_then`. I found no fourth sentinel value being read live on that path.

VERDICT: NOT CONVERGED

---

# The four-rounds question, answered here because it is owed here

`docs/dev-process.md`: *"Reaching four rounds OBLIGES ASKING, and does not fire. Answer* thrashing
or prose floor? *in the round document, with per-finding evidence."* This is round 4.

## The answer: NEITHER — and the third thing it is has a name and a repair

**Not a prose floor.** Every round produced *executable* defects, not wording. Fourteen single-edit
mutations of delivered code that left a green suite green, each demonstrated by running it.

**Not thrashing as the condition describes it.** The arming condition is *two consecutive rounds
whose findings came from the previous round's fix, in one component*, and its decisive test is
*can a redesign remove it?* Per finding:

| round | finding | caused by the previous fix? |
|---|---|---|
| r1 | H1 the `no banner` term is unwritten | **no** — present in the first commit |
| r1 | H2 `paused` sampled vs re-read | **no** — present in the first commit |
| r1 | M1 log detail equals the threshold | **no** |
| r1 | L2 pause key match | **no** |
| r3 | H-A `armed`/`steps` unpinned | **yes** — the r1 fold fixed the instance, not the class |
| r3 | H-B the previous slot is reachable | **no** — pre-existing wiring on `master`, and the r1 fold's M2 widened its blast radius |
| r3 | M-A the sibling sentinel reader | **yes** — same instance-not-class shape |
| r3 | L-A `_drive_changing` duplicates `_drive` | **yes** — the r1 fold introduced it |
| sweep | `steps` bound twice on one path | **yes** — the r3 fold verified one binding, shipped the other |
| r4 | H-A4 satisfied by a constant | **yes** — the fix added after the sweep |

So rounds 3 and 4 both carry findings caused by the previous round's fix, in one component. **On a
literal reading the condition is met.** It is answered rather than ticked because the shape
underneath is different from the one the condition was written for — and the difference is
actionable.

## What the repeats actually share

The six "yes" rows are not six repairs of one defect at a moving boundary, which is the shape that
bought the arming condition (a reservation producing a Blocking in six consecutive rounds, four
introduced by the previous fix). They are **two distinct root causes, each recurring**:

1. **Instance-not-class** (r3 H-A, r3 M-A, and the sweep's `steps`). A finding names a mechanism;
   the fix pins the one member it was shown. H2 said *the value consumed must be the one sampled*
   and its own fix comment cited `armed` as the precedent — then left `armed` unpinned.
2. **A case satisfied by an ambient constant** (r1 H1, r4 H-A4, plus two more this round's sweep
   found). A case asserts a value that the fixture also produces for unrelated reasons, so a
   constant substitution passes. r1's H1 was `armed=True` ambient; r4's is `3 unticked` ambient;
   the sweep found the message's tool count passing via a *different sentence* in the same string,
   in the case literally named *"catches a hardcoded message"*.

**Can a redesign remove them?** Root 2, yes, and it was done this round rather than patched: the
repair is that asserted values are now mutually **distinct**, so no single constant satisfies two
cases at once — a property of the fixture set, not of any one case, held by three manifest entries.
The sweep that found it (`ambient.py`) probes every derived value reaching a user-visible string and
now reports **7/7 caught, no constant survives**.

Root 1 is not removable by redesigning this file — it is a discipline (*after fixing, SEARCH for
the class*), and the repo already records it. What this round did differently is apply it: r4's
single finding was not fixed alone, it was swept.

## Why this is not the moment to stop, and what would be

The rounds are not converging on the same defect at a finer boundary; they are descending through
**distinct mechanisms** — rule terms (r1), the journal round trip and a whole reachable code path
(r3), and the falsifiers' own susceptibility to constants (r4). Yield is falling in the right way:
r1 found 4, r3 found 9, r4 found 1 whose class sweep found 2 more.

⚠ **The pre-committed stop condition, so it is not invented later:** if round 5 finds a defect whose
root is again *instance-not-class* or *ambient constant* — the two named above — then the discipline
is not holding and the arming condition fires on its own terms. A finding with a **new** root does
not fire it.

⚠ **And one honest qualification.** This answer is written by the coordinator, who wrote the code
under review and therefore has the weakest claim to judging whether its own fixes are adequate —
which is precisely what rounds 1 and 3 each proved by finding what the coordinator had missed. It
is recorded as a judgement with its evidence, not as a verdict.
