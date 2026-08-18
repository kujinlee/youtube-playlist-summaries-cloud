# Spec review — cloud blob key encoding (backlog #36), ROUND 6, Claude half

**Subject:** `docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md` **v6, working tree**
(not a pinned commit). **Branch:** `fix/cloud-blob-key-encoding`. **Date:** 2026-08-14.

**Verdict: NOT CONVERGED.** 1 Blocking, 1 High, 3 Medium, 2 Low.

I want to be precise about the calibration, because round 6 with a Phase 6 behind it deserves it.
**Everything v6 changed, it changed correctly.** I re-measured all four of the new claims and all four
hold: `utf16le` really does restore injectivity on lone surrogates; the `move()`-409 argument is real;
the fallback key is servable for every shape of `videoId`; and behaviors 19/21/22/23 are constructible
where 16/19/21 were not. **If the finding below were absent I would say CONVERGED.**

It is not absent. There is a **fourth write entrance** — `reconcileCloudBase`, in the module the spec
cites twice for other reasons — and it is the one that *undoes v6's own repair*. It writes a blob at a
key it never validates, advertises that key `promoted`, and then **deletes the old blobs**. That is a
paid artifact made unreachable, so it is Blocking under the brief's own rule.

Probe scripts:
`/Users/kujinlee/.claude-tmp/claude-501/-Users-kujinlee-code-agentic-ai-docs-youtube-playlist-summaries-cloud/a00a513a-4135-416e-bbf4-48c0416ca19d/scratchpad/{r6-guard.mjs,r6-sb.mjs}`.
`r6-sb.mjs` asserted `new URL(NEXT_PUBLIC_SUPABASE_URL).hostname` is `127.0.0.1`/`localhost` and exits
non-zero otherwise; it wrote under a UUID prefix and removed everything (`leftover entries: 0`).

---

## Measurements this review rests on

| # | Probe | Result |
|---|---|---|
| P1 | Local Storage upload, per key | `003_🎉-my-talk.md` **400 Invalid key**; `003_x~y.md` **400**; `003_한국어.md` **400**; `003_x�.md` **400**; `003_my summary.md` **`ok`**; `003_a=hAAAA.md` **`ok`**; `=hAAAA.md` **`ok`** |
| P2 | `move()` onto an occupied destination | **409 `The resource already exists`**; destination body still `DST`; **source still present** |
| P3 | `sha256` of `'003_x\uD840.md'` vs `'003_x\uD850.md'` | `utf8` → **identical** digest (`laPXAty8NJEj4FE00WS_y9`); `utf16le` → **distinct** (`hF5ygck…` / `f4zxMMM…`) |
| P4 | Widened `CLOUD_SUMMARY_MD_KEY` against every fallback shape | `003_dQw4w9WgXcQ.md`, `003_-abc123defg.md`, `003__abcdefghij.md`, `003_12_abcdefgh.md` — **all pass**; `999999999_dQw4w9WgXcQ.md` (24 ch) passes |
| P5 | Widened guard against the hazard set | emoji, `~`, space, lone surrogate, `U+FFFD`, 200-char base — **all rejected**; `café` NFD **accepted** (widening works) |

---

## Blocking

### B1 — `reconcileCloudBase` is a FOURTH write entrance: it writes an unvalidated key, advertises it `promoted`, and then deletes the servable original

**The spec names three entrances twice** (§2.6:89-93, §3.5:267-271) and cites `reconcile-serial.ts`
twice for other reasons — §1:45 quotes its "LOCAL IS AUTHORITATIVE" comment, §3.3:166 lists it as a
`list()` *reader*. It is never counted as a writer. It is one.

**Evidence — the chain, end to end.**

1. It runs in production on the two-sided path, **before** Class A. `sync-run.ts:729-734`:
   ```ts
   const rec = occupancyTrusted
     ? await reconcileCloudBase({ cloud: cloudSide, cloudIndex: cloudSnapshot, localVideo: lv, cloudVideo: cv, … })
     : { ok: true as const, action: 'agreed' as const };
   ```
   and the comment at `:723-724` — *"repair a diverged `base` BEFORE the Class-A transfer"*.

