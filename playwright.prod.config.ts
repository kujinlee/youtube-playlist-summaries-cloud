import { defineConfig } from '@playwright/test';
import { PROD_URL } from './tests/e2e/prod-fixture';

/**
 * M3.1-B — the read-only smoke against the DEPLOYED application.
 *
 *     npm run test:e2e:prod
 *
 * Spec: docs/superpowers/specs/2026-08-19-prod-readonly-smoke-design.md
 *
 * A THIRD CONFIG, for the same reason there is a second: `playwright.cloud.config.ts:8-14` records
 * that `/` dispatches between two whole applications on a runtime env var, so each target needs its
 * own server. This one goes further — it has NO `webServer` AT ALL. There is nothing to start; the
 * server under test is production, and a config that could start something is a config that could
 * accidentally test the wrong thing.
 *
 * WHY IT IS A GATE AND NOT A SUITE. Decided with the user 2026-08-19: this runs after every deploy
 * and a red run means the release is not good. The alternative — a tool run on a whim — was
 * rejected because an optional check drifts into never being run and is broken by the time it is
 * wanted.
 *
 * NO RETRIES, DELIBERATELY. A retry converts an intermittent production failure into a green run,
 * which is the one outcome a deploy gate must never produce. If a check is flaky the check is
 * wrong; fix it rather than hiding it.
 *
 * NO MONEY IS SPENT, AND THE RUN MEASURES THAT RATHER THAN PROMISING IT — tests/e2e/prod-global.ts
 * brackets the run with a read of the PRODUCTION spend ledger through a read-only credential that
 * was measured to hold zero write grants across all 12 public tables. Until this existed nothing
 * watched prod's ledger at all.
 */
export default defineConfig({
  testDir: './tests/e2e',
  testMatch: /prod-smoke\.spec\.ts$/,
  outputDir: './test-results',
  globalSetup: './tests/e2e/prod-global.ts',
  // One worker: the checks are serial by declaration and share one production account. Parallelism
  // would buy seconds on a suite that is already meant to finish in under a minute.
  workers: 1,
  retries: 0,
  reporter: [['list']],
  use: {
    baseURL: PROD_URL,
    screenshot: 'only-on-failure',
    trace: 'retain-on-failure',
    // A named agent so anything this suite does is identifiable in production access logs. It only
    // ever reads, but "which client made that request" should never be a guess.
    userAgent: 'm3.1b-prod-smoke (read-only deploy gate)',
  },
  // NOTE: no project-level `storageState`. Playwright loads it when the CONTEXT is created, before
  // any test body runs, so a missing session file would become an unreadable framework error and
  // would take checks 1, 5 and 6 down with it — and those need no session. The three checks that
  // do need one build their context by hand, after the pre-flight has spoken.
});
