# Whole-branch re-review (ROUND 3, Claude adversarial) — `feat/stage3-cloud-sync`

Scope: shipped state at HEAD `1f54c60`. Read-only. Spec:
`docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md`.

Test baseline verified at HEAD:
- `npx jest tests/lib/cloud-sync` → **15 suites / 85 tests passed**
- `npx jest --config jest.integration.config.ts --runInBand tests/integration/cloud-sync` →
  **4 suites / 35 tests passed**

Known-and-accepted, not re-reported: T14-M1, T14-M2, T5 coverage gaps, T4 automock comment,
Claude-R2-M1 (stale non-`summaryMd` artifact pointers), Codex-R2-Medium (absent companion scalars),
`tests/integration/reservation-release.test.ts` (pre-existing).

---

## Part A — are the round-2 fixes genuinely fixed?

### H-R2-1 — validate the MD body BEFORE claiming the receiver slot
**Verdict: GENUINELY FIXED** (for the additive path).

`lib/cloud-sync/sync-run.ts:160-162` now precedes `ensureReceiverSlot` (`:164`).

- **No partial receiver state before the throw.** `setPlaylistMeta` and `claimVideoSlot` both live
  inside `ensureReceiverSlot` (`:135-138`), which is now unreachable when the guard fires. Nothing is
  created, so there is nothing to roll back. Correct.
- **Would the new e2e assertion actually fail if the guard moved back?** Yes, and on run 1, not only
  run 2: `e2e.int.test.ts:452` asserts `await localVideoRecord(ctx)` is `null`. With the guard after
  the slot claim, `claimVideoSlot` inserts `{ id, serialNumber }` and that assertion fails
  immediately. The run-2 baseline assertion (`:462`) is the extra guard against the laundering itself.
  Both are real.
- **Later throws on the additive path still leave partial state**, but none reproduce the H-R2-1
  laundering. `putStaged`-verify (`:172`), row-not-persisted (`:198`) and promoted-assert (`:206`) all
  fire only when `mdBody != null`, i.e. the source body is READABLE — so on the next run the source
  side derives a non-null `mdHash`, `reconcileClassA:22` returns `copyToLocal`/`copyToCloud` and the
  video heals through the transfer path. The `!lHas && !cHas → skip` laundering branch is not
  reachable from these. Convergent.
- **Orphaned staged blob.** A throw between `putStaged` (`:169`) and `promote` (`:174`) leaves the
  `_staging/<uuid>/…` object behind; the additive path has no `delete` counterpart to
  `transferClassA:300`. Storage litter only — the temp key is per-attempt-unique so it can never be
  mistaken for a final object, and no reader looks under `_staging/`. Nit, not a finding.
- **Is the residual `mdBody != null` at `:167` dead?** Logically yes (given `:160`, `video.summaryMd`
  truthy ⇒ `mdBody != null`). It hides nothing: it is a narrowing guard whose only fallthrough is the
  `else if` at `:185-190`, which strips the artifact pointer — a strictly safe degradation, not a
  silent promotion. Keep or drop; immaterial.

### H-R2-2 — `digDeeperMd` preserved on `transferClassA`
**Verdict: GENUINELY FIXED, and the flip side is safe.**

I checked the "stale dig anchors" worry directly. It does not materialize, because the merge is
already defensive:

- `lib/html-doc/dig-merge.ts:97-107` matches a `DugSection` to a summary section by **exact
  `sectionId === startSec`**, and `sectionId` *is* the section start second
  (`lib/dig/section-window.ts:58`, `lib/dig/dig-section.ts:40,73`). A match therefore means the two
  bodies agree on that section's anchor — semantically the right section, not a positional guess.
- Unmatched dug sections are never silently dropped or mis-attached: step 2 falls back to exact title
  (`dig-merge.ts:141-156`), and anything still unconsumed becomes an **orphan**
  (`:167-183`) rendered under "Unmapped dug sections" with the explicit note *"This section was dug
  but could not be matched to a current summary section. Re-dig to regenerate."*
  (`lib/html-doc/render-dig-deeper.ts:341-346`).
- `isStale` (`dig-merge.ts:104`) additionally surfaces `↻ outdated` for old `genVersion`.

So a winner MD with different sections degrades to *visibly orphaned* dig content, never to wrong
anchors. Preserving paid content and letting the merge flag the mismatch is strictly better than
destroying it. `digDeeperHtml: null` (`sync-run.ts:332`) is sufficient to force the re-merge —
`build-doc-html.ts:126-135` re-parses the companion on every dig-deeper build.

`sanitizeAdditiveVideo` nulling `digDeeperMd` (`:111`) remains correct: on the additive path the
receiver has no row and no dig blob is copied, so keeping the pointer would advertise a file that
does not exist there.

