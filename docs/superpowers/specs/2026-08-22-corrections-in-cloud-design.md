# Slice A — corrections work in the cloud, attended path

**Backlog:** #23. **Phase:** 1. **Scope:** the user-initiated cloud correction, and nothing else.

**History.** v1 → r1 (26 findings) → v2 → r2 (33) → v3 → r3 (Codex 2B/2H/2M/2L, Claude 3B/7H/8M/10L)
→ **this document**. All three rounds NOT CONVERGED from both halves, firing `docs/dev-process.md`'s
Phase 6 trigger. **Both halves independently concluded the document was three slices, not one.** This
is slice A, with the round-3 residue that survives the split folded in.
Reviews: `docs/reviews/spec-corrections-in-cloud-r{1,2,3}-{codex,claude}.md`.

**Round-3 residue folded in:** r3 H6 the inverted sync falsifier (§7), r3 H7 the magazine envelope
(§2), r3 M3 the unstated `maxDuration` (§5.4), r3 M7 the unnamed clear surface and r3 M8's
server-side cap (§4.1, §2), and ten citation drifts — all ten of r3's line references were correct.

> ⚠ **Round 4 ran on that fold-in and returned NOT CONVERGED from both halves** (Codex 0B/2H/1M/1L;
> Claude 2B/4H/6M+L). It found **two Blockings in the fixes themselves**, which is why the round
> existed. Both are corrected in place below — §4.1 (the `updated_at` trigger) and §2 (the blob write
> protocol) — along with H1–H4 and M1–M6.
>
> **The one decision that needed the user — the magazine envelope — is SETTLED: option (e), 2026-08-23.**
> Invalidation is **derived** from the envelope's existing `sourceMdHash` via one conjunct in
> `isFresh`; nothing is deleted and the correction path writes no envelope at all. The share path and
> the over-budget fallback are untouched, so backlog #57 stands. Full reasoning and costs in §2.
>
> **Two of the four rounds' worst errors were the same shape, and neither was a wrong line number.**
> §4.1 cited a function correctly and missed the trigger *underneath* it; §2 cited `isFresh` correctly
> and missed the `sourceMdHash` the predicate *ignores*. Citation-checking cannot catch either. The
> question that would have is **"what else touches this?"** — and it is now the first question this
> spec's own review brief asks.

> **Decided 2026-08-23 (user).** Decompose. Slice A ships with **post-hoc spend recording and no
> reservation protocol** — a third option neither reviewer named. v3's error was choosing "metered",
> specifying the mechanism, and omitting the amount: *"the worst of both"*.

**Goal.** A cloud user edits corrections, presses the button, and gets a corrected summary — the same
behaviour as local.

---

## 0. The other two slices

| Slice | Contents | Where it went |
|---|---|---|
| **B — unattended correction** | worker integration, the pre-apply re-read, the `mdCorrectionsHash` stamp on a generated body | `docs/backlog.md` #60. **Blocked on #22**: `promote` is create-if-absent, so a corrected body can be discarded while the row claims it. A failure inside the job also discards a completed ~115¢ generation, which needs containment slice A does not |
| **C — money instruments** | reserve/settle RPCs, `correction_est_cents`, `correctionWorstCents()`, the `cap-soundness` extension, the `max_duration_seconds ≤ 4,332s` ratchet | `docs/backlog.md` #61. A money-path slice; this repo's record for those is five to seven rounds (`serve-path-bounding`, PR #67) |

⚠ **The create-if-absent hazard is AVOIDED in slice A, not absent from it (r4 B2).** Slice A writes
the same body to the same key through the same store, and the B row above previously read as though
the hazard lived only in B — *"an active misdirection introduced by the split"*. A stays safe **only
because §2 requires `put` rather than `writeArtifact`**. What B additionally faces, and A does not, is
the *publication* problem (`promote` inside a job it does not control) and the ~115¢ containment.

**Three round-3 findings die with this split** and are not addressed here because they belong to B
and C: the falsifier asserting unattended survival (r3 B2), the structural-validation throw
discarding a generation (r3 B3), and the missing `correction_est_cents` (r3 H1 — with post-hoc
recording there is no estimate to name).

---

## 1. Measured position

| Fact | Value | Source |
|---|---|---|
| Apply paths | one — `app/api/videos/[id]/regenerate/route.ts:63` | `grep -rn fixSummary` |
| …reachable from cloud | none — `fs.promises` at `:50`, `:69` | same |
| Storage seam already used | `getStorageBundle()` at `:36` — **metadata only** | `grep -n` |
| Corrections UI gate | `components/VideoMenu.tsx:181` — `{!cloudMode && video.summaryMd && (`, with `cloudMode` from `:52`. `:188` is the button's label, not the gate | read |
| Apply guard today | `route.ts:63` — `trimmedCorrections ? fixSummary(…) : stripped` | read |
| Quick-view today | `:66`, **unconditional** | read |
| Stamping rule | `:77-79` — a **different** quantity from the apply input | read |
| `withCaps` | `lib/gemini.ts:36`; **four** call sites — `:326` `generateSummary`, `:433` `extractQuickView`, `:536` `generateMagazineModel`, `:686` `transcribeViaGemini`; **not `fixSummary`** | `grep -n withCaps` |
| Per-call Gemini timeout | 60,000 ms | `lib/gemini.ts:105` |
| Retry budgets | `fixSummary` `retries = 2` (`:473`); `generateJson` `GENERATE_JSON_RETRIES = 2` (`gemini-cost.ts:22`) → 3 attempts each | read |
| Server-side corrections cap | **none** — `route.ts:24-26` checks `typeof === 'string'` only; the 1,000-char limit is client-side at `CorrectionsPanel.tsx:105` | read |
| Typical correction cost | ≈0.6¢ | `lib/gemini-cost.ts:33,35` |

**Not verified:** the row's "99 existing free-form corrections" — no `psql`; `pg` cannot verify
Supabase's TLS chain.

### 1.1 Corrections to backlog #23

1. *"Unaffordable by construction"* → **wrong**. ≈0.6¢ typical.
2. *"A reworded heading orphans paid digs"* → **overstated**. A reworded heading alone does not orphan
   a dig while `startSec` is stable (`lib/dig/cloud/dig-blob-key.ts:13-25`, key expression at `:22`;
   `lib/dig/cloud/enqueue-dig-core.ts:33-39`). It **does** drop the magazine gists for every section
   (`lib/html-doc/read-model.ts:12-25`) and remove the title fallback
   (`lib/html-doc/dig-merge.ts:120-155`). **If both move, orphaning is real.**

