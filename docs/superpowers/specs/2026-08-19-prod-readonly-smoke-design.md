# M3.1-B — a read-only production smoke against the deployed URL

> **Anchor:** `prod-smoke` — **ADR:** none
> **Goal:** After every deploy, prove by machine that the deployed application serves the real application.

**Backlog:** #41 🟠 · **Roadmap:** the untaken half of 3.1 · **Status:** design approved by the user
2026-08-19, spec awaiting review.

**Goal.** After every deploy, prove by machine that the *deployed* application serves the *real*
account's data, spends nothing, and still has its security locks on — in under a minute, for free.

**Non-goal.** Re-running the M3.1-A journey against production. A already covers code regressions.
B covers the class A structurally cannot reach: **the deployment being wrong while the code is
right** — a secret missing on Fly, an env var set differently, a storage grant that differs between
local and hosted.

---

## 1. Why this is a separate item at all

3.1 originally read *"against the deployed URL"*. It cannot be automated end-to-end, for two
reasons that are both **verified, not recalled**:

| Obstacle | Evidence |
|---|---|
| Prod login is Google OAuth only, and Playwright cannot drive Google's password step | `app/login/page.tsx` → `signInWithOAuth({provider:'google'})` |
| The email/password route is closed in prod at the provider level | `docs/reviews/task-7-prod-auth-verification.md:7` — *"Enable email provider: OFF"*, verified 2026-07-24 |
| The dev back door is 404 in prod by design | `lib/supabase/dev-login.ts` — fails closed unless `DEV_LOGIN_ENABLED` is set **and** the Supabase URL is local |

So a prod session must be **captured by hand, once**, and replayed. That is the accepted cost, and
it is why A (unattended, free, every commit) was built first and B is a per-deploy gate.

**DECIDED 2026-08-19 (user): this is a GATE, not an instrument.** It becomes a step in the deploy
procedure; a red run means the release is not good. The alternative — a tool run on a whim — was
rejected on the grounds that it drifts into never being run and is broken by the time it is wanted.

---

## 2. What was measured before designing (all this session, against prod)

Nothing below is recalled. Each was run.

| Fact | How established |
|---|---|
| Prod is live and bounces anonymous requests to `/login` | `curl -sIL https://youtube-playlist-summaries.fly.dev/` → `200 …/login` |
| `claude_ro` **bypasses RLS**, is not superuser | `pg_roles.rolbypassrls = t`, `rolsuper = f` |
| It can read `playlists`, `videos`, `spend_ledger`, `ledger_audit` | 3 / 12 / 5 / 2 rows returned |
| It holds **zero** write grants across all 12 `public` tables | `has_table_privilege` for INSERT/UPDATE/DELETE — 0 tables |
| A summarised video is identifiable by `data->>'summaryMd'` | `jsonb_object_keys` over `public.videos` |
| The markdown serve path cannot reach a paid call | `app/api/html/[id]/route.ts:75-82` — returns before `resolveAndParse`, comment `D4 money invariant` |
| Google **accepts** a Playwright-driven real Chrome at the identifier step | spike, 2 consecutive runs, `channel: 'chrome'`, account chooser reached |
| The app's sign-in button drops clicks before hydration | same spike — run A navigated on attempt 1, run B needed attempt 2 |

The last one is a design input, not trivia: a single-click capture script would intermittently do
nothing and look like a Google problem.

---

## 3. Architecture

Mirrors the existing local split, for the reason `playwright.cloud.config.ts:8-14` already records —
one config cannot serve two applications that dispatch on a runtime env var.

