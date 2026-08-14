<!-- claude adversarial review — the Claude half of the dual gate, never run on this branch before -->
<!-- reviewed: 11a9d42 (branch docs/m31-review-round-2), diffed against 9df4d94 -->
<!-- instrument: reading + `npx tsc --noEmit` (clean). The e2e suite was NOT executed. -->

# M3.1 cloud e2e money guard — Claude adversarial review, round 4

Rounds 2–4 were Codex-only. This is the first pass by the other reviewer, and it deliberately did
not start from Codex's findings. Codex converged onto comment-precision Lows about runner
internals; the defects below are mostly one layer in from there — in the fixture the guard is
supposed to make unnecessary, and in what the suite does and does not actually exercise.

---

## Blocking

### B1 · The pre-seeded magazine envelope can NEVER be accepted as fresh, so the suite's one stated money protection is inert — and three comments say it works

`tests/e2e/cloud.setup.ts:100` seeds the envelope with

```ts
      sourceSections: ['2. Encoder'],
```

against the markdown seeded at `tests/e2e/cloud.setup.ts:82-83`:

```ts
    `# ${'A seeded video with a summary'}\n\n## 2. Encoder\n` +
```

The serve path derives its comparison titles from that markdown with the parser, not from the
heading text. `lib/html-doc/parse.ts:54-56`:

```ts
    const ord = headingLine.match(/^(\d+)\.\s+(.*)$/);
    const numeral = ord ? ord[1] : null;
    const title = ord ? ord[2].trim() : headingLine;
```

so `## 2. Encoder` yields `title === 'Encoder'`, and `lib/html-doc/serve-doc.ts:71` takes
`parsed.sections.map((s) => s.title)` → `['Encoder']`. `lib/html-doc/read-model.ts:16-17`
compares element-by-element:

```ts
  return envelope.sourceSections.length === titles.length &&
    envelope.sourceSections.every((t, i) => t === titles[i]);
```

`'2. Encoder' !== 'Encoder'` → `sameTitles` false → `isFresh` false (`read-model.ts:24`) →
`readFreshMagazineModel` returns `not_ready` (`read-model.ts:37-38`) → `resolveMagazineModel` falls
through the B1 early return at `serve-doc.ts:78-79`, past the `tryGet` probe, into
`reserve_serve_model` and a live Gemini call (`serve-doc.ts:118-173`).

Verified by replicating both regexes on the exact seeded string: parsed titles `["Encoder"]`,
seeded `["2. Encoder"]`, `sameTitles` false.

The file the setup says it copied its shape from gets this right, which is what makes it a typo
rather than an unknown contract. `tests/integration/share-route.test.ts:56` seeds
`## 1. Intro` and `:88` seeds `sourceSections: ['Intro']` — numeral stripped. `:291` does the same
for two sections. `:229` uses a deliberately-wrong value to exercise the *drift* path. The e2e
setup took the shape and kept the numeral.

**Three load-bearing comments assert the opposite of what the code does:**

- `tests/e2e/cloud.setup.ts:86-92` — "⚠ SEED THE MAGAZINE MODEL TOO, OR THE SUITE SPENDS REAL MONEY
  ON EVERY RUN." The seed as written does not stop that.
- `tests/e2e/cloud-journey.spec.ts:22-23` — "The setup now pre-seeds the magazine model so the
  serve path finds one." It does not find one; it finds a stale one and pays to replace it.
- `playwright.cloud.config.ts:22` — "NO MONEY IS SPENT ANYWHERE IN THIS SUITE". True today only
  because rung 4 is skipped, not because of the mechanism the sentence credits.

**Failure scenario, concrete:** un-skip rung 4 (`cloud-journey.spec.ts:135`) — which the skip
comment at `:132-134` explicitly invites — and every run reserves `magazine_est_cents` and calls
Gemini. The money guard *will* fire (that part works), but the run is red for a reason the author
was told was already fixed.

**And the skip comment's own economics are wrong.** `cloud-journey.spec.ts:117-127` says:

> the resolver is judging the seeded envelope STALE and regenerating: most likely `sourceSections`
> not matching the titles its own parser derives from the markdown … Each attempt to guess that
> contract costs 6–12¢ of real Gemini spend. Today's debugging put 24¢ through the local ledger
> before this was understood.

