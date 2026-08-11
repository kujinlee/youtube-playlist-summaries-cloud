import type { SupabaseClient } from '@supabase/supabase-js';
import type { BlobStore } from '@/lib/storage/blob-store';
import type { Principal } from '@/lib/storage/principal';
import type { ParsedSummary, MagazineModel } from './types';
import { GENERATOR_VERSION } from './constants';
import { writeModelEnvelopeWithin, MODEL_KEY } from './model-store';
import { mdHash } from '@/lib/cloud-sync/content-hash';
import { readFreshMagazineModel, readTitleStableModel } from './read-model';
import { generateMagazineModelForServe } from '@/lib/gemini';
import { callRpcBounded } from '@/lib/serve-rpc';
import {
  SERVE_BUDGET, SERVE_RESERVE_RPC_TIMEOUT_MS, SERVE_PUT_TIMEOUT_MS, SERVE_SETTLE_RPC_TIMEOUT_MS,
  SERVE_SETTLE_ATTEMPTS,
} from '@/lib/serve-budget';
import type { SettleAttemptCount } from '@/lib/serve-budget';
import type { CloudGeminiCaps } from '@/lib/gemini-cost';
import { classifyGeminiFailure, releaseGateOpen } from '@/lib/gemini-failure';
import type { BillingLatch } from '@/lib/job-queue/billing-latch';
import {
  MAX_TRANSCRIBE_INPUT_TOKENS, MAX_TRANSCRIBE_OUTPUT_TOKENS, MAX_TRANSCRIPT_INPUT_BYTES,
  MAX_SUMMARY_OUTPUT_TOKENS, MAX_MAGAZINE_INPUT_TOKENS, MAX_MAGAZINE_OUTPUT_TOKENS,
} from '@/lib/gemini-cost';

/** Serve-side caps for the paid magazine transform (only the magazine fields are load-bearing;
 *  the rest satisfy the CloudGeminiCaps type). */
const SERVE_CAPS: CloudGeminiCaps = {
  transcribeInputTokens: MAX_TRANSCRIBE_INPUT_TOKENS,
  transcribeOutputTokens: MAX_TRANSCRIBE_OUTPUT_TOKENS,
  transcriptInputBytes: MAX_TRANSCRIPT_INPUT_BYTES,
  summaryOutputTokens: MAX_SUMMARY_OUTPUT_TOKENS,
  magazineInputTokens: MAX_MAGAZINE_INPUT_TOKENS,
  magazineOutputTokens: MAX_MAGAZINE_OUTPUT_TOKENS,
};

export type ResolveResult =
  | { status: 'ok'; model: MagazineModel; stale?: boolean }
  | { status: 'busy' }
  | { status: 'attempts_exhausted' }
  | { status: 'at_capacity' }
  | { status: 'over_budget' }
  | { status: 'denied' };

