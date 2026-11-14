---
name: launch-roadmap-state
description: "FIRES-WHEN: needing launch status, what is deployed, or a prod ops recipe (claude_ro, the prod smoke, a prod session) — M1/M2/M3 closed; DERIVE current state from git + flyctl + docs/roadmap-to-launch.md; this file holds only the prod facts and recipes the repo does not"
metadata:
  node_type: memory
  type: project
  originSessionId: 39a195b3-d01f-4d5a-af05-18d8fbdbde18
  modified: 2026-08-21T22:44:45.843Z
---

**The rule: all three launch milestones (M1 Deploy, M2 Sync, M3 Acceptance) are closed. Never read
current state out of this file — derive it.** `docs/roadmap-to-launch.md` is canonical (its `▶ Start
here` block gives the derive commands; `▶ NEXT ACTIONS` is a candidate pool, not a plan), and
remaining work lives in `docs/backlog.md`. This memory keeps only what the repo does not: prod ops
facts and recipes that cost hours to rediscover.

    git log --oneline -10                                       # what is merged
    flyctl releases --app youtube-playlist-summaries | head -3   # what is actually DEPLOYED

**Last recorded (verify, do not trust):** the roadmap's status cell says Fly **v11, deployed
2026-10-15**, prod schema **`0027`**. On 2026-11-14 master carried migration `0028` with its PR
HELD until it deploys (backlog #392). Prod has twice run behind what the docs said (a v6 line while a
fix sat undeployed; a migration eight days behind), so "merged" ≠ "deployed" ≠ "working".

**Why:** Session Resume must read the RUNNING system, not just git and files — see [[process-conventions]].

**How to apply:** for status, run the two commands above and read the roadmap's top block. For prod
work, use the recipes below.

## Prod ops facts (verify against the running system before trusting)

- Fly app `youtube-playlist-summaries`, region `iad`, web + worker machines; web
  `min_machines_running = 0` in `fly.toml` (verified 2026-11-14), worker stopped when idle — see
  [[lease-sweep-merged-318]]. Supabase prod `uykwcybxqgewmbltroxf` (us-east-1, legacy JWT keys).
  Google OAuth client `yps-supabase`. Signup toggle OFF since 2026-07-22, and the Auth **email
  provider is OFF** — re-open only after checking guardrail defaults ([[access-tiers-vision]]).
- `guardrail_config` read 2026-08-11: `daily_cap_cents=5000`, `magazine_est_cents=6`,
  `lease_ttl_seconds=180`, `max_serve_attempts=5`, `summary_max_attempts=1`, `dig_max_attempts=2`.
- **Read-only prod role `claude_ro`** (`CLAUDE_RO_DATABASE_URL` in `.env.local`, gitignored — a
  `grep -r --include=*` misses dotfiles). It bypasses RLS and holds zero write grants on all public
  tables, so `spend_ledger` + `ledger_audit` can be watched read-only.
- ⚠ That URL carries `sslmode=require`, which in pg 8 does **not** verify the server and overrides an
  `ssl` object passed beside it ([[a-mechanism-can-be-silently-overridden]]).
