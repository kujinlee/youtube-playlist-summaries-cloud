---
name: launch-roadmap-state
description: "FIRES-WHEN: needing launch status, remaining blockers, or production ops — Path-to-launch state: ⭐⭐ **THE LAST LAUNCH BLOCKER IS CLOSED, DEPLOYED AND VERIFIED IN PROD** — backlog #36: PR #104 (`324ec77`) → Fly **v7** → re-ran the ORIGINAL failing Korean video live and it now completes + serves. Docs reconciled in PR #105 (`126190a`). M1/M2/M3 all complete; **nothing is blocked on the human and there is no successor blocker**. Prod ops facts + the claude_ro recipe live here (put the SQL in a FILE). No master-PR number: run `git log -1`. ⟳ 2026-08-22 master `9211f74`: the backlog now RENDERS as a page (`python3 scripts/gen-backlog-page.py` → http://127.0.0.1:7391/backlog-table) and that page says what to start first — the root of the six-item address cluster is the PARKED ADR-0006, under which #20/#21/most of #17 are DELETED not done, while #19 and #22 SURVIVE it"
metadata:
  node_type: memory
  type: project
  originSessionId: 39a195b3-d01f-4d5a-af05-18d8fbdbde18
  modified: 2026-08-21T22:44:45.843Z
---

## ⟳ 2026-08-22 — master `9211f74`. Five PRs, all page/harness work; PRODUCT UNTOUCHED.

Prod is still Fly **v7**; no `lib/` `app/` `worker/` `supabase/` change since. What shipped is
deliverable #2:

- **#128 #130 #131** — `docs/backlog.md` now renders as a standing page. Regenerate with
  `python3 scripts/gen-backlog-page.py` → **http://127.0.0.1:7391/backlog-table** (fixed url;
  undated filenames are excluded from `/latest` so it never steals the brief's bookmark). A
  PostToolUse hook regenerates it on any edit to the backlog, and the open tab reloads itself.
  Carries: change-since-last-visit badges + per-entry word diff (history read from git, 55 versions
  ≈ 1s), a hand-written plain-English grouping whose COVERAGE is mechanical, and a dependency map.
- **#132** — `portable-practices.md` §14 (assert the rendered artifact, don't just run it) and §15
  (hand prose is fine if its coverage is mechanical). Two candidates parked under *Not yet mined*
  with evidence status.

**⭐ THE MAP ANSWERS "WHAT FIRST", so read the page before planning group 1.** The root of the
six-item address cluster is **not a backlog row** — it is the parked stable-addressing slice
(ADR-0006, still `status: proposed`; parked 2026-08-11). Under it: **#20 #21 and most of #17 are
DELETED, not done**; **#19 and #22 SURVIVE it** and are real work either way. Starting #20 or #21
first means guarding an address about to stop existing.

**Four sibling pages filed, all needing a spec, all one substrate:** #56 roadmap · #57 review-round
tracker · #58 gate inventory · #59 decision index. **#40 now records the direction** (user: *"md
files aren't friendly — build html interactive dev reference pages"*) and owns packaging the
substrate: loopback server, stable urls, regenerate-on-change hook, git-derived history, Ask tray,
prose-coverage contract.

⚠ **The backlog table's own guards fired twice while filing those** — a literal `|` inside a code
span (7 cells vs 6) and an ungrouped new item. Both refuse to write the page and leave the previous
build serving. Filing a row therefore REQUIRES adding a line to `GROUPS` in
`scripts/gen-backlog-page.py`; that is the design, not an obstacle.

**Canonical roadmap is `docs/roadmap-to-launch.md`** — read it, don't trust this summary for detail.
Its `▶ NEXT ACTIONS` block is written to survive a context reset. This memory holds only what is
**not derivable from the repo**.

## ⭐⭐ The last launch blocker closed — 2026-08-17 (PR #104, squash `324ec77`)

Backlog #36 (a non-ASCII title destroyed a paid summary) is **fixed and merged**, master CI green.
The encoder shipped **alone** — 4 of 16 planned tasks — by user decision after a Phase 6 review found
the other twelve were not on the critical path. See [[gates-detect-defects-not-design]].

**✅ IT IS LIVE AND PROVEN — Fly release v7, verified 2026-08-17.** The verification re-ran the
**original failing video** (`wr4nCMUy1dk`, `돈 버는 방식은…`), which had died in prod **twice** with
`Invalid key` while `ever_metered = t`. On v7 it completes, appears in the library tagged KO, and
serves. The decisive observable is the physical key now in the bucket:

    5a1df936-…/PLXX3HKP5ZNN0XbVDK0IkjESRuJFcJRxYR/003_=hc00SCQvLFMd1mWqZ8dodvO.md