The hypothesis is correct, and it is not a guess — it is three lines in two files
(`parse.ts:54-56`, `read-model.ts:16-17`) plus a working sibling fixture. 24¢ was spent on a money
path to learn something that reading answers in a minute, and the conclusion drawn was "this is an
open contract, skip the rung" rather than "the fixture has a typo". Calling it "a bounded reading
task, not an open question" (`:134`) while leaving it unread is the same shape as the defects this
branch has spent four rounds removing.

Fix is one token: `sourceSections: ['Encoder']`. I have not run the suite, so I cannot claim rung 4
then passes — `isFresh` also requires `generatorVersion === GENERATOR_VERSION`, which the setup does
pass (`cloud.setup.ts:101`), and `readTitleStableModel`'s `model.sections.length >= titles.length`
holds (1 ≥ 1). Those are the only other gates I found on the read path.

---

## High

### H1 · "globalSetup runs on every invocation that gets as far as running tests" is FALSE for every test-server run — UI mode, `--watch`, and the VS Code extension

`tests/e2e/cloud-global.ts:50-54` is the whole argument for deleting the fixture instead of stamping
it with a run id:

> The fix is identity by construction rather than identity by stamp: `globalSetup` runs on every
> invocation that gets as far as running tests — including partial ones — so deleting both files
> here means a fixture can only exist if THIS run's setup project wrote it. There is no id to check
> because there is nothing stale to check it against.

That universal claim is false on the test-server path. In `node_modules/playwright/lib/runner/index.js`:

- `TestRunner.runGlobalSetup` (`:6215-6234`) runs `createGlobalSetupTasks(config)` **once** and
  stores the cleanup for later: `this._globalSetup = { cleanup }`.
- `TestRunner.runTests` (`:6372-6376`) builds its task list as
  `[createApplyRebaselinesTask(), createLoadTask(...), ...createRunTestsTasks(config2)]`.
  `createRunTestsTasks` (`:5836-5843`) is `[phases, reportBegin, pluginBegin…, runTests]`.
  **No global setup task.** Every subsequent run in the session skips it.
- Watch mode proves the lifecycle in this same file: `runWatchModeLoop` calls
  `await testServerConnection.runGlobalSetup({})` once at `:7155` and then loops on `runTests`.
- The dispatcher hard-codes `doNotRunDepsOutsideProjectFilter: true` (`:6609`), so when the user
  filters to a project or a single test, the `setup` project — a *dependency* — is not run at all.

**Failure scenario:** `npx playwright test --ui --config playwright.cloud.config.ts` (or `--watch`).
globalSetup fires once: both fixture files are deleted, a ledger baseline is taken. The developer
clicks "run" on the `cloud` project or on rung 3 alone. The setup project does not re-run
(`doNotRunDepsOutsideProjectFilter`), globalSetup does not re-run, and nothing is deleted. Rung 3
seeds a new playlist row into the live database on every click while `playwright/.auth/cloud-fixture.json`
still names the owner and playlist from whenever setup last ran in that session. That is exactly
"a file with no run identity, compared against a live database" — the hazard `cloud-fixture.ts:15-17`
says has been eliminated.

Second consequence, on the money half: in that same session the baseline is from session start and
the check runs only in `runGlobalTeardown` (`:6235-6240`) when the UI is closed. Dozens of runs sit
inside one window, the verdict names no run, and a UI session that is killed rather than closed
never fires the guard at all. The "WHERE IT STILL MAKES NO CLAIM" list (`cloud-global.ts:25-40`)
does not contain this, and it is a bigger hole than three of the four items that are on it.

Codex r4 waved at this with "`--ui` is not claimed here". It *is* claimed — by the word "every" at
`cloud-global.ts:51` and again at `playwright.cloud.config.ts:30-31`. Either narrow both sentences
to the CLI runner or restore an identity stamp for the paths where deletion does not happen.

---

## Medium

### M1 · There is a SECOND un-intercepted path to the YouTube Data API, fired automatically by the component under test, and the ledger cannot see it

`cloud-journey.spec.ts:37-39`:

> The one call that would reach YouTube and enqueue paid work — POST /api/jobs — is intercepted in
> step 3, and only that call