One real consequence of preserving the pointer is reported as **M1** below (dig-deeper view derives
its summary path from `digDeeperMd`). It does not change this verdict.

### M-R2-2 — corrections guard narrowed to `la.mdHash != null && ca.mdHash != null`
**Verdict: NOT FIXED SAFELY — the narrowing predicate is wrong and reopens WB-B1. See B1.**

The "hoist is behavior-neutral" claim itself checks out for the normal case: `readMdBody`
(`sync-run.ts:59-63`) is a pure `blob.get` + `toString`, and `deriveClassASignals` does no I/O. The
only ordering change is that a **throwing** blob read now aborts the video before the
corrections-unresolved baseline would have been written. Local `get` throws on non-ENOENT
(`lib/storage/local/local-blob-store.ts:20`); Supabase `get` never throws (`:25`). That change is in
the right direction (do not record a baseline for state you could not read) and matches how every
other two-sided video already behaved.

The defect is not the hoist — it is that `la.mdHash != null` was used as the test for "this side
holds an MD". It does not mean that. See B1.

---

## Part B — new findings

### B1 (BLOCKING) — `mdHash == null` conflates "has no MD" with "MD is unreadable", so an unreadable blob silently destroys the other replica's body and launders it into an agreed baseline
**`lib/cloud-sync/sync-run.ts:491-501`** (guard), **`:509`** via
**`lib/cloud-sync/reconcile-class-a.ts:21-23`**, **`lib/storage/supabase/supabase-blob-store.ts:25`**

`readMdBody` returns `null` for *two* different situations: the record advertises no `summaryMd`, or
it advertises one whose bytes could not be read. On Supabase they are indistinguishable —
`get` is `if (error) return null`, which swallows **every** failure (network, 5xx, timeout, RLS
denial), not just 404. The additive path knows this and guards it explicitly (H-R2-1, `:160`). The
two-sided path has **no equivalent guard**, and M-R2-2 has now routed the corrections-conflict case
into it.

**Both manifestations reproduced** (temporary probe under `jest.integration.config.ts`, since
deleted; seeds a cloud row advertising `summaryMd` + a `promoted` artifact with no readable body):

**P1 — the WB-B1 destruction, back.** Local holds a corrected body with `corrections: 'A'`; cloud has
`corrections: 'B'`; both backfilled ⇒ unresolved conflict. Cloud body unreadable.
```
report: {"updatedCloud":1,"conflictsLogged":1,"needsRegen":0,"errors":[]}
cloud blob after: "# Local…"        ← cloud's body overwritten
baseline written: classA.mdHash = <hash of the LOCAL body>   ← full agreement recorded
```
`ca.mdHash == null` ⇒ the guard at `:501` does not fire ⇒ `reconcileClassA:23` (`!cHas`) ⇒
`copyToCloud` ⇒ `transferClassA` `put`s the local body at the same key (`:299`, overwrite on both
backends). This is precisely the destructive copy under an unresolved corrections conflict that
WB-B1 was filed to prevent — and it is silent (`errors: []`).