Filename encoded; **owner prefix and playlist key NOT** — the asymmetry that keeps ADR-0008's serve
money guard alive, now a fact in the bucket rather than a claim in a doc. Marked objects 0 → 1.
Ledger 2,142 → 2,292 (+150¢ reserved; `actual_cents` still 0 = the deferred settle slice).

> **Why this step is worth repeating for any future deploy:** "merged" ≠ "working". Prod once ran
> eight days behind on a migration while everything on disk looked right. Session Resume must read
> the **running system**, not just git and files — see [[process-conventions]].

Two things are deliberately still open, and both are asserted rather than remembered:
- **`slugify`'s astral-surrogate slice** — asserted as **STILL BROKEN** in
  `tests/integration/korean-title-e2e.test.ts`, so it fails loudly the day it is fixed.
- **`companionTransfer` (`sync-run.ts:475`)** — the one deferred task with a MEASURED defect.

## ⭐ #41 M3.1-B SHIPPED — 2026-08-19 (PR #119, squash `de0622a`)

`master` = **`de0622a`**. **The prod deploy gate exists and runs**: `npm run test:e2e:prod` — six
checks against the deployed app, four pre-flight refusals, free, under a minute. **The user DECIDED
it is a GATE** (a step in the deploy procedure), not an optional instrument.

**Verified against release v7 with no session captured: 3 pass, 3 report NOT RUN.** That split *is*
the acceptance criterion — the checks that can run without a session do, and the ones that cannot
say so loudly rather than skipping.

⭐ **Production has a money guard for the first time.** `claude_ro` bypasses RLS and holds **zero
write grants across all 12 public tables**, so `spend_ledger` + `ledger_audit` can be bracketed
read-only. The local suite's guard only ever watched a local stack.

**THE ONE THING STILL OUTSTANDING IS THE HUMAN'S:** `npm run prod:session` — one Google sign-in,
captured once to `playwright/.auth/prod.json` (gitignored). Cannot be automated: prod login is
Google-only *and* the email provider is OFF at the provider level. **Check 5 now re-asserts both
locks every run**, so that 2026-07-24 decision can no longer change silently.

⚠ **One assumption is flagged, not resolved** (spec §7.5): check 4 compares served markdown against
the `videos.data->>'summaryMd'` **column**, but the route serves bytes from **storage**. Unverifiable
without a session. If it fails on the first authenticated run, decide whether they genuinely differ
*before* weakening the check.

See [[a-mechanism-can-be-silently-overridden]] for the two defects running it exposed.

## Session 2026-08-20/21 — six more PRs, all merged; prod still untouched

`master` = **`df496b1`**. Every change was docs, `scripts/` or `tests/` — **prod remains Fly v7**.

| PR | |
|---|---|
| #119 `de0622a` | **M3.1-B prod deploy gate** — six checks; prod gets a money guard for the first time |
| #120 `bb6a9b5` | **#44** the cloud e2e finally renders the main pane; found 2 defects only rendering could reach |
| #121 `ce567e0` | **#55 filed** — an unscored video is invisible and the empty state blames your filters |
| #122 `db0c6f7` | **#53's build trigger was unfalsifiable** — retired, replaced with an observable one |
| #123 `b8ee77f` | **#54 ratchet half** — anon-exposure gate; **it caught itself failing open** |
| #124 `df496b1` | **#48 CLOSED** — `/loop` is the mechanism, Stop hook discarded, count 3→5 |

**Two facts a fresh session should not re-derive:**
- **Local and prod DISAGREE on anon exposure** — 5 vs 10 `definer + anon-executable`. Schema gates
  that point at the docker container are green over the wrong subject. `check-anon-exposure.py`
  defaults to **prod** for this reason.
- **`CLAUDE_RO_DATABASE_URL` carries `sslmode=require`, which in pg 8 does NOT verify the server.**
  It also *overrides* an `ssl` object passed beside it. See [[a-mechanism-can-be-silently-overridden]].

## ⭐ THE PROD SMOKE IS LIVE — **6/6 GREEN**, 2026-08-21. `master` = `5e45814`

`npm run test:e2e:prod` — 13s, free, read-only, **6/6 against release v7**. Session at
`playwright/.auth/prod.json` is captured, cookies valid to **2027-09-25**; `flyctl` authenticated.
⭐ **Production's spend ledger now has a watcher — it never had one before.**
**It is a GATE, written into `docs/deploy.md` Step 3b** (between `fly deploy` and the manual smoke).

