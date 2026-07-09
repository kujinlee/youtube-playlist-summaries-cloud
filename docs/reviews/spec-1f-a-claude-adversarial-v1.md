# Adversarial Review — Stage 1F-a (Authorized, Blob-Backed Summary-HTML Serving)

**Reviewer:** Claude (adversarial mandate)
**Spec under review:** `docs/superpowers/specs/2026-07-09-stage-1f-a-authorized-doc-serving-design.md`
**Date:** 2026-07-09
**Method:** Read spec + `CONTEXT.md` + the touched/depended code (`summary-handler.ts`, `generate.ts`,
`render.ts`, `rerender.ts`, `resolve.ts`, `blob-store.ts`, `supabase-blob-store.ts`,
`supabase-metadata-store.ts`, `worker-persistence.ts`, `gemini.ts` (`generateMagazineModel`,
`generateJson`, `generateSummary`), `gemini-cost.ts`, `cap-soundness.test.ts`, `theme.ts`, `nav.ts`,
`app/api/html/[id]/route.ts`).

Each finding is tagged **INTENT/DESIGN** (needs a human product decision) or **CORRECTNESS** (a fix that
does not change intent).

---

## BLOCKING

### B-1 — `generateMagazineModel` cannot honor caps today; the magazine pass is an *unbounded* paid call → spend bound is not provable — CORRECTNESS
**Where:** spec §4.1 step 2, B2 ("`maxOutputTokens` set, `thinkingBudget:0`, `countTokens` preflight — same as other cloud calls"); code `lib/gemini.ts:464-505`.

The spec assumes the worker can call `generateMagazineModel(...)` "under `CLOUD_CAPS`" with the same
discipline as `generateSummary`/`transcribeViaGemini`. The actual function signature is:

```ts
export async function generateMagazineModel(
  sections: Array<{ title: string; prose: string }>,
  language: 'en' | 'ko',
): Promise<MagazineModel>
```

It takes **no `caps`, no `opts`, no `signal`**. Its `generationConfig` (line 471) sets **no
`maxOutputTokens` and no `thinkingConfig.thinkingBudget`**, and it calls `generateJson(model, prompt,
MagazineModelSchema, 'magazine')` **without `opts`**, so it also cannot honor an abort signal. The
response schema (`MAGAZINE_RESPONSE_SCHEMA`) has **no `maxItems` on `sections`** — output length is not
structurally bounded either.

Consequences:
1. **No enforced `maxOutputTokens` ⇒ the magazine output is unbounded**, so the worst-case cost of this
   pass is unbounded. That directly breaks Stage 1D's crown-jewel invariant — a *provable* spend bound
   (`summary_est_cents >= ceil(worst) * attempts`). §4.2 / B4 / Success-Criterion 2 all assert the bound
   "stays provable"; it cannot, because the recompute would be bounding a call that enforces no cap.
2. **The claimed `countTokens` input preflight does not exist for magazine.** `CloudGeminiCaps` has only
   `transcribeInputTokens/transcribeOutputTokens/transcriptInputBytes/summaryOutputTokens`
   (`gemini-cost.ts:36-41`); there is no magazine field and no `assertMagazineInputWithinCap`. §4.1's
   "same … `countTokens` preflight discipline" is aspirational, not implementable as written.
3. **No `signal` threading ⇒ a lease-lost/SIGTERM mid-magazine cannot be aborted**, widening the stale-write /
   double-charge window the worker comment at `summary-handler.ts:168-170` already flags.

**This is a load-bearing, unstated code change.** The spec presents the money-path work as "add a pass +
re-price," but honoring `CLOUD_CAPS` requires modifying `generateMagazineModel`'s signature and body
(add `caps`/`signal`, set `maxOutputTokens`, add a `maxItems` bound or an input `countTokens` preflight,
thread `opts` into `generateJson`). Until that exists, B2 is untestable and the bound is unprovable.

