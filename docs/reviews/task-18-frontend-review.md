# Task 18 — Claude code review (frontend + endpoints)

Scope: `git diff 08042e9..4cb115b` — Header root-field/derived-target, page wiring,
resolve-folder `root` param, normalize-folder route. 604/604 green, tsc clean.

## Critical
None. The #1 risk (silent wrong-folder write) is properly defended: `onIngest`/`onSync`
cannot fire with a target resolved for a different (url, root) pair — the `resolvedKey ===
currentKey` freshness gate + the `resolveSeq` stale guard (checked on both sides of
`await res.json()`) + the self-correct re-key keep the button disabled until the preview
matches the current inputs.

## Important
1. **Lost coverage — URL trim before `onIngest` is no longer tested.** `onIngest(trimUrl, …)`
   is correct but the old "trims whitespace" test was dropped and not replaced; B13 uses a
   clean URL. → add a Header test typing `"  <URL>  "`, settle, Fetch, assert `onIngest`
   got the trimmed URL and the resolve call used the trimmed `url=` param.
2. **Root not trimmed before resolve/key.** Effect guard `if (!trimUrl || !root)` trims the
   URL but not the root; a whitespace-only root is truthy → resolves garbage
   `path.join("   ", slug, "raw")`, while `isFresh` checks `root.trim() !== ''` — guard and
   freshness disagree. → `const trimRoot = root.trim()`; guard/key/fetch on `trimRoot`.

## Minor
3. Sync onClick (`target && onSync(...)`) lacks the `canAct` re-check `handleSubmit` has —
   safe today (same render) but asymmetric. → `onClick={() => { if (canAct && target) onSync(target, trimUrl); }}`.
4. `keyFor` space separator — theoretical collision (`"a b"+"c"` vs `"a"+"b c"`); use a
   delimiter not present in either value (e.g. `\n`).
5. `resolve-folder` `get('root') || fallback` treats empty `?root=` as absent — intentional
   and correct for this client; no change.

## Verified OK
- Endpoint error mapping (400 invalid / 500 generic no-leak), blank-path guard, anchor
  normalization for both `?root` and the settings fallback (E2/E3/E5/E6/E7).
- Effect deps `[trimUrl, root]` omitting stable `onRootChange` (documented eslint-disable);
  self-correct convergence (idempotent normalize → `data.root === root` second pass, button
  stays disabled mid-cycle); seq guard across both awaits + early-return invalidation.
- Page refs current at read time; no mismatched-pair persist window; `currentPlaylistUrl`
  clear-on-empty with `urlEditedByUser` still protecting user-typed URLs.
- B15/B16 regression guards genuinely assert no `<slug>/raw` into the root field and no
  `/api/playlist-info` call.

## Test gap noted
No direct out-of-order stale-response test (slow-first/fast-second) for the seq guard — the
most safety-critical code path. B7 covers debounce coalescing only.

**Action:** fix Important #1, #2 before merge; #3, #4 cheap hardening; add the stale-response test.
