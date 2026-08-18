import fs from 'fs';
import os from 'os';
import path from 'path';
import { LocalFsMetadataStore } from '@/lib/storage/local/local-metadata-store';
import { localPrincipal } from '@/lib/storage/principal';

const store = new LocalFsMetadataStore();
// assertOutputFolder requires the path to be within home directory (macOS os.tmpdir()
// resolves outside home); create isolated sub-dirs under home instead.
//
// ⛔ DELETE WHAT YOU CREATED — never sweep $HOME by prefix. MEASURED 2026-08-17, ~1 run in 5:
// this cleanup used to be `readdirSync(os.homedir()).filter(d => d.startsWith('lms-'))`, and
// `'lms-serial-x9f2'.startsWith('lms-')` is TRUE — so it deleted the LIVE temp directories of
// tests/lib/storage/claim-video-slot-desired-serial.test.ts, which uses the `lms-serial-` prefix.
// Jest runs test files in parallel worker processes, so the two overlap and the victim's next
// readIndex died on ENOENT at lib/index-store.ts:85. A prefix is a claim on a NAMESPACE, and this
// file only owns the directories it made. Tracking them cannot silently widen; a prefix can, and
// the next `lms-…` test file would have been eaten too.
const created: string[] = [];
function tmp() {
  const dir = fs.mkdtempSync(path.join(os.homedir(), 'lms-mds-'));
  created.push(dir);
  return dir;
}
afterEach(() => {
  while (created.length) fs.rmSync(created.pop()!, { recursive: true, force: true });
});

test('readIndex on an empty folder returns the empty index shape', async () => {
  const p = localPrincipal(tmp());
  await expect(store.readIndex(p)).resolves.toEqual({ playlistUrl: '', outputFolder: p.indexKey, videos: [] });
});

test('claimVideoSlot appends serialNumber (1-based) and preserves array order', async () => {
  const p = localPrincipal(tmp());
  await store.setPlaylistMeta(p, { playlistUrl: 'https://youtube.com/playlist?list=X' });
  const a = await store.claimVideoSlot(p, 'vid00000001');
  const b = await store.claimVideoSlot(p, 'vid00000002');
  // A6a — the return is the serial ONLY; the row ordinal is no longer surfaced. Ordering is still
  // a real guarantee, so assert it where it actually lives: the persisted array.
  expect(a).toEqual({ serialNumber: 1 });
  expect(b).toEqual({ serialNumber: 2 });
  expect((await store.readIndex(p)).videos.map((v) => v.id))
    .toEqual(['vid00000001', 'vid00000002']);
});

test('bulkUpdateVideoFields merges fields, preserves array order', async () => {
  const p = localPrincipal(tmp());
  await store.claimVideoSlot(p, 'vid00000001');
  await store.upsertVideo(p, { id: 'vid00000001', youtubeUrl: 'https://youtu.be/vid00000001' } as any);
  await store.bulkUpdateVideoFields(p, [{ videoId: 'vid00000001', fields: { playlistIndex: 5 } as any }]);
  const idx = await store.readIndex(p);
  expect(idx.videos[0].playlistIndex).toBe(5);
});

test('reconcilePlaylistMembership archives absent, restores present', async () => {
  const p = localPrincipal(tmp());
  await store.claimVideoSlot(p, 'vid00000001');
  await store.upsertVideo(p, { id: 'vid00000001', youtubeUrl: 'https://youtu.be/vid00000001', archived: true, removedFromPlaylist: true } as any);
  await store.reconcilePlaylistMembership(p, ['vid00000001']);   // now present again
  const idx = await store.readIndex(p);
  expect(idx.videos[0].archived).toBe(false);
  expect(idx.videos[0].removedFromPlaylist).toBe(false);
});
