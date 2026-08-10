<!-- codex-review: model=gpt-5.5 -->

**Await Audit**

Lease starts inside `reserve_serve_model`, before the RPC response reaches the app.

| Await | Location | In lease window? | v4 term |
|---|---:|---|---|
| `readFreshMagazineModel` -> `blobStore.get` | `serve-doc.ts:56`, `read-model.ts:36`, `model-store.ts:60` | Outside if before reserve | Not needed for lease sum |
| `blobStore.tryGet` | `serve-doc.ts:70` | Outside | Not needed for lease sum |
| `supabaseClient.rpc('reserve_serve_model')` | `serve-doc.ts:74` | Yes, from DB claim until response | Omitted |
| `readFreshMagazineModel` on `in_flight` | `serve-doc.ts:85` | No charge held by this caller | Not relevant to charged lease |
| `readTitleStableModel` on over-budget | `serve-doc.ts:92` | No release token returned | Not relevant to charged lease |
| `assertMagazineInputWithinCap` -> `countTokens` | `serve-doc.ts:112`, `gemini.ts:548`, `gemini.ts:82` | Yes | `COUNT_TOKENS_TIMEOUT_MS = 10s` |
| `generateJson` -> `generateContent` | `gemini.ts:549`, `gemini.ts:259` | Yes | `2 * REQUEST_TIMEOUT_MS = 120s`, if retries are passed correctly |
| `abortableSleep` | `gemini.ts:267` | Yes | `SERVE_BACKOFF_TOTAL_MS = 400ms` |
| `writeModelEnvelope` -> `blobStore.put` | `serve-doc.ts:117`, `model-store.ts:51`, `supabase-blob-store.ts:23` | Yes | `PUT_TIMEOUT_MS = 15s`, caller-side only |
| `supabaseClient.rpc('settle_serve_model')` success | `serve-doc.ts:126` | Yes, until settle reaches DB | Only guessed inside `SETTLE_SLACK_MS = 5s` |
| `supabaseClient.rpc('settle_serve_model')` catch | `serve-doc.ts:133` | Yes | Only guessed inside `SETTLE_SLACK_MS = 5s` |

Synchronous work inside the charged section also includes `GoogleGenerativeAI` construction and `getGenerativeModel` (`gemini.ts:511`, `:524`), prompt construction (`:527-545`), `JSON.parse`/Zod validation (`gemini.ts:262`, `types.ts:34-47`), section-count validation (`gemini.ts:550-552`), envelope Zod validation/serialization (`model-store.ts:33-35`), and `mdHash` (`serve-doc.ts:124`, `content-hash.ts:16-17`). v4 only gestures at some of this through `SETTLE_SLACK_MS`.

**Findings**

**Blocking — The 150,400 ms “worst case” omits the reserve RPC wait, so the CHECK floor does not prove the lease inequality.**  
Spec §3.2/§3.3: `docs/superpowers/specs/2026-08-10-serve-path-deadline-design.md:153-188`; code: `serve-doc.ts:74`, `0020_reservation_release.sql:217-254`. `createServerSupabase` does not set a DB timeout (`lib/supabase/server.ts:10-20`), while Supabase/PostgREST only applies timeout when configured (`PostgrestClient.ts:89-145`) and `rpc` is a POST (`PostgrestClient.ts:397-420`). Concrete failure: request A’s reserve transaction commits and charges at t=0, but the HTTP response stalls for 152s due to DNS/TLS/socket/proxy/network delay; request B arrives at t=151.1 with `lease_ttl_seconds = 151`, the reclaim clause sees `lease_expires_at < now()` and charges a second producer; A then receives its token and starts generation. Raising the floor to 151 does not help because the omitted term can be larger than any configured floor.