**P2 — worse, and not conflict-gated.** Cloud holds a `docVersion.major: 9` doc; local `major: 1`;
no corrections anywhere. Cloud body unreadable for one run:
```
report: {"updatedCloud":1,"needsRegen":0,"errors":[]}
cloud blob after: "# Local…"
cloud docVersion after: {"major":1,"minor":0}     ← format DOWNGRADED 9 → 1
baseline: classA.docVersionMajor 1, mdHash <local>  ← agreement laundered
```
The `!cHas` early return at `reconcile-class-a.ts:23` fires **before** the "never downgrade format"
rule at `:43-46`, so a transient download error bypasses the entire currency/format ladder. Run 2
reads identical bodies on both sides → `skip` → the loss is permanent and unrecoverable
(`companionTransfer` additionally deleted the receiver's model envelope, `shareNeedsOwnerServe: 1`).

**Why this is Blocking, not High:** silent, unrecoverable destruction of user content triggered by an
ordinary transient network error, with the error laundered into a baseline that asserts the two
replicas agree. It also forces a full re-generation to recover — a money finding of the H-R2-2 class.
P2 predates round 2 (it is not a regression); **P1 is newly introduced by M-R2-2**.

**Fix** — one guard closes both, mirroring `copyAdditiveVideo:160`. After deriving `la`/`ca`
(`:491-492`), before the corrections guard:
```ts
if (lv.summaryMd && la.mdHash == null) throw new Error(`local MD body unreadable for ${id}`);
if (cv.summaryMd && ca.mdHash == null) throw new Error(`cloud MD body unreadable for ${id}`);
```
A per-video throw is caught at `:540`, surfaces in `report.errors`, and — critically — advances no
baseline, so the run heals once the body is readable. `reconcileClassA`'s `!lHas/!cHas` branches then
mean what they claim: the side genuinely advertises no MD. M-R2-2's intent survives intact, because
"purely additive hydration" is exactly "the loser advertises no `summaryMd`". Regression tests: the
two probe scenarios above (assert `errors` non-empty, blob byte-preserved, no baseline written).

### M1 (Medium) — with `digDeeperMd` preserved, the dig-deeper view renders the PRE-SYNC summary when the two replicas' MD keys differ
**`lib/html-doc/build-doc-html.ts:86-104`** ← exposed by **`sync-run.ts:331-335`**

`transferClassA` writes the **winner's** `summaryMd` key onto the loser (`:304`). The two replicas'
keys are not guaranteed equal: the key is `${padSerial(serialNumber)}_${slug}.md`
(`lib/pipeline.ts:245,265`) and `serialNumber` is deliberately **replica-local** — sync never
propagates it (`sanitizeAdditiveVideo:117`, receiver claims its own via `claimVideoSlot`). So local
`003_slug.md` vs cloud `007_slug.md` for the same video is a normal outcome of divergent ingestion
order.

After a `copyToLocal` transfer the local row holds `summaryMd: '007_slug.md'` (new body, written) but
`digDeeperMd: '003_slug-dig-deeper.md'` (preserved). `build-doc-html.ts:86-92` derives `base` from
`digDeeperMd` **in preference to** `summaryMd`, then reads `relDir/003_slug.md` (`:104,112`) — the
stale pre-sync local file, which `transferClassA` never deletes. Result: `type=summary` serves the
post-sync body while `type=dig-deeper` (and the dig-deeper PDF, `lib/pdf/pdf-path.ts`) serves the
pre-sync one, self-consistently and with no staleness indicator. The summary path is unaffected —
`rerender.ts:42` and `ensure.ts:35` both derive `base` from `summaryMd`.

Medium, not High: no data is lost, dig is out of scope for M2a (spec §line 35), it requires diverged
keys, and the degradation is stale-but-coherent. Note it is **not a regression** — behaviour matches
pre-`32a164c`; the H-R2-2 fix restored it rather than introducing it. Cleanest fix lives outside
sync: prefer `summaryMd` for `base` derivation in `build-doc-html`, using `digDeeperMd` only for the
companion path. Recording it so the choice is deliberate rather than accidental.

---

## Checked and clean

- **Baseline honesty on the NEW branch (one-sided hydration under an unresolved corrections
  conflict).** Traced both runs. Run 1: `!lHas` → `copyToLocal` (`needsRegen` set), then
  `buildBaseline` (`:539`) → `buildClassBBaseline:372-373` carries the **previous** baseline for the
  conflicted `corrections` field rather than the winner. No agreement about corrections is recorded.
  Run 2: both sides now hold bodies, `reconcileHuman` still sees `A` vs `B` against an
  `{undefined, undefined}` base → conflict re-fires → the guard at `:501` now fires → skip. Stable,
  sticky conflict, no oscillation, no false agreement. Covered by the new e2e test at
  `e2e.int.test.ts:519-551`.
- **Money-safety.** No producer/enqueue import, no `spend_ledger` reference anywhere in
  `lib/cloud-sync/*`; `needsRegen` is written to the report only (`:502,510`) and never read as a
  trigger. `summaryHtml`/`digDeeperHtml` are the only regenerable caches touched. Re-spend-forcing
  paths: the H-R2-2 class is fixed; B1 is a new one and is counted as such above.
- **Atomicity / durable-before-advertise.** `transferClassA:286-299` stage → verify hash → `put` the
  verified bytes at the final key → `updateVideoFields` advertises `promoted` only after. Manifest
  strictly after the commit on every branch (`:460`, `:504`, `:539`). Unchanged by `1f54c60`.
- **Idempotency across two runs** on the additive-throw, transfer, skip, corrections-unresolved and
  new one-sided-hydration branches. The only laundering path found is B1.
- **Cross-backend semantics.** Null persistence through `merge_video_data`'s `data || (p_fields -
  'artifacts')` (cloud) and the shallow spread in `lib/index-store.ts:132-146` (local) re-verified for
  the now-two-field null set; both store JSON null, both read falsy. The `get`-swallows-errors
  asymmetry between the two backends is B1.
- **RLS / no service-role.** Unchanged: `SyncDeps` exposes no raw client, `cloudP.id = deps.ownerId`
  (`:435`), RPCs remain `security invoker`.

---

**NOT CONVERGED** — 1 new Blocking (B1: unreadable-blob conflation destroys the other replica's MD
and records a false agreement; reproduced in two forms, one of them newly opened by the M-R2-2
narrowing) plus 1 Medium. Part A: H-R2-1 genuinely fixed, H-R2-2 genuinely fixed, M-R2-2 fixed the
stranding but with an unsafe predicate. Another round is required after B1.
