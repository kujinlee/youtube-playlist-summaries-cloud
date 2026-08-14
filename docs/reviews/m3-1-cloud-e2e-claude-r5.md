<!-- claude adversarial review — round 5, the Claude half of the dual gate -->
<!-- reviewed: 83b9742 (branch docs/m31-review-round-2), read as a fresh change; diffed against 11a9d42 -->
<!-- ⚠ HEAD MOVED MID-REVIEW: 6c2dd06 landed while this was being written. Re-checked against it; -->
<!--    see "Head drift" below. Every anchor in this doc is against the tree at 6c2dd06. -->
<!-- instrument: reading + `npx tsc --noEmit` (exit 0). The e2e suite was NOT executed. -->

# M3.1 cloud e2e money guard — Claude adversarial review, round 5

`83b9742` is the response to round 4. Both round-4 findings are genuinely fixed in the sense that
matters — the seed literal is corrected and rung 4 really does take the free path (see *Explicitly
found nothing*, first two items, where I trace it end to end rather than take the commit message's
word for it).

The defects below are all in the **fix**, not in what it replaced. Two of them descend directly from
my own round-4 Lows, and one of those Lows was **wrong**; the commit implemented it faithfully and
is worse for it. That is stated first because it is the finding I am least able to be objective
about and the one a third reviewer should check hardest.

**Head drift.** `6c2dd06 "rung 4 now asserts WHICH path served it"` landed while this review was in
progress. It acts on Codex r5's single Low — the `X-Magazine-Stale` assertion — which I had reached
independently as my own L4; that finding is therefore recorded below as **already actioned**, with
the residue that survives it. `6c2dd06` also, without meaning to, supplies the measurement that
falsifies H1 (see H1), and introduces M4.

**Reviewer disagreement, flagged rather than resolved.** Codex r5 returned **CONVERGED** on the same
commit and explicitly cleared two of the things I file findings on — *"Guardrail pin: no finding"*
and *"Loopback assertion: no finding"* (`docs/reviews/m3-1-cloud-e2e-codex-r5.md`). On the guardrail
pin we are not looking at the same question: Codex asked whether pinning those two columns lets the
fresh path work (it does), and did not ask whether the *justification* for touching the row is true
or what the write leaves behind. This repo's own memory says the reviewer that reports a finding has
been right three times out of three against a CONVERGED verdict; adjudicate H1 by reading
`cloud.setup.ts:62-66` against `cloud-journey.spec.ts:164`, not by counting votes.

---

## Blocking

None. Nothing here makes the branch unmergeable on its own; H1 comes closest.

---

## High

### H1 · The `guardrail_config` pin multiplies the stack's money kill-switch by ten, permanently — and the sentence justifying it is false

`tests/e2e/cloud.setup.ts:67-70`:

```ts
  const pinned = await svc.from('guardrail_config')
    .update({ daily_cap_cents: 5000, magazine_est_cents: 6 }).eq('id', true).select('id');
```

The migration default is **500** (`supabase/migrations/0011_cost_guardrails.sql:28`,
`daily_cap_cents int not null default 500 … -- $5.00`). `daily_cap_cents` is not a test knob; 0011
introduces it as *"an atomic money kill-switch"* and it is the operand of the global arbiter in
every reserve on this stack — `enqueue_job` (0011) and `reserve_serve_model`
(`0014_serve_owner_budget.sql:85`). Nothing restores it. After one `npm run test:e2e:cloud`, the
local stack's daily spend ceiling is **$50 instead of $5**, for that developer, until something else
happens to write the row.

So the file whose sibling config asserts *"NO MONEY IS SPENT ANYWHERE IN THIS SUITE"*
(`playwright.cloud.config.ts:22`) raises the ceiling on everyone else's spend tenfold as a side
effect. On a stack that has already put 24¢ of real Gemini money through this exact path, that is a
money control being widened by a fixture.

**The justification is factually wrong.** `tests/e2e/cloud.setup.ts:62-66`:

> Left behind, every serve reserve here returns at_capacity and the render rungs go green having
> proved nothing about the seeded model: a pass for the wrong reason on the one rung this suite
> exists for.

