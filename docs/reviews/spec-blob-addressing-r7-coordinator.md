# Round 7 — coordinator adjudication

**Verdict: NOT CONVERGED.** Both reviewers independently, and my own cross-derivation agrees.

| Reviewer | Findings | Could execute? |
|---|---|---|
| Codex (`gpt-5.5`) | 1 Blocking, 1 High | **No** — `dial unix docker.sock: operation not permitted`; reported `0/35 … SQL did not run`. Findings are reasoned, not measured |
| Claude | 2 Blocking, 3 High, 5 Medium, 1 Low | Yes — every finding measured, verbatim error text |
| Coordinator (this doc) | 2 confirmed, 3 claims audited clean | Yes |

**Both reviewers independently checked and CONFIRMED my two headline claims** — 89/89 assertions pass,
35/35 mutations behave as expected. That is worth stating plainly: *the instruments were honest and the
defects are still there.* Round 7's findings are, without exception, things neither instrument can see.

---

## Adjudication — I re-ran both Blockings myself rather than accepting them

Per `dev-process.md` ("reviewer disagreement is the signal… adjudicate by reading the code"), and
because two findings contradict comments **I wrote**, each was reproduced independently before being
accepted.

### B1 — CONFIRMED. `record_artifact`'s append path collides with its own pending row.

```
B1a REPRODUCED [23505] duplicate key value violates unique constraint "video_artifacts_paid_uq"
```

Reproduced with **no race, no reclaim, and a live lease** — a single worker that restarted and no
longer knows its `lease_token`. The token mismatch sends the flip down the append path, which inserts
blind; `video_artifacts_paid_uq` has no state predicate, so it collides with the worker's *own*
`pending` row.

**This silently revokes a user decision.** On 2026-08-07 the `lease_token` veto was declined because
*"rejecting W1 does not prevent the double charge — it throws away one of the two things we paid for"*,
and the rule recorded was **the reservation guards SPENDING, not RECORDING; a writer that already paid
always records.** The design still says `record_artifact` *"never refuses"*
(`…-design.md:2151`). Measured, it throws the paid work away anyway — just via a raw `23505` instead of
a typed refusal. Shape #8 (a policy that errors rather than denies), and the sibling of a fix
`reserve_artifact_slot:304-306` already applies to itself. **Shape #10, instance seven.**

Codex reached the same defect from a different direction (a `busy` loser leaving a completable
generation). My own cross-derivation reached a third face of it — measured, a writer completed
*another writer's* generation and the real owner was then locked out of its own paid work:

```
XD-B  B completed ANOTHER WRITER'S generation gA -> recorded_after_loss, state=complete
XD-C  A COULD NOT RECORD ITS OWN PAID WORK -> [P0001] the CONTENT of complete generation gA is immutable
```

Three independent routes to one root cause: **`record_artifact` fences the artifact on the token and
the generation on nothing.**

### B2 — CONFIRMED, and it refutes a comment I wrote. Item 1 × item 3.

```
B2-A REPRODUCED [P0001] detached_at 2026-08-08… precedes generation gFUT produced_at 2026-08-18…
```

A generation carrying a **future** `produced_at` can never have its digs detached — permanently, since
`produced_at` is frozen by `video_generations_freeze` and `detached_at` is trigger-owned on UPDATE.
Not exotic: `record_artifact` takes `p_produced_at` from the caller *precisely so sync can carry a
remote clock's value*, and the spec's own fixture `gC_STALE` carries `2026-09-09`, a month ahead.

**The second half is the part I got wrong.** `04_artifacts.sql:727-730` claims the trigger firing order
is *"required rather than incidental: on UPDATE the append-only trigger OWNS `detached_at`, so the
bounds above must read the value it settled."* Literally true, and the consequence is the **opposite**
of what the comment implies:

```
B2-H writer asked for 2020-01-01 on UPDATE; stored value = 2026-08-08 01:07:47
     (the bound saw trigger output, not writer input)
```

Because `append_only` overwrites `detached_at` first, **the bound can never fire on writer input on the
UPDATE path.** It is not useless — the gap it was added to close is the INSERT path, where no
append-only trigger fires, and the `G13` assertions exercise exactly that. But the comment sells the
ordering as *making the guard work* when what it actually does is *make the guard inert on UPDATE*.
A correct sentence and a misleading one, in the same paragraph, about my own fix.

---

## Claims I audited that held

| Claim | Verdict |
|---|---|
| Trigger name-order on `video_artifacts` is `append_only` → `generation_complete` | **TRUE** (`pg_trigger`) |
| Trigger name-order on `video_generations` is `forbid_collecting_current` → `freeze` | **TRUE** |
| `produced_at` cannot be NULL when the `detached_at` bounds run (3-valued-logic hazard) | **TRUE** — the completeness check raises first; measured `[P0001] … generation gY is pending` |
| A `COMPLETE` generation is never left with no recorded artifact | **TRUE** — 0 rows |

---

## The pattern this round confirms

Round 6's cross-derivation verdict was that the fixes *"fail as a set — every Blocking is an
interaction between two fixes, not a defect in either one."* **Round 7 reproduced that exactly**: every
Blocking and High is an interaction between two of the four merged items, and none is a defect in any
one of them. Four items, four sittings, no re-derivation between them — the same condition, the same
outcome.

The one genuinely new shape, added to the standing list this round and immediately instantiated twice:

> **#11 — AN INSTRUMENT THAT MISREPORTS ITS OWN RESULT.** Round 5's `when others` (failure → pass);
> round 7's missing trigger verdict (catch → miss); and now `RED(trigger)` accepting *any* matching
> prefix without checking it is the expected guard — found by Codex, in the fix I wrote for the
> previous instance, hours earlier.

**Round 8 is mandatory** — `dev-process.md`: a round that surfaces new Blocking/High is proof the loop
is still earning its cost.
