<!-- codex-review: model=gpt-6.1-sol -->

NOT CONVERGED — 0 Blocking, 1 High, 1 Medium, 1 Low.

## Blocking

None found.

## High

**H1 — H2 pins the constant but leaves the production wording unprotected. THRASHING.**

At `scripts/check-plan-code.py:3151`, replace only:

```python
said = (_QUOTED_PREFIX
```

with:

```python
said = ("CPython SAID THE FOLLOWING KILLED THE CHILD, at column zero, in reverse order — "
```

**Measured on an isolated complete harness tree:** `--self-test` passes **300/300**; `--binding` passes **1560 anchors / 1552 entries**. A subsequent production `run_mutations` invocation renders that false attribution immediately before the unchanged refusal.

The equality oracle at `scripts/check-plan-code.py:4068` checks the unused constant. The new mutation at `scripts/mutations/check-plan-code.json:1959` also targets only its definition. Thus the exact wording H2 exists to exclude can return through the producer, with both checks green.

The remedy needs to verify the rendered harness-owned prefix, independently of the raw diagnostic window.

## Medium

**M1 — The new “exactly ONE line” case also accepts ZERO quoted lines. THRASHING.**

The predicate at `scripts/check-plan-code.py:4015` checks `ONLY_KILLER` anywhere in the report and absence of `·`. The raw traceback supplies that marker.

Immediately before the production assignment at `scripts/check-plan-code.py:3151`, I inserted:

```python
if len(heads) == 1 and len(se) <= DIAGNOSTIC_WINDOW:
    heads = []
```

**Measured:** **300/300 passed**, and `--binding` remained green with **1560/1552**.

An instrumented repeat confirmed this sever fires on the actual new fixture: stderr was **203 characters**, and `['RuntimeError: ONLY_KILLER']` was cleared. Its rendered section became:

```text
stderr printed these lines, in stream order — . ⛔ THIS HARNESS DOES NOT CLAIM ...
```

The traceback below still contained `ONLY_KILLER`, satisfying the companion assertion. Consequently, that case does not establish the producer property claimed at `scripts/check-plan-code.py:4012`.

## Low

**L1 — The fold’s committed case-count transition is inaccurate. PROSE FLOOR.**

The commit message says **298 → 300**, with two cases added. I restored all three changed files to `52f47910^` in an isolated tree and ran its suite: **297/297 passed**. The current suite runs **300/300**.

The actual committed transition is **297 → 300**: the two one-head cases at `scripts/check-plan-code.py:4010` and `:4015`, plus the prefix pin at `:4068`. The parent’s `scripts/check-plan-code.py:6` also declares 297.

Correct the historical account in the next review record; no implementation redesign is needed for this finding.

## Checked and found SOUND

- **Both new manifest mutations kill and attribute correctly.** I ran production `run_mutations` against the entries at `scripts/mutations/check-plan-code.json:1942` and `:1955`: **2 killed, 2 attributed, 0 survivors**.
- **The mirror refusal mutation is caught.** Keeping refusal only when `len(heads) == 1` produces **299/300**, failing the two-head emission assertion at `scripts/check-plan-code.py:4071`.
- **Current counts agree.** Runtime derivation yielded **150** target entries, **1552** total entries, **1560** anchors, and declared sum **1552** (`scripts/check-plan-code.py:1353`, `:6690`).
- **Every pristine anchor binds exactly once.** An independent scan over every loaded manifest found **zero `count != 1` anchors**, corroborating `--binding` (`scripts/check-plan-code.py:2420`).
- **Coordinated prefix replacement:** rewriting definition and oracle together passes **300/300**, but binding rejects the missing anchor at `scripts/mutations/check-plan-code.json:1959`.
- **Deleting the polarity entry does not silently pass everything.** Combined with the coordinated refusal sweep, binding passes, but the suite fails **299/300** on the live-entry count assertion at `scripts/check-plan-code.py:6965`. The “only protection” wording at `:583` omits this safeguard.
- **Stripping remains live.** Executing the extractor on an indented frame followed by `\u3000END  ` returns `['END']` (`scripts/check-plan-code.py:741`). Removing the sentence does not change that behavior; I found no separate defect requiring its restoration.

## CANNOT RUN

No execution blocker encountered.

**NOT RUN / UNVERIFIED:** full `--mutate .`, eight-shard matrix, real Jest-results validation, and PR-event guard forms. This is a scoped executable review, not a full CI certification.

## Instruments

Ran current and parent self-tests, current binding, independent manifest/count/anchor derivation, both new production mutations, and seven additional mutation variants. Inspected rendered counterexamples using production `run_mutations`. Experiments used temporary harness trees; no review artifact or worktree change was written.

## Thrashing or prose floor

**THRASHING — the diagnostic quotation renderer and its verification boundary.**

H1 moves protection into a constant while leaving its production use unchecked. M1 adds a producer assertion that raw child output satisfies. Both are executable coverage failures introduced by the previous remedy, continuing the sequence documented at `scripts/check-plan-code.py:4051`. They meet the mechanism test required by `docs/dev-process.md:113`.

A redesign should represent quoted lines and raw diagnostic output separately, render them through one narrow formatter, and test that formatter’s complete output with explicit zero-, one-, and multiple-line inputs. This would remove ambient substring satisfaction and expose prefix bypasses directly.

L1 is **PROSE FLOOR**: a historical arithmetic error with a finite correction, independent of that redesign.