Trace it. `at_capacity` → `serve-summary-core.ts:122`
(`case 'at_capacity': return { ok: false, status: 503, error: 'at capacity' }`) →
`app/api/html/[id]/route.ts:85` (`if (!r.ok) return json({ error: r.error }, r.status)`) → the
document response is **503**. Rung 4's first line is `expect(res?.status()).toBe(200)`
(`cloud-journey.spec.ts:159`). `page.goto` does not throw on an HTTP error status; it returns the
response, the expect fails, the rung goes **red**. There is no rung that renders magazine HTML
without asserting 200, and rung 5 is `format=md`, which short-circuits before `resolveAndParse`
(`route.ts:75-82`) and is unaffected by any cap. **No rung goes green under `at_capacity`.**

That claim is mine — round-4 L4 — and I did not check it. It was already checkable at the time:
rung 4's body at `11a9d42` carried the same `toBe(200)` line under its `test.skip`.

**The repo now contains the measurement that falsifies it, two commits apart, in two files.**
`6c2dd06` tried to reach the stale branch by mutation and wrote down what happened —
`cloud-journey.spec.ts:164-167`:

> Reaching it needs `reserve_serve_model` to answer `owner_over_budget` — **NOT `at_capacity`, which
> returns 503 without consulting the stale path** (serve-doc.ts:139-150) … Two attempts were made: a
> global `daily_cap_cents: 1` produced the 503

So `at_capacity` producing a 503 rather than a green rung is no longer an inference of mine; it is
recorded as an observed result in this branch. `cloud.setup.ts:62-66` still says the opposite, forty
lines away in the file the observation was made against. One of the two has to go, and it is not the
measurement.

**What the pin actually changes**, in the only scenario where it is not dead code (the seed drifts,
or `GENERATOR_VERSION` is bumped, so `isFresh` is false and the reserve is reached):

| | without the pin, `daily_cap_cents` left at 3 | with the pin |
|---|---|---|
| reserve | `at_capacity` (PJ004, `0014:85`) | `reserved` |
| Gemini | not called | **called** |
| spend | **0¢** | 6¢, plus a `serve_settle` audit row |
| rung 4 | red (503 ≠ 200) | red (the lead text is LLM paraphrase) |

The pin converts a **free red into a paid red**. It removes the one fail-closed brake standing
between a fixture regression and a live Gemini call, on the suite built specifically because a
fixture regression caused live Gemini calls.

**And that conversion has now been observed, in `6c2dd06`'s own numbers.** Its message reports the
successful mutation as `spend_ledger 642 -> 648`. The ledger stood at **642¢** for the day *before*
the mutation — i.e. already above the migration default cap of 500 (`0011:28`). With
`daily_cap_cents` at its default, `642 + 6 <= 500` is false, the guarded update at `0014:83-85` finds
no row, PJ004 fires, and the reserve returns `at_capacity` **without calling Gemini**. The pin to
5000 is the reason that reserve succeeded and the reason the 6¢ was spent. For a deliberate mutation
that is the desired outcome and the money was well spent. The point is that the mechanism does not
know the difference: on the day the seed drifts by accident, the same pin will buy the same call.

**Two more problems with the pin as written, both consequences of pinning at all:**

- **It is a hardcoded restore, and the sibling file argues at length against exactly that.**
  `tests/integration/serve-config-invariant.test.ts:15-31` faces the same shared-singleton problem
  and rejects the hardcoded fix in writing — *"The fix is NOT a hardcoded restore
  (`update({ daily_cap_cents: 500, … })`) — that would reintroduce the exact tautology this suite
  exists to avoid: if a future migration retunes a default, a hardcoded literal here would silently
  mask the drift"* — then reads the live column DEFAULT out of `information_schema` and applies that
  (`:32-51`, `:67-72`). The e2e file writes a literal, and not even the default one. There is also
  already a helper for "pin generous headroom", `ensureGuardrailHeadroom`
  (`tests/integration/helpers/clients.ts:45-51`), which this does not use — in a file that justifies
  reusing the env loader on the grounds that *"a second copy of an env loader is a second thing to
  drift"* (`cloud.setup.ts:25-26`).
