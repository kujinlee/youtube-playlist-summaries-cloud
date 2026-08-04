# Round 5 (final convergence round) — branch `fix/serial-coherence-sync`

Claude half of the dual adversarial review. Codex half:
`task-A-serial-coherence-branch-v5-rereview-codex.md` (ran on `gpt-5.5` — the wrapper fell through
`gpt-5.6-sol → -terra → -luna` on HTTP 400, exactly the failure mode `scripts/codex-review.py`
exists to absorb).

**Verdict: NOT CONVERGED.** One High, confirmed by reading the code. It is an instance of the
already-recorded worker-vs-sync gap, but a sharper one than that entry describes, and it is on a
paid-content path. Recorded here; the decision is the human's.

---

## Claude finding 1 — the `localVideo.summaryMd == null` branch had ZERO unit coverage (FIXED)

**Severity: High (coverage), fixed in this round.**

`reconcile-serial.ts:126-131` — when local advertises no MD, `describeDivergence` *synthesizes*
local's intended base as `applySerial(cloudVideo.summaryMd, localVideo.serialNumber)`. This is the
branch that decides **where paid dig blobs get relocated to**.

Found by mutation, not by a failing test. Replacing the fallback with `baseOf(cloudVideo.summaryMd)`
— i.e. "never diverged when local has no MD" — left **all 2582 unit tests green**. The only thing
exercising it was integration test M-R2-2, and that test was asserting the *pre-A3* key, so it had
been passing on `master` for the wrong reason.

The branch is reachable in production: `claimVideoSlot` reserves a stub `{id, serialNumber}` before
generation, so a crash between the claim and the summary write leaves exactly this shape — a serial
with no MD behind it.

**Fixed:** four tests added (`tests/lib/cloud-sync/reconcile-serial.test.ts`), covering renumber-with-
dig-blobs, the idempotent no-op, the no-serial early return, and — the one that matters most — that
the **occupancy guard still refuses** on the synthesized target. Without that last case the no-MD
path would be a hole straight through the collision check. Re-mutated: the same mutant now kills 2
tests (it killed 0 before).

---

## Codex High #1 — a stale worker persist re-diverges the row *after* A3 has moved and deleted

**Severity: High. CONFIRMED by reading the code — not accepted on the reviewer's word.**

Verified claim by claim:

1. `summary-handler.ts:95-96` pins `baseName = <padSerial(serial)>_<slug>` from the serial reserved
   at that moment — then `summaryCore` runs transcription + Gemini. **Minutes.**
2. `persist_summary` (`0021:135`) resolves the key as
   `coalesce(p_video->>'summaryMd', v.data->>'summaryMd')` — **the payload wins.**
3. `serialNumber` is not in the re-applied summary-owned list (step 3); it is restored from the
   existing row by step 2 (`|| (v.data - 'artifacts')`). **The row's serial wins.**

So the two halves come from different writers, and the result is the exact incoherence this branch
exists to remove:

| | serialNumber | summaryMd | paid digs live at |
|---|---|---|---|
| before | 7 | `007_alpha.md` | `dig/007_alpha/` |
| after A3 | 3 | `003_alpha.md` | `dig/003_alpha/` |
| after the stale worker persist | **3** | **`007_alpha.md`** | `dig/003_alpha/` — **orphaned** |

The worker rewrites `007_alpha.md` itself, so the summary body is not lost. The **dig blobs are** —
they sit at `003_alpha` while the row points at base `007_alpha`, and A3's cleanup already deleted
`dig/007_alpha/*`.

**Codex's suggested fix is not sufficient, and this is the adjudication that matters.** It proposes
strengthening A3's pre-write freshness check to compare `serialNumber` as well as `summaryMd`. That
cannot work: in this interleaving the worker has not written *anything* when A3 performs its check,
so there is nothing for a stronger comparison to see. The write happens strictly after. Only fencing
(a lease/CAS on the worker persist, or serialization) closes it — which is precisely the open
question the roadmap records as *"queue-based serialization vs conditional writes. Needs a decision
before filing."*

**Relationship to the known gap.** The roadmap already records "sync has no mutual exclusion against
the WORKER," adjudicated *pre-existing and not A3-specific* (`transferClassA` and
`copyAdditiveVideo` carry the same exposure). That adjudication still holds for the **root cause**.
What is new here, and what the existing entry does not say, is the **consequence on the A3 path**:
because A3 *moves and then deletes*, a lost update stops being "the row points at the wrong body"
and becomes "paid dig content is orphaned." Same cause, worse outcome.

**Not silently downgraded, not silently fixed.** A fix belongs to the whole sync write path, not to
A3, and the roadmap says that decision is not yet made.

---

## What was checked and found clean

- **A6a** (`93631da`) — `findIndex` → `find` is behaviour-preserving: `Video` is always truthy, and a
  null array element would throw on `v.id` under either form. A row present with `serialNumber: null`
  reaches the legacy-fill branch in both shapes (Codex independently agreed).
- **`remap()`** — no unmapped real key shape found, no two-sources-to-one-destination case beyond the
  covered tests. Fails closed.
- **Ordering** — plan → copy (sources retained) → verify → advance metadata → delete best-effort.
  Every failure before the metadata write leaves the old blobs intact and still serving the current
  row.
- **The two integration fixes** (`aee620e`, `5433873`) — both re-derived from the code rather than
  from the tests. `metadata-store` test 10 was pinning the phantom serial 0023 *fixes*; M-R2-2 was
  pinning the pre-A3 key and is now an invariant assertion.
- **Gates** — tsc clean, unit 2586 pass, integration 470 pass (green twice back-to-back with no DB
  reset between, per the idempotency rule).

## Standing root-cause shapes, re-run against this round

| Shape | Result |
|---|---|
| absent vs unreadable | no new instance |
| returning-void RPC trusted as proof | no new instance (A3 reads back and verifies) |
| computed-before-insert returned as persisted | **fixed** this round in the integration test that pinned it |
| guard passing in both worlds | **one found** (Claude finding 1), fixed |
| two unrelated numbers sharing a type | **A6a removes the last instance** (`position` vs `playlistIndex`) |
| pre-write re-read mistaken for a CAS | **the open High** — and the reason Codex's proposed fix fails |
