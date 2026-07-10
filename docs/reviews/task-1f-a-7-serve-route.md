# Task 7 review — cloud serve branch on `GET /api/html/[id]` (auth/serve boundary + money-path wiring)

**Commits:** `b93e65a` (impl) → `d38c11b` (auth/money test depth)
**Gate:** single round Claude + Codex, both at high scrutiny (auth boundary + money wiring). Execution: SDD.

## Reviews — both SOUND/Approved, no Critical/High
### Money-path adjudication (the flagged concern) — RESOLVED, both reviewers independently: `base != videoId` is SAFE
The Task-6 carry-forward assumed `base===videoId`; the implementer found the real worker keys MD as `${padSerial(serial)}_${slug}.md`, so `base` (= that serial_slug baseName) ≠ `videoId`. It shipped the real code (`base` from the promoted `artifact.summaryMd.key`, minus `.md`) with a coherence comment instead of a false assertion. Both reviewers traced the three coherence properties and confirmed safe:
- **(a) Deterministic/stable per doc:** `mdKey = artifact.key ?? video.summaryMd`; 0009 `persist_summary` sets `artifacts.summaryMd.key` to the same `${baseName}.md` the worker wrote → every view reads the same frozen row → same `base` → `readModelEnvelope` HITS → `resolveMagazineModel` returns `ok` **before** the reserve RPC. **No re-charge per view.**
- **(b) No cross-doc collision:** blob keyed on `(principal=(owner,playlistKey), base)`, serial unique per video within a playlist → base unique per doc; same video in two playlists → different principal AND base. **No wrong-model serve.**
- **(c) Read==write base:** one `base` var for both read/write; the charge keys on a different namespace (`doc_key=playlistId/videoId`) governing only the lease/charge. Coherent.
A literal `base===videoId` assertion would have thrown on **every** real request — the implementer was right.

### Other boundaries — verified sound (both)
- **B20 confinement REAL:** route imports only session/anon-scoped helpers; `reachesService(route)===false`; NOT in `ALLOWED_SERVICE_IMPORTERS`; `check:confinement` → "service_role confinement OK"; the route test's `getStorageBundle` mock throws on a bare (service-role) call and asserts the exact `createServerSupabase` return was passed.
- **UUID→400 (D9):** `UUID_RE` + `assertVideoId` run before any DB call → malformed playlist = 400, never a `22P02` 500.
- **CSP strict/coherent (D7):** `buildSummaryCsp` = `default-src 'none'`, nonce'd script/style, no `unsafe-*`; the single `<style>` + every script helper carry the nonce; `dig:false` suppresses navScript (D12); `Cache-Control: private, no-store`.
- **Owner isolation (B9/B10):** RLS + explicit `owner_id===auth.uid()` assert; integration `html-serve-isolation` 2/2 on real DB (own registered+anon 200; foreign 404 both directions).
- **Status→HTTP:** ok→200, busy/attempts_exhausted/at_capacity→503, denied→404, committed→503, non-promoted→404, blob-null→409, no-session→401.
- **Local path preserved** with the intentional `playlist`-param→400 guard.

## Test-depth fix (`d38c11b`, test-only; each proven genuine by temporary source mutation)
1. **Foreign/absent playlist → 404** (Claude Medium — the owner-assert-fail→404 route line was untested): `resolveOwnedPlaylistKey` mock → null → assert 404. (Proven: flipping the branch to 200 fails the test.)
2. **base-derivation coherence** (Codex Low): `artifact.key="0001_intro.md"` + a distinct videoId → assert `resolveMagazineModel` receives `base:"0001_intro"` + videoId unchanged. (Proven: `base=videoId` fails.)
3. **`<style>` nonce assertion** (Claude Low — silent CSP-regression guard): assert every `<style` tag carries the response nonce. (Proven: stripping the style nonce fails.)

## Carry-forward → Task 9 whole-branch triage (honest residuals, both acceptable)
- No test drives the real route against a real DB end-to-end (route tests mock the primitives; the integration test drives the primitives directly) — documented F7 scope trade-off.
- Validation-before-auth ordering: an unauth `type=dig-deeper` returns 400 before 401 (leaks nothing) — note only.

## Result
Tests: cloud 16 + local 22 + confinement 3 + isolation 2 (real DB); full suite 1746; tsc clean; `check:confinement` OK. **Task 7 COMPLETE.**