- **It pins one half of a coupled pair.** `per_owner_serve_daily_cents` carries
  `check (per_owner_serve_daily_cents >= magazine_est_cents)`
  (`0014_serve_owner_budget.sql:16-17`), and two integration files write it directly
  (`html-download.test.ts:101`, `serve-doc-materialize.test.ts:50`). If any future test legally
  leaves the pair at `magazine_est_cents = 1, per_owner_serve_daily_cents = 1`, this update raises
  `magazine_est_cents` to 6 against a per-owner cap of 1, the check fires 23514, and the setup dies
  with `could not pin guardrail_config` on every subsequent run until someone resets the database.
  Pinning two of five coupled columns is the half-pinned state, and it is more brittle than none.

**Recommendation:** delete the pin. `at_capacity` is a correct, free, loud failure for this suite,
and it is the behaviour the money guard's whole design prefers. If headroom is genuinely wanted
later, restore from `information_schema` defaults the way `serve-config-invariant.test.ts` does, and
put the row back afterwards.

### H2 · The seed's correctness is still a hand-copied literal, in the file where that exact class cost a week and 24¢ — and it is one line from being impossible

`tests/e2e/cloud.setup.ts:99-103` seeds the markdown, and `:126` seeds the titles the resolver will
be compared against:

```ts
    `# ${'A seeded video with a summary'}\n\n## 2. Encoder\n` + …
…
      sourceSections: ['Encoder'],
```

Two literals in one file that must agree under a transformation defined in a third
(`lib/html-doc/parse.ts:54-56`). Nothing checks that they agree. The commit's response to the
round-4 Blocking was to correct the literal and add eight lines of comment (`:119-125`) explaining
the contract — which fixes the instance and leaves the class exactly where it was.

**Concrete failure, and it is the one the brief asks about:** add a second section to the seeded
markdown — the obvious next move for backlog #44, which wants the library pane rendered with real
content. `titles` becomes `['Encoder', 'X']`, `sourceSections` stays `['Encoder']`,
`sameTitles` is false at `read-model.ts:16-17`, `isFresh` false, and the serve path reserves and
calls Gemini (`serve-doc.ts:118-173`). Cost: 6–12¢ per run, plus a red rung whose message says
nothing about section titles. That is the identical failure this branch just spent a week and 24¢
on, re-armed and waiting for the next person to touch a string.

Ask this repo's own question (memory: *hardcode only what fails loudly*): what happens when this
literal goes stale? It fails **expensively and mutely** — the rung reports "text not visible", the
guard reports "the ledger moved", and neither names the seed. That is the profile the rule says must
be derived, not hardcoded.

**The fix is one line, and the file already imports app code to do exactly this kind of thing**
(`writeModelEnvelope`, `GENERATOR_VERSION`, `SupabaseBlobStore` at `:33-36`):

```ts
const md = `# …\n\n## 2. Encoder\n▶ […]\nSeeded prose for the e2e journey.\n`;
await seedSummaryBlob(svc, user.id, listed.playlistKey, video.base, md);
…
      sourceSections: parseSummaryMarkdown(md).sections.map((s) => s.title),
