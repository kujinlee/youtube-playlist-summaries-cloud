# Adversarial review — corrections-in-cloud **slice A**, round 5 (Claude half). SCOPED.

Subject: `docs/superpowers/specs/2026-08-22-corrections-in-cloud-design.md`, the block headed
`#### ✅ DECIDED 2026-08-23 (user) — option (e)`, plus the §5 and §7 rows that depend on it.
Change under review: commit `9eb11d2`. Nothing outside that block is filed.

**Counts: 1 Blocking, 3 High, 5 Medium, 3 Low.**

**Top line.** (e) is the right shape. Deriving invalidation from `sourceMdHash` instead of inventing a
marker is correct, the polarity matches `decideCompanion` exactly, and "the correction path writes
nothing" genuinely dissolves four questions rather than deferring them. The design is better than (a),
(b) and (d), and I would not send it back on its choice.

I am sending it back on **one thing it did not check about its own oracle**, and it is the question
the brief asked me to attack hardest.

> **B, answered.** `mdHash` is *deterministic* — `canonicalizeMd` (`lib/cloud-sync/content-hash.ts:9-13`)
> folds CRLF, trailing newlines and NFC, and both writers hash the same object: the raw decoded blob
> (`generate.ts:34,59`; `serve-doc.ts:181` ← `serve-summary-core.ts:99` `mdBytes.toString('utf-8')`).
> Two serves of an **unchanged document** produce the same hash. There is no normalisation loop and no
> charge loop from that direction. ✅
>
> **But the document does not stay unchanged.** `route.ts:66-69` rewrites the body on **every** press,
> including a bare one, re-inserting a quick-view callout built from a *fresh, non-deterministic*
> `extractQuickView`. The bytes move, so the hash moves, so under (e) a press that applied nothing
> invalidates the model and books a deferred ~6¢. **B1.**

## What I executed

