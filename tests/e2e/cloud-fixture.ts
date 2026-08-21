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

/** NOT under test-results/: Playwright wipes outputDir at the start of every run — but see
 *  cloud-global.ts, which deletes BOTH of these itself at the start of every run. Surviving the run
 *  was the whole hazard: a file with no run identity, compared against a live database. */
export const AUTH_FILE = 'playwright/.auth/cloud-user.json';
export const FIXTURE_FILE = 'playwright/.auth/cloud-fixture.json';

export type CloudFixture = {
  email: string;
  /** The owner's `/dev-login` password, so a spec that must END signed out can mint its OWN session
   *  instead of destroying the shared one — see the sign-out rung in cloud-journey.spec.ts. Written
   *  to `playwright/.auth/`, which is gitignored and already holds a live session token, so this is
   *  not a new exposure class. Local stack only: `/dev-login` fails closed against any non-local
   *  Supabase URL (lib/supabase/dev-login.ts). */
  password: string;
  ownerId: string;
  /** `title` is the PLAYLIST's title (the sidebar link); `videoTitle` is the seeded video's row
   *  label in the library pane. Both are written here rather than re-typed in a spec, per this
   *  file's own rule — a spec carrying its own copy of a seeded string agrees with itself even
   *  when the seed has moved. */
  listed: {
    playlistId: string; playlistKey: string; title: string; videoId: string; videoTitle: string;
  };
};

export type LedgerSnapshot = { auditMaxId: number; centsTotal: number };

/** ONE round trip's worth of the two money witnesses. Not a snapshot — see readLedger. */
async function readOnce(svc: ReturnType<typeof adminClient>): Promise<LedgerSnapshot> {
  const [audit, ledger] = await Promise.all([
    svc.from('ledger_audit').select('id').order('id', { ascending: false }).limit(1),
    svc.from('spend_ledger').select('reserved_cents, actual_cents'),
  ]);
  // CANNOT RUN IS A FAILURE, and this one fails OPEN if you let it. The earlier version destructured
  // `data` and ignored `error`: a failed query yields data=null, which reduces to auditMaxId=0 and
  // centsTotal=0 — for the baseline AND for the final read. Two unread ledgers compare equal, so the
  // guard would report "no money moved" precisely when it had read nothing at all. Found by hand
  // while acting on the round-2 review, which did not raise it.
  if (audit.error) throw new Error(`ledger_audit unreadable: ${audit.error.message}`);
  if (ledger.error) throw new Error(`spend_ledger unreadable: ${ledger.error.message}`);
  return {
    auditMaxId: Number(audit.data?.[0]?.id ?? 0),
    centsTotal: (ledger.data ?? []).reduce(
      (n, r) => n + Number(r.reserved_cents ?? 0) + Number(r.actual_cents ?? 0), 0),
  };
}

/**
 * Read the money witnesses as a state that ACTUALLY EXISTED at some instant.
 *
 * `ledger_audit.id` is a sequence, so max(id) only ever GROWS — it cannot be cancelled out by a
 * release the way a sum over spend_ledger can (round-1 Blocking: a reserve followed by a refund nets
 * to zero and a sum-based assertion passes while the money path was very much reached). The cents
 * total is kept as a secondary, weaker signal.
 *
 * The two witnesses live in different tables and PostgREST has no cross-table snapshot, so a single
 * pass can straddle a concurrent write and describe a state that never existed (round-2 Medium).
 * Concretely: a stray settle lands between the two queries, the BASELINE records the new cents with
 * the old audit id, and the final read then disagrees on the audit id alone — a failure with no
 * money moved during the run. So read the pair repeatedly until two consecutive passes agree; that
 * is a real instant, because nothing changed across it.
 *
 * If it never settles, something is writing to the ledger throughout and this guard cannot make its
 * claim. That is a failure, not a shrug — a money guard that cannot read is worth less than none.
 */
export async function readLedger(svc = adminClient()): Promise<LedgerSnapshot> {
  let prev = await readOnce(svc);
  for (let attempt = 0; attempt < 4; attempt++) {
    const next = await readOnce(svc);
    if (next.auditMaxId === prev.auditMaxId && next.centsTotal === prev.centsTotal) return next;
    prev = next;
  }
  throw new Error(
    'The spend ledger would not hold still across 5 consecutive reads, so no baseline can be taken.\n' +
    'Something else is writing to it — another test run, a worker, or a browser tab left open.\n' +
    'TREAT THIS AS NOT RUN: the money guard made no claim either way.',
  );
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
