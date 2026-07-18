import type { ModelEnvelope } from '@/lib/html-doc/model-store';

/** H1 (round 4) — the result of reading the SENDER's model, as a TRI-state.
 *  `readModelEnvelope` collapses three different situations into one null: the envelope is absent,
 *  it is corrupt/schema-invalid, or its bytes could not be READ. The first two mean the sender has
 *  nothing shippable (the receiver's model is now stale and should go); the third means we simply
 *  do not know, and acting on it destroys a paid artifact. Which of those a null is depends on the
 *  backend — see BlobStore.provesAbsence — so the caller resolves it and hands the answer here. */
export type SenderModelRead =
  | { kind: 'envelope'; envelope: ModelEnvelope }
  | { kind: 'none' }      // the sender PROVABLY has no usable model
  | { kind: 'unknown' };  // the read failed in a way that cannot prove absence

export type CompanionAction =
  | { kind: 'ship'; envelope: ModelEnvelope }
  | { kind: 'deleteReceiverModel'; shareNeedsOwnerServe: true }
  | { kind: 'noop' };

/** Ship the sender's model iff it was generated from the winning MD (§4.2).
 *
 *  H1 (round 4) — `unknown` is a NO-OP, not a delete. Deleting the receiver's model costs a paid
 *  Gemini magazine transform to recover (runHtmlDoc → generateMagazineModel locally, or
 *  resolveMagazineModel → reserve_serve_model → spend_ledger on the cloud), and the delete is
 *  silent and sticky: it does not throw, so the caller advances the manifest baseline, and the next
 *  run's Class-A reconcile returns 'skip' and never revisits the companion step. Keeping a possibly
 *  stale receiver model is the cheap side of that trade — a model is only ever a cache, and the
 *  serve path's sourceSections drift guard (lib/html-doc/read-model.ts) rejects a mismatched one
 *  for free. */
export function decideCompanion(args: {
  winnerMdHash: string;
  senderModel: SenderModelRead;
}): CompanionAction {
  const { winnerMdHash, senderModel } = args;
  if (senderModel.kind === 'unknown') return { kind: 'noop' };
  if (senderModel.kind === 'envelope' && senderModel.envelope.sourceMdHash === winnerMdHash) {
    return { kind: 'ship', envelope: senderModel.envelope };
  }
  return { kind: 'deleteReceiverModel', shareNeedsOwnerServe: true };
}