`PlaylistSidebar` calls `backfillPlaylistTitles()` from its mount effect
(`components/cloud/PlaylistSidebar.tsx:182`) and again from the post-ingest refresh effect
(`:250`), whenever `result.some((p) => !p.playlistTitle)`. That reaches
`app/api/playlists/backfill-titles/route.ts:84`, `await fetchPlaylistTitleOrNull(p.playlistKey, apiKey)`
— the real YouTube Data API, once per null-title row, with no interception and no ledger row of any
kind. The guard is structurally blind to it.

It is reachable because **the seeder creates null-title rows and the title fixes are unchecked**.
`tests/integration/helpers/seed.ts:11-13` inserts a playlist with no `playlist_title`. Both places
that repair it discard the result:

- `tests/e2e/cloud.setup.ts:63` — `await svc.from('playlists').update({ playlist_title: listedTitle }).eq('id', listed.playlistId);`
- `tests/e2e/cloud-journey.spec.ts:85` — same shape for the rung-3 playlist.

PostgREST does not throw on an update that matches zero rows, and neither call inspects `error`.
Any failure of either statement turns a locator timeout into an outbound YouTube call on a suite
whose config promises it "runs unattended, every time, for free"
(`playwright.cloud.config.ts:20`). Check both errors, and either narrow the header sentence or
intercept `**/api/playlists/backfill-titles`.

### M2 · The main pane never renders in a browser, and the one comment that enumerates the gap says otherwise

Every rung that opens a page opens `/` with no query string: `:60`, `:66`, `:80`, `:177`, `:184`.
`app/page.tsx` → `CloudApp` → `CloudAppBody` renders `PlaylistLibrary` only when
`searchParams.get('playlist')` is non-null (`components/cloud/CloudApp.tsx:98-107`). So across the
whole suite:

- `PlaylistLibrary`, `VideoList`, `FilterBar`, `IngestProgressBanner` and `ScopeProvider` are never
  mounted.
- The video seeded by `seedPromotedVideo` — the fixture the setup works hardest to build — is never
  rendered on screen. Rung 5 reads its bytes over HTTP; nothing displays it.
- The sidebar link is asserted visible three times (`:67`, `:81`, `:112`) and never clicked, so
  "the sidebar link leads to a working library view" is untested.

Rung 3's own success path does `router.push('/?playlist=…')` (`CloudApp.tsx:88`) and lands on a
playlist with zero videos, so even incidentally the list view is only ever exercised in its empty
state.

Against that, `cloud-journey.spec.ts:129-133`:

> WHAT IS AND IS NOT COVERED WITHOUT IT. Step 5 already proves the summary blob round-trips through
> the serve path … What is missing is only "the magazine HTML renders in a browser"

"Only" is wrong. Also missing, and acknowledged nowhere in this file, the config, or the roadmap
line quoted at `:6-8`: the library pane, playlist deletion (`DeletePlaylistDialog`), sharing
(`ShareDialog`), dig-deeper serving, and PDF. A completeness claim in the one comment whose job is
to bound the skip is worse than no claim, and this branch's round-3 commit
(`bfe7640 "the coverage list was one item too generous"`) already fixed this exact species once.

### M3 · The teardown reads the ledger while the app server is still up and possibly still writing

Teardown order, from the runner: `createGlobalSetupTasks` (`runner/index.js:5828-5834`) emits
`[removeOutputDirs, ...pluginSetup, ...globalTeardowns, ...globalSetups]`, and the task loop
`unshift`s each teardown as its task starts (`:5655`). So teardowns run last-registered-first: this
guard, **then** the `webServer` plugin teardown. The Next dev server is alive when `readLedger()`
runs.

Playwright aborts in-flight requests when it closes a browser context; Node does not abort the
handler that was already executing. Any request a rung fired and did not await — and the app fires
several on its own (`listVideos` on the rung-3 push, `IngestProgressBanner`'s probe, the sidebar
refetch) — can complete after the final read. A handler that reaches `reserve_serve_model` writes
its cents after the guard has already compared. That is a "money moved, guard silent" window, and
it is the one class the `WHERE IT STILL MAKES NO CLAIM` list at `cloud-global.ts:25-40` does not
name, while naming SIGKILL, a global timeout, a dead webServer and a hypothetical
`globalTeardown` file.

Not reachable through a money path today (rung 4 is skipped, rung 5's md path short-circuits before
`resolveAndParse` — `app/api/html/[id]/route.ts:77-84`). It becomes reachable the moment rung 4
comes back. Either add it to the list or quiesce before reading.

