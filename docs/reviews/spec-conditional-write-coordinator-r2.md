# Coordinator finding — round 2, before the reviewers reported

**Date:** 2026-08-04
**Target:** spec v2 (`3dca7b0`), §6 recovery loop
**Found by:** tracing the slug-race recovery path by hand while round 2 was dispatched.
Recorded separately so the convergence trail distinguishes coordinator findings from reviewer ones.

---

## C1 (Blocking) — the re-address recomputes the slug from the payload, re-orphaning the digs it just saved

**The guard works. The recovery undoes it.**

v2 §6 recomputes the destination on each attempt as:

```
baseName := pad(serial) + '_' + slug(title)
```

`title` is `payload.title` — frozen in the job payload at enqueue time (`summary-handler.ts:96`). That
is correct for the **serial** race and wrong for the **slug** race, which is the race the second
conjunct was added to catch.

### The interleaving, with values

| Step | Actor | State |
|---|---|---|
| 1 | worker | reads row at `:84` → `serialNumber 7`, `summaryMd '007_alpha.md'`; captures both as expected |
| 2 | worker | Gemini — minutes. `payload.title` is still **"alpha"** |
| 3 | sync | local title changed → A3 relocates slug-only: row becomes `summaryMd '007_beta.md'`, **serial still 7**; paid digs copied to `dig/007_beta/`, `dig/007_alpha/*` deleted |
| 4 | worker | persists with expected `(7, '007_alpha.md')` → row holds `'007_beta.md'` → **guard REJECTS** ✅ *the conjunct does its job* |
| 5 | worker | re-address: observed address is `(7, '007_beta.md')`. But §6 recomputes `baseName = pad(7) + '_' + slug("alpha")` = **`007_alpha`** |
| 6 | worker | passes expected `(7, '007_beta.md')` → **guard PASSES** → writes `summaryMd = '007_alpha.md'` |
| 7 | — | row = `summaryMd '007_alpha.md'`, digs at `dig/007_beta/` → **orphaned, exactly as if the guard had never existed** |

The guard fires correctly at step 4 and the recovery walks the damage back in at step 6. Worse than a
missing guard, because the rejection at step 4 makes it look like the mechanism worked.

### Root cause

§6 treats the address as something to **re-derive** when it is something to **adopt**. After a
rejection the row already holds the authoritative address; recomputing it from the worker's own stale
inputs discards exactly the information the rejection just delivered.

This is the same root-cause shape as round 1's B2 (the payload not being rebuilt) one level deeper:
*v2 fixed which fields are recomputed and left wrong how one of them is computed.*

### Fix

On a re-address, take the base from the **observed address**, not from the payload:

```
if observedSummaryMd is not null:
    baseName := baseOf(observedSummaryMd)        # adopt: '007_beta' or '003_alpha'
else:
    baseName := pad(serial) + '_' + slug(title)  # first summary only (G2: bare row has no key)
```

Correct in all three cases:

| Case | observed | adopted base | right? |
|---|---|---|---|
| serial race | `003_alpha.md` | `003_alpha` | ✅ |
| slug race | `007_beta.md` | `007_beta` | ✅ |
| first summary | *absent* | `pad(serial)_slug(title)` | ✅ — nothing to adopt |

`baseOf` already exists (`lib/cloud-sync/reconcile-serial.ts:84-86`), though it is module-private there.

### Test this demands

§8's slug-race test must assert the **post-recovery** row, not merely that the first persist was
rejected. Concretely: after the loop completes, `data->>'summaryMd'` **equals `007_beta.md`** and the
dig blobs under `dig/007_beta/` are reachable. A test asserting only "the RPC raised" passes against
the broken recovery — the round-1 B2 lesson, recurring in the very section written to fix it.

---

## Note on what this says about the round

Two rounds have now each produced a Blocking in the *recovery* path rather than the predicate. The
predicate has been correct since v1. Worth carrying into round 3 as a standing shape:
**the guard is easy; what the caller does with a rejection is where this slice keeps breaking.**
