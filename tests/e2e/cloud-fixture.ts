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

/** NOT under test-results/: Playwright wipes outputDir at the start of every run. */
export const AUTH_FILE = 'playwright/.auth/cloud-user.json';
export const FIXTURE_FILE = 'playwright/.auth/cloud-fixture.json';

export type CloudFixture = {
  email: string;
  ownerId: string;
  listed: { playlistId: string; playlistKey: string; title: string; videoId: string };
};

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
