# Adversarial review — append-only generations roadmap + M1 plan (round 1, Claude half)

**Reviewer:** Claude (independent of the Codex half — `plan-append-only-m1-r1-codex.md` was not read).
**Reviewed at:** `ceccbbc` (`docs(plan): append-only generations — the milestone spine, and M1 in full`),
tree clean apart from the two untracked review files.
**Date:** 2026-08-22.

**Counts: 1 Blocking, 6 High, 6 Medium, 6 Low.**

---

## What I executed

| Command | Result |
|---|---|
| `npm test` | **268 suites / 2,722 tests, all passing, 36.9s.** Reproduces the roadmap's figure exactly. |
| `wc -l docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema/*.sql` | 4 files, **4,108** total. ✅ reproduces |
| `ls supabase/migrations/ \| tail -5` | highest is `0025_settle_is_observable.sql`. ✅ reproduces |
| `grep -rn "generation_id" lib/ app/ worker/ supabase/` | **0**. ✅ reproduces |
| `grep -rln "generation_id" --exclude-dir={node_modules,.git,docs} .` | `scripts/check-guard-coverage.py`, `scripts/check-sentinel-meanings.py`, `scripts/gen-backlog-page.py`. **Three scripts, no contract test** — see L5 |
| `head -2 docs/adr/0006-*.md` | `status: proposed`. ✅ reproduces |
| `ls docs/reviews/ \| grep blob-addressing` | rounds r1–r8, **r10, r12, r13, r14, r15, r16, r17**. ❌ contradicts the table — see H4 |
| `grep -rn "summaryMd" …` | 175 hits / 37 files (`lib app worker components`); 213 / 50 repo-wide excl. tests+docs. ❌ neither is 192/40 — see L4 |

**NOT VERIFIED (say so out loud):** integration and e2e tiers were not run (no live Supabase stack).
`SupabaseBlobStore.promote`'s create-if-absent behaviour is read from source
(`lib/storage/supabase/supabase-blob-store.ts:116-134`), **not** exercised against live Storage.
Whether the extra `transferClassA` in H6 costs Gemini money on a later serve is **not established** —
I did not run the serve path. The Fly `v7` row is a doc claim (`docs/roadmap-to-launch.md:1397`), not
a `fly status` I ran.

I did not apply the plan's patch — the review brief forbids editing files — so every claim below is
traced by hand through quoted code, not observed from a modified tree.

---

## BLOCKING

### B1 — M1 stamps a card for a body the worker did not write, in exactly the case M1 exists for

