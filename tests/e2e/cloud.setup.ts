/**
 * M3.1-A — the authenticated cloud session every cloud spec reuses.
 *
 * Runs once, as its own Playwright project, before the `cloud` project (see playwright.config.ts
 * `dependencies`). It creates a fresh owner, seeds that owner's data, signs in THROUGH THE APP,
 * and writes the storage state to disk.
 *
 * WHY SIGN IN THROUGH THE UI RATHER THAN INJECT A COOKIE
 * `@supabase/ssr` owns the session cookie's name, chunking and encoding, and it has changed
 * across versions. A test that hand-writes that cookie asserts a FORMAT rather than a behaviour:
 * it would keep passing after the real format changed, and start failing when nothing was wrong.
 * Driving `/dev-login` makes the application's own client write the cookies, so this harness
 * cannot drift away from the thing it is meant to exercise.
 *
 * `/dev-login` cannot open anywhere but here: `lib/supabase/dev-login.ts` requires BOTH
 * `DEV_LOGIN_ENABLED === 'true'` AND a local Supabase URL, and fails closed on either.
 *
 * NO MONEY IS SPENT. Everything is seeded directly into the local database; no Gemini call and no
 * worker run is involved anywhere in this suite. THIS PROJECT IS INSIDE THE MEASURED WINDOW:
 * cloud-global.ts takes the ledger baseline before any project runs, and checks it as the run's
 * teardown even when this file fails (round-2 Blocking — the earlier `afterAll` lived in the
 * dependent project, which Playwright skips entirely when its dependency fails).
 */
// Side-effect import: loads .env.test.local and aliases the supabase-status names, and THROWS
// with the exact command to run when the local stack is absent. Reused rather than re-implemented
// — a second copy of an env loader is a second thing to drift.
import '../integration/setup';
import { test as setup, expect } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';
import { adminClient, newUser } from '../integration/helpers/clients';
import { seedPlaylist, seedPromotedVideo, seedSummaryBlob } from '../integration/helpers/seed';
import { SupabaseBlobStore } from '@/lib/storage/supabase/supabase-blob-store';
import { ARTIFACTS_BUCKET } from '@/lib/supabase/storage-env';
import { writeModelEnvelope } from '@/lib/html-doc/model-store';
import { GENERATOR_VERSION } from '@/lib/html-doc/constants';
import { parseSummaryMarkdown } from '@/lib/html-doc/parse';

// CANNOT RUN IS A FAILURE. @supabase/supabase-js's realtime client needs a native WebSocket, which
// Node has only from 22 — under 20 it dies with "Node.js 20 detected without native WebSocket
// support" from deep inside a constructor, which reads like a library bug rather than a local
// setup problem. Measured 2026-08-13. CI already pins 22 (.github/workflows/ci.yml); this makes the
// same requirement true of a laptop, and says so in one sentence.
const major = Number(process.versions.node.split('.')[0]);
if (major < 22) {
  throw new Error(
    `The cloud e2e suite needs Node >= 22 (running ${process.versions.node}).\n` +
    'supabase-js requires a native WebSocket, which Node 20 does not have.\n' +
    'Run: nvm use 22   (CI already pins 22)',
  );
}

import { AUTH_FILE, FIXTURE_FILE, type CloudFixture } from './cloud-fixture';



