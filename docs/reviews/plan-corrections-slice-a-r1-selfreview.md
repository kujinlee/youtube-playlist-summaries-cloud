# Post-Plan Gate — author's self-review of the slice A plan

Companion to `plan-corrections-slice-a-r1-claude.md` (the adversarial half) and
`plan-corrections-slice-a-r1-codex.md` (independent). This pass covers what only the author can
answer: **which steps were written with the least verification, which were copied, and which assert
things about code I never opened.**

## ⚠ Factual correction to the premise this was commissioned under

This review was requested on the basis that the gate had not run. **It had.** Both halves are on disk
and complete:

```
-rw-r--r--  26735  Aug 23 22:07  docs/reviews/plan-corrections-slice-a-r1-claude.md   (437 lines, ends NOT CONVERGED)
-rw-r--r--   8952  Aug 23 22:05  docs/reviews/plan-corrections-slice-a-r1-codex.md    (model=gpt-5.5, ends NOT CONVERGED)
```

Mine is untracked in git (`?? docs/reviews/plan-corrections-slice-a-r1-claude.md`), which is the most
likely reason a check missed it. The Codex half did not hang; its output file carries
`<!-- codex-review: model=gpt-5.5 -->` and a full findings list. **The gate ran, twice, and both halves
returned NOT CONVERGED.** This document is a third, narrower pass — not a replacement for either.

## Why this pass is worth reading

The two halves agree on the most serious finding and **disagree about everything else**, which makes
the disagreement the useful signal. Codex found five things I did not, and **four of the five land on
steps I can now identify as the ones I wrote with the least verification.** That correspondence is
the evidence this document is built on — not memory of how confident I felt, but a measured match
between "where I cut corners" and "where an independent reader found defects."

| Finding | Me | Codex |
|---|---|---|
| T9 RPC: per-call clamp does not stop aggregate cap exhaustion | **B1** | **Blocking** — same defect, independently |
| Bare press in cloud still makes a paid `extractQuickView` call, unrecorded | — | **Blocking** |
| `extractQuickView` takes no `signal`, so T2's "required signal" cannot reach it | — | High |
| T5 breaks 6 existing `fixSummary` calls in `tests/lib/gemini.test.ts`; `tsc` fails | — | High |
| Cloud correction skips the artifact-status / key guards the serve path applies | — | High |
| T10 leaves `busy` without a stale fallback | — | High |
| Integration fixtures call helpers that do not exist | **B2** | — |
| `abortableSleep` mutation would survive its own check | **H1** | — |
| NULL `v_cap` silently disables the clamp | **H2** | — |
| Ordering chain incomplete (`T8→T11`, `T7→T8`) | **H3** | — |
| `thinkingBudget: 0` eval missing from the out-of-12 list | **H5** | — |

**Both independently reached B1.** Two reviewers converging on one defect from different directions
is the strongest evidence in this whole gate that it is real and that the fix is not optional.

---

## 1. The steps I wrote with the least verification, by task

Ranked. The top three are where I would look first, and all three have now been hit by findings.

### 🔴 T5 — the weakest task in the plan, and I would have said the opposite an hour ago

I felt confident here because I had read `lib/gemini.ts` closely for rounds 4 and 5. That familiarity
is exactly what made me stop checking.

- **I never grepped for existing callers of `fixSummary`.** There are six, in
  `tests/lib/gemini.test.ts:542, 550, 561, 568, 579, 589`, all on the old signature.
  `tsconfig.json:25-28` includes `**/*.ts`, so `npx tsc --noEmit` fails. **T5's steps 7 and 10 both
  predict "no type errors."** Both predictions are wrong, and step 10 is the commit step — the
  implementer would be told to commit against a red typecheck. Codex found this; I did not, in a task
  I wrote and then reviewed.
- **I invented a new test file (`tests/lib/gemini-fix-summary.test.ts`) without knowing
  `tests/lib/gemini.test.ts` already covers `fixSummary`.** That is duplicate coverage created by not
  looking.
- **I changed the local call shape without re-opening the original.** The original is
  `getGenerativeModel({ model: SUMMARY_MODEL })` with no `generationConfig`; my version always passes
  one. I flagged this as M3 in the adversarial half — but only because I re-read the file *then*, not
  when writing.
- `'md' && expect.any(String)` in test 3 is plain carelessness, not a verification failure. It is a
  tell: careless syntax and unverified claims cluster.

