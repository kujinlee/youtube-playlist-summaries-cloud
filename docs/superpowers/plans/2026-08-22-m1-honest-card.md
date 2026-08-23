# M1 — The Honest Card: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the cloud summary worker stamp the provenance of the body it just wrote, so a video
row can no longer advertise one document's `mdGeneratedAt`/`mdCorrectionsHash` beside another
document's content.

**Architecture:** `persist_summary` layers the payload under the existing row
(`0021_cloud_sync_signals.sql:115-133`): layer (1) is the payload, layer (2) is
`|| (v.data - 'artifacts')` — *the existing row wins back* — and layer (3) re-applies only the
summary-owned keys the payload actually **provides**, because `jsonb_strip_nulls` turns an absent
key into "no write". The worker supplies ten of the twelve; the two it omits are exactly the two
that identify the body. This milestone adds those two to the payload. **No schema change, no
migration, no behaviour change to the RPC.**

**Tech Stack:** TypeScript, Jest, Supabase Postgres (integration tier only), existing
`InMemoryBlobStore` test double.

## Global Constraints

- **No schema change.** If a task appears to need a migration, stop — it belongs to M4, not M1.
- **Match the local pipeline exactly.** `lib/pipeline.ts:271-272` already stamps
  `mdGeneratedAt: new Date().toISOString()` and `mdCorrectionsHash: mdHash('')`. Cloud must use the
  same two expressions and the same `mdHash` import, so the two pipelines cannot drift.
- `mdHash` is imported from `@/lib/cloud-sync/content-hash` — never re-implement a hash.
- Branch + PR, always (`docs/dev-process.md` Phase 5). Merging is a human gate.
- Anything longer than a line goes in a **file**, never a shell argument (`git commit -F`,
  `gh --body-file`).

---

## Why `mdHash('')` and not "carry the corrections forward"

Carrying corrections forward costs a whole-document Gemini round trip today (`fixSummary`,
`gemini.ts:456`) — that is backlog #23 clause (b), and it is M2's job. **M1 does not make the worker
apply corrections. It makes the worker stop claiming it did.** After this change a re-summarized
cloud row honestly reports "no corrections applied", which is what `reconcileClassA` needs in order
to protect the corrected body (`reconcile-class-a.ts:39`) instead of overwriting it.

## Consequences checked before writing this plan

| Consequence | Verdict |
|---|---|
| `deriveClassASignals` sets `backfilled: !hasReal`, and `hasReal` becomes true | **No behaviour change.** `backfilled` is read only by Class-B (`reconcile-class-b.ts:43`); `reconcileClassA` never consults it. |
| Videos with no corrections anywhere | reconciled hash is `mdHash('')`, both sides current, falls to the recency tiebreak as before — except cloud's timestamp is now honest rather than a `processedAt` fallback. |
| Videos with corrections | `lCur=true, cCur=false` → `copyToCloud` (`:39`) → the corrected local body wins. **This is the fix.** |
| Existing rows written before this change | Unaffected. They keep whatever stamps they have; the next worker run corrects them. No backfill needed. |

## File Structure

- **Modify** `lib/job-queue/summary-handler.ts` — the `video` object literal at `:149-164`; add the
  `mdHash` import. Sole production change in this milestone.
- **Create** `tests/lib/job-queue/summary-handler-card-provenance.test.ts` — Tasks 1 and 2. Unit
  tier, no database. Mirrors the mocking idiom already established in
  `tests/lib/job-queue/summary-handler-promote-divergence.test.ts`.
- **Modify** `tests/lib/cloud-sync/reconcile-class-a.test.ts` (or create if absent) — Task 3, pure.
- **Modify** `docs/backlog.md`, `scripts/gen-backlog-page.py`,
  `docs/superpowers/plans/2026-08-22-append-only-generations-roadmap.md` — Task 4.

---

### Task 1: The worker stamps the body it wrote