2. Its destination is a **raw vault filename**. `reconcile-serial.ts:183-186` takes
   `newBase = d.to`, and `describeDivergence` (`:152-153`) sets
   `to = localVideo.summaryMd ? baseOf(localVideo.summaryMd) : …`. `localVideo.summaryMd` is
   whatever the filesystem allowed: `recoverOrphanedVideos` (`pipeline.ts:129-154`) adopts **any**
   `.md` in the vault carrying a `video_id` frontmatter field, and `reconstructVideo` sets
   `const summaryMd = file;` — the raw `readdirSync` name. This is the same provenance §3.5:272-274
   already identifies as dangerous for the Class-A path.

3. **Nothing validates it.** The only checks are `assertLogicalKey(from)` / `assertLogicalKey(to)`
   (`reconcile-serial.ts:267-268`), and `assertLogicalKey` is `blob-store.ts:87-91` —
   leading `/`, a `..` segment, a NUL. `grep -rn assertCloudSummaryMdKey lib/ app/ worker/` returns
   exactly three non-test sites: `resolve-summary-key.ts:16`, `serve-summary-core.ts:61`, and the
   definition. None is on this path.

4. **It writes blobs.** `reconcile-serial.ts:282` `await cloud.blob.copy(cloud.p, from, to)` →
   `supabase-blob-store.ts:98-100` `return copyBlob(this, p, from, to)` → `blob-store.ts` `copyBlob`,
   which ends in `store.put`. This is a `put` at the seam, exactly like the three named entrances.

5. **It advertises the key.** `reconcile-serial.ts:293-296`:
   ```ts
   summaryMd: `${newBase}.md`,
   artifacts: { summaryMd: { key: `${newBase}.md`, status: 'promoted' } },
   ```

6. **Then it deletes the old blobs.** `reconcile-serial.ts:357-361`:
   ```ts
   for (const { from, to } of plan) {
     if (to === from) continue;
     try { await cloud.blob.delete(cloud.p, from); } catch { cleanupFailures += 1; }
   }
   ```

**Failure scenario (constructible).** A vault file `003_🎉 my talk.md` — adopted by
`recoverOrphanedVideos`, so `localVideo.summaryMd = '003_🎉 my talk.md'`, `serialNumber = 3`. The
same video exists in the cloud at a slugified base, say `007_my-talk`. Bases differ → diverged.

- **On master this fails LOUDLY.** P1: Storage returns **400 Invalid key** for an emoji segment, so
  `copy` returns `copy-failed`, `reconcileCloudBase` refuses at `:289`, `sync-run.ts:754-756` throws,
  the video is reported per-run and **no blob is written and none is deleted**.
- **After this slice** the encoder makes `003_🎉 my talk.md` storable. Step 4 succeeds, step 5 writes
  the row, step 6 **deletes `007_my-talk.md`, its model and every dig**. Then
  `serve-summary-core.ts:56-64` `assertCloudSummaryMdKey(mdKey)` throws → **409 `corrupt summary key`**,
  and `resolve-summary-key.ts:16` returns `null`, so the dig path sees no summary at all.

The bytes are in the bucket at a key no route will ever name, the only other copy has been deleted, and
the row says `promoted`. Nothing repairs it: the bases now agree, so the reconciliation never runs
again. **That is the exact shape of backlog #36 — a promoted row, real spend, and a 409 the user finds
by opening the document — reproduced at a site the spec does not cover, and this time with the old copy
deleted.**