export async function resolveMagazineModel(args: {
  supabaseClient: SupabaseClient;
  blobStore: BlobStore;
  principal: Principal;
  playlistId: string;
  videoId: string;
  base: string;
  parsed: ParsedSummary;
  language: 'en' | 'ko';
  /** Stage 3 (§4.2): the MD BODY this model is generated from (NOT the blob key) — hashed
   *  into the envelope's sourceMdHash on a fresh materialize. Optional for back-compat with
   *  callers that pre-date this signal (sourceMdHash is an optional envelope field); the
   *  real production caller (serve-summary-core.ts) always supplies it. */
  mdBody?: string;
  signal?: AbortSignal;
}): Promise<ResolveResult> {
  const { supabaseClient, blobStore, principal, playlistId, videoId, base, parsed, language, mdBody, signal } = args;
  const titles = parsed.sections.map((s) => s.title);
  // `reserve_serve_model`'s own key formula (`0012_serve_model_charge.sql:53`). Every money log
  // below carries it, because round-3 review H-R3-1 measured that not one of them named an owner,
  // a document, a day or a token — so an operator reading `REFUND NOT APPLIED` had nothing to look
  // up in any table. An alarm you cannot attribute is not much better than no alarm.
  const docKey = `${playlistId}/${videoId}`;

  const fresh = await readFreshMagazineModel({ blobStore, principal, base, titles });
  if (fresh.status === 'ok') return { status: 'ok', model: fresh.model }; // B1 — no Gemini, no reserve

  // ── MONEY GUARD — never spend on an UNPROVABLE read.
  // `readFreshMagazineModel` returns not_ready for three different situations: the model is absent,
  // it is present but drifted/stale-version, or **it could not be read**. The first two justify
  // regenerating; the third does not — the model may be sitting in the bucket, already paid for.
  // `blobStore.get` collapses every Storage failure (5xx, timeout, RLS denial, transport error) into
  // the same `null` as a genuine 404, so without this probe a transient blip re-reserves and
  // re-generates: measured 6¢ → 12¢ with attempt_count 1 → 2 in
  // tests/integration/serve-model-unreadable.test.ts.
  // `tryGet` distinguishes them (Supabase reports a missing object with statusCode "404"). On
  // `unreadable` we return `busy` — the same transient, retryable status the single-flight branch
  // uses — instead of paying. Absent and drifted still fall through and materialize as before.
  const probe = await blobStore.tryGet(principal, MODEL_KEY(base));
  if (!probe.ok && probe.reason === 'unreadable') return { status: 'busy' };

  // Absent / drifted / stale-version → materialize under the reserve RPC.
  const reserve = await callRpcBounded(
    (abortSignal) => supabaseClient
      .rpc('reserve_serve_model', { p_playlist_id: playlistId, p_video_id: videoId })
      .abortSignal(abortSignal),
    SERVE_RESERVE_RPC_TIMEOUT_MS, 'reserve_serve_model',
  );
  if (!reserve.ok) {
    if (reserve.reason === 'error') throw reserve.cause;   // unchanged from `if (error) throw error`
    // TIMEOUT. The transaction is NOT rolled back, so what may exist now is an EMPTY PAID LEASE:
    // charged, an attempt burned, no producer. Retries before expiry see in_flight although nobody
    // is generating. Loud, because that is an infrastructure alarm, not a user error.
    console.error(
      `[serve-model] reserve timed out for owner=${principal.id} ${docKey} — possible empty paid lease`,
    );
    return { status: 'busy' };
  }
  const row = (reserve.data as Array<{ status: string; release_token: string | null }> | null)?.[0];   // table-return → data[0]
  const reserveStatus = row?.status;
  const releaseToken = row?.release_token ?? null;
  switch (reserveStatus) {
    case 'denied': return { status: 'denied' };
    case 'in_flight': {
      // Single-flight: another attempt holds the lease. Serve the model if it landed meanwhile, else busy.
      const now = await readFreshMagazineModel({ blobStore, principal, base, titles });
      return now.status === 'ok' ? now : { status: 'busy' };
    }
    case 'attempts_exhausted': return { status: 'attempts_exhausted' };
    case 'at_capacity': return { status: 'at_capacity' };
    case 'owner_over_budget': {
      // Spec D5: serve the title-stable stale rendering instead of failing; else 503.
      const staleRead = await readTitleStableModel({ blobStore, principal, base, titles });
      return staleRead.status === 'ok'
        ? { status: 'ok', model: staleRead.model, stale: true }
        : { status: 'over_budget' };
    }
    case 'reserved': break;
    default: throw new Error(`reserve_serve_model: unexpected status ${String(reserveStatus)}`);
  }

  // We hold the lease and this attempt was charged. Generate → upsert (overwrite) → serve.
  // The model uses writeModelEnvelope (plain `put` → `upload(upsert:true)`), NOT staged→promote: a
  // regenerated model on drift / version-bump must OVERWRITE the stale blob so the doc self-heals
  // (create-if-absent promote could never replace it → re-reserve + re-charge every view until K, then 503).
  // On a terminal outcome (success or throw) we settle the reservation via settle_serve_model: success
  // keeps the charge (released=false) and clears the per-attempt token; a throw refunds ONLY a
  // positively-not-metered class-A failure under an open gate — same rule as the generation worker-runner
  // (Task 10). Anything else (metered, non-class-A, gate closed) keeps the charge — over-count is safe,
  // under-count is the bug.
  const billing: BillingLatch = { metered: false };
  try {
    const model = await generateMagazineModelForServe(
      parsed.sections.map((s) => ({ title: s.title, prose: s.prose })),
      language,
      SERVE_BUDGET,                                   // REQUIRED — cannot be omitted
      { caps: SERVE_CAPS, signal, billing },
    );
    await writeModelEnvelopeWithin(SERVE_PUT_TIMEOUT_MS, principal, base, {
      sourceMd: parsed.sourceMd ?? `${base}.md`,
      generatedAt: new Date().toISOString(),
      sourceSections: titles,
      generatorVersion: GENERATOR_VERSION,
      model,
      // Hash the MD BODY, not the key — see the `mdBody` param doc above (§4.2).
      ...(mdBody !== undefined ? { sourceMdHash: mdHash(mdBody) } : {}),
    }, blobStore);
    // A lost KEEP is benign — the charge is already correct and only a per-attempt token is left
    // behind — but it is still an infrastructure signal worth seeing.
    if (releaseToken) {
      const outcome = await settleBounded(supabaseClient, releaseToken, false, docKey);
      if (outcome !== 'applied') {
        console.warn(
          `[serve-model] keep-settle ${outcome} for owner=${principal.id} ${docKey}; `
          + 'the charge stands, the token was not cleared',
        );
      }
    }
    return { status: 'ok', model };
  } catch (err) {
    // Same rule as generation: refund only a positively-not-metered class-A failure.
    const released = releaseGateOpen()
      && classifyGeminiFailure(err, signal) === 'release'
      && !billing.metered;
    // A lost REFUND is money: the owner was charged 6¢ for work that failed and the ledger still
    // holds it. Distinguish it from a lost keep AT THE POINT WHERE THE DISTINCTION HAS A COST, or
    // the refund mechanism can stop working in production and emit nothing at all.
    //
    // Three outcomes, three different things to say. `error` is reserved for the one case where we
    // KNOW money is stranded; an alarm that also fires on "we are not sure" trains its reader to
    // ignore it, which is how the round-1 signal would have died a second death.
    if (releaseToken) {
      const outcome = await settleBounded(supabaseClient, releaseToken, released, docKey);
      // A KEEP that did not apply is the same event here as on the success path, and was silent on
      // this one only because the branch below is written around `released` (round-3 M-R3-2).
      if (!released && outcome !== 'applied') {
        console.warn(
          `[serve-model] keep-settle ${outcome} for owner=${principal.id} ${docKey}; `
          + 'the charge stands, the token was not cleared',
        );
      } else if (released && outcome === 'refused') {
        console.error(
          `[serve-model] REFUND NOT APPLIED for owner=${principal.id} ${docKey} `
          + `token=${releaseToken} — the owner was charged for a failed generation`,
        );
      } else if (released && outcome === 'indeterminate') {
        // Name the check that ACTUALLY resolves this, and name the row. An earlier draft of this
        // line said "reconcile against ledger_audit" — but settle_serve_model only writes
        // ledger_audit on a release_underflow anomaly, so it is EMPTY in precisely the case this
        // message is about. That is round-1 H2's defect in miniature: a detection pointing at
        // nothing. A committed settle clears the token (`set reserved_cents = 0, release_token =
        // null`, 0020_reservation_release.sql:278), so the token is the signal that exists.
        console.warn(
          `[serve-model] refund outcome UNKNOWN for owner=${principal.id} ${docKey} `
          + `token=${releaseToken} — a settle attempt went unanswered and may have committed. `
          + `RESOLVE: select * from ledger_audit where kind = 'serve_settle' and note like `
          + `'${releaseToken}:%' — a row means it landed (migration 0025).`,
        );
      }
    }
    throw err;
  }
}

