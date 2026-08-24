// Spec §7's falsifiers asserted at the CONSUMER, not at the code that produces the value.
// Tasks 1–11 each tested their own unit; these are the rows no single task owns.
//
// ⚠ The rows that need a live Supabase stack are in tests/integration/corrections-cloud.int.test.ts
// and are NOT covered here. A green run of this file is evidence about pure functions only.
import { isFresh } from '@/lib/html-doc/read-model';
import { GENERATOR_VERSION } from '@/lib/html-doc/constants';
import { mdHash } from '@/lib/cloud-sync/content-hash';
import { stripQuickViewCallout, insertQuickViewCallout } from '@/lib/quick-view-callout';

const env = (over: Record<string, unknown> = {}) => ({
  sourceMd: 'x.md', generatedAt: 'now', sourceSections: ['A'],
  generatorVersion: GENERATOR_VERSION,
  model: { sections: [{ lead: 'l', bullets: [{ label: 'a', text: 'x' }, { label: 'b', text: 'y' }, { label: 'c', text: 'z' }] }] },
  ...over,
} as never);

describe('§7 — the reader sees the correction', () => {
  it('a corrected body makes the cached model stale', () => {
    const before = 'body one';
    const after = 'body two';
    expect(isFresh(env({ sourceMdHash: mdHash(before) }), ['A'], mdHash(after))).toBe(false);
  });

  it('an unchanged body keeps it fresh — no regeneration loop', () => {
    const body = 'body one';
    expect(isFresh(env({ sourceMdHash: mdHash(body) }), ['A'], mdHash(body))).toBe(true);
  });

  it('a legacy envelope with no sourceMdHash stays fresh and moves no money', () => {
    expect(isFresh(env(), ['A'], mdHash('anything'))).toBe(true);
  });
});

describe('§7 — a bare press disturbs nothing the sync decision reads', () => {
  const DOC = '---\nvideo_id: v\n---\n\n# T\n\n**Channel:** C\n\n---\n\n## 1. A\n\nProse.\n';

  it('a callout-only change moves the whole-body hash — which is why the write is skipped', () => {
    const a = insertQuickViewCallout(DOC, 'TLDR A', ['x'], []);
    const b = insertQuickViewCallout(stripQuickViewCallout(a), 'TLDR B', ['y'], []);
    // The fixture must actually differ, or both assertions below are vacuous.
    expect(a).not.toEqual(b);
    expect(mdHash(a)).not.toBe(mdHash(b));
  });

  it('…while the PROSE hash is invariant under it', () => {
    const a = insertQuickViewCallout(DOC, 'TLDR A', ['x'], []);
    const b = insertQuickViewCallout(stripQuickViewCallout(a), 'TLDR B', ['y'], []);
    expect(mdHash(stripQuickViewCallout(a))).toBe(mdHash(stripQuickViewCallout(b)));
  });

  it('so a non-deterministic quick-view alone would have booked a regeneration', () => {
    // The two facts above, joined into the claim T3 rests on: the callout lands in the region the
    // body hash covers but the magazine model is NOT built from, so writing it would invalidate
    // (e)'s freshness and buy a regeneration that recomputes an identical result. Stated as its own
    // row because neither hash assertion alone says it.
    const a = insertQuickViewCallout(DOC, 'TLDR A', ['x'], []);
    const b = insertQuickViewCallout(stripQuickViewCallout(a), 'TLDR B', ['y'], []);
    const titles = ['A'];
    expect(isFresh(env({ sourceMdHash: mdHash(a) }), titles, mdHash(b))).toBe(false);
  });
});