setup('create an owner, seed their library, and sign in through /dev-login', async ({ page }) => {
  const svc = adminClient();
  const { user, email, password } = await newUser();

  const listedTitle = `E2E Listed ${Date.now()}`;

  // ⚠ THIS FILE BRIEFLY PINNED `guardrail_config`, AND THAT WAS A MONEY REGRESSION. Recorded
  // because the reasoning was plausible and wrong. The worry was that the integration suite leaves
  // `daily_cap_cents: 3` behind (serve-model-charge.test.ts), so a render rung would "go green
  // having proved nothing". Traced, it does not: at_capacity → 503 (serve-summary-core.ts:122) →
  // the route returns that status, and rung 4 asserts 200 first, so it goes RED. Measured directly
  // — a run with daily_cap_cents=1 failed rung 4 with `Received: 503`. The pin therefore converted
  // a FREE red into a PAID red: with headroom restored the same drift reaches reserve_serve_model
  // and calls Gemini for 6¢. It also raised the local stack's kill-switch from its 500 default
  // (0011:28) to 5000 permanently, with nothing to restore it. A fixture widening a money control
  // is the opposite of what this suite is for, and `at_capacity` is exactly the fail-closed brake
  // it should be leaning on.
  const listed = await seedPlaylist(svc, user.id);
  // CHECK THE ERROR. seedPlaylist inserts with a NULL playlist_title, and PlaylistSidebar's mount
  // effect calls backfillPlaylistTitles() whenever any listed row has none — which reaches the REAL
  // YouTube Data API (app/api/playlists/backfill-titles/route.ts), un-intercepted and invisible to
  // the spend ledger. PostgREST does not throw when an update matches zero rows, so a silent
  // failure here would turn a locator timeout into outbound API calls on a suite whose config
  // promises it runs "for free".
  const titled = await svc.from('playlists')
    .update({ playlist_title: listedTitle }).eq('id', listed.playlistId).select('id');
  if (titled.error) throw new Error(`could not title the seeded playlist: ${titled.error.message}`);
  if (!titled.data?.length) throw new Error(`no playlist row ${listed.playlistId} to title`);
  const video = await seedPromotedVideo(svc, {
    ownerId: user.id,
    playlistId: listed.playlistId,
    // MUST be <= 20 chars of [A-Za-z0-9_-]: the routes run assertVideoId, and seedPromotedVideo's
    // default is `v-${randomUUID()}` (38 chars), which every route would reject with a 400 that
    // looks nothing like "your fixture is malformed". Same constraint the integration fixtures
    // call out (dig-serve-interactive.test.ts:32).
    videoId: `e2e${Date.now().toString(36)}`,
    title: 'A seeded video with a summary',
    position: 1,
  });
  // A KEY IS NOT A SUMMARY. seedPromotedVideo writes `artifacts.summaryMd.key`; the bytes live in
  // the blob store and the serve path get()s them. Without this upload every render assertion
  // downstream would be asserting against an empty document. Shape copied from
  // tests/integration/dig-serve-interactive.test.ts — a real parseable section (▶, en-dash range,
  // trailing `s`), not an invention, so the renderer's own parser is what is being exercised.
  const summaryMd =
    `# ${'A seeded video with a summary'}\n\n## 2. Encoder\n` +
    `▶ [2:12–2:20](https://youtu.be/${video.videoId}?t=132s)\nSeeded prose for the e2e journey.\n`;
  await seedSummaryBlob(svc, user.id, listed.playlistKey, video.base, summaryMd);

  // ⚠ SEED THE MAGAZINE MODEL TOO, OR THE SUITE SPENDS REAL MONEY ON EVERY RUN.
  // MEASURED 2026-08-13: without this, opening the HTML render called resolveMagazineModel, which
  // found no model, called Gemini, and reserved 12¢ in spend_ledger — while the header of the spec
  // file claimed "NO MONEY IS SPENT". The claim had been written from intent and never checked; it
  // was caught only because the rendered prose came back as LLM paraphrase instead of the seeded
  // text. The md path is exempt by design (serve-summary-core.ts:28 — it reads the blob and returns
  // without ever calling resolveMagazineModel); the HTML path is not.
  // Envelope shape copied from tests/integration/share-route.test.ts:79.
  await writeModelEnvelope(
    { id: user.id, indexKey: listed.playlistKey },
    video.base,
    {
      sourceMd: `${video.base}.md`,
      generatedAt: new Date().toISOString(),
      // DERIVED, NOT TYPED. This must equal what the serve path derives from the markdown above —
      // `parsed.sections.map(s => s.title)` at serve-doc.ts:71 — and the transformation is not the
      // identity: parse.ts:56 (`const title = ord ? ord[2].trim() : headingLine`) strips the leading
      // ordinal into a separate `numeral` field, so `## 2. Encoder` yields `Encoder`.
      //
      // It was hand-written as `['2. Encoder']` for a week. isFresh was permanently false, every
      // HTML render regenerated through Gemini, and the rung that would have shown it was skipped
      // BECAUSE of the cost that caused — 24¢ went through the ledger guessing at a contract that
      // is one line of the parser. Correcting the literal fixed the instance and left the class:
      // two strings in one file that must agree under a rule defined in another, checked by nothing.
      //
      // Ask what happens when it goes stale (memory: hardcode only what fails loudly). It fails
      // EXPENSIVELY and MUTELY — the rung says "text not visible", the guard says "the ledger
      // moved", neither says "the seed". So it is derived. Adding a second `##` section to the
      // markdown above now cannot silently re-arm it, which is the exact next edit backlog #44 wants.
      //
      // The trade, stated: the fixture can no longer catch a change in the parser. That is correct
      // here — its job is to BE FRESH, and the parser's own contract is pinned by the unit suite and
      // by share-route.test.ts. A tautological assertion is a defect; a tautological fixture cannot
      // be wrong.
      sourceSections: parseSummaryMarkdown(summaryMd).sections.map((s) => s.title),
      generatorVersion: GENERATOR_VERSION,
      model: {
        sections: [{
          lead: 'Seeded lead for the e2e journey.',
          bullets: [
            { label: 'one', text: 'Seeded bullet one.' },
            { label: 'two', text: 'Seeded bullet two.' },
            { label: 'three', text: 'Seeded bullet three.' },
          ],
        }],
      },
    },
    new SupabaseBlobStore(svc, ARTIFACTS_BUCKET),
  );

  await page.goto('/dev-login');
  await expect(page.getByRole('heading', { name: /local dev sign-in/i })).toBeVisible();
  await page.getByPlaceholder('Email').fill(email);
  await page.getByPlaceholder('Password').fill(password);
  await page.getByRole('button', { name: /sign in/i }).click();

  // hardNavigate('/') on success. Landing on the cloud root — and NOT being bounced to /login —
  // is the assertion that the session cookie was actually written and the middleware accepted it.
  await page.waitForURL('**/');
  await expect(page).not.toHaveURL(/\/login/);

  fs.mkdirSync(path.dirname(AUTH_FILE), { recursive: true });
  await page.context().storageState({ path: AUTH_FILE });

  const fixture: CloudFixture = {
    email,
    ownerId: user.id,
    listed: { playlistId: listed.playlistId, playlistKey: listed.playlistKey, title: listedTitle, videoId: video.videoId },
  };
  fs.writeFileSync(FIXTURE_FILE, JSON.stringify(fixture, null, 2));
});

