# Task 9 — `pdfHref` client URL builder — dual review trail

**Files:** `lib/client/api.ts` (added pdfHref) + test. Base 52f76d7 → head (T9 + injection test).

## Both passes: Approved — 0 Blocking/High/Medium
- **Codex:** `pdfHref` builds `/api/pdf/${encodeURIComponent(videoId)}?playlist=…&type=summary` — matches the route contract (path id, `type===summary`, UUID `playlist` per route.ts:25/31-33); param order `playlist,type` mirrors summaryHref; playlist query-encoded via URLSearchParams. **Low:** test only proved space-encoding, not path/query-injection resistance.
- **Claude:** exact parity with summaryHref's convention; test uses `new URL()`+`searchParams.get` (non-vacuous); minimal diff (summaryHref + rest of api.ts untouched); only new `pdfHref` + its test added. Cosmetic note (object-literal URLSearchParams vs summaryHref's `.set()` — functionally identical, not worth changing).

## Fix (Codex Low)
Added an injection test: videoId `vid/1?x=2#frag&y=z` → whole id stays in one path segment (`/api/pdf/vid%2F1%3F…`), `u.hash===''`, only `playlist`+`type` query params (no injected `x`/`y`). Pins that `encodeURIComponent` prevents path/query injection.

**Final:** pdf-href 2/2; full suite 2072/2072; tsc clean. Both passes converged (0 Blocking/High); trivial pure builder, injection-safety now pinned.
