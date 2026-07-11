# Codex Adversarial Review — Stage 1G per-owner serve budget spec (v1)

**Reviewer:** Codex (gpt-5.5, from coordinator) · **Date:** 2026-07-10

## Blocking
- **R1/§6 — `create or replace` must restate the full function attributes.** If 0014's replacement omits `security definer set search_path = public`, the RPC reverts to SECURITY INVOKER → writes to force-RLS/no-policy tables (`serve_model_charge`, `spend_ledger`, new `serve_owner_budget`) fail → owner HTML materialization → RPC error → route 500. Grants/ownership DO survive a same-signature replace, but the definer/search_path attributes are part of the definition. Fix: 0014 restates the complete header (`create or replace … returns text language plpgsql security definer set search_path = public as $$…$$`) + restate `revoke all … / grant execute … to authenticated, anon` for auditability. Do NOT `drop function`.

## High
- **D5 — "serve last-materialized doc state" is false with the current renderer.** Route renders the **current** `parsed` (route.ts:93/109) against the **stale** `model`; `render.ts:82` pairs `parsed.sections[i]` with `model.sections[i]` by position. If titles were edited/reordered, current heading X shows old lead/bullets for A; extra current sections silently vanish (`if (!m) return ''`). Schema-valid → won't crash, but serves misleading hybrid content. Fix: serve stale ONLY for generator-version staleness where titles still match current (else 503), or persist a source snapshot in the envelope. If title/content-stale fallback ever remains, require a visible banner, not just `X-Magazine-Stale`.

## Medium
- **Global-first ordering → avoidable global row-lock contention.** An over-budget owner repeatedly viewing invalidated docs locks `spend_ledger` (5a) then rolls back on 5b failure each time — no phantom spend, but contends on the global money row and can slow other tenants. Fix: run the per-owner arbiter FIRST (5b before 5a), roll back on global failure; or keep `at_capacity` precedence and document + consider a cheap precheck.

## Low
- **Behavior table missing the key per-owner concurrency contract:** same owner, two different docs, exactly one 6¢ slot left, global has room → one `reserved`, one `owner_over_budget`; both ledgers +6 exactly; only the winner gets a `serve_model_charge` marker. Add as P15.

## Confirmed sound
No atomicity money leak — the `begin … exception … end` sub-block (0012:55) is the right savepoint; PJ004/PJ005 roll back the lease claim + both increments. Conditional UPDATE on (owner,day) serializes same-owner races. Share path never calls reserve_serve_model (s/[token]:81). Owner format=md returns before model resolution (route:84). Cap boundary `spent+est<=cap` exact; lowering cap below spend just blocks, no underflow.