**Files:**
- Create: `tests/lib/job-queue/summary-handler-card-provenance.test.ts`
- Modify: `lib/job-queue/summary-handler.ts` (import block; object literal at `:149-164`)

**Interfaces:**
- Consumes: `makeSummaryHandler(serviceClient)` → `JobHandler`; `persistSummary(client, ownerId, playlistId, videoId, video, status)`; `mdHash(s: string): string` from `@/lib/cloud-sync/content-hash`.
- Produces: the `p_video` payload now carries `mdGeneratedAt: string` (ISO 8601) and `mdCorrectionsHash: string`. Task 2 and Task 3 both rely on those two names.

- [ ] **Step 1: Write the failing test**

Create `tests/lib/job-queue/summary-handler-card-provenance.test.ts`. The fixture block below is
lifted from `summary-handler-promote-divergence.test.ts:29-110` — **copy it from that file rather
than retyping it**; this repo has measured that hand-transcribed fixtures lose identifiers.

```ts
/**
 * M1 — the card must describe the body the worker just wrote.
 *
 * `persist_summary` layer (2) (`0021_cloud_sync_signals.sql:117`) lets the EXISTING row win back
 * every key the payload omits, and `jsonb_strip_nulls` in layer (3) means an absent key is not a
 * write. The worker omitted `mdGeneratedAt` and `mdCorrectionsHash`, so a row could advertise one
 * document's provenance beside another document's body. These tests assert the payload, which is
 * the only thing the worker controls.
 */
import type { LeasedJob } from '@/lib/storage/job-queue';
import { InMemoryBlobStore } from '@/lib/storage/testing/in-memory-blob-store';
import { localPrincipal } from '@/lib/storage/principal';
import type { HandlerCtx } from '@/lib/job-queue/handler-context';
import { padSerial } from '@/lib/serial-filename';
import { slugify } from '@/lib/slugify';
import { mdHash } from '@/lib/cloud-sync/content-hash';

jest.mock('@/lib/storage/resolve');
jest.mock('@/lib/storage/worker-persistence');
jest.mock('@/lib/ingestion/summary-core');

import { getWorkerStorageBundle } from '@/lib/storage/resolve';
import { reserveVideoSlot, persistSummary, readVideo } from '@/lib/storage/worker-persistence';
import { summaryCore } from '@/lib/ingestion/summary-core';
import { makeSummaryHandler } from '@/lib/job-queue/summary-handler';
import { docVersionKey } from '@/lib/storage/job-queue';
import { CURRENT_DOC_VERSION } from '@/lib/doc-version';

const OWNER = '11111111-1111-4111-8111-111111111111';
const PLAYLIST = '22222222-2222-4222-8222-222222222222';
const VIDEO = 'vid123';
const TITLE = 'A Video About Alpha';
const SERIAL = 7;

const principal = localPrincipal('/idx');
const WORKER_VERSION = docVersionKey(CURRENT_DOC_VERSION);
const SUMMARY_KEY = `${padSerial(SERIAL)}_${slugify(TITLE)}.md`;

const ctx: HandlerCtx = {
  isCancelled: async () => false,
  signal: new AbortController().signal,
  setPhase: async () => {},
  billing: { metered: false },
};

const serviceClient = {
  from: () => ({
    select: () => ({ single: async () => ({ data: { max_duration_seconds: 4 * 3600 }, error: null }) }),
    delete: () => ({ eq: () => ({ eq: () => ({ eq: () => ({ is: async () => ({ error: null }) }) }) }) }),
  }),
} as never;

function job(): LeasedJob {
  return {
    id: 'job-1', ownerId: OWNER, playlistId: PLAYLIST, videoId: VIDEO, sectionId: 0,
    kind: 'summary', version: WORKER_VERSION, attempts: 1, leaseToken: 'tok',
    payload: {
      youtubeUrl: 'https://youtu.be/vid123', title: TITLE,
      durationSeconds: 600, playlistIndex: 1,
    },
  };
}

/** Every payload the handler hands to persistSummary, in order. */
let payloads: Record<string, unknown>[];

function setup(store: InMemoryBlobStore, mdContent: string, existingRow: unknown | null) {
  payloads = [];
  (getWorkerStorageBundle as jest.Mock).mockResolvedValue({ blobStore: store, principal });
  (reserveVideoSlot as jest.Mock).mockResolvedValue(SERIAL);
  (readVideo as jest.Mock).mockResolvedValue(existingRow);
  (persistSummary as jest.Mock).mockImplementation(
    async (_c: unknown, _o: string, _p: string, _v: string, video: Record<string, unknown>) => {
      payloads.push(video);
    },
  );
  (summaryCore as jest.Mock).mockResolvedValue({
    frontmatter: {}, markdown: mdContent, mdContent, quickView: null,
    geminiFields: { language: 'en', ratings: {}, overallScore: 4 },
  });
}

describe('M1 — the summary worker stamps its own card', () => {
  it('sends mdGeneratedAt and mdCorrectionsHash on every persist', async () => {
    const store = new InMemoryBlobStore({ promoteSemantics: 'overwrite' });
    const before = Date.now();
    setup(store, 'FRESH summary body', null);

    await makeSummaryHandler(serviceClient)(job(), ctx);

    expect(payloads.length).toBeGreaterThan(0);
    for (const p of payloads) {
      // Absent keys are NOT writes (jsonb_strip_nulls), so presence is the whole assertion.
      expect(Object.keys(p)).toContain('mdGeneratedAt');
      expect(Object.keys(p)).toContain('mdCorrectionsHash');
      // The worker applies no corrections, so it must say so — not stay silent.
      expect(p.mdCorrectionsHash).toBe(mdHash(''));
      const stamped = Date.parse(p.mdGeneratedAt as string);
      expect(Number.isNaN(stamped)).toBe(false);
      expect(stamped).toBeGreaterThanOrEqual(before);
    }
  });
});
```

