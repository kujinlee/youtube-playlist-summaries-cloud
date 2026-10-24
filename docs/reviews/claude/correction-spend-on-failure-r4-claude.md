# correction-spend-on-failure — round 4 — Claude half

Subject: `git diff origin/master...HEAD` at `f67683b9` (code at `4f60ac97`), branch `fix/correction-spend-on-failure`.
Mandate: refute, focusing on round 4's three questions (n, o, p) and the earlier ones where the redesign could have reopened them.

## What I ran

| Check | Result |
|---|---|
| `npx jest` on `tests/lib/gemini-fix-summary-real-sdk.test.ts`, `tests/lib/gemini-fix-summary.test.ts`, `tests/lib/corrections/`, `tests/api/regenerate-cloud.test.ts`, `tests/api/regenerate.test.ts`, `tests/lib/cloud-sync/regenerate-stamp.test.ts` | 9 suites, **141 passed** |
| `npx tsc --noEmit` | rc=0 |
| `python3 scripts/check-function-revokes.py` | rc=0, 28 migrations |
| Local Postgres (`supabase_db_youtube-playlist-summaries-cloud`), read-only catalog queries | the live `correction_allowance()` body does **not** contain `max_cents` (it is the final 0028); `prosecdef=t`, `proconfig={search_path=public}`, `provolatile=s`; EXECUTE: anon **f**, authenticated **t**, service_role f |
| Local Postgres, ROLLED-BACK probe | with no JWT claims: `ERROR: correction_allowance: authentication required`. With a real profile's `sub`: allowance `{"calls": 0, "max_calls": 8}` → `record_correction_spend(9)` and `record_correction_spend(0)` → allowance `{"calls": 2, "max_calls": 8}` → `ROLLBACK`. So 0028 reads the same row and the same UTC day that 0026 writes, and a 0¢ press is accepted (`p_cents < 0` is the only lower refusal) |
| NOT RUN | `scripts/check-schema-gates.sh` (it is not a rolled-back probe and the Codex half shares the database) and the integration files. The implementer's report says both are green against the final 0028; I did not re-verify that. |

## n — is every exit metered exactly once?

Traced `fixSummary` (`lib/gemini.ts`, the loop after the prompt):

- The loop-top guard throws before the push, so an attempt that is never dispatched gets no entry. The push (`attempts.push(...) - 1`) is synchronous and comes right after the guard, so nothing can happen between them.
- One push per loop iteration, one `slot` per push, and the response path **assigns** `attempts[slot]`. It never pushes. So a retry adds exactly one entry and a success replaces its own entry. The real-SDK case "a body-read timeout is RETRIED and every attempt is metered" pins this: `hits=2`, 2 entries.
- The replacement comes before `assertNotTruncated` and the empty check, so a paid response that is then discarded keeps its measured figures.
- In the catch, an abort during the backoff (`abortableSleep`) propagates out of the catch block with the earlier entries already in place. That is the mocked case "keeps the billed attempt when an abort lands during the backoff".
- In the route, the `meter` is created before the `try`, and nothing paid sits between them. The `finally` runs once per `serveCloud` invocation. The 429 and 503 refusals return inside the `try` with an empty meter, so `recordCorrectionSpend` returns at `attempts.length === 0`. Separate presses (including a client re-press after a timeout) each get their own meter, so nothing is recorded twice.
- `recordCorrectionSpend` cannot throw. `meteredCorrectionCents` is pure, and `raceRpc` puts a synchronous throw, a rejection and an error inside its union (`serve-rpc.ts`, the inner `async` IIFE).

Composition: the route tests mock `lib/gemini` but run the real `applyCorrection`. If `meter: input.meter` were dropped at the `apply-core.ts` call site it would still compile, because `meter` is optional on `fixSummary`. It would still be caught, though: the mock writes into `opts.meter`, so an unwired meter records nothing and "records the measured cents after a successful correction" goes red. I reasoned this through and did not run that mutation.

**No finding.**

## o — retrying an SDK timeout: cost and latency

- **Cost:** the loop bound is still `FIX_SUMMARY_RETRIES + 1 = 3` dispatches. Retrying a timeout re-rolls inside that bound and cannot add a fourth. The worst press stays at 3 × `CORRECTION_WORST_ATTEMPT_CENTS` = 9¢ against 0026's 12¢. A timed-out attempt is charged the full per-attempt bound, which covers any billing Gemini applies to a request it went on generating after we stopped reading.
- **Latency:** before round 3, a body-read timeout ended the press at once, because the name check rethrew it as `AbortError`. Now a hung Gemini can hold a press for about 3 × 60 s + 1.2 s. That is exactly the figure `app/api/videos/[id]/regenerate/route.ts`'s `maxDuration` comment already budgets per Gemini phase: 10 + 2 × 181.2 = 372.4 s, leaving ~48 s. The two correction RPCs add at most 2 × 3 s = 6 s, which fits that margin. Nothing enforces `maxDuration` on Fly anyway, as the route itself says. The client fetch in `components/CorrectionsPanel.tsx` has no timeout of its own.
- **Measured usage can exceed the bound?** The preflight counts `stripped` with the real `countTokens` and refuses anything over 8,192. The 4,000-token overhead covers the instructions plus a corrections field of ≤1,000 code points. A pathological field (byte-fallback characters at about 4 tokens per code point) could pass 4,000 by roughly a hundred tokens. Even at 4¢ per attempt, three attempts total 12¢, which is still within the ceiling. **No finding.**