| File | Responsibility |
|---|---|
| `playwright.prod.config.ts` | targets the deployed URL. **No `webServer`** — it starts nothing |
| `tests/e2e/prod-fixture.ts` | the read-only reads: anchor, ledger, session state, the NOT-RUN message |
| `tests/e2e/prod-global.ts` | the four pre-flights and the money bracket, outside every project |
| `tests/e2e/prod-smoke.spec.ts` | the six checks |
| `tests/e2e/supabase-prod-ca-2021.crt` | Supabase's private root CA, pinned (see §3.1). Public cert, not a secret |
| `scripts/capture-prod-session.mjs` | headed real-Chrome capture of `playwright/.auth/prod.json` |

`npm run test:e2e:prod` and `npm run prod:session`. One new devDependency: **`pg`** — the read-only
credential is a Postgres connection string, and there is no other way to use it from Node. Dev-only,
so it does not ship in the container.

### 3.1 TLS to the pooler — pinned, not bypassed

Not foreseen at design time and found by running it. The pooler presents a chain rooted in a
**private** CA (`Supabase Root 2021 CA`, self-signed), which Node's default trust store rightly
rejects. The first fix written was `rejectUnauthorized: false`; that is **wrong** and was replaced —
it accepts *any* certificate, on a connection carrying a database credential.

The root is instead downloaded from Supabase's published URL over **public** TLS and vendored, so
trust is anchored in the public web PKI rather than in whatever the pooler presented the first time
we looked (trust-on-first-use would be circular).

⚠ **`sslmode=` must be stripped from the connection string, and the reason generalises.** With
`sslmode=require` present, pg's connection-string parsing builds its own `ssl` config and
**overrides** the object passed alongside it — the pinned CA was supplied and silently ignored.
Worse, pg 8 maps `require` to a **non-verifying** connection, so the credential URL as issued was
never verifying the server at all. Pinning is therefore a real improvement over the status quo, not
a formality.

**Why the guard lives in `globalSetup` and not in a hook:** settled already by
`tests/e2e/cloud-global.ts:8-35` — a project whose dependency failed is never run, so a guard inside
a spec is absent in exactly the window it is needed. That reasoning transfers unchanged.

### The anchor query

Expectations are **derived at run time**, never committed. A hard-coded playlist id goes red the day
it is deleted, which trains the reader to ignore the gate.

```sql
select p.id as playlist_id, p.playlist_title, v.video_id, v.data->>'summaryMd' as md
  from public.videos v
  join public.playlists p on p.id = v.playlist_id
 where coalesce(v.data->>'summaryMd', '') <> ''
   and coalesce(p.playlist_title, '')     <> ''
 order by v.updated_at desc, v.video_id
 limit 1;
```

Zero rows is **NOT RUN**, never a pass — there is nothing to anchor on.

---

## 4. Pre-flight — four refusals before a request reaches prod

Their job is to make *"could not run"* impossible to confuse with *"ran and passed"*, and equally
impossible to confuse with *"ran and found something"*.

| | Refuses when | Verdict |
|---|---|---|
| **P1** | `playwright/.auth/prod.json` missing, or every auth cookie's `expires` is in the past | **NOT RUN — re-capture the session** |
| **P2** | `SUPABASE_SERVICE_ROLE_KEY` is present in the environment | **REFUSE — this suite must never hold a write credential** |
| **P3** | `CLAUDE_RO_DATABASE_URL` absent, or the anchor query returns no row | **NOT RUN — nothing to anchor on** |
| **P4** | the ledger baseline cannot be read | **NOT RUN — the money guard would be absent** |

**P1 is the disambiguator, and it is the reason it runs first.** "Bounced to `/login`" has two
meanings — *your session expired* (could not run) and *authentication is broken in production*
(a finding). Reported as the same red, the first meaning teaches the reader to dismiss the second.
Checking expiry **before** navigating separates them by construction.

**P2 is the mirror of `assertLocalStack()`** (`tests/e2e/cloud-global.ts:137-152`). That guard stops
a *write* credential being aimed at prod; this one stops the suite *holding* one. Read-only becomes
a mechanism rather than a promise.

---

## 5. The six checks

