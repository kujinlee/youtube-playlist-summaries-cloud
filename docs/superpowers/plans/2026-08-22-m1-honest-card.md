# M1 — The Honest Card: Implementation Plan (v2)

> **Anchor:** `stable-blob-addressing` — **ADR:** 0006, 0007
> **Goal:** The cloud worker's card describes the body it actually published. M1 of the stable-addressing spine; re-scoped and deferred 2026-08-22.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the cloud summary worker stamp `mdGeneratedAt`/`mdCorrectionsHash` **when, and only
when, its bytes became the live body** — so a video row can never advertise one document's
provenance beside another document's content.

**Architecture:** `persist_summary` layers the payload under the existing row
(`0021_cloud_sync_signals.sql:115-153`): layer (1) is the payload, layer (2) is
`|| (v.data - 'artifacts')` — *the existing row wins back* — and layer (3) re-applies only the
summary-owned keys the payload **provides**, because `jsonb_strip_nulls` turns an absent key into
"no write". Silence is therefore a meaningful signal: it means *"I am not telling you anything about
this field."* M1 makes the worker use that signal correctly — speak when it published, stay silent
when it did not. **No schema change, no migration, no change to the RPC.**

**Tech Stack:** TypeScript, Jest, existing `InMemoryBlobStore` test double. Unit tier only.

## Global Constraints

- **No schema change.** If a task appears to need a migration, stop — it belongs to M4.
- `mdHash` is imported from `@/lib/cloud-sync/content-hash` — never re-implement a hash.
- Branch + PR, always. Merging is a human gate.
- Anything longer than a line goes in a **file**, never a shell argument.
- **Reference the right row.** This work is **backlog #23 clause (a)**, not #19. #19 is the
  `transferClassA` content race, whose stated mechanism is that the transfer never writes
  `serialNumber`. Commit as `#23a`.

---

## v1 → v2: what round 1 changed and why

Round 1 was dual adversarial (`plan-append-only-m1-r1-codex.md`, `plan-append-only-m1-r1-claude.md`).
Both returned NOT CONVERGED. **v1's central patch was wrong**, and the reason is worth stating
because it is the third instance of one error class in a single session.

**v1 stamped unconditionally.** But the worker's bytes frequently never become the live body:
`SupabaseBlobStore.promote` is create-if-absent (`supabase-blob-store.ts:120-123`), and the
handler's only verification checks `ref.tempKey`, never the final key
(`summary-handler.ts:174`). When the final key is occupied — by a sync transfer, or by the previous
generation on any re-summarize — the worker's staged object is **deleted** and the existing body
stays live.

So on the very interleaving M1 was written for:

| | Card fields `mdGeneratedAt` / `mdCorrectionsHash` | Verdict |
|---|---|---|
| Today | layer (2) preserves the transferred values, which describe the body that **is** at the key | accidentally **correct** |
| v1 | layer (3) overwrites them with the worker's values, describing a **discarded** document | **worse than today** |
| v2 | stamped only after the bytes are read back and match | correct in both cases |

**The lesson, recorded rather than absorbed silently:** v1 reasoned about a write the storage layer
does not actually perform. The same class produced two other errors in this session — modelling a
mutable pointer the design had replaced with append-only, and ordering work from a roadmap
cross-reference instead of the referenced item's own trigger. **Before asserting what a write
achieves, read the function that performs it.**

Also corrected in v2: Task 2's fixture was unreachable and its assertions lived inside a loop over a
list that would be empty, so it would have passed having checked nothing (H1); Task 2's
characterization contradicted an existing `it.failing` tripwire under an explicit repo ban (Codex
Blocking / Claude H2); Task 3 pasted a whole file over one that already exists (Codex Medium /
Claude H3); Step 6 had no decision procedure (both halves).

---

## Scope: five more fields inherit the same way, and M1 does not fix them

`persist_summary` layer (3) re-applies twelve keys. Ten *can* come from the worker — but five of
those are optional and **absent when Gemini returns nothing for them**, because JSON serialization
drops `undefined` (the handler says so at `summary-handler.ts:146-148`). When `tags` is absent,
layer (3) drops it and layer (2) returns **the previous run's tags**: same mechanism, same row, a
card field describing a different body.

