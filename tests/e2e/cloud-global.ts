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
 * `-x`, a global timeout, and SIGINT.
 *
 * It does NOT cover SIGKILL or a hard process crash — nothing in-process can. Say so rather than
 * letting "runs regardless" quietly mean "almost regardless".
 *
 * ─────────────────────────────────────────────────────────────────────────────────────────────
 * WHY THIS DELETES THE FIXTURE FILES (round-2 High, 2026-08-13)
 *
 * AUTH_FILE and FIXTURE_FILE deliberately live outside `outputDir` so Playwright's own wipe cannot
 * take them — and that is precisely what made them dangerous. They carried no run id, no timestamp
 * and no database identity, so `--project=cloud --no-deps`, an interrupted setup, or a cloud-only
 * invocation would happily compare a live database against a previous run's seed.
 *
 * The fix is identity by construction rather than identity by stamp: `globalSetup` runs on EVERY
 * invocation, including partial ones, so deleting both files here means a fixture can only exist if
 * THIS run's setup project wrote it. There is no id to check because there is nothing stale to
 * check it against. A missing fixture then produces readFixture()'s loud "run the whole config"
 * error instead of a plausible pass against week-old rows.
 */
// Side-effect import: loads .env.test.local and THROWS with the exact command to run when the local
// stack is absent. Must come before anything that builds a Supabase client.
import '../integration/setup';
import fs from 'node:fs';
import { AUTH_FILE, FIXTURE_FILE, readLedger } from './cloud-fixture';

export default async function cloudGlobalSetup() {
  for (const stale of [AUTH_FILE, FIXTURE_FILE]) fs.rmSync(stale, { force: true });

  const baseline = await readLedger();

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
