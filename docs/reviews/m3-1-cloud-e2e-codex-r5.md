<!-- codex-review: model=gpt-5.5 -->

**Blocking:** none found.

**High:** none found.

**Medium:** none found.

**Low:**
- [tests/e2e/cloud-journey.spec.ts:159](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/tests/e2e/cloud-journey.spec.ts:159) Rung 4 is close, but it does not directly assert “fresh envelope accepted.” `200 + seeded lead visible + no ledger movement` rules out the live paid regeneration path in the normal CLI run, and `at_capacity` would be a 503. But it still does not distinguish the intended `readFreshMagazineModel` early return from the B4 title-stable stale fallback if that path ever becomes reachable. The single assertion I’d add is `expect(res?.headers()['x-magazine-stale']).toBeUndefined()` / null. That directly rejects the stale fallback path already marked by [app/api/html/[id]/route.ts:92](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/app/api/html/[id]/route.ts:92).

**Targeted Checks:**
- Seed correctness: confirmed. The exact seeded markdown has one `## 2. Encoder`; [parse.ts:53](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/html-doc/parse.ts:53) strips the ordinal into `numeral`, so titles are `['Encoder']`, matching [cloud.setup.ts:126](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/tests/e2e/cloud.setup.ts:126). If the fixture gains a second `##`, both `sourceSections` and `model.sections` must grow in lockstep or freshness fails / rendering drops a section.
- Guardrail pin: no finding. `reserve_serve_model` reads `daily_cap_cents`, `magazine_est_cents`, `max_serve_attempts`, `lease_ttl_seconds`, and `per_owner_serve_daily_cents`; pinning the first two is coherent for this fresh-path test because a new owner gets at least one serve attempt under the DB check. Concurrent suites remain unsafe because the singleton is shared, but this stack already has that property.
- Loopback assertion: no finding. It runs before fixture deletion at [cloud-global.ts:146](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/tests/e2e/cloud-global.ts:146). It can reject legitimate aliases like `host.docker.internal`, but that is a conservative local-only gate, not a bypass.
- `update().select('id')`: no finding. That is the right PostgREST/Supabase pattern to get matched rows back; matched-but-unchanged rows still return.
- UI/watch narrowing: no finding. The comment now honestly scopes the guard to CLI at [cloud-global.ts:78](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/tests/e2e/cloud-global.ts:78). The other side is real: UI mode can still run a silently stale fixture, but the branch no longer claims support for that mode.
- Load-bearing comments: no additional false guarantee found.

CONVERGED