**Nine PRs merged 2026-08-20/21, prod untouched throughout (all docs/scripts/tests):**
#119 prod gate · #120 cloud e2e renders the main pane · #121 filed #55 · #122 #53's trigger retired ·
#123 anon-exposure ratchet · #124 **#48 CLOSED** · #125 check-4 needle fixed · #126 gate into the
runbook · #127 **#55 fixed** (unscored video shows as pending). Unit tests **2,722 / 268 suites**.

⚠ **BACKLOG BOOKKEEPING IS 5 ROWS WRONG — fix before trusting any "what's left" count.**
Derived 2026-08-21: **42 open / 10 closed / 52 rows**, but
`#14`, `#34`, `#35` are closed in Status yet never got the `✅` item marker (a severity scan counts
them open); `#31` carries **no severity marker at all**; and **`#41` still reads OPEN** though its
gate went 6/6 today (Status says "DESIGNED AND BUILT", never ✅). `check-docs` passes because its
rule only fires when a *severity* marker survives on a closed row.

**Biggest real risk left: the 🟠 stale-address cluster — #17, #19, #20, #21, #22.** Five rows, one
root cause (paid content orphaned when a video's address changes), all "+ design", so none can start
without a design conversation. #20 is the most concrete entry point.

⚠ **`npm run prod:session` DOES NOT WORK — Google rejects the Playwright-launched Chrome** after the
identifier step (`accounts.google.com/v3/signin/rejected`). The 2026-08-20 spike bounded itself to
the identifier step, and that bound was the operative one. **The procedure that works, and it makes
Google a one-time step because the profile persists:**

```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --remote-debugging-port=9222 --user-data-dir="$HOME/.chrome-claude-prod" \
  --no-first-run --no-default-browser-check \
  "https://youtube-playlist-summaries.fly.dev/login" &
# human signs in by hand, then attach over CDP:
#   chromium.connectOverCDP('http://127.0.0.1:9222') -> ctx.storageState({path: AUTH_FILE})
```

⚠ **Do NOT `source .env.local` before running the smoke** — it exports `SUPABASE_SERVICE_ROLE_KEY`
and pre-flight **P2 refuses to start**. That is the guard working; the fixture reads the one variable
it needs (`CLAUDE_RO_DATABASE_URL`) out of the file itself.

⚠ **`videos.data->>'summaryMd'` is the blob's KEY, not the markdown** (e.g.
`003_돈-버는-…-다이제스트.md`). Check 4 asserted a document contains its own filename and failed on
its first real run; the needle is now `data->>'title'`. See
[[quote-the-code-dont-characterise-it]] — the seed's comment said exactly this and was designed
against as if it said the opposite.

⚠ **Still human-only:** `flyctl auth login`. See [[never-close-with-a-promise]].

## Session 2026-08-19/20 — six PRs, all merged, none touching runtime code

Prod still **Fly v7** (2026-08-18) and correctly untouched — every change in these six was docs or
`scripts/`.

| PR | |
|---|---|
| #113 `56917ea` | ranked the whole backlog; `▶ Start here` at the top of the roadmap; repaired the Ask-tray CSS shim |
| #114 `12e357b` | deleted a cached line count from the very box arguing against cached state |
| #115 `a066eee` | prod evidence folded into backlog #30/#33; **#54 filed** |
| #116 `aae9358` | `docs/backlog.md` was not rendering as a table, and that had **silently closed #46 and #50** |
| #117 `7f294db` | the last four ratchets get `--self-test`; `check-ratchet-contract` BASELINE **4 → 0** |
| #118 `342ac2e` | the red schema ratchets now say what their subject IS before their verdict |

**Backlog now: 43 open (12 🟠 / 23 🟡 / 8 🟢), 0 unmarked, 8 closed** — derived from the Status cell
on a table that is now provably a table. **#46 and #50 are back to OPEN**; they had been closed by a
gate reading the wrong cell.

⚠ **Two schema ratchets are RED on master by DECISION, not by neglect.**
`check-sentinel-meanings` exits 1 (5 problems) and `check-guard-coverage` exits 1 (10). ADR-0007
(`1a7c076`, 2026-08-10) deleted the reservation protocol; the entries describing what it removed went
stale, and nothing noticed because these need a live Postgres, are **not in CI**, and therefore
**cannot fail a merge — PR #66 merged over its own gates.** The user's decision 2026-08-19: **leave
all fifteen entries.** The stale ones are the reservation protocol's death certificate in executable
form, and the 3 `UNCLASSIFIED` guards need a SHAPE-vs-SEQUENCE call belonging to the parked slice.
PR #118 made the red self-explanatory instead — each gate now prints that its subject is UNSHIPPED
and when it last moved, all derived. **Do not "fix" these by deleting entries.**