**The second half, and the reason this is the *specific* hazard v6 created.** Take the video §3.5's
fallback exists for: a title of 59 ASCII letters + `U+20000`. The cloud mints it at
`003_${videoId}.md` (the repair — good). The local replica has no fallback; `pipeline.ts:240-245`
uses `slugify(meta.title)` and nothing else, so local's base is the lone-surrogate slug. The two bases
**necessarily differ** — that is what the fallback *is* — and `describeDivergence` compares whole
bases (`:151-155`), not serials. So every sync run sees this video as diverged and relocates the cloud
**onto local's unservable slug key**, deleting the servable fallback blobs it just paid for.
**v6's repair is systematically undone by the entrance v6 does not name.** P5 confirms both the lone
surrogate and its `U+FFFD` filesystem form are rejected by the widened guard.

**Fix.** Two parts, and the first is the one that matters:

1. Put the servability check on **entrance four**: in `reconcileCloudBase`, before the copy phase —
   naturally at `:261-278`, where the plan is already built precisely so a refusal is a genuine
   no-move. A new refusal reason (`unservable-target`) joins `unmappable-key`; `sync-run.ts:754-756`
   already surfaces any `rec.reason`. Like the other sync entrances the fallback is not available
   here (the base must match local's), so this is a genuine refusal — and unlike them it costs nothing,
   because refusing is what master already does.
2. **Stop enumerating entrances in prose.** Six enumerations across six rounds have each missed one.
   The mechanical form is a check script in the §4 style: *every* call reaching `BlobStore.put` /
   `putStaged` / `copy` with a key that becomes a `summaryMd` value passes `assertCloudSummaryMdKey`
   first. `grep -n "putStaged\|\.put(\|\.copy(" lib/cloud-sync/ lib/job-queue/` is the ground truth the
   table keeps failing to match. A branded `CloudSummaryKey` type constructed only by the validator
   is the same idea enforced by `tsc` — the write sites take the branded type, so a fifth entrance
   cannot compile without passing the check.

---

## High

### H2 — §3.4 says the blob probe replaces the row scan; on the cloud receiver it must be added to it

**Evidence.** §3.4:189-190: *"**Ask the filesystem, not the index.** The guard must consult the
receiver's blob store **rather than** scanning index rows"*. The row scan it displaces is
`sync-run.ts:203-213`:

```ts
if (video.serialNumber != null || video.summaryMd) {
  const holder = idx.videos.find((v) =>
    (video.serialNumber != null && v.serialNumber === video.serialNumber) ||
    (video.summaryMd != null && v.summaryMd === video.summaryMd));
  if (holder) throw new Error(`serial collision: …`);
}
```

Two things that check cannot be replaced by a blob probe:

- **It checks the serial**, not only the key. A blob probe cannot see a serial at all. Its own comment
  (`:198-202`) records that dropping the *key* half destroyed a summary; dropping the *serial* half is
  the A1 defect the guard was built for.
- **On the Supabase receiver it is the reliable half of the pair.** `readIndex` throws on failure;
  `tryGet` on Supabase has `provesAbsence = false`, so its `absent` is 404-shaped and an RLS denial is
  indistinguishable from absence. v6's fail-closed-on-`unreadable` rule (§3.4:204-208) closes the
  *transient* case — genuinely, and it is the right fix — but not the false-`absent` case. §3.4's
  answer there is P2, which I re-measured and which holds: `move()` onto an occupied destination
  returns 409 and does not overwrite. **The bytes are safe; the row is not.**
  `supabase-blob-store.ts:112-118` treats a present destination as **success**:

  ```ts
  if (await this.exists(ref.principal, ref.finalKey)) {
    await this.b().remove([from]).catch(() => {});
    return;
  }
  ```

  so `copyAdditiveVideo` proceeds to `sync-run.ts:279` and writes
  `artifacts = { summaryMd: { key, status: 'promoted' } }` over bytes belonging to something else.
  The row scan is what catches that.

**Failure scenario.** An implementer reads "rather than" literally and deletes `sync-run.ts:203-213`.
A local→cloud additive create then accepts a video whose serial is already held by another cloud row —
the A1 case — with no check at all, because the blob probe cannot express it.

**Fix.** One clause: *"in addition to the row scan at `sync-run.ts:203-213`, not instead of it — the
row scan checks the serial, which no blob probe can, and on Supabase it is the reliable half. The blob
probe adds the case the row scan cannot see: a real receiver file with no index row."* That is exactly
what §3.4's own motive sentence describes, so the fix is to stop the wording overshooting it.

---

## Medium

### M1 — "the same loud failure master already produces" is false for the space and over-length subclass

§3.5:278-281: *"an unservable adopted key is a genuine **refusal** … That is the same loud failure
master already produces, preserved deliberately."*

P1 measured `003_my summary.md` → **`ok`**. A space is storable today; over-length (the guard's bound
is 128 characters, Storage's is 255) likewise. Those keys **sync successfully on master right now** —
silently, and unservably. v6 converts them into a per-video error on every run, forever, and §1
decision 1 fixes the vault filename so the user is given nothing to do. Round-5 M2 asked for the
remediation and v6 did not add it.

The refusal is the right direction — I am not arguing for the silent path. Two corrections: drop the
"same as master" sentence for this subclass (it is only true for the charset Storage already rejects:
emoji, `~`, `%`, non-ASCII), and say what the user does — rename the vault file is the honest answer,
and it is available here precisely because this key came *from* the vault rather than from `slugify`.

### M2 — the segment-boundary rule still contradicts behavior 12 (round-5 M1, unaddressed)

§3.2:152-153: *"**A prefix must end on a segment boundary.** `list`/`deletePrefix` throw otherwise."*
Behavior 12: *"`list(p, 'dig/{base}/')` and `list(p, 'dig/{base}')` return the same set."* No
observation distinguishes a mid-segment prefix from a complete one — both `list` and `deletePrefix`
see only a string. The only implementable predicate is v4's (*"empty or ends in `/`"*), and it makes
behavior 12 fail. Consequence is bounded — all three `list` callers pass a trailing slash (§3.3's
table, which I re-verified is complete) and the one `deletePrefix` caller passes `''` — but the rule
as written has no test and the behavior as written forbids the only rule that would.

### M3 — the injectivity contract is still absolute over a 132-bit truncated hash

§3.2:136 still says *"**injective over all valid logical segments as raw JS strings**"*, and behavior 4
mandates a property test for it. P3 confirms v6's `utf16le` fix is correct and removes the *reachable*
counterexample — that was round-5 H1 and it is genuinely fixed. What remains is the word: 22 base64url
characters is 132 bits, so the map is collision-*resistant*, not injective, and no property test can
establish the difference. Codex's round-5 Blocking was about this; I adjudicate it Medium, because
2⁻¹³² is not a failure scenario and §7.1 chose hashing deliberately with the trade-off written down.
But behavior 4 should say what it actually tests — the crafted `SAFE`/`=` branch-disjointness preimage
(which is real, and which the "widen `SAFE` to include `=`" mutation targets correctly) plus the P3
lone-surrogate pair (behavior 22) — and §3.2 should read *"collision-resistant, with structurally
disjoint identity and hash branches"*.

---

## Low

### L1 — the "seam is the only funnel" verification is still dropped (round-5 L1)

v4 §9 carried the measured fact that the only `client.storage.from(` in non-test code is
`supabase-blob-store.ts:20`, no signed/public URLs, no SQL touching `storage.objects` outside
`0007_storage_and_rpcs.sql`. Both §3.2's totality claim and §4's gate completeness rest on it. One
line. (B1 is a reminder of what happens when an enumeration lives only in prose.)

### L2 — §3.4's snippet does not name its home, and throws an `unknown`

`throw occupied.cause` throws a value typed `unknown` (`blob-store.ts:13`). More materially, round-5 M3
asked where the guard lands and v6 still does not say: the snippet reads `to.blob.tryGet(toP, key)` but
`copyAdditiveVideo`'s signature is `(to: MetadataStore, toP: Principal, toBlob: BlobStore, …)`
(`sync-run.ts:221-225`) and `ensureReceiverSlot`'s (`:167-170`) has no blob store at all. Name the
function. Round-5 L2 (the three adapters do not share a `list()` contract) is also still dropped.

---

## What I checked that would have found a defect of each class, and did not

- **The fallback's availability and servability (§3.5:240-244).** P4: `${padSerial(serial)}_${videoId}.md`
  passes the widened guard for every awkward `videoId` shape — leading `-`, leading `_`, an embedded
  `_`, and a nine-digit serial (24 characters against the 128 bound). The claim *"`videoId` is always
  ASCII … the fallback cannot itself fail"* is true. **It also survives serial coherence**: `applySerial`
  (`serial-filename.ts:20-25`) strips `/^\d+_/` once, so `003_12_abcdefgh.md` → `007_12_abcdefgh.md`
  correctly, and `reconstructVideo`'s `/^(\d+)_/` reads serial 3 from it. `remap`
  (`reconcile-serial.ts:116-139`) handles the fallback base like any other string — `${base}.md`,
  `MODEL_KEY`, `dig/${base}/`, the `-dig-deeper.md` basename — with no assumption that the base embeds a
  slug. Two videos cannot share a serial, so the fallback base cannot collide with a slug base. **The
  fallback itself is sound; B1 is about what later moves it, not about the fallback.**
- **`utf16le` (§3.2:123).** P3 reproduces round-5 P6 and confirms the fix. The second half of the brief's
  question is clean: `grep -rn createHash lib/ app/ worker/ scripts/` returns four non-test sites —
  `content-hash.ts:17` (markdown body, utf8), `pdf-render-version.ts:21` (HTML, utf8), `token.ts:12`
  (share token) — **none hashes a key**, so nothing disagrees with the encoder. Lone surrogates are
  reachable exactly as §3.2 says (`slugify`'s `.slice(0, 60)` cuts UTF-16 code units), and I note
  without filing it that the vault round-trip turns them into `U+FFFD`, which P5 shows is *also*
  rejected by the widened guard — so the conclusion is unchanged either way.
- **The `move()`-409 argument (§3.4:212-214).** P2 reproduces it independently: 409, destination body
  unchanged, source retained. The cloud side genuinely cannot clobber. That claim is correct and load-
  bearing, and it is why H2 is High and not Blocking.
- **Both directions of the additive create.** cloud→local: `LocalFsBlobStore` has `provesAbsence = true`
  and `statSync` resolves the APFS alias, so `absent` is proof — §3.4's core claim holds. local→cloud:
  the fail-closed-on-`unreadable` rule is a real improvement over v5's `exists()`; the residue is the
  false-`absent` case, folded into H2 rather than filed separately because v6 closed the larger half.
- **Behaviors 19/21/22/23 constructibility.** 19: the astral-letter title's slug key is rejected by the
  widened guard (P5), so the fallback fires and `003_${videoId}.md` serves — constructible, and it fails
  against v5, which refused instead. 21: `003_my summary.md` and `003_🎉-x.md` are both rejected by the
  guard (P5) — constructible, though see M1 about the *space* case not matching master. 22: P3 —
  constructible, and it fails against a `utf8` encoder. 23: constructible with a stub store. **All four
  are real falsifiers; the round-5 vacuity is genuinely fixed.**
- **The `list()` path under a relocation.** `paidKeysUnder` (`reconcile-serial.ts:102`) calls
  `blob.list(p, 'dig/${base}/')` with a possibly-Korean base — it is in §3.3's table, ends on a segment
  boundary, and returns ASCII leaves. The encoding side of the relocation is fine. B1 is about
  servability, not encoding.
- **§4 and §4.1.** The gate predicate and its "first two segments" carve-out are right; P1 re-confirms
  `=` and a leading `=` are accepted, so the marker choice is safe. §4.1's ⛔ is correctly marked
  unrunnable and I did not try to work around it. *"Cannot run" is a failure, and the spec says so.*

**NOT CONVERGED**
