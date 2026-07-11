# Claude Adversarial Re-Review — Stage 2b Plan v2 (Round 2)

**Reviewer:** Claude (independent subagent, full source). **Artifact:** plan v2 (`7040d8d`). **Date:** 2026-07-11.
**Verdict:** **1 Blocking + 1 High + 1 Medium + 2 Low — not converged.** All surviving defects are in Task 7 test fixtures + wiring; the component *logic* is genuinely solid (Round-1 fixes confirmed).

## New findings

1. **[BLOCKING] Task 7 poll tests can't go green — `status()` returns `jobs:[]` while the banner recomputes rollup from jobs.** The poll path reads `.jobs` (always `[]`) → `rollup([]).terminal` always false → "resolves to complete" and "mixed" tests time out. This is Round-1 Codex#10/Claude-M4, which the v2 Self-Review **falsely marked ✅**. *Fix:* `jobsFrom(rollup)` helper building rows from bucket counts. **(v3: fixed)**

2. **[HIGH] "N of M" test asserts a transient render React batching eliminates.** Probe→`progress` then poll→`done` settle in one microtask flush (no timer suspension), so React coalesces to `done`; `findByText(/Ingesting 0 of 2/)` never matches. *Fix:* observable non-terminal poll step under fake timers, or drop the transient assertion and test only stable state. **(v3: split into a fake-timer progress test + real-timer done/mixed tests)**

3. **[MEDIUM] Task 1 "aborts via signal" test hangs at RED** — `now:()=>0` + noop `sleep` never yields a macrotask, so against current (no-signal) code the loop spins and Jest's timeout timer can't fire → permanent hang during the RED step. *Fix:* incrementing `now` + finite `timeoutMs` backstop. **(v3: fixed)**

4. **[LOW] Task 9 wiring omits `useRouter()` in `CloudAppBody`.** `onIngestSuccess` calls `router.push` but `CloudAppBody` has no router. *Fix:* add `const router = useRouter()`. **(v3: fixed)**

5. **[LOW] Task 7 probe 401 → `/login` not `cancelled`-guarded.** A 401 resolving after unmount still navigates. *Fix:* `if (!cancelled) router.replace('/login')`. **(v3: fixed)**

## Round-1 fixes confirmed genuine

Tokens (all exist in `app/globals.css`, no dead names, Verification audits); broken FSM removed (no `live`, no `state` read in closure); cancellation (`AbortSignal` + `{aborted}`; unmount "no further fetch" assertion passes — first fetch fires synchronously before unmount, abort returns on post-fetch check); empty-poll-forever fixed; 401 both paths; give-up only-when-live; refetch dedup (active→failed advances count); focus trap consistent (`:not([disabled])` == test query while not submitting); integration store-layer + helpers exist + `enqueue_job` 8-arg + `status='completed'`→terminal (uses real rows, unaffected by #1); `import type` erased (no server code in browser bundle); `{aborted}`/`fatal?` additive.
