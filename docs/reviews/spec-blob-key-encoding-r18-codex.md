# Adversarial review — cloud blob key encoding spec v20 — round 18 Codex

## Medium — §3.5.1b row 6 misses one of `mdKey`'s producers, so this round's operand falsifier fires

Evidence:

```ts
// lib/share/serve.ts:44-48
const artifact = (vid.data as { artifacts?: { summaryMd?: { key?: string; status?: string } }; summaryMd?: string })
  .artifacts?.summaryMd;
if (artifact?.status !== 'promoted') return denied;
const mdKey = artifact?.key ?? (vid.data as { summaryMd?: string }).summaryMd;
if (!mdKey) return denied;
```

Spec row:

```md
docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:1011
| 6 | **The share guard** | `mdKey` from `getShareServeContext` (`lib/share/serve.ts:13`) | **One** — the cloud row's `summaryMd` | BLIND |
```

Read to the end: `artifact?.key ?? summaryMd` has two producers. Arm A produces `artifacts.summaryMd.key`; arm B produces top-level `summaryMd`. The table names only top-level `summaryMd` and therefore fails the new operand question exactly as stated in the round-18 falsifier.

Concrete failure scenario: a future implementation or reviewer follows row 6 and checks only `summaryMd`, while a promoted artifact carries `artifacts.summaryMd.key = 'nested/x.md'` and top-level `summaryMd = 'safe.md'`. The live code would choose the artifact key first; the table's producer list directs attention to the fallback instead. Today this is not a data-loss path because the proposed guard is still provenance-blind and should deny either bad producer identically, but the rebuilt instrument has not held.

Proposed fix: do not patch in a fourth hand table. The falsifier condition was explicit: a fourth missed producer under the operand question means manual producer enumeration is not reliable enough. Replace §3.5.1b with an executable/source-derived instrument, or reduce it to rows generated from named expressions (`??`, ternaries, fallbacks) plus a checked citation to the exact expression.

Classification: `branch-coverage`. Caused by v20's own fixes: yes, this is in the rebuilt v20 §3.5.1b table.

## Low — v20 still states the old adopt-guard location after saying the location is stated once

Evidence:

```md
docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:959-961
**THE GUARD GOES IN THE CALLER, on the `to = cloudSide` arm only — and specifically ABOVE
`sync-run.ts:626`**
```

Contradicting residues:

```md
docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:623-624
The adopt refusal (`sync-run.ts:236-238`, **above `ensureReceiverSlot`** ...
```

```md
docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:1043
| `copyAdditiveVideo` — **receiver is the CLOUD** (`copyToCloud`) | **the adopt guard**, above `ensureReceiverSlot` (`sync-run.ts:236-238`) | ...
```

Read to the end: line 881 says row 4 is the one place the caller location is stated, but lines 623 and 1043 still state the old in-function location as if normative. Lines 667-668 also preserve the old historical instruction, but the two above are enough because they are current behavior/cost text rather than quoted code.

Concrete failure scenario: an implementer follows §3.5.2's refusal table and places the guard inside `copyAdditiveVideo` at `sync-run.ts:236-238`. That is the location §3.5.1b itself says cannot know `presentIsLocal`, reopening the direction-agnostic guard problem round 16 closed unless the implementer adds type sniffing.

Proposed fix: leave exactly one normative statement: row 4 / the caller branch above `sync-run.ts:626`. Change the §3.5 cost bullet and §3.5.2 refusal table to point to row 4 instead of naming `sync-run.ts:236-238`.

Classification: `stale cross-reference`. Caused by v20's own fixes: yes, v20 attempted the "state once" repair and left old statements behind.

## Low — `origin` is specified with a different predicate from the ternary arm it describes

Evidence:

```ts
// lib/cloud-sync/reconcile-serial.ts:150-155
if (localVideo.serialNumber == null || !cloudVideo.summaryMd) return { diverged: false };
const from = baseOf(cloudVideo.summaryMd);
const to = localVideo.summaryMd
  ? baseOf(localVideo.summaryMd)
  : baseOf(applySerial(cloudVideo.summaryMd, localVideo.serialNumber));
return from === to ? { diverged: false } : { diverged: true, from, to };
```

Spec:

```md
docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:840-843
`origin` is `localVideo.summaryMd != null ? 'vault-filename' : 'cloud-key'`
```

Read to the end: the ternary chooses arm A by truthiness of `localVideo.summaryMd`; the proposed `origin` chooses by nullishness. `summaryMd: ''` takes arm B in the code but would be reported as `vault-filename` by the spec's origin expression.

Concrete failure scenario: a malformed local row has `serialNumber = 3` and `summaryMd = ''`, while the cloud row has `summaryMd = 'a'.repeat(128) + '.md'`. `describeDivergence` takes arm B and computes `newBase` from `applySerial(cloudVideo.summaryMd, 3)`, but the v20 origin expression reports `vault-filename`. If 26d3 fires, the operator is told to repair the wrong subject.

Proposed fix: derive `origin` from the same branch as `to`, preferably by returning it from `describeDivergence` together with `to`, or at minimum use the exact same truthiness predicate. Also add the empty-string case as a unit test if empty `summaryMd` is accepted by `VideoSchema`.

Classification: `branch-coverage`. Caused by v20's own fixes: yes, the `origin` field is part of v20's B1 repair.

## Checks that held

B1's `oldBase` conjunct does not reopen round-14 B1 in the old-unservable/new-unservable case. The relocation copies from old unservable to new unservable, updates the row, verifies, and only then deletes sources; it does not destroy a working advertisement because the old one was already unservable.

Behaviors 26d, 26d2, and 26d3 are writable. 26d3 is constructible: a legacy bare cloud key with 128 ASCII letters plus `.md` is servable at 131 code points; `applySerial` adds a `NNN_` prefix and pushes the resulting key over the bound. Existing serial-prefixed max keys can also grow by one when renumbered from a one-digit historical prefix to the padded form.

Behavior 26f's rewritten observable separates the placements. The caller-above-626 placement refuses before `readMdBody(from.blob, ...)`; the inside-`copyAdditiveVideo` mutant necessarily has already executed the sender blob `get` at `sync-run.ts:626-627`. `readMdBody` is observable by a fake sender blob store recording `get` calls for the summary key.

The rollout table's 41 call sites held under recount: 3 production calls plus 38 test/e2e calls to `writeModelEnvelope`/`writeModelEnvelopeWithin`. The rough literal count also matches the listed helpers/fixtures.

18j8 is writable as a unit test: feed `rewriteEnvelopeSourceMd` JSON containing `videoId`, assert `sourceMd` changes and `videoId` survives. The mutation "strip unknown fields in `rewriteEnvelopeSourceMd`" would go red.

L5's fourth caller enumeration is complete for the scoped claim I checked: the non-test `MetadataStore` data-writing calls include the three sync entrances plus `serial-migrate-exec.ts:130,146`; other non-test callers either update non-summary fields or go through annotation/update paths outside this seam.

Falsifier judgment: fired. §3.5.1b row 6 misses a producer of the guarded value.

Phase 1 judgment: not ready to leave Phase 1. The design mechanisms look stable, but the rebuilt instrument failed its own exit test.

NOT CONVERGED