### M4 · The guard accuses the suite of spending money that something else spent

`cloud-global.ts:82-88` throws with `THE CLOUD E2E SUITE MOVED MONEY … the usual cause is a serve
path finding no pre-seeded magazine model and regenerating it.`

The stability loop in `readLedger` only rules out a concurrent writer during the read itself —
five round trips, milliseconds. Nothing rules one out during the **run**, which is tens of seconds
against a database `playwright.cloud.config.ts:35-36` describes as "one shared stack". A developer
with a browser tab open on `localhost:3001` viewing any magazine document — the exact scenario
`cloud-fixture.ts:76` lists as a cause of the *other* error — moves both witnesses and gets a
capitalised accusation naming the wrong culprit, on a run that behaved perfectly. The failure text
should say "the ledger moved during this run" and offer the external-writer explanation with equal
billing, or the two witnesses should be scoped to the owner the run created.

---

## Low

- **L1 · No locality assertion on the client the guard uses.** `adminClient()`
  (`tests/integration/helpers/clients.ts:7-9`) takes whatever `NEXT_PUBLIC_SUPABASE_URL` /
  `SUPABASE_SERVICE_ROLE_KEY` are in the environment; `tests/integration/setup.ts:27-36` only checks
  they are non-empty. `lib/supabase/dev-login.ts` is described at `cloud.setup.ts:15-16` as failing
  closed unless the URL is local — the guard has no such gate, so a `.env.test.local` pointing
  anywhere else deletes local fixture files and reads that project's ledger with its service key.
  Cheap fix: assert a loopback URL in `cloudGlobalSetup` before the baseline.

- **L2 · `playwright.cloud.config.ts:30-33` still overclaims.** "it deletes both fixture files on
  every invocation that reaches it — including a partial `--project=cloud --no-deps` one" carries
  the same "every" as H1 and the webServer caveat Codex r4 already raised. Two sentences in two
  files making the same claim is also two places to fix it.

- **L3 · Rung 5 is an HTTP assertion wearing a browser rung's title.** `'5 · the summary downloads
  as markdown'` (`:144`) uses `page.request.get` (`:145`) — no UI affordance, no `download` event,
  no click. It proves the route answers with the right bytes and header, which is worth having, but
  in a suite justified as "the thing a manual pass cannot" do
  (`playwright.cloud.config.ts:19-20`) it is an integration test that happens to live here. Rung 2
  (`:65-68`) is also fully subsumed by rung 3's first two statements (`:80-81`).

- **L4 · The run's money behaviour depends on `guardrail_config` left behind by whoever ran last.**
  The e2e setup pins nothing; the integration suite writes this singleton freely, including
  `daily_cap_cents: 3` (`tests/integration/serve-model-charge.test.ts:68`, deliberately below
  `magazine_est_cents = 6`). With that value left in place, every serve reserve fails the global
  arbiter and returns `at_capacity` (`supabase/migrations/0014_serve_owner_budget.sql:81-85`), so a
  restored rung 4 would go green having proved nothing about the seed. Fail-closed, so not a money
  hole — but it is a "passes for the wrong reason" hole in the very rung this branch is holding open.

- **L5 · One caveat missing from the teardown claim.** `cloud-global.ts:19-21` says a throw in the
  guard "still fails the run". True when everything else passed; `TaskRunner.run` is
  `return status === "passed" ? teardownStatus : status` (`runner/index.js:5643-5645`), so when the
  test phase already failed the guard's verdict does not reach the exit code and survives only as a
  `reporter.onError` line (`:5668-5670`). The run is non-zero either way, but "it moved money" and
  "rung 3 timed out" become the same exit status — worth one clause, given this file's standard.

---

## Explicitly found nothing

Checked and cleared, with the reasoning, so the next round does not re-spend it:

- **The stability loop in `readLedger` (`cloud-fixture.ts:67-79`) is sound.** I tried to build an
  interleaving that returns a state that never existed and could not. The exit condition needs two
  *consecutive* `readOnce` results to agree, `readOnce` calls are strictly sequential (each is
  awaited before the next is issued), and `ledger_audit.id` is `bigint generated always as identity`
  (`0020_reservation_release.sql:13`) so it is monotonic. If pass *n* reads a `spend_ledger` value
  that reflects commit W, then W committed before pass *n* returned, hence before pass *n+1*'s audit
  query was issued, so pass *n+1* sees W's audit row too — two consecutive torn reads cannot agree.
  The off-by-one in the message is also correct: 1 + up to 4 calls = "5 consecutive reads".