/**
 * What a settle actually did. THREE values, because a boolean here carried three meanings and the
 * alarm built on it fired on the wrong one (round-2 review H-R2-2).
 *
 *   applied        the database says it settled — the only outcome that may be reported as success
 *   refused        the database said no on FIRST contact: the token is stale, duplicated, forged, or
 *                  the lease was reclaimed. Nothing settled, and nothing will
 *   indeterminate  we never got a trustworthy answer. An attempt timed out or errored, and this
 *                  path already knows such a call CAN commit server-side (`serve-doc.ts` reserve
 *                  branch, and backlog #28, both rest on exactly that). A later no-op reply may
 *                  therefore be the idempotent echo of our own success rather than a refusal
 *
 * Collapsing the last two is what made `REFUND NOT APPLIED` fire on refunds that HAD applied. The
 * deliverable of the round-1 fix was a trustworthy signal; an alarm that cries wolf on the only
 * path it watches is worth no more than the silence it replaced.
 */
type SettleOutcome = 'applied' | 'refused' | 'indeterminate';

/**
 * Settle the reservation under a bounded wait, retrying ONLY the refund.
 *
 * Bounding the settle is not free. Before this, an unbounded await eventually landed; a bounded one
 * can give up with the refund unapplied — real money left on the ledger. So the release path gets a
 * second attempt and a lost keep does not: `released=false` merely clears a per-attempt token whose
 * charge is already correct, while `released=true` is the refund itself.
 *
 * Never throws: a failed settle must not mask the original error on the throw path.
 */