| Field | Always sent? |
|---|---|
| `language`, `ratings`, `overallScore`, `processedAt`, `docVersion` | yes |
| `videoType`, `audience`, `tags`, `tldr`, `takeaways` | **no — optional, absent when Gemini omits them** |
| `mdGeneratedAt`, `mdCorrectionsHash` | **no — never sent today. M1 fixes these two only.** |

**M1 scopes the five out deliberately** — they are quick-view prose, not provenance, and no guard
reads them. File a backlog row for them as part of Task 4. Do not let this plan imply the class is
closed at two.

## Consequences checked

| Consequence | Verdict |
|---|---|
| `ClassASignals.backfilled` flips to `false` for cloud rows | **No effect: `ClassASignals.backfilled` has no readers at all** (`grep -rn "backfilled" lib/ app/ components/ worker/ types/` — the only consumer, `reconcile-class-b.ts:43`, reads `FieldState.backfilled`, a different field on a different type fed by `annotationsEditedAt`). |
| Bytes did NOT land (occupied key) | Worker stays silent → layer (2) preserves the existing card → **unchanged from today.** This is what dissolves round-1 H6. |
| Bytes DID land, corrections settled | Cloud honestly reports `mdHash('')`; `lCur && !cCur` → `copyToCloud` (`reconcile-class-a.ts:39`) → corrected local body preserved. **The fix.** |
| Bytes DID land, corrections an **unresolved** Class-B conflict | Class A never runs — `sync-run.ts:707-720` logs the conflict, flags regen and `continue`s. The M1 change is invisible here. |
| Bytes DID land, no corrections anywhere | Both sides current; recency tiebreak as before, but on an honest cloud timestamp instead of a `processedAt` fallback. |
| Existing rows | Untouched until their next worker run. No backfill. |

---

## File Structure

- **Modify** `lib/job-queue/summary-handler.ts` — the write sequence at `:149-180`. Sole production change.
- **Create** `tests/lib/job-queue/summary-handler-card-provenance.test.ts` — Tasks 1 and 2.
- **Modify** `tests/lib/cloud-sync/reconcile-class-a.test.ts` — Task 3. **This file already exists**
  (created 2026-07-18) with an `S()` signal helper and `const CUR = 'C'`. Append inside its existing
  `describe`; do not redeclare either.
- **Modify** `docs/backlog.md`, `scripts/gen-backlog-page.py`, the roadmap — Task 4.

---

### Task 1: Stamp only what was published

**Files:**
- Modify: `lib/job-queue/summary-handler.ts`
- Create: `tests/lib/job-queue/summary-handler-card-provenance.test.ts`

**Interfaces:**
- Consumes: `makeSummaryHandler(serviceClient)` → `JobHandler`; `persistSummary(client, ownerId, playlistId, videoId, video, status)`; `mdHash(s: string): string`; `BlobStore.get(principal, key): Promise<Buffer | null>`.
- Produces: the `'promoted'` payload carries `mdGeneratedAt: string` (ISO 8601) and `mdCorrectionsHash: string` **only when the live bytes match what this run generated**. The `'committed'` payload never carries them. Tasks 2 and 3 rely on those two key names.

- [ ] **Step 1: Write the failing test**

Create `tests/lib/job-queue/summary-handler-card-provenance.test.ts`. **Open
`tests/lib/job-queue/summary-handler-promote-divergence.test.ts` and copy its fixture block
(imports through the end of `setup`, which closes at `:112`) rather than retyping it** — then apply
the two changes noted in the code below. Retyped fixtures lose identifiers; this repo has measured it.

