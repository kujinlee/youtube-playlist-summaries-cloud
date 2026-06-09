# Task 17 — Codex adversarial review of the Enumerated Behaviors table

Model: gpt-5.5 (`--fresh`). Scope: the behaviors TABLE for the Header + endpoints + page
wiring of "auto-derive output folder from root + playlist URL" — reviewed **before** writing
any test code. All Blocking + High findings were folded into the hardened table in the plan
(`~/.claude/plans/atomic-moseying-bengio.md`).

## BLOCKING

1. **[E2, P1] No-root resolve must normalize the settings root.** Anchoring on the raw stored
   `outputFolder=/d/cs146s/raw` yields `/d/cs146s/raw/<slug>/raw`. → `anchor =
   normalizeToRoot(settings.baseOutputFolder ?? settings.outputFolder)`; return that normalized root.
2. **[B3,B4,B8,B13,B14] Stale resolve/normalize responses can overwrite newer state.** → request
   sequence guard; apply a response only if it still matches the current `{url, root}`.
3. **[B4,B8] resolve→setRoot→resolve loop / false dirty flag.** Programmatic root correction must
   not set `rootEditedByUser` and must not re-trigger normalize unless the value actually changed.
4. **[B13,B14,B18] No "resolving" disabled state → double-click duplicate ingests.** → disable
   action buttons while resolving; fire callback at most once per click.
5. **[B8,B13,B14,B17,B18] Empty root unspecified.** → empty root is invalid: clear hint, skip
   resolve, disable Fetch/Sync, never call `onIngest`/`onSync`.
6. **[P2] Persist may write a mismatched `{root, outputFolder}` pair.** → define exact persisted
   `outputFolder`; always persist the current app-state pair, never a half-stale one.

## HIGH

- **[B3,B13,B18]** Cancel/ignore pending debounced resolves when submit/sync begins.
- **[B6]** Network error preserving a stale target misleads → clear or mark stale.
- **[B7]** "Only ONE resolve" → restate as "only the latest trimmed url/root pair is requested;
  earlier timers/responses ignored."
- **[B15,B16]** Regression guards too weak now that URL typing legitimately calls resolve-folder →
  assert URL entry never puts `outputFolder`/`<root>/<slug>/raw` into the root field; submit uses
  the resolved target while the field stays normalized root.
- **[B15]** Guard both `<root>/<slug>` AND `<root>/<slug>/raw` (the real derived shape).
- **[B9,B12,P4]** Browse to a non-playlist/root: clear or explicitly preserve `currentPlaylistUrl`.
- **[B9,P4]** Browse to the root itself unspecified → define normalize returns `/d`,
  `onRootChange('/d')`, `onFolderChange('/d')` root view.
- **[P2,P3]** Define whether ingest persists settings (persist `{root, target}` after resolution).
- **[B1,P1]** `defaultBaseOutputFolder` vs existing tests asserting the field shows
  `defaultOutputFolder` → explicit migration: field from `defaultBaseOutputFolder`,
  `defaultOutputFolder` stays the viewed/write target.
- **[B13,B14]** Existing tests assert `onIngest(url, fieldValue)`/`onSync(fieldValue, url)` →
  replace with resolved-target assertions.

## MEDIUM (incorporated where sensible)

- [E3,E8] Examples need the precondition that `<dir>/raw/playlist-index.json` exists (else
  `normalizeToRoot` returns the path unchanged).
- [E2,E3] Returned `root` is absolute + normalized by the same server helper.
- [B3,B8,B13,B14] Trim both URL and root; empty-after-trim is invalid.
- [B19] Clearing URL cancels pending resolve and clears the hint.
- [B5] Tie invalid-URL to the latest-request guard.
- [B10b] Pick succeeds but normalize fails → root unchanged, no `onRootChange`.
- [E7] Empty/blank `?path=` → 400, no helper call.
- [B1] Read-only hint has a defined placeholder/empty state and is never a valid callback target.

## Resolution

Architecture simplified in response: **the debounced resolve is the single resolver**; Fetch/Sync
are gated on a fresh target (`resolvedKey === current {url,root}`) instead of awaiting on submit.
This removes the submit-time await race (#4, High cancel-pending) and makes duplicate fires
impossible. See the hardened Enumerated Behaviors table (E1–E9, B1–B19, P1–P4) in the plan.
