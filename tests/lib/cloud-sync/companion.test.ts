import { decideCompanion, type ModelRead } from '@/lib/cloud-sync/companion';
import type { ModelEnvelope } from '@/lib/html-doc/model-store';

const env = (sourceMdHash?: string): ModelEnvelope => ({
  sourceMd: 'x', generatedAt: '2026', sourceSections: ['A'],
  model: { sections: [{ lead: 'l', bullets: [{ label: 'a', text: 'b' }, { label: 'c', text: 'd' }, { label: 'e', text: 'f' }] }] },
  ...(sourceMdHash ? { sourceMdHash } : {}),
});
const envelope = (h?: string): ModelRead => ({ kind: 'envelope', envelope: env(h) });
const decide = (senderModel: ModelRead, receiverModel: ModelRead) =>
  decideCompanion({ winnerMdHash: 'h1', senderModel, receiverModel });

const DELETE = { kind: 'deleteReceiverModel', shareNeedsOwnerServe: true };
/** Keep the receiver's blob. `flag` is the SEPARATE report-only axis (§10 row 7). */
const KEEP = (flag: boolean) => ({ kind: 'noop', shareNeedsOwnerServe: flag });

// ── Rule 1 — the sender has a model built from the WINNING md: ship it, whatever the receiver holds.
describe('sender ships', () => {
  it.each<[string, ModelRead]>([
    ['receiver absent', { kind: 'none' }],
    ['receiver unreadable', { kind: 'unknown' }],
    ['receiver stale', envelope('h2')],
    ['receiver already current', envelope('h1')],
  ])('ships a matching sender envelope (%s)', (_label, receiver) => {
    expect(decide(envelope('h1'), receiver)).toMatchObject({ kind: 'ship' });
  });
});

// ── H-R5-1 (round 5) — rules 2/3. The sender read answers "can a replacement be shipped?"; it does
//    NOT answer "is the receiver's model stale?". Only the RECEIVER's own sourceMdHash answers that,
//    and it answers it exactly. So every non-ship sender state funnels into the same receiver-keyed
//    decision — `unknown` is no longer a decision of its own, and `none` no longer deletes blind.
describe('receiver-keyed decision (every non-shipping sender state)', () => {
  const nonShippingSenders: [string, ModelRead][] = [
    ['sender provably has none', { kind: 'none' }],
    ['sender read is unprovable', { kind: 'unknown' }],
    ['sender envelope does not match the winner', envelope('h2')],
    ['sender envelope is legacy (no sourceMdHash)', envelope(undefined)],
  ];

  describe.each(nonShippingSenders)('%s', (_label, sender) => {
    it('DELETES a receiver model whose sourceMdHash provably differs from the winner', () => {
      expect(decide(sender, envelope('h2'))).toEqual(DELETE);
    });
    it('KEEPS a receiver model whose sourceMdHash matches the winner (still valid — paid artifact)', () => {
      expect(decide(sender, envelope('h1'))).toEqual(KEEP(false));
    });
    it('touches nothing when the receiver PROVABLY has no model, but still counts the unready share', () => {
      // §10 row 7 — nothing to delete, yet the share cannot render until the owner re-serves. The
      // blob action and the report flag are separate axes.
      expect(decide(sender, { kind: 'none' })).toEqual(KEEP(true));
    });
    it('KEEPS but still counts when the receiver read itself could not prove absence', () => {
      // Unprovable, so the DELETE must not fire — but the flag costs nothing and under-reporting
      // is what strands an anon visitor on a not-ready share.
      expect(decide(sender, { kind: 'unknown' })).toEqual(KEEP(true));
    });
    it('KEEPS but still counts a legacy receiver envelope with no sourceMdHash', () => {
      expect(decide(sender, envelope(undefined))).toEqual(KEEP(true));
    });
  });
});

// ── The report flag on the SHIP branch: the receiver ends up holding a model built from the
//    winning MD, so the share renders and nothing is owed.
it('never flags owner-serve when a model was shipped', () => {
  for (const r of [{ kind: 'none' }, { kind: 'unknown' }, envelope('h2'), envelope('h1')] as ModelRead[]) {
    expect(decide(envelope('h1'), r)).not.toMatchObject({ shareNeedsOwnerServe: true });
  }
});

// ── The money invariant, stated once as its own assertion: the ONLY input that deletes is a receiver
//    envelope carrying a sourceMdHash that differs from the winner's. Everything else keeps.
it('deletes only on a proven receiver-side mismatch', () => {
  const senders: ModelRead[] = [{ kind: 'none' }, { kind: 'unknown' }, envelope('h2'), envelope(undefined), envelope('h1')];
  const receivers: ModelRead[] = [{ kind: 'none' }, { kind: 'unknown' }, envelope('h1'), envelope(undefined), envelope('h2')];
  for (const s of senders) {
    for (const r of receivers) {
      const deleted = decideCompanion({ winnerMdHash: 'h1', senderModel: s, receiverModel: r }).kind === 'deleteReceiverModel';
      const senderShips = s.kind === 'envelope' && s.envelope.sourceMdHash === 'h1';
      const receiverProvablyStale = r.kind === 'envelope' && r.envelope.sourceMdHash !== undefined
        && r.envelope.sourceMdHash !== 'h1';
      expect(deleted).toBe(!senderShips && receiverProvablyStale);
    }
  }
});