## p — 0028 after its edit

The body only lost the `max_cents` read and return. Its safety properties are unchanged and are confirmed above from the live catalog: owner taken from `auth.uid()` and never a parameter, `search_path` pinned, PUBLIC and anon revoked, and the same UTC day expression as `0026` (`(now() at time zone 'utc')::date`, 0026:42). The route reads only `calls` and `max_calls` (`readCorrectionAllowance`) and fails closed on a missing or non-integer value. The ceiling test now holds `correction_max_cents` to 0026 alone, and 0028 no longer mentions it. Editing an applied migration is safe here only because 0028 has never left local, and the implementer re-applied it there. ⚠ Any OTHER database that applied the first 0028 (for example the throwaway staging project) keeps the old body. The old body is a strict superset, returning an extra `max_cents` key that the route ignores, so it is harmless, but it is drift.

## Findings

### F1 — Low — the accepted over-count is described as touching only the owner's allowance. It also moves the GLOBAL ledger, which gates everyone's paid work.

- **Where:** `lib/gemini.ts:522` (the `UsageMeter` docstring: *"an over-count only spends the owner's allowance sooner"*) and `docs/dashboard-entries.md:17374` (*"it can only use up a person's allowance sooner"*).
- **Input:** Gemini refuses every request before generating anything: a quota 429, a 5xx outage, or a bad `GEMINI_SUMMARY_MODEL` slug returning 400.
- **What happens:** each press dispatches 3 attempts. Each one is charged at the 3¢ bound, so the press records 9¢ through `record_correction_spend`. That function adds `p_cents` to `spend_ledger.actual_cents` (0026, the `update spend_ledger` at the end). `actual_cents` is the operand of the global daily-cap predicate `reserved_cents + actual_cents + v_est <= v_cfg.daily_cap_cents` in summary reservation (0011:114), serve charges (0012:88, 0014:84) and digs (0018:63).
  - So during a Gemini outage, phantom cents accrue at up to 8 × 9 = 72¢ per active owner per day, and they reduce headroom for **every** user's summaries, magazines and digs.
  - Today that is bounded and probably small. But the sentence that justifies the trade is false about who pays for it. I verified this by reading the SQL; I did not run it.
- **Fix:** correct both sentences to say that the over-count consumes the owner's allowance **and** the shared daily cap. Optionally, add a sentence to backlog #62's "what remains" or #61 noting that an outage-shaped failure inflates the global ledger. No code change is needed: classifying pre-generation HTTP errors as unbilled would bring back exactly the error-shape classification this round deleted, and the conservative direction is defensible. It just has to be described accurately.

### F2 — Low (observation, no change required) — `meter` is optional on `fixSummary`.

- **Where:** `lib/gemini.ts`, the `fixSummary` `opts` type.
- **What it means:** a future CLOUD caller can omit `meter` and silently restore the round-0 leak. The comment just above argues the opposite rule for `signal` ("optional here would let a caller silently restore…").
- **Why it is optional today:** `applyCorrection` requires `meter`, and the only other caller is the LOCAL branch (`regenerate-handlers.ts:139`), which records no spend by design.
- **Possible fix:** require `meter` whenever `caps` is present (a discriminated `opts` type), or leave it and mention it in the docstring. Not blocking.

## Earlier mandates, re-checked against the redesign

- **a/c:** every path records once. The response waits at most `CORRECTION_RPC_TIMEOUT_MS` per RPC, and a failure is `console.error`'d with owner, video and cents. That log line is the only observation, as the backlog states.
- **d:** a 0¢ or all-bound press passes 0026's `p_cents` checks (probe above). Failed presses spend daily slots, which is the stated intent.
- **e:** `STRUCTURAL_REFUSALS` is a `Record<StructuralFailureReason, …>`, so it is exhaustive by type. The status is 422, a sibling of the 413. The panel renders `data.error`.
- **j:** another owner's allowance cannot be read or spent, because both RPCs take the owner from `auth.uid()` (probe above).
- **k:** the ceiling test reads 0026's declared default from the real migration files and refuses any other migration that mentions the column.
- **l:** a caller abort on the last attempt and one between attempts are both covered: the real-SDK last-attempt case, and the mocked backoff case.
- **g:** backlog #62's closure text matches what shipped, including its "what remains" list and the deploy-order warning. The F1 wording issue is in the docstring and dashboard, not in the backlog row.

Neither finding is Blocking, High or Medium. The redesign closes the class that rounds 1 to 3 kept finding instance by instance.

VERDICT: CONVERGED
