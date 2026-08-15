# Adversarial review — cloud blob key encoding v16, round 14, Codex

Subject: working tree `docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md` at draft v16.

I reviewed the repaired discriminator in `docs/review-method.md`, not the missing root `review-method.md`. The controlling test is quoted at `docs/review-method.md:65-71`: "Can a redesign remove it?" A stale decision sentence is its own outcome (`docs/review-method.md:84-89`), not mechanism or branch coverage.

## Findings

### 1. Medium — the new `videoId` credential is only specified for the cloud serve writer and receiver-side envelope branch

Evidence:

`docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:1005-1011`:

```md
**DECISION: add `videoId?: string` to `ModelEnvelopeSchema`.** Ownership becomes
`envelope.videoId === row.videoId` — two immutable ASCII ids. Relocation cannot break it because
nothing in the answer moves. Verified: `serve-doc.ts:174` already has `videoId` as an explicit param of
`resolveMagazineModel` (`:48`, destructured `:70`, already used for `docKey` and the reserve RPC);
`sync-run.ts:464` ships `decision.envelope` wholesale, so it propagates correct by construction.
`model-store.ts:25-26` records that `.strict()` was *"intentionally removed"* so a new field cannot
break an old reader.
```

`docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:1128-1132`:

```md
| 18j | `companionTransfer` **refuses** ship/delete when the receiver envelope's **`videoId`** differs from the row's — and **returns an `error`, never throws**, so the baseline still advances (round-13 M2) | integration |
| 18j2 | `companionTransfer` **ships** when the receiver read is `none` or `unknown` — no envelope, and the common case (round-12 H2) | integration |
| 18j3 | **After a cloud base relocation, the ship still succeeds** — the credential survives `remap` (round-13 H1) | integration |
| 18j4 | An envelope with **no `videoId`** (legacy) proceeds, and **`sourceMd` is not consulted** | integration |
| 18j5 | `serve-doc` writes `videoId` into every new envelope | unit |
```

But there is another production model writer:

`lib/html-doc/generate.ts:49-60`:

```ts
  const base = video.summaryMd.replace(/\.md$/, '');
  await writeModelEnvelope(principal, base, {
    sourceMd: video.summaryMd,
    generatedAt: new Date().toISOString(),
    sourceSections: parsed.sections.map((s) => s.title),
    generatorVersion: GENERATOR_VERSION,
    model,
    // Stage 3 (§4.2): hash the MD BODY (`md`, line ~33), NOT `sourceMd`/`video.summaryMd`
    // (the blob key/filename) — decideCompanion (Task 8) compares against mdHash(body); a
    // filename-hash would never match and every synced companion would be deleted.
    sourceMdHash: mdHash(md),
  }, resolvedBlob);
```

The spec also relies on shipping the selected envelope verbatim:

`lib/cloud-sync/sync-run.ts:451-464`:

```ts
  const [senderModel, receiverModel] = await Promise.all([
    readModelSide(winner, base), readModelSide(loser, base),
  ]);
  const decision = decideCompanion({ winnerMdHash, senderModel, receiverModel });
  if (decision.kind === 'ship') {
    // M-R6-1 — a throw here would be STICKY, not merely noisy: the Class-A body already landed, so the
    // next run's reconcileClassA returns 'skip' and the companion step (gated on !== 'skip') never
    // runs again. The receiver would keep a model built from the PRE-SYNC body — and if its section
    // titles and generatorVersion still match, the serve path's drift guard cannot see it, so it is
    // served as fresh forever (the prose-only-change case behind H-R5-1). Swallow the failure the way
    // the delete below already does and report the share as unready, so the staleness is at least
    // visible; the error is returned so it still surfaces in report.errors.
    try {
      await writeModelEnvelope(loser.p, base, decision.envelope, loser.blob);
```

Concrete failure scenario:

1. After this slice, a local user runs the local HTML generation path. If implementation follows behavior 18j5 literally, only `serve-doc` is changed, so `runHtmlDoc` still writes a fresh envelope with no `videoId`.
2. A later local→cloud Class-A transfer reads that local sender envelope, `decideCompanion` returns `ship`, and `companionTransfer` writes `decision.envelope` wholesale to cloud.
3. The receiver now has a post-v16 envelope that is indistinguishable from legacy for the new ownership guard. The intended credential does not become universal through normal use; it remains absent on one writer path.
4. A stricter variant of the same gap: if a sender envelope ever carries `videoId` for a different row while still matching `winnerMdHash`, the current v16 behavior names only the **receiver** mismatch. It does not say to reject the sender envelope before `ship`, even though `sync-run.ts:464` copies that envelope into the loser.

I am not calling this a stale-by-construction credential. `videoId` survives `remap` and `copyBlob` because the bytes are copied unchanged, and it is not derived from the mutable base. The gap is that v16 has not enumerated every writer and every envelope branch that must participate in the comparison.

Proposed fix:

- Change behavior 18j5 from "`serve-doc` writes `videoId` into every new envelope" to "every model-envelope writer writes `videoId`", and name at least `serve-doc.ts:174` and `generate.ts:50`.
- Add a contract or unit behavior proving `writeModelEnvelope` callers cannot create a new non-legacy envelope without `videoId`, or make the API require it where the caller has a row id.
- Extend 18j to cover both envelope-bearing sides: reject a sender envelope whose `videoId` is present and differs from the reconciled row before `ship`, and reject a receiver envelope whose `videoId` is present and differs before `ship` or `deleteReceiverModel`.

Classification:

- Kind: branch-coverage. A redesign would not remove it; the `videoId` shape is sound, but v16 did not exhaust the writer set and the sender/receiver envelope branches it governs.
- Caused by v16 fixes: yes. This is introduced by the new `videoId` credential replacing `sourceMd`.

### 2. Medium — §3.6's `transferClassA` recipe still shows a direct `put` path without the v16 servability guard

Evidence:

`docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:554-561`:

```md
**Fix, both mechanical:**

1. Move the adopt guard **above** `ensureReceiverSlot`, next to the existing WB-H1 check at
   `sync-run.ts:236-238`. No row is created, the video stays one-sided, and the refusal genuinely
   re-fires every run.
2. **Guard `transferClassA` too.** The Class-A path is a second entrance to the same durable state,
   and §2.5 already lists it as write entrance 3. Enumerating the entrances was never the problem —
   *guarding only the one we were thinking about* was.
```

`docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:825-835`:

```md
**R3 — Class-A transfer: the identity question is answered by the loser's RECORD.**
`transferClassA` is required to overwrite, so R1 does not apply and it keeps `put`. The right question
is not *"is the occupant this same logical key?"* but **"is this address the loser's own?"** — and the
caller already holds the answer at both call sites:

```ts
if (!canonicallyEqualName(loserVideo.summaryMd, key)) {
  const dest = await loser.blob.tryGet(loser.p, key);      // only on this branch
  if (dest.ok || dest.reason === 'unreadable') throw …;    // occupied by something we do not own
}
await loser.blob.put(loser.p, key, staged, 'text/markdown');   // unchanged
```
```

`docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:1154-1156`:

```md
| 26 | **The adopt refuses a non-servable key before `ensureReceiverSlot`** — no receiver row is created — and the error message names the manual repair | integration |
| 26b | **The refusal survives a SECOND run**: re-running sync does not route around it via the two-sided Class-A path (round-13 H2) | integration |
| 26c | `transferClassA` refuses a non-servable key too — the second entrance to the same durable state | integration |
```

Concrete failure scenario:

1. An implementer edits `transferClassA` from the detailed §3.6 R3 recipe.
2. They add the loser-record ownership probe and keep `await loser.blob.put(loser.p, key, staged, 'text/markdown')` as shown.
3. They miss the separate §3.5 sentence requiring `isServableSummaryKey(key)` at the same entrance.
4. Run 2 of the round-13 H2 scenario is still closed if behavior 26c is written correctly, but the design text that governs the function still contains a stale direct-write recipe. If the behavior is omitted, weakened, or written after the implementation, a non-servable key can still land through the two-sided Class-A path.

Proposed fix:

- Inline the servability guard into the R3 code block before any staging/write:

```ts
if (!isServableSummaryKey(key)) throw new Error(...manual repair...);
if (!canonicallyEqualName(loserVideo.summaryMd, key)) {
  const dest = await loser.blob.tryGet(loser.p, key);
  if (dest.ok || dest.reason === 'unreadable') throw ...;
}
await loser.blob.put(loser.p, key, staged, 'text/markdown');
```

- State that `transferClassA` now has two independent guards: servability of the incoming key and loser-record ownership of the destination.

Classification:

- Kind: stale cross-reference. A redesign would not remove it; v16 changed an enforcement point and one implementation recipe still states the old direct `put` path without the new guard.
- Caused by v16 fixes: yes. This was introduced by moving the adopt guard and adding the `transferClassA` guard in v16.

## Checks that held

- The `videoId` credential is not stale by construction in the way `sourceMd` was. `reconcileCloudBase`/`copyBlob` byte-copying preserves an immutable id; it does not derive the credential from the mutable base.
- The moved adopt guard is structurally right. Placing it above `ensureReceiverSlot` leaves no receiver row, so a second run remains one-sided and re-enters the same refusal. Behavior 26b is writable: seed a local-only adopted non-servable key, run sync twice, and assert the cloud receiver row is absent both times.
- The legacy branch is an explicit compatibility trade. It can fail to protect a manually misplaced paid model that an old `sourceMd` check might have refused, but I did not find a normal writer path that creates that cross-video legacy state. Falling back to `sourceMd` would reintroduce the measured stale-by-construction defect.
- The prompt's named stale-reference grep did not find a live superseded `sourceMd` credential instruction, live `'already-exists'` return contract, or live instruction to change `promote` rather than add `promoteIfAbsent`. Those occurrences are historical notes, rejected wording, or mutation guards.

CONVERGED