```

`lib/html-doc/parse.ts` is a leaf (its only import is `../transcript-timestamps`), so this pulls in
nothing.

**The counter-argument, stated so it does not have to be rediscovered:** deriving makes the seed
agree with the parser by construction, so the fixture can no longer catch a parser change. That is
the right trade here. The fixture's job is to *be fresh*; the parser's contract is pinned by the unit
suite and by `tests/integration/share-route.test.ts`. A tautological assertion is a defect; a
tautological fixture is a fixture that cannot be wrong.

---

## Medium

### M1 · The narrowing was applied to one of the two files round 4 named, and the two now contradict each other

`cloud-global.ts:62-81` is correctly narrowed: *"ON THE CLI RUNNER, globalSetup runs once per
invocation"*, followed by the ⚠ paragraph naming UI mode, `--watch` and the VS Code extension. I
re-verified the mechanism against the installed `playwright@1.60.0` / `@playwright/test@1.60.0`:
`TestRunner.runGlobalSetup` (`node_modules/playwright/lib/runner/index.js:6215-6232`) runs
`createGlobalSetupTasks` once and stashes `this._globalSetup = { cleanup }`; `runTests` at `:6375`
composes `createRunTestsTasks(config2)` (`:5836`) with **no** global-setup task; and the test server
hard-codes `doNotRunDepsOutsideProjectFilter: true` at `:6609`. The narrowed text is accurate.

`playwright.cloud.config.ts:30-33` was **not touched by this commit** (the diff is
`docs/backlog.md`, the review doc, and the three `tests/e2e/` files):

> it deletes both fixture files on every invocation that reaches it — including a partial
> `--project=cloud --no-deps` one.

The universal is still there, in the file a developer opens first, and it now says the opposite of
`cloud-global.ts`. Round-4 L2 named this file explicitly — *"Two sentences in two files making the
same claim is also two places to fix it"* — and one was fixed. A contradiction between two comments
is strictly worse than the single wrong comment it replaced: whichever one you read, you cannot tell
which was updated.

### M2 · Declining the run-id stamp trades a detectable hazard for an undetected one, and the notice lives where the affected user never looks

`cloud-global.ts:78-81`:

> RUN THIS SUITE FROM THE CLI (`npm run test:e2e:cloud`). UI and watch mode are not supported by the
> guard … restoring a stamp would detect the staleness without preventing it.

Arguing the other side, as the brief asks. **Detection is the deliverable here.** What happens today
in UI mode is not "unsupported", it is *silently testing the previous session's owner*: `readFixture`
(`cloud-fixture.ts:81-91`) reads a file that was not deleted, rungs 1–2 assert against
`fx().listed.title` from an earlier session, and rung 3 inserts a playlist under `fx().ownerId`. If
that owner still exists — the suite never deletes owners — every rung can pass. A green suite
describing a database state nobody seeded is exactly the hazard `cloud-fixture.ts:15-17` says the
deletion eliminated; the deletion eliminates it on the CLI only, and the replacement on the other
path is a paragraph.

A stamp is three lines: put `runId` in the fixture and in the storage-state directory name, and have
`readFixture` throw when they disagree. It is redundant on the CLI (harmless) and is the only signal
on the path where deletion does not happen. "Detect but not prevent" is the normal standing of every
other guard in this suite — the money guard detects, it does not prevent.

Second, the placement: this warning is in `tests/e2e/cloud-global.ts`. Playwright's UI shows the
developer the **spec**. Nothing in `cloud-journey.spec.ts` or in `package.json:25` mentions it. If
the narrowing is kept, the sentence belongs in the spec header and in the npm script's neighbourhood,
not only in the file the affected user has no reason to open.

### M3 · `assertLocalStack` is a second copy of a predicate this repo already has, and it is looser than the original

`cloud-global.ts:134-143`:

```ts
  if (host === '127.0.0.1' || host === 'localhost' || host === '[::1]') return;
```

Its own docstring (`:128-133`) frames the fix as reaching parity with dev-login:
*"`/dev-login` refuses to work against anything but a local URL (lib/supabase/dev-login.ts) — this
guard … had no equivalent gate."* But `lib/supabase/dev-login.ts:16` does not inline a host list; it
calls `isLocalSupabaseUrl`, whose whole body is
`return host === 'localhost' || host === '127.0.0.1'` (`lib/supabase/is-local-url.ts:11`). The new
guard is therefore not the equivalent gate, it is a **third** host predicate that admits `[::1]`
where the canonical one does not.

Nothing catastrophic follows — with `NEXT_PUBLIC_SUPABASE_URL=http://[::1]:54321` the new guard
passes, the fixtures are deleted, the baseline is taken, and then `/dev-login` 404s and the setup
times out on a heading locator — but that is a confusing failure produced by the divergence, and the
divergence is the recurring shape this project has a memory entry for (*two mechanisms for one
concern; duplicate vocabulary is the observable shadow of a duplicate mechanism*). `import
{ isLocalSupabaseUrl } from '@/lib/supabase/is-local-url'` and throw on `false`: one predicate, and
the e2e guard then tracks the security gate automatically instead of drifting from it.