```ts
/**
 * M1 (backlog #23a) — the worker may only describe a body it actually published.
 *
 * `persist_summary` layer (2) (`0021_cloud_sync_signals.sql:117`) lets the existing row win back
 * every key the payload omits, and `jsonb_strip_nulls` in layer (3) means an absent key is not a
 * write. Silence is therefore a real signal — "I am telling you nothing about this field" — and it
 * is the CORRECT signal whenever the worker's bytes did not become the live body, which happens
 * every time the final key is already occupied (`supabase-blob-store.ts:120-123`, create-if-absent).
 */
// ── fixture: copied from summary-handler-promote-divergence.test.ts:29-112, with two changes ──
//   1. add `import { mdHash } from '@/lib/cloud-sync/content-hash';`
//   2. `setup()` records whole PAYLOADS keyed by status, not just docVersion.
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
const WORKER_BODY = 'WORKER body, generated minutes later';

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

let persists: { status: string; video: Record<string, unknown> }[];

function setup(store: InMemoryBlobStore, mdContent: string, existingRow: unknown | null) {
  persists = [];
  (getWorkerStorageBundle as jest.Mock).mockResolvedValue({ blobStore: store, principal });
  (reserveVideoSlot as jest.Mock).mockResolvedValue(SERIAL);
  (readVideo as jest.Mock).mockResolvedValue(existingRow);
  (persistSummary as jest.Mock).mockImplementation(
    async (_c: unknown, _o: string, _p: string, _v: string, video: Record<string, unknown>, status: string) => {
      persists.push({ status, video });
    },
  );
  (summaryCore as jest.Mock).mockResolvedValue({
    frontmatter: {}, markdown: mdContent, mdContent, quickView: null,
    geminiFields: { language: 'en', ratings: {}, overallScore: 4 },
  });
}

const promoted = () => persists.filter((p) => p.status === 'promoted');
const committed = () => persists.filter((p) => p.status === 'committed');

describe('M1 (#23a) — the worker stamps only the body it published', () => {
  it('stamps the card when its bytes became the live body', async () => {
    // Empty store: nothing occupies the final key, so promote genuinely moves the object.
    const store = new InMemoryBlobStore({ promoteSemantics: 'create-if-absent' });
    const before = Date.now();
    setup(store, WORKER_BODY, null);

    await makeSummaryHandler(serviceClient)(job(), ctx);

    // Guard first — without it every assertion below is vacuous on an empty list.
    expect(promoted().length).toBeGreaterThan(0);
    // Precondition: the worker's bytes really are live. If this fails the test proves nothing.
    expect((await store.get(principal, SUMMARY_KEY))!.toString('utf8')).toBe(WORKER_BODY);

    for (const p of promoted()) {
      expect(p.video.mdCorrectionsHash).toBe(mdHash(''));
      const stamped = Date.parse(p.video.mdGeneratedAt as string);
      expect(Number.isNaN(stamped)).toBe(false);
      expect(stamped).toBeGreaterThanOrEqual(before);
    }
  });

  it('never stamps on the committed persist — nothing is published yet', async () => {
    const store = new InMemoryBlobStore({ promoteSemantics: 'create-if-absent' });
    setup(store, WORKER_BODY, null);

    await makeSummaryHandler(serviceClient)(job(), ctx);

    expect(committed().length).toBeGreaterThan(0);
    for (const p of committed()) {
      expect(Object.keys(p.video)).not.toContain('mdGeneratedAt');
      expect(Object.keys(p.video)).not.toContain('mdCorrectionsHash');
    }
  });
});
```

- [ ] **Step 2: Run and verify it FAILS**

Run: `npx jest tests/lib/job-queue/summary-handler-card-provenance.test.ts -t "stamps the card"`

Expected: FAIL — `p.video.mdCorrectionsHash` is `undefined`; the literal at
`summary-handler.ts:149-164` never sets it. The second test passes already (the handler sends
nothing today); it is a regression guard, not a red test.

**If the first test passes, stop.** The premise of this milestone is wrong.

- [ ] **Step 3: Add the import**

In `lib/job-queue/summary-handler.ts`, beside the existing `@/lib/...` imports:

```ts
import { mdHash } from '@/lib/cloud-sync/content-hash';
```

- [ ] **Step 4: Capture the generation time, leave `video` unstamped**

The `const video: Video = { … }` literal at `:149-164` stays **exactly as it is**. Immediately
before it, add:

```ts
    // M1 (#23a) — the moment this run's body came into existence. Captured here rather than at
    // persist time so the stamp describes the generation, not the bookkeeping that follows it.
    const generatedAt = new Date().toISOString();
```

- [ ] **Step 5: Stamp the promoted persist, and only if the bytes landed**

Replace the write sequence at `:172-179`:

```ts
    const key = `${baseName}.md`;
    const ref = await bundle.blobStore.putStaged(bundle.principal, key, Buffer.from(core.mdContent, 'utf-8'), 'text/markdown');
    if (!(await bundle.blobStore.exists(bundle.principal, ref.tempKey))) {
      throw new Error('staged upload not verified');
    }
    await persistSummary(serviceClient, job.ownerId, job.playlistId, job.videoId, video, 'committed');
    await bundle.blobStore.promote(ref);

    // M1 (#23a) — promote is NOT guaranteed to publish. SupabaseBlobStore.promote is
    // create-if-absent (supabase-blob-store.ts:120-123): when the final key is already occupied —
    // by a sync transfer, or by the previous generation on any re-summarize — it DELETES this
    // run's staged object and leaves the existing body live. The `exists` check above tests
    // ref.tempKey, never the final key, so it cannot see this.
    //
    // Stamping provenance for a body we did not publish is worse than staying silent: layer (2) of
    // persist_summary (0021:117) preserves the existing card, which correctly describes the body
    // that IS at the key. Silence is the honest answer, so prove publication before speaking.
    // Fail closed — an unreadable read-back is not proof.
    const live = await bundle.blobStore.get(bundle.principal, key).catch(() => null);
    const published = live != null && mdHash(live.toString('utf-8')) === mdHash(core.mdContent);
    const promotedVideo = published
      ? { ...video, mdGeneratedAt: generatedAt, mdCorrectionsHash: mdHash('') }
      : video;

    await persistSummary(serviceClient, job.ownerId, job.playlistId, job.videoId, promotedVideo, 'promoted');
```

**Why `mdHash('')` and not the user's corrections:** the worker applies no corrections, so "the empty
correction set was applied to this body" is the true statement. Making corrections *affordable* to
carry forward is backlog #23 clause (b) and belongs to M2. M1 stops the false claim; it does not
start applying corrections.

- [ ] **Step 6: Run and verify it PASSES**

Run: `npx jest tests/lib/job-queue/summary-handler-card-provenance.test.ts`
Expected: both tests PASS.

- [ ] **Step 7: Run the full unit suite**

Run: `npm test`

**Decision rule — this replaces v1's "read it and record it in the PR body", which licensed shipping
a regression.** This plan's Consequences table asserts that no Class-A outcome changes. Therefore:

> **If any Class-A or sync test fails, the Consequences table is wrong. STOP. Do not modify the
> test. Do not proceed to Task 2.** Record the failing test, the old and new `ClassASignals` on both
> sides, and which branch of `reconcileClassA` (`:21-50`) changed — then re-derive the table and
> re-review the plan before writing another line.

A green suite is the only outcome that permits continuing.

- [ ] **Step 8: Commit**

```bash
git add lib/job-queue/summary-handler.ts tests/lib/job-queue/summary-handler-card-provenance.test.ts
git commit -m "fix(#23a): the worker stamps the card only for a body it published"
```

---

### Task 2: Silence when the bytes did not land

**Files:**
- Modify: `tests/lib/job-queue/summary-handler-card-provenance.test.ts`

**Interfaces:** consumes Task 1's `setup`, `persists`, `promoted()`, `SUMMARY_KEY`, `WORKER_BODY`. Adds no exports.

This is the B1 regression guard — the case v1 got backwards. It also models the #19 interleaving
honestly: the handler read the row **before** the transfer landed, so `readVideo` returns the
pre-transfer state while the blob store already holds the transferred body.

**Do not add a test asserting the worker's body is discarded.** That behaviour is backlog #22 and
already has an `it.failing` tripwire at
`tests/lib/job-queue/summary-handler-promote-divergence.test.ts:148`, whose comment bans exactly
this: *"Do NOT rewrite the assertion to match current behaviour (dev-process.md bans it)."* A second
test asserting the opposite polarity would leave M5 with contradictory instructions.

- [ ] **Step 1: Write the test**

Append inside the existing `describe`:

