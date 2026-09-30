---
name: stage3-cloud-sync-branch-state
description: "FIRES-WHEN: citing Stage 3 cloud sync or PR #23 — Stage 3 Cloud Sync (M2a) MERGED (PR #23) after 7 whole-branch review rounds; cloud verification deferred to M1.4"
metadata: 
  node_type: memory
  type: project
  originSessionId: ec2b8b91-61e0-42e1-b2f1-c2eb82b7915f
---

`feat/stage3-cloud-sync` (M2a) — ✅ **MERGED to master (PR #23, merge commit `d2bf143`, 2026-07-19)**;
branch deleted. Converged at whole-branch review round 7. 52 commits, 86 files. tsc clean, 2450 unit / 245 suites, cloud-sync integration 46/46.

Review trail (all in `docs/reviews/whole-branch-cloud-sync{,-v2..-v6}-rereview-{codex,claude}.md`
plus `-v7-focused-{codex,claude}.md`): R1 1 Blocking + 2 High → R2 2 High (one a regression from R1's
fix) → R3 **1 Blocking** → R4 3 High (one a regression from R3's fix) → R5 1 High (both reviewers) →
R6 1 defect (severity split) → R7 focused, both CONVERGED, 0 findings.

**Dominant root cause, worth carrying to other slices:** *a value meaning "absent" is also what a
failure produces.* `SupabaseBlobStore.get` is `if (error) return null` — it swallows network/5xx/
timeout/RLS — while `LocalFsBlobStore.get` nulls only on ENOENT. Remedy shipped as
`BlobStore.provesAbsence` (optional, absent ⇒ false ⇒ fail-closed). Four separate Blocking/High
findings were instances of this one shape (MD bodies, model envelopes, playlist titles).

**Process facts that actually changed outcomes** — see [[dual-review-what-it-catches]]:
- Reviewers split 3× on severity; the *finding* reviewer was right all 3×, twice while the other
  returned CONVERGED. Adjudicate by reading the code, never by majority.
- Mutation-testing every new guard (reintroduce the bug, confirm red) caught one guard with ZERO
  coverage that a fully green suite concealed.
- `scripts/codex-frontier-model.py` returned a slug the pinned Codex CLI (0.142.5) cannot run →
  HTTP 400. It ranks by `priority` without filtering on client-version support, so the Codex half of
  the review gate can silently no-op. Read the output FILE, not the exit code. `gpt-5.5` works.

**Six deferred findings** with rationale in `docs/roadmap-to-launch.md` under "M2a deferred findings"
— the two most substantive are M-R7-1 (companion freshness guard judges a CLOUD receiver against the
LOCAL `GENERATOR_VERSION`; correct for copyToLocal, inert for copyToCloud under deploy skew) and
Claude-R3-M1 (dig-deeper view can serve a pre-sync summary when replica keys diverge).

**Pre-existing, NOT caused by this branch:** `tests/integration/reservation-release.test.ts` fails
identically on a stashed clean tree — local Supabase state pollution (leftover `ledger_audit` rows,
stale queued job). Needs a DB reset or per-test isolation. Verify by stashing before blaming a branch.

Nothing here was verified against a real deployment — all 46 integration tests run on local Supabase.

**Named follow-up slice (in `docs/roadmap-to-launch.md`): the honest-blob-read (`BlobRead`) slice.**
Make `BlobStore.get` return a discriminated result instead of `Buffer | null`, so the compiler forces
every caller to say whether it means *absent* or *unreadable*; retire the `provesAbsence` side-channel.
Also delete the `setPlaylistMeta` footgun (omitting the optional title ERASES it; the safe
`setPlaylistTitleIfNull` already existed and was simply not called).

**The money-path instance it was named for is CONFIRMED and FIXED** — ✅ merged to master (PR #24,
squash `7e75be7`, 2026-07-19). A transient Storage failure made an EXISTING magazine model look absent,
so the serve path reserved and regenerated: measured `spend 6→12, gemini_calls=1, attempt_count=2`;
after the guard `status=busy, spend 6→6`. No prod infra was needed — the repo already had
fault-injecting blob-store wrappers and spend_ledger assertions, and the `null` a transient error
produces is byte-identical to a 404's. Fix: `BlobStore.tryGet` returning a discriminated `BlobRead`
(REQUIRED, so tsc listed all 7 implementers), Supabase 404-detection verified against the live stack,
and `resolveMagazineModel` returning `busy` instead of spending on an unprovable read. Regression test
`tests/integration/serve-model-unreadable.test.ts`.

**Lesson worth reusing:** the finding sat as an unverified roadmap line headed for a deploy-time check;
one test file settled it in minutes. When a suspected defect can be expressed as an assertion, build the
assertion instead of scheduling a manual check — see [[dual-review-what-it-catches]].

**Still open:** the FULL honest-blob-read slice (~10 remaining `blob.get` callers, retiring
`provesAbsence`) — own spec + merge gate, fresh session. And the local reproduction cannot prove a REAL
hosted 5xx carries a non-404 `statusCode`, so a narrowed M1.4 check remains.

**Post-merge state (2026-07-19):** M2 Sync milestone COMPLETE. Path to launch is now M1 (1.1 live-Gemini
verification, 1.3 prod infra, 1.4 deploy) then M3 acceptance. **M1.4 carries five specific cloud-sync
checks** written into `docs/roadmap-to-launch.md` — round-trip with RLS-correct blob paths, the B1 guard
under a live unreadable blob, the serve-doc money inference (inject a Storage 5xx, watch spend_ledger),
M-R7-1 GENERATOR_VERSION skew, and service-role confinement against the real environment. The serve-doc
result can promote the honest-blob-read slice from post-launch to pre-launch.

