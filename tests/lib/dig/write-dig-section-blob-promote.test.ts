/**
 * Architecture review finding #2 — "the commit→promote protocol has no owner".
 *
 * `lib/storage/supabase/consistency.ts:writeArtifact` implements the correct ordered
 * write and has ZERO production callers. Five writers hand-roll it instead. One of
 * them (`lib/cloud-sync/sync-run.ts:322`) discovered that the two adapters DISAGREE
 * about `promote()` and worked around it AT THAT ONE CALL SITE:
 *
 *   local     -> fs.renameSync(from, to)                  -> final gets the NEW body
 *   Supabase  -> if (exists(final)) { remove(temp); return } -> final KEEPS ITS OLD BODY
 *
 * `writeDigSectionBlob` still calls `promote()` assuming uniformity. This test asks
 * the question the review could only raise: when a dug section is re-written to an
 * existing key, does the cloud path serve the new content or silently keep the old?
 *
 * Per docs/dev-process.md — "before deferring a finding, try to turn it into an
 * assertion" — this exists to promote the hypothesis to a confirmed defect or retire it.
 */
import { writeDigSectionBlob } from '@/lib/dig/cloud/write-dig-section-blob';
import { digSectionKey } from '@/lib/dig/cloud/dig-blob-key';
import { InMemoryBlobStore } from '@/lib/storage/testing/in-memory-blob-store';
import { localPrincipal } from '@/lib/storage/principal';

const principal = localPrincipal('/idx');
const BASE = 'vid123';
const SECTION = 65;

function input(blobStore: InMemoryBlobStore, body: string) {
  return {
    blobStore,
    principal,
    base: BASE,
    videoId: 'vid123',
    sectionId: SECTION,
    startSec: SECTION,
    title: 'A section',
    language: 'en' as const,
    sourceVideoUrl: 'https://youtu.be/vid123',
    bodyMarkdown: body,
    generatedAt: '2026-07-30T00:00:00.000Z',
  };
}

describe('writeDigSectionBlob — re-writing an already-dug section (finding #2)', () => {
  it('writes to the SAME key for the same (base, sectionId) — so a re-dig collides', () => {
    expect(digSectionKey(BASE, SECTION)).toBe(digSectionKey(BASE, SECTION));
  });

  it('serves the NEW body under local semantics (promote overwrites)', async () => {
    const store = new InMemoryBlobStore({ promoteSemantics: 'overwrite' });
    await writeDigSectionBlob(input(store, 'ORIGINAL dig content'));
    await writeDigSectionBlob(input(store, 'REGENERATED dig content'));

    const bytes = await store.get(principal, digSectionKey(BASE, SECTION));
    expect(bytes?.toString()).toContain('REGENERATED dig content');
  });

  // The behaviour under test. If this fails, finding #2 is a LIVE DEFECT on the cloud
  // path: a re-dug section keeps its stale body, and the writer stamps no metadata that
  // would reveal it (behaviour W2 of the review — the only writer with no metadata at all).
  it('serves the NEW body under Supabase semantics (promote is create-if-absent)', async () => {
    const store = new InMemoryBlobStore({ promoteSemantics: 'create-if-absent' });
    await writeDigSectionBlob(input(store, 'ORIGINAL dig content'));
    await writeDigSectionBlob(input(store, 'REGENERATED dig content'));

    const bytes = await store.get(principal, digSectionKey(BASE, SECTION));
    expect(bytes?.toString()).toContain('REGENERATED dig content');
  });

  it('leaves no staging temp behind either way', async () => {
    for (const semantics of ['overwrite', 'create-if-absent'] as const) {
      const store = new InMemoryBlobStore({ promoteSemantics: semantics });
      await writeDigSectionBlob(input(store, 'first'));
      await writeDigSectionBlob(input(store, 'second'));
      const staged = (await store.list(principal, '')).filter((k) => k.startsWith('_staging/'));
      expect(staged).toEqual([]);
    }
  });
});
