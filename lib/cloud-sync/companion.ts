import { GENERATOR_VERSION } from '@/lib/html-doc/constants';
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
 *
 *  L-R6-1 (round 6) — the ship branch could DOWNGRADE. When BOTH envelopes match winnerMdHash the
 *  bodies are identical, so the only remaining difference is generatorVersion — and shipping the
 *  sender's blind overwrites a receiver model isFresh() accepts (lib/html-doc/read-model.ts) with one
 *  it rejects. The share flips from rendering to a 503 (app/s/[token]/route.ts) and the only recovery
 *  is an owner re-serve, which reserves and charges (lib/html-doc/serve-doc.ts) — the same
 *  user-re-spend class as H1 and H-R5-1, so it is guarded rather than tolerated.
 *  Reachability is not exotic: it needs GENERATOR_VERSION skew between the local checkout and the
 *  deployed cloud image (routine whenever the deploy lags the checkout) AND the loser already holding
 *  a model built from the winner's exact body — which is the normal state after any prior sync, since
 *  reconcile-class-a.ts falls through to a transfer on equal mdHash when currency or format disagree.
 *  So when both match, prefer the FRESHER by generatorVersion, and never write when the receiver is
 *  already current. (The report flag stays false on every both-match path: a version-skewed receiver
 *  was already not-fresh BEFORE this run, which is L-R6-2, deliberately out of scope here.)
 */
export function decideCompanion(args: {
  winnerMdHash: string;
  senderModel: ModelRead;
  receiverModel: ModelRead;
}): CompanionAction {
  const { winnerMdHash, senderModel, receiverModel } = args;

  const senderMatch = senderModel.kind === 'envelope'
    && senderModel.envelope.sourceMdHash === winnerMdHash ? senderModel.envelope : null;
  const receiverMatch = receiverModel.kind === 'envelope'
    && receiverModel.envelope.sourceMdHash === winnerMdHash ? receiverModel.envelope : null;

  // 1. BOTH sides hold a model built from the winning MD (L-R6-1). Same body, so generatorVersion is
  //    the whole difference: ship ONLY when it is a genuine upgrade, never a downgrade, and never a
  //    write that changes nothing.
  if (senderMatch && receiverMatch) {
    if (receiverMatch.generatorVersion === GENERATOR_VERSION) {
      return { kind: 'noop', shareNeedsOwnerServe: false }; // receiver already fresh — do not write
    }
    if (senderMatch.generatorVersion === GENERATOR_VERSION) {
      return { kind: 'ship', envelope: senderMatch }; // a real upgrade
    }
    return { kind: 'noop', shareNeedsOwnerServe: false }; // neither is current — both need a re-serve
  }

  // 2. Only the sender holds a model built from the winning MD → ship it (it supersedes whatever the
  //    receiver has, so the receiver's own state does not matter here).
  if (senderMatch) return { kind: 'ship', envelope: senderMatch };

  // 3. Nothing shippable, but the receiver already holds a model built from the WINNING MD — it is
  //    still valid. Do not destroy a paid artifact, and the share renders, so report nothing.
  if (receiverMatch) return { kind: 'noop', shareNeedsOwnerServe: false };

  // 4. The receiver's model is not known-good. The two axes now diverge, and DELIBERATELY:
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
