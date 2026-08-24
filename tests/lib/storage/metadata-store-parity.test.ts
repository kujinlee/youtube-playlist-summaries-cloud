// Parity properties of the MetadataStore annotations surface, against a REAL local store and a
// REAL index file on disk — no mocks. These pin the property that forces read-before-write into the
// CALLER (spec §4.1, slice A Task 6): both backends stamp `annotationsEditedAt` for every Class-B
// key SET OR CLEARED, so neither store can implement "only when it actually changed".
//
// ⚠ THE SUPABASE HALF IS NOT COVERED HERE and cannot be — it needs a live Postgres. Its equivalent
// is `update_video_annotations` (0021_cloud_sync_signals.sql:33-43), which stamps in both
// directions through the same `changed` accumulation. A green run of THIS file is evidence about
// the local adapter only; do not read it as evidence about the seam.
import fs from 'fs';
import os from 'os';
import path from 'path';
import * as indexStore from '@/lib/index-store';
import { LocalFsMetadataStore } from '@/lib/storage/local/local-metadata-store';
import { localPrincipal } from '@/lib/storage/principal';

const VIDEO_ID = 'testVideoId1';

let outputFolder: string;

function seed(corrections: string | undefined) {
  indexStore.writeIndex(outputFolder, {
    playlistUrl: 'https://youtube.com/playlist?list=PL1',
    outputFolder,
    videos: [{ id: VIDEO_ID, title: 'T', ...(corrections === undefined ? {} : { corrections }) }],
  } as never);
}

beforeEach(() => {
  // Inside HOME, not os.tmpdir(): assertOutputFolder refuses any path outside the home directory
  // (index-store.ts:52-54), and on macOS os.tmpdir() is /var/folders/… — outside it. Measured here
  // rather than assumed; the guard is real and this test drives the real adapter through it.
  outputFolder = fs.mkdtempSync(path.join(os.homedir(), '.yps-parity-'));
});

afterEach(() => {
  fs.rmSync(outputFolder, { recursive: true, force: true });
});

describe('local updateVideoAnnotations stamps in BOTH directions', () => {
  it('stamps annotationsEditedAt.corrections on a SET', async () => {
    seed(undefined);
    const store = new LocalFsMetadataStore();
    await store.updateVideoAnnotations(localPrincipal(outputFolder), VIDEO_ID, { corrections: 'x' }, []);
    const after = indexStore.readIndex(outputFolder).videos[0];
    expect(after.corrections).toBe('x');
    expect(after.annotationsEditedAt?.corrections).toEqual(expect.any(String));
  });

  it('stamps annotationsEditedAt.corrections on a CLEAR, not just a set', async () => {
    // THIS is the case that forces read-before-write upstream. A clear looks like "removing data",
    // so it reads as though it could not possibly move an edit timestamp — and it does.
    seed('x');
    const store = new LocalFsMetadataStore();
    await store.updateVideoAnnotations(localPrincipal(outputFolder), VIDEO_ID, {}, ['corrections']);
    const after = indexStore.readIndex(outputFolder).videos[0];
    expect(after.corrections).toBeUndefined();
    expect(after.annotationsEditedAt?.corrections).toEqual(expect.any(String));
  });

  it('stamps even when clearing an ALREADY-EMPTY field — the store cannot tell it was a no-op', async () => {
    // The store has no idea nothing changed, which is exactly why the ROUTE must not call it.
    // If this ever goes green-by-behaving-differently, the caller's guard becomes redundant rather
    // than wrong — re-read spec §4.1 before deleting anything.
    seed(undefined);
    const store = new LocalFsMetadataStore();
    await store.updateVideoAnnotations(localPrincipal(outputFolder), VIDEO_ID, {}, ['corrections']);
    const after = indexStore.readIndex(outputFolder).videos[0];
    expect(after.annotationsEditedAt?.corrections).toEqual(expect.any(String));
  });

  it('reports found: false for an unknown video rather than throwing', async () => {
    seed('x');
    const store = new LocalFsMetadataStore();
    const r = await store.updateVideoAnnotations(localPrincipal(outputFolder), 'noSuchVideo', { corrections: 'y' }, []);
    expect(r).toEqual({ found: false });
  });
});
