import type { ModelEnvelope } from '@/lib/html-doc/model-store';

export type CompanionAction =
  | { kind: 'ship'; envelope: ModelEnvelope }
  | { kind: 'deleteReceiverModel'; shareNeedsOwnerServe: true };

/** Ship the sender's model iff it was generated from the winning MD (§4.2). */
export function decideCompanion(args: {
  winnerMdHash: string;
  senderEnvelope: ModelEnvelope | null;
}): CompanionAction {
  const { winnerMdHash, senderEnvelope } = args;
  if (senderEnvelope && senderEnvelope.sourceMdHash === winnerMdHash) {
    return { kind: 'ship', envelope: senderEnvelope };
  }
  return { kind: 'deleteReceiverModel', shareNeedsOwnerServe: true };
}