```ts
  it('stays silent when a concurrent transfer already occupied the key', async () => {
    const store = new InMemoryBlobStore({ promoteSemantics: 'create-if-absent' });
    // t1: transferClassA committed the LOCAL winner at this key with `put` — deliberately not
    // `promote`, precisely because promote is create-if-absent (sync-run.ts:386-394).
    await store.put(principal, SUMMARY_KEY, Buffer.from('TRANSFERRED local body', 'utf8'), 'text/markdown');
    // t0: the handler's idempotency read happened BEFORE that transfer, so it saw a bare
    // reservation. Modelling it as null is what makes this the #19 window rather than a re-summarize.
    setup(store, WORKER_BODY, null);

    await makeSummaryHandler(serviceClient)(job(), ctx);

    expect(promoted().length).toBeGreaterThan(0);
    // The transferred body is still live — so its card, preserved by layer (2), still describes it.
    expect((await store.get(principal, SUMMARY_KEY))!.toString('utf8')).toBe('TRANSFERRED local body');
    for (const p of promoted()) {
      expect(Object.keys(p.video)).not.toContain('mdGeneratedAt');
      expect(Object.keys(p.video)).not.toContain('mdCorrectionsHash');
    }
  });

  it('stays silent when the read-back cannot be performed', async () => {
    const store = new InMemoryBlobStore({ promoteSemantics: 'create-if-absent' });
    setup(store, WORKER_BODY, null);
    jest.spyOn(store, 'get').mockRejectedValue(new Error('transient storage failure'));

    await makeSummaryHandler(serviceClient)(job(), ctx);

    // Fail closed: an unreadable read-back is not proof of publication.
    expect(promoted().length).toBeGreaterThan(0);
    for (const p of promoted()) {
      expect(Object.keys(p.video)).not.toContain('mdGeneratedAt');
    }
    jest.restoreAllMocks();
  });
```

- [ ] **Step 2: Run**

Run: `npx jest tests/lib/job-queue/summary-handler-card-provenance.test.ts`
Expected: all four PASS. If "stays silent when a concurrent transfer…" fails, Task 1 Step 5's
`published` gate is wrong — fix the handler, not the test.

- [ ] **Step 3: Commit**

```bash
git add tests/lib/job-queue/summary-handler-card-provenance.test.ts
git commit -m "test(#23a): silence when promote did not publish, and when read-back fails"
```

---

### Task 3: The tie case at the consumer

**Files:**
- Modify: `tests/lib/cloud-sync/reconcile-class-a.test.ts`

**Interfaces:** consumes the file's existing `S(o: Partial<ClassASignals>): ClassASignals` helper and `const CUR = 'C'`. Declares neither.

**This does not prove M1.** `reconcileClassA` is untouched by Task 1 — revert the handler entirely
and this still passes. It documents *why the stamp matters* at the consumer, and it is the one case
the file does not already cover: `:19-22` already tests current-beats-stale. Do not describe it as
evidence for M1; the falsifiable evidence is Tasks 1 and 2.

- [ ] **Step 1: Append inside the existing `describe`**

```ts
  // M1 (#23a) context — this is the shape an INHERITED card produced: cloud carried local's
  // corrections hash AND local's timestamp, because persist_summary layer (2) preserved both when
  // the worker sent neither. Both sides then read corrections-current, so :32-36 falls through to
  // the recency tiebreak at :49 — where `newer` is a strict `>`, an exact tie returns false, and
  // the UNCORRECTED body wins. M1 stops the worker producing this state; the function is unchanged.
  it('an exact mdGeneratedAt tie resolves to copyToLocal (why an inherited card is dangerous)', () => {
    const at = '2026-02-02T00:00:00.000Z';
    const r = reconcileClassA({
      local: S({ mdHash: 'LOCAL', mdCorrectionsHash: CUR, mdGeneratedAt: at }),
      cloud: S({ mdHash: 'WORKER', mdCorrectionsHash: CUR, mdGeneratedAt: at }),
      reconciledCorrectionsHash: CUR,
    });
    expect(r.action).toBe('copyToLocal');
  });
```

- [ ] **Step 2: Run and commit**

```bash
npx jest tests/lib/cloud-sync/reconcile-class-a.test.ts
git add tests/lib/cloud-sync/reconcile-class-a.test.ts
git commit -m "test(#23a): an exact mdGeneratedAt tie sends the corrected body the wrong way"
```

---

### Task 4: Reconcile the artifacts, then open the PR

**Files:** `docs/backlog.md`, `scripts/gen-backlog-page.py`, both plan documents.

- [ ] **Step 1: Narrow backlog #23 to clause (b)**

