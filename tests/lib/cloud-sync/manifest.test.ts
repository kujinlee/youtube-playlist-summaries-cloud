// tests/lib/cloud-sync/manifest.test.ts
import { promises as fs } from 'fs';
import os from 'os';
import path from 'path';
import { manifestPath, readManifest, writeVideoBaseline, appendConflict } from '@/lib/cloud-sync/manifest';

async function root() { return fs.mkdtemp(path.join(os.tmpdir(), 'cs-man-')); }

it('returns an empty manifest when the file is missing', async () => {
  const r = await root();
  expect(await readManifest(r, 'PL1')).toEqual({ version: 1, videos: {} });
});

it('returns an empty manifest (no throw) on a corrupt file', async () => {
  const r = await root();
  await fs.mkdir(path.dirname(manifestPath(r, 'PL1')), { recursive: true });
  await fs.writeFile(manifestPath(r, 'PL1'), '{not json', 'utf8');
  expect(await readManifest(r, 'PL1')).toEqual({ version: 1, videos: {} });
});

it('round-trips a written baseline', async () => {
  const r = await root();
  const base = { classA: { docVersionMajor: 3, mdGeneratedAt: 't', mdCorrectionsHash: 'c', mdHash: 'h' },
                 classB: { personalNote: { value: 'n', editedAt: 't1' }, personalScore: { value: undefined, editedAt: undefined }, corrections: { value: undefined, editedAt: undefined } } };
  await writeVideoBaseline(r, 'PL1', 'v1', base as any);
  expect((await readManifest(r, 'PL1')).videos.v1).toEqual(base);
});

it('de-duplicates a repeated conflict within a run', async () => {
  const r = await root();
  const e = { video_id: 'v1', class: 'B' as const, field: 'personalNote', valueL: 'a', valueR: 'b', reason: 'both-changed' };
  await appendConflict(r, 'PL1', e);
  await appendConflict(r, 'PL1', e);
  const log = await fs.readFile(path.join(r, 'PL1', '.cloud-sync-conflicts.log'), 'utf8');
  expect(log.trim().split('\n')).toHaveLength(1);
});