| # | Check | FAILS IF |
|---|---|---|
| **1** | Record the live release (`flyctl releases --app youtube-playlist-summaries`) | **NOT RUN** if `flyctl` is missing or unauthenticated; **FAIL** if it answers but names no complete release. The two are different and must not print the same verdict |
| **2** | `GET /` serves the cloud application | bounced to `/login` **despite P1 passing**, or the `playlists` navigation landmark is absent |
| **3** | The sidebar lists the playlist the database says exists | no link with that exact title is visible |
| **4** | The summary downloads, and the bytes are the database's | non-200; no `content-disposition: attachment`; or the body does not contain **the first non-empty line of the anchor row's `data->>'summaryMd'`, trimmed** (see the coupling warning in §7.5) |
| **5** | The locks that force this test to be semi-manual still hold | the bogus-credential probe returns anything but `"Email logins are disabled"`, **or** `GET /dev-login` returns anything but 404 |
| **6** | Nothing spent | `spend_ledger` cents or `max(ledger_audit.id)` moved during the run |

**Check 2 is not cosmetic.** This exact dispatch broke on the first deploy: `/` was prerendered with
`STORAGE_BACKEND` absent and a signed-in cloud user was served the local application and its
filesystem ingest, which 400s in a container (`tests/e2e/cloud-journey.spec.ts:71-74`).

**Check 4 reaches further than it looks.** The bytes come from Supabase Storage, so a pass also
proves the bucket, its grants and the storage credentials are correct **in the deployed
environment** — a class the local suite cannot test. And it is free by contract, not by luck
(§2, `route.ts:75-82`).

**Check 5 converts a decision into a standing assertion.** The prod email provider being OFF is a
dashboard setting: changeable with no commit, no diff and no review. `docs/dev-process.md` requires
that a decision earn its place as a gate by asserting the world still matches it. This is that
assertion.

---

## 6. Deliberately excluded

| Excluded | Why | What it costs |
|---|---|---|
| The magazine HTML render (`format=html`) | regenerates when the model is stale — 6–12¢ per run, measured in PR #96 | the most complex serve path stays unsmoked in prod |
| Ingest, sharing, deletion, PDF, dig-deeper | every one writes, spends, or both | browser-level prod coverage of those stays manual (3.2) |
| **Sign-out** | it would invalidate the captured session **every run**, converting an occasional chore into a per-run one | no prod check that sign-out clears the session |

The sign-out exclusion is the one to remember. `cloud-journey.spec.ts:212` does exactly this and is
right to — copying it here would quietly destroy the thing that makes the suite runnable.

A later refinement, explicitly **not** in v1 (YAGNI): pre-check magazine freshness read-only and
render only when it is provably free.

---

## 7. Bounds — stated now, not discovered later

1. **The expiry pre-flight is not exact.** Supabase refreshes sessions, so a cookie that looks live
   can be dead if its refresh token was revoked server-side. That case appears as a check-2 failure
   rather than a NOT RUN. Believed rare; not designed around.
2. **The money guard's window is the whole run, and the ledger is global.** Using the app in another
   tab mid-run fires it falsely. Identical to the limitation `cloud-global.ts:117-124` documents.
3. **`claude_ro` bypasses RLS; the browser session does not.** Check 3 therefore compares *what a
   privileged reader sees* against *what your session sees*. It catches data failing to **reach**
   you. It cannot catch a policy that wrongly **widens** access to a third party — that needs a
   second, unprivileged session and is out of scope.
4. **The spike proves Google does not refuse the browser at the identifier step. It does not prove a
   sign-in completes** — Google can still object after the password. Only the capture itself settles
   that, and it needs the human.