- **PostgREST's `max_rows = 1000` (`supabase/config.toml:17`) does not truncate the cents witness.**
  `spend_ledger` is "global, one row per UTC day" (`0011_cost_guardrails.sql:12`), so the unordered,
  unpaginated `select('reserved_cents, actual_cents')` cannot lose rows at any realistic age.
- **Test filters do NOT strip the setup project**, so the deletion does not break `-g`, a file/line
  filter, or `--last-failed` on the CLI. Dependency projects are prepended from the **unfiltered**
  `projectSuites` map (`runner/index.js:2462-2468`), and `--last-failed` is a `postShardTestFilter`
  applied at `:2458`, before that prepend. I expected this to be a workflow-loss finding; it is not.
- **Relative paths are consistent.** `fs.rmSync('playwright/.auth/…')` resolves against
  `process.cwd()`, and so does Playwright's own read — `prepareStorageState` passes the raw string
  to `fs.readFile` (`playwright-core/lib/coreBundle.js:57134-57140`). Writer
  (`cloud.setup.ts:127-135`), deleter and reader agree.
- **The local config cannot consume or be broken by these files**: `testIgnore: /cloud[.-]/`
  (`playwright.config.ts:11`) excludes `cloud.setup.ts`, `cloud-journey.spec.ts` and
  `cloud-global.ts`.
- **No browser-reachable Gemini path bypasses the ledger.** The only serve-side call is
  `generateMagazineModelForServe` at `serve-doc.ts:168`, unreachable without a `reserved` return
  from `reserve_serve_model`, which increments `spend_ledger.reserved_cents` before returning
  (`0014_serve_owner_budget.sql:81-85`). The other two Gemini entry points in `app/` are LocalApp-only:
  `app/api/quick-view/backfill/route.ts` reads the filesystem and is triggered only by
  `BackfillOverlay`, imported once, at `components/local/LocalApp.tsx:7`; `app/api/videos/[id]/regenerate`
  likewise. (The YouTube-side gap is M1, and it is not a Gemini path.)
- **The cents witness always has non-zero amplitude**: `check (magazine_est_cents >= 1)`
  (`0012_serve_model_charge.sql:20`), so a reserve can never move `spend_ledger` by 0 and hide.
- **Runner claims in `cloud-global.ts:18-23` are accurate.** Installed version really is
  `playwright@1.60.0` and `@playwright/test@1.60.0`. The teardown task is `unshift`ed before
  `task.setup?.()` is awaited (`runner/index.js:5654-5656`), the teardown runner sets
  `_isTearDown = true` (`:5651`) and therefore does not interrupt on error (`:5671`), and
  `globalSetupResult` is only invoked `if (typeof … === "function")` (`:5902-5903`) — which is what
  the single-`return` shape at `cloud-global.ts:101` now defends. The round-4 change is a real
  mechanism, not a comment.
- **Rung 1's locator is genuinely cloud-only.** `getByRole('navigation', { name: /playlists/i })` —
  the only `<nav>` in the repo is `components/cloud/PlaylistSidebar.tsx:298`, `aria-label="Playlists"`,
  and `LocalApp` has none. It cannot pass against LocalApp, which is the failure it was written for.
- **Rung 6's locators match the real component.** `AccountMenu.tsx:63-64` puts the email in a `<span>`
  with an `aria-hidden` chevron sibling, so the accessible name is the email alone and `exact: true`
  holds; `role="menu"` at `:69` and `role="menuitem"` with text `Sign out` at `:77-81`.
- **Rung 3's strict-mode risk is not live.** `getByRole('textbox')` (`:105`) is unambiguous because
  `FilterBar` only renders under `PlaylistLibrary`, which needs `?playlist` (`CloudApp.tsx:98`), and
  no rung ever sets it. `/^Add/` (`:109`) matches both `Add ▸` and the `Adding…` disabled state
  (`NewPlaylistModal.tsx:96`) and nothing else on the page.
- **`npx tsc --noEmit` is clean** on the branch.

---

NOT CONVERGED
