# Claude Task Review — Stage 2b Task 9 (CloudApp wiring, integration)

**Reviewer:** Claude (independent subagent). **Diff:** `b2d35ed..3fb7b93`. **Date:** 2026-07-11.

## Verdict (round 1)
- **Spec compliance:** ✅ — wiring contract verbatim. reqSeq guard in try+catch before all setState; onIngestSuccess closes modal (setModalOpen(false)) → setSummary → router.push; IngestSummaryNotice gated summary.playlistId===playlistId (no clear-effect); banner key={bannerNonce}; Refresh disabled/re-POST/no-nav/401/IngestError all correct; reset before fetch. Traced R3 test non-vacuous (never-resolving A → stale drop). 21/21 across cloud-app-ingest + 2a cloud-app + sidebar; full suite 1953; tsc 0.
- **Code quality:** Approved. Real tokens.

## Miss vs. Codex + related Minor (controller adjudication)
Claude approved and thoroughly verified the reqSeq **async** guard but did NOT flag the **synchronous** retained-state window Codex rated High (Refresh enabled with A's URL for one render after A→B nav, before the reset effect runs). Claude DID independently flag the root cause as a Minor: the reqSeq guard "silently depends on PlaylistLibrary not being keyed by playlistId — a future `key={playlistId}` refactor would break it." Both point at the same defect: `playlistUrl` isn't tied to playlist identity.

**Controller decision:** fix by making `playlistUrl` purely DERIVED from an id-tagged `urlEntry` (`entry.playlistId === playlistId ? url : null`) and dropping the manual reset. This makes the spend path correct-by-construction (timing- and key-independent), closes Codex's High, and removes Claude's fragile-invariant Minor in one move — and becomes a discriminating, RTL-testable property. Re-review both (spend-path behavior change). See `-codex.md` + `-v2-rereview.md`.

## Claude Low (noted)
onRefresh's own createIngest result isn't null-checked before setSummary — fails safe (id-match gate → notice just doesn't render), no crash/spend. Acceptable.
