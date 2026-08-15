# Design pass — the model-ownership credential (backlog #36, owed by round-13 H1)

**Scope, deliberately narrow.** Round 13's H1 fired the FIX→REDESIGN falsifier on §3.6.4's `sourceMd`
credential. The reviewer scoped what was owed: *a design pass on the third residual's credential only*
— R1–R4 were attacked that round and held. This is that pass. It is **not** a fifth rewrite of the
vault write protocol.

**Trigger question as originally posed:** *"What proves that `models/<base>.json` belongs to `base`?"*

---

## 1. The question was wrong, and that is the finding

The user reframed it, and the reframing dissolves the problem rather than answering it:

> *"if we always use a stable part (videoId) as identification and the rest of the name is decorative
> — summary, dig section — there will not be an issue. Besides, a blob always carries its
> identification token."*

**MEASURED — the second half is true of summaries and false of model envelopes:**

```
summary body    video_id: "dQw4w9WgXcQ"        summary-core.ts:103   ← a stable id
model envelope  sourceMd:  "003_wk08-intro.md"  model-store.ts:17     ← a NAME
```

`ModelEnvelopeSchema` has **no stable id at all**. The summary was given an identity token; the model
was given a *provenance* token — *what it was made from* — and then asked an *identity* question.
Those are different facts, and only one of them survives a rename.

So `sourceMd` is not stale by accident. **It is the wrong kind of credential**, and any repair that
keeps it name-shaped (rewrite it at `remap`, or switch to `sourceMdHash`) still answers *"does this
file match this address?"* rather than *"whose is it?"*

---

## 2. Prior art — this was decided before, drifted, and was caught and undersized

Found by searching every doc for the identifiers involved. All three are still on disk.

| Where | What it says |
|---|---|
| `2026-07-02-stage-1c-supabase-adapters-design.md:160` | the original layout keys models by **`id`** — `models/${id}.json` — while the summary and PDF use `baseName`. The model's address **drifted from id to base** afterwards |
| `docs/reviews/task-1f-a-6-materialize-helper.md:19` | the drift **was caught**: *"`base`/`videoId` coupling (Claude Minor): the reserve RPC keys the charge on `p_video_id=videoId` while the cache reads/writes on `base`. **In tests `base===videoId`**"* |
| `2026-08-03-stable-blob-addressing-design.md:179-184` | the destination, fully specified: `<workspaceId>/videos/<videoId>/<generationId>/model.json`. **PARKED** by user decision 2026-08-11 |

**Why it was rated Minor is in the finding's own sentence: `base === videoId` in the fixtures.** A test
that sets two distinct values equal cannot observe them diverging — the same fixture defect this
project has now paid for twice (see round-11 M3, *"right for the input it was tested on"*).

Round-13 H1 is that Minor arriving three months later, on a paid artifact.

---

## 3. Options

| | Answers | Cost | Verdict |
|---|---|---|---|
| **A. `sourceMd` rewritten at `remap`** | *does the name match?* | small; mirrors what local already does (`serial-provenance.ts:16`) | **No** — keeps a name-shaped credential for an identity question. Fixes this instance, not the class |
| **B. `sourceMdHash`** | *does the content match?* | free — already in the schema | **No** — same category error, and it goes stale on any legitimate MD edit |
| **C. `videoId` in the envelope** | ***whose is it?*** | **one optional schema field** | **RECOMMENDED** |
| **D. re-address models by `videoId`** | question never arises | migration of derived artifacts (**8 objects in prod today**) | **Right, and parked.** This is the 2026-08-03 spec. Record C as its down payment |

---

## 4. Recommendation: C, with D named as the destination

**Add `videoId?: string` to `ModelEnvelopeSchema`.** The ownership test becomes
`envelope.videoId === row.videoId` — a comparison of two immutable ASCII ids. Relocation cannot
break it, because nothing in the answer moves.

**Both writers verified:**

| Writer | `videoId` available? |
|---|---|
| `serve-doc.ts:174` (`writeModelEnvelopeWithin`) | **Yes** — an explicit param of `resolveMagazineModel` (`:48`), destructured at `:70`, already used for `docKey` and the reserve RPC. Free to add |
| `sync-run.ts:464` (`writeModelEnvelope`) | **Yes, by propagation** — it ships `decision.envelope` wholesale, so a sender envelope carrying `videoId` arrives correct by construction (same video) |

**Optional, not required — and the schema is already built for it.** `model-store.ts:25-26` records
that `.strict()` was *"intentionally removed"* so a new-writer envelope cannot make an old reader
return `null`. Adding a field is an anticipated, non-breaking operation.

**The legacy window, stated rather than discovered.** The 7 envelopes in prod today carry no
`videoId`. The rule must therefore be:

| Envelope | Ownership test |
|---|---|
| `videoId` present | `envelope.videoId === row.videoId`; **refuse** the destructive operation on mismatch |
| `videoId` absent (legacy) | **cannot prove ownership ⇒ ship / proceed**, which is exactly today's behaviour and therefore not a regression. **Do NOT fall back to `sourceMd`** — round-13 H1 measured it stale by construction, so the fallback would reintroduce the defect for precisely the envelopes least able to survive it |

Self-healing: any re-serve rewrites the envelope through `serve-doc.ts:174`, which will carry
`videoId`. The legacy window closes without a migration.

**`sourceMd` is not deleted.** It remains what it always was — provenance, used by the freshness
guard and the footer. It simply stops being asked an ownership question.

---

## 5. What this does and does not close

**Closes:** round-13 H1 in full. The credential is stable by construction; `reconcileCloudBase` may
byte-copy the envelope freely because the field it carries does not depend on the address.

**Does not close, and must not be claimed to:** the model is still *addressed* by a mutable `base`, so
relocation still happens and `remap` still runs. **Option D is what removes that**, and it is parked.
This pass buys the correctness without the migration; it does not make D unnecessary.

**Behaviors to replace §3.6.4's:**

| # | Behavior |
|---|---|
| 18j | `companionTransfer` **refuses** ship/delete when `envelope.videoId` is present and differs from the row's | integration |
| 18j2 | `companionTransfer` **ships** when the envelope carries no `videoId` (legacy) — and **does not** consult `sourceMd` | integration |
| 18j3 | After a cloud base relocation, ship still **succeeds** — the credential survives `remap` | integration |
| 18j4 | `serve-doc` writes `videoId` into every new envelope | unit |

Mutation: *make the legacy branch fall back to `sourceMd`* must turn **18j3** red.