5. ✅ **RESOLVED 2026-08-21 ON THE FIRST AUTHENTICATED RUN — and the real defect was one level more
   basic than this bound predicted.** The two sources are not two versions of the same thing:
   **`videos.data->>'summaryMd'` is the blob's KEY** (`003_돈-버는-…-다이제스트.md`), not the
   markdown. Check 4 was looking for a *filename* inside a document, and duly failed. The needle is
   now `data->>'title'`, **observed** in the served response (6,010 bytes, HTTP 200) rather than
   inferred from a column name, plus a size floor so a short error envelope cannot pass.
   ⚠ **The lesson is not "the bound was wrong" — it is that naming a risk is not the same as
   checking it.** `tests/integration/helpers/seed.ts` states plainly that `summaryMd` is *"the
   top-level key the route get()s"*. That comment was read during design and then designed against
   as if it said the opposite. A flagged assumption still has to be *measured*; flagging it only
   guarantees you notice when it breaks. Original text follows.

   ⚠ **UNVERIFIED COUPLING, and check 4 rests on it.** The check compares the *served* markdown
   against `videos.data->>'summaryMd'` in the database. The route serves `load.mdBytes`, which comes
   from **Supabase Storage** (`route.ts:78`), while the anchor query reads a **column**. Nothing in
   this session established that those two are the same text, and it could not be: reading the blob
   needs a session, and `claude_ro` cannot read `storage.objects` (measured previously — task #90).
   **This is an assumption, labelled as one.** If the first authenticated run shows they differ,
   check 4 degrades to the weaker, certain form — 200, `attachment`, non-empty body beginning with a
   markdown heading — and that weakening must be written into this spec rather than absorbed
   silently. Deciding it is the first job of the first session-bearing run.

---

## 8. Acceptance

- [x] `npm run test:e2e:prod` with **no** session file reports **NOT RUN** and exits non-zero —
      verified by running it, not by reading it. **3 failed (2, 3, 4), each naming the missing
      session and the command that fixes it; 3 passed.**
- [x] With `SUPABASE_SERVICE_ROLE_KEY` exported, the suite **refuses** and names P2. **Verified.**
- [x] Checks 1, 5 and 6 pass against live prod with no session present. **Verified 2026-08-19
      against release v7**: `release=v7 · anchor=wr4nCMUy1dk in "Business" · ledger=audit 2, 2298¢`.
- [x] With a captured session, **5 of 6 pass against production, 2026-08-21** — checks 2, 3, 4, 5
      and 6 green, ledger provably unmoved at teardown. Check 1 is red and correct: `flyctl`
      auth expired mid-session, so it reports **NOT RUN**, which is the behaviour this spec
      asked for. Restore with `flyctl auth login` for 6/6.
- [x] ⚠ **The capture is harder than §1 assumed, and the workaround is now the procedure.**
      Google **rejected** the Playwright-launched browser after the identifier step
      (`accounts.google.com/v3/signin/rejected`) — the spike had explicitly bounded itself to
      the identifier step and that bound was the operative one. What works: launch a NORMAL
      Chrome with a dedicated profile and a debug port, sign in by hand, attach over CDP and
      export. The profile persists, so Google is involved once rather than per capture.
- [ ] Mutation check: breaking each check's assertion turns **that named check** red — not merely a
      non-zero exit.
- [ ] The roadmap's 3.1 note and backlog #41 are updated in the same PR as the code.

---

## 9. Open, and owned by the human

1. **The session capture itself** (`npm run prod:session`) — needs the user at the keyboard. Nothing
   else in this spec is blocked on it; checks 1, 5 and 6 plus all four pre-flights run without it.
2. ✅ **DONE 2026-08-21 — `docs/deploy.md` Step 3b.** The gate is in the deploy runbook, between
   `fly deploy` and the manual smoke, with its six failure conditions, the NOT-RUN rule, the
   `.env.local`/P2 trap and the session-recapture pointer.
   ⚠ **It was NOT written down for the first two hours after it went green, and the user had to
   ask.** This item existed precisely to prevent that, and it did not — reading a note is not
   acting on one. Same shape as backlog #48, one turn after #48 was closed.