- [ ] **Step 2: Run the test and verify it FAILS**

Run: `npx jest tests/lib/job-queue/summary-handler-card-provenance.test.ts -t "sends mdGeneratedAt"`

Expected: FAIL. `Object.keys(p)` does not contain `mdGeneratedAt` — the literal at
`summary-handler.ts:149-164` never sets it. **If this passes, stop and re-read the handler: the
premise of this milestone is wrong.**

- [ ] **Step 3: Add the import**

In `lib/job-queue/summary-handler.ts`, beside the existing `@/lib/...` imports:

```ts
import { mdHash } from '@/lib/cloud-sync/content-hash';
```

- [ ] **Step 4: Stamp the two fields**

In the same file, in the `const video: Video = { … }` literal, immediately after
`docVersion: CURRENT_DOC_VERSION,`:

```ts
      docVersion: CURRENT_DOC_VERSION,
      // M1 — the card must describe THIS body. persist_summary layer (2) (0021:117) lets the
      // existing row win back any key the payload omits, so staying silent here published the
      // PREVIOUS writer's provenance beside our content. Mirrors lib/pipeline.ts:271-272 exactly;
      // the worker applies no corrections, so mdHash('') is the honest value, not a placeholder.
      mdGeneratedAt: new Date().toISOString(),
      mdCorrectionsHash: mdHash(''),
      processedAt: new Date().toISOString(),
```

- [ ] **Step 5: Run the test and verify it PASSES**

Run: `npx jest tests/lib/job-queue/summary-handler-card-provenance.test.ts -t "sends mdGeneratedAt"`
Expected: PASS.

- [ ] **Step 6: Run the full unit suite — this changes a shared write path**

Run: `npm test`
Expected: 2,722+ passing, 0 failing. Any Class-A sync test that breaks is a **real signal**, not
noise: read it before touching it, and record what it says in the PR body.

