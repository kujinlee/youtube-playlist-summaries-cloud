import type { ModelEnvelope } from '@/lib/html-doc/model-store';

/** H1 (round 4) — the result of reading ONE side's model, as a TRI-state.
 *  `readModelEnvelope` collapses three different situations into one null: the envelope is absent,
 *  it is corrupt/schema-invalid, or its bytes could not be READ. The first two mean that side has
 *  nothing usable; the third means we simply do not know, and acting on it destroys a paid artifact.
 *  Which of those a null is depends on the backend — see BlobStore.provesAbsence — so the caller
 *  resolves it and hands the answer here.
 *
 *  H-R5-1 (round 5) — this is now read for BOTH sides, hence the neutral name. */
export type ModelRead =
  | { kind: 'envelope'; envelope: ModelEnvelope }
  | { kind: 'none' }      // that side PROVABLY has no usable model
  | { kind: 'unknown' };  // the read failed in a way that cannot prove absence

/** @deprecated round-4 name, kept so the tri-state reads naturally at the sender call site. */
export type SenderModelRead = ModelRead;

/** H-R5-1 (round 5) — `shareNeedsOwnerServe` is now carried on `noop` too, because it is a SEPARATE
 *  axis from the blob action and conflating the two is what produced this finding. The action answers
 *  "what do we do to the receiver's blob?"; the flag is a report-only count of shares that cannot
 *  render until the owner re-serves. §10 row 7 (neither side holds a model) is exactly the case where
 *  there is nothing to delete and yet the share IS unready — noop + true. */
export type CompanionAction =
  | { kind: 'ship'; envelope: ModelEnvelope }
  | { kind: 'deleteReceiverModel'; shareNeedsOwnerServe: true }
  | { kind: 'noop'; shareNeedsOwnerServe: boolean };

/** Ship the sender's model iff it was generated from the winning MD (§4.2); otherwise decide the
 *  receiver's fate from the RECEIVER's own envelope.
 *
 *  H1 (round 4) — `unknown` must not delete. Deleting the receiver's model costs a paid Gemini
 *  magazine transform to recover (runHtmlDoc → generateMagazineModel locally, or
 *  resolveMagazineModel → reserve_serve_model → spend_ledger on the cloud), and the delete is
 *  silent and sticky: it does not throw, so the caller advances the manifest baseline, and the next
 *  run's Class-A reconcile returns 'skip' and never revisits the companion step.
 *
 *  H-R5-1 (round 5) — round 4 made the SENDER read honest but left the whole decision keyed to it,
 *  which was wrong in both directions:
 *   (a) `unknown` → noop KEPT a provably-stale receiver model. The claimed safety net does not
 *       exist: the serve path's drift guard (lib/html-doc/read-model.ts) compares section TITLES and
 *       generatorVersion, never sourceMdHash, so a prose-only MD change — precisely the
 *       recency-tiebreak case — is served as fresh forever (dig-deeper merges the cached envelope
 *       without regenerating). And `unknown` is the COMMON outcome: a cloud video that was never
 *       HTML-served has no model blob, and the Supabase backend cannot prove that 404.
 *   (b) `none` → delete DESTROYED receiver models that were still valid, since the receiver was
 *       never consulted.
 *  The backend ambiguity was only ever about the SENDER. The receiver's staleness is provable
 *  independently: we hold winnerMdHash, so a receiver sourceMdHash that is present and DIFFERENT is
 *  definitively stale — its backing body no longer exists — with no ambiguity involved. So the
 *  sender read now decides only whether a REPLACEMENT can be shipped, and everything else is keyed
 *  to the receiver. Deleting a provably-stale model is not a money loss; deleting a matching one is.
 */
export function decideCompanion(args: {
  winnerMdHash: string;
  senderModel: ModelRead;
  receiverModel: ModelRead;
}): CompanionAction {
  const { winnerMdHash, senderModel, receiverModel } = args;

  // 1. The sender holds a model built from the winning MD → ship it (it supersedes whatever the
  //    receiver has, so the receiver's own state does not matter here).
  if (senderModel.kind === 'envelope' && senderModel.envelope.sourceMdHash === winnerMdHash) {
    return { kind: 'ship', envelope: senderModel.envelope };
  }

  // 2. Nothing shippable, but the receiver already holds a model built from the WINNING MD — it is
  //    still valid. Do not destroy a paid artifact, and the share renders, so report nothing.
  if (receiverModel.kind === 'envelope' && receiverModel.envelope.sourceMdHash === winnerMdHash) {
    return { kind: 'noop', shareNeedsOwnerServe: false };
  }

  // 3. The receiver's model is not known-good. The two axes now diverge, and DELIBERATELY:
  //
  //  - DELETE the blob only on PROOF. A receiver envelope whose sourceMdHash is present and differs
  //    is definitively stale — its backing body no longer exists — and needs no sender read to
  //    establish. Everything else is unprovable: `none`/`unknown` say nothing about a model we never
  //    read, and a legacy pre-1F-a envelope predates sourceMdHash entirely (the field is .optional()
  //    in model-store.ts), so it cannot be checked. Fail-safe-for-money: KEEP those. A possibly-stale
  //    cache is recoverable — any regeneration overwrites it, and the existing sourceSections /
  //    generatorVersion drift guard still catches the common legacy drift — but a deleted paid
  //    artifact costs a Gemini transform to rebuild.
  //
  //  - REPORT on doubt. shareNeedsOwnerServe is a report-only count (§10 row 7): "these shares may
  //    not render until you re-serve." It spends nothing and destroys nothing, so the harmful
  //    direction is UNDER-reporting — an anon visitor silently hitting a not-ready share. Note the
  //    receiver of a copyToCloud is always the Supabase store, which can never return `none`, so
  //    keying the flag to proof would make §10 row 7 unreportable in the direction it describes.
  const provablyStale = receiverModel.kind === 'envelope'
    && receiverModel.envelope.sourceMdHash !== undefined;
  if (provablyStale) return { kind: 'deleteReceiverModel', shareNeedsOwnerServe: true };
  return { kind: 'noop', shareNeedsOwnerServe: true };
}
