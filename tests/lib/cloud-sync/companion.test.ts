import { decideCompanion } from '@/lib/cloud-sync/companion';
import type { ModelEnvelope } from '@/lib/html-doc/model-store';

const env = (sourceMdHash?: string): ModelEnvelope => ({
  sourceMd: 'x', generatedAt: '2026', sourceSections: ['A'],
  model: { sections: [{ lead: 'l', bullets: [{ label: 'a', text: 'b' }, { label: 'c', text: 'd' }, { label: 'e', text: 'f' }] }] },
  ...(sourceMdHash ? { sourceMdHash } : {}),
});

it('ships when the envelope matches the winning MD', () => {
  expect(decideCompanion({ winnerMdHash: 'h1', senderModel: { kind: 'envelope', envelope: env('h1') } }))
    .toMatchObject({ kind: 'ship' });
});
it('deletes the receiver model when the envelope does not match', () => {
  expect(decideCompanion({ winnerMdHash: 'h1', senderModel: { kind: 'envelope', envelope: env('h2') } }))
    .toEqual({ kind: 'deleteReceiverModel', shareNeedsOwnerServe: true });
});
it('deletes when the legacy envelope lacks sourceMdHash', () => {
  expect(decideCompanion({ winnerMdHash: 'h1', senderModel: { kind: 'envelope', envelope: env(undefined) } }))
    .toEqual({ kind: 'deleteReceiverModel', shareNeedsOwnerServe: true });
});
it('deletes when the sender PROVABLY has no model at all', () => {
  expect(decideCompanion({ winnerMdHash: 'h1', senderModel: { kind: 'none' } }))
    .toEqual({ kind: 'deleteReceiverModel', shareNeedsOwnerServe: true });
});

// ── H1 (round 4) — the third state. A sender read that could not PROVE the model is absent
//    (a Supabase get swallows network/5xx/timeout/RLS into the same null as a 404) must NOT be
//    read as "the sender has no model": deleting the receiver's model on that signal destroys a
//    cache whose only recovery is a PAID Gemini magazine transform. No-op instead — the receiver
//    keeps its (possibly stale) model, which the serve path's sourceSections drift guard rejects
//    for free if it no longer matches.
it('no-ops when the sender model could not be read (absence unprovable)', () => {
  expect(decideCompanion({ winnerMdHash: 'h1', senderModel: { kind: 'unknown' } }))
    .toEqual({ kind: 'noop' });
});
it('no-ops on unknown even when a matching hash would otherwise ship', () => {
  // There is no envelope to ship — `unknown` carries no bytes at all, so the only safe action is
  // to leave BOTH sides exactly as they are.
  expect(decideCompanion({ winnerMdHash: 'h1', senderModel: { kind: 'unknown' } }).kind).toBe('noop');
});