async function settleBounded(
  supabaseClient: SupabaseClient, token: string, released: boolean, docKey: string,
): Promise<SettleOutcome> {
  // An unapplied REFUND is real money left on the ledger; a lost KEEP is already correct.
  // TYPED, not inferred (round-5 review H-R5-1). `const attempts = released ? … : 1` is an inference
  // site: it widens to `number`, so `SERVE_SETTLE_ATTEMPTS + SERVE_SETTLE_ATTEMPTS` assigns to it
  // happily — measured at tsc exit 0 with all 2657 tests green, spending 4 settles against a sum
  // that pays for 2. Naming the type is what makes the arithmetic unrepresentable; branding the
  // constant alone does not, because nothing was checking the local.
  const attempts: SettleAttemptCount | 1 = released ? SERVE_SETTLE_ATTEMPTS : 1;
  // Once ANY attempt fails to return a trustworthy answer, every later reply is ambiguous: the RPC
  // may have committed after we stopped listening. Conservative on purpose — over-reporting
  // "indeterminate" costs an operator one reconciliation; under-reporting it means claiming a
  // refund was refused when it was applied.
  let anAttemptMayHaveCommitted = false;
  for (let i = 0; i < attempts; i++) {
    // `boolean | null`, not `boolean`: postgrest types data as null on its failure branch, and
    // asserting a non-null the client never promises is the same absent-vs-failed conflation this
    // function exists to remove — one level up, in the types. Hence the explicit `=== true` below.
    const out = await callRpcBounded<boolean | null>(
      (abortSignal) => supabaseClient
        .rpc('settle_serve_model', { p_token: token, p_released: released })
        .abortSignal(abortSignal),
      SERVE_SETTLE_RPC_TIMEOUT_MS, `settle_serve_model(released=${released})`,
    );
    if (out.ok) {
      // `ok` means the ROUND TRIP succeeded, not that the settle happened. settle_serve_model
      // `returns boolean` and answers `false` for a no-op — `if not found then return false`
      // (0020_reservation_release.sql:281). Measured against the live database in
      // tests/integration/settle-rpc-shape.test.ts: success is `true`, a no-op is `false`, and
      // neither is an error.
      if (out.data === true) return 'applied';
      // `false` is the documented no-op. ANYTHING ELSE — `null` from postgrest's failure branch, or
      // a shape a future client version returns — is an answer we do not recognise, and an
      // unrecognised answer is not a refusal (round-3 review L-R3-3). Calling it one would put the
      // loudest money alarm behind the least understood branch.
      if (out.data !== false) {
        console.warn(
          `[serve-model] settle(released=${released}) returned an UNRECOGNISED value for ${docKey} `
          + `token=${token}: ${JSON.stringify(out.data)} — treating as indeterminate`,
        );
        return 'indeterminate';
      }
      // A no-op AFTER one of our own attempts went unanswered is exactly what an idempotent
      // re-settle looks like — the second call cannot distinguish "someone else's stale token" from
      // "the row my own timed-out attempt already cleared". Do not spend the retry either way: a
      // genuinely stale token will not become valid.
      if (anAttemptMayHaveCommitted) return 'indeterminate';
      console.warn(
        `[serve-model] settle(released=${released}) REFUSED by the database for ${docKey} `
        + `token=${token} — stale, duplicated, or the lease was reclaimed; nothing was settled`,
      );
      return 'refused';
    }
    anAttemptMayHaveCommitted = true;
    console.warn(
      `[serve-model] settle attempt ${i + 1}/${attempts} failed for ${docKey} token=${token}: ${out.reason}`,
    );
  }
  return 'indeterminate';   // no attempt ever answered
}