Rejections worth knowing about either way, since both lists are host-exact: `host.docker.internal`,
a docker-compose service name (`kong`), `0.0.0.0`, `127.0.0.2`, and any `.local` mDNS name are all
refused. Fail-closed is the right default; it is worth one clause in the error message so the person
who hits it does not think their stack is broken.

### M4 · A known flake in the regression net exists only in a commit message (introduced by `6c2dd06`)

`6c2dd06`'s message ends:

> Also observed: rung 2 failed once and passed on an identical re-run. Flaky, cause unknown, not
> investigated — noted here rather than left as folklore.

Recording it beats not recording it, and the instinct is right. But a commit message is not a place
anyone looks: `grep` for `flak|intermittent` across `tests/e2e/`, `docs/backlog.md` and
`docs/roadmap-to-launch.md` returns **nothing about this**. The next person to see rung 2 go red will
re-run it, see green, and conclude nothing — which is precisely the folklore the sentence says it is
avoiding. This repo already treats an unidentified flake as tracked debt:
`docs/roadmap-to-launch.md:386` carries *"an UNIDENTIFIED unit-suite flake 2026-07-30"* as an open
item with a status line.

It also matters more here than in a unit suite, for two reasons this branch established itself.
Rung 2 is the **second** rung of a `test.describe.serial` block (`cloud-journey.spec.ts:10`), so an
intermittent failure there silently withholds rungs 3–6 — including rung 3, *"THE STEP THIS SUITE
EXISTS FOR"* (`:85`), and rung 4, whose whole point is the money path. And an e2e suite justified as
the thing that *"runs unattended, every time"* (`playwright.cloud.config.ts:20`) is worth exactly its
signal-to-noise ratio; one unexplained red teaches the reader to re-run rather than to look.

Rung 2 is also, by round-4 L3's reasoning, fully subsumed by rung 3's first two statements
(`:94-95`), so one option is to delete it and let rung 3 carry the assertion — which would move the
flake rather than fix it, but at least moves it onto a rung that would then be investigated.
Whatever the disposition: it belongs in `docs/backlog.md` and in the spec header, not in `git log`.

---

## Low

- **L1 · The citation excludes the line it cites.** `cloud.setup.ts:120` and
  `cloud-journey.spec.ts:140` both say `parse.ts:53-55`, and the commit message repeats it. The
  assignment that proves the claim is `lib/html-doc/parse.ts:56`
  (`const title = ord ? ord[2].trim() : headingLine;`); line 53 is `const headingLine = …`. The
  cited range is off by one at both ends and omits the load-bearing statement. Trivial, except that
  a `file:line` in this repo is offered as evidence, and this one does not open on the evidence.

- **L2 · A citation that points at prose rather than at the mechanism.** `cloud.setup.ts:110-111`
  supports the md-path exemption with *"serve-summary-core.ts:28 — it reads the blob and returns
  without ever calling resolveMagazineModel"*. Line 28 is inside that file's **doc comment**, i.e.
  another assertion. The code is `app/api/html/[id]/route.ts:75-82`, whose `if (format === 'md')`
  returns before `resolveAndParse` at `:84`. Cite the branch.

- **L3 · "so no null-title row is ever listed. If that check ever fails, this suite makes outbound
  API calls" is backwards.** `cloud-journey.spec.ts:43-44`. If the check fails it *throws* —
  `cloud.setup.ts:81-82` and the `expect`s at `cloud-journey.spec.ts:103-104` — the run stops and no
  page is ever loaded, so no backfill fires. The hazard is the check being **removed or bypassed**,
  not failing. As written the sentence tells the next reader that a red check means outbound spend,
  which is the opposite of the design and could talk someone into deleting it.