⚠ **§3's structural validation is justified by that second clause and must not overstate it.** The
reason to validate is the *measured* cost — gist invalidation, and the fallback disappearing — not
the retracted "orphans paid digs".

**"Regenerate" is a misnomer**: zero references to `summaryCore`, `generateSummary` or
`resolveTranscriptSegments`. It corrects an existing document.

### 1.2 What the user asked for, and what this does not do

⚠ The original request was *"if current text do not include specified misspelling, do not correct"* —
a check on whether the misspelling **occurs in the text**. **That feature is not in this slice.** Three
rounds of trying to specify it produced four false-negative Blockings, and a false negative silently
discards a correction the user typed. What remains skips only when the corrections **field is empty**.
The accepted trade: ≈0.6¢ per press on a video whose corrections no longer match.

---

## 2. Components

**`lib/corrections/apply-core.ts`** — new, store-agnostic.
`stripQuickViewCallout` → `fixSummary` → **structural validation** → `extractQuickView` →
`insertQuickViewCallout`. In `{ md, corrections, tags, signal }`, out `{ content, tldr, takeaways }`.

- **`tags` is required.** `route.ts:67` passes `video.tags ?? []`; dropping it deletes the callout's
  Concepts line.
- ⚠ **`signal` is required.** v3 lost it, leaving the abort check as a point test in front of ~181 s
  of uncancellable paid work. **Three places take it (r4 M3 — v4 said two):**
  1. `generateContent` — `gemini.ts:496` passes none, where `generateJson:273` does.
  2. The backoff sleep — `fixSummary:505` is a bare `new Promise(setTimeout)` where
     `generateJson:281` uses `abortableSleep`.
  3. **The loop-top guard** — `generateJson:271` re-checks `opts?.signal?.aborted` at the head of
     *every* iteration and throws. `fixSummary`'s loop (`:494`) has no equivalent, so a signal that
     aborts between attempts still buys attempt 3.

  Wire only the first and an abort waits out up to 1.2 s of uninterruptible sleep **and** a further
  paid attempt. `generateJson` is the worked example for all three; copy its shape.

**Structural validation — specified as a comparison, not as "the same invariants".** v3 said the
latter, which is the deleted prose-rule relocated. The check is exact:

> Parse the pre-correction document (after callout strip) and the post-correction document with
> `lib/html-doc/parse.ts`. **Throw** unless: the H2 sequence is identical in count, order and exact
> text; every section's `▶` timestamp tuple `(startSec, endSec)` is identical; the H1 and frontmatter
> are present. No repair — `generateSummary` repairs (`ensureSectionTimestamps`, `gemini.ts:391-403`,
> the call at `:401`) because it authored the structure; correction did not, so a structural change
> means the model disobeyed and the result is discarded.

