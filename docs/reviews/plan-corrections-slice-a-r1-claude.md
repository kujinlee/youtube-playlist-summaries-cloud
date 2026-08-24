# Post-Plan Gate — slice A implementation plan, round 1 (Claude half)

Subject: `docs/superpowers/plans/2026-08-24-corrections-in-cloud-slice-a.md` (12 tasks, 86 steps).
Spec: `docs/superpowers/specs/2026-08-22-corrections-in-cloud-design.md`.

**Counts: 2 Blocking, 5 High, 6 Medium, 3 Low.**

## ⚠ Declared conflict of interest — read before weighting anything below

**I wrote most of these steps.** T1–T12's bodies are mine; the decomposition, the ordering section's
existence and the `T3 → T4` edge are the coordinator's. Reviewing your own work is the weakest
adversarial position there is, so:

- **Every code claim below was re-verified by opening the file**, not by recalling what I meant. That
  discipline is what produced **B2** and **H1** — two defects I introduced by asserting signatures I
  had seen imported but never opened. Both are in steps I wrote fast and felt sure about.
- **Authorship is tagged on every finding** (`[mine]` / `[coordinator]` / `[spec]`) so the counts can
  be discounted appropriately.
- **Where I could not be impartial I say so and mark NOT VERIFIED** rather than passing. There is one
  such item, listed at the end under *Declined*.

The honest summary: **the plan is not executable as written.** Both Blockings are mine, and one of
them (B1) is a live money defect that the design review specifically asked me to hunt and that I put
there myself two turns ago.

## What I executed

| Check | Result |
|---|---|
| `grep -n "^export" tests/integration/helpers/clients.ts` | **`newUser` and `signInAs` have different signatures than T9 and T12 assume; `userClient` does not exist** — B2 |
| `grep -n "^export" tests/integration/helpers/seed.ts` | `seedPlaylist`, `seedPromotedVideo`, **`seedSummaryBlob`** (T12 hand-rolls what this does) — L3 |
| read `lib/gemini.ts:132-149` (`abortableSleep`) | rejects with `AbortError` ✅ — but T5's test cannot distinguish it from the loop guard — H1 |
| read `supabase/migrations/0011_cost_guardrails.sql:11-18, 28, 36` | `spend_ledger` global one-row-per-day ✅; `daily_cap_cents` default **500**; `guardrail_config` singleton seeded ✅ |
| arithmetic: `500 ÷ 25` | **20 calls exhaust the global daily cap for every user** — B1 |
| `grep -rln ensureGuardrailHeadroom tests/` | **10+ integration suites depend on ledger headroom** that T9's tests consume without resetting — M1 |
| read `types/index.ts:57` | `summaryHtml: z.string().nullable().optional()` — T3's `patch.summaryHtml = null` typechecks ✅ (a concern I had, now dead) |
| read `lib/gemini.ts:474-476` (original `fixSummary`) | passes **no** `generationConfig`; T5 introduces `generationConfig: {}` on the local path — M3 |
| `grep -n "fixture eval" <spec>` | `:701` — §5.1 requires one before enabling `thinkingBudget: 0`; **no task does it and the out-of-12 list omits it** — H5 |
| placeholder scan of the plan | clean ✅ — the claim holds |

**NOT RUN:** nothing was executed against a database or Gemini; this is a document review. The
integration behaviours below are reasoned from the SQL and the helper signatures, not observed.

---

## Blocking

### B1 — the T9 clamp bounds the size of one lie, not the number of them, and the resource is global `[mine]`

**Where.** Plan Task 9, step 3's migration; spec §5.2's requirement 1. Code:
`supabase/migrations/0011_cost_guardrails.sql:11-13` (`spend_ledger`, `day date primary key`),
`:28` (`daily_cap_cents int not null default 500`), `:114` and `0012:88` (the cap predicate).

The clamp asks *"is this one number too big?"*. The threat model is *"can one account degrade every
other account?"*. Those are different questions and the plan answers only the first.

```sql
-- plan T9 step 3
if p_cents < 0 or p_cents > v_cap then
  raise exception 'record_correction_spend: correction spend % exceeds ceiling %', p_cents, v_cap;
end if;
…
grant execute on function record_correction_spend(int) to authenticated;
```

