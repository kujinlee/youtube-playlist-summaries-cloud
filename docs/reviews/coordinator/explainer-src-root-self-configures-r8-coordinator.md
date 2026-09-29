# Round 8 — `explainer-src-root-self-configures` (PR #295) — coordinator

```yaml
round: 8
fixes_nontrivial: false
subject: explainer-src-root-self-configures
halves:
  codex: ran
  claude: ran
findings:
  - {id: H1, severity: High, aim: instrument, fix_induced: true, component: readiness-case, disposition: filed}
  - {id: M1, severity: Medium, aim: deliverable, fix_induced: true, component: start-restart, disposition: filed}
  - {id: M2, severity: Medium, aim: deliverable, fix_induced: false, component: respawn-logging, disposition: filed}
  - {id: L1, severity: Low, aim: instrument, fix_induced: true, component: readiness-case, disposition: filed}
```

## ⛔ THE PRE-COMMITTED CONDITION TRIGGERED, AND THIS BRANCH STOPS HERE

Round 7's document said, **before this round ran**: *if round 8 finds another fix-induced defect in
`start-restart`, this branch splits.* Round 8's Claude half found one — **M1, fix-induced, in the
runtime** — and reported it with the observation that applying the rule to a Medium was the
coordinator's call, not its own.

**It applies.** The commitment said *another fix-induced defect*, not *another fix-induced High*.
Narrowing it now to exclude a Medium is widening a framing to fit the result, which is the failure
this repository has a memory entry about: **move the member, never loosen the sentence.**

### What "splits" means here, and what it does not

⚠ **It does NOT mean performing the surgery now.** `explainer-serve.py` carries 938 changed lines and
`page_chrome.py` 300; the two features are entangled across eight rounds of history. Doing that
reconstruction at the end of a very long session — in which *every one of the last four fixes
introduced the next defect* — is how the ninth defect gets written. The commitment's purpose was to
**stop patching**, and it is honoured by stopping.

**So: no further fixes land on this branch, and it is not merged.** The separation is the next
session's first task, with fresh context and the plan below.

## The evidence that the decision is right on its merits, not only by rule

| | |
|---|---|
| `/src/` — the bug this branch exists to fix | **no finding since round 4** |
| the restart button — a separate feature that arrived in the same branch | r6 High, r7 High ×2, r8 High, r8 Medium |
| every one of those fixes | introduced the next defect |

⭐ **And the deepest reason is not any single defect — it is that the verification cannot be
trusted.** There is no `scripts/mutations/explainer-serve.json`, so **none of that file's 140 cases
has ever been shown load-bearing.** H1 is that fact made visible: the case written in round 7 to
guard the r7 High is **green on a live reproduction of the r7 High**, and 2 of 3 mutations against it
survived. Backlog **#122**, filed this morning, is exactly this and was deferred as *"a slice, not a
side-effect of a bug fix."* That judgement was right and this is its bill.

## H1 — the readiness case is green on the corpse → **FILED**

`_post_ready_statements()` slices `body[k+1:]` where `k` indexes the *statement containing* the `K`
write — but the write lives **inside a `try`**, so anything added after it *within that try* is
invisible to the check. Confirmed by the coordinator: inserting
`httpd.timeout = float(os.environ["EXPLAINER_TIMEOUT"])` (a `KeyError`, not an `OSError`) after the
write produced `rc=0`, `serving … (pid 50580)`, a pidfile naming a **dead** pid and **nothing
listening** — the r7 corpse verbatim — while the readiness case stayed **green**.

⚠ **Codex found two bypasses at the top level and the fix closed exactly those two instances, not the
class one indent in.** That is the shape this branch keeps producing, now in the guard for the guard.

## M1 — a refused second press reports `restart FAILED` about a restart that is succeeding → **FILED**

Round 6 added the `409`; the page's client funnels every non-2xx into
`rfail('restart FAILED: ' + e.message + …)`. Measured live: three concurrent presses → 200/409/409,
the restart **succeeded**, and the second tab was told `restart FAILED: {"ok": false, …}` — raw JSON,
a wrong verdict, and it directs the reader to run a manual restart *mid-replacement*. Reachable only
from a second page, which is exactly the scenario the 409 exists for.

**Fix-induced, in the runtime.** This is the trigger.

## M2 — the failure the pipe exists to detect is logged nowhere → **FILED**

`respawn()` promises *"a trace somewhere a person can look"* but writes `RESTART_LOG` in one of four
branches. Measured with `.serve.log` a directory, spawned detached: not listening, **no pidfile, no
`.restart.log`, no readable `.serve.log`** — total silence, with round 7's good diagnosis going to
`/dev/null`. ⚠ **Not fix wreckage:** provenance checked — `respawn`, `RESTART_LOG` and that docstring
all arrive in the original feature commit. A seven-round blind spot.

## The plan the next session inherits

1. **Ship the `/src/` fix** — `SrcRoot`, `src_root`, `src_root_help`, `_gone_checkout_help`, the
   `[FAIL]` report-format repair, and their cases. Converged since round 4.
2. **Park the restart button** behind backlog **#122**: seed `scripts/mutations/explainer-serve.json`
   first, so its cases can be shown load-bearing, then re-review the feature against a ratchet that
   works. H1 is the argument that reviewing it without one is guesswork.
3. M1, M2 and L1 are filed and travel with the parked feature.

## Q4 / Q5

Convergence: **not reached** — a High and two Mediums. Thrashing: **armed and acted on**, by stopping
rather than by a ninth fix.
