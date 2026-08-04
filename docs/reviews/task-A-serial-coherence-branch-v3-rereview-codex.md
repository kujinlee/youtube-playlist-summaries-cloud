<!-- codex-review: model=gpt-5.5 -->

**Blocking**

None. I checked the round-2 fixes for cleanup-before-pointer, unsupported artifact ordering, exact `digDeeperMd`, and `noteCloudRow` call sites.

**High**

1. `lib/cloud-sync/reconcile-serial.ts:211` / `lib/cloud-sync/reconcile-serial.ts:227` — round-2 High is not genuinely fixed for concurrent rewrites.

Scenario: client A reads cloud `summaryMd: 007_alpha.md` and wants `003_alpha`; client B concurrently reads the same old row and wants `004_alpha`. Both copy paid blobs. B updates metadata to `004_alpha.md` and verifies. A then calls the non-conditional `updateVideoFields`, overwrites B’s pointer with `003_alpha.md`, re-reads, sees `summaryMd === 003_alpha.md`, and cleanup proceeds. The check proves only “the row now says my target key,” not “I updated the row I read” or “no one rewrote it first.” B’s copied paid blobs are orphaned and B’s move is lost.

`readIndex` is also a heavy probe here: Supabase `readIndex` performs playlist lookup plus a full videos select for the playlist, so this adds O(playlist size) DB/data transfer per relocated video. It is a usable zero-row detector, but not a compare-and-swap.

Fix: use a dedicated conditional relocation RPC. Lock the row and update only if current `summaryMd`, `serialNumber`, and relevant artifact/dig pointers still match the values from `cloudVideo`; return the updated row plus an affected/stale status. Cleanup only after that RPC returns the row that was actually updated.

**Medium**

1. `lib/cloud-sync/reconcile-serial.ts:98` — exact `digDeeperMd` matching refuses supported directory-qualified dig-deeper paths.

Scenario: a legacy/supported row has `summaryMd: "raw/007_alpha.md"` and `digDeeperMd: "raw/007_alpha-dig-deeper.md"`. This shape is accepted elsewhere: `buildDocHtml` treats `digDeeperMd` as a relative path and derives `relDir` from it, and PDF tests cover `raw/...-dig-deeper.md`. Current generated local digs from `lib/dig/dig-section.ts:83-106` are bare basenames, so new local-generated values match. But directory-qualified legacy values now hit `unmappable-key`, abort sync, and stay stuck where the previous remap could move them.

Fix: match the basename exactly, not the whole key: if `path.posix.basename(key) === ${oldBase}-dig-deeper.md`, preserve `path.posix.dirname(key)` and rewrite only the basename. Keep rejecting prefix matches like `003_ab-dig-deeper.md`.

**Low**

1. `lib/cloud-sync/reconcile-serial.ts:227` / `lib/cloud-sync/sync-run.ts:723` — a verification read failure after a successful metadata write leaves the run in an uncertain mutated state.

Scenario: `updateVideoFields` succeeds, then `readIndex` throws transiently. `reconcileCloudBase` throws past its typed `metadata-unverified` result; `sync-run` catches it per video and continues with `cloudSnapshot` still showing the old serial/base. The next run can converge the row, but old-base blobs are never cleaned because the row no longer diverges, and later videos in the same run make occupancy decisions from a stale snapshot.

Fix: catch verification read failures and return an explicit uncertain result; in `sync-run`, after any post-metadata uncertainty, either re-read the cloud snapshot successfully before continuing the playlist or abort the rest of that playlist for the run.

**Round-2 Fix Checks**

`unsupported-artifacts` is now before `paidKeysUnder` and every copy, so the round-2 duplicate-copy refusal bug is fixed.

`noteCloudRow` after `copyToCloud` now guards the `readVideo` result before calling it. The remaining non-null assertion is after `rec.action === 'relocated'`; under successful verification it should exist, but the uncertainty path above is still too loose.

Not converged. The deleted-row/no-op write case is fixed, but concurrent rewrite is still not protected by the new verification model.

---

## Adjudication (round 3) — coordinator, 2026-07-31

### High #1 — verification is a zero-row detector, not a compare-and-swap → **CORRECT, and NOT a regression this branch introduced**

The mechanism is exactly as described: `updateVideoFields` is unconditional, so re-reading proves
*"the row now says my target key"*, not *"I updated the row I read"*. Two concurrent syncs of the same
playlist can interleave, and A's write lands on top of B's.

**But this is a property of the whole Stage-3 sync write path, not of `reconcileCloudBase`.**
`transferClassA` (`sync-run.ts:380-418`) does `blob.put` then an unconditional `updateVideoFields`
with the identical exposure, as does `copyAdditiveVideo`. Making A3 alone compare-and-swap would buy
very little: the surrounding transfers would still race, on the same rows, in the same run.

Two changes made now:
- **The window is narrowed** from the whole copy phase (N blob round-trips) to the gap between two
  statements: the row is re-read immediately before the write and must still match the record the
  copies were planned from.
- **The remaining gap is named, not hidden.** A true conditional relocation RPC — lock the row,
  update only if `summaryMd`/`serialNumber` still match, return affected-row state — is the right
  fix, and it should cover **every** sync write, not just this one. That is a scoped follow-up to
  raise with the human, not something to bolt onto this branch asymmetrically.

On the cost note: `readIndex` is `O(playlist size)` per relocated video. Accepted — relocation is a
one-off repair of already-diverged videos, not a steady-state operation, and the steady state after
this branch is `action: 'agreed'`, which reads nothing extra.

### Medium #1 — exact `digDeeperMd` match strands directory-qualified rows → **CONFIRMED, fixed**

Verified from two directions. `raw/275_google-okf.md` is a supported `summaryMd`
(`tests/lib/pdf/pdf-path.test.ts:9,17`), and `buildDocHtml` derives `relDir` from exactly these
fields. More decisively, `dig-section.ts:83` builds the name from `path.basename(summaryMdName)`, so
a video whose `summaryMd` is `raw/275_x.md` carries a **bare** `275_x-dig-deeper.md` — the whole-key
comparison refuses that pair and strands the video where the previous code could move it.

Fixed as suggested: match the **basename**, preserve the directory, keep rejecting prefix matches
like `003_ab-dig-deeper.md`.

### Low #1 — a failed verification read throws past the typed result → **CONFIRMED, fixed**

Correct, and it is the absent-vs-unreadable rule applied to metadata instead of blobs: "nothing
happened" and "something happened and we cannot see what" were collapsing into one thrown error.
Now returns a typed `verification-unreadable`. Cleanup is skipped either way, so nothing paid is
destroyed under the uncertainty, and a later run re-reads and finishes it.

The second half of the suggestion — abort the rest of the playlist after any post-metadata
uncertainty — was **not** taken. It would stop a whole playlist over one uncertain video, and the
stale-snapshot consequence is bounded and fail-closed: a stale entry can only cause a later video to
refuse a relocation it could have made, never to make one it should not.

### Round-3 outcome

1 High (adjudicated: correct, pre-existing, narrowed + named), 1 Medium (fixed), 1 Low (fixed).
255 suites / 2579 tests green, tsc clean.

**Round 4 required.** The round-3 fixes changed the pre-write path on the money path, which is new,
unreviewed design.