**Failure scenario, arithmetic included.** `record_correction_spend` is granted to `authenticated`,
so PostgREST exposes it at `POST /rest/v1/rpc/record_correction_spend` to **any signed-in user** —
including an anonymous account, which this product issues (`quota_allowance` carries
`is_anonymous` rows, `0011:22`). Nothing ties `p_cents` to a Gemini call having happened. The
attacker never exceeds the ceiling:

```
for i in {1..20}; do curl -s -X POST …/rpc/record_correction_spend \
  -H "Authorization: Bearer $USER_JWT" -d '{"p_cents":25}'; done
```

`actual_cents` reaches **500 = `daily_cap_cents`**. Every subsequent `enqueue_job` (`0011:114`),
`reserve_serve_model` (`0012:88`) and dig enqueue (`0018:63`) fails its
`reserved + actual + est <= daily_cap` predicate. **One free account has taken the whole product
down for the day, at a cost of 20 HTTP requests and zero spend.** Repeat daily.

The clamp makes each individual over-report ≤ 25¢. It does nothing about frequency, and the ledger it
writes to is the one global resource in the schema.

**Why this is mine and why that matters.** The coordinator specified the guard from the outside and
asked me to find the input that gets past it. I wrote the SQL and then reviewed my own clamp against
the threat it was given, rather than against the resource it protects. The spec's own sentence names
the shape correctly — *"lets one account exhaust the daily cap for every user"* — and the
implementation I wrote defends the *magnitude* clause of that sentence and not the *exhaust* clause.

**Suggested fix — the per-call ceiling is necessary and not sufficient. Add a per-owner bound:**

1. **Bound the owner, not just the call.** The schema already has the pattern:
   `serve_model_charge` is keyed `unique (owner_id, doc_key, day)` with a `max_serve_attempts`
   ceiling (`0012:13,21`). Mirror it — a `correction_spend_log(owner_id, day, cents, calls)` row with
   a per-owner daily ceiling, rejected loudly the same way. One account can then degrade only its
   own budget.
2. **Or tie the record to evidence.** The unforgeable version is the one slice C already owns: a
   reservation token issued before the call and settled after. That is exactly the protocol the user
   declined for slice A — which is worth saying out loud, because **B1 is evidence that "record
   without reserve" has a floor it cannot get under on a shared ledger.**
3. **Minimum, if neither lands in this slice:** do not grant the RPC to `authenticated` at all.
   Record spend from the worker or a service-role path, and accept that the attended route's spend is
   invisible until slice C — which is option (1) from #129, reconsidered with this cost known.

This needs the user, not the plan. It reopens #129 with information #129 did not have.

### B2 — T9's and T12's integration tests call helpers that do not exist with those signatures `[mine]`

**Where.** Plan Task 9 step 1 (whole test file); Task 12 step 2 (`seedCorrectable`, every `it`).
Code: `tests/integration/helpers/clients.ts:12, 22, 29`.

```
export async function newUser(): Promise<{ user: { id: string }; email: string; password: string }>
export async function signInAs(email: string, password: string): Promise<{ client: SupabaseClient; userId: string }>
export async function anonSession(): Promise<{ client: SupabaseClient; userId: string }>
```

Both task bodies assume something else:

| Plan says | Reality |
|---|---|
| `const ownerId = await newUser();` then uses `ownerId` as a uuid | returns `{ user: { id }, email, password }` — `ownerId` is an object |
| `const client = await signInAs(ownerId);` | takes **`(email, password)`**, two args, and returns `{ client, userId }` |
| `const anon = userClient(null);` | **`userClient` does not exist.** The anon helper is `anonSession()` |

**Failure scenario.** An engineer with zero context — the reader this gate is defined against — opens
T9, copies step 1, and gets three TypeScript errors before the red phase they were promised. Step 2
says *"Expected: FAIL — PostgREST reports `Could not find the function`"*. They will not see that.
They will see a compile failure, and the plan has just taught them that its stated red phases are
unreliable — which is the specific harm the brief names in its item 3.

**Root cause, stated plainly because it is the shape this project keeps hitting.** I read
`tests/integration/serve-doc-materialize.test.ts:2` — `import { adminClient, newUser, signInAs } from './helpers/clients';` — and wrote fixtures from the *names*. I never opened `helpers/clients.ts`.
The citation was correct and the claim about it was invented: *true about the object it names, silent
about what the object actually is.* Same shape as the r4 trigger and the r5 tripwire, authored by the
person who filed both.

**Suggested fix.** Rewrite both fixture blocks against the real signatures:

