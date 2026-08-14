/**
 * The money guard for the whole cloud e2e RUN — and the reason the fixture cannot go stale.
 *
 * Both jobs belong here, at the run level, for the same reason: everything narrower has a window it
 * cannot see.
 *
 * ─────────────────────────────────────────────────────────────────────────────────────────────
 * WHY NOT A HOOK INSIDE THE SPEC (round-2 Blocking, 2026-08-13)
 *
 * The guard was a `test.afterAll` in cloud-journey.spec.ts, which already survives a failing rung —
 * that was round 1's fix and it was right as far as it went. But the spec belongs to the `cloud`
 * project, and `cloud` declares `dependencies: ['setup']`. Playwright does not run a project whose
 * dependency failed. So if the SETUP project moved money and then failed or timed out, the guard
 * was silently absent — in exactly the window that round 1 had moved the baseline to cover.
 * A guard that disappears when something goes wrong is absent when it is most needed, which is the
 * same defect this suite keeps rediscovering in different clothes.
 *
 * `globalSetup` sits outside every project. Returning a function from it registers that function as
 * the run's teardown (verified in playwright 1.60.0, runner/index.js `createGlobalSetupTask`: the
 * teardown task is queued the moment the setup task STARTS, and the teardown runner sets
 * `_isTearDown`, so a failing test phase cannot skip it and a throw in here still fails the run).
 * That covers: the setup project failing, the cloud project never being scheduled, `--max-failures`,
 * `-x`, and SIGINT.
 *
 * WHERE IT STILL MAKES NO CLAIM — round 3 caught this list being one item too generous, which is
 * the same "asserted in a comment, not by code" failure the rest of this file is about:
 *   · SIGKILL or a hard process crash. Nothing in-process can cover it.
 *   · A GLOBAL TIMEOUT. `TaskRunner.run` passes the SAME `deadline` to the cleanup pass
 *     (runner/index.js `runDeferCleanup`), and `TimeoutWatcher` resolves immediately when the
 *     deadline has already gone by — so a run that times out races its own teardown and the ledger
 *     read may never finish. The run still exits non-zero, but for the timeout, not for the money.
 *   · A webServer that never starts. Plugin setup is ordered BEFORE user global setup in
 *     `createGlobalSetupTasks`, so if `next dev` fails to come up this file does not run at all —
 *     no baseline, and no fixture deletion either. (An existing server satisfying the probe under
 *     `reuseExistingServer` is a plugin SUCCESS, so that path is covered normally.)
 *   · Anything a `globalTeardown` FILE does. `createGlobalSetupTasks` lists globalTeardowns before
 *     globalSetups and teardown tasks are `unshift`ed, so the order is: this guard, then the
 *     globalTeardown file. Money moved there is after the final read. This config has no
 *     globalTeardown; if one is ever added, the guard has to move after it.
 * The global timeout is the one to remember: a non-zero exit is not the same as a guard that fired.
 *
 * ─────────────────────────────────────────────────────────────────────────────────────────────
 * WHY THIS DELETES THE FIXTURE FILES (round-2 High, 2026-08-13)
 *
 * AUTH_FILE and FIXTURE_FILE deliberately live outside `outputDir` so Playwright's own wipe cannot
 * take them — and that is precisely what made them dangerous. They carried no run id, no timestamp
 * and no database identity, so `--project=cloud --no-deps`, an interrupted setup, or a cloud-only
 * invocation would happily compare a live database against a previous run's seed.
 *
 * The fix is identity by construction rather than identity by stamp: `globalSetup` runs on every
 * invocation that gets as far as running tests — including partial ones — so deleting both files
 * here means a fixture can only exist if THIS run's setup project wrote it. There is no id to check
 * because there is nothing stale to check it against. (The one gap is a webServer that never
 * starts, above; then nothing is deleted, but nothing runs either.)
 *
 * WHAT A PARTIAL RUN LOOKS LIKE, so nobody has to rediscover it. `--project=cloud --no-deps` now
 * fails on the FIRST rung with Playwright's own
 *     Error reading storage state from playwright/.auth/cloud-user.json
 * rather than readFixture()'s friendlier message, because a project's `storageState` is loaded when
 * the browser context is created, before any test body runs. That is the intended outcome — loud,
 * naming the exact file — but the cause is this deletion, not a broken checkout. Run the whole
 * config: `npm run test:e2e:cloud`.
 *
 * Detecting the partial run here instead was TRIED AND DOES NOT WORK: `FullConfig.projects` is the
 * declared list, not the selected one — measured 2026-08-13, it reports ["setup","cloud"] under
 * `--project=cloud --no-deps` exactly as it does for a full run. A check built on it could never
 * fire, which is indistinguishable from a check that does nothing.
 */
// Side-effect import: loads .env.test.local and THROWS with the exact command to run when the local
// stack is absent. Must come before anything that builds a Supabase client.
import '../integration/setup';
import fs from 'node:fs';
import { AUTH_FILE, FIXTURE_FILE, readLedger, type LedgerSnapshot } from './cloud-fixture';

/** The run teardown, as a pure function of the baseline — see the single `return` below for why
 *  this is a named helper rather than an inline closure. */
function moneyGuard(baseline: LedgerSnapshot) {
  return async () => {
    const now = await readLedger();
    if (now.auditMaxId === baseline.auditMaxId && now.centsTotal === baseline.centsTotal) return;
    throw new Error(
      'THE CLOUD E2E SUITE MOVED MONEY. It is supposed to be free: every fixture is seeded straight\n' +
      'into the local database, and the one call that would enqueue paid work is intercepted.\n' +
      `  ledger_audit max(id)   ${baseline.auditMaxId} -> ${now.auditMaxId}\n` +
      `  spend_ledger cents     ${baseline.centsTotal} -> ${now.centsTotal}\n` +
      'A new ledger_audit row means a serve settled or a release underflowed. A cents change with no\n' +
      'audit row means a reservation is still open. Either way something reached Gemini — the usual\n' +
      'cause is a serve path finding no pre-seeded magazine model and regenerating it.',
    );
  };
}

export default async function cloudGlobalSetup() {
  for (const stale of [AUTH_FILE, FIXTURE_FILE]) fs.rmSync(stale, { force: true });

  // ONE STATEMENT, deliberately. A throw after the baseline read but before the return would leave
  // `globalSetupResult` a non-function, and the runner only invokes it `if (typeof … ===
  // "function")` — the guard would be silently absent with a baseline already taken. Round 3 asked
  // for a comment forbidding an insertion there; round 4 pointed out that a comment is not a
  // mechanism. There is now no statement gap to insert into.
  return moneyGuard(await readLedger());
}
