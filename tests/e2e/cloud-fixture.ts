/**
 * The seeded-fixture contract shared by the cloud setup (writer) and the journey spec (reader).
 *
 * A PLAIN MODULE, not a test file: Playwright refuses to let one test file import another
 * ("should not import test file", measured 2026-08-13), and it is right to — a spec importing a
 * setup would run that setup's own `test()` registrations twice.
 *
 * The values are written to disk rather than recomputed, so the spec asserts against what was
 * actually seeded. A spec that re-derives its expectations can agree with itself while both it and
 * the database are wrong.
 */
import fs from 'node:fs';
import { adminClient } from '../integration/helpers/clients';

/** NOT under test-results/: Playwright wipes outputDir at the start of every run. */
export const AUTH_FILE = 'playwright/.auth/cloud-user.json';
export const FIXTURE_FILE = 'playwright/.auth/cloud-fixture.json';

export type CloudFixture = {
  email: string;
  /** The money witnesses read BEFORE the setup did anything — see cloud.setup.ts. The cloud
   *  project's own `beforeAll` runs only after the setup project has finished, so a baseline taken
   *  there silently excludes everything the setup did (review Blocking, 2026-08-13). */
  ledgerBaseline: { auditMaxId: number; centsTotal: number };
  ownerId: string;
  listed: { playlistId: string; playlistKey: string; title: string; videoId: string };
};

/** Read the money witnesses. `ledger_audit.id` is a sequence, so max(id) only ever GROWS — it cannot
 *  be cancelled out by a release the way a sum over spend_ledger can (review Blocking, 2026-08-13:
 *  a reserve followed by a refund nets to zero and a sum-based assertion passes while the money path
 *  was very much reached). The cents total is kept as a secondary, weaker signal. */
export async function readLedger(svc = adminClient()) {
  const [{ data: audit }, { data: ledger }] = await Promise.all([
    svc.from('ledger_audit').select('id').order('id', { ascending: false }).limit(1),
    svc.from('spend_ledger').select('reserved_cents, actual_cents'),
  ]);
  return {
    auditMaxId: Number(audit?.[0]?.id ?? 0),
    centsTotal: (ledger ?? []).reduce(
      (n, r) => n + Number(r.reserved_cents ?? 0) + Number(r.actual_cents ?? 0), 0),
  };
}

export function readFixture(): CloudFixture {
  if (!fs.existsSync(FIXTURE_FILE)) {
    // CANNOT RUN IS A FAILURE. A bare ENOENT here reads as a missing file; it is almost always
    // "the setup project did not run", which is a different problem with a different fix.
    throw new Error(
      `No cloud fixture at ${FIXTURE_FILE}. The setup project writes it.\n` +
      'Run the whole config, not one spec: npm run test:e2e:cloud',
    );
  }
  return JSON.parse(fs.readFileSync(FIXTURE_FILE, 'utf8')) as CloudFixture;
}
