<!-- codex-review: model=gpt-5.5 -->

**Findings**

**High — The revised gate still implements the URL half with a literal `NEXT_PUBLIC_*` read, despite saying not to.**  
Spec §3 says to use the computed-key runtime path via `getSupabaseEnv()` and “not the inlined literal” at [docs/superpowers/specs/2026-07-24-dev-login-design.md](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-24-dev-login-design.md:74). But the spec’s own helper uses `process.env.NEXT_PUBLIC_SUPABASE_URL` at [docs/superpowers/specs/2026-07-24-dev-login-design.md](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-24-dev-login-design.md:108), and the plan implements the same literal at [docs/superpowers/plans/2026-07-24-dev-login-13.md](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-07-24-dev-login-13.md:413). Next’s installed docs say direct `NEXT_PUBLIC_*` references are replaced at `next build`; dynamic lookups like `process.env[varName]` are not. So the primary `DEV_LOGIN_ENABLED` flag is runtime and fail-closed, but the “runtime local-URL defense-in-depth” is not actually implemented as claimed. Use `getSupabaseEnv().url` or `process.env['NEXT_PUBLIC_SUPABASE_URL']` inside the server-only helper.

**High — The deploy assertion does not check the real runtime leak path for the new server-only flag.**  
Task 6 only greps `fly.toml` and `Dockerfile` for `DEV_LOGIN_ENABLED` at [docs/superpowers/plans/2026-07-24-dev-login-13.md](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-07-24-dev-login-13.md:659). But after the redesign, `DEV_LOGIN_ENABLED` is a runtime server env var, and this app’s deploy runbook uses Fly secrets as runtime env at [docs/deploy.md](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/deploy.md:54). Grepping repo files misses `fly secrets set DEV_LOGIN_ENABLED=true`, platform env, or launch-time env. This is still mostly H2 reworded, not fixed. Add a production smoke check that curls `/dev-login` and asserts 404, and/or a deploy/runbook assertion against the actual Fly machine env/secrets.

**Medium — Task 7’s bogus-credential probe is only sound for provider-disabled detection, not for “no password-capable users.”**  
Task 7 allows dashboard verification, or attempting `signInWithPassword` with bogus creds and confirming provider-level rejection at [docs/superpowers/plans/2026-07-24-dev-login-13.md](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-07-24-dev-login-13.md:693). That is sound only if the observed error clearly says the email/password provider is disabled. A normal “invalid credentials” response does not prove the provider is disabled and cannot prove there are no password-capable users. The plan says “not merely invalid credentials,” which helps, but it should remove bogus-creds as evidence for the “no password users” branch.

**Low — Test-env hygiene is stated globally but not consistently written into the new gate tests.**  
The spec requires suites reading these vars to set/delete them in `beforeEach` at [docs/superpowers/specs/2026-07-24-dev-login-design.md](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-24-dev-login-design.md:167). Task 5 follows that for `LoginPage` at [docs/superpowers/plans/2026-07-24-dev-login-13.md](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-07-24-dev-login-13.md:529), but Task 4’s `devLoginEnabled` tests restore only in `afterEach` at [docs/superpowers/plans/2026-07-24-dev-login-13.md](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-07-24-dev-login-13.md:365). Each test does call `setEnv`, so this is not a likely behavior bug, but it violates the stated hygiene rule.

**Round-1 Fix Verification**

B1: **Fixed, with a Task 7 caveat.** Spec §9 correctly separates Layer 1 prod Supabase Auth config from Layer 2 UI discoverability at [docs/superpowers/specs/2026-07-24-dev-login-design.md](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-24-dev-login-design.md:206), and §11/Task 7 require prod auth verification at [docs/superpowers/specs/2026-07-24-dev-login-design.md](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-24-dev-login-design.md:262) and [docs/superpowers/plans/2026-07-24-dev-login-13.md](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-07-24-dev-login-13.md:687).

H1: **Partially fixed.** The primary flag is now server-only and fail-closed at [docs/superpowers/plans/2026-07-24-dev-login-13.md](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-07-24-dev-login-13.md:355), and `force-dynamic` is valid for request-time rendering at [docs/superpowers/plans/2026-07-24-dev-login-13.md](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-07-24-dev-login-13.md:484). But the URL check still uses the inlined literal.

H2: **Not genuinely fixed.** The assertion only scans repo files, not actual runtime env/secrets.

M1: **Fixed.** The form uses hard navigation after password sign-in at [docs/superpowers/plans/2026-07-24-dev-login-13.md](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-07-24-dev-login-13.md:287).

M2: **Fixed.** The revised spec correctly explains local prod-build behavior using the new flag+URL pair at [docs/superpowers/specs/2026-07-24-dev-login-design.md](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-24-dev-login-design.md:83).

M3: **Mostly fixed.** The spec and login-page tests address it, but Task 4 should use `beforeEach` cleanup too.

**Bottom Line**

The plan has improved, but it has not converged yet. There are still new/unresolved **High** issues: the literal `NEXT_PUBLIC_SUPABASE_URL` contradicts the intended runtime defense, and the deploy assertion misses the runtime env leak path introduced by the server-only flag.