```ts
const { user, email, password } = await newUser();
const { client } = await signInAs(email, password);
const { error } = await client.rpc('record_correction_spend', { p_cents: 3 });
```

and use `anonSession()` for the anon case. Then re-check every other helper the plan names —
`seedPlaylist` and `seedPromotedVideo` were used from the same import line and their argument shapes
are **NOT VERIFIED** by me beyond their existence at `helpers/seed.ts:7,23`.

---

## High

### H1 — T12's mutation table records a mutation as caught that its test would not catch `[mine]`

**Where.** Plan Task 12 step 3, row *"Replace `abortableSleep` with `new Promise(setTimeout)`"* →
*"`gemini-fix-summary.test.ts` → aborts DURING the backoff"*. Also Task 5 step 1's fifth test.

The test:

```ts
const p = fixSummary('md', 'c', { signal: ac.signal });
await Promise.resolve();
ac.abort();
await expect(p).rejects.toThrow(expect.objectContaining({ name: 'AbortError' }));
expect(mockGenerateContent).toHaveBeenCalledTimes(1);
```

T5 wires **three** abort sites. Two of them satisfy this assertion independently:

- if `abortableSleep` is present, the abort rejects the sleep → `AbortError`, one call ✅
- if `abortableSleep` is replaced by a bare `setTimeout`, the sleep completes, the loop advances, and
  the **loop-top guard** (`if (opts.signal.aborted) throw new DOMException('aborted','AbortError')`)
  throws before the second `generateContent` — `AbortError`, **still one call** ✅

So the mutation the table names survives, and the test stays green. A mutation recorded as caught
which is not is worse than no mutation row: step 4 tells the implementer to write the result into the
PR body, so this ships as positive evidence for a guard that is untested.

Verified: `abortableSleep` does reject with `AbortError` (`lib/gemini.ts:132-149`) — the mechanism is
right; the *test* cannot distinguish the two sites.

The timing is separately fragile: a single `await Promise.resolve()` may fire `ac.abort()` before
`abortableSleep` is even entered, in which case the loop guard is what fires **in the unmutated run
too**, and the test never exercised the sleep at all.

**Suggested fix.** Isolate the site. Set `retries = 1`, use fake timers, and assert on *elapsed
behaviour* rather than the call count — the sleep must reject **without the timer firing**:

```ts
it('an abort during the backoff rejects the SLEEP, not the next loop iteration', async () => {
  jest.useFakeTimers();
  const ac = new AbortController();
  mockGenerateContent.mockRejectedValueOnce(new Error('transient'));
  const p = fixSummary('md', 'c', { signal: ac.signal }, 1, 400);
  await Promise.resolve(); await Promise.resolve();   // enter the sleep
  ac.abort();
  await expect(p).rejects.toThrow(expect.objectContaining({ name: 'AbortError' }));
  expect(jest.getTimerCount()).toBe(0);   // the timer was CLEARED, not run — only abortableSleep does that
  jest.useRealTimers();
});
```

`abortableSleep`'s `onAbort` calls `clearTimeout` (`:139`); a bare `setTimeout` does not. That is the
observable that separates them.

### H2 — a NULL `v_cap` silently disables the clamp, and step 5's mutation does not cover it `[mine]`

**Where.** Plan Task 9 step 3, and step 5's mutation-check.

```sql
select correction_max_cents into v_cap from guardrail_config where id = true;
if p_cents < 0 or p_cents > v_cap then
```

If that `select` returns no row, `v_cap` is `NULL`. Then `p_cents > NULL` is `NULL`,
`p_cents < 0 or NULL` is `NULL` for any non-negative input, and `if NULL then` is **false** — the
branch is skipped and **any positive amount is inserted**. The guard does not fail; it evaporates.

This is the question the plan itself tells the implementer to ask — *"what would I see if it were
silently doing nothing?"* — and the answer for this guard is "every test still green", because
step 5's mutation sets the ceiling to `2147483647` and never exercises the missing-row path.

Reachability is low: `guardrail_config` is a singleton seeded by `0011:36` with
`id boolean primary key default true check (id)`. But `service_role` holds `delete` on it
(`0011:35`), and "low probability" is not the standard for a guard on a global money resource.

**Suggested fix.** Fail closed, and mutation-check the closure:

```sql
select correction_max_cents into v_cap from guardrail_config where id = true;
if v_cap is null then
  raise exception 'record_correction_spend: guardrail_config missing — refusing to record unbounded spend';
end if;
```

