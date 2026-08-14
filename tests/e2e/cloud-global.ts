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
 *   · REQUESTS STILL IN FLIGHT WHEN THE READ HAPPENS. Teardowns run last-registered-first, so this
 *     guard runs BEFORE the webServer plugin's — the Next dev server is alive during the final
 *     read. Playwright aborts a closed context's requests; Node does not abort a handler already
 *     executing. A handler that reaches `reserve_serve_model` after the compare is money the guard
 *     did not see. Now that rung 4 is live again this is reachable in principle, though every
 *     request the rungs make is awaited.
 *   · UI MODE, `--watch`, AND THE VS CODE EXTENSION — see the next section; this file does not run
 *     per run there, only per session.
 * The global timeout is the one to remember: a non-zero exit is not the same as a guard that fired.
 * And when the test phase has ALREADY failed, `TaskRunner.run` returns
 * `status === "passed" ? teardownStatus : status`, so a money verdict does not reach the exit code
 * — it survives only as a reporter error line. Non-zero either way, but "it moved money" and "a
 * rung timed out" become the same exit status.
 *
 * ─────────────────────────────────────────────────────────────────────────────────────────────
 * WHY THIS DELETES THE FIXTURE FILES (round-2 High, 2026-08-13)
 *
 * AUTH_FILE and FIXTURE_FILE deliberately live outside `outputDir` so Playwright's own wipe cannot
 * take them — and that is precisely what made them dangerous. They carried no run id, no timestamp
 * and no database identity, so `--project=cloud --no-deps`, an interrupted setup, or a cloud-only
 * invocation would happily compare a live database against a previous run's seed.
 *
 * The fix is identity by construction rather than identity by stamp: ON THE CLI RUNNER, globalSetup
 * runs once per invocation — including partial ones like `--project=cloud --no-deps` — so deleting
 * both files here means a fixture can only exist if THIS run's setup project wrote it. There is no
 * id to check because there is nothing stale to check it against.
 *
 * ⚠ THE CLI RUNNER IS THE WHOLE SCOPE OF THAT SENTENCE, and an earlier draft said "every
 * invocation", which is false on the test-server path — UI mode, `--watch`, the VS Code extension.
 * There, `TestRunner.runGlobalSetup` runs ONCE per session and stashes its cleanup for
 * `runGlobalTeardown` (runner/index.js), while `runTests` builds
 * `[applyRebaselines, load, …createRunTestsTasks]` with NO global setup task — so nothing is deleted
 * between runs. Worse, the server hard-codes `doNotRunDepsOutsideProjectFilter: true`, so clicking a
 * single cloud test does not re-run the `setup` project either. The fixture then survives every
 * click while the database moves underneath it: precisely the hazard this deletion replaced a run-id
 * stamp to prevent. The money half degrades the same way — one baseline at session start, one check
 * at session close, and a session that is killed rather than closed never checks at all.
 *
 * SO: RUN THIS SUITE FROM THE CLI (`npm run test:e2e:cloud`). UI and watch mode are not supported by
 * the guard, and narrowing the sentence is the honest fix rather than pretending otherwise —
 * restoring a stamp would detect the staleness without preventing it, and the CLI path is the one
 * CI and the roadmap actually depend on.
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
      'THE SPEND LEDGER MOVED DURING THIS RUN. The suite is supposed to be free: every fixture is\n' +
      'seeded straight into the local database, and the one call that would enqueue paid work is\n' +
      'intercepted.\n' +
      `  ledger_audit max(id)   ${baseline.auditMaxId} -> ${now.auditMaxId}\n` +
      `  spend_ledger cents     ${baseline.centsTotal} -> ${now.centsTotal}\n` +
      'TWO EXPLANATIONS, AND THIS GUARD CANNOT TELL THEM APART — both witnesses are global, not\n' +
      'scoped to the owner this run created:\n' +
      '  1. THE SUITE SPENT. Usually a serve path finding no fresh magazine model and regenerating\n' +
      '     it — check that cloud.setup.ts seeds `sourceSections` as the PARSED titles (no leading\n' +
      '     ordinal: "Encoder", not "2. Encoder").\n' +
      '  2. SOMETHING ELSE ON THIS STACK SPENT — a browser tab left open on localhost:3001, another\n' +
      '     suite, a worker. The stability loop only rules out a writer during the read itself,\n' +
      '     which is milliseconds; this window is the whole run.\n' +
      'A new ledger_audit row means a serve settled or a release underflowed; a cents change with no\n' +
      'audit row means a reservation is still open.',
    );
  };
}

/** FAIL CLOSED ON A NON-LOCAL STACK. `adminClient()` uses whatever `NEXT_PUBLIC_SUPABASE_URL` is in
 *  the environment with the service-role key, and tests/integration/setup.ts only checks the vars
 *  are non-empty. `/dev-login` refuses to work against anything but a local URL
 *  (lib/supabase/dev-login.ts) — this guard, which DELETES files and reads a ledger with a service
 *  key, had no equivalent gate. A stray `.env.test.local` was one edit away from pointing the whole
 *  suite at a hosted project. */
function assertLocalStack() {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL ?? '';
  const host = (() => { try { return new URL(url).hostname; } catch { return ''; } })();
  if (host === '127.0.0.1' || host === 'localhost' || host === '[::1]') return;
  throw new Error(
    `The cloud e2e suite refuses to run against a non-local Supabase: ${url || '(unset)'}\n` +
    'It seeds users, deletes fixture files and reads the spend ledger with the service-role key.\n' +
    'Start the local stack (`npx supabase start`) and let tests/integration/setup.ts supply the env.',
  );
}

export default async function cloudGlobalSetup() {
  assertLocalStack();
  for (const stale of [AUTH_FILE, FIXTURE_FILE]) fs.rmSync(stale, { force: true });

  // ONE STATEMENT, deliberately. A throw after the baseline read but before the return would leave
  // `globalSetupResult` a non-function, and the runner only invokes it `if (typeof … ===
  // "function")` — the guard would be silently absent with a baseline already taken. Round 3 asked
  // for a comment forbidding an insertion there; round 4 pointed out that a comment is not a
  // mechanism. There is now no statement gap to insert into.
  return moneyGuard(await readLedger());
}