- **L4 · ~~Rung 4 does not assert it got the FRESH model rather than the stale one.~~ ALREADY
  ACTIONED at `6c2dd06`.** Reached independently here and by Codex r5; the fix landed mid-review at
  `cloud-journey.spec.ts:171` (`expect(res?.headers()['x-magazine-stale']).toBeUndefined()`), and the
  reasoning attached to it is correct: `owner_over_budget` → `readTitleStableModel` →
  `{ status: 'ok', stale: true }` (`serve-doc.ts:146-152`) is the second route to a 200 carrying the
  seeded lead with no money moved, and `X-Magazine-Stale` (`lib/html-doc/file-response.ts:47`,
  `route.ts:92`) is the only thing that separates them. The comment's ⚠ block is the right disclosure
  — the header has never been observed *present*, so the assertion is not mutation-proven and says
  so. **One residue, and it is this repo's own recurring shape:** `res?.headers()['x-magazine-stale']`
  evaluates to `undefined` when `res` is `null`, so the new assertion is **vacuously true** on a
  response that never arrived. It is non-vacuous only because `expect(res?.status()).toBe(200)` two
  lines above fails first. That ordering dependency is invisible at the assertion, and a future edit
  that moves or relaxes the status check turns a money guard into a tautology. `expect(res).not
  .toBeNull()` first, or read the header off a non-optional local.

- **L5 · Un-skipping rung 4 puts the two most deterministic rungs behind the only environment-
  dependent one.** Under `test.describe.serial` a rung-4 failure aborts the remainder
  (`cloud-journey.spec.ts:10`), so rung 5 (md download) and rung 6 (the sign-out session check) now
  stop running whenever the seed drifts, a cap is tight, or Gemini is unreachable. Both were
  previously reached unconditionally. Rung 4 is the only rung whose outcome depends on
  `guardrail_config`, on `spend_ledger`'s state for the day, and on an external API being
  configured; making it a gate for the sign-out regression net is a sequencing choice worth stating,
  and moving it after rung 6 costs nothing.

- **L6 · "every request the rungs make is awaited" overstates it slightly.** `cloud-global.ts:44-45`.
  True of the requests the *rungs* issue; the app issues its own — `PlaylistSidebar`'s mount and
  post-ingest refetches (`components/cloud/PlaylistSidebar.tsx:175`, `:248`), `listVideos` on rung
  3's `router.push`, the ingest banner's probe — and none of those is awaited. None reaches a money
  path today, which is the point the bullet is making, so the conclusion holds; the premise as
  written is the kind of universal this branch has already had to narrow twice.

- **L7 · Backlog #43's closing note quotes a guard that no longer exists.** `docs/backlog.md:51`
  retains *"rung 6 already asserts the ledger did not move"* from the original filing. The guard was
  moved out of the spec three rounds ago and rung 6 is the sign-out rung
  (`cloud-journey.spec.ts:195-209` records the move). Preserving the original text is right; the
  ✅ block appended to it is the place to say the sentence was superseded.

---

## Explicitly found nothing

Checked and cleared, with the reasoning, so round 6 does not re-spend it.

- **The guard is now mutation-proven end to end, and that is the strongest single fact on this
  branch.** `6c2dd06` forced a stale envelope, the serve path called Gemini, and the run-level
  teardown fired with `ledger_audit 307 -> 308, spend_ledger 642 -> 648`. Every earlier round argued
  the guard *would* catch a paid regeneration from the migration text; this is the first time it has
  been made to. It cost 6¢ and it was worth it — note the contrast with the 24¢ spent guessing at the
  seed contract, which reading answered for nothing. The rule this branch wrote for itself holds up:
  read the contract for free, spend money only to prove the alarm rings.

