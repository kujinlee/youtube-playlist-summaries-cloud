# Task 18 — Codex adversarial review (frontend + endpoints)

Model: gpt-5.5 (`--fresh`). Scope: `git diff 08042e9..4cb115b`.

## Blocking
- **Header.tsx:75 — untrimmed root.** Gating uses `root.trim()` but the resolver keys/fetches
  with raw `root`. `/data ` → target `/data /slug/raw`, `canAct` true, `onIngest` fires with a
  wrong folder before blur normalization. → one `trimRoot = root.trim()` for `currentKey`,
  debounce emptiness, fetch param, `resolvedKey`, submit gating; also trim in `/api/resolve-folder`.

## High
- **Header.tsx:127 — `handleRootBlur` has no stale guard.** A slow `/api/normalize-folder`
  response for an old root can `setRoot` after the user typed a different root → silent root
  mutation + resolve for the wrong root. → `normalizeSeq` ref mirroring `resolveSeq`.
- **page.tsx:228 — Browse persists a stale pair.** `onRootChange(newRoot)` persists with
  `outputFolderRef.current` still the old folder; `onFolderChange(picked)` does not persist →
  reload reopens the wrong folder. → persist the combined `{root, pickedFolder}` atomically.

## Medium
- **resolve-folder/route.ts:21 — `get('root') || fallback` treats explicit empty `?root=` as
  absent**, silently anchoring on settings. → distinguish absent (`=== null`) from blank;
  blank → 400.

## Cleared (asked to attack, found safe)
No exploitable stale-response path through `resolveSeq` / `resolvedKey === currentKey`. Old
responses are blocked by the post-`await res.json()` seq check or the key mismatch on re-render.
The self-correct path converges: after `setRoot`, `currentKey` changes, old `resolvedKey` no
longer matches, `isFresh` stays false until the new resolution lands.

## Test gaps (not caught by the 604-green suite)
whitespace roots; stale `/api/normalize-folder` responses; explicit empty `?root=`; browse
persistence ordering. B15/B16 catch the old auto-suggest bug but not a wrong target from an
untrimmed root.

## Resolution
All Blocking + High + the Medium folded into a single fix batch (Task 18): trim root end-to-end,
`normalizeSeq` guard on blur+browse, a debounced page-level persist effect that always writes the
latest consistent `{baseOutputFolder, outputFolder}` pair (fixes Browse ordering), and
absent-vs-blank `?root` handling. New tests added for each gap.