**Top of the ranked list: backlog #41** (🟠 prod read-only smoke against the deployed URL). It needs a
short Phase 1 design pass — what it checks, what makes it FAIL — before any work starts.

## `check-test-counts.py` guards absence but NOT staleness — measured 2026-08-17

It is correctly fail-closed on a *missing* `jest-results.json`. It has **no freshness bound**, and a
results file left at the repo root from four days earlier reported exactly the counts the roadmap
claimed — so a stale snapshot and a stale document agreed and the gate exited **0**. CI failed the
same check, because CI has no leftover file. **Run it the way CI does or it is checking a memory:**

    npm test -- --ci --json --outputFile=jest-results.json
    python3 scripts/check-test-counts.py --results jest-results.json

Whether the script should enforce freshness itself is an **open decision for the user** — not yet
filed. Same family as [[a-test-that-cannot-fail]] and
[[hardcode-only-what-fails-loudly]].

## `claude_ro` can now enumerate prod migrations — 2026-08-12

The read-only role was **denied on `supabase_migrations`**, so the one question that once went eight
days unanswered ("is prod on the schema we think?") could not be answered by the role built to answer
it. Fixed permanently by two grants, run by the user in the Supabase SQL editor (they require
`postgres`; `claude_ro` is not superuser and the schema is owned by `postgres`):

    grant usage on schema supabase_migrations to claude_ro;
    grant select on supabase_migrations.schema_migrations to claude_ro;

**Verified 2026-08-12: prod == master, 25 migrations, `0001`…`0025`, set-diff against
`supabase/migrations/*.sql` IDENTICAL.** Re-run with no login and no token:

    psql "$CLAUDE_RO_DATABASE_URL" -At \
      -c "select version from supabase_migrations.schema_migrations order by version;"

**Diff the SETS, not count-and-max** — those agree while a middle migration is missing.

### ⚠ There is no local `psql` — and `-c` will fight you. PUT THE SQL IN A FILE.

Measured 2026-08-12, twice in one session. The recipe is `docker run --rm postgres:16`, so the query
crosses **two** shells (host → container) plus psql's own parser. Anything with quotes, `||`, `$$` or
non-ASCII gets mangled before it runs — a `select a||' : '||b` died on the host shell, and a
`\echo` block died on nested quoting. **Write the SQL to a file and mount it read-only:**

    PGURL=$(grep '^CLAUDE_RO_DATABASE_URL=' .env.local | sed 's/^CLAUDE_RO_DATABASE_URL=//' | tr -d '"')
    docker run --rm -e PGURL="$PGURL" -v "$SQLDIR":/sql:ro postgres:16 \
      sh -c 'psql "$PGURL" -f /sql/query.sql'

Same rule as `--prompt-file` / `--body-file` / `git commit -F` in `docs/plugins.md`: **anything longer
than a line goes in a file.** The var lives in `.env.local` (gitignored, so `grep -r` with
`--include=*` misses it — dotfiles are not matched by that glob).

⚠ This reads the migration **ledger**, not the schema. A partial migration leaves the ledger saying
yes. Probing for an object the migration creates (e.g. `ledger_audit_kind_note_idx` from `0025`)
stays the stronger check — same lesson as [[hardcode-only-what-fails-loudly]]: prefer the instrument
that touches the subject.

## ⭐ M1 COMPLETE — 2026-08-11

**M1.4 closed: all of A1–A3 and B1–B5.** Every first-class path has now been exercised against real
infra. **The only milestone left is M3 acceptance** (browser-level Playwright e2e against the
deployed URL). M2 Sync completed 2026-07-19.

Closing it took four PRs in one evening: #76 (B4 — the share tolerates version skew), #77 (filed
backlog #34), #78 (fixed #34), #79 (A1/A2 re-verified against v6).

**Two lessons worth more than the milestone:**
1. **B3 "failed" against a state the app cannot reach.** The harness read the markdown with
   `service_role` to isolate the model read, which manufactured a situation the real caller prevents.
   See [[rls-denial-is-indistinguishable-from-absence]].
2. **A1/A2 had been ticked against release v4 while the app ran v6.** A tick records *that* something
   was verified, never *what against* — which is why every gate now carries `VERIFIED AGAINST: vN`.

**Verification technique worth reusing:** for "logged out", fetch with `curl` (no cookie jar) rather
than an incognito window. Stronger guarantee, and it avoids the trap that made the 2026-07-22 attempt
inconclusive — a same-browser tab kept the owner logged in.

