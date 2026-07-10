# Claude Adversarial Review — Stage 1F-c Downloads spec (v1)

**Reviewer:** Claude (opus), independent · **Date:** 2026-07-10.
**Verdict:** 0 Blocking, 2 High, 3 Medium, 3 Low. Money invariant (D4/D5/D10) genuinely holds — MD short-circuit verified before every charge point on both routes, confused-deputy untouched — but the spec drops the share revocation re-check on the MD path and ships an inline raw-HTML-capable response with no anti-sniffing header.

## High
- **H1 — Share MD download skips the mandatory pre-response re-check (revocation window).** The share route re-checks `getShareServeContext` at `s/route.ts:57-59` before emitting bytes (closes B10b/D14). The spec's `format=md` branch returns at `:45`, *before* that. A token revoked / doc un-promoted between the initial resolve and the response is still honored for MD. Contradicts D6/§7 "1F-b invariants preserved". No behavior row for revoke-mid-MD-download. **Fix:** MD branch must run the same re-check before returning; add a B10b-style MD test + behavior row. *(Codex ranks this Blocking — adopt Blocking.)*
- **H2 — inline `format=md` has no `X-Content-Type-Options: nosniff` / CSP → sniffing XSS.** Raw AI/worker-authored markdown served inline as `text/markdown` can contain `<script>`/`<html>`; a sniffing UA executes it on the app origin — worst case owner content executing in a share recipient's authenticated origin. The only response the slice adds with no content-safety header. **Fix:** `nosniff` on all MD responses; default MD to attachment or serve inline MD as `text/plain`.

## Medium
- **M1 — `asciiSafe`/`encodeRFC5987` under-specified for header injection.** Title is attacker-influenceable; the strip set omits CR/LF/C0 controls + backslash; `title ?? base` doesn't catch empty-string. **Fix:** strict allowlist encoder for `filename*`; `asciiSafe` strips `[\x00-\x1f\x7f]"\/;`, trims dots/spaces, empty→fixed `summary`.
- **M2 — D10 overstates B18b coverage: the new `file-response.ts` helper isn't in the guard scan set** (`app/s`, `lib/share`, `read-model.ts` only). **Fix:** add `lib/html-doc/file-response.ts` to `shareSources`, or soften D10. *(Codex ranks this High.)*
- **M3 — "byte-identical" overstated once routed through `fileResponse`.** Owner view has no `Referrer-Policy`; share does; nonce differs per response. **Fix:** restate as "same status + same header name/value set + same body modulo nonce + no Content-Disposition when download absent"; regression test asserts owner no-param response has no Referrer-Policy.

## Low
- **L1 — `ShareServeContext.title: string` may be `undefined` for legacy/unvalidated rows** (seeds omit title). Type as `title?: string` + coalesce to base.
- **L2 — downloaded share HTML loses CSP offline;** any inline print-button script runs from `file://`. Owner's own share-stripped content, `file://`-sandboxed → Low. Assert the doc's print control is script-we-control (`window.print()` only), or note accepted.
- **L3 — owner `format` vs `type` validation order unspecified** (`?format=pdf&type=bad`). Pin it (type first, then format).

## Verified sound (evidence)
Owner MD never charges (branch between `route.ts:61`–`:75`, before `resolveMagazineModel` at `:75`). Share MD never charges (before `readFreshMagazineModel`; read-model is a verified generate-free leaf). Owner isolation intact (after owner-assert + status gates). Share confused-deputy intact (title from the same owner-scoped `vid.data` row; no new query, no cross-tenant leak). Corrupt/missing share MD → coarse 404. `Video.title` required in schema.

## Bottom line
Address H1 (re-check on MD share branch) + H2 (nosniff) — each reopens a guarantee the spec claims preserved; M1–M3 resolve in spec text before the plan.