On this slice a throw costs one correction (≈0.6¢). *(Inside the summary job it would cost a
completed generation — that containment problem is slice B's.)*

⚠ **That guarantee invalidates nothing, so something must.** `isFresh` is
`sameTitles && generatorVersion` (`read-model.ts:12-25`). A successful correction is by construction
*prose changed, headings pinned*: `fixSummary`'s prompt pins them (`gemini.ts:480`) and the validator
above now **enforces** it. So the cached model reads fresh forever and the rendered magazine serves
**pre-correction gists over corrected prose**. Pinning made this certain where it used to be merely
likely — the one thing that used to break the cache by accident is now forbidden.

> ⚠ **CORRECTED at round 4 (r4 H2).** This section previously said *"there is no content hash"*. That
> is true of **`isFresh`**, not of the envelope. `ModelEnvelopeSchema` has carried `sourceMdHash`
> since Stage 3 (`model-store.ts:23`), written on every materialize (`serve-doc.ts:181`) and already
> used as a staleness oracle by the sync companion path. `read-model.ts:54-56` says in the code
> exactly why it is not in `isFresh`: *"Deliberately NOT added to `isFresh`: that governs the OWNER
> path, where refusing an envelope triggers a reserve-and-charge regeneration. Making a money path
> stricter is its own slice with its own review."* **The false premise made the better option
> invisible** — the same shape of error as §4.1's.

#### ⚠ DECIDED (e) — BUT THE IMPLEMENTATION HAS AN OPEN BLOCKING FROM ROUND 5. DO NOT PLAN THIS BLOCK YET.

> **Round 5 (scoped to this block): NOT CONVERGED from both halves.** Codex 1B/1H/1M/1L,
> Claude 1B/3H/5M/3L. Both say (e) is the **right shape** — neither sends the *choice* back. The
> defects are in how it lands.
>
> **r5-claude B1 — (e) charges once per PRESS, not once per CORRECTION.** `route.ts:66-69` rewrites
> the markdown on **every** press, re-inserting a callout built from a fresh, non-deterministic
> `extractQuickView` — which §3 requires to run unconditionally. `serve-summary-core.ts:101` hashes
> the **full** body, callout included. So a **bare press, which applies nothing, moves the hash and
> books a ~6¢ magazine regeneration.** Verified here. It also means §7's row asserting `mdHash`
> byte-identical on a bare press contradicts §4's table saying `tldr`/`takeaways` are updated —
> before (e) that was bookkeeping; now it is money.
>
> **r5-claude H1 — (e) moves the owner's own page into the reserve state machine.** Of the five
> non-ok statuses at `serve-summary-core.ts:118-125`, only `over_budget` has a stale fallback;
> `busy`, `attempts_exhausted` (K=5/UTC-day, `0012:21`), `at_capacity` and `denied` return 503/404
> **with a readable model in the bucket**. The block protected the anonymous reader and left the
> paying owner worse off.
>
> **r5-claude H3 — "#57 stands" is scoped to the correction path.** `companion.ts:151-153` already
> deletes receiver envelopes on this signal, so a *local* correction already breaks the cloud share
> link via sync **today**. (e) still beats (a); the claim was just stated unconditionally.
>
> **Cleared:** `mdHash` is stable (`canonicalizeMd`, `content-hash.ts:9-13`) — no per-serve loop.
> Polarity vs `decideCompanion` is consistent and sync cannot ship a mismatched envelope. The **local
> path is entirely unaffected** — nothing local calls `isFresh`. (e) does deliver corrected gists.
> `isFresh` has 1 production caller, `readFreshMagazineModel` 2, as claimed.
>
> ⚠ **No test fixture anywhere sets `sourceMdHash`, so the whole suite passes unchanged under the new
> conjunct.** (e) would ship with **zero** regression coverage; the mutation-check is the only thing
> between it and a silent no-op.
>
> **The root cause is not in (e).** It is that §3 makes `extractQuickView` unconditional, so a press
> that applies nothing still rewrites the body. Any body-derived freshness signal will fire on that.
> **Resolving it is a fork the spec has not settled** — see the note below — and it is deliberately
> left open rather than guessed at, because this block has now taken three attempts and produced a
> Blocking each time.

##### ✅ The CHOICE stands — option (e), 2026-08-23 (user): invalidation is DERIVED from `sourceMdHash`, nothing is deleted and nothing is written

Round 4 (r4 H1/H2) measured that **deleting the envelope is the worst available option**, and that it
reverses a decision already on record. The envelope is not a private owner cache: it is the **only**
input the anonymous share path can render from (`app/s/[token]/route.ts:102-103`, a generate-free leaf
by design) **and** the fallback the owner path serves when the per-owner budget is exhausted
(`serve-doc.ts:147-151`). Deleting it turns a **working public share link** into `notReady()` because
someone made a private edit, and removes the degradation path backlog **#57 — tolerate version skew on
the share path** decided to keep.

**The asymmetry that decides this.** There are two readers, and only one is strict:

| Reader | Used by | Checks |
|---|---|---|
| `readFreshMagazineModel` → `isFresh` (`read-model.ts:20-25`) | owner serve — regenerate-or-not | **today:** `sameTitles` **&& `generatorVersion`**. (e) adds the guarded `sourceMdHash` conjunct below |
| `readTitleStableModel` (`:57-69`) | **share path + over-budget fallback** | `sameTitles` && section count — **ignores `generatorVersion`** |

So an invalidation that acts on the **owner** predicate alone regenerates correctly while leaving the
share path and the over-budget fallback untouched. That is option (e).

##### The mechanism already exists, and it is `sourceMdHash` — not a new marker

An earlier draft of (e) proposed adding an `invalidated` marker to the envelope. **Rejected**: it
would be a *second* vocabulary for one concern, which is what
`scripts/check-vocabulary-collisions.py` exists to catch and what
`docs/backlog.md`'s two-mechanisms lesson records as *"the observable shadow of a duplicate
protocol."*

`sourceMdHash` is **already this codebase's staleness oracle**. `ModelEnvelopeSchema` has carried it
since Stage 3 (`model-store.ts:23`), both generators write it (`serve-doc.ts:181`,
`generate.ts:59`), and `decideCompanion` already keys on it — including the exact
absent-means-unprovable guard this needs:

```ts
// lib/cloud-sync/companion.ts — the sync path settled this already
const provablyStale = receiverModel.kind === 'envelope'
  && receiverModel.envelope.sourceMdHash !== undefined;
```

**`isFresh` simply never adopted it**, and **four** places in the tree already say so:
`read-model.ts:54-56`; `model-store.ts:84` — *"`isFresh` ignores sourceMdHash, so a clobbered model is
served indefinitely whenever the section titles are unchanged"*; `companion.ts:41-46`; and
§3.5.1 of the serve-path-deadline spec (below).

> **Requirement.** `isFresh` gains one conjunct, guarded the way `decideCompanion` guards it:
>
> ```ts
> sameTitles(envelope, titles)
>   && envelope.generatorVersion === GENERATOR_VERSION
>   && (envelope.sourceMdHash === undefined || envelope.sourceMdHash === currentMdHash)
> ```
>
> `readFreshMagazineModel` takes `currentMdHash`. **Both call sites already have the body:**
> `serve-doc.ts:78` and `:141` sit inside `resolveModel`, whose `mdBody: string` is a **required**
> param (`:67`, destructured `:70`). No other caller exists in `lib/`, `app/` or `components/`.

##### What the correction path does: nothing

**This is the property that makes (e) better than what was pitched.** Invalidation is **derived from
the body**, not stored beside it. The correction path writes the corrected markdown and stops:

- no envelope read, no envelope write, **no read-modify-write race**;
- no ordering question between body write and invalidation, because there is no second write;
- no failure semantics for a delete that no longer happens;
- `BlobStore.delete`'s undocumented absent-key behaviour stops mattering.

The §2 requirements about delete ordering, delete failure and `delete` idempotence are **withdrawn** —
they were answering a question this design does not ask.

##### ⚠ There is a TRIPWIRE on this change, and it was planted deliberately

`tests/lib/html-doc/read-model.test.ts:39-51` is a test whose only purpose is to go red when someone
does exactly this:

```
// KNOWN GAP, accepted in the serve-bounding spec §3.5.1 (#46).
// WHEN THIS GOES RED: someone made isFresh hash-aware. That is a MONEY decision — prose-only
// edits would then force paid regeneration — so read §3.5.1 before deleting this test.
expect(isFresh(envelope({ sourceMdHash: 'hash-of-OLD-markdown' }), titles)).toBe(true);
```

**Read as instructed.** `docs/superpowers/specs/2026-08-10-serve-path-deadline-design.md` §3.5.1
tabled *"Make `isFresh` compare `sourceMdHash`"* as option 1 of 3 and did **not** choose it:

> *"Closes it, but changes serve-path **caching**, not timeouts … Flipping that is a **money**
> decision needing its own reasoning, not a rider on a timeout fix."*

**That is a routing instruction, not a prohibition** — and it is satisfied here. §3.5.1 declined to
make the change *as a rider on a timeout fix*; this is a dedicated decision with a user sign-off and
its own review round. `read-model.ts:54-56` says the same thing in the same words: *"its own slice
with its own review."* **This is that slice.** The tripwire did its job: it forced this paragraph to
exist.

⚠ **But §3.5.1's stated reason mis-cites the code it rests on.** It says *"`companion.ts:43` indicates
ignoring the hash is deliberate."* `companion.ts:41-46` says the opposite — it lists the
titles-and-version-only check under *"round 4 … was wrong in both directions"*:

> *"the claimed safety net **does not exist**: the serve path's drift guard … compares section TITLES
> and generatorVersion, never sourceMdHash, so a prose-only MD change … is served as fresh forever."*

That is a **complaint about** the behaviour, not a defence of it. The decision was sound on its own
terms — don't ride a money change on a timeout fix — but the supporting citation should not be
inherited without re-reading it. (Same failure this project records as *quote the code, don't
characterise it*.)

##### The cost §3.5.1 named, which v(e)-as-first-written understated

§3.5.1's parenthetical is the substantive part and it survives: *"it stops a prose-only MD edit
forcing a paid regeneration."* **Corrections are not the only prose-only edit.** Under (e), **any**
body change from **any** source makes the model stale and the next owner serve pay:

| Source of a prose-only body change | Under (e) |
|---|---|
| A cloud correction (this slice) | regenerates — **intended** |
| A **sync** copying a newer body cloud-ward | regenerates — correct, but recurring, and **not** counted in this spec's cost model |
| The `model-store.ts:79-85` late-write clobber | regenerates — the bug §3.5.1 routed to backlog #25 |

So this is **not** the one-time wave the section below describes. It is a **standing per-body-change
cost**. Every one of those regenerations is *correct* — the model really is stale, and the status quo
is serving wrong gists — but "correct" is not "free", and the spec must not present a recurring cost
as a migration blip.

⚠ **NOT VERIFIED — the `decideCompanion` interaction.** `sync-run.ts:464` already ships or deletes the
receiver's envelope on a sync, keyed on the same `sourceMdHash`. So the sync row above may already be
handled before any serve, making the marginal cost smaller than stated — or the two mechanisms may
double up. **Two mechanisms now read one field for related-but-different purposes**, which is the
shape `scripts/check-vocabulary-collisions.py` watches for. The plan resolves this before the
`isFresh` change lands; it is not resolved here.

##### Test callers — the claim above is about PRODUCTION callers only

`readFreshMagazineModel` and `isFresh` have two production callers. **They have four direct test
callers**, and one of them is the tripwire:

`tests/lib/html-doc/read-model.test.ts:30, 40, 59, 68, 74`.

The plan must: delete or invert the `:40` tripwire **with a comment pointing at this section**; and add
current / stale / **absent** `sourceMdHash` cases for both `isFresh` and `readFreshMagazineModel`.

⚠ **Fixture precondition for every §7 row in this block, or the falsifiers lie.** Existing fixtures
build envelopes **without** `sourceMdHash` (`read-model.test.ts:24-25`), and under the guarded
conjunct a legacy envelope is correctly **still fresh**. A test author who seeds a "corrected
document" with a legacy-style envelope will watch a *correct* implementation fail. Every row asserting
regeneration must seed `sourceMdHash = mdHash(preCorrectionBody)`, mutate the body, then assert: first
owner serve regenerates **once** and persists `sourceMdHash = mdHash(correctedBody)`; second owner
serve is **free**.

##### What it costs, stated honestly

- **A deferred ~6¢ magazine regeneration on the next owner serve** of a corrected document. §1's
  ≈0.6¢ and §5's post-hoc recording both omit it, and §7's ledger falsifier cannot see it because it
  lands on a later request. §7 carries a row for it.
- **It makes a money path stricter** — precisely what `read-model.ts:54-56` reserves for "its own
  slice with its own review". That note is honoured, not overridden: this *is* that review, and the
  change is landing with the guard the note's own sibling path already uses.
- ⚠ **NOT VERIFIED — the one-time regeneration wave.** Every *already-drifted* document (envelope
  `sourceMdHash` present and not matching its current body, for any reason — the `model-store.ts:84`
  clobber, a prose-only resummarize) becomes stale the moment this ships, and pays ~6¢ on its next
  owner serve. **Bounded**: once per document, never recurring, and each one is a document that has
  been silently serving wrong gists. **Unmeasured**: the population size is unknown.
  **Plan task — measure before shipping**, read-only via `claude_ro`: count envelopes whose
  `sourceMdHash` is present and differs from the current body hash. If that number is large, the
  rollout is staged rather than the design changed.
- Legacy envelopes with **no** `sourceMdHash` are untouched — absent means *cannot prove stale*, so
  nothing mass-invalidates.

**Bonus, not scope creep:** this fixes the whole staleness class, not the corrections instance of it —
including the clobber `model-store.ts:79-85` accepted specifically because it would be *"visible in
production rather than inferred."*

**`app/api/videos/[id]/regenerate/route.ts`** — gains a real cloud branch. It cannot execute under
Supabase today: the panel sends `outputFolder` (`CorrectionsPanel.tsx:52`), the route rejects its
absence (`:20-21`) and calls `getPrincipal(outputFolder)` (`:30`), and `getStorageBundle()` at `:36`
throws without a client — **outside the try block**, so it 500s rather than returning an error.

The cloud branch: `?playlist=<uuid>`, `createServerSupabase`, `getUser`, `resolveOwnedPlaylistKey`,
`getPrincipalFromSession`, `getStorageBundle({ supabaseClient })`; rejects `outputFolder` in cloud
mode; the resolution moves **inside** the try.

⚠ **How the corrected body is written back — `put`, NOT `writeArtifact` (r4 B2).** v3 enumerated
everything the cloud branch gains and never named the one line it most needs to replace:
`fs.promises.writeFile(mdPath, …)` at `route.ts:69`. That silence is not neutral, because this repo
has an established convention for writing a `summaryMd` artifact and **it is the wrong one here**:

> `writeArtifact` (`lib/storage/supabase/consistency.ts:15`) runs
> `putStaged → verify → committed → promote → promoted`, and `promote` is **create-if-absent**
> (`supabase-blob-store.ts:120-123`: *"if final already present, ensure temp gone and return"*). A
> correction never changes the key — `base` derives from the persisted `video.summaryMd`
> (`serve-summary-core.ts:71`) and the structural validator above **pins the headings** — so the final
> object **always** already exists. `promote` would delete the corrected temp, return success, and
> leave the original document in place while the card describes the corrected one.

**Requirement:** the corrected body is written with `blobStore.put` (upsert, `blob-store.ts:69`).
One line of reasoning goes in the code: *the object exists by construction, so create-if-absent would
discard the correction.*

⚠ **A server-side length cap on `corrections`, rejecting with 400.** Today `:24-26` validates the
*type* and nothing else; the 1,000-char limit lives in the browser (`CorrectionsPanel.tsx:105`) and
§5.3 already concedes the route is reachable by any authenticated client. Corrections are therefore
the **only unbounded input to a paid call** — a 200 KB blob is a real request. The cap is the
client's 1,000, enforced where it binds.

**DECIDED here, not deferred to the plan (r4 M5) — the two halves are not independent.**
`sync-run.ts:358` writes `corrections` through `updateVideoAnnotations` with **no length check**, and
the local index caps nothing, so **a >1,000-char value can already exist** and can arrive from a local
replica after this ships. v4 framed "cap here or also at sync" as two free choices; it is one coupled
choice, and getting it wrong strands a row.

> ⚠ **CORRECTED (r4 H5).** An earlier draft of this paragraph also named
> `app/api/videos/[id]/review/route.ts:147` as a corrections writer. **It is not.** `:147` calls
> `updateVideoAnnotations`, but `validateBody` (`:16-18`) admits only `personalScore` and
> `personalNote`, and the `set`/`clear` at `:135-145` are built from those two alone. **The complete
> set of `corrections` writers is two:** `regenerate/route.ts:56,58` and `sync-run.ts:358`. Enumerating
> them is what §4.3 depends on, so the error mattered beyond this sentence.

> **The cap applies to the incoming request only.** Enforcing it at the `updateVideoAnnotations` seam
> would make a *sync* fail on data it did not create — worse, and slice B/C territory.
> **An already-long stored row is not bricked:** the 400 names the limit and the actual length, and
> because the panel's field is editable the user shortens it in place and presses again. §7 asserts
> this case — a route-level test will not generate it by itself, since the panel caps what it sends.

**`components/CorrectionsPanel.tsx` / `VideoMenu.tsx`** — reachable in cloud mode, scope-aware body,
and the §6 discriminator rendered.

---

## 3. When it runs

```
fixSummary runs  ⟺  the request's corrections are non-empty after trimming.
```

Exactly today's guard at `route.ts:63`. **The apply input is the request's corrections; the stamp
input is the `:77-79` effective value. They are different quantities and this spec never uses one
word for both** — v3's thesis sentence conflated them and would have reinstated a paid bare press.

**`extractQuickView` runs either way**, as at `:66` today. Removing it on a bare press would delete
the local quick-view refresh; **18 tests across `tests/api/regenerate.test.ts` and
`tests/lib/cloud-sync/regenerate-stamp.test.ts` cover this path** (2 suites, 18 tests — counted, not
estimated; v2 said two and v3 said seven, both wrong).

---

## 4. Write hygiene

| Field | On a press with no corrections |
|---|---|
| `tldr`, `takeaways`, `summaryHtml` | **updated** — quick-view runs; today's behaviour |
| `mdCorrectionsHash` | ⚠ **left untouched — do NOT recompute. See §4.3** |
| `mdGeneratedAt` | ⚠ **must not move** — the body did not change. `deriveClassASignals` (`backfill.ts:13`) feeds it to the recency tiebreak; a false stamp lets an unchanged cloud body beat a newer local one |
| `annotationsEditedAt.corrections` | ⚠ **only when the corrections text actually changed.** Today `:54-59` writes on every non-empty or explicit-clear request; a no-op press must not beat a real remote edit in Class-B reconciliation |
| **`updated_at`** | ⚠ `merge_video_data` bumps it unconditionally (`0021:89`), and `deriveHumanSnapshot` reads `updatedAt ?? processedAt` (`backfill.ts:22`), so a metadata-only write can make an old `personalNote` look newly edited |

### 4.1 The clear surface exists. The `updated_at` unknown does NOT dissolve — a trigger settles it the other way

v3 left two holes here — *"use a narrow RPC that does not bump `updated_at`"* and *"use the store's
own clear surface, named in the plan"*. **This section claimed both were the same already-built call.
Half of that was right.**

> ⚠ **CORRECTED at round 4 (r4 B1).** The earlier claim — *"`update_video_annotations` writes only the
> `data` column, so nothing bumps `updated_at`"* — is **wrong**, and both review halves of round 3 plus
> the Codex half of round 4 confirmed it wrongly. The function is clean; the **table** is not.
> `0015_video_updated_at_trigger.sql:13-14` installs a row-level trigger underneath every RPC:
>
> ```sql
> create trigger trg_videos_updated_at before update on videos
>   for each row execute function set_videos_updated_at();   -- new.updated_at = now()
> ```
>
> Its own header says the inline `updated_at = now()` at `0021:89`/`:149` is *"idempotent alongside"*
> it — **redundant, not the mechanism**. `grep -rn trg_videos_updated_at` returns only 0015; nothing
> later drops it. **No write to a `videos` row in this schema can avoid moving `updated_at`.**
>
> **The error was not a wrong line number — it was a wrong question.** Reading the function answers
> *"does this statement set the column?"*. The question that mattered was *"what else touches this
> table?"* No citation check catches that, in either direction.

**This is decided, not open — see §4.2.** The rest of this section stands as measured.

`update_video_annotations` (`0021:19-56`) writes only the `data` column *in its own statement*. Its
typed surface is
`updateVideoAnnotations(p, videoId, set, clear, opts?)` — `metadata-store.ts:73`,
local `local-metadata-store.ts:125`, cloud `supabase-metadata-store.ts:269`. It is
`security invoker` with `owner_id = auth.uid()` and returns `{ found }`; the route 404s on
`found: false`. So:

- **Write** corrections with `updateVideoAnnotations(p, id, { corrections }, [])`.
- **Clear** with `updateVideoAnnotations(p, id, {}, ['corrections'])`. This replaces
  `updateVideoFields(p, id, { corrections: undefined })` (`route.ts:58`), which is a **no-op on
  Supabase** — `undefined` is dropped by JSON serialization — after which the route stamps
  `mdHash('')` over a row that still holds corrections.

⚠ **The stamp is unconditional in both directions and on both backends**, so the *caller* owns the
"only when it changed" rule — the store cannot. Supabase stamps on set (`0021:35`) and on clear
(`:41-43`); local does both through one `changed` array (`local-metadata-store.ts:139-159`). Read the
stored value first and **issue no call at all** when it already equals the incoming one — including
the clear-an-already-empty case, which would otherwise stamp an edit that did not happen.

Test against both backends; they agree here, and a test that only proves it on one proves nothing
about the seam.

### 4.2 DECIDED — slice A accepts the `updated_at` bump, and says so out loud

The choice is not between three options, because **two of them are not reachable from slice A**:

| Option | Verdict |
|---|---|
| (a) Accept the bump; document and assert the consequence | ✅ **chosen** |
| (b) Stop `deriveHumanSnapshot` treating `updatedAt` as an annotation-edit proxy | A **sync-semantics** change with its own review. Not slice A |
| (c) Make the trigger conditional, or add a column | A **migration**. Not slice A |

**And (a) is forced, not merely preferred.** §3 makes `extractQuickView` unconditional, so *every*
press — corrections or not — writes `{ tldr, takeaways, summaryHtml: null }` through
`updateVideoFields` → `merge_video_data`, which sets `updated_at = now()` explicitly at `0021:89`
*and* fires the trigger. **No choice of corrections-write surface can avoid the bump**, so it is not a
consequence of this design; it is a property of pressing the button at all, and it is true on `master`
today.

**The consequence, named rather than buried.** `deriveHumanSnapshot` (`backfill.ts:22`) computes
`provisional = video.updatedAt ?? video.processedAt` and uses it as the `editedAt` for every Class-B
field lacking a real `annotationsEditedAt` entry. So after a press, a **never-edited** `personalNote`
on the cloud row carries a fresh provisional timestamp and can beat a genuinely newer local edit in
Class-B reconciliation. **The blast radius is bounded to rows with `backfilled: true` entries** — a
field with a real `annotationsEditedAt` is unaffected, because `real ?? provisional` prefers the real
one.

§7 carries the row that would fail if this got worse. **§8's "no migration of any kind" bullet is
withdrawn** — see §8.

### 4.3 A bare press must NOT recompute `mdCorrectionsHash` — today it does, and that is defect (a)

Round 4's Codex half noticed §7 omitted `mdCorrectionsHash` from its "nothing moves" list. Following
that into the code found something neither reviewer raised in four rounds.

```ts
// route.ts:77-79 — the stamp input
const effectiveCorrections = trimmedCorrections
  ? trimmedCorrections
  : corrections === '' ? '' : (video.corrections ?? '');   // ← bare press: the STORED value
// route.ts:88
mdCorrectionsHash: mdHash(effectiveCorrections),
```

On a **bare press** `fixSummary` never runs (`:63`), yet `:88` stamps the hash of the **stored**
corrections. If the row was corrections-*stale*, one press flips it to *current* **with no Gemini call
and no change to the body.** `mdCorrectionsHash` is the sole input to `reconcileClassA`'s currency
predicate (`reconcile-class-a.ts:8`), so sync then believes the document reflects corrections it has
never seen.

**That is backlog #23's defect (a) — the row claims corrections it never applied — reachable on the
ATTENDED path, in code that ships today.** #23 attributes it exclusively to a fresh summarize.

The comment at `:74-76` states its own assumption in the open: *"a bare regenerate keeps prior
corrections baked in, so stamping `mdHash('')` there would wrongly mark a still-corrected MD as
stale."* True while this route is the only way corrections reach a row. **Sync breaks it** — and sync
is the world slice A ships into.

**The mechanism, enumerated (r4 H5).** There are exactly **two** writers of `corrections`:

| Writer | Regenerates the MD? | Touches `mdCorrectionsHash`? |
|---|---|---|
| `regenerate/route.ts:56,58` | yes | yes (`:88`) |
| **`sync-run.ts:358`** — Class-B reconciliation | **no** | **no** — the `mdCorrectionsHash` references in that file (`:317`, `:402`, `:523`, `:542`) are all on Class-A paths |

So the loss is not hypothetical and not a slip:

1. The user edits corrections **C1 → C2** locally. No regenerate.
2. Sync writes **C2** to the cloud row (`sync-run.ts:358`) and does **no** MD work.
3. `reconcileClassA` correctly reports **`needsRegen: true`** — the body reflects C1.
4. **One bare press stamps `mdHash(C2)`** → `needsRegen: false`, **permanently**. Nothing ever
   re-derives currency from the body, so C2 is never applied and never flagged again.

**Two ways to reach step 4, and neither is a fat finger.** The panel sends the **raw** textarea value
(`CorrectionsPanel.tsx:52` — `JSON.stringify({ outputFolder, corrections })`, no trim), so
select-all + space sends `"  "`, which trims to falsy. And §5.3 already concedes any authenticated
client can POST `{ outputFolder }` with no `corrections` key at all.

⚠ **Severity: Blocking for slice A, though the `:77-79` rule pre-dates it.** On `master` the defect is
dormant on cloud — `VideoMenu.tsx:181` gates the panel out of cloud mode and the route 500s there
anyway, so a sync-delivered pending correction has no cloud press to extinguish it. **Slice A is what
supplies the press.** It converts a dormant local edge case into live data loss on the cloud.

⚠ **And the r3-H6 fix installed a §7 row this defect PASSES.** That row asserts `needsRegen` goes
true → false after a correction; step 4 produces exactly that transition. Round 3 replaced a falsifier
a *correct* implementation failed with one the *defect* satisfies — a fix that moved the blind spot
rather than closing it. §7 now carries the row neither version could express.

> **Requirement.** Write `mdCorrectionsHash` **only when `fixSummary` ran**, as
> `mdHash(request corrections)`. On a bare press, omit the field entirely: the stored value already
> describes what the body reflects, whatever that is. `:77-79` tries to *derive* the truth; leaving it
> alone *preserves* it, and needs no assumption.

⚠ **Explicit clear is unchanged and remains imperfect.** Clearing stamps `mdHash('')` while the body
may still carry previously applied corrections — there is no un-apply short of regenerating from
source. Accepted as today's behaviour; **not** introduced here, and out of scope for A.

---

## 5. Money — capped, recorded, not reserved

**5.1 Caps.** `fixSummary` gains `maxOutputTokens`, `thinkingBudget: 0` and `signal`, **applied
through `withCaps`** (`gemini.ts:36`). v3 said "mirroring `generateJson`"; in fact `generateSummary`
builds a capped model via `withCaps` at `:326` and passes it in — `generateJson` has no cap parameters
of its own.

> ⚠ **Pass a `CloudGeminiCaps` OBJECT, not just the constant (r4 H3).** `withCaps` decides *whether to
> cap at all* from its **second** argument, not its third:
>
> ```ts
> // lib/gemini.ts:41
> if (!caps) return base;   // the local pipeline, unchanged — by design
> ```
>
> v4 named `MAX_SUMMARY_OUTPUT_TOKENS` and never named a caps object, so an implementer could write
> `withCaps({…}, opts?.caps, MAX_SUMMARY_OUTPUT_TOKENS)`, have nothing construct `opts.caps`, and ship
> an **uncapped** call with thinking enabled — while the diff reads correct. The correction path
> constructs or imports a `CloudGeminiCaps` with `summaryOutputTokens: MAX_SUMMARY_OUTPUT_TOKENS`
> (8192, `gemini-cost.ts:16`), shaped like `SERVE_CAPS` (`serve-doc.ts:30`), and passes **that** as
> argument two. On the **local** branch `caps` is absent by design, so §7's bounded-run row is a
> **cloud-only** assertion.

⚠ **The cap is not justified by "a corrected document cannot need more output than a generated one"
(r4 H4) — that sentence is deleted.** It is false twice: `MAX_SUMMARY_OUTPUT_TOKENS` bounds
`generateSummary` only when caps are present, and the **local pipeline passes none**; and cloud-side
it bounds a *JSON response* (summary + ratings + tags), whereas `fixSummary` emits the **assembled
markdown** — H1, frontmatter and rendered `▶` lines the pipeline adds after generation.

**Kept at 8192 anyway, with the refusal made explicit.** Documents measured in this repo sit far
below it, and raising the ceiling is a money decision belonging to slice C. **The consequence must be
stated rather than discovered:** a large locally-generated summary — synced to the cloud, which is the
whole point of Stage 3 — can exceed the preflight and be **permanently uncorrectable**.

> **Requirement.** Over-cap input returns **HTTP 413** with a distinguishable error code, before any
> Gemini call. The panel shows *"This summary is too long to correct"* rather than a generic failure.
> §7 asserts that a local-origin over-cap document produces **that** response and not a 500 — a row
> that would otherwise read green while the feature is silently refused.

⚠ **Preflight before the first call.** `fixSummary` retries twice on truncation (loop at `:494-508`),
so an over-cap document would cost three full passes and then throw. Check the input against the cap
first and fail before paying. **The preflight has its own timeout and its own row in §5.4** — the
repo's only precedent (`assertMagazineInputWithinCap`, `gemini.ts:77-101`) is a `countTokens`
**network round trip**, not a local estimate.

⚠ **`thinkingBudget: 0` is a quality risk on this task — NOT VERIFIED.** Live gates exist for its
billing behaviour (`tests/integration/gemini-live-gates.test.ts`), nothing for correction quality.
Run a fixture eval before enabling.

⚠ **A correction has a SECOND, deferred cost that lands on a later request.** §2's option (e) makes a
corrected document's magazine model stale, so the next **owner** serve regenerates it — ~6¢, once per
correction, on a request this route never sees. §1's ≈0.6¢ is the *correction's* cost, not the
*correction's total* cost, and §5.2's post-hoc recording cannot observe the second half. Both numbers
are real; neither is the whole. §7 asserts the deferred charge fires **once** and not repeatedly.

**5.2 Post-hoc recording, no reservation.** The route records **actual** spend to the ledger after the
call returns. No reserve RPC, no settle semantics, no idempotency key, no `correction_est_cents`.

**Why this and not full metering:** a reservation protocol is what makes this a money-path slice, and
this repo's record for those is five to seven rounds. Recording gives the guardrails visibility —
the daily cap and per-owner budget see the spend on the *next* decision — for a fraction of the work.

⚠ **The accepted risk, named rather than buried:** one un-preauthorised call per press. It is bounded
by the §5.1 cap, attributable to an authenticated user action, and visible in the ledger immediately
afterwards. It is **not** pre-authorised, so a burst can exceed a cap before the cap sees it. If the
ledger shows that happening, slice C exists.

**5.3 No lease.** Duplicate presses converge on the same content; the cost is duplicate spend, now
visible. The route is reachable by any authenticated client once cloud-enabled — the panel's disabled
button is not the bound.

**5.4 `maxDuration = 420`** (7 minutes), stated here rather than deferred. Derivation — **two** Gemini
phases, not one:

| Phase | Attempts | Per attempt | Backoff | Worst |
|---|---|---|---|---|
| **`countTokens` preflight** (r4 M2) | 1 | **10 s, stated not inherited** | — | 10 s |
| `fixSummary` | 3 (`retries = 2`, `gemini.ts:473`) | 60 s (`:105`) | 400 + 800 ms (`:505`) | 181.2 s |
| `extractQuickView` → `generateJson` | 3 (`GENERATE_JSON_RETRIES = 2`, `gemini-cost.ts:22`) | 60 s | 400 + 800 ms (`:281`) | 181.2 s |
| | | | **Total** | **372.4 s** |

⚠ **v4's table omitted the preflight and its own §5.1 required one.** Two sections written in one pass
that did not know about each other. Inheriting `REQUEST_TIMEOUT_MS` by accident would make it 60 s and
the worst case **422.4 s — over the 420 s budget**. Hence the explicit 10 s: it is a token count, not
a generation. 420 s now leaves ~48 s for the blob read, the blob write and the metadata RPC.

⚠ **`maxDuration` bounds THE WORK, not THE REQUEST, and on this deployment nothing enforces it
(r4 M1).** Next's own docs call it an output annotation — *"Deployment platforms **can** use
`maxDuration` from the Next.js build output"* — and this app ships `output: 'standalone'`
(`next.config.ts:11`) running `node server.js` under Fly, where no adapter consumes it. Keep
`export const maxDuration = 420`: it is correct-by-portability and free. **The 1800 s precedent
sentence is deleted** — `app/api/quick-view/backfill/route.ts:10` is inert for the identical reason,
so it was evidence that the repo has *written* 1800 somewhere, not that a long request survives.
**NOT VERIFIED:** what actually bounds the request in prod (Fly proxy / idle timeouts, client `fetch`
timeouts). That measurement is a plan task.

---

## 6. The outcome discriminator

The route returns `applied` or `no-corrections`, and the panel reports it, so a press that changes
nothing does not read as a bug.

---

## 7. Falsifiers

Assert at the consumer.

| Claim | Consumer | Assertion |
|---|---|---|
| Cloud correction works | the stored blob | POST → holds corrected text, not the original |
| …and the card | `tldr`, `takeaways`, **and the Concepts line** | all three reflect the corrected document |
| Empty corrections cost nothing in `fixSummary` | the ledger | no `fixSummary` charge; quick-view still runs |
| A run is recorded | the ledger | moves by the **actual** spend, after the call |
| A run is bounded | the request to Gemini | `maxOutputTokens` and `thinkingBudget` present; over-cap input rejected **before** any call |
| Structure survives | the parsed document | H2 sequence and `▶` tuples byte-identical pre/post |
| …and the reader sees the correction | the **served magazine HTML** (owner) | after a correction the owner serve regenerates and the HTML contains **corrected gists**, not the cached ones. Mutation-check it: revert the `sourceMdHash` conjunct and this must fail |
| …without breaking the share link | the **anonymous `/s/<token>` render** | still returns **200 with a readable page** immediately after a correction — `readTitleStableModel` is untouched. **This is the row that fails if anyone reintroduces the delete** |
| …and without breaking the over-budget path | `serve-doc.ts:147-151` | with the owner budget exhausted **and** a corrected body, the stale-but-readable render is still served, not a 503 |
| A legacy envelope is not invalidated | the owner serve | an envelope with **no** `sourceMdHash` serves from cache and **moves no money** — absent means *cannot prove stale* |
| The correction path writes no envelope | the blob store | after a correction, `MODEL_KEY(base)` is **byte-identical** — invalidation is derived, and a write here would mean the read-modify-write design crept back |
| The deferred charge is real and bounded | the ledger | the next owner serve of a corrected doc moves ~6¢ **once**; a second serve moves **nothing** (guards against a regenerate loop — both writers build fresh envelopes, `serve-doc.ts:174-182`, `generate.ts:50-60`) |
| An **applying** press makes the row current | the **sync decision** | `reconcileClassA`'s `needsRegen` goes **true → false**. **Fails if the stamp is missing** |
| ⚠ A **bare** press does NOT | the **sync decision** | on a video whose `needsRegen` is `true` — corrections delivered by `sync-run.ts:358`, body never regenerated — a bare press leaves it **`true`**. **This is the row neither r3 version could express, and the row the r3-H6 fix let the defect pass.** Reach the press both ways: whitespace-only (the panel sends the raw value, `CorrectionsPanel.tsx:52`) and a POST with no `corrections` key |
| A no-correction press disturbs nothing | the **sync decision** | **all six `ClassASignals` fields** (`backfill.ts:8-16`) byte-identical before and after: `summaryMdKey`, `mdHash`, `docVersionMajor`, `mdGeneratedAt`, **`mdCorrectionsHash`** (§4.3 — it must NOT move), `backfilled`. Plus every `annotationsEditedAt` entry |
| …and the one thing it **does** disturb is bounded | `deriveHumanSnapshot` | `updatedAt` moves (§4.2, unavoidable). Assert the blast radius: a field **with** a real `annotationsEditedAt` is unaffected; only `backfilled: true` fields take the new provisional. **This is the row that fails if §4.2's acceptance stops holding** |
| An oversized corrections field never reaches Gemini | the route | rejected 400 **before** any call; no ledger movement |
| An already-long stored value does not brick the button | the route + panel | a row holding >1,000 chars from sync/local yields the §2 error path, not a 500 — and the panel says how to clear it |
| An over-cap document refuses cleanly | the route | a **local-origin** (uncapped-pipeline) summary above the preflight returns **413** with its own code, not 500, and no Gemini call |
| Clearing works on Supabase | the stored row | corrections actually absent afterwards, both backends; and clearing an already-empty field issues **no call**, so the stamp does not move |
| Abort works | the in-flight call | aborting mid-correction cancels it rather than paying to completion |
| Local is unchanged | **18 tests, 2 suites** | all pass unmodified |

**Negative tests assert which error.** Slice A adds **no** assertion about unattended behaviour — that
is slice B's, and backlog #22's `it.failing` tripwire
(`summary-handler-promote-divergence.test.ts:148`) already owns the scenario.

---

## 8. Out of scope

- The unattended path — **slice B**, backlog #60.
- Reserve/settle, `correction_est_cents`, the `cap-soundness` extension, the duration ratchet —
  **slice C**, backlog #61.
- `{from,to}` pairs — rejected with reasons.
- The occurrence check the user originally asked for — §1.2.
- **Regenerating the magazine model inside the correction request.** §2's option (e) invalidates;
  the *regeneration* happens on the next owner serve, through the existing paid path. Doing it
  in-request was option (c) and blows §5.4's budget.
- **`readTitleStableModel` and the share path** — deliberately untouched by (e), which is the point
  of it. Anything that changes what an anonymous visitor sees belongs to backlog **#57**, not here.
- **No migration — but on a narrower argument than v4 gave (r4 B1).** v4 said *"§4.1 settles it —
  `update_video_annotations` already excludes `updated_at`"*. **That premise was false**, and §4.1 now
  carries the correction. The conclusion survives on a different footing: §4.2 **accepts** the
  `updated_at` bump, and the only options that would need a schema change — a conditional trigger or a
  new column — were rejected as out of slice A. So: no schema change and no data migration, **because
  a consequence was accepted**, not because it does not exist. A reader deciding whether the plan needs
  a migration gets the same answer; a reader deciding whether `updated_at` is safe gets the opposite
  one, and that is the reader v4 would have misled.
- **Ordering against append-only M1** (r3 M8 first half). M1 is the other plan that would write
  `mdCorrectionsHash` through `persist_summary`, and two specs writing one field need an order. It is
  ⛔ **RE-SCOPED AND DEFERRED** (`docs/superpowers/plans/2026-08-22-append-only-generations-roadmap.md`),
  and the field it contends over is written on the **unattended** path — slice B's. No ordering
  constraint binds slice A. If M1 is revived before B ships, that changes.

## 8.1 Named gaps — decisions for the plan, not oversights (r4)

1. **The corrected-body READ.** §2 replaces `fs.promises.readFile` (`route.ts:50`) only implicitly.
   The cloud read must be a **proving** read: `serve-summary-core.ts:66-67` returns *409 repair
   needed* rather than treating an unreadable MD as absent, and the same discipline binds here. A
   failed blob read must never become *"empty document — correct it anyway"*. (This is the repo's
   measured `rls-denial-is-indistinguishable-from-absence` hazard on a paid path.)
2. **`summaryHtml` in cloud.** `route.ts:86` writes `summaryHtml: null`. Whether the cloud branch does
   the same, and whether a rendered-HTML blob needs invalidating too, is unstated. ⚠ **§2's (e) does
   NOT cover it** — (e) derives *model* freshness from `sourceMdHash`; a separately cached rendered
   HTML has no such tie to the body, so if one exists in cloud it can go stale in exactly the way (e)
   just fixed for the model. The plan establishes whether a cloud rendered-HTML cache exists at all
   before deciding — this is a "what else touches this?" question of the kind that produced both of
   round 4's Blockings.
3. **What the panel shows for each new failure class** — structural-validation throw, 413 over-cap,
   400 over-length, abort. §6's discriminator covers `applied` / `no-corrections` only.

## 9. Follow-ups

1. Correct backlog #23 per §1.1; record the representation clause as rejected and §1.2 as descoped.
2. Move a summary fixture into the repo — the size row cited a path **outside the repo**. It was
   reproducible on this machine and round 2 reproduced it to the digit; the problem is portability,
   not correctness. (v3 said "unreproducible", which overstated it.)