- **The round-4 Blocking is genuinely fixed, and rung 4 passes for the right reason.** Traced end to
  end on the exact seeded bytes rather than trusting the commit message. The markdown at
  `cloud.setup.ts:101-102` has one `##` line, `## 2. Encoder`. `parseSections` (`parse.ts:54-56`)
  splits it into `numeral: '2'`, `title: 'Encoder'`; `serve-doc.ts:71` takes
  `parsed.sections.map((s) => s.title)` → `['Encoder']`; `sameTitles` (`read-model.ts:16-17`) now
  compares equal, `generatorVersion` matches `GENERATOR_VERSION` (`constants.ts:5`, seeded at
  `cloud.setup.ts:127`), so `isFresh` is true and `serve-doc.ts:78-79` returns **before** the `tryGet`
  probe, before `reserve_serve_model`, before Gemini. Keys line up: the setup writes
  `MODEL_KEY(base)` = `models/${videoId}.json` under principal
  `{ id: user.id, indexKey: listed.playlistKey }` (`cloud.setup.ts:113-140`, `model-store.ts:32`),
  and the serve path derives the identical `base` from `mdKey.replace(/\.md$/, '')`
  (`serve-summary-core.ts:71`) with `getPrincipalFromSession` (`:41`). The envelope validates:
  `ModelEnvelopeSchema` (`model-store.ts:15-24`) makes `sourceMdHash` optional and is deliberately
  not `.strict()`, `MagazineModelSchema` needs only `sections` (`types.ts:45-47`), and the seeded
  section supplies `lead` + `bullets`. `renderMagazineHtml` emits the lead at
  `lib/html-doc/render.ts:99` and the `2:12–2:20` label at `:88`, which are the two strings rung 4
  asserts.

- **I could not build a way for rung 4 to go green without the seeded envelope being accepted.** I
  enumerated every route to `status: 'ok'` in `resolveMagazineModel`:
  · **fresh** (`:79`) — the intended one, free.
  · **`in_flight`** (`:139-143`) — re-reads through the same `readFreshMagazineModel`, so it is the
  same freshness proof; and it needs a live lease row for `(owner, doc_key, day)`, impossible on the
  first serve of an owner created seconds earlier in the same run.
  · **`owner_over_budget` → title-stable stale** (`:146-152`) — the one path that would render the
  seeded lead without proving freshness, and it is unreachable for a fresh owner:
  `0014_serve_owner_budget.sql:74-78` inserts `serve_owner_budget` at `spent_cents = 0` and the
  guarded increment `0 + magazine_est_cents <= per_owner_serve_daily_cents` cannot fail, because
  `0014:16-17` constrains `per_owner_serve_daily_cents >= magazine_est_cents`. Recorded as L4 anyway
  because the assertion that closes it costs one line — and `6c2dd06` has since added it
  (`cloud-journey.spec.ts:171`), reaching the same conclusion by the same route and confirming
  independently that `at_capacity` cannot get there.
  · **`reserved`** (`:153`) — Gemini's output replaces the lead, so the text assertion fails, and
  both witnesses move (`reserved_cents` at `0014:84`, a `serve_settle` row at
  `0025_settle_is_observable.sql:114`) so the guard fires too.
  A cached response cannot mask any of this — the route sets `Cache-Control: private, no-store`
  (`route.ts:91`) — and an error page cannot, because every non-`ok` arm of `resolveAndParse`
  returns JSON with a non-200 status (`serve-summary-core.ts:118-125`, `route.ts:85`) and rung 4
  asserts the status first. "Nothing spent AND the seeded text visible" is, today, equivalent to
  "the fresh path was taken".

- **The `guardrail_config` write cannot break the integration suite by leaving values behind.** I
  read the consumers rather than assuming. The one file that would be sensitive to a dirty singleton,
  `serve-config-invariant.test.ts`, restores every relevant column from the live catalog DEFAULT in
  its `beforeAll` (`:67-72`) precisely for this reason; `cap-soundness.test.ts:11,32` reads
  `dig_est_cents`/`dig_max_attempts`, which this update does not touch; every other integration file
  that depends on a value sets it itself. `magazine_est_cents: 6` is already the migration default
  (`0012_serve_model_charge.sql:20`), so only `daily_cap_cents` actually moves — which is H1, and it
  is a hazard to the *stack*, not to the integration suite. The remaining blast radius is
  concurrency: two suites against one local stack now fight over this row (e.g.
  `serve-model-charge.test.ts:68` sets `daily_cap_cents: 3` to exercise `at_capacity`), and unlike a
  concurrent ledger writer — which `readLedger`'s stability loop refuses to average over
  (`cloud-fixture.ts:67-79`) — a concurrent config writer is invisible to every instrument here.
  Deleting the pin (H1) removes this too.

