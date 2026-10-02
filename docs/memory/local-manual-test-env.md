---
name: local-manual-test-env
description: "FIRES-WHEN: needing to run or test the Sync feature locally — Durable local manual-test environment for the Sync feature against"
metadata: 
  node_type: memory
  type: project
  originSessionId: 03d9e3f7-1666-404f-a1e3-28defe9b9b44
---

Durable manual-test harness set up 2026-07-24 so the user can test the **Sync** feature by hand
(add video → sync → check browser + FS) against **#2 local Docker Supabase** — NOT prod.

- **Data root (open in Obsidian/editor):** `~/code/agentic-ai-docs/yps-sync-test/`
  (sibling of the repo, outside git). Holds `cs146s-the-modern-software-development/raw/*.md` (12 files).
- **One-command sync:** `~/code/agentic-ai-docs/yps-sync-test/sync.sh` — self-contained wrapper
  (Node 22 PATH + `source .env.local` + `CLOUD_SYNC_DATA_ROOTS`=durable root; does `login` then sync).
  Not committed (personal, lives in the untracked durable folder). Verified end-to-end: 0 errors,
  10 skippedIdentical (idempotent).
- **One-command browser login:** `~/code/agentic-ai-docs/yps-sync-test/login.sh` — mints a fresh
  session via `signInWithPassword` (test user) and `pbcopy`s a `document.cookie=…;location.reload()`
  one-liner to paste into DevTools console (Cmd+Opt+J) at localhost:3100. Session lasts 1h. Self-service
  workaround for Google-only login until backlog #13 (env-gated dev-login) lands. Token is MINTED fresh
  each run (not a stored secret); `sb-127-auth-token` is just the @supabase/ssr cookie NAME.
- **Test user (#2 only):** `sync-test@example.com`, owner `52990721-543a-4261-b51c-729031e69634`,
  password `dev-sync-test-2026` set via service-role admin API. Creds in `.env.local`
  (gitignored) as `CLOUD_SYNC_EMAIL`/`CLOUD_SYNC_PASSWORD`.
- **Browser login — USE `/dev-login` now (#13 shipped 2026-07-25, PR #36, merge `cf27f10`).**
  Go to `http://localhost:3100/dev-login` (or the "Local dev sign-in" link on `/login`), enter
  `sync-test@example.com` / `dev-sync-test-2026`. Requires `DEV_LOGIN_ENABLED=true` in `.env.local`
  (already set) and a dev server started AFTER that was added. This replaces the `login.sh` +
  console-paste dance (that still works as a fallback). Gate = server-only `DEV_LOGIN_ENABLED` flag
  + runtime local-URL check, fail-closed, `force-dynamic`; 404s in prod. **Prod safety:** the real
  boundary is prod Supabase's Auth **email provider = OFF** (verified, Task 7); the UI gate is
  defense-in-depth. If prod ever re-enables the email provider, revisit.

**Sync is ADDITIVE (M2a):** adds propagate both ways; **deletes do NOT** (tombstone delete = M2b,
deferred). So an add-video test fully round-trips; a delete-video test won't propagate — by design.
See [[stage3-cloud-sync-branch-state]].