**Fix:** State explicitly that `generateMagazineModel` gains `opts?: { signal?; caps? }`, sets
`maxOutputTokens` via `withCaps(...)`, threads `opts` into `generateJson`, and either caps output tokens
*and* preflights input tokens or documents why input is transitively bounded (see B-2). Add a
`MAGAZINE_OUTPUT_TOKENS` cap to `CloudGeminiCaps` + `CLOUD_CAPS`.

### B-2 — Cap-soundness recompute as scoped in §4.2 undercounts the magazine pass (input tokens omitted; input bound undefined) — CORRECTNESS
**Where:** spec §4.2 ("a pass-count constant **and an output token cap**"), B4; `tests/integration/cap-soundness.test.ts:16-21`; `gemini-cost.ts:49-69`.

Every other pass in `perRunWorstCents` prices **input + output** (transcribe: audio+video+overhead in,
output out; summary/quickview: transcript-bytes+overhead in, output out). §4.2 describes the magazine
pass as only "a pass-count constant and an output token cap" — it names **no input-token contribution**.
The magazine *input* is the full parsed summary MD (all sections' prose) plus prompt/schema overhead. If
the recompute (and the inline recompute at `cap-soundness.test.ts:16-19`) adds only output cost, the bound
is undercounted and therefore **not sound** — exactly the failure the drift-proof test exists to catch.

Additionally the input is only *bounded* if something bounds it. The summary MD is transitively bounded by
`MAX_SUMMARY_OUTPUT_TOKENS` (8192) — but the spec never states that reasoning, and there is no enforced
magazine-input cap. A future change that lets the MD grow (or a magazine that also ingests titles/TL;DR)
silently invalidates the bound.

Pass count is also unstated: `generateMagazineModel` → `generateJson` with default `retries =
GENERATE_JSON_RETRIES (2)` ⇒ **3 passes** (mirrors `QUICKVIEW_MAX_PASSES`). The spec should pin
`MAGAZINE_MAX_PASSES = GENERATE_JSON_RETRIES + 1` so the constant can't drift from the retry loop, exactly
as the existing constants do.

**Fix:** In §4.2, price magazine as `MAGAZINE_MAX_PASSES × (input_cents + output_cents)` where
`input_cents` uses an explicit `MAGAZINE_INPUT_*` bound (or the documented `MAX_SUMMARY_OUTPUT_TOKENS +
overhead` transitive bound) and `output_cents` uses the new output cap. Extend both `perRunWorstCents`
**and** the inline recompute in `cap-soundness.test.ts`.

### B-3 — Nonce CSP cannot authorize the inline `onclick` print button; strict-CSP and byte-identical-local are mutually unsatisfiable for it — INTENT/DESIGN + CORRECTNESS
**Where:** spec §4.4, D7, B10, B15, §8 ("no `'unsafe-inline'` fallback slipping in"); code `theme.ts:88-89`, emitted unconditionally at `render.ts:114`.

`renderMagazineHtml` always emits:
```ts
export const PRINT_BUTTON =
  `<button id="print-btn" type="button" onclick="window.print()" ...>🖨️</button>`;
```
A **nonce-based** `script-src` does **not** cover inline **event-handler attributes** (`onclick=`). Under
CSP Level 3, the presence of a nonce also causes `'unsafe-inline'` to be ignored, so an `onclick` handler
is blocked outright unless you add `'unsafe-hashes'` (or `'unsafe-inline'`, which the spec forbids in §8).
Therefore:

- The print button **breaks** under the intended CSP. B15's "theme/nav scripts still execute under the
  CSP" is false for the print button, and D7's "stays valid as the inline theme/nav scripts evolve"
  overlooks that this is an inline *attribute*, not a nonce-able `<script>`.
- Fixing it properly (convert to `addEventListener` in the nonce'd `THEME_TOGGLE_SCRIPT`) **changes the
  local static output**, which violates the hard byte-identical requirement (§4.4, B14).

So the two hard requirements collide on this one element: you cannot have *both* a strict nonce CSP *and*
byte-identical local output without either (a) weakening the CSP (`'unsafe-hashes' 'sha256-…window.print()…'`
or `'unsafe-inline'`), or (b) diverging cloud vs. local markup for the print button.

**Fix (needs a decision):** Choose one — (a) refactor `PRINT_BUTTON` to a nonce'd `addEventListener`
handler and **accept that "byte-identical" now means the post-refactor local baseline** (re-baseline the
snapshot; local also loses the inline handler but keeps working); or (b) keep the inline handler and add a
single `'unsafe-hashes' 'sha256-<hash of window.print()>'` to `script-src`, explicitly documented as the
one allowed exception (still no blanket `'unsafe-inline'`). Option (a) is cleaner and keeps §8's promise.
Whichever is chosen, add an explicit behavior row: "print button works under CSP."

---

## HIGH

### H-1 — "Repair needed" is a dead-end state: nothing in the spec can ever repair a missing model, and every pre-1F-a promoted summary becomes permanently repair-needed — INTENT/DESIGN
**Where:** spec §4.1 (idempotency skip), D8, B9b, B3; glossary "Repair needed"/"Magazine model"; code `summary-handler.ts:84-92`.

The idempotency skip returns **at the top of the handler** when `summaryMd.status === 'promoted'` at the
current version — *before* `reserveVideoSlot` and long before the new magazine step. D8 forbids serve-path
regeneration. So a model that is missing behind a *promoted* summary can be repaired by **no path the spec
defines**: the serve won't regenerate (D8), and the worker's skip short-circuits before it would. B9b
"surfaces" repair-needed but nothing resolves it.

Two concrete ways to reach this dead-end:
1. **Post-hoc model loss** (storage deletion, bucket lifecycle rule, a bug) → permanent repair-needed.
2. **Migration:** every summary promoted **before** 1F-a shipped has **no** `models/{base}.json` (the
   magazine step didn't exist). After deploy, those rows are `promoted` at the current `DocVersion`, so the
   skip fires and the model is never produced ⇒ **every pre-existing cloud summary is permanently
   repair-needed**, invisible-as-broken to its owner. The spec has no migration/`DocVersion`-bump story.

**Fix (needs a decision):** Define the repair path. Options: (a) a targeted "repair" that bypasses the
`summaryMd.status` skip when the model blob is absent (regenerate model only, priced as the magazine pass,
re-uses stored MD — cheap, no transcribe/summary re-bill); (b) tie repair to a `DocVersion` bump /
resummarize; (c) a one-shot backfill migration for pre-1F-a promoted summaries. At minimum, state the
migration posture for existing data and add a behavior row for "promoted summary predating the magazine
pass."

### H-2 — Serve path cannot distinguish "repair-needed" from "finalizing (committed)" from blob presence alone; the mandated ordering is insufficient — CORRECTNESS
**Where:** spec §4.3 step 4, §4.1 ordering ("promote model before marking summary promoted"), B9/B9b; code `summary-handler.ts:172-179`, `supabase-metadata-store.ts:13-35`.

The serve flow (§4.3) classifies "md present + model absent ⇒ repair-needed (409/410)". But it **never reads
the artifact status**, and the mandated ordering pins only *model-before-status-flip*, leaving the **md-blob
vs model-blob** order unspecified. On a *normal first run* the sequence includes a window where the md blob
is promoted, the model blob is not yet, and `summaryMd.status` is still `committed`. A serve landing in that
window sees md-present/model-absent and would **mis-classify a finalizing doc as repair-needed** (false 409),
even though it will self-heal in milliseconds. Per the glossary, a *committed* (not yet promoted) artifact
should read as **not-yet-available**, not broken.

Also note the serve reads via `metadataStore.readIndex`, which selects only the `data` jsonb
(`supabase-metadata-store.ts:23-33`). `artifacts.summaryMd.status` lives *inside* `data` (see
`summary-handler.ts:84-90`), so it is technically reachable — but the spec's flow doesn't read it, so the
repair-needed vs finalizing distinction is unimplementable as written.

**Fix:** (a) Read `artifacts.summaryMd.status` and only classify **repair-needed when status ===
'promoted'** (status `committed` ⇒ "finalizing / try again", e.g. 404-with-retry or 425); **and/or**
(b) pin the worker ordering to **promote the model blob *before* the md blob** so that md-presence implies
model-presence for a given run — then md-present/model-absent can *only* be genuine repair-needed. (b) is
the stronger invariant and removes the status read from the hot path.

### H-3 — Coupling the magazine pass into the same atomic run makes a transient magazine failure re-bill the entire transcribe+summary chain — INTENT/DESIGN
**Where:** spec D3, D8, §4.1 ordering; code `summary-handler.ts:99-179`, `gemini.ts:495-504`.

Because the invariant is "a promoted summary implies a promoted model," the magazine pass must succeed
*before* the summary is marked promoted. So **any** transient magazine Gemini failure (rate limit, 5xx,
truncation, schema mismatch) fails the *whole* job with the summary still `committed`. On the next attempt
the idempotency skip does **not** fire (status ≠ promoted), so the worker re-runs **transcribe + summary +
quickview + magazine** and **re-bills all of them** — even though the expensive transcribe/summary already
succeeded once. The pre-existing "AbortSignal doesn't stop billing" reclaim double-charge
(`summary-handler.ts:168-170`) now spans one more pass, and magazine adds a fresh failure surface to every
job. This raises both worst-case spend *and* the job failure rate.

The reservation still *bounds* this (if B-2 is fixed) via `worst × attempts`, so it's not a bound
*violation* — but it is a real cost/reliability regression that the spec doesn't acknowledge, and it is the
same root cause as H-1's dead-end (a decoupled, status-keyed magazine step would fix both: summary promotes
first and is billed once; magazine is its own self-healing artifact that can be repaired without
re-transcribing).

**Fix (needs a decision):** Either accept the coupling and *document* the re-bill/failure-amplification
tradeoff explicitly in D3/D8, or decouple: promote the summary first (billed once), then produce the
magazine as a separately-status-tracked source-of-truth blob whose absence is repair-needed *and*
repairable without re-billing transcribe/summary. The decoupled design also resolves H-1.

### H-4 — Malformed `playlistId` returns 500, not the promised 400 (B13) — CORRECTNESS
**Where:** spec §4.3 step 2, B13 ("malformed params (bad UUID, etc.) → 400"); pattern `resolve.ts:75-80` (`.eq('id', playlistId).maybeSingle()`).

Resolving `playlistId → playlist_key` uses `.from('playlists').select(...).eq('id', playlistId)`. If
`playlistId` is not a valid UUID, Postgres raises `22P02 invalid input syntax for type uuid` — an **error**,
not an empty result — so `.maybeSingle()` rejects and (per the `getWorkerStorageBundle` pattern) the error is
thrown. The serve flow in §4.3 has **no UUID pre-validation** and no error→400 mapping, so B13's promised
400 becomes an unhandled **500** (and leaks a DB error string unless caught). `assertVideoId` guards the
video id, but there is no analogous `assertUuid(playlistId)`.

**Fix:** Pre-validate `playlistId` as a UUID (regex/`assertUuid`) before the query and return 400 on
failure — or catch `22P02` and map to 400. Add it to the flow, not just the behavior table.

---

## MEDIUM

### M-1 — Cloud summary view renders non-functional "dig deeper ▶" controls — INTENT/DESIGN
**Where:** spec D2 (dig serving deferred), §4.4; code `render.ts:82-91` (`digControl`), `nav.ts:189-212, 396-443`.

`renderMagazineHtml` unconditionally emits a `digControl` link (`<a class="dig" data-section=…>dig deeper
▶</a>`) for every section that has a `timeRange`, plus the `NAV_SCRIPT`. The summary-side nav wiring reads
`outputFolder` from the URL (`nav.ts:211-212`) and `return`s early if it's absent. Cloud URLs carry
`playlist=<uuid>`, **not** `outputFolder`, so the nav script bails and the dig controls **never get an
href** — the cloud summary shows dead "dig deeper ▶" affordances that do nothing on click. D2 defers dig
*serving* but the shared renderer still paints the dig *controls*.

**Fix (needs a decision):** Either suppress dig controls when rendering the cloud summary (e.g. a render
option `showDig:false`), or teach the nav wiring to read `playlist` as well and render the controls as
visibly-disabled "coming soon" rather than inert links. Add a behavior row for the state of dig controls in
the cloud view.

### M-2 — Envelope unwrap and corrupt-model handling on the serve path are unspecified — CORRECTNESS
**Where:** spec §4.3 steps 4-5 ("`blobStore.get(models/${base}.json)` … `renderMagazineHtml(parsed, model)`"); code `generate.ts:49-54` (envelope shape), `render.ts:56` (expects a bare `MagazineModel`).

`models/{base}.json` stores the **envelope** `{sourceMd, generatedAt, sourceSections, model}`, not a bare
`MagazineModel`. §4.3 passes "`model`" straight to `renderMagazineHtml`, glossing the required JSON-parse +
`.model` extraction + schema validation. A corrupt/partial/older-shape envelope (truncated write,
schema-version skew) would throw inside `render` → **unhandled 500**, and there is no enumerated behavior
for it. `rerender.ts:44` treats an unreadable/invalid envelope as `skipped-no-model`; the cloud serve needs
an equivalent decision (repair-needed vs 500).

**Fix:** Specify: `get` → `JSON.parse` → validate `.model` against `MagazineModelSchema`; on
parse/validation failure classify as repair-needed (a corrupt source-of-truth blob is exactly the
repair-needed condition) rather than 500. Add a behavior row. (A `sourceSections` drift check is *not*
needed in cloud since md+model are produced in one run — worth stating so it isn't cargo-culted from
`rerender.ts`.)

### M-3 — D6's explicit video-level `owner_id === auth.uid()` assertion is not implementable from `readIndex` output — CORRECTNESS
**Where:** spec D6, §4.3 step 3 ("assert `owner_id === auth.uid()` explicitly as defense-in-depth"); code `supabase-metadata-store.ts:22-34` (selects only `data`), `worker-persistence.ts:32-40`.

`readIndex`/`readVideo` return a `Video` reconstructed from the `data` jsonb, which carries **no
`owner_id`** (that's a separate column). So the "explicit `owner_id === auth.uid()`" check at the *video*
level (§4.3 step 3) can't be performed on `readIndex`'s output. The meaningful, implementable owner
assertion is the **playlist-level** one in step 2 (the `playlists` row does expose `owner_id`). At the
video level, RLS is the only real backstop and the explicit check is either vacuous-as-written or requires
an extra `owner_id` select.

**Fix:** Either drop the video-level explicit-assert claim (state RLS + the playlist-level assert are the
isolation guarantees), or explicitly `select('owner_id, data')` for the video and assert on it. Don't leave
D6 describing a check that the read path can't make.

### M-4 — CSP is under-specified beyond `script-src`/`style-src`; nonce generation unspecified — CORRECTNESS/INTENT
**Where:** spec §4.3 step 6, D7, B10.

The spec names only `script-src`/`style-src` nonces. A real, hardened CSP for a doc-serving GET needs
decisions on `default-src`, `base-uri`, `object-src` (all typically `'none'`), and `connect-src`. The nav
script issues same-origin `fetch`/`EventSource` (`nav.ts:230-233, 362, 433`) — harmless for the summary
view *today* because it early-returns without `outputFolder`, but it becomes load-bearing the moment dig
serving lands (1F-c) and a too-loose default would silently allow it now / a too-tight one break it later.
The nonce itself has no stated generation contract (must be a per-response CSPRNG value, ≥128-bit, base64).

**Fix:** Specify the full policy (`default-src 'none'; script-src 'nonce-…'; style-src 'nonce-…'; img-src
'self' data:; base-uri 'none'; object-src 'none'; connect-src 'self'` as a starting point) and the nonce
generation source (`crypto.randomBytes`/`randomUUID`, per response).

---

## LOW

### L-1 — "Thread an optional nonce" understates the refactor: the scripts are exported *const strings*, not functions — CORRECTNESS
`THEME_HEAD_SCRIPT`, `NAV_SCRIPT`, `THEME_TOGGLE_SCRIPT` are module-level `const` strings
(`theme.ts:78,97`, `nav.ts:189`) consumed directly in `render.ts:110,122`. Stamping a per-request nonce
requires converting them to nonce-taking functions (or injecting the attribute via string surgery) across
every call site, while preserving byte-identical no-nonce output. Say so, so the plan sizes it correctly
rather than treating it as "add an optional param."

### L-2 — Redundant double playlist lookup — CORRECTNESS
§4.3 step 2 resolves `playlistId → playlist_key`; step 3's `readIndex` then re-selects the same playlist by
`playlist_key` (`supabase-metadata-store.ts:14-18`). Harmless under RLS (key is unique per owner) but a
wasted round-trip; the already-resolved `playlistId` could be passed through.

### L-3 — Local-vs-cloud branch trigger is ambiguous — CORRECTNESS
§4.3 keys local behavior on `STORAGE_BACKEND=local`, while §5 keys it on `playlist` vs `outputFolder`
param ("mutually exclusive by backend"). Define precedence when a request carries the "wrong" param for the
active backend (e.g. `outputFolder` present under `STORAGE_BACKEND=supabase`) — reject 400, or ignore?

### L-4 — `generateMagazineModel` has no `signal`; magazine call can't be aborted on lease-loss — CORRECTNESS
Covered under B-1, noted separately for the plan: `generateJson` supports `opts.signal`
(`gemini.ts:219,223,225`) but `generateMagazineModel` never passes it, so a SIGTERM/lease-loss during the
magazine call runs to completion (billing) before the abort is observed. Thread `opts.signal` through when
adding caps.

---

## Summary

| Severity | Count |
|---|---|
| Blocking | 3 |
| High | 4 |
| Medium | 4 |
| Low | 4 |

**Blocking**
- **B-1** — `generateMagazineModel` takes no caps/`maxOutputTokens`/signal today; the magazine pass is an unbounded paid call, so the spend bound is not provable (unstated code change).
- **B-2** — §4.2 cap-soundness recompute omits the magazine pass's *input* tokens and leaves its input bound + pass count undefined → bound undercounted / not sound.
- **B-3** — Nonce CSP can't authorize the inline `onclick` print button; strict-CSP and byte-identical-local are mutually unsatisfiable for it without weakening CSP or diverging markup.

**High**
- **H-1** — Repair-needed is a dead-end: the idempotency skip blocks worker regeneration and D8 blocks serve regeneration, and every pre-1F-a promoted summary becomes permanently repair-needed (no migration story).
- **H-2** — Serve path can't distinguish repair-needed from finalizing (committed) by blob presence alone; the mandated ordering doesn't pin md-blob vs model-blob order, so normal finalizing reads as a false 409.
- **H-3** — Coupling magazine into the atomic run makes any transient magazine failure re-bill the whole transcribe+summary chain and amplifies job failure rate.
- **H-4** — Malformed `playlistId` (non-UUID) returns 500, not the B13-promised 400 (no UUID pre-validation).

(Medium/Low: dead cloud dig controls; envelope-unwrap + corrupt-model handling unspecified; D6 video-level owner-assert not implementable from `readIndex`; CSP under-specified beyond script/style + no nonce-gen contract; const-not-function refactor scope; redundant playlist lookup; local/cloud branch trigger ambiguity; missing signal threading.)