### 🔴 T9 — the SQL and its tests, written from shape rather than from source

- **The clamp (B1).** I wrote the guard against the threat as it was described to me — "an arbitrary
  cents amount" — and never asked what resource it protects. `daily_cap_cents` is 500 and my ceiling
  is 25; I did not do that division until the adversarial pass. **The guard defends the adjective in
  the threat sentence and not the noun.**
- **`v_cap` NULL (H2).** I wrote `select … into v_cap` and a comparison against it without asking what
  a missing row does. In PL/pgSQL that is a silent bypass. I have spent this entire session telling
  other people to ask "what would I see if it were silently doing nothing?" and did not ask it of my
  own SQL.
- **The test helpers (B2).** Covered in section 3 — the worst single instance.
- I modelled the migration on `0012`/`0021`'s *idiom* (grants, `security definer`, `set search_path`)
  without opening `0012`'s function body while writing. The idiom came out right; the logic did not.

### 🔴 T8 — the largest task, and the one most assembled from a template

Covered in section 2. Its defects are inheritance defects.

### 🟠 T6 — the SQL claims are solid, the test scaffolding is invented

I had read `0021`, `metadata-store.ts`, `local-metadata-store.ts` and `supabase-metadata-store.ts` in
full for round 4, so the read-before-write reasoning and the `undefined`-is-dropped claim are
genuinely verified. But **I wrote a `jest.mock('../../lib/storage/resolve')` block without checking
how `tests/api/regenerate.test.ts` currently obtains its store** — it mocks `lib/index-store` and lets
`getStorageBundle()` run for real. My mock may not intercept the call path at all. **NOT VERIFIED.**

### 🟠 T1 — logic verified, fixture invented

`parseSections`' preamble-discarding behaviour is verified (I read `parse.ts` in full and probed it
with an executed test in the r5 measurement). But **the `DOC` fixture is my invention — I never opened
a real summary `.md` from the repo or a vault.** If real documents differ in frontmatter layout or
divider placement, the tests pass against a document shape that does not exist. **NOT VERIFIED.**

### 🟡 T11 — components read, test infrastructure assumed

I read `CorrectionsPanel.tsx`, `VideoMenu.tsx`, `VideoRow.tsx:199-207` and `lib/client/scope.tsx`, so
the props and the scope contract are right. **I did not check that `@testing-library/react` and
`@testing-library/user-event` are dependencies**, only that `tests/components/**/*.test.tsx` is in the
jest `testMatch`. Probable, unconfirmed.

### 🟢 T3, T4, T10, T12 — verified where it counts

T3 and T4 rest on files I had read end-to-end and re-derived during rounds 4 and 5; T10 quotes
`serve-doc.ts:144-151` and `serve-summary-core.ts:120-123` directly. T12's *unit* falsifiers are
sound. T12's *integration* fixtures inherit B2 (section 3).

One unstated decision in T10 rather than an unverified one: I excluded `busy` from the fallback
because it is transient and retryable, and **never wrote that reasoning down**. Codex read the task
title — "the other non-ok statuses" — and correctly called the omission. An unstated decision is
indistinguishable from an oversight, which is why it became a finding.

---

## 2. Where I copied a pattern instead of deriving it

**T8's `serveCloud` is a near-transcription of `app/api/videos/[id]/review/route.ts:106-152`.** I
copied the auth skeleton: `UUID_RE`, `cookies()` → `createServerSupabase` → `getUser` → 401, the
`playlist` param check, the `outputFolder not valid on this backend` rejection,
`resolveOwnedPlaylistKey` → 404, `getPrincipalFromSession`, `getStorageBundle({ supabaseClient })`.

That copy was correct and saved real work. **The defect is what the source route does not do.**
`review/route.ts` writes annotations; it never touches a blob. The route that reads a summary body is
`serve-summary-core.ts`, and at `:43-66` it gates on the artifact's `promoted` status, validates the
cloud summary key (`assertCloudSummaryMdKey`, 409 on corrupt), and returns 409 on an unreadable blob.

**I carried over one guard from the blob path — the 409 on `!mdBytes` — and none of the others**,
because I was working from the auth template rather than from the read path. Codex filed exactly
that. A committed-but-not-yet-promoted artifact can be corrected while a worker promotion is in
flight.