Clause (a) — *"a fresh summarize silently drops the user's corrections AND claims it did not"* — is
closed by M1 **for `mdCorrectionsHash`**. Say so, cite this plan, and leave clause (b) (the
affordability redesign) open as M2's subject.

- [ ] **Step 2: File the five-field residue as a new backlog row**

`videoType`, `audience`, `tags`, `tldr`, `takeaways` inherit through the same layer-2 mechanism when
Gemini omits them. Quote `summary-handler.ts:146-148`. Severity 🟡 — quick-view prose, no guard
reads them. Note that M5 dissolves it.

- [ ] **Step 3: Correct backlog #19**

Record what was measured: its corrections half was never #19's (that is #23a); its addressing half
dissolves at M5. Change the status cell away from `pending (needs spec)` — **#19 is a symptom, not
work.**

- [ ] **Step 4: Correct backlog #17**

Its text still says *"publication is a conditional update on one row"*. Round 4 deleted that CAS:
§5.1 is append-only and `current` is a view. Replace the sentence.

- [ ] **Step 5: Fix `DEPENDS[19]`, and record the gap the structure cannot express**

`DEPENDS[19]` → `dissolved-by` (was `survives`; §5.2 decided it).

⚠ **The "#23 gates the root" edge cannot be added.** `DEPENDS` is `item → (relation, root, note)`
(`gen-backlog-page.py:356-366`) — it expresses item→root only, and `ROOTS` has no parent field, so
there is no way to say a *root* is blocked by an item. Do not fake it by pointing #23 at the root
with a `blocked-by` relation: that reverses the arrow and the rendered graph would read backwards.
Add the fact as prose in the root's `detail` string and file a row for the structural gap.

- [ ] **Step 6: Regenerate and verify**

```bash
python3 scripts/gen-backlog-page.py
python3 scripts/check-docs.py; echo "check-docs exit=$?"
```
Expected: both exit 0. A non-zero `depends_errors` means an edge points at nothing — fix it.

- [ ] **Step 7: Commit, dual review, PR**

```bash
git add docs/backlog.md scripts/gen-backlog-page.py docs/superpowers/plans/
git commit -m "docs(#23a): reconcile the backlog against M1 — one clause closed, four rows corrected"
```

Then the dual gate per `docs/plugins.md` — `superpowers:requesting-code-review` **and**
`python3 scripts/codex-review.py --prompt-file <path> --out docs/reviews/m1-honest-card-codex.md`.
Codex unavailable for any reason → immediately fall back to a Claude adversarial review and note the
gap. Then `gh pr create --body-file <path>`. **Do not merge.**

---

## Self-review

**Coverage.** B1 → Task 1 Step 5 (conditional stamp) + Task 2 (both silence cases). H1 → reachable
fixture, `expect(...length).toBeGreaterThan(0)` guards, and a precondition assertion that the bytes
are live. H2/Codex-Blocking → the characterization is deleted, with a pointer to the existing
tripwire. H3/Codex-Medium → Task 3 appends and reuses `S()`/`CUR`. H6 → dissolved by B1's fix, and
recorded in the Consequences table. M1 → Task 3 no longer claims to prove M1. M2 → the `backfilled`
row now makes the stronger, verifiable claim. M3 → Task 4 Step 5 states the structural limit instead
of an unexecutable instruction. M4 → the five-field section plus Task 4 Step 2. M5 → every commit
message is `#23a`. M6/Codex-Medium → Step 7's stop rule. Codex High → the unresolved-corrections row
in the Consequences table.

**Placeholders.** None. The one cross-file instruction (Task 1's fixture) names the file and the
block boundary (`setup` closes at `:112`) and lists the two edits to apply.

**Type consistency.** `mdGeneratedAt` (string, ISO 8601) and `mdCorrectionsHash` (string) match
`0021:131-132` and `ClassASignals` (`types.ts:32`). `persists`/`promoted()`/`committed()` are
declared in Task 1 and used unchanged in Task 2. Task 3 declares nothing.

**Known gaps.** (1) No integration-tier test drives a real `transferClassA` against a real worker
persist; the interleaving is proven at unit tier via `create-if-absent`. That belongs to M5. (2) The
read-back in Step 5 adds one `GET` per summary job — negligible against a Gemini call, but it is a
new storage call on the money path and should be named in the PR body.
