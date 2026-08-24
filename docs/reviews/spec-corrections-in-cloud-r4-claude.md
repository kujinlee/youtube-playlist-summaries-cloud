# Adversarial review — corrections-in-cloud **slice A** (round 4, Claude half)

Subject: `docs/superpowers/specs/2026-08-22-corrections-in-cloud-design.md` at commit `88214d2`.
Scope: the six areas the brief names, plus the citation audit and the coherence pass. Nothing
belonging to slice B (backlog #60) or slice C (backlog #61) is filed here.

**Counts: 2 Blocking, 5 High, 6 Medium, 4 Low.**

> **Added after the first pass, at the coordinator's request.** **H5** independently confirms — and
> extends — the coordinator's finding about the `:77-79` stamp on a bare press. It is the most
> consequential item in this review after the two Blockings, and I would not object to it being
> promoted to Blocking; my reasons for filing it High are stated in the finding.

**Verdict up front.** The split was right and the document is much closer to implementable. But the
brief's primary question — *did these fixes introduce new defects?* — answers **yes, twice**, and
both times in the same shape this repo keeps producing: a fix that is correct about the thing it
looked at and wrong about the layer underneath it.

- §4.1 measured the **function body** and concluded `update_video_annotations` does not bump
  `updated_at`. It measured the right function and missed a **trigger** (B1). §8's "no migration of
  any kind" rests entirely on that conclusion.
- §2 fixed the magazine staleness by **deleting** the envelope, having measured `isFresh`. The
  envelope it deletes is also the *only* thing the anonymous share path can render from, and that
  path is forbidden to regenerate it (H1).

- §7's split of the sync falsifier (r3 H6) replaced a row that a *correct* implementation failed with
  a row that a **live defect passes** (H5). The transition it asserts as success is produced equally
  by a bare press that applies nothing.

The count of *"a fix that moved or reintroduced a defect"* goes from seven to ten.

## What I executed

| Command / read | Result |
|---|---|
| `git show --stat 88214d2` | 1 file, +106/−29. Diff is the spec only ✅ |
| read `supabase/migrations/0021_cloud_sync_signals.sql` in full | `update_video_annotations` body updates `data` only; `updated_at = now()` at `:89`, `:149` only ✅ (but see **B1**) |
| `grep -rn "create trigger" supabase/migrations/` | **`0015_video_updated_at_trigger.sql:13` — `before update on videos … for each row`** ⛔ |
| read `lib/html-doc/read-model.ts`, `lib/html-doc/model-store.ts` | `isFresh` has no content hash ✅; the **envelope does** (`model-store.ts:23`) — see **H2** |
| read `app/s/[token]/route.ts:102-103`, `lib/html-doc/serve-doc.ts:78-151` | envelope is the sole input to both the share render and the `owner_over_budget` fallback — see **H1** |
| read `lib/storage/supabase/supabase-blob-store.ts:116-134`, `lib/storage/supabase/consistency.ts:15-41` | `promote` is create-if-absent; `writeArtifact` is the repo's `summaryMd` write — see **B2** |
| read `lib/cloud-sync/reconcile-class-a.ts` in full | §7's needsRegen row **is** falsifiable and non-vacuous ✅ — see the note under M4 |
| read `lib/gemini.ts:30-47, 105, 271-281, 470-510`; `lib/gemini-cost.ts:10-40` | every §5.4 input correct; arithmetic recomputed ✅ — but see **H3**, **M2**, **M3** |
| read `fly.toml`, `next.config.ts`, `node_modules/next/dist/docs/…/maxDuration.md` | `output: 'standalone'` + `node server.js` on Fly; no adapter reads `maxDuration` — see **M1** |
| citation audit — every `file:line` in the changed sections | **all correct.** Details at the end |

**NOT VERIFIED / not run:** the unit suite (`npm test`) — I reviewed a document, not code, and the
tree is unchanged from r3's green baseline. Fly's actual proxy/idle request timeout — I have no
access to the deployed app, so M1's *consequence* is bounded by what the docs and config prove, not
by a measurement.

---

## Blocking

### B1 — `update_video_annotations` **does** bump `updated_at`. A trigger does it, and §4.1 only read the function.

**Where.** Spec §4.1 (lines 174-201) and §8 (line 294). Code:
`supabase/migrations/0015_video_updated_at_trigger.sql:9-14`.

The spec's central new claim is:

> `update_video_annotations` (`0021:19-56`) writes **only the `data` column**; the two
> `updated_at = now()` statements in that migration are at `:89` … and `:149` …, both outside it.

Both halves of that sentence are **true and irrelevant**. Migration 0015 installed a row-level
trigger *underneath* every one of these RPCs:

```sql
-- supabase/migrations/0015_video_updated_at_trigger.sql:9-14
create or replace function set_videos_updated_at() returns trigger
  language plpgsql set search_path = public as $$
begin new.updated_at = now(); return new; end $$;
drop trigger if exists trg_videos_updated_at on videos;
create trigger trg_videos_updated_at before update on videos
  for each row execute function set_videos_updated_at();
```

Its own header comment says why, in the words that make the spec's inference unsafe: *"This BEFORE
UPDATE trigger sets `updated_at = now()` on **EVERY** row update — idempotent alongside the RPCs
… that already set it explicitly inline."* The inline `updated_at = now()` at `:89`/`:149` is
**redundant**, not the mechanism. `grep -rn "trg_videos_updated_at"` over the whole tree returns
only 0015 — nothing drops or disables it later.

**Failure scenario.** A cloud user opens the corrections panel, clears the field, presses apply.
Per §4.1 the route issues `updateVideoAnnotations(p, id, {}, ['corrections'])`. The RPC's `update`
fires `trg_videos_updated_at`; `videos.updated_at` moves to now. Later a sync runs.
`deriveHumanSnapshot` (`lib/cloud-sync/backfill.ts:20-32`) computes
`provisional = video.updatedAt ?? video.processedAt` and uses it as the `editedAt` for **every**
Class-B field that has no real `annotationsEditedAt` entry:

```ts
// lib/cloud-sync/backfill.ts:21-29
const provisional = video.updatedAt ?? video.processedAt;
…
: { value, editedAt: real ?? provisional, backfilled: real === undefined };
```

So the cloud row's *never-edited* `personalNote` now carries a brand-new `editedAt` and wins
Class-B reconciliation against a genuinely newer local edit. This is precisely the hazard §4's own
table row flags (line 172) — and §4.1 is presented as the section that settles §4's unknowns.

**Second consequence, independent of the trigger.** Even if the trigger did not exist, the bare
press still writes `{ tldr, takeaways, summaryHtml: null }` via `updateVideoFields` →
`merge_video_data` (`supabase-metadata-store.ts:133-146`), which sets `updated_at = now()`
explicitly at `0021:89`. Quick-view is unconditional by §3's own requirement, so **no press can
avoid moving `updated_at`**, whatever RPC the corrections write uses. §4.1 cannot settle this
because the field it needs to protect is moved by a write §3 mandates.

**Why Blocking.** §8 line 294 reads *"**No migration of any kind.** v3 hedged here; §4.1 settles
it."* That is now an unsupported claim in the section a plan reads to decide whether it needs a
schema change. Any of the three plausible resolutions is a design decision, not an implementation
detail: (a) accept the `updated_at` bump and state that `deriveHumanSnapshot`'s provisional path is
knowingly degraded by every correction press; (b) change `deriveHumanSnapshot` to stop treating
`updatedAt` as an annotation-edit proxy (a sync-semantics change with its own review); (c) make the
trigger conditional, or add a column — **a migration**, which §8 forbids.

**Suggested fix.** Correct §4.1's premise to name the trigger and say what it means: no RPC in this
schema can update a `videos` row without moving `updated_at`. Then either delete §8's "no migration
of any kind" bullet or re-derive it from a stated decision to accept (a). Add the observation that
would make it fail to §7 (see M4). Keep the *rest* of §4.1 — the `updateVideoAnnotations` surface,
the `undefined`-is-dropped clear bug, and the caller-owns-the-conditional rule are all correctly
measured and all stand.

---

### B2 — the corrected body's blob write is unspecified, and the repo's default protocol for it silently discards the paid result

**Where.** Spec §2, "`app/api/videos/[id]/regenerate/route.ts` — gains a real cloud branch"
(lines 126-133), and §0's slice-B row (line 30). Code: `lib/storage/supabase/consistency.ts:17-41`,
`lib/storage/supabase/supabase-blob-store.ts:116-134`.

§2 enumerates exactly what the cloud branch gains: `?playlist=<uuid>`, `createServerSupabase`,
`getUser`, `resolveOwnedPlaylistKey`, `getPrincipalFromSession`,
`getStorageBundle({ supabaseClient })`, rejecting `outputFolder`, and moving resolution inside the
try. It never says **how the corrected markdown is written back**. Today that write is
`fs.promises.writeFile(mdPath, …)` at `route.ts:69` — the single most load-bearing line the cloud
branch has to replace, and the spec is silent on it.

That silence is not neutral, because the repo has an established convention for writing a
`summaryMd` artifact and it is the wrong one here:

```ts
// lib/storage/supabase/consistency.ts:14-15, 27-41
 * Sequence: putStaged → verify temp exists → updateVideoFields(committed) → promote → updateVideoFields(promoted)
export async function writeArtifact(opts: { … kind: ArtifactKind; key: string; … })
```

and `promote` is create-if-absent:

```ts
// lib/storage/supabase/supabase-blob-store.ts:119-123
// move = copy+delete (non-atomic). Idempotent: if final already present, ensure temp gone and return.
if (await this.exists(ref.principal, ref.finalKey)) {
  await this.b().remove([from]).catch(() => {});
  return;
}
```

A correction never changes the key — `base` is derived from the persisted `video.summaryMd`
(`lib/html-doc/serve-summary-core.ts:71`) and §2's own structural validator *pins the headings*, so
nothing that feeds the key can move. The final object therefore **always** already exists.

**Failure scenario.** The implementer follows the repo convention and calls `writeArtifact(… kind:
'summaryMd' …)`. `putStaged` uploads the corrected body to a temp key; `exists` confirms it;
metadata is stamped `committed`; `promote` sees the final key already present, **deletes the temp
and returns**; metadata is stamped `promoted`. The user is charged, the route returns `applied`
with a fresh `tldr`/`takeaways` extracted from the corrected text, the envelope is deleted per §2 —
and the stored markdown is the **original, uncorrected document**. The card now describes a
document the reader cannot see.

**Why Blocking, and why this is a fold-in defect rather than a pre-existing one.** §0 line 30 tells
the reader this hazard is slice B's: *"**Blocked on #22**: `promote` is create-if-absent, so a
corrected body can be discarded while the row claims it."* Slice A writes the same body to the same
key through the same store. Attributing the hazard exclusively to B is an active misdirection
introduced by the split — a reader who checks §0 concludes slice A is unaffected.

§7's first falsifier (*"the stored blob holds corrected text, not the original"*) would catch it
**if** the fixture writes over a pre-existing blob, which it must, since a correction presupposes a
document. So this is caught at test time rather than in production — that is what keeps it from
being worse, not what makes it acceptable in a spec.

**Suggested fix.** State the write protocol explicitly in §2: the corrected body is written with
`blobStore.put` (upsert, `blob-store.ts:69`), **not** `writeArtifact`/`putStaged`→`promote`, and say
why in one line — the object exists by construction, so create-if-absent would discard the
correction. Amend §0's slice-B row to say the create-if-absent hazard is *avoided* in A by that
choice rather than *absent* from A. Add the ordering against the envelope delete (see M6).

---

## High

### H1 — deleting the model envelope breaks live share links and removes the over-budget stale fallback

**Where.** Spec §2's new requirement (lines 121-124). Code: `app/s/[token]/route.ts:102-103`,
`lib/html-doc/serve-doc.ts:147-151`.

The envelope at `MODEL_KEY(base)` is not a private owner cache. It is the **only** input the
anonymous share path can render from, and that path is a generate-free leaf by design
(`read-model.ts:7-10`):

```ts
// app/s/[token]/route.ts:102-103
const model = await readTitleStableModel({ blobStore: readOnly, principal, base, titles });
if (model.status !== 'ok') return notReady(); // absent / title-drifted / unparsable
```

It is also the fallback the owner path serves when the per-owner budget is exhausted:

```ts
// lib/html-doc/serve-doc.ts:147-151
case 'owner_over_budget': {
  // Spec D5: serve the title-stable stale rendering instead of failing; else 503.
  const staleRead = await readTitleStableModel({ blobStore, principal, base, titles });
  return staleRead.status === 'ok' ? { status: 'ok', model: staleRead.model, stale: true } : { status: 'over_budget' };
}
```

**Failure scenario.** An owner shares a summary; the link is live and rendering. They then apply a
one-word correction. Per §2 the route deletes the envelope. Every visitor to that share link now
gets `notReady()` — a working public URL becomes broken by a private edit — and it stays broken
until the *owner* happens to open the document and pays for a magazine regeneration. If the owner's
serve budget is exhausted when they do, `owner_over_budget` finds no envelope either and returns
`over_budget`/503 where it previously served the stale-but-readable page. **The delete removes the
degradation path as well as the cache.** Backlog #57's decision was explicitly to *tolerate skew and
serve the stale model*; §2 deletes the artifact that decision depends on.

**On the brief's sub-questions.** `MODEL_KEY(base)` does use the same `base` the correction path has
in hand — `base = mdKey.replace(/\.md$/, '')` from the persisted `video.summaryMd`
(`serve-summary-core.ts:71`) — so that part checks out ✅. A concurrent reader between the body write
and the envelope delete sees corrected prose with stale gists, which is the pre-existing bad state,
so the ordering is not itself harmful. A **failed** delete leaves exactly the permanent staleness the
requirement exists to prevent, and §2 does not say whether that fails the request (see M6).

**Suggested fix.** Do not delete. Two better options, both of which preserve the artifact:
1. **Overwrite the envelope's `sourceMdHash`/`sourceSections` invalidation marker** rather than the
   object — see H2, which shows the envelope already carries a content hash that `isFresh` ignores.
2. If the envelope genuinely must go, state the two consequences above as accepted, and say what the
   share path serves in the interim. Given backlog #57 decided the opposite way for a *weaker*
   version of the same trade, that acceptance needs the user, not a reviewer.

### H2 — "there is no content hash" is true of `isFresh`, not of the envelope

**Where.** Spec §2 lines 113-119. Code: `lib/html-doc/model-store.ts:22-23`,
`lib/html-doc/serve-doc.ts:181`, `lib/html-doc/read-model.ts:54-56`.

The spec states, as the fact that forces the delete:

> Magazine freshness is `sameTitles && generatorVersion` — **there is no content hash**
> (`read-model.ts:12-25`).

The citation is correct for `isFresh`. But the envelope carries a body hash and always has:

```ts
// lib/html-doc/model-store.ts:22-23
// Stage 3 (§4.2): MD-body-only digest of the MD this model was generated from.
sourceMdHash: z.string().optional(),
```

written on every fresh materialize at `serve-doc.ts:181` (`sourceMdHash: mdHash(mdBody)`) and at
`generate.ts:59`, and already used as a staleness oracle by the sync companion path
(`lib/cloud-sync/companion.ts:106-108, 152`). `read-model.ts:54-56` records, in the code, exactly
why it is not in `isFresh`:

> *Deliberately NOT added to `isFresh`: that governs the OWNER path, where refusing an envelope
> triggers a reserve-and-charge regeneration. Making a money path stricter is its own slice with its
> own review.*

**Why this matters.** §2's delete has the *same* cost as the change that comment declines to make —
the next owner serve reserves and regenerates, ~6¢ per `serve-doc.ts`'s own measurement — while
additionally destroying the share path (H1) and the over-budget fallback. The spec chose the
strictly worse of two options because its premise made the better one invisible, and it did so
without the money-path review that comment says the better one would need. The correction's stated
cost (§1, ≈0.6¢) does not mention the deferred magazine regeneration at all, and §7's ledger
falsifier (*"moves by the actual spend, after the call"*) will not see it, because it lands on a
later request.

**Suggested fix.** Correct the sentence to *"`isFresh` ignores the envelope's `sourceMdHash`
(`model-store.ts:23`) — the hash exists, the freshness predicate does not consult it."* Then state
the option set honestly: (a) delete (H1's costs), (b) add `sourceMdHash` to `isFresh` — which fixes
the whole class, not just corrections, and is the change `read-model.ts:54-56` scopes to its own
slice, (c) regenerate-in-place. And record in §5 that whichever is chosen, a correction implies a
deferred magazine charge on the next serve.

### H3 — `withCaps` is a no-op without a `CloudGeminiCaps`, and §5.1 supplies a constant instead

**Where.** Spec §5.1 lines 207-211. Code: `lib/gemini.ts:36-47`.

```ts
// lib/gemini.ts:36-47
function withCaps(base: GenerationConfig, caps: CloudGeminiCaps | undefined, maxOutputTokens: number): GenerationConfig {
  if (!caps) return base;
  return { ...base, maxOutputTokens, thinkingConfig: { thinkingBudget: 0 } } as GenerationConfig;
}
```

The cap value is the third argument, but **whether any cap is applied at all** is decided by the
second. Every existing call site passes `caps?.<field> ?? 0` and gets its caps object from a
module-level `CloudGeminiCaps` (`lib/job-queue/summary-handler.ts:36`,
`lib/job-queue/dig-handler.ts:29-33`, `lib/html-doc/serve-doc.ts:30`). §5.1 says only:

> `fixSummary` gains `maxOutputTokens = MAX_SUMMARY_OUTPUT_TOKENS` (8192, `gemini-cost.ts:16`),
> `thinkingBudget: 0` and `signal`, **applied through `withCaps`**

— naming the constant and never naming a caps object or where the correction path gets one.

**Failure scenario.** The implementer writes
`withCaps({ … }, opts?.caps, MAX_SUMMARY_OUTPUT_TOKENS)`; nothing constructs `opts.caps` for this
route because the spec never asked for one; `withCaps` returns the base config **unchanged**;
`fixSummary` runs uncapped with thinking enabled. §7's falsifier *"A run is bounded — `maxOutputTokens`
and `thinkingBudget` present"* fails, and the money bound §5.1 exists to establish does not exist.
It also fails silently in the other direction: a reviewer reading the diff sees `withCaps` and
`MAX_SUMMARY_OUTPUT_TOKENS` and both look right.

**Suggested fix.** §5.1 should name the caps object, not the constant: the correction path
constructs (or imports) a `CloudGeminiCaps` with `summaryOutputTokens: MAX_SUMMARY_OUTPUT_TOKENS`
and passes it as `withCaps`'s second argument, matching `serve-doc.ts:30`'s `SERVE_CAPS` shape. Also
state that on the **local** branch `caps` is absent by design, so §7's bounded-run falsifier is a
cloud-only assertion — otherwise it reads as failing on local.

### H4 — the cap's justification does not hold for any document the local pipeline generated

**Where.** Spec §5.1 lines 213-217.

> The cap comes from the enforced summary output cap: a corrected document cannot need more output
> than a generated one.
>
> ⚠ **Preflight before the first call.** … Check the input against the cap first and fail before paying.

`MAX_SUMMARY_OUTPUT_TOKENS` bounds `generateSummary` **only when a caps object is present**
(`gemini.ts:326-330`, and `withCaps`'s `if (!caps) return base`). The local pipeline passes none —
that is `withCaps`'s documented purpose (`gemini.ts:31-33`: *"When `caps` is absent (the local
pipeline) the base object is returned UNCHANGED"*). Cloud-side, the cap bounds the **JSON response**
(summary + ratings + videoType + audience + tags), whereas `fixSummary` must emit the **assembled
markdown document** — H1, frontmatter and the rendered `▶` timestamp lines that the pipeline adds
after generation, none of which were inside the 8192 the generator was held to.

**Failure scenario.** A user generates summaries locally (uncapped), syncs the playlist to the
cloud — the whole point of Stage 3 — and presses apply on one. The §5.1 preflight measures the
document against 8192 output tokens, it exceeds, and the route fails before any call. Corrections
are permanently impossible on that document, and the spec states no behaviour for the case: no error
code, no message, no falsifier. §7's bounded-run row asserts *"over-cap input rejected before any
call"*, which passes — the feature is refused rather than broken, so the falsifier reads green on a
document the user cannot ever correct.

**Suggested fix.** Either (a) derive the correction's output cap from the *document*, not from the
summary generator's cap — e.g. `countTokens(document) × a stated margin`, clamped — or (b) keep 8192
and state the refusal explicitly: which status code, what the panel shows, and a §7 row asserting
that a legacy/local-origin over-cap document produces that response rather than a 500. Either way,
delete the sentence *"a corrected document cannot need more output than a generated one"* — it is
false for the local path and unproven for the cloud one.

### H5 — a bare press stamps corrections-currency the document does not have, and **extinguishes the only signal that would ever have applied them**

**CONFIRMED — the coordinator's reading of `route.ts:77-79`/`:88` is correct.** I reached it
independently from the code and then extended it: the consequence is not a wrong timestamp, it is
**silent, permanent loss of a pending correction**, and §7's *new* row is satisfied by it.

**Where.** Spec §3 line 152 (*"Exactly today's guard at `route.ts:63`"*), §4's table row
(*"`mdCorrectionsHash` | per the `:77-79` rule"*, line 169), §7's needsRegen row (line 274). Code:
`app/api/videos/[id]/regenerate/route.ts:54-59, 63, 77-79, 88`; `lib/cloud-sync/sync-run.ts:337-361`;
`lib/cloud-sync/reconcile-class-a.ts:8`.

**The mechanism, quoted.** On a bare press `trimmedCorrections` is falsy and `corrections !== ''`,
so both the apply guard and the stamp fall to their third branch — and they fall to *different*
values:

```ts
// route.ts:63 — nothing is applied
const fixed = trimmedCorrections ? await fixSummary(stripped, trimmedCorrections) : stripped;

// route.ts:77-79 — but the stamp resolves to the STORED corrections
const effectiveCorrections = trimmedCorrections
  ? trimmedCorrections
  : corrections === '' ? '' : (video.corrections ?? '');

// route.ts:88 — and is written as if the document reflected them
mdCorrectionsHash: mdHash(effectiveCorrections),
```

The route's own comment (`:71-79`) defends this: *"a bare regenerate keeps prior corrections baked
in, so stamping `mdHash('')` there would wrongly mark a still-corrected MD as stale."* That reasoning
holds **only if the stored corrections are the ones the MD was last corrected with.** The comment
assumes that invariant; nothing establishes it.

**The producer that breaks the invariant is the sync path — the same feature this slice serves.**
I enumerated every writer of `corrections`:

| Writer | Regenerates the MD? | Touches `mdCorrectionsHash`? |
|---|---|---|
| `regenerate/route.ts:56,58` | yes (when non-empty) | yes, `:88` |
| **`lib/cloud-sync/sync-run.ts:358`** — Class-B reconciliation | **no** | **no** |
| `videos/[id]/review/route.ts:147` | — | — (**not** a corrections writer: `validateBody:16-18` accepts `personalScore`/`personalNote` only, and `serveCloud:135-145` builds `set`/`clear` from those two alone) |

`sync-run.ts:337-361` loops `FIELDS` — which includes `corrections` — and writes the winning value
to the losing side via `updateVideoAnnotations(…, { editedAt: m.editedAt })`, with no MD work of any
kind. That is by design: leaving the body stale is exactly why `reconcileClassA` computes
`needsRegen` at all.

**Failure scenario, end to end.**

1. The user edits corrections `C1 → C2` on their laptop. Nothing regenerates; the MD still reflects
   `C1`; `mdCorrectionsHash = mdHash(C1)`.
2. Sync runs. `sync-run.ts:358` writes `C2` to the cloud row. `mdCorrectionsHash` is untouched.
3. `reconcileClassA` (`:8`, `current(s, cur) => s.mdCorrectionsHash === cur`) sees
   `mdHash(C1) ≠ mdHash(C2)` → **`needsRegen: true`.** Correct: the document owes the user a
   correction.
4. A bare press arrives. Two ways, and the second is not a slip: the panel sends the raw textarea
   value, so selecting-all and typing a space yields `"  "` (`trimmedCorrections = ''`, falsy;
   `corrections !== ''`); and §5.3 already concedes the route is reachable by any authenticated
   client, where a plain `POST {outputFolder}` omits `corrections` entirely (`typeof !== 'string'`
   → `undefined`). Either way `:79` resolves `effectiveCorrections = C2`, `:63` applies **nothing**,
   and `:88` writes `mdCorrectionsHash = mdHash(C2)`.
5. `reconcileClassA` now returns **`needsRegen: false`**. Nothing anywhere re-derives currency from
   the body, so the flag never comes back. **`C2` is gone** — the user's correction was recorded,
   the system knew it was owed, and one press that did no work discarded the debt.

**Why the §7 fix does not catch it — and this is the part that makes it round-4 material.** The row
added by the r3-H6 split reads:

> `A correction makes the row current | the sync decision | reconcileClassA's needsRegen goes
> **true → false** for that video. **Fails if the stamp is missing**`

Step 5 produces *exactly that transition*. The falsifier tests only the direction where the stamp is
**absent**; it cannot distinguish a correction that was applied from a press that applied nothing and
stamped anyway. The r3-H6 fix removed a row that a correct implementation failed and replaced it with
a row that the defect **passes**. §7's second row does not cover it either — Codex is right that it
omits `mdCorrectionsHash` (see M4), but omitting the field is what makes it *consistent* with §4's
allowance, not what makes it safe.

**Why High rather than Blocking.** Honest accounting: the `:77-79` rule is **pre-existing**, it is
reachable on the local backend today, and the fold-in did not introduce it. What the fold-in did is
re-affirm it three times (§3's *"Exactly today's guard"*, §4's *"per the `:77-79` rule"*, §7's new
row) so that it now reads as a reviewed decision rather than unexamined inheritance. And slice A is
what makes it **cloud-reachable**: `VideoMenu.tsx:181` gates the panel out of cloud mode today and
the route 500s there (`route.ts:36`), so the sync-produced pending correction of step 2 currently has
no cloud press that can extinguish it. Slice A supplies that press. If the coordinator prefers to
weigh "slice A converts a dormant local edge case into a live data-loss path on the money side of
the cloud" over "pre-existing", Blocking is defensible and I would not argue.

**Suggested fix.** The two branches at `:63` and `:77-79` must not disagree. Either:

- **(a) Stamp only what you applied.** `mdCorrectionsHash` moves *only* when `fixSummary` ran; a bare
  press leaves it untouched. The comment's fear — that stamping `mdHash('')` marks a still-corrected
  MD stale — is answered by not stamping at all rather than by stamping the stored value. This is
  also the only option consistent with §4's `mdGeneratedAt` row (*"must not move — the body did not
  change"*): the same argument applies verbatim to `mdCorrectionsHash`.
- **(b) Make a bare press with stale stored corrections apply them**, i.e. treat
  `video.corrections` as the apply input when the request omits the field. That is a behaviour
  change with a cost (it makes a bare press paid) and it collides with §1.2's descoping; (a) is the
  smaller and safer change.

Then add the §7 row that the current pair cannot express: **a bare press on a video whose
`needsRegen` is `true` leaves it `true`.** That is the observation that fails today, and neither
existing row makes it.

---

## Medium

### M1 — `maxDuration = 420` is inert on this deployment, and the precedent cited as reassurance is inert for the same reason

**Where.** Spec §5.4 lines 248-250. Code: `fly.toml`, `next.config.ts:11`,
`node_modules/next/dist/docs/01-app/03-api-reference/03-file-conventions/02-route-segment-config/maxDuration.md:6`.

The Next docs are explicit that this is an *output annotation*, not an enforcement:

> `maxDuration.md:6` — *"Deployment platforms **can** use `maxDuration` from the Next.js build output
> to add specific execution limits."* … `index.md:13` lists its default as *"Set by deployment
> platform."*

This app deploys as `output: 'standalone'` (`next.config.ts:11`) running `node server.js` under Fly
(`fly.toml` `[processes] web = "node server.js"`). No adapter consumes the build output, so nothing
reads the value. §5.4's reassurance — *"It is well inside the 1800 s this repo already uses on a
route (`app/api/quick-view/backfill/route.ts:10`)"* — cites a value that is inert for the identical
reason, so it is evidence that the repo has *written* 1800 somewhere, not that a long request
survives in production.

**NOT VERIFIED:** what actually bounds the request in prod (Fly proxy/idle timeouts, any client
`fetch` timeout). I cannot measure the deployed app.

**Suggested fix.** Keep the `export const maxDuration = 420` — it is correct-by-portability and free
— but relabel §5.4: the derivation bounds *the work*, not *the request*, and on Fly nothing enforces
it. Name what does, or file the measurement as an open item. Drop the 1800 s precedent sentence.

### M2 — §5.1's preflight is not in §5.4's budget, and it consumes the stated slack

**Where.** Spec §5.1 lines 215-217 vs §5.4's table, lines 242-248.

I recomputed the table and it is right: `3 × 60 s + 400 ms + 800 ms = 181.2 s` per phase, `× 2 =
362.4 s`, leaving 57.6 s. Every input is correctly cited (`gemini.ts:473`, `:105`, `:505`;
`gemini-cost.ts:22`; `gemini.ts:281`).

What the table omits is the preflight §5.1 requires in the same commit. The repo's only precedent
for it is a `countTokens` **network round trip** — `assertMagazineInputWithinCap`
(`gemini.ts:77-101`) forwards `timeout: opts.timeoutMs`, i.e. the same 60 s budget. Add one and the
worst case is **422.4 s > 420 s**; add one with no timeout at all and the bound is open-ended. The
two sections were written in one pass and do not know about each other.

**Suggested fix.** Add a preflight row to §5.4's table with its own timeout, and re-derive. State the
preflight's timeout explicitly rather than inheriting `REQUEST_TIMEOUT_MS` by accident.

### M3 — `fixSummary` needs the signal in **three** places, not two

**Where.** Spec §2 lines 94-98 ("Two places take it, not one").

Both cited sites are correct: `gemini.ts:496` passes no `signal` where `:273` does, and `:505` is a
bare `new Promise(setTimeout)` where `:281` uses `abortableSleep`. ✅

The third is the loop guard. `generateJson` re-checks abort at the top of every iteration:

```ts
// lib/gemini.ts:271-273
for (let attempt = 0; attempt <= retries; attempt++) {
  if (opts?.signal?.aborted) throw new DOMException('aborted', 'AbortError');
  try {
    const result = await model.generateContent(prompt, { timeout: timeoutMs, signal: opts?.signal });
```

`fixSummary` does not:

```ts
// lib/gemini.ts:494-496
for (let attempt = 0; attempt <= retries; attempt++) {
  try {
    const result = await model.generateContent(prompt, { timeout: REQUEST_TIMEOUT_MS });
```

**Failure scenario.** A signal that aborts *between* attempt 1's failure and attempt 2's dispatch —
during the backoff, which §2 is fixing precisely because it is a real window — is not observed until
the next `generateContent` rejects. With `abortableSleep` wired but no loop guard, an abort during
the sleep resolves the sleep and the loop then issues **another paid call** before noticing. The fix
for the second site makes the third site's absence newly reachable.

**Suggested fix.** §2: *"**Three** places take it: the `generateContent` call (`:496`), the backoff
sleep (`:505`), and the per-attempt abort guard the loop lacks entirely (`:494-495`, cf.
`generateJson:271`)."*

### M4 — §7's "nothing moves on a bare press" list is incomplete

**Where.** Spec §7 line 275. Code: `lib/cloud-sync/backfill.ts:6-17`.

**First, the good half — the brief's question 3.** The `needsRegen` row *is* falsifiable and *not*
vacuous. `reconcile-class-a.ts:8` makes `mdCorrectionsHash` the sole currency input, and the true
state is reachable two ways without a contrived fixture: the one-sided branch
(`:22-23`, `needsRegen: !current(cloud, cur)` — a cloud-only video whose stored corrections were
edited but never applied) and the two-sided branch (`:38-39`, `cCur && !lCur → copyToLocal,
needsRegen: false` after the correction, versus the recency tiebreak at `:48-49` returning
`needsRegen: bothStale = true` before it). The split fixed r3 H6 correctly. ✅

But the first row has a blind spot the split created, which **H5** covers in full: the `true → false`
transition it asserts as success is also produced by a bare press that applies nothing. Read H5
before acting on this row.

The second row does not fare as well. `ClassASignals` has six fields
(`backfill.ts:8-16`): `summaryMdKey`, `mdHash`, `docVersionMajor`, `mdGeneratedAt`,
`mdCorrectionsHash`, `backfilled`. The row asserts four of them. `mdCorrectionsHash` is deliberately
excluded because §4 lets it move — fine, but then the row's title ("disturbs nothing") overclaims
and should say which field is allowed to move and under what rule. `summaryMdKey` is simply missing.

And nothing in §7 asserts `updatedAt`, which is the field B1 shows a bare press *always* moves and
which `deriveHumanSnapshot` (`backfill.ts:21`) reads. **The falsifier is green while the defect
stands** — the exact failure mode this repo has documented repeatedly.

**Suggested fix.** Complete the list to all six `ClassASignals` fields, mark `mdCorrectionsHash` as
"moves only per the `:77-79` rule; assert the rule, not immobility", and add a separate row for the
Class-B side: what `deriveHumanSnapshot` returns before and after a bare press, for a field with no
`annotationsEditedAt` entry. That row is the one that fails today.

### M5 — the length cap's two halves are not independent, and the spec defers the coupling

**Where.** Spec §2 lines 135-140. Code: `components/CorrectionsPanel.tsx:105`,
`lib/cloud-sync/sync-run.ts:358`, `app/api/videos/[id]/review/route.ts:147`.

The cap itself is well-motivated and the citations are right (`maxLength={1000}` at
`CorrectionsPanel.tsx:105`; `route.ts:24-26` checks only the type). The spec then says: *"The sync
path writes this field too, so the plan states whether the cap applies there or only at this route."*

That framing presents the two as independent choices. They are not. `sync-run.ts:358` and the review
route (`:147`) both write `corrections` through `updateVideoAnnotations` with no length check, and
the local index has no cap at all — so a >1,000-char value **can already exist**, and can arrive from
a local replica after the cap ships. For such a row the panel loads the stored text and any apply
press submits it verbatim: the user gets a 400 they cannot clear except by shortening text they may
not have written. Cap-at-route-only therefore creates a state where the attended path is permanently
refused while the *unattended* path (slice B) would hand the same value to Gemini uncapped.

**Suggested fix.** State the decision in the spec rather than the plan, because it is a
product-visible behaviour: either (a) the cap applies to the incoming request only, and §2 says what
the user sees for an already-long row and how they escape it, or (b) the cap is enforced at the
`updateVideoAnnotations` seam so no path can create one. Add a §7 row for the already-long row —
it is the case a route-level test will not generate by itself.

### M6 — the envelope delete has no failure semantics, and no stated ordering against the body write

**Where.** Spec §2 lines 121-124.

The requirement says *"After a successful correction the caller deletes the model envelope"* and
stops. Three things are unstated, all of which the implementer must decide and all of which are
observable:

1. **Ordering** — body write then delete, or delete then body write. (Body-first is right: a reader
   between the two sees corrected prose with stale gists, which is the pre-existing state; the
   reverse serves original prose with no model, i.e. a regression for a window.)
2. **Failure** — the delete happens *after* the paid call. If it throws, does the route 500 (losing
   the user's successful correction from the response, though not from storage) or log and return
   `applied` (leaving the permanent staleness the requirement exists to prevent)?
3. **Idempotence** — `BlobStore.delete` on an absent key: `deletePrefix` is documented as
   best-effort/idempotent (`blob-store.ts:74-76`) but `delete` (`:71`) carries no such note.

**Suggested fix.** Specify body-first, log-and-continue on delete failure with the key named, and
confirm `delete`'s absent-key behaviour on both adapters (or require the caller to tolerate a throw).
If H1 changes the mechanism away from delete, these questions transfer to whatever replaces it.

---

## Low

- **L1 — §4.1 promotes a surface its own code says is not on the local runtime path.**
  `local-metadata-store.ts:115-117` documents `updateVideoAnnotations` as *"Interface-shape parity
  only — not on a local runtime path (the local review route branch is unchanged and still calls
  `updateVideoFields` directly)"*, and `:58-59` says `updateVideoFields` is *"the PRODUCTION Class-B
  write path (review + regenerate routes call this…)"*. §4.1's switch makes the local
  `updateVideoAnnotations` production code for the first time. Behaviourally the two agree on
  stamping (`:75-86` vs `:139-159`), so this is low — but they differ on a missing video:
  `updateVideoAnnotations` returns `{ found: false }` while `updateVideoFields` throws `Video not
  found in index`. §7's *"Local is unchanged — 18 tests, 2 suites — all pass unmodified"* assumes the
  local path is untouched; §4.1 touches it. Say which, and note the error-shape change.

- **L2 — "issue no call at all" also skips the `{ found }` check.** §4.1 line 198 requires no call
  when the value is unchanged; §4.1 line 185 notes the route 404s on `found: false`. In the no-op
  case there is no RPC and so no ownership re-check — harmless here (the route already read the row
  at `route.ts:37-42`) but worth one clause, because the 404 reads as unconditional.

- **L3 — the cap's unit is unstated.** §2 says *"The cap is the client's 1,000"*. `maxLength={1000}`
  on a `<textarea>` counts **UTF-16 code units**, so a Korean or emoji-bearing correction that the
  browser accepts can be rejected server-side by a `Buffer.byteLength` check, or vice versa. Also
  unstated: trimmed or raw. Given backlog #36's history with non-ASCII, say `[...s].length` or
  `s.length` explicitly, and say whether the check runs before or after `.trim()`.

- **L4 — read-before-write is TOCTOU against the sync path.** §4.1 line 196-198 requires reading the
  stored value and skipping the write when equal. `sync-run.ts:358` writes the same field with an
  explicit `p_edited_at`. A sync landing between the route's `readIndex` (`route.ts:37`) and its
  write can be silently overwritten with a `now()` stamp, or skipped when it should not be. The
  window is small and the consequence is a stamp, not data — but §4.1 presents read-before-write as
  *sufficient*, and it is sufficient only in the absence of a concurrent writer. One sentence naming
  the residual is enough.

---

## Citation audit — the other direction

The brief asks whether the fold-in introduced *new* citation errors. **It did not.** Every reference
in the changed sections that I checked resolves to what the spec says it does:

`0021:19-56` (function bounds) ✅ · `0021:35` (set-stamp) ✅ · `0021:41-43` (clear-stamp) ✅ ·
`0021:89` ✅ · `0021:149` ✅ · `read-model.ts:12-25` ✅ · `model-store.ts:32` (`MODEL_KEY`) ✅ ·
`blob-store.ts:71` (`delete`) ✅ · `metadata-store.ts:73` ✅ · `local-metadata-store.ts:125` ✅ ·
`local-metadata-store.ts:139-159` ✅ · `supabase-metadata-store.ts:269` ✅ ·
`reconcile-class-a.ts:8` ✅ · `backfill.ts:13` ✅ · `backfill.ts:22` ✅ (r3's L4 drift is fixed) ·
`gemini.ts:36` ✅ · `:105` ✅ · `:273` ✅ · `:281` ✅ · `:326` ✅ · `:391-403` with the call at `:401` ✅ ·
`:433` ✅ · `:473` ✅ · `:480` ✅ · `:496` ✅ · `:505` ✅ · `:536` ✅ · `:686` ✅ ·
`gemini-cost.ts:16` ✅ · `:22` ✅ · `:33,35` ✅ · `CorrectionsPanel.tsx:52` ✅ · `:105` ✅ ·
`VideoMenu.tsx:52` ✅ · `:181` (the gate) ✅ · `:188` (the label) ✅ ·
`route.ts:20-21, 24-26, 30, 36, 50, 58, 63, 66, 69, 77-79` ✅ ·
`quick-view/backfill/route.ts:10` ✅ · `dig-blob-key.ts:22` ✅ ·
`summary-handler-promote-divergence.test.ts:148` ✅.

The two errors in this round are not line drift. They are **scope** errors: a citation that is
correct about the object it names and silent about the layer that overrides it (B1's trigger under
`0021`), and one that is correct about the predicate it names and silent about the record the
predicate ignores (H2's `sourceMdHash` under `isFresh`). Line-checking would never have caught
either; both needed the question *"what else touches this?"*

## Coherence after surgery

Checked; three things to fix, all already filed above rather than duplicated here:

- §4.1's heading — *"Both unknowns are one surface, and it already exists"* — is now half true. The
  clear-surface unknown is genuinely settled; the `updated_at` unknown is not (**B1**). The heading
  and §8's bullet both need to stop asserting the second.
- §0's slice-B row and §2's cloud-branch paragraph disagree about who owns the create-if-absent
  hazard (**B2**).
- §1 (typical cost ≈0.6¢), §5 (post-hoc recording of *actual* spend) and §2's new envelope delete
  are three sections written to three different cost models — the delete's deferred magazine charge
  appears in none of them (**H2**).

No renumbered-section cross-references are broken; §1.1/§1.2/§4.1/§5.1–§5.4 all resolve. No claim
survives from v3 into an unsupported context that I could find beyond the three above.

## What slice A still does not cover (bounded to A)

Not defects — gaps a plan should decide, listed so they are not mistaken for oversights:

1. **The corrected-body read.** §2 replaces `fs.promises.readFile` (`route.ts:50`) implicitly. The
   cloud read must be the *proving* read — `serve-summary-core.ts:66-67` bails at `409 repair
   needed` rather than treating an unreadable MD as absent, and the same discipline applies here:
   a failed blob read must not become "empty document, correct it anyway".
2. **`summaryHtml` cache invalidation in cloud.** `route.ts:86` writes `summaryHtml: null`; §2 does
   not say whether the cloud branch does the same, or whether any rendered-HTML blob needs removing
   alongside the model envelope.
3. **What the panel shows for each of the new failure classes** — structural-validation throw,
   over-cap preflight refusal (H4), 400 over-length (M5), abort. §6's discriminator covers
   `applied`/`no-corrections` only.

## Honest assessment, as the brief asks

Slice A is **close**, and most of round 3's residue was folded in correctly — the `signal` analysis,
the falsifier split, the `maxDuration` arithmetic and all forty-odd citations are right. The
remaining Mediums and Lows genuinely belong in the plan.

But B1, B2 and H5 are not plan-level. B1 makes §8's central conclusion ("no migration of any kind")
unsupported, and resolving it is a decision about sync semantics that the plan is not authorised to
make. B2 leaves the one write that can silently discard a paid result unspecified, in a document
that tells the reader that hazard lives in another slice. H1 changes the behaviour of a *public*
URL — a share link the owner already handed out — which is user-visible and reverses backlog #57's
recorded decision. **H5 is a silent data-loss path that slice A makes cloud-reachable, and §7's new
row is satisfied by it.**

Those five need the spec, not the plan.

**One pattern worth naming, because it accounts for four of the seven Blocking/High.** B1, H2, H5 and
M4 are all the same error at different scales: a claim measured against **one artifact** and
generalised to the **behaviour**. The function body versus the trigger under it. The freshness
predicate versus the record it reads. The apply branch versus the stamp branch three lines below,
which look at the same condition and resolve it differently. The falsifier that asserts a state
transition without asserting what caused it. Line-checking found none of these — every citation in
the document is correct. What finds them is asking, of each measured fact, *"what else participates
in this outcome?"*

NOT CONVERGED