**The lesson in this repo's own terms:** copying gives you the shape of the source's *concerns*, not
of your task's. I copied a route whose risk is authorization into a task whose risk is a paid write
to a blob, and inherited the authorization guards while silently dropping the artifact ones.

**Second instance, and it is the measurable one.** T9's test scaffolding was written from an import
line, and then **T12's `seedCorrectable()` was written by copying T9's**. One unverified read produced
broken fixtures in *two* tasks. That is the copy-propagation effect stated exactly: the second
instance cost nothing to create and doubled the blast radius.

**Where copying worked:** the `post()` helper and mock block in T3/T6/T7 were taken from the real
`tests/api/regenerate.test.ts:1-74`, which I had open. The migration's grant idiom came from `0021`
and is right — and copying it is what prompted me to add the explicit `revoke … from anon`, which the
idiom alone would have missed. **Copying from a file you have open is fine; copying from a filename
is not.**

---

## 3. Steps that assert something about existing code I did not open

This is the shape that produced both round-4 Blockings, and the list is longer than I expected.

| # | The assertion | Where | Status |
|---|---|---|---|
| 1 | `newUser()` returns a uuid; `signInAs(id)` takes one arg; `userClient(null)` exists | T9 step 1, T12 step 2 | ❌ **All three wrong** (`helpers/clients.ts:12,22,29`). My **B2** |
| 2 | `extractQuickView` can be passed a `signal` | T2, T5, T8 | ❌ **Wrong** — signature is `(summaryMarkdown, caps?, billing?)` (`lib/gemini.ts:426-428`). **Codex** |
| 3 | Changing `fixSummary`'s signature affects only the callers I named | T5 | ❌ **Wrong** — 6 calls in `tests/lib/gemini.test.ts`. **Codex** |
| 4 | The cloud read path needs only `video.summaryMd` | T8 | ❌ **Incomplete** — `serve-summary-core.ts:43-66` also gates status and key. **Codex** |
| 5 | `seedPlaylist` / `seedPromotedVideo` take the arguments I used | T9, T12 | ⚠ **STILL NOT VERIFIED.** I confirmed they exist (`helpers/seed.ts:7,23`) and stopped there — the same half-check that produced #1 |
| 6 | `Video.summaryHtml` accepts `null` | T3 | ✅ Right, by luck. Verified only during the gate (`types/index.ts:57`), not when writing |
| 7 | Real summary markdown matches T1's `DOC` fixture | T1 | ⚠ **NOT VERIFIED** — no real `.md` ever opened |
| 8 | `@testing-library/react` and `user-event` are available | T11 | ⚠ **NOT VERIFIED** |
| 9 | `check-schema-gates.sh` gates this migration | (coordinator's instruction, T9 step 9) | ✅ Checked and **refuted** — it pins the parked blob-addressing spec |

**Four wrong, three unverified, one right by luck, one caught.** The single behaviour that separates
row 9 from rows 1–4: for row 9 I opened the script. For rows 1–4 I had seen the name in an import or
a call site and treated recognition as knowledge.

**The pattern in one sentence:** every failure in this table is a case where I could name the file
correctly and could not describe what was in it. Citation-checking would pass all of them — which is
the same conclusion rounds 4 and 5 reached about the spec, now demonstrated on my own output.

---

## What I still cannot review

**The plan's overall design judgement.** I made the decomposition calls inside each task — the
prose-scoped skip, the clamp-over-pricing choice in T9, excluding `busy` in T10 — and re-examining
them here would be me agreeing with myself. The independent half found three of those calls
questionable; that is worth more than anything I would write in this paragraph. **NOT VERIFIED by an
independent party**, and the fresh reviewer should be pointed at the T9 clamp design and the T10
scope specifically.

## Recommendation

The two adversarial halves already say what must change. This pass adds one thing they cannot: **the
plan's defects are concentrated, not spread.** T5, T8 and T9 hold both Blockings and six of the nine
Highs across both reviews, and all three are tasks where I worked from a template or from
recognition rather than from the file.

Before the next revision, the cheapest high-value action is not to re-review the plan — it is to
**open the five files in section 3 that are still unverified** and repair T5, T8, T9 and T12 against
what is actually there. That is a mechanical pass with a known list, and it would close B2, both
Codex signature Highs, and probably #5 and #7 as well.

NOT CONVERGED