Add to step 5: `delete from guardrail_config where id = true;` inside a transaction must make the
*accept* test fail with that message, then roll back.

### H3 — the ordering chain is incomplete: two more arm/safe pairs `[chain: coordinator; both tasks: mine]`

**Where.** Plan's "Hard ordering constraints" section, which states `T3 → T10 → T4` and asserts T9
adds nothing.

Both stated edges check out. `T3 → T4`: T4's conjunct plus an unconditional body write means every
bare press moves `mdHash` and books a regeneration — the ~6¢ figure is the serve path's own measured
number (`serve-doc.ts` money-guard comment). `T10 → T4`: attempts are `unique (owner_id, doc_key, day)`
with `max_serve_attempts` default 5 (`0012:13,21`) and `attempts_exhausted` maps to a bare 503
(`serve-summary-core.ts:121`), so a UTC-day-long outage is right. ✅

Two more pairs have the same shape and are stated nowhere:

**(a) `T8 → T11` — safety.** T11 deletes the cloud gate at `VideoMenu.tsx:181`
(`{!cloudMode && video.summaryMd && (`), making the corrections panel reachable in cloud mode. T8 is
what makes the route work there. Ship T11 first and every cloud user gets a **500** — the route calls
`getStorageBundle()` at `route.ts:36`, **outside the try block**, which throws without a client. This
is arming a UI against a backend that does not exist, and it is the identical shape to the two
already listed.

**(b) `T7 → T8` — compile.** T8's `serveCloud` imports and uses `MAX_CORRECTIONS_CHARS`, which T7
creates in `lib/corrections/apply-core.ts`. T8 before T7 does not build.

Neither is caught by numbering being "in order", because that is exactly what was true of T10 before
it was promoted. The section exists precisely so a scheduler cannot reorder around a coupling.

**Suggested fix.** Extend the section to a graph rather than one chain:

```
T1 → T2 → T5 → T7 → T8 → {T9, T11}
T3 ─┐
T10 ┴→ T4
T12 last
```

with (a) and (b) given rows in the cost table — (a)'s cost is *"every cloud user sees a 500 on a
button you just made visible"*, (b)'s is *"it does not compile"*.

**On completeness.** Three reviewers have now each found one edge the others missed (coordinator: T3;
me, twice: T10 then these two). I would not assert the graph above is complete either. The durable
fix is mechanical: **a step in T12 that greps each task's `Consumes` block against earlier tasks'
`Produces` blocks and fails on a forward reference.** A convention catches what you read; a script
catches what is there.

### H4 — T7's 413 test proves the catch, not the precondition the falsifier is about `[mine]`

**Where.** Plan Task 7 step 1, *"returns 413 summary-too-large when the preflight refuses the
document, NOT 500"*.

```ts
mockFixSummary.mockRejectedValue(new NonRetryableError('correction input 9000 tokens exceeds cap 8192'));
```

It mocks **`fixSummary`** rejecting. The preflight is `assertCorrectionInputWithinCap`, a *different*
function that T5 requires to run **before** `fixSummary`. So the test passes on an implementation
where the preflight was never wired at all and the error happens to come from somewhere else — and
spec §5.1's whole point is that the refusal must land *before any paid call*, because `fixSummary`
retries twice and an over-cap document would otherwise cost three full passes.

§7's row is *"over-cap input rejected **before** any call"*. This test cannot see that.

**Suggested fix.** Mock the preflight, and assert the paid call never happened:

```ts
jest.mocked(gemini.assertCorrectionInputWithinCap).mockRejectedValue(
  new NonRetryableError('correction input 9000 tokens exceeds cap 8192'),
);
const res = await post(VIDEO_ID, { outputFolder: OUTPUT_FOLDER, corrections: 'fix X' });
expect(res.status).toBe(413);
expect(mockFixSummary).not.toHaveBeenCalled();   // the assertion that matters
```

Keep the existing case too, retitled *"an ordinary NonRetryableError from elsewhere is still 500"* —
it is a good negative, just mislabelled.

### H5 — the spec requires a quality eval before `thinkingBudget: 0`; T5 enables it and no task or list item covers that `[spec requirement, T5 mine]`

