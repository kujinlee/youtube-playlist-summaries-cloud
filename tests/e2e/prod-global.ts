/**
 * Pre-flight and the money bracket for the M3.1-B production smoke.
 *
 * WHY THIS LIVES IN globalSetup AND NOT IN A HOOK — settled already by tests/e2e/cloud-global.ts:8-35
 * and transferred unchanged: Playwright does not run a project whose dependency failed, so a guard
 * inside a spec is absent in exactly the window it is needed. `globalSetup` sits outside every
 * project, and returning a function from it registers that function as the run's teardown.
 *
 * ONE REFUSAL ABORTS THE RUN; THREE FAILURES DO NOT — and the difference is deliberate.
 *
 *   P2 (a write credential is present) THROWS. It is a refusal, not a finding: the suite must not
 *   run at all while holding something that can mutate production.
 *
 *   P1, P3 and P4 are RECORDED instead. Aborting on them would throw away real evidence — checks 1,
 *   5 and 6 need no session and no anchor, and a run that reports "release v7, auth locks intact,
 *   ledger unmoved, and these three could not run" is strictly more useful than one that reports
 *   nothing. Each dependent check then fails with a NOT RUN message, so the run still exits
 *   non-zero and nothing green is ever claimed on unmeasured ground.
 */
import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import {
  AUTH_FILE, FIXTURE_FILE, FLY_APP, readAnchor, readLedger, readOnlyDatabaseUrl, sessionState,
  type Fixture, type Ledger,
} from './prod-fixture';

/** P2 — the mirror image of the cloud suite's assertLocalStack().
 *
 *  That guard (cloud-global.ts:137-152) stops a WRITE credential being aimed at prod. This one
 *  stops the suite HOLDING one. The asymmetry matters: this suite's entire safety claim is that it
 *  cannot mutate production, and a claim enforced by "we only wrote read queries" is a promise,
 *  not a mechanism. The service-role key bypasses RLS and every grant; if it is in the environment
 *  at all, one careless import is enough.
 */
function refuseWriteCredential(): void {
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!key) return;
  throw new Error(
    'P2 — REFUSED: the production smoke will not run while SUPABASE_SERVICE_ROLE_KEY is set.\n' +
    'This suite is read-only BY CONSTRUCTION, and that claim is worth only as much as the\n' +
    'credentials it holds. The service-role key bypasses RLS and every table grant.\n' +
    'Unset it for this run:  env -u SUPABASE_SERVICE_ROLE_KEY npm run test:e2e:prod',
  );
}

/** Check 1's input. Separated from the assertion so the two failure modes stay distinguishable:
 *  flyctl MISSING is NOT RUN, flyctl ANSWERING WITH NO COMPLETE RELEASE is a finding. */
function readLiveRelease(): { release: string | null; error: string | null } {
  try {
    const out = execFileSync('flyctl', ['releases', '--app', FLY_APP, '--json'], {
      encoding: 'utf8', timeout: 30_000, stdio: ['ignore', 'pipe', 'pipe'],
    });
    const rows = JSON.parse(out) as Array<{ Version?: number; version?: number; Status?: string; status?: string }>;
    const complete = rows.find((r) => (r.Status ?? r.status) === 'complete');
    if (!complete) return { release: null, error: 'flyctl answered but named no complete release' };
    return { release: `v${complete.Version ?? complete.version}`, error: null };
  } catch (err) {
    return { release: null, error: `flyctl unavailable: ${(err as Error).message.split('\n')[0]}` };
  }
}

function moneyGuard(baseline: Ledger | null) {
  return async () => {
    if (!baseline) return;               // P4 already recorded it; check 6 reports the NOT RUN
    const now = await readLedger();
    if (now.auditMaxId === baseline.auditMaxId && now.centsTotal === baseline.centsTotal) return;
    throw new Error(
      'THE PRODUCTION SPEND LEDGER MOVED DURING THIS RUN.\n' +
      `  ledger_audit max(id)   ${baseline.auditMaxId} -> ${now.auditMaxId}\n` +
      `  spend_ledger cents     ${baseline.centsTotal} -> ${now.centsTotal}\n` +
      'This suite touches only paths that cannot reach a paid call — the markdown serve path\n' +
      'short-circuits before resolveAndParse (app/api/html/[id]/route.ts:75-82).\n' +
      'TWO EXPLANATIONS AND THIS GUARD CANNOT TELL THEM APART, because the ledger is GLOBAL:\n' +
      '  1. the suite spent — a serve path regenerated, which would mean the money invariant broke;\n' +
      '  2. YOU spent — a browser tab open on the deployed app, or the worker, during the run.\n' +
      'Re-run with nothing else touching prod before concluding (1).',
    );
  };
}

export default async function prodGlobalSetup() {
  refuseWriteCredential();                                            // P2 — the only abort

  // Stale-fixture deletion, for the reason cloud-global.ts:57-67 records: identity by construction
  // rather than identity by stamp. On the CLI runner globalSetup runs once per invocation, so a
  // fixture can only exist if THIS run wrote it. (UI/watch mode is not supported — same caveat.)
  fs.rmSync(FIXTURE_FILE, { force: true });
  fs.mkdirSync(path.dirname(FIXTURE_FILE), { recursive: true });

  const session = sessionState();                                     // P1
  const { release, error: releaseError } = readLiveRelease();

  let ledger: Ledger | null = null;
  let ledgerError: string | null = null;
  let anchor: Awaited<ReturnType<typeof readAnchor>> = null;
  let anchorError: string | null = null;

  if (!readOnlyDatabaseUrl()) {
    ledgerError = anchorError = 'CLAUDE_RO_DATABASE_URL is not set (checked env and .env.local)';
  } else {
    try { ledger = await readLedger(); }                              // P4
    catch (err) { ledgerError = (err as Error).message; }
    try {
      anchor = await readAnchor();                                    // P3
      if (!anchor) anchorError = 'no production video has a non-empty summaryMd to anchor on';
    } catch (err) { anchorError = (err as Error).message; }
  }

  const fixture: Fixture = { ledger, ledgerError, anchor, anchorError, session, release, releaseError };
  fs.writeFileSync(FIXTURE_FILE, JSON.stringify(fixture, null, 2));

  // A one-line situation report before any check runs, so a reader of the output knows what the
  // suite could and could not reach WITHOUT decoding six failures to work it out.
  const parts = [
    `release=${release ?? `UNKNOWN (${releaseError})`}`,
    `session=${session}${session === 'live' ? '' : `  (${AUTH_FILE})`}`,
    `anchor=${anchor ? `${anchor.videoId} in "${anchor.playlistTitle}"` : `NONE (${anchorError})`}`,
    `ledger=${ledger ? `audit ${ledger.auditMaxId}, ${ledger.centsTotal}¢` : `UNREADABLE (${ledgerError})`}`,
  ];
  console.log(`\nM3.1-B prod smoke · ${parts.join('\n                    ')}\n`);

  return moneyGuard(ledger);
}