**Where:** `docs/superpowers/plans/2026-08-22-m1-honest-card.md:206-215` (the patch),
`:280-293` (the plan's own CHARACTERIZATION test),
`lib/storage/supabase/supabase-blob-store.ts:120-123`, `lib/job-queue/summary-handler.ts:172-179`.

The plan's goal sentence is `:5-7`: *"Make the cloud summary worker stamp the provenance of the body
it just wrote."* The worker's write sequence is:

```ts
// lib/job-queue/summary-handler.ts:172-179
    const key = `${baseName}.md`;
    const ref = await bundle.blobStore.putStaged(bundle.principal, key, Buffer.from(core.mdContent, 'utf-8'), 'text/markdown');
    if (!(await bundle.blobStore.exists(bundle.principal, ref.tempKey))) {
      throw new Error('staged upload not verified');
    }
    await persistSummary(serviceClient, job.ownerId, job.playlistId, job.videoId, video, 'committed');
    await bundle.blobStore.promote(ref);
    await persistSummary(serviceClient, job.ownerId, job.playlistId, job.videoId, video, 'promoted');
```

and the cloud `promote` is:

```ts
// lib/storage/supabase/supabase-blob-store.ts:116-123
  async promote(ref: StagedRef): Promise<void> {
    const from = this.objectKey(ref.principal, ref.tempKey);
    const to = this.objectKey(ref.principal, ref.finalKey);
    // move = copy+delete (non-atomic). Idempotent: if final already present, ensure temp gone and return.
    if (await this.exists(ref.principal, ref.finalKey)) {
      await this.b().remove([from]).catch(() => {});
      return;
    }
```

Note the `exists` guard at `summary-handler.ts:174` checks `ref.tempKey`, never the final key. **When
the final key already exists, the worker's bytes are deleted and the pre-existing body stays live.**

So the sentence "the body it just wrote" is false whenever the final key is occupied. The plan does
not merely fail to notice this — **it proves it, in the very next test**:

```ts
// plan :285-292 — Task 2, CHARACTERIZATION
    const store = new InMemoryBlobStore({ promoteSemantics: 'create-if-absent' });
    await store.put(principal, SUMMARY_KEY, Buffer.from('TRANSFERRED local body', 'utf8'), 'text/markdown');
    setup(store, 'WORKER body, generated minutes later', null);
    await makeSummaryHandler(serviceClient)(job(), ctx);
    const live = await store.get(principal, SUMMARY_KEY);
    expect(live!.toString('utf8')).toBe('TRANSFERRED local body');
```

Put the two Task-2 tests side by side. Test 1 (`:255-278`) seeds the *same* pre-existing blob and
then asserts the payload carries `mdCorrectionsHash === mdHash('')` and a fresh `mdGeneratedAt`. Test 2
asserts the live blob is still `'TRANSFERRED local body'`. **Together they assert a row whose card says
"generated at T, no corrections applied" over a body that was generated elsewhere and does have
corrections applied.** That is the precise defect the plan opens by describing (`:5-8`).

**Concrete failure scenario (Supabase, the #19 interleaving the plan is built around):**

1. Worker reserves serial 7 → `key = 007_a-video-about-alpha.md`; enters Gemini for minutes.
2. `transferClassA` decides local wins, commits the LOCAL corrected body at that key with
   `await loser.blob.put(loser.p, key, staged, 'text/markdown')` (`sync-run.ts:394` — deliberately
   `put`, not `promote`, precisely because promote is create-if-absent, see `:386-393`), and patches
   the row with the local card (`mdGeneratedAt: wv.mdGeneratedAt`, `mdCorrectionsHash: wv.mdCorrectionsHash`,
   `sync-run.ts:401-402`).
3. Worker returns. `promote` **skips**. Both `persistSummary` calls carry the new stamps.

- **Pre-M1 outcome:** layer (2) (`0021_cloud_sync_signals.sql:117`) preserves the transferred
  `mdGeneratedAt`/`mdCorrectionsHash`. The card **matches the body that is actually at the key.**
  The card was *correct*.
- **Post-M1 outcome:** layer (3) (`0021:131-132`) overwrites both with the worker's values. The card
  is now **wrong** about a body it does not describe.

**M1 makes the card dishonest on the one interleaving it was written to fix.** Every consumer that
trusts `mdCorrectionsHash` then acts on a false premise — including `reconcileClassA`
(`reconcile-class-a.ts:8`), the very function the plan nominates as the beneficiary (`:39`).

This is the same shape as the error the plan's author flagged in the brief — reasoning about a write
that the storage layer does not actually perform.

**Suggested fix (all stay inside "no schema change"):** make the stamp conditional on the bytes
having landed. Cheapest correct form: keep the `'committed'` persist unstamped, and after
`promote(ref)` read the final key back and compare `mdHash(bytes) === mdHash(core.mdContent)`; stamp
`mdGeneratedAt`/`mdCorrectionsHash` only on the `'promoted'` persist and only when the comparison
holds. If it does not hold, the worker did not publish, and the honest action is to stay silent (the
layer-2 preservation that exists today is then correct behaviour, not a defect). Alternatively give
`BlobStore.promote` a `{ moved: boolean }` return and gate on it — but that touches the seam and is
probably M5's job. Either way the plan cannot ship the unconditional stamp.

---

## HIGH

### H1 — Task 2's first test can pass with zero assertions, and its fixture contradicts the code it cites

**Where:** plan `:255-278`; `lib/job-queue/summary-handler.ts:84-92`; `lib/cloud-sync/sync-run.ts:430`.

The fixture claims to model a row `transferClassA` just patched:

```ts
// plan :263-269
    setup(store, 'WORKER body, generated minutes later', {
      id: VIDEO, serialNumber: SERIAL, summaryMd: SUMMARY_KEY,
      docVersion: CURRENT_DOC_VERSION,
      …
      artifacts: { summaryMd: { key: SUMMARY_KEY, status: 'committed' } },
    });
```

But `transferClassA` does not write `'committed'`:

```ts
// lib/cloud-sync/sync-run.ts:430
    artifacts: { summaryMd: { key, status: 'promoted' } },
```

Substitute the value the cited code actually writes and the handler short-circuits:

```ts
// lib/job-queue/summary-handler.ts:86-92
    if (
      existingArtifacts?.summaryMd?.status === 'promoted' &&
      existing?.docVersion &&
      docVersionKey(existing.docVersion) === job.version
    ) {
      return;
    }
```

`payloads` is then `[]`, and the test's only assertions live inside `for (const p of payloads)`
(`:273-277`) — **the body never runs and the test passes green having checked nothing.** Task 1's
test guards against exactly this with `expect(payloads.length).toBeGreaterThan(0)` (`:170`); Task 2's
two tests have no such guard.

This matters beyond the typo, because it means the plan has not identified the state in which its
scenario is actually reachable. With a `'promoted'` artifact the worker only proceeds when the stored
`docVersion` differs from the job's — so the real fixture is `status: 'promoted'` **plus** an older
`docVersion` (`{ major: 1, minor: 0 }`, exactly as
`summary-handler-promote-divergence.test.ts:133` does it).

**Fix:** add `expect(payloads.length).toBeGreaterThan(0);` to both Task-2 tests, and change the
fixture to `status: 'promoted'` with an older `docVersion`.

### H2 — Task 2's CHARACTERIZATION duplicates an existing `it.failing` tripwire with inverted polarity, against an explicit repo ban

**Where:** plan `:280-293`; `tests/lib/job-queue/summary-handler-promote-divergence.test.ts:140-158`.

That defect is already guarded, in the file the plan tells the engineer to copy its fixture from:

```ts
// tests/lib/job-queue/summary-handler-promote-divergence.test.ts:140-149
  // KNOWN-FAILING TRIPWIRE — backlog #22. `it.failing` asserts the test DOES fail, so this
  // suite is green while the defect exists and goes RED the moment someone fixes it. Do NOT
  // rewrite the assertion to match current behaviour (dev-process.md bans it).
  …
  it.failing('serves the NEW body under Supabase semantics (promote is create-if-absent)', async () => {
```

The plan's CHARACTERIZATION is the same mechanism asserted the other way round, as a plain `it`. Two
problems:

1. **It is the banned move.** "Rewrite the assertion to match current behaviour" is exactly what
   `expect(live!.toString('utf8')).toBe('TRANSFERRED local body')` does. The plan's mitigation is a
   prose comment (`:284`: *"this assertion should then be INVERTED, not deleted"*) — prose where the
   existing test uses a **mechanism**. When M5 lands, `it.failing` flips red automatically and
   correctly; the plan's plain `it` flips red in a way that reads as "M5 broke a test", which invites
   deletion.
2. **The plan never mentions the existing tripwire**, so a reviewer cannot tell whether the
   duplication was considered. Two guards on one behaviour with opposite polarity is the
   *two-mechanisms-for-one-concern* shape this repo has already paid for.

**Fix:** delete the CHARACTERIZATION test. If the sync-first variant is worth covering separately
from the doc-version-bump variant, add it as a second `it.failing` in
`summary-handler-promote-divergence.test.ts` next to its sibling, not as a positive assertion in a
new file.

### H3 — Task 3 pastes a whole file over one that already exists, with colliding declarations

**Where:** plan `:317` and `:327-366`; `tests/lib/cloud-sync/reconcile-class-a.test.ts` (exists,
4,648 bytes, 11 tests).

The plan hedges — *"create with the header comment below if it does not exist"* — but then supplies a
**complete file**: file-level docstring, `import { reconcileClassA }`, `import { mdHash }`,
`import type { ClassASignals }`, `const CORRECTIONS`, `const CUR`, `const signals`, then two
top-level `it`s. The existing file opens:

```ts
// tests/lib/cloud-sync/reconcile-class-a.test.ts:1-8
import { reconcileClassA } from '@/lib/cloud-sync/reconcile-class-a';
import type { ClassASignals } from '@/lib/cloud-sync/types';

const S = (o: Partial<ClassASignals>): ClassASignals => ({
  summaryMdKey: 'x.md', mdHash: 'h', docVersionMajor: 3, mdGeneratedAt: '2026-01-01T00:00:00.000Z',
  mdCorrectionsHash: 'C', backfilled: false, ...o,
});
const CUR = 'C'; // reconciled corrections hash
```

An engineer with no context has two literal readings and both are wrong: append → `SyntaxError:
Identifier 'CUR' has already been declared` plus two duplicate-import errors; overwrite → **11 tests
deleted**, including the `§5.3` ladder coverage at `:11-64`.

**Fix:** state that the file exists, give the snippet as an *append inside the existing
`describe('reconcileClassA (§5.3)')`*, reuse the existing `S` helper, and name the new constant
something that does not collide with `CUR`.

### H4 — The roadmap's spec-convergence row and M3 are seven rounds stale

**Where:** roadmap `:35` and `:92`.

> `| Spec convergence | rounds 1–9 all NOT CONVERGED; round 10 marked mandatory |`
> `Spec round 10 (mandatory; rounds 1–9 all NOT CONVERGED), then ADR-0006 → accepted.`

`ls docs/reviews/ | grep blob-addressing` returns coordinator adjudications for **r10, r12, r13, r14,
r15, r16 and r17** — all of them already run, all NOT CONVERGED:

```
docs/reviews/spec-blob-addressing-r10-coordinator.md:3: **Verdict: NOT CONVERGED.** 1 Blocking, 4 High, 4 Medium. Round 11 is mandatory.
docs/reviews/spec-blob-addressing-r13-coordinator.md:3: **Verdict: NOT CONVERGED.** 2 Blocking, 4 High, 6 Medium, 1 Low. Round 14 mandatory.
docs/reviews/spec-blob-addressing-r14-coordinator.md:3: **Verdict: NOT CONVERGED.** 4 Blocking, 4 High, 5 Medium, 1 Low. Round 15 mandatory.
docs/reviews/spec-blob-addressing-r15-coordinator.md:3: **Verdict: NOT CONVERGED.** 3 Blocking, 3 High, 6 Medium, 2 Low. Round 16 required.
docs/reviews/spec-blob-addressing-r17-coordinator.md:3: **Verdict: NOT CONVERGED.** 1 Blocking, 4 High, 3 Medium, 1 Low (Claude); 1 Blocking, 1 High, 1 Medium (Codex).
```

ADR-0007's own front matter confirms the same series: *"Rounds 13, 14, 15, 16, 17 — five DESIGN
reviews, all answered here"* (`docs/adr/0007-artifacts-are-an-append-only-log.md:4`).

The consequence is not cosmetic. M3 as written tells an engineer to run a review that ran weeks ago,
and its "one more round" framing understates a **seventeen-round** non-convergence history that has
already tripped `dev-process.md`'s Phase-6 four-non-converging-rounds trigger more than once. The
table header says *"Every figure here came from a command run when this file was written"* — this
figure did not.

**Fix:** replace both with the measured state: rounds 1–8, 10, 12–17 all NOT CONVERGED, latest r17
with 1 Blocking / 4 High outstanding; M3 is "round 18", and it should say what r17 left open.

### H5 — M3's one specific technical instruction is refuted by the schema it points at

**Where:** roadmap `:94-97`.

> **Point round 10 at the ranking that computes `current`.** … the spec claims the result is
> *"identical for every reader, on every replica, forever"*, which holds only if the ordering is
> **total and deterministic** — and `mdGeneratedAt`, the field M1 is about, is exactly the kind of key
> that ties.

The ranking already is total and deterministic, and `mdGeneratedAt` is already not the last key:

```sql
-- docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema/04_artifacts.sql:695-782
create view video_summary_current with (security_invoker = true) as
select distinct on (a.workspace_id, a.video_id) a.*
…
order by a.workspace_id, a.video_id,
         (g.card->>'mdCorrectionsHash' = wv.corrections_hash) desc,
         g.doc_version_major desc nulls last,
         -- Round 5 B3: rank the CARD's mdGeneratedAt, not produced_at. …
         (g.card ->> 'mdGeneratedAt') desc nulls last,
         g.produced_at desc nulls last,
         a.generation_id desc;
```

`video_artifacts_current` ends the same way (`:789-790`). A `mdGeneratedAt` tie falls to
`produced_at` and then to `generation_id`, which is unique per generation — so the ordering is total.
Further, the `mdGeneratedAt` key was *introduced* by round 5 finding B3 (comment at `:777-780`,
explicitly citing `reconcileClassA:49`) and revisited in round 15 M3 (`:760`). The roadmap points the
next round at ground three earlier rounds have already worked.

**Fix:** drop the paragraph or re-aim it. If there is a residual concern it is a different one — the
`(g.card->>'mdCorrectionsHash' = wv.corrections_hash)` rung carries no guard of its own by the
schema's own admission (`:711-716`) — and that is worth naming instead.

### H6 — M1 converts `skip` into a full `transferClassA` for the class of video the plan claims to fix; the Consequences table misses it

**Where:** plan `:41-49` (the table); `lib/cloud-sync/reconcile-class-a.ts:32-40`;
`lib/cloud-sync/sync-run.ts:394-432`.

Take the plan's own row 3 case — a video with corrections, previously transferred cloud-ward. Because
`promote` skipped (B1), **both replicas hold identical bytes**, so `deriveClassASignals`
(`backfill.ts:11`) computes the same `mdHash` on both sides.

```ts
// lib/cloud-sync/reconcile-class-a.ts:32-40
  if (local.mdHash === cloud.mdHash) {
    if (lCur && cCur) return { action: 'skip', needsRegen: false };
    if (bothStale && local.docVersionMajor === cloud.docVersionMajor) return { action: 'skip', needsRegen: true };
    // else: fall through to currency/format below.
  }
  if (lCur && !cCur) return { action: 'copyToCloud', needsRegen: false };
```

- **Pre-M1:** cloud inherited local's `mdCorrectionsHash` → `lCur && cCur` → `skip`. Correct and free.
- **Post-M1:** cloud is `mdHash('')` → `cCur` false → falls through `:36` → `:39` **`copyToCloud`**.

So a run that previously skipped now performs a complete `transferClassA` of bytes that are already
identical: staged put, verify, `put`, delete, `updateVideoFields`, plus `companionTransfer`. And that
transfer is not side-effect-free:

```ts
// lib/cloud-sync/sync-run.ts:426-427
    summaryHtml: null,
    digDeeperHtml: null,
```

The rendered-HTML caches are dropped on a transfer that moved nothing. It self-heals on the following
run (cloud now carries the current hash → `skip`), so this is not data loss — but it is a Class-A
outcome change on existing rows, and the plan's table asserts the opposite twice: row 3 predicts
`copyToCloud` as *the fix* (it is instead a redundant no-op copy in this shape), and row 4 says
existing rows are *"Unaffected"*.

I could **not** establish whether the dropped `summaryHtml` costs Gemini on the next serve — that
needs the serve path and a live stack. **NOT VERIFIED**, and it is the reason this is High rather
than Medium: the plan is a money-adjacent write path and the table that was supposed to bound the
blast radius does not contain this case at all.

**Fix:** add the equal-bytes case to the Consequences table with its real verdict, and either accept
the extra transfer explicitly or make B1's fix (stamp only when the bytes landed) — which dissolves
this too, since a skipped promote then leaves the card untouched and the `skip` survives.

---

## MEDIUM

### M1 — Task 3's tests cannot fail from any M1 change, yet the Self-review claims they prove the payoff

Plan `:372-373` admits it: *"it asserts the pure function, which is unchanged, so it must pass before
**and** after."* `reconcileClassA` is not touched by Task 1. Revert `summary-handler.ts` entirely and
both Task-3 tests still pass. But `:452-453` claims *"Task 3 proves the payoff at the consumer."* It
does not — it documents a property of an unchanged function. Per this repo's own
`a-checklist-item-can-be-an-unfalsifiable-guard`: name the observation that would make it fail. There
isn't one.

Additionally the first test duplicates existing coverage:

```ts
// tests/lib/cloud-sync/reconcile-class-a.test.ts:19-22
  it('mdHash equal but one current, one stale → current wins, NOT skip (Blocking ③ scenario 1)', () => {
    const r = reconcileClassA({ local: S({ mdHash: 'h', mdCorrectionsHash: CUR }), cloud: S({ mdHash: 'h', mdCorrectionsHash: 'OLD' }), reconciledCorrectionsHash: CUR });
    expect(r).toEqual({ action: 'copyToCloud', needsRegen: false });
  });
```

Only the exact-tie-on-`mdGeneratedAt` case (plan `:359-366`) is genuinely new.

**Fix:** keep the tie case, drop the first, and stop describing Task 3 as proof of M1.

### M2 — The Consequences table's first row cites the wrong reader

Plan `:45`: *"`backfilled` is read only by Class-B (`reconcile-class-b.ts:43`); `reconcileClassA`
never consults it."* The conclusion is right; the evidence is a different field on a different type.

- `ClassASignals.backfilled` is written at `lib/cloud-sync/backfill.ts:15` and, by
  `grep -rn "backfilled" lib/ app/ components/ worker/ types/`, **read by nothing**.
- `reconcile-class-b.ts:43` reads `local.backfilled || cloud.backfilled` on `FieldState`
  (`types.ts:25`), produced by `deriveHumanSnapshot` at `backfill.ts:28-29` from
  `video.annotationsEditedAt`, which `mdGeneratedAt` does not feed.

The stronger true statement — *"`ClassASignals.backfilled` has no readers at all"* — is both easier
to verify and a better argument. This repo's standing rule is quote, don't characterise; the row
characterised and landed on the wrong line.

### M3 — Task 4 Step 4's second bullet is not executable, and the ratchet will not catch the mistake

Plan `:415`: *"Add the missing parent: #23 gates `adr-0006-addressing` (roadmap :1018)."* The cited
line does support the fact:

```
docs/roadmap-to-launch.md:1018
**Blocked by:** **backlog #23** — corrections as deterministic `{from, to}` pairs.
```

But the data structure only expresses item→root:

```python
# scripts/gen-backlog-page.py:356-364
# item → (relation, root key, optional note)
DEPENDS: dict[int, tuple[str, str, str]] = {
    19: ("survives", "adr-0006-addressing", …),
```

with relations `survives / partly-dissolved-by / blocked-by / dissolved-by` (`:346-355`), all read
*from the item's side*. "#23 gates the root" is the reverse edge and has no representation. The
obvious literal execution — `DEPENDS[23] = ("blocked-by", "adr-0006-addressing", …)` — asserts the
**opposite** (that #23 waits on the root), and `depends_errors` (`:369-397`) checks only that the
relation is known, the root exists, and the item is open. It will pass a fully inverted graph.

**Fix:** either add a `gates`/`blocks` relation to `RELATIONS` and a reverse-edge renderer, or say
plainly that the edge cannot be expressed and put the fact in `ROOTS["adr-0006-addressing"]["detail"]`
as prose. Do not leave the instruction as-is.

### M4 — The same defect class is left unfixed in five more fields, and the plan states the count as if it were closed

Plan `:14`: *"The worker supplies ten of the twelve."* The literal is:

```ts
// lib/job-queue/summary-handler.ts:149-164
    const video: Video = {
      ...core.geminiFields,
      …
      docVersion: CURRENT_DOC_VERSION,
      processedAt: new Date().toISOString(),
    };
```
```ts
// lib/ingestion/summary-core.ts:148
    geminiFields: { language, ratings, overallScore, videoType, audience, tags, tldr: outTldr, takeaways: outTakeaways },
```

Ten is an upper bound, not a fact. The handler's own comment says why (`:146-148`): *"already carries
videoType/audience/tags/tldr/takeaways as optional (possibly undefined) keys … JSON serialization
drops undefined-valued keys."* When Gemini returns no `tags` on this run, `tags` is absent from the
payload, `jsonb_strip_nulls` in layer (3) drops it, and layer (2) hands back **the previous run's
tags** — the identical mechanism, on the identical row, producing a card field describing a different
body. The plan's framing ("the two it omits are exactly the two that identify the body", `:14-15`)
reads as if the class is closed at two.

**Fix:** say explicitly that five more layer-3 keys inherit under the same mechanism, and that M1
scopes them out (with a backlog row), rather than implying the count is exhaustive.

### M5 — The work is backlog #23 clause (a), not #19; every commit message says `#19`

`docs/backlog.md:52` (#23) is a verbatim description of what M1 does:

> *(a) A fresh summarize silently drops the user's corrections AND claims it did not.* `pipeline.ts:272`
> stamps `mdCorrectionsHash: mdHash('')`, and the cloud worker (`summary-handler.ts`) never mentions
> corrections at all — so `persist_summary`'s layer-2 merge **preserves the previous hash**.

`docs/backlog.md:48` (#19) is a different defect — the `transferClassA` content race, whose mechanism
is that the transfer *"never writes `serialNumber`"* so a serial-keyed fence cannot catch it, and
which states *"**Establish first whether it is a defect at all** — that is the cheapest possible
outcome and it has not been ruled out."*

Yet all four commit messages are `(#19)` (plan `:232`, `:309`, `:379`, `:430`), the roadmap says
*"Kills: backlog #19's live harm"* (`:74`), and *"Any work item for backlog #19… Its corrections half
is M1"* (`:145-146`) — #19 has no corrections half. Per `feedback-name-every-reference`, a reference
must resolve where it is read; these resolve to the wrong row, and git history is where that
misattribution becomes permanent.

**Fix:** commit as `fix(#23a)` / `test(#23a)`, and correct the roadmap's M1 "Kills" line to
`#23 clause (a)` only.

### M6 — Task 1 Step 6's instruction has no decision procedure and licenses shipping a regression

Plan `:225-227`:

> Any Class-A sync test that breaks is a **real signal**, not noise: read it before touching it, and
> record what it says in the PR body.

The plan's own thesis is that behaviour does not change (`:48`: *"Unaffected"*). So **any** Class-A
break falsifies the Consequences table, and the correct instruction is *stop and re-plan*. "Record
what it says in the PR body" tells the engineer to proceed with the break documented. Given H6 says a
Class-A outcome genuinely does change, this is the step most likely to be exercised.

**Fix:** *"If any Class-A test breaks, the Consequences table is wrong. Stop, do not modify the test,
and re-derive the table before continuing."*

---

## LOW

- **L1** — plan `:76-77` says the fixture is *"lifted from `summary-handler-promote-divergence.test.ts:29-110`"*
  and to copy rather than retype. `setup()` closes at `:112`, so lines 29-110 are a syntactically
  incomplete block; and the plan's own `setup` has a different signature (`existingRow` vs
  `existingDocVersion`), so it is not a copy anyway. Say "adapted from", cite `:29-112`.
- **L2** — plan `:463` cites *"the `ClassASignals` fields at `types.ts:32`"*. Line 32 is
  `VideoBaseline['classA']`; `ClassASignals` is `lib/cloud-sync/types.ts:4-11`, the two fields at
  `:8-9`.
- **L3** — plan `:341`: `const CORRECTIONS = 'Clawcode -> Clawcode';` — `from` and `to` are identical.
  Presumably `'Clawcode -> Claude Code'`. Harmless to the assertion, confusing to a no-context reader.
- **L4** — roadmap `:34`: *"`base`/`summaryMd` — 192 call sites across 40 files"* does not reproduce
  and no command is given. `grep -rn "summaryMd" lib/ app/ worker/ components/` → 175 hits / 37 files;
  repo-wide excluding tests and docs → 213 / 50. Publish the command next to the figure.
- **L5** — roadmap `:33`: *"only 2 ratchet scripts + 1 contract test"*.
  `grep -rln "generation_id" --exclude-dir={node_modules,.git,docs} .` returns three **scripts** —
  `check-guard-coverage.py`, `check-sentinel-meanings.py`, `gen-backlog-page.py` — and no test file.
  (`tests/lib/blob-addressing-caller-contract.test.ts` is referenced by `backlog.md:55` but does not
  match `generation_id`.)
- **L6** — plan `:9-10` cites `0021_cloud_sync_signals.sql:115-133` for the layering; the layers run
  `:116-132` and the function to `:153`. The prompt's own `:115-153` is the better citation. Also, the
  plan calls layer (1) *"the payload"* where the SQL comment calls it *"payload defaults — fill keys a
  first-time bare row lacks"* (`:116`); the distinction is load-bearing for the argument and worth
  keeping.

---

## The brief's six suspicions, answered

1. **Is `mdHash('')` honest?** — **Yes, for this consumer, and I could not break it.**
   `reconciledCorrectionsHash` is computed as `mdHash(String(merges.corrections.value ?? ''))`
   (`sync-run.ts:651`), so a video whose corrections were deleted reconciles to `mdHash('')` and the
   worker's row correctly reads as current. "No corrections applied" and "the empty corrections set
   was applied" are the same statement under the only test that exists
   (`reconcile-class-a.ts:8`, `s.mdCorrectionsHash === cur`). The local pipeline already makes the
   same claim on a first generation, with the same reasoning written down
   (`pipeline.ts:268-272`). **Doubt refuted.** The honesty problem is elsewhere — it is B1, and it is
   about `mdGeneratedAt` and the body, not about the hash.
2. **Can M1 change Class-A outcomes for existing rows?** — **Yes. See H6.** One of the four table
   rows is wrong (row 3's mechanism) and row 4's "Unaffected" is wrong for any row whose cloud card
   was previously inherited from a transfer.
3. **Is `backfilled` unread by Class A?** — **Yes, and more strongly than the plan says.** See M2:
   `ClassASignals.backfilled` has zero readers repo-wide, so `hasReal` flipping true is inert. No
   behaviour change from that field. **Doubt refuted, evidence corrected.**
4. **Is the CHARACTERIZATION test right?** — **No. See H2.** It entrenches the defect as a positive
   assertion, duplicating an `it.failing` tripwire whose comment explicitly bans this move.
5. **Is it safe to ship M1 before M3 converges?** — The ordering is *not* the problem; B1 is. M1 does
   not depend on anything M3 decides, and it is a payload-only change to a path that already writes
   these two keys from two other callers (`pipeline.ts:271-272`,
   `app/api/videos/[id]/regenerate/route.ts:87-88`). It should ship before M3 — **once it is correct.**
   The real ordering defect is H4: M3 is written against a seven-round-stale reading of its own
   review history, so "M3 converges the design" is not a one-round step and the roadmap should not
   present it as one.
6. **Is Step 6 actionable?** — **No. See M6.**

## Decomposition, placeholders, type consistency

- **Decomposition:** Tasks 1→2 are correctly ordered (2 consumes `setup`/`payloads`/`SUMMARY_KEY`
  from 1). Task 3 is independent. Task 4 depends on nothing in 1–3 and could run first. No task uses
  a name an earlier task fails to define. **No finding.**
- **Placeholders:** the plan's claim of none (`:456-459`) is **almost** right. Task 4 Steps 1–3 say
  *what* to write into `docs/backlog.md` but not the text (`:395-409`) — defensible for prose. Step 4's
  second bullet is the genuine one: it names an outcome the code cannot express (M3).
- **Type consistency:** `mdGeneratedAt: string` and `mdCorrectionsHash: string` are consistent across
  Tasks 1–3, present on `VideoSchema` (`types/index.ts:87-88`, both `.optional()`), so the object
  literal type-checks, and `persistSummary` forwards the object to the RPC unfiltered
  (`lib/storage/worker-persistence.ts:22-25`) — the Task-1 test's subject is therefore legitimate
  despite mocking the wrapper. **No finding beyond L2.**
- **Test quality:** Task 1's test is sound and guarded. Task 2's are not (H1, H2). Task 3's are
  unfalsifiable (M1). No negative test catches "any error" — there are no negative tests.

## What the plan does not cover and should

1. **The promote-skip case** — B1. Nothing in the plan makes the stamp conditional on publication.
2. **The other five inheriting layer-3 keys** — M4.
3. **The two other writers of these fields.** `app/api/videos/[id]/regenerate/route.ts:87-88` sets
   both, and `transferClassA` (`sync-run.ts:401-402`) carries them across. The plan's Global
   Constraint (`:23-25`) says "match the local pipeline exactly" and names only `pipeline.ts`. If the
   point is that the two pipelines cannot drift, the constraint should enumerate all four writers.
4. **`processedAt` and `mdGeneratedAt` are two separate `new Date()` calls** in the patch
   (`:212`, `:214`) and can differ by a millisecond. Harmless today because
   `deriveClassASignals` prefers `mdGeneratedAt` (`backfill.ts:13`), but the plan asserts the worker
   stamps *the* provenance and two clock reads is one more than that needs. Hoist to a single
   `const now = new Date().toISOString()`.

---

## Verdict

**NOT CONVERGED**