- [ ] **Step 7: Commit**

```bash
git add lib/job-queue/summary-handler.ts tests/lib/job-queue/summary-handler-card-provenance.test.ts
git commit -m "fix(#19): the cloud worker stamps the card for the body it wrote"
```

---

### Task 2: The chimera, reproduced and then refuted

**Files:**
- Modify: `tests/lib/job-queue/summary-handler-card-provenance.test.ts`

**Interfaces:**
- Consumes: everything Task 1 established (`setup`, `payloads`, `SUMMARY_KEY`, `principal`).
- Produces: no new exports. This task only adds coverage.

This is backlog #19's falsifier at unit tier — no database. `InMemoryBlobStore` accepts
`promoteSemantics: 'create-if-absent'`, which is precisely `SupabaseBlobStore.promote`'s behaviour
(`supabase-blob-store.ts:120-122`), so the interleaving is reproducible in-process.

- [ ] **Step 1: Write the failing test**

Append inside the existing `describe`:

```ts
  it('does not inherit a transferred card when sync got there first', async () => {
    // Supabase semantics: promote SKIPS when the final key already exists.
    const store = new InMemoryBlobStore({ promoteSemantics: 'create-if-absent' });
    // Sync's transferClassA already committed the LOCAL winner body at this key and patched the
    // row with the LOCAL document's provenance (sync-run.ts:394-432).
    await store.put(principal, SUMMARY_KEY, Buffer.from('TRANSFERRED local body', 'utf8'), 'text/markdown');
    const TRANSFERRED_AT = '2020-01-01T00:00:00.000Z';
    const TRANSFERRED_CORRECTIONS = mdHash('fix Clawcode spelling');
    setup(store, 'WORKER body, generated minutes later', {
      id: VIDEO, serialNumber: SERIAL, summaryMd: SUMMARY_KEY,
      docVersion: CURRENT_DOC_VERSION,
      mdGeneratedAt: TRANSFERRED_AT,
      mdCorrectionsHash: TRANSFERRED_CORRECTIONS,
      artifacts: { summaryMd: { key: SUMMARY_KEY, status: 'committed' } },
    });

    await makeSummaryHandler(serviceClient)(job(), ctx);

    for (const p of payloads) {
      expect(p.mdGeneratedAt).not.toBe(TRANSFERRED_AT);
      expect(p.mdCorrectionsHash).not.toBe(TRANSFERRED_CORRECTIONS);
      expect(p.mdCorrectionsHash).toBe(mdHash(''));
    }
  });

  it('CHARACTERIZATION: the worker body is still silently discarded (M5 fixes this)', async () => {
    // Not a defect this milestone closes — recorded so the behaviour is visible rather than
    // folklore. Under create-if-absent promote the worker's bytes never land, so a paid Gemini
    // generation is dropped by a no-op. Generation addressing (M5) removes the shared key and
    // this assertion should then be INVERTED, not deleted.
    const store = new InMemoryBlobStore({ promoteSemantics: 'create-if-absent' });
    await store.put(principal, SUMMARY_KEY, Buffer.from('TRANSFERRED local body', 'utf8'), 'text/markdown');
    setup(store, 'WORKER body, generated minutes later', null);

    await makeSummaryHandler(serviceClient)(job(), ctx);

    const live = await store.get(principal, SUMMARY_KEY);
    expect(live!.toString('utf8')).toBe('TRANSFERRED local body');
  });
```

- [ ] **Step 2: Run both and check which fails**

Run: `npx jest tests/lib/job-queue/summary-handler-card-provenance.test.ts`

Expected after Task 1: the *first* test PASSES (Task 1 already fixed it) and the
CHARACTERIZATION test PASSES (it documents current behaviour). **Both passing is the correct
outcome here** — Task 1 was the red-green cycle; this task locks the behaviour in so M5 cannot
change it silently. If the first test fails, Task 1 is incomplete.

- [ ] **Step 3: Commit**