**Blocking — `SETTLE_SLACK_MS = 5_000` is not an enforced bound, but the constraint treats it as one.**  
Spec §3.2 and §4: `docs/...deadline-design.md:156-163`, `:171-178`, `:320-336`; code: `serve-doc.ts:126`, `:133`. The settle RPC is an unbounded Supabase POST, and no timeout/race is specified for it. Concrete failure at the allowed floor: countTokens consumes 10s, generation consumes 120.4s, put consumes 15s, parsing/hash/event-loop overhead consumes 700ms, and settle takes 1s to reach Postgres. Total is 152.1s, so a second request can reclaim before settlement. The CHECK permits exactly this configuration.

**High — The “serve-path-only” retry reduction is not exposed at the serve boundary.**  
Spec §3.1/§3.5: `docs/...deadline-design.md:145-147`, `:216-227`; code: `serve-doc.ts:112-116`, `gemini.ts:499-549`, `html-doc/generate.ts:40`. `generateJson` has a `retries` parameter, but `resolveMagazineModel` calls `generateMagazineModel`, whose current signature has no retry override. Changing `gemini.ts:549` from `undefined` to `1` changes every `generateMagazineModel` caller, including local generation. Concrete failure: a local transform that currently succeeds after two transient failures and a third success will fail after v4’s “one-argument change.” To make this serve-only, the spec needs an explicit `generateMagazineModel` option and tests proving local/default callers still get `GENERATE_JSON_RETRIES`.

**High — The put-timeout residual risk is understated: the upload can still complete late and overwrite a later producer.**  
Spec §3.1 and §4: `docs/...deadline-design.md:149-151`, `:332-337`; code: `model-store.ts:51`, `supabase-blob-store.ts:22-24`, storage-js upload uses plain fetch without a signal in this call path. A caller-side race cancels only the app’s wait, not the upload. Concrete failure: A times out waiting for `put`, settles keep, B reserves and writes a model, then A’s original in-flight upload completes later with `upsert:true` and overwrites B. If the source markdown changed between A and B, the stored envelope can regress to the older `sourceMdHash`. `max_serve_attempts` bounds new charges per `(owner, doc, day)`, not late writes or cross-day repeats.

**Medium — The 600 ms margin at the CHECK floor is operationally non-survivable.**  
Spec §3.2/§3.3: `docs/...deadline-design.md:153-188`. Even if the explicit network omissions above are fixed, floor `151` leaves only 600ms over the stated 150.4s. That margin must cover timer overshoot, JS scheduling, GC, JSON parse, Zod validation, hashing, model construction, prompt construction, response text extraction, and Supabase client overhead. Concrete failure: any operator setting the legal floor converts routine millisecond-scale variance into lease expiry and duplicate paid producers. The practical floor needs a real tail budget or the CHECK must require materially more than `ceil(worst_case_ms / 1000)`.

**Medium — “Bound every call” is false as written for Supabase calls.**  
Spec §2.1/§3.1: `docs/...deadline-design.md:79-82`, `:130-151`. The table says external calls are bounded by per-call timeout, but reserve/settle are external Supabase calls and are not bounded; storage reads before reserve are outside the lease but still unbounded request latency. I checked `lib/supabase/server.ts:10-20`, `supabase-js` construction at `SupabaseClient.ts:380-386`, and PostgREST timeout support at `PostgrestClient.ts:108-145`.

**Low — v4 loses v3’s live remaining-time guard and does not acknowledge that loss.**  
Spec §3.0/§3.4: `docs/...deadline-design.md:117-128`, `:204-214`. This is not a reason to restore v3’s protocol, but it is a real lost property: a runtime deadline would have bounded unmodeled local overhead and late arrival after reserve. v4 replaces that with a static sum plus a CHECK, so omissions in the sum become invisible until production.

Checked: spec v4 at commit `5a7548c`, `serve-doc.ts`, `generateMagazineModel`/`generateJson`, model store/read path, Supabase blob adapter, migrations `0011/0012/0020`, Supabase/PostGREST/storage client sources, Gemini SDK d.ts/implementation, and current caller set for `generateJson`/`generateMagazineModel`.

NOT CONVERGED.