**Where.** Spec §5.1, line 701: *"⚠ `thinkingBudget: 0` is a quality risk on this task — NOT
VERIFIED. Live gates exist for its billing behaviour … nothing for correction quality. **Run a
fixture eval before enabling.**"* Plan Task 5 step 4 enables it via `withCaps`, and step 8's mutation
asserts it is **present**.

No task runs a fixture eval, and the "Out of the 12 — must not be forgotten" section does not list
it. So the plan turns a spec item marked NOT VERIFIED into shipped behaviour, and its own mutation
check will report green for the thing the spec asked someone to question first.

This is the brief's item 6, and the answer is that the list is **not** complete.

**Suggested fix.** Add it to the out-of-12 list as a gate: *"a fixture eval of correction quality with
`thinkingBudget: 0` versus default, before T5's caps are enabled in prod — spec §5.1 marks this NOT
VERIFIED and T5 does not resolve it."* Also add the two §9 follow-ups the section omits (correct
backlog #23 per §1.1; move a summary fixture into the repo). Neither is code; both are spec asks with
no home.

---

## Medium

- **M1 — T9's tests mutate global shared state that ten other suites depend on `[mine]`.** Every
  assertion in Task 9 step 1 reads and writes `spend_ledger` for today, the single global row, and
  none resets it. `grep -rln ensureGuardrailHeadroom tests/` returns **10+ suites**
  (`worker-main`, `enqueue-dig`, `producer-roundtrip`, `dig-cloud`, `cancel-*`, …) that call
  `helpers/clients.ts:45`'s `ensureGuardrailHeadroom` precisely because the ledger accumulates across
  a run. T9's tests push `actual_cents` up by ~50¢ per run against a 500¢ cap and never restore it, so
  a full integration run can turn those suites red **depending on file order** — a nondeterministic
  failure whose cause is three files away. Fix: `beforeEach` snapshots `actual_cents` and `afterAll`
  restores it, or call `ensureGuardrailHeadroom(svc)` in `beforeAll` like every other suite does.

- **M2 — the structural validator checks H1 and frontmatter *presence*, so a rewritten title or a
  mutated `video_id` passes `[spec wording; T1 mine]`.** T1 tests `after.startsWith('---\n')` and
  `/^#\s+\S/m` — nothing compares the H1 text or the frontmatter fields to `before`. Spec §2 says
  exactly *"the H1 and frontmatter are present"*, so the implementation matches; the requirement is
  the weak part. A model that renames the document or changes `video_id` — which `parse.ts:124` reads
  and downstream consumers key on — has disobeyed in a way the validator was built to catch. Fix:
  compare the H1 line and the `video_id` frontmatter field byte-for-byte, and amend §2's sentence
  from "present" to "unchanged".

- **M3 — T5 changes the local Gemini call shape, and `withCaps`' contract promises it will not
  `[mine]`.** The original is `client.getGenerativeModel({ model: SUMMARY_MODEL })` — no
  `generationConfig` key at all (`lib/gemini.ts:474-476`). T5 makes it
  `generationConfig: withCaps({}, opts.caps, …)`, which on the local path returns `{}` — so the
  request now carries an empty `generationConfig`. `withCaps`' own docstring (`:30-33`) says *"the
  local `generateContent` call shape stays byte-identical"*. Probably harmless; unasserted either
  way, and it quietly falsifies a documented invariant. Fix: omit the key when `caps` is absent, or
  add a test pinning the local call shape.

- **M4 — T8 puts `assertVideoId` inside the try, so a malformed id 500s in cloud where it 400s in
  local `[mine]`.** `serveLocal` catches it at `route.ts:32-34` and returns 400 `invalid request`;
  T8's `serveCloud` calls it inside the main try, so it lands in the generic catch and returns 500.
  Same input, two status codes, and the review route it was modelled on validates before the try.
  Fix: move `assertVideoId` above the try in `serveCloud`, beside the UUID check.

- **M5 — T5 step 1's third test contains an expression that reads as a typo `[mine]`.**
  `expect(mockGenerateContent).toHaveBeenCalledWith('md' && expect.any(String), …)` — `'md' &&
  expect.any(String)` evaluates to `expect.any(String)`, so the test works, but an implementer
  copying it will either "fix" it wrongly or lose confidence in the surrounding code. Fix: write
  `expect.any(String)`.

- **M6 — T12's `deriveClassASignals({ …data!.data, id: s.videoId } as never, body)` `[mine]`.**
  `as never` defeats the type system to silence an error rather than constructing a `Video`. Fix:
  `as Video`, importing the type — and if that does not compile, the fixture is wrong and should be
  fixed rather than cast.