```bash
git add tests/lib/job-queue/summary-handler-card-provenance.test.ts
git commit -m "test(#19): the transferred card is no longer inherited; discard is characterized"
```

---

### Task 3: A corrections-current body stops being overwritten

**Files:**
- Modify: `tests/lib/cloud-sync/reconcile-class-a.test.ts` (create with the header comment below if it does not exist)

**Interfaces:**
- Consumes: `reconcileClassA({ local, cloud, reconciledCorrectionsHash })` from `@/lib/cloud-sync/reconcile-class-a`; `ClassASignals` from `@/lib/cloud-sync/types`.
- Produces: nothing. Pure-function coverage proving M1's user-visible payoff.

Task 1 changed a payload; this proves what that buys. `reconcileClassA` is pure, so no mocks.

- [ ] **Step 1: Write the test**

```ts
/**
 * M1's payoff, at the decision that consumes the card.
 *
 * Before M1 a cloud row could inherit the LOCAL document's mdCorrectionsHash, making `cCur` true
 * for a body that had no corrections applied. Both sides then read as corrections-current, the
 * decision fell through to the recency tiebreak, and `newer` is a strict `>` — so an inherited
 * (identical) timestamp returned false and the UNCORRECTED body won. With M1 the cloud card is
 * honest, currency wins first (reconcile-class-a.ts:39), and the corrected body is preserved.
 */
import { reconcileClassA } from '@/lib/cloud-sync/reconcile-class-a';
import { mdHash } from '@/lib/cloud-sync/content-hash';
import type { ClassASignals } from '@/lib/cloud-sync/types';

const CORRECTIONS = 'Clawcode -> Clawcode';
const CUR = mdHash(CORRECTIONS);

const signals = (over: Partial<ClassASignals>): ClassASignals => ({
  summaryMdKey: 'x.md', mdHash: 'H', docVersionMajor: 1,
  mdGeneratedAt: '2026-08-22T00:00:00.000Z', mdCorrectionsHash: null,
  backfilled: false, ...over,
});

it('keeps the corrections-current local body when the cloud card is honest', () => {
  const local = signals({ mdHash: 'LOCAL', mdCorrectionsHash: CUR });
  // Post-M1: the worker stamped mdHash('') — "no corrections applied".
  const cloud = signals({ mdHash: 'WORKER', mdCorrectionsHash: mdHash('') });

  expect(reconcileClassA({ local, cloud, reconciledCorrectionsHash: CUR }))
    .toEqual({ action: 'copyToCloud', needsRegen: false });
});

it('REGRESSION: an inherited card sends the corrected body the wrong way', () => {
  const local = signals({ mdHash: 'LOCAL', mdCorrectionsHash: CUR });
  // Pre-M1 shape: cloud inherited local's hash AND local's timestamp via persist_summary layer (2).
  const cloud = signals({ mdHash: 'WORKER', mdCorrectionsHash: CUR });

  // The tie on mdGeneratedAt makes `newer` false → copyToLocal → the uncorrected body wins.
  expect(reconcileClassA({ local, cloud, reconciledCorrectionsHash: CUR }).action).toBe('copyToLocal');
});
```

- [ ] **Step 2: Run**

Run: `npx jest tests/lib/cloud-sync/reconcile-class-a.test.ts`
Expected: PASS — both. The second documents the behaviour M1 makes unreachable from the worker;
it asserts the pure function, which is unchanged, so it must pass before *and* after.

- [ ] **Step 3: Commit**

```bash
git add tests/lib/cloud-sync/reconcile-class-a.test.ts
git commit -m "test(#19): an honest cloud card preserves the corrected body"
```

---

### Task 4: Reconcile the artifacts, then open the PR