- ⚠ **Local and prod DISAGREE on anon exposure** (measured 5 vs 10 `definer + anon-executable`);
  `check-anon-exposure.py` defaults to **prod** for that reason. Background:
  [[anon-execute-is-the-default-not-a-decision]] (backlog #30/#33/#54).

## Recipe — query prod with `claude_ro`: PUT THE SQL IN A FILE

There is no local `psql`; the query crosses host shell → container shell → psql, and quotes, `||`,
`$$` or non-ASCII get mangled (measured twice 2026-08-12). Mount a SQL file read-only and expand the
URL inside the container:

    PGURL=$(grep '^CLAUDE_RO_DATABASE_URL=' .env.local | sed 's/^CLAUDE_RO_DATABASE_URL=//' | tr -d '"')
    docker run --rm -e PGURL="$PGURL" -v "$SQLDIR":/sql:ro postgres:16 \
      sh -c 'psql "$PGURL" -f /sql/query.sql'

**Is prod on the schema we think?** (grants added 2026-08-12 by the owner, as `postgres`:
`grant usage on schema supabase_migrations to claude_ro; grant select on
supabase_migrations.schema_migrations to claude_ro;`)

    select version from supabase_migrations.schema_migrations order by version;

**Diff the SETS against `supabase/migrations/*.sql`, not count-and-max** — those agree while a middle
migration is missing. ⚠ This reads the migration LEDGER; a partial migration leaves it saying yes, so
probing for an object the migration creates stays the stronger check
([[hardcode-only-what-fails-loudly]]).

## Recipe — the prod smoke gate (`docs/deploy.md` Step 3b)

`npm run test:e2e:prod` — ~13s, free, read-only, 6 checks; **6/6 green against v7 on 2026-08-21**.
The owner decided it is a GATE in the deploy procedure, not an optional instrument. Without a session,
3 pass and 3 report NOT RUN — by design.

- ⚠ **Do NOT `source .env.local` first** — it exports `SUPABASE_SERVICE_ROLE_KEY` and pre-flight P2
  refuses to start. The fixture reads `CLAUDE_RO_DATABASE_URL` out of the file itself.
- ⚠ **`npm run prod:session` DOES NOT WORK** — Google rejects the Playwright-launched Chrome after the
  identifier step (`accounts.google.com/v3/signin/rejected`). What works (the profile persists, so
  Google is a one-time step):

```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --remote-debugging-port=9222 --user-data-dir="$HOME/.chrome-claude-prod" \
  --no-first-run --no-default-browser-check \
  "https://youtube-playlist-summaries.fly.dev/login" &
# human signs in by hand, then attach over CDP:
#   chromium.connectOverCDP('http://127.0.0.1:9222') -> ctx.storageState({path: AUTH_FILE})
```

  Session file `playwright/.auth/prod.json` (gitignored); cookies captured 2026-08-21 were valid to
  2027-09-25. `flyctl auth login` stays human-only.
- ⚠ **`videos.data->>'summaryMd'` is the blob's KEY, not the markdown** — check 4's needle is
  `data->>'title'` ([[quote-the-code-dont-characterise-it]]).

## Recipe — `check-test-counts.py` must be run the way CI runs it

It fails closed on a MISSING `jest-results.json` but has **no freshness bound**: a four-day-old file
at the repo root matched the roadmap's stale counts and exited 0 (2026-08-17) while CI failed.

    npm test -- --ci --json --outputFile=jest-results.json
    python3 scripts/check-test-counts.py --results jest-results.json

## Lessons carried (the reasoning is not in the diff)

- **A suite green only on its FIRST run counts as red** — verify twice with no DB reset.
- **A wrong recorded root cause is expensive** — "state pollution needing a DB reset" (an unowned
  chore) sat for days when it was a test bug in one file. Wrong diagnosis → wrong owner → no fix.
- **Two review rounds finding one bug shape by different paths → delete the mechanism**, don't patch
  the second instance (PR #27 dropped stdout parsing for `--output-last-message`).
- **A tick records THAT something was verified, never WHAT against** — A1/A2 were ticked against v4
  while v6 ran; every gate now carries `VERIFIED AGAINST: vN`.
- For "logged out", fetch with `curl` (no cookie jar), not an incognito tab.
- Still-open non-obvious items (2026-08-11): `CLOUD_TRANSCRIBE_FALLBACK_VERIFIED` (`lib/gemini.ts`)
  is a different premise from the release gate and stays unverified; cosmetic `<title>Create Next
  App</title>`, Next 16 `middleware`→`proxy` deprecation, Turbopack NFT over-tracing from
  `lib/settings-store.ts`.

## History (condensed)

- **2026-08-11 — M1 complete** (M1.4 A1–A3, B1–B5; PRs #76–#79). Release v6 shipped a 45-commit gap
  (#46 serve bounding, serial coherence). Staging project `neeufoxdbgbpkjukzzuc` safe to delete
  ([[staging-supabase-project]]). B3 "failed" against a state the app cannot reach
  ([[rls-denial-is-indistinguishable-from-absence]]).
- **2026-08-17 — last launch blocker closed**: backlog #36 (non-ASCII title destroyed a paid
  summary), PR #104 `324ec77` → Fly v7; the original failing video `wr4nCMUy1dk` re-ran live and
  served. Filename encoded, owner prefix and playlist key not (ADR-0008's serve money guard).
  Shipped 4 of 16 planned tasks by owner decision after Phase 6 ([[gates-detect-defects-not-design]]).
- **2026-08-19/21 — M3.1-B prod gate** (PR #119) and PRs #113–#127, none touching runtime code.
  The owner decided 2026-08-19 to leave the stale `check-sentinel-meanings` / `check-guard-coverage`
  entries describing the deleted reservation protocol — do not "fix" them by deleting entries.
- **2026-08-22** — the backlog renders as a page (`python3 scripts/gen-backlog-page.py` →
  http://127.0.0.1:7391/backlog-table); filing a row requires a `GROUPS` line in that script.
  The six-item address cluster then hung off a PARKED ADR-0006 — **superseded**: ADR-0006 was
  accepted 2026-08-24 and migration `0027_stable_blob_addressing` shipped in PR #155 (M4).

See [[stage3-cloud-sync-branch-state]], [[serve-path-bounding-merged]], [[local-cloud-validation-run]],
[[never-close-with-a-promise]].
