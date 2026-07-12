# Dual Review — Stage 2c Task 7 (VideoRow wiring — mount ShareDialog + focus restore)

**Diff:** c8eb927..a597a23 (impl) + 1bcc280 (portal fix). **Date:** 2026-07-11. **Verdict: CONVERGED both.**

**Wiring (both reviewers correct):** showShare state + menuTriggerRef + useScope playlistId mirror the existing showCorrections pattern; onShare={() => {setMenuOpen(false); setShowShare(true)}} to VideoMenu; ShareDialog onClose restores focus to the ☰ trigger (sole restore path — ShareDialog has no self-restore); playlistId=cloud?scope.playlistId:'', videoId/videoTitle passed; import from ./cloud/ShareDialog. **Claude independently verified the focus-restore assertion is load-bearing** (removed the line → test fails with focus on <body>). Mock uses jest.mock + jest.requireActual keeping sibling exports (summaryHref/saveAnnotation/getQuickView) real. Local mode never mounts the dialog (Share item cloud+ready only). VideoRow 52/52 unchanged.

**Codex R1 HIGH (Claude missed):** ShareDialog rendered a `<div>` under `<tbody>` — invalid DOM nesting (VideoRow is a table row). Existing CorrectionsPanel portals to document.body for exactly this reason; ShareDialog did not. **Controller verified against source** (CorrectionsPanel:78/131 createPortal; ShareDialog none; both mounted as fragment siblings of `<tr>`) — Codex correct. Pattern: Codex caught the structural defect Claude approved past (consistent with 2b).

**Fix 1bcc280:** ShareDialog wraps its JSX in `createPortal(..., document.body)` with a `typeof document === 'undefined'` SSR guard, mirroring CorrectionsPanel; no internal logic changed. **R2 Codex CONVERGED** — portal correct, focus trap/inFlightRef/guardedClose/tokens/data-testid intact, no regression; DOM-nesting warning confirmed gone (0 grep matches).

share-dialog 18/18, video-row-share-2c 1/1, VideoRow 52/52, full suite 1989, tsc 0.
