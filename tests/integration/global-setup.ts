// tests/integration/global-setup.ts
//
// Apply pending Supabase migrations ONCE before the integration suite runs.
//
// WHY THIS EXISTS — a gate that failed OPEN. `npm run test:integration` used to run against
// whatever schema the local stack happened to have. On a branch that adds a migration, that is the
// *old* schema, and the whole suite reports green while testing code that is not the code under
// review. Not a red suite someone learns to ignore: a GREEN one that proves nothing.
//
// It bit exactly once, and expensively. Migration 0023 sat unapplied on `fix/serial-coherence-sync`;
// applying it by hand surfaced two real failures immediately — one test asserting the very
// phantom-serial bug 0023 fixes (its own comment said "Observed behavior … per T8/T9 flag", i.e.
// someone noticed it was odd, wrote down what it *did* instead of what it *should* do, and never
// closed the flag), and one stale key assertion that had been passing for the wrong reason.
//
// A migration is precisely when the suite matters most, and precisely when it silently stopped
// applying. Hence: apply first, every run.
//
// WHY SHELL OUT rather than introspect. `pg` is not a dependency, and reaching the DB otherwise
// means `docker exec` against a container name that varies by project. `supabase migration up` is
// the same tool that owns the migration state, is idempotent (a no-op costs ~4.6 s against a ~160 s
// suite), and fails loudly if the stack is down.
//
// WHY globalSetup and not setupFiles. `setupFiles` runs per test FILE — 60+ times per run.

import { execFileSync } from 'child_process';

/** Pull the CLI's JSON result line out of its chatter ("Connecting to local database…" first). */
function parseApplied(stdout: string): string[] | null {
  for (const line of stdout.split('\n')) {
    const trimmed = line.trim();
    if (!trimmed.startsWith('{')) continue;
    try {
      const parsed = JSON.parse(trimmed);
      if (Array.isArray(parsed?.applied)) return parsed.applied as string[];
    } catch {
      // not the line we want; keep looking
    }
  }
  return null;
}

export default function globalSetup(): void {
  let stdout: string;
  try {
    stdout = execFileSync('npx', ['supabase', 'migration', 'up'], {
      encoding: 'utf8',
      stdio: ['ignore', 'pipe', 'pipe'],
      cwd: process.cwd(),
    });
  } catch (e) {
    const err = e as { stdout?: string; stderr?: string };
    throw new Error(
      'Could not apply pending Supabase migrations, so the integration suite would be testing an ' +
      'UNKNOWN schema. Refusing to run rather than reporting a green suite that proves nothing.\n' +
      'Start the stack with: npx supabase start\n\n' +
      `${err.stderr ?? ''}${err.stdout ?? ''}`,
    );
  }

  const applied = parseApplied(stdout);
  if (applied === null) {
    // The command succeeded but said something this parser does not recognise — treat that as
    // unknown rather than fine, for the same reason the suite refuses above.
    throw new Error(
      `Could not read the result of 'supabase migration up'; refusing to run against an ` +
      `unverified schema.\n${stdout}`,
    );
  }

  // Applying anything here means the developer's DB was BEHIND the branch — i.e. every previous
  // run on this machine tested the wrong schema. Say so loudly; silence is what caused the bug.
  if (applied.length > 0) {
    const names = applied.map((p) => p.split('/').pop()).join(', ');
    console.warn(
      `\n[integration] Applied ${applied.length} pending migration(s) before running: ${names}\n` +
      `[integration] Your local schema was BEHIND this branch — earlier runs on this machine ` +
      `tested the old schema.\n`,
    );
  }
}