- **`.select('id')` after `.update()` is the right way to get "one row matched", and does not change
  the statement.** It sets PostgREST's `Prefer: return=representation`; the UPDATE is unchanged and
  service_role holds SELECT on both tables (`0011_cost_guardrails.sql:38`, and the playlists grants). A
  matched-but-unchanged row still returns: Postgres writes a new tuple for an UPDATE even when every
  value is identical, and `RETURNING` yields it — there is no `BEFORE UPDATE` trigger on
  `guardrail_config` or `playlists` that could suppress it (grepped the migrations; there are none on
  either table). So `data.length === 0` really does mean "no row matched", which is what
  `cloud.setup.ts:70,82` and `cloud-journey.spec.ts:104` assert.

- **The loopback assertion does run before the deletion, and nothing destructive precedes it.**
  `cloud-global.ts:145-147` — `assertLocalStack()` is the first statement, `fs.rmSync` the second.
  The only thing that executes earlier is the module-scope `import '../integration/setup'` (`:98`),
  which reads `.env.test.local` and assigns env vars (`tests/integration/setup.ts:1-36`) and touches
  no database. It cannot be bypassed by env, either: the check reads
  `process.env.NEXT_PUBLIC_SUPABASE_URL` at call time, after that loader has resolved the
  `API_URL` alias (`setup.ts:23`). Its host list is the M3 finding; its *ordering* is correct.

- **The narrowed H1 text is accurate against the installed Playwright.** Line-by-line re-verified
  against `playwright@1.60.0` — see M1 for the four anchors. I also re-confirmed the round-4
  clearances that this commit's rewrites touch: teardown tasks are `unshift`ed at task start
  (`runner/index.js:5654-5656`), the teardown runner sets `_isTearDown` (`:5651`), and
  `globalSetupResult` is only invoked `if (typeof … === "function")` (`:5902-5903`) — which the
  single-`return` shape at `cloud-global.ts:154` still defends. `npx tsc --noEmit` exits 0.

- **The M4 rewrite of the failure text is correct on the facts.** `cloud-global.ts:122-123` —
  *"A new ledger_audit row means a serve settled or a release underflowed"*: the only writers of that
  table in the whole schema are `0025:114` (`serve_settle`, unconditional in `settle_serve_model`)
  and five `release_underflow` sites (`0020:85,124,170,286,293`, `0025:123,130`). No third kind
  exists. The two-explanations framing (`:114-121`) also fixes what round-4 M4 was actually about.

- **The un-skipping does not make the in-flight-teardown window (round-4 M3) live.** The bullet added
  at `cloud-global.ts:40-45` is the right disclosure, and its "in principle" hedge is correct: rung
  4's document is fully awaited by `page.goto`, and the rendered page issues no subresource requests
  (`dig: false` at `route.ts:88`, so no `digControl`; styles and the theme script are inline —
  `render.ts:118`). Playwright closes the context at test end. The genuinely un-awaited requests
  are the app's own (L6) and none of them reaches `reserve_serve_model`.

- **The main-pane coverage correction is accurate and complete this time.**
  `cloud-journey.spec.ts:46-53` now says the pane is never mounted and lists deletion, sharing,
  dig-deeper and PDF; `CloudApp.tsx:98` still gates `PlaylistLibrary` on `?playlist`, and no rung
  sets it (`:74, :80, :94, :216`). Backlog #44 carries the same list. Round-4 M2 is fixed, not
  reworded.

- **The YouTube-backfill hole (round-4 M1) is genuinely closed for every reachable path.** Both
  `update`s are now checked (`cloud.setup.ts:79-82`, `cloud-journey.spec.ts:101-104`), and the
  sidebar's two trigger sites both require `result.some((p) => !p.playlistTitle)`
  (`PlaylistSidebar.tsx:175`, `:248`). The owner is created fresh each run, so the only playlists it
  can list are the two this suite titles. The window between `seedPlaylist` and the `update` at
  `cloud-journey.spec.ts:97-102` is not a hazard: nothing triggers a sidebar refetch in it.

---

NOT CONVERGED
