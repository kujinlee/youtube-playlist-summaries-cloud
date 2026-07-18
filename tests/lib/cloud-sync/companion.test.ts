import { decideCompanion } from '@/lib/cloud-sync/companion';
import type { ModelEnvelope } from '@/lib/html-doc/model-store';

const env = (sourceMdHash?: string): ModelEnvelope => ({
  sourceMd: 'x', generatedAt: '2026', sourceSections: ['A'],
  model: { sections: [{ lead: 'l', bullets: [{ label: 'a', text: 'b' }, { label: 'c', text: 'd' }, { label: 'e', text: 'f' }] }] },
  ...(sourceMdHash ? { sourceMdHash } : {}),
});

it('ships when the envelope matches the winning MD', () => {
  expect(decideCompanion({ winnerMdHash: 'h1', senderEnvelope: env('h1') })).toMatchObject({ kind: 'ship' });
});
it('deletes the receiver model when the envelope does not match', () => {
  expect(decideCompanion({ winnerMdHash: 'h1', senderEnvelope: env('h2') }))
    .toEqual({ kind: 'deleteReceiverModel', shareNeedsOwnerServe: true });
});
it('deletes when the legacy envelope lacks sourceMdHash', () => {
  expect(decideCompanion({ winnerMdHash: 'h1', senderEnvelope: env(undefined) }))
    .toEqual({ kind: 'deleteReceiverModel', shareNeedsOwnerServe: true });
});
it('deletes when the sender has no model at all', () => {
  expect(decideCompanion({ winnerMdHash: 'h1', senderEnvelope: null }))
    .toEqual({ kind: 'deleteReceiverModel', shareNeedsOwnerServe: true });
});