**Staging project `neeufoxdbgbpkjukzzuc` is now SAFE TO DELETE** — nothing outstanding needs it
([[staging-supabase-project]]).

## Current state — 2026-08-11

- **App LIVE at https://youtube-playlist-summaries.fly.dev, release v6** (15:47Z). Previous was v5,
  2026-07-29 — a **45-commit** gap that shipped #46 serve-path bounding (PR #67) and PR #42 serial
  coherence, both of which were merged but protecting nothing until deployed.
- **Prod schema == master: all 25 migrations.** `0023`/`0024`/`0025` applied 2026-08-11.
- **`master` clean**, tsc clean, **2671 unit / 265 suites** green.
- **Blob-addressing schema ⏸ PARKED by user decision** — merged as design (ADR-0006, ADR-0007) but
  has never run as a migration and holds zero rows. Unpark trigger + the backlog-#26 precondition are
  in the roadmap section. **Do not resume it by momentum.**
- **What remains:** the B1–B5 live checks in `docs/m1.4-finishup-checklist.md` (close M1.4), then
  **M3 acceptance**. B3/B4 spend real Gemini money and need a signed-in session.

## Prod ops facts (verify against the running system before trusting)

Fly app `youtube-playlist-summaries`, region `iad`, 2 machines (web 1 GB + worker 2 GB),
`auto_stop_machines=suspend` on web. Image **471 MB** (measured at the 2026-07-22 deploy; the earlier
3.44 GB single-stage figure was cut 7.3× by PR #26's multi-stage/standalone/bundled-worker build).
Supabase prod `uykwcybxqgewmbltroxf` (us-east-1, **legacy JWT keys**), co-located with Fly iad.
Google OAuth client `yps-supabase`. Supabase **signup toggle OFF** since 2026-07-22 (owner account
created first) — publicly reachable, locked to existing accounts; re-open only after verifying
guardrail defaults, see [[access-tiers-vision]].

**Live `guardrail_config` read 2026-08-11:** `daily_cap_cents=5000`, `magazine_est_cents=6`,
`lease_ttl_seconds=180`, `max_serve_attempts=5`, `summary_max_attempts=1`, `dig_max_attempts=2`.
There is a **read-only prod role `claude_ro`** (`CLAUDE_RO_DATABASE_URL` in `.env.local`) — use it to
read live prod. No local `psql`; run one via `docker run --rm postgres:16`, and expand the URL
*inside* the container (`sh -c 'psql "$PGURL" …'`) or the host shell eats it.

## Non-obvious, still open

- `CLOUD_TRANSCRIBE_FALLBACK_VERIFIED` (`lib/gemini.ts`) is a **different premise** from the
  release gate and remains **false/unverified**.
- ~~**`anon` holds EXECUTE on nearly every `public` function** … not yet filed~~ — ✅ **FILED AND
  MEASURED IN PROD 2026-08-19 (PR #115).** It is backlog **#33**, its sibling is **#30** (TRUNCATE),
  and the durable half is now **#54** (`alter default privileges` + a `pg_catalog` ratchet). Both
  claims are TRUE and BOUNDED; **no exploitable path found.** Two things this memory used to state
  are wrong and are corrected in the backlog rows: the functions are **not** all `security invoker`
  (16 of 26 are; **10 are DEFINER**, defended instead by an `auth.uid()` check in 8 of them), and
  #30's "SELECT/INSERT correctly denied" was a grant-vs-outcome conflation. Full detail in
  [[anon-execute-is-the-default-not-a-decision]].
- Cosmetic, never fixed: `<title>Create Next App</title>`; Next 16 deprecation of the `middleware`
  file convention (→ `proxy`); Turbopack NFT over-tracing from `lib/settings-store.ts`.

## Lessons carried (reasoning isn't in the diff)

- **A suite green only on its FIRST run counts as red.** Verify twice with no DB reset. A
  self-poisoning suite looks environmental from CI and like someone else's mess from the desk —
  neither vantage point sees the accumulation.
- **Recording a wrong root cause is expensive.** A red suite sat for days because the roadmap called
  it "state pollution needing a DB reset" (an unowned infra chore) when it was a test-correctness bug
  in one file. Wrong diagnosis → wrong owner → no fix.
- **When two review rounds find the same bug shape through different paths, delete the mechanism
  rather than patch the second instance** (PR #27: stdout parsing abandoned wholesale for
  `--output-last-message`).

See [[stage3-cloud-sync-branch-state]], [[serve-path-bounding-merged]],
[[process-conventions]], [[local-cloud-validation-run]], [[access-tiers-vision]].
