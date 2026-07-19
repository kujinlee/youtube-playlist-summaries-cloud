// tests/lib/cloud-sync/model-writer-hash.test.ts
//
// Drives the REAL generation path (runHtmlDoc, mirroring tests/lib/html-doc/generate.test.ts)
// and asserts the persisted model envelope's sourceMdHash is the hash of the MD BODY that was
// fed to generation — NOT a hash of the sourceMd/summaryMd blob KEY (the filename). Guards
// former-High ⑤: decideCompanion (Task 8) compares against mdHash(body); a filename-hash never
// matches, so every synced companion would be wrongly deleted (needless re-charge on serve).
import crypto from 'crypto';
import fs from 'fs';
import os from 'os';
import path from 'path';
import { runHtmlDoc } from '../../../lib/html-doc/generate';
import * as gemini from '../../../lib/gemini';
import { readModelEnvelope } from '../../../lib/html-doc/model-store';
import { localPrincipal } from '@/lib/storage/principal';
import { mdHash } from '../../../lib/cloud-sync/content-hash';

jest.mock('../../../lib/gemini');
const mockTransform = gemini.generateMagazineModel as jest.Mock;

let dir: string;
const VIDEO_ID = 'vid12345';

// The MD body fed to generation (the whole file `runHtmlDoc` reads as `video.summaryMd`'s blob).
const BODY = `---
video_id: "vid12345"
lang: EN
score: 4
---

# A Title

**Channel:** Chan | **Duration:** 1:00 | **URL:** https://youtu.be/x

---

## 1. First
First section prose.
---
## Conclusion
Wrap up.
`;

function writeIndex(videos: unknown[]) {
  fs.writeFileSync(
    path.join(dir, 'playlist-index.json'),
    JSON.stringify({ playlistUrl: 'https://x.test/p', outputFolder: dir, videos }, null, 2),
  );
}

function baseVideo() {
  return {
    id: VIDEO_ID, title: 'A Title', youtubeUrl: 'https://youtu.be/x', language: 'en',
    durationSeconds: 60, archived: false,
    ratings: { usefulness: 4, depth: 4, originality: 4, recency: 4, completeness: 4 },
    overallScore: 4, summaryMd: 'a-title.md',
    summaryHtml: null, processedAt: '2026-06-09T00:00:00.000Z',
  };
}

beforeEach(() => {
  jest.clearAllMocks();
  dir = path.join(os.homedir(), `.tmp-modelhash-test-${crypto.randomUUID()}`);
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(path.join(dir, 'a-title.md'), BODY);
  writeIndex([baseVideo()]);
});
afterEach(() => { fs.rmSync(dir, { recursive: true, force: true }); });

it('a freshly written model envelope carries sourceMdHash = mdHash(MD BODY)', async () => {
  mockTransform.mockResolvedValueOnce({
    sections: [
      { lead: 'Lead one.', bullets: [{ label: 'L', text: 't' }, { label: 'M', text: 'u' }, { label: 'N', text: 'v' }] },
    ],
  });
  await runHtmlDoc(VIDEO_ID, dir, () => {});

  const principal = localPrincipal(dir);
  const env = await readModelEnvelope(principal, 'a-title');
  expect(env).not.toBeNull();
  expect(env!.sourceMdHash).toBe(mdHash(BODY));            // hashes the BODY
  expect(env!.sourceMdHash).not.toBe(mdHash(env!.sourceMd)); // NOT the filename/key (guards N1)
});