---

## Low

- **L1 — `p_cents = NULL` produces a not-null constraint violation, not the intended message
  `[mine]`.** Both comparisons yield `NULL`, the branch is skipped, and the insert fails on
  `actual_cents int not null` (`0011:15`). Safe, but the operator sees a Postgres constraint error
  instead of `correction spend … exceeds ceiling`. Untested. Add `if p_cents is null then raise …`
  and a case.

- **L2 — `correction_max_cents` default 25 has 3× headroom over the derived worst case, unexplained
  `[mine]`.** The cap-soundness test asserts `>= correctionActualCents({8192+4000, 8192}) * 3` ≈ 8¢.
  The comment says *"default 25¢ against a measured worst case of ~8¢"* without saying why 25 and not
  10. Given B1, the headroom is not free — every unexplained cent is 20 fewer requests to exhaust the
  cap. State the reason or lower it.

- **L3 — T12 hand-rolls a fixture the helpers already provide `[mine]`.** `seedCorrectable()` does
  `blob.put(principal, key, …)` plus a `merge_video_data` rpc; `tests/integration/helpers/seed.ts:66`
  exports `seedSummaryBlob`. Use it — a second way to seed the same thing is how fixtures drift.

---

## The brief's questions, answered directly

| | Question | Answer |
|---|---|---|
| 1 | Is the ordering chain complete? | **No — H3.** Both stated edges verify, and two more exist: `T8 → T11` (safety, 500s) and `T7 → T8` (compile). I do not claim the extended graph is complete either; the durable fix is the mechanical Consumes-vs-Produces check in H3 |
| 2 | Does T9's clamp make cap exhaustion impossible? | **No — B1.** 20 calls of 25¢ against a 500¢ global cap, from any authenticated account including an anonymous one, with no spend. The clamp bounds magnitude; the threat is frequency. The default of 25 is sound *per call* and unsound *in aggregate* (L2). The cap-soundness derivation itself is correct |
| 3 | Are the stated red phases right? | **One is wrong and one is misdirected.** T9 step 2 and T12's fixtures will fail to compile before reaching the predicted failure (**B2**); T7's 413 red phase fires from the wrong function (**H4**) |
| 4 | Do Produces/Consumes match across tasks? | **Yes for types, no for order.** `fixSummary`'s `{ text, usage }` with `usage: GeminiUsage \| null` is consistent in T5, T9 and T12, and `actualCents: number \| null` is used with the null case handled at every site. The mismatch is the forward references in H3(b) |
| 5 | Would the mutations actually be caught? | **One would not — H1.** The `abortableSleep` row survives its own mutation because the loop guard satisfies the same assertion. The `isFresh`, caps, and ceiling mutations are sound, except the ceiling's missing-row path (**H2**) |
| 6 | Is the out-of-12 list complete? | **No — H5.** It omits the `thinkingBudget: 0` fixture eval (spec §5.1, explicitly NOT VERIFIED) and both §9 follow-ups |
| — | Placeholders | **Clean.** The claim holds; I re-scanned |
| — | Task sizing | Reasonable. T8 is the largest and is close to the limit, but it is one deliverable — a reviewer cannot sensibly accept half a cloud branch |
| — | Negative tests assert which error | **Mostly yes** — T1 asserts `reason`, T9 matches the exception text, T7 asserts `code`. The exception is H4, which asserts the right code from the wrong cause |

## Declined — where I could not be impartial

**The `T3 → T4` ordering rationale and the r5 B1 finding it rests on.** I authored that finding, the
measurement behind it, and the task that acts on it. I re-read the code and it still looks right —
the callout is in the preamble `parseSections` discards, so the write moves the hash and buys
nothing — but a reviewer confirming his own three-turns-ago conclusion adds no information. **NOT
VERIFIED by an independent party.** The Codex half should be asked specifically to attack it; if it
converges there too, that is worth more than this paragraph.

## Verdict

Two Blockings, both mine, one of them a money defect on the exact guard this gate was told to attack.
The rest is repairable in a pass. The plan's *structure* is sound — the decomposition holds, the
interfaces line up, the placeholder discipline held — and none of the findings argue for re-cutting
tasks. But an engineer executing this today would hit a compile error in the first integration file
they touch, and would ship an RPC any user can use to take the product offline for a day.

NOT CONVERGED