| Command / read | Result |
|---|---|
| `git show 9eb11d2` | spec only, +113/−58 ✅ |
| `grep -rn "isFresh\|readFreshMagazineModel\|sameTitles"` over the **whole tree** (tests, e2e, scripts) | production claim ✅; **4 test sites the grep of `lib/`+`app/`+`components/` could not see** — H2 |
| read `lib/cloud-sync/content-hash.ts` in full | `canonicalizeMd`: LF + single trailing `\n` + NFC. Hash is stable for identical logical content ✅ |
| read `lib/html-doc/generate.ts:30-60`, `serve-summary-core.ts:99-115`, `serve-doc.ts:174-182` | both writers hash the **raw decoded blob**; no spread in either literal ✅ (the lead's no-charge-loop claim is correct) |
| read `lib/html-doc/serve-summary-core.ts:118-124` | `busy` / `attempts_exhausted` / `at_capacity` → **503, no stale fallback** — H1 |
| read `supabase/migrations/0012_serve_model_charge.sql:10-13, 21, 59-65, 74-87` | attempts are **per (owner, doc, UTC day)**, K = `max_serve_attempts` default **5**, **each attempt charged** — M5 |
| read `lib/cloud-sync/companion.ts:98-153` in full | polarity matches (e) ✅; **branch 4 deletes receiver envelopes** — H3 |
| `grep -rn sourceMdHash tests/` | **no fixture sets it** — the suite passes unchanged under the new conjunct — M1 |
| `git log -S sourceMdHash -- lib/html-doc/model-store.ts` → `c591603` **2026-07-17**; `git log -- lib/html-doc/constants.ts` → `e6470ad` **2026-07-10** | `GENERATOR_VERSION` has **not** bumped since `sourceMdHash` began being written — no repo-side bound on the wave exists — M3 |

**NOT VERIFIED / not run:** the unit suite (I reviewed a document; the tree is unchanged). The size of
the drifted-envelope population — that needs the database, and M3 explains why no repo-side proxy
substitutes.

---

## Blocking

### B1 — a **bare** press moves the body hash, so (e) charges ~6¢ for a press that applied nothing — and §7 asserts the opposite of what the code does

**Where.** §2's (e) block ("What it costs, stated honestly", first bullet); §5.1's new ⚠ paragraph;
§7's row *"A no-correction press disturbs nothing"*. Code:
`app/api/videos/[id]/regenerate/route.ts:62-69`, `lib/cloud-sync/backfill.ts:8-16`.

The route rewrites the markdown on **every** press, whether or not a correction was applied:

```ts
// app/api/videos/[id]/regenerate/route.ts:62-69
const stripped = stripQuickViewCallout(mdContent);
const fixed = trimmedCorrections ? await fixSummary(stripped, trimmedCorrections) : stripped;

// Re-extract tldr/takeaways from corrected content and re-insert callout
const { tldr, takeaways } = await extractQuickView(fixed);
const updatedContent = insertQuickViewCallout(fixed, tldr, takeaways, video.tags ?? []);

await fs.promises.writeFile(mdPath, updatedContent, 'utf-8');
```

On a bare press `fixed === stripped` — the prose is untouched — but `extractQuickView` is an **LLM
call**, run unconditionally and by §3's explicit requirement (*"`extractQuickView` runs either way, as
at `:66` today"*). Its `tldr`/`takeaways` are not required to be, and in general will not be,
byte-identical to last time. `insertQuickViewCallout` splices them back into the document, so
`updatedContent` differs from `mdContent`, and the callout is **inside the hashed region** — nothing
strips it before hashing on either write path (`generate.ts:34,59` hashes the whole decoded blob;
`serve-doc.ts:181` hashes `mdBody`, which `serve-summary-core.ts:99` derives as
`load.mdBytes.toString('utf-8')`).

**Failure scenario.** A cloud user opens the corrections panel on a document with no corrections,
changes nothing, and presses the button — or a client POSTs `{outputFolder}` with no `corrections`
key (§5.3 concedes this is reachable). No `fixSummary` call, so §7's *"Empty corrections cost nothing
in `fixSummary`"* row passes and the ledger row passes. But the body is rewritten with a different
callout; the stored `sourceMdHash` no longer matches; under (e) `isFresh` returns false on the next
**owner** serve; `resolveMagazineModel` reserves and pays ~6¢ to regenerate a magazine model for a
document whose prose is identical to the one the old model was built from. Repeat the bare press,
repeat the charge — it is **once per press**, not once per correction.

**And the spec contradicts itself about it, in two adjacent sections.**

- §4's write-hygiene table, row 1: `tldr`, `takeaways`, `summaryHtml` → **"updated — quick-view runs;
  today's behaviour."**
- §7, the row folded in at round 4: *"A no-correction press disturbs nothing … **all six
  `ClassASignals` fields** (`backfill.ts:8-16`) byte-identical before and after: `summaryMdKey`,
  **`mdHash`**, `docVersionMajor`, `mdGeneratedAt`, `mdCorrectionsHash`, `backfilled`."*

`deriveClassASignals` computes `mdHash: mdBody != null ? mdHash(mdBody) : null`
(`backfill.ts:11`) — the **body** hash. So §7 asserts the body is byte-identical after a bare press
while §4 asserts the quick-view fields it splices into that body are updated. Both cannot hold. Before
(e) this was a bookkeeping inconsistency that would surface as a spurious sync `copyTo*`. **Under (e)
it is a money defect**, because the same hash now gates a paid regeneration.

**Why Blocking.** It falsifies the one number the (e) block was careful to state honestly ("~6¢, once
per correction"), it breaks §7's new *"the deferred charge is real and bounded"* row, and it makes the
spec's own *"Empty corrections cost nothing"* claim false end-to-end — the press costs nothing
*in `fixSummary`* and ~6¢ *in the magazine*. A reader who checks the ledger falsifier sees green.

**Suggested fix.** Pick one and say which:

1. **Skip the body write when nothing changed.** After building `updatedContent`, compare
   `mdHash(updatedContent) === mdHash(mdContent)` and skip the blob write when equal. Cheap, exact,
   and it makes §7's byte-identical row *true* instead of aspirational. Note this does **not** require
   skipping `extractQuickView` — §3's requirement survives; only the write is conditional. It also
   means a bare press whose quick-view happens to be identical costs nothing at all.
2. **Make the callout deterministic-or-preserved on a bare press** — reuse the stored `tldr`/
   `takeaways` when `fixSummary` did not run, so the spliced bytes are unchanged by construction.
3. **Accept it and re-state the cost**: "~6¢ per *press*, not per correction", and delete `mdHash`
   from §7's byte-identical list. This is the weakest option — it prices a no-op at 6¢ — but it is
   honest, and it is better than the current state where two rows disagree.

Whichever is chosen, add the §7 row that does not exist: **a bare press moves no deferred money.**

---

## High

### H1 — (e) takes the owner's own page out of the unconditional-200 path and into a state machine with five 503s and only one fallback

**Where.** §2's (e) block, the asymmetry table ("only one is strict") and *"the share path and the
over-budget fallback are untouched"*. Code: `lib/html-doc/serve-doc.ts:78-79, 112-151`;
`lib/html-doc/serve-summary-core.ts:118-124`; `supabase/migrations/0012_serve_model_charge.sql:59-87`.

The asymmetry table is correct as far as it goes, and it is why (e) beats (a). But it draws the wrong
boundary. `readTitleStableModel` is consulted in exactly **one** of the reserve path's exits:

```ts
// lib/html-doc/serve-doc.ts:146-151 — the ONLY stale fallback
case 'owner_over_budget': {
  const staleRead = await readTitleStableModel({ blobStore, principal, base, titles });
  return staleRead.status === 'ok' ? { status: 'ok', model: staleRead.model, stale: true } : { status: 'over_budget' };
}
```

Every other non-`reserved` exit returns a bare status, and the mapper turns them all into 503 with no
second look at the bucket:

```ts
// lib/html-doc/serve-summary-core.ts:120-123
case 'busy':               return { ok: false, status: 503, error: 'generating, retry shortly' };
case 'attempts_exhausted': return { ok: false, status: 503, error: 'temporarily unavailable, try later' };
case 'at_capacity':        return { ok: false, status: 503, error: 'at capacity' };
```

`busy` alone has three producers — the unreadable-probe guard (`:115`), a reserve RPC timeout
(`:132`), and losing the single-flight race (`:142`).

**Failure scenario.** Today a corrected document is `isFresh === true`, so `serve-doc.ts:78-79`
short-circuits and the owner gets **200 every time**, forever, with stale gists. That is the bug (e)
fixes. But after (e) the same document falls through to the reserve on every serve until a
regeneration succeeds — and if Gemini is erroring, or the daily cap is hit, or Storage blips, the
owner's own document returns **503 "temporarily unavailable"** while a perfectly readable model sits
in the bucket that `readTitleStableModel` would happily serve. `0012:80` shows `attempts_exhausted` is
reached after K attempts (`max_serve_attempts` default **5**, `:21`) keyed on
`(owner_id, doc_key, day)` (`:13`), so the outage lasts **the rest of the UTC day**, not a moment.

The spec protected the anonymous reader and left the paying owner — the person who just made the
correction — with strictly worse availability than before. That inversion is not named anywhere in the
block.

**Suggested fix.** Either (i) extend the stale fallback to `attempts_exhausted` and `at_capacity` —
same helper, same #57 rationale, and it is the natural completion of the asymmetry argument the block
already makes — or (ii) state the regression explicitly as accepted, and add a §7 row: *"with
regeneration failing, a corrected document still serves a readable page"*, which is the observation
that fails today. Option (i) is a two-line change to `serve-doc.ts` and I would recommend it; note it
is itself a money-path-adjacent change and belongs in the same review as (e), which is this one.

### H2 — the repo contains a **deliberate tripwire test asserting the exact opposite of the requirement**, and the block never mentions it

**Where.** §2's (e) requirement block (*"No other caller exists in `lib/`, `app/` or `components/`"*).
Code: `tests/lib/html-doc/read-model.test.ts:39-51`.

The lead flagged the caller claim as a hypothesis. It is **true for production code** — I re-ran the
grep across the whole tree and `isFresh` has exactly one caller (`read-model.ts:37`) and
`readFreshMagazineModel` exactly two (`serve-doc.ts:78`, `:141`), both inside `resolveMagazineModel`
where `mdBody: string` is required. ✅

What the `lib/`+`app/`+`components/` scope could not see is **one file with four sites**, and one of
them is not a mechanical break:

```ts
// tests/lib/html-doc/read-model.test.ts:39-51
// KNOWN GAP, accepted in the serve-bounding spec §3.5.1 (#46).
it('treats an envelope with a STALE sourceMdHash as fresh when titles match', () => {
  …
  // WHEN THIS GOES RED: someone made isFresh hash-aware. That is a MONEY decision — prose-only
  // edits would then force paid regeneration — so read §3.5.1 before deleting this test.
  expect(isFresh(envelope({ sourceMdHash: 'hash-of-OLD-markdown' }), titles)).toBe(true);
});
```

This is not incidental coverage. It is a **guard the project installed against this exact change**,
naming it a money decision and pointing at the spec that accepted the residual. It is the fourth place
in the tree that says `isFresh` ignores `sourceMdHash` — the block already cites three
(`read-model.ts:54-56`, `model-store.ts:84`, `companion.ts`) and missed the one that is executable.

Note also what the tripwire's comment says the cost is: *"**prose-only edits** would then force paid
regeneration"* — not *corrections*. That is a broader population than the block's cost model, and it
is the same population B1 is about.

The other three sites are ordinary signature breaks: `read-model.test.ts:59, 68, 74` call
`readFreshMagazineModel` without `currentMdHash`.

**Failure scenario.** The implementer makes the change, the suite goes red on an assertion that reads
like a bug, and — with no instruction in the spec — updates it to `toBe(false)`. A designed gate is
retired silently, with no record that the decision it guarded was revisited.

**Suggested fix.** The block must name the tripwire, quote its "WHEN THIS GOES RED" line, and say what
happens to it: it is **inverted deliberately**, and its comment is rewritten to record that #46 §3.5.1's
residual was closed here, by this review, on this date. Retiring a guard is a spec-level act. Also add
the three signature call sites to the plan's task list so they are not discovered as breakage.

### H3 — "nothing is deleted" and "backlog #57 stands" are true of the correction path only; `decideCompanion` already deletes receiver envelopes on the same signal

**Where.** §2's (e) block header (*"nothing is deleted"*), the intro bullet (*"The share path and the
over-budget fallback are untouched, so backlog #57 stands"*). Code:
`lib/cloud-sync/companion.ts:151-153`.

```ts
// lib/cloud-sync/companion.ts:151-153
const provablyStale = receiverModel.kind === 'envelope'
  && receiverModel.envelope.sourceMdHash !== undefined;
if (provablyStale) return { kind: 'deleteReceiverModel', shareNeedsOwnerServe: true };
```

Branch 4 is reached when neither side's envelope matches `winnerMdHash`. So the sync path **already
deletes** a receiver's model envelope on precisely the signal (e) adopts, and already sets
`shareNeedsOwnerServe: true` — the report that exists because a deleted receiver model *"is absent,
not skewed, and still 503s"* (`companion.ts:145-147`, its own words).

**Failure scenario.** A user applies a correction **locally** — the existing local flow, unchanged by
this slice. The local body wins the next Class-A comparison. The cloud is the receiver; its envelope's
`sourceMdHash` is the pre-correction hash, so `receiverMatch` is null; if the sender has no matching
envelope either, branch 4 fires and the **cloud** envelope is deleted. The owner's live share link now
returns `notReady()` — the exact scenario r4 H1 used to rule out option (a), reached by a different
door, with (e) in place.

**This does not change the decision.** (e) is still better than (a): (a) deletes on every correction,
immediately, unconditionally; sync deletes only when a sync runs, only on the receiver, and only on
proof. But the block states its safety property **unconditionally**, and the property is scoped. A
reader deciding a future question from this block ("we established that nothing deletes the envelope")
will be wrong.

**Suggested fix.** Narrow the claims: *"the **correction path** deletes nothing, and (e) adds no new
deletion. The sync path's `decideCompanion` (`companion.ts:151-153`) already deletes a provably-stale
receiver envelope and reports `shareNeedsOwnerServe` — (e) neither introduces nor removes that, and
#57's tolerance is unaffected by this change but is not absolute."* One sentence; it converts an
overclaim into an accurate scoping.

---

## Medium

- **M1 — no existing fixture sets `sourceMdHash`, so the whole suite passes unchanged and proves
  nothing.** `grep -rn sourceMdHash tests/` returns hits only in `read-model.test.ts` (the tripwire),
  `model-store.test.ts:127` (a comment) and `section-identity-after-resummarize.test.ts:108` (a
  comment). Every envelope fixture in `tests/integration/serve-doc-materialize.test.ts`,
  `pdf-cloud.test.ts`, `share-route.test.ts`, `serve-doc-mapping.test.ts`, `tests/e2e/cloud.setup.ts`
  and the rest omits the field, so the new conjunct's `=== undefined` escape hatch makes them all
  fresh exactly as before. That is good news for breakage and **bad news for coverage**: the change
  ships with the existing suite unable to observe whether the conjunct works. §7's new rows must
  therefore specify that their fixtures **set** `sourceMdHash`, and the mutation-check the first row
  already asks for ("revert the conjunct and this must fail") is the only thing standing between (e)
  and a no-op. Say so.

- **M2 — (e) does not fix "the whole staleness class"; the legacy subset is permanently
  un-invalidatable.** The block's closing "Bonus, not scope creep" line claims the class. But an
  envelope with **no** `sourceMdHash` is fresh forever under the new conjunct *and* is deliberately
  kept by `companion.ts` branch 4 (*"Fail-safe-for-money: KEEP those"*). Such an envelope has no path
  back to correctness except a `sourceSections` or `generatorVersion` change. The escape hatch is
  right — mass invalidation would be worse — but the class claim should read *"fixes the whole
  staleness class **for envelopes written since 2026-07-17**; pre-`sourceMdHash` envelopes remain
  unreachable by any invalidation signal."*

- **M3 — brief E: deferring the count is legitimate, but no repo-side bound exists, and I can prove
  it.** The natural hope is that the existing `generatorVersion` conjunct already invalidated
  everything older than the last bump, capping the wave at envelopes written since. It did not:
  `sourceMdHash` began being written in `c591603` (**2026-07-17**), and `GENERATOR_VERSION`'s value
  `'magazine-skim v2'` was last set in `e6470ad`/`18a4b26` (**2026-07-10**, `lib/html-doc/constants.ts`
  has no later commit). So **the version conjunct has invalidated nothing since the hash started being
  written** — every cloud envelope from 2026-07-17 onward is a candidate, and only a database count
  can bound it. The spec should carry that sentence, because "unmeasured" currently reads as "nobody
  has looked", when the accurate statement is "nothing in the repo can measure it, and the one
  mechanism that could have capped it did not fire."

- **M4 — §7's "A legacy envelope is not invalidated" row asserts a fixture, not a population.** Both
  writers set `sourceMdHash` unconditionally today (`generate.ts:59`; `serve-doc.ts:181`'s conditional
  spread is on a now-required param, so it always fires). The only envelopes lacking the field predate
  2026-07-17. The row is a legitimate unit test of the escape hatch, but as written it reads as a
  production guarantee about live data. Reword to *"an envelope fixture with no `sourceMdHash` …"*.

- **M5 — §7's "the deferred charge fires once" holds only on success.** `reserve_serve_model` charges
  **per attempt** (`0012:84-87`), bounded by `max_serve_attempts` (default 5, `:21`) per
  `(owner_id, doc_key, day)` (`:13`). A corrected document whose regeneration keeps failing books up to
  5 charges in a day, less any refunds for positively-not-metered class-A failures
  (`serve-doc.ts:196-199`). The row's "a second serve moves nothing" is true only after a successful
  regeneration. Add the failure arm, or scope the row to the success path explicitly.

---

## Low

- **L1 — the share reader is knowingly stale, and §7 only asserts that it is *served*.** The new row
  *"…without breaking the share link"* asserts a 200 and a readable page. Correct and worth having.
  But under (e) that page shows **pre-correction gists indefinitely** — `readTitleStableModel` ignores
  both `generatorVersion` and `sourceMdHash`, and only an owner serve refreshes it. That is #57's
  decision, not a defect; it should be one sentence in the block so nobody later reads the row as
  "the share is correct after a correction".

- **L2 — two more gist gates ignore `sourceMdHash`, and (e) does not touch them.** `dig-merge.ts:62`
  and `rerender.ts:67` use a *different* `sameTitles` (`rerender.ts:17`, two string arrays) to decide
  whether gists are trusted for rendering. Neither consults the hash —
  `section-identity-after-resummarize.test.ts:108` says so explicitly. They are downstream of a fresh
  envelope so the owner path is fine, but this is the same "what else touches this?" shape the block
  already flags for the rendered-HTML cache in §8.1 item 2. Name them there too, and the answer to
  brief **D** is settled by the same fact: **the local path is unaffected**, because nothing local
  calls `isFresh` at all — local reads envelopes through `rerender.ts` and `dig-merge.ts`. No extra
  local Gemini calls, no re-render loop, no local/cloud divergence introduced.

- **L3 — citation check on the changed block: all correct.** `read-model.ts:20-25`, `:57-69`,
  `:54-56`; `model-store.ts:23`, `:84`, `:79-85`; `serve-doc.ts:78`, `:141`, `:147-151`, `:174-182`,
  `:181`; `serve-doc.ts` `resolveMagazineModel`'s `mdBody` at `:67` and destructured `:70`;
  `generate.ts:50-60`, `:59`; `app/s/[token]/route.ts:102-103`; `companion.ts`'s quoted `provablyStale`
  snippet (verbatim, `:151-153`); `sync-run.ts:358`; `CorrectionsPanel.tsx:52`; `backfill.ts:8-16`.
  One nit: the block quotes `companion.ts` without a line number where every other citation has one.

---

## The brief's questions, answered directly

| | Question | Answer |
|---|---|---|
| **A** | Is the two-caller claim complete? | **For production, yes** — verified across the whole tree, not just `lib/`+`app/`+`components/`. **For tests, no**: 4 sites in `read-model.test.ts`, three signature breaks and **one deliberate tripwire asserting the opposite** (H2) |
| **B** | Is `mdHash(mdBody)` stable across two serves of an unchanged document? | **Yes** — `canonicalizeMd` folds CRLF/trailing/NFC and both writers hash the raw decoded blob. No normalisation loop, no charge loop; the fresh-object-literal argument checks out. **But the document is rewritten on every press, including bare ones — B1** |
| **C** | Does the conjunct disturb `decideCompanion`? | **Polarity is consistent** — both treat absent as unprovable, and the companion refuses to ship a non-matching envelope, so sync cannot deliver a mismatched envelope into the cloud. No double regeneration. **But the block's "nothing is deleted" claim is contradicted by branch 4 — H3** |
| **D** | Does this change local behaviour? | **No.** Nothing in the local path calls `isFresh`; local envelope reads go through `rerender.ts:67` and `dig-merge.ts:62`. No extra local calls, no divergence. The block could say this in one line (L2) |
| **E** | Is deferring the wave measurement legitimate? | **Yes as a decision, understated as a description.** No repo-side bound exists and I proved why: `GENERATOR_VERSION` has not bumped since `sourceMdHash` began being written (M3) |
| **F** | Does (e) fix what it was chosen for? | **Yes for the owner** — corrected body → hash mismatch → not fresh → reserve → regenerate → new envelope → `dig-merge` trusts it → corrected gists render. Traced end to end. The share reader stays stale by design (L1) |

## Honest assessment

Strip B1 and this block converges. H2 and H3 are documentation defects on a sound design — real, and
both must land before the plan, but neither changes the mechanism. H1 is a genuine behaviour gap that
I would fix in the same change because it is two lines and it completes the argument the block already
makes.

B1 is different. It is the oracle problem: (e) is correct, and the thing it reads is moved by a press
that does no work. That is not a wording fix — it is a decision about whether a no-op press may cost
6¢, and about which of §4 and §7 is telling the truth. It belongs to the spec.

NOT CONVERGED