**Files:**
- Modify: `docs/backlog.md` (rows #19, #23, #17)
- Modify: `scripts/gen-backlog-page.py` (`DEPENDS`, `ROOTS`)
- Modify: `docs/superpowers/plans/2026-08-22-append-only-generations-roadmap.md` (tick M1)

This is the milestone contract from the roadmap, executed for the first boundary. **Do not skip it
because the code is done** — the whole point of the contract is that the backlog is reconciled in
the same PR as the work.

- [ ] **Step 1: Correct backlog #19**

Rewrite the row to say what was measured: the mechanism is `persist_summary` layer (2) preserving
omitted keys; the corrections half is closed by M1; the addressing half dissolves at M5. Change the
status cell from `pending (needs spec)` to reference this plan. **#19 is not work — it is a symptom.**

- [ ] **Step 2: Correct backlog #23**

Clause (a) — *"a fresh summarize silently drops the user's corrections AND claims it did not"* — is
**closed by M1**. Narrow the row to clause (b), the affordability redesign, which is M2.

- [ ] **Step 3: Correct backlog #17**

Its text still says *"publication is a conditional update on one row"*. Round 4 deleted that CAS:
§5.1 is append-only and `current` is a view. Replace the sentence; cite the round-4 box.

- [ ] **Step 4: Fix the dependency graph**

In `scripts/gen-backlog-page.py`:
- `DEPENDS[19]` → `dissolved-by` (was `survives`; §5.2 decided it — the card joins the generation).
- Add the missing parent: #23 gates `adr-0006-addressing` (roadmap :1018).

- [ ] **Step 5: Regenerate and verify the page**

```bash
python3 scripts/gen-backlog-page.py
python3 scripts/check-docs.py; echo "check-docs exit=$?"
```
Expected: both exit 0. A non-zero `depends_errors` means the edge points at nothing — fix it, do
not suppress it.

- [ ] **Step 6: Tick M1 in the roadmap and commit**

```bash
git add docs/backlog.md scripts/gen-backlog-page.py docs/superpowers/plans/
git commit -m "docs(#19): reconcile the backlog against M1 — one row closed, three corrected"
```

- [ ] **Step 7: Dual adversarial review before the PR**

Per `docs/plugins.md`: Claude review (`superpowers:requesting-code-review`) **and** Codex
(`python3 scripts/codex-review.py --prompt-file <path> --out docs/reviews/m1-honest-card-codex.md`).
Codex unavailable for any reason → fall back to a Claude adversarial review immediately, and note
the gap in the review doc. Do not wait on it.

- [ ] **Step 8: Open the PR — do not merge**

```bash
gh pr create --title "M1: the cloud worker stamps the card for the body it wrote" --body-file docs/reviews/m1-pr-body.md
```

Merging is a human gate. Notify and stop.

---

## Self-review

**Spec coverage.** M1's scope is the two omitted fields; Task 1 adds them, Task 2 proves they are
not inherited, Task 3 proves the payoff at the consumer, Task 4 reconciles the artifacts. The
`persist_summary` RPC is deliberately untouched — layer (2) is correct behaviour (it stops a stale
payload reverting operational state) and the defect was always the caller's silence.

**Placeholders.** None. Every code step carries the code. The one instruction that points at
another file — the Task 1 fixture — says *copy it from* `summary-handler-promote-divergence.test.ts:29-110`
rather than describing it, because retyping fixtures is a measured defect source in this repo.

**Type consistency.** `mdGeneratedAt` (string, ISO 8601) and `mdCorrectionsHash` (string) are named
identically in Tasks 1, 2 and 3 and match the keys `persist_summary` reads at `0021:131-132` and the
`ClassASignals` fields at `types.ts:32`. `mdHash` is imported from `@/lib/cloud-sync/content-hash`
in all three.

**Known gap, deliberately out of scope.** No integration-tier test drives a real
`transferClassA` against a real worker persist; the interleaving is proven at unit tier with
`InMemoryBlobStore`'s `create-if-absent` mode. A live two-sided test needs the Supabase stack and
belongs with M5, where the behaviour actually changes.
