import path from 'path';
import fs from 'fs';
import { NextResponse } from 'next/server';
import { isCloudBackend, isPlaylistUuid } from '@/lib/http/request-scope';
import { assertVideoId } from '@/lib/index-store';
import { getPrincipal, getStorageBundle } from '@/lib/storage/resolve';
import { fixSummary, extractQuickView } from '@/lib/gemini';
import { stripQuickViewCallout, insertQuickViewCallout } from '@/lib/pipeline';
import { logError, errorSummary } from '@/lib/dev-logger';
import { mdHash } from '@/lib/cloud-sync/content-hash';
import type { Video } from '@/types';
import { MAX_CORRECTIONS_CHARS } from '@/lib/corrections/apply-core';
import { NonRetryableError } from '@/lib/job-queue/errors';
import { cookies } from 'next/headers';
import { createServerSupabase, type CookieStore } from '@/lib/supabase/server';
import { loadSummaryForServe } from '@/lib/html-doc/serve-summary-core';
import { applyCorrection, CORRECTION_CAPS, meteredCorrectionCents } from '@/lib/corrections/apply-core';
import type { UsageMeter } from '@/lib/gemini';
import { raceRpc } from '@/lib/serve-rpc';

/** The wait on EACH correction RPC — the allowance read before the paid call, the spend record after
 *  it (round 1, M1/M3). Raced against our own timer by `raceRpc`, because a postgrest abort
 *  RETURNS rather than throws (serve-rpc.ts, `RpcOutcome`). PROVISIONAL, like SERVE_RESERVE_RPC_TIMEOUT_MS:
 *  one round trip, revise from observed p99. */
export const CORRECTION_RPC_TIMEOUT_MS = 3_000;
import { StructuralValidationError, type StructuralFailureReason } from '@/lib/corrections/structural-validation';

/** What the reader is told when the model's corrected document failed structural validation
 *  (backlog #63). The validator's own message is for the log — it names section indices and parsed
 *  tuples the reader cannot act on. Typed by reason so a new reason is a compile error here, not a
 *  raw string in the panel. 422, not 500: nothing failed on the server, and nothing was saved. */
export const STRUCTURAL_REFUSALS: Record<StructuralFailureReason, { code: string; error: string }> = {
  'missing-frontmatter': {
    code: 'structure-missing-frontmatter',
    error: 'The corrected summary came back without its metadata header, so it was not saved. Please try again.',
  },
  'missing-h1': {
    code: 'structure-missing-h1',
    error: 'The corrected summary came back without its title, so it was not saved. Please try again.',
  },
  'section-count': {
    code: 'structure-section-count',
    error: 'The correction added or removed a section, so it was not saved. Corrections can change wording, not which sections exist.',
  },
  'section-title': {
    code: 'structure-section-title',
    error: 'The correction changed a section heading, so it was not saved. Corrections cannot rename sections.',
  },
  'section-timestamp': {
    code: 'structure-section-timestamp',
    error: 'The correction changed a section\'s video timestamp link, so it was not saved. Please try again.',
  },
};

/** The whole handler, LOCAL and CLOUD, lifted out of app/ so the route file holds no backend
 *  fork, no UUID literal and no serveLocal/serveCloud names — see lib/http/request-scope.ts for
 *  which architecture findings that repairs and why. */
export async function handleRegenerate(request: Request, videoId: string): Promise<Response> {
  return isCloudBackend() ? serveCloud(request, videoId) : serveLocal(request, videoId);
}

async function serveLocal(request: Request, videoId: string): Promise<Response> {

  const body = await request.json().catch(() => null) as Record<string, unknown> | null;
  const outputFolder = body?.outputFolder;
  const corrections = body?.corrections;

  if (!outputFolder || typeof outputFolder !== 'string') {
    return NextResponse.json({ error: 'outputFolder is required' }, { status: 400 });
  }

  if (corrections !== undefined && typeof corrections !== 'string') {
    return NextResponse.json({ error: 'corrections must be a string' }, { status: 400 });
  }

  // Corrections are the ONLY unbounded input to a paid call on this route. The 1,000 limit lives in
  // the browser (CorrectionsPanel.tsx:105) and §5.3 concedes any authenticated client can reach this
  // handler, so enforce it where it binds. Code points, not UTF-16 units — see MAX_CORRECTIONS_CHARS.
  if (typeof corrections === 'string' && [...corrections].length > MAX_CORRECTIONS_CHARS) {
    return NextResponse.json(
      { error: `corrections must be ${MAX_CORRECTIONS_CHARS} characters or fewer`, code: 'corrections-too-long' },
      { status: 400 },
    );
  }

  let principal;
  try {
    principal = getPrincipal(outputFolder);
    assertVideoId(videoId);
  } catch {
    return NextResponse.json({ error: 'invalid request' }, { status: 400 });
  }

  const { metadataStore: store } = getStorageBundle();
  const index = await store.readIndex(principal);
  const video = index.videos.find((v) => v.id === videoId);

  if (!video) {
    return NextResponse.json({ error: 'video not found' }, { status: 404 });
  }

  if (!video.summaryMd) {
    return NextResponse.json({ error: 'no summary file for this video' }, { status: 422 });
  }

  try {
    const mdPath = path.join(outputFolder, video.summaryMd);
    let mdContent = await fs.promises.readFile(mdPath, 'utf-8');

    // Save corrections BEFORE the Gemini call so a page refresh shows the latest text even if
    // Gemini fails.
    //
    // updateVideoAnnotations, not updateVideoFields (spec §4.1). Two reasons:
    //  - `updateVideoFields(p, id, { corrections: undefined })` is a NO-OP on Supabase — `undefined`
    //    is dropped by JSON serialization before merge_video_data ever sees it, after which the
    //    route stamped mdHash('') over a row that still held corrections.
    //  - the RPC enforces the allowlist and `owner_id = auth.uid()` in SQL, and returns { found }.
    //
    // READ BEFORE WRITE, and issue NO CALL when nothing changed. Both backends stamp
    // annotationsEditedAt for every Class-B key set OR cleared (0021:33-43;
    // local-metadata-store.ts:139-159), so "only when it changed" cannot live in the store. A no-op
    // press must not beat a real remote edit in Class-B reconciliation — including the
    // clear-an-already-empty case, which would otherwise stamp an edit that did not happen.
    const trimmedCorrections = typeof corrections === 'string' ? corrections.trim() : undefined;
    const storedCorrections = video.corrections ?? '';
    if (trimmedCorrections && trimmedCorrections !== storedCorrections) {
      const { found } = await store.updateVideoAnnotations(
        principal, videoId, { corrections: trimmedCorrections }, [],
      );
      if (!found) return NextResponse.json({ error: 'video not found' }, { status: 404 });
    } else if (corrections === '' && storedCorrections !== '') {
      const { found } = await store.updateVideoAnnotations(principal, videoId, {}, ['corrections']);
      if (!found) return NextResponse.json({ error: 'video not found' }, { status: 404 });
    }

    // Apply text corrections if provided (works on prose only — callout is stripped first)
    const stripped = stripQuickViewCallout(mdContent);
    const fixed = trimmedCorrections
      ? (await fixSummary(stripped, trimmedCorrections, { signal: request.signal })).text
      : stripped;

    // Re-extract tldr/takeaways from corrected content and re-insert callout
    const { tldr, takeaways } = await extractQuickView(fixed);
    const updatedContent = insertQuickViewCallout(fixed, tldr, takeaways, video.tags ?? []);

    // WRITE ONLY WHEN A CORRECTION WAS APPLIED (spec §2, round-5 Blocking). On a bare press
    // `fixed === stripped`, so the prose is unchanged — but `extractQuickView` above is a
    // non-deterministic LLM call and `insertQuickViewCallout` splices its output into the hashed
    // region, so writing would move `mdHash(body)`. Under §2's option (e) that invalidates the
    // magazine model and books a ~6¢ regeneration for a press that applied nothing. Measured: the
    // callout sits in the preamble `parseSections` discards (parse.ts:45-47), so it can change no
    // input the model is built from — the regeneration would recompute an identical result.
    if (trimmedCorrections) {
      await fs.promises.writeFile(mdPath, updatedContent, 'utf-8');
    }

    // Stage 3 (§5.1/§5.7) + spec §4.3. Stamp corrections-currency ONLY when fixSummary actually ran,
    // and stamp it against the REQUEST's corrections — the quantity that was applied.
    //
    // The old rule (`:77-79`) fell back to the STORED value on a bare press, which flipped a
    // corrections-stale row to current with no Gemini call. `mdCorrectionsHash` is the sole input to
    // reconcileClassA's currency predicate (reconcile-class-a.ts:8), and sync-run.ts:358 writes
    // `corrections` without touching the body, so one bare press permanently discarded a pending
    // correction. Omitting the field preserves whatever the row already claimed.
    //
    // An explicit clear still stamps mdHash('') — unchanged, imperfect (the body may still carry
    // previously applied corrections) and out of scope for slice A.
    //
    // NOTE: this write carries MD-currency fields, not a Class-B key, so it must NOT bump
    // annotationsEditedAt (the earlier updateVideoFields({ corrections }) call above is the
    // Class-B write that stamps annotationsEditedAt.corrections).
    const patch: Partial<Video> = { tldr, takeaways, summaryHtml: null };
    if (trimmedCorrections) {
      patch.mdGeneratedAt = new Date().toISOString();   // the body DID change
      patch.mdCorrectionsHash = mdHash(trimmedCorrections);
    } else if (corrections === '') {
      patch.mdCorrectionsHash = mdHash('');
    }

    await store.updateVideoFields(principal, videoId, patch);

    return NextResponse.json({
      outcome: trimmedCorrections ? 'applied' : 'no-corrections',
      tldr,
      takeaways,
      corrections: trimmedCorrections,
      summaryHtml: null,
    });
  } catch (err) {
    logError(`regenerate:${videoId}`, err);
    // The preflight refusal is a CLIENT-side fact about this document, not a server fault: the
    // summary is larger than the correction cap can accept and no retry will change that. A 500
    // would tell the user to try again forever. Matched on the NonRetryableError class AND the
    // message prefix that assertCorrectionInputWithinCap emits, so an unrelated NonRetryableError
    // from elsewhere in the graph still reports 500.
    if (err instanceof NonRetryableError && err.message.startsWith('correction input ')) {
      return NextResponse.json(
        { error: 'This summary is too long to correct', code: 'summary-too-large' },
        { status: 413 },
      );
    }
    return NextResponse.json({ error: errorSummary(err) }, { status: 500 });
  }
}

async function serveCloud(request: Request, videoId: string): Promise<Response> {
  const { searchParams } = new URL(request.url);

  const cookieStore = (await cookies()) as unknown as CookieStore;
  const supabase = createServerSupabase(cookieStore);
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: 'authentication required' }, { status: 401 });

  const playlistId = searchParams.get('playlist');
  if (!isPlaylistUuid(playlistId)) {
    return NextResponse.json({ error: 'invalid playlist' }, { status: 400 }); // before any DB call
  }

  const body = await request.json().catch(() => null) as Record<string, unknown> | null;
  if (body && 'outputFolder' in body) {
    return NextResponse.json({ error: 'outputFolder not valid on this backend' }, { status: 400 });
  }
  const corrections = body?.corrections;
  if (corrections !== undefined && typeof corrections !== 'string') {
    return NextResponse.json({ error: 'corrections must be a string' }, { status: 400 });
  }
  if (typeof corrections === 'string' && [...corrections].length > MAX_CORRECTIONS_CHARS) {
    return NextResponse.json(
      { error: `corrections must be ${MAX_CORRECTIONS_CHARS} characters or fewer`, code: 'corrections-too-long' },
      { status: 400 },
    );
  }

  // Filled by fixSummary as each paid attempt returns, and read in the `finally` below — so a press
  // that throws AFTER paying still records what it paid (backlog #62).
  const meter: UsageMeter = { attempts: [] };

  // EVERYTHING BELOW IS INSIDE THE TRY. On the local branch `getStorageBundle()` sits OUTSIDE it,
  // so a missing client 500s instead of returning an error.
  try {
    // ⚠ CALL THE EXISTING LOADER — DO NOT HAND-ROLL THIS. An earlier draft transcribed the auth
    // skeleton from `review/route.ts:106-152` and reproduced only the owner check and the blob
    // read. `review/route.ts` writes annotations and never touches a blob, so it carries none of
    // the guards a blob read needs. `loadSummaryForServe` (serve-summary-core.ts:34) is the read
    // path, and it does ALL of this in one call:
    //
    //   resolveOwnedPlaylistKey → 404      getPrincipalFromSession + getStorageBundle
    //   readIndex + video lookup → 404     artifacts.summaryMd.status === 'committed' → 503
    //   status !== 'promoted' → 404        key = artifact.key ?? video.summaryMd, else 404
    //   assertCloudSummaryMdKey → 409      blobStore.get → null → 409 'repair needed'
    //
    // The status gate is the one a hand-rolled version drops, and it matters MORE here than on the
    // serve path: correcting a `committed` artifact writes to a blob a worker promotion is still
    // finalizing. The `!mdBytes` → 409 guard is also its (blobStore.get collapses RLS denials and
    // transport faults into the same null as a genuine 404, blob-store.ts:57-66 — treating null as
    // "no content" would hand Gemini an empty string and overwrite a real document).
    const load = await loadSummaryForServe(supabase, { videoId, playlistId, userId: user.id });
    if (!load.ok) return NextResponse.json({ error: load.error }, { status: load.status });

    const { principal, bundle, video, mdKey, mdBytes } = load;
    const { metadataStore: store, blobStore } = bundle;
    const mdContent = mdBytes.toString('utf-8');

    const trimmedCorrections = typeof corrections === 'string' ? corrections.trim() : undefined;

    // ⚠ THE DAILY LIMIT REFUSES THE PRESS, BEFORE ANY PAID CALL (round 1, H1 — both halves). 0026's
    // per-owner limit lives inside record_correction_spend, so on its own it refused only the
    // BOOKKEEPING: from press N+1 Gemini was billed and nothing was written anywhere. Checked before
    // the annotation write too, so a refused press changes nothing. Fails CLOSED — no readable
    // allowance, no paid call.
    // ⚠ A CHECK, NOT A RESERVATION — and the window is UNBOUNDED (round 2, Claude M1): K concurrent
    // presses at N-1 all pass and all pay; 0026 then refuses K-1 recordings, raising BEFORE its
    // spend_ledger write, so those presses reach neither counter; and nothing rate-limits this route,
    // so K is the client's choice. Closing it is reserve/settle — backlog #61.
    if (trimmedCorrections) {
      const allowance = await readCorrectionAllowance(supabase);
      if (!allowance.ok) {
        return NextResponse.json(
          { error: 'Corrections are temporarily unavailable. Please try again in a moment.', code: 'correction-limit-unavailable' },
          { status: 503 },
        );
      }
      if (allowance.calls >= allowance.maxCalls) {
        return NextResponse.json(
          { error: 'You have reached today\'s limit for corrections. Please try again tomorrow.', code: 'correction-limit-reached' },
          { status: 429 },
        );
      }
    }

    const storedCorrections = video.corrections ?? '';
    if (trimmedCorrections && trimmedCorrections !== storedCorrections) {
      const { found } = await store.updateVideoAnnotations(principal, videoId, { corrections: trimmedCorrections }, []);
      if (!found) return NextResponse.json({ error: 'video not found' }, { status: 404 });
    } else if (corrections === '' && storedCorrections !== '') {
      const { found } = await store.updateVideoAnnotations(principal, videoId, {}, ['corrections']);
      if (!found) return NextResponse.json({ error: 'video not found' }, { status: 404 });
    }

    let tldr: string;
    let takeaways: string[];

    if (trimmedCorrections) {
      const applied = await applyCorrection({
        md: mdContent,
        corrections: trimmedCorrections,
        tags: video.tags ?? [],
        signal: request.signal,
        caps: CORRECTION_CAPS,
        meter,
      });
      tldr = applied.tldr;
      takeaways = applied.takeaways;
      // `put`, NEVER writeArtifact. writeArtifact goes putStaged → promote, and promote is
      // create-if-absent (supabase-blob-store.ts:120-123): the key never changes on a correction, so
      // the final object always exists and the corrected body would be silently discarded while the
      // row was stamped `promoted`. That is backlog #22, and it applies to slice A too.
      // `mdKey` from loadSummaryForServe, NOT `video.summaryMd`: the loader prefers
      // `artifacts.summaryMd.key` and falls back to the top-level field, so writing to
      // `video.summaryMd` could target a blob the artifact record does not govern.
      await blobStore.put(principal, mdKey, Buffer.from(applied.content, 'utf-8'), 'text/markdown');
    } else {
      // Bare press or explicit clear: quick-view still refreshes (spec §3), but NOTHING is written to
      // the blob — the prose did not change and a rewritten callout would move the body hash, which
      // under §2 option (e) books a ~6¢ magazine regeneration for a press that applied nothing.
      const qv = await extractQuickView(stripQuickViewCallout(mdContent), CORRECTION_CAPS);
      tldr = qv.tldr;
      takeaways = qv.takeaways;
    }

    const patch: Partial<Video> = { tldr, takeaways, summaryHtml: null };
    if (trimmedCorrections) {
      patch.mdGeneratedAt = new Date().toISOString();
      patch.mdCorrectionsHash = mdHash(trimmedCorrections);
    } else if (corrections === '') {
      patch.mdCorrectionsHash = mdHash('');
    }
    await store.updateVideoFields(principal, videoId, patch);

    return NextResponse.json({
      outcome: trimmedCorrections ? 'applied' : 'no-corrections',
      tldr,
      takeaways,
      corrections: trimmedCorrections,
      summaryHtml: null,
    });
  } catch (err) {
    logError(`regenerate:cloud:${videoId}`, err);
    if (err instanceof NonRetryableError && err.message.startsWith('correction input ')) {
      return NextResponse.json(
        { error: 'This summary is too long to correct', code: 'summary-too-large' },
        { status: 413 },
      );
    }
    if (err instanceof StructuralValidationError) {
      const { code, error } = STRUCTURAL_REFUSALS[err.reason];
      return NextResponse.json({ error, code }, { status: 422 });
    }
    return NextResponse.json({ error: errorSummary(err) }, { status: 500 });
  } finally {
    // AFTER the response is decided, on EVERY path: success, structural refusal, exhausted retries,
    // a failed blob write, an abort. On success this still runs after `blobStore.put`.
    await recordCorrectionSpend(supabase, meter, user.id, videoId);
  }
}

type Allowance = { ok: true; calls: number; maxCalls: number } | { ok: false };

/** Today's recorded correction count for the signed-in owner and 0026's per-owner call limit
 *  (migration 0028; it also returns `max_cents`, which the route no longer needs since round 2
 *  removed the split). Anything other than two integers — an error, a timeout, a malformed row — is `ok: false`,
 *  which the caller treats as a refusal: a missing limit must never read as "no limit". */
async function readCorrectionAllowance(supabase: ReturnType<typeof createServerSupabase>): Promise<Allowance> {
  // No `.abortSignal(signal)`: on a timeout the read is simply abandoned, which costs nothing.
  const out = await raceRpc<unknown>(
    () => supabase.rpc('correction_allowance'), CORRECTION_RPC_TIMEOUT_MS, 'correction_allowance',
  );
  if (!out.ok) {
    console.error(`[correction-allowance] UNREADABLE (${out.reason}) — refusing the press`);
    return { ok: false };
  }
  const d = out.data as { calls?: unknown; max_calls?: unknown } | null;
  if (!d || !Number.isInteger(d.calls) || !Number.isInteger(d.max_calls)) {
    console.error(`[correction-allowance] MALFORMED ${JSON.stringify(d)} — refusing the press`);
    return { ok: false };
  }
  return { ok: true, calls: d.calls as number, maxCalls: d.max_calls as number };
}

/**
 * Record ACTUAL spend, after the paid call settled (spec §5.2). Post-hoc, not pre-authorised: the
 * guardrails see this on the NEXT decision, which is the accepted trade (reserve/settle is backlog #61).
 *
 * ⚠ RUNS WHATEVER THE OUTCOME (backlog #62). It used to run only after a successful correction, and
 * this RPC is the sole writer of both the per-owner-per-day counter and the `spend_ledger` the daily
 * cap watches — so a correction made to fail deterministically spent in a loop while every guardrail
 * read zero. Measured in production 2026-08-24: a failed press left 0 rows and the ledger unmoved.
 *
 * Every METERED attempt is charged — a returned one at its reported usage (a missing field at its
 * bound), and one cut off in flight by an abort or timeout at the per-attempt bound
 * (`meteredCorrectionCents`, UsageMeter). So a press with attempts always records, never 0¢ and
 * never nothing (round 1 Codex H2, round 2 Claude High).
 *
 * ONE CALL PER PRESS, ALWAYS (round 2, Codex High). 0026 checks `correction_max_cents` per RPC call
 * and REJECTS the whole amount above it. Round 1 split an over-ceiling press across calls, but each
 * call spends one of the owner's daily slots, so at calls = N-1 a [3,3,1] press recorded 3¢ and lost
 * 4. Removed. The ceiling is instead PROVED to cover the worst press —
 * (FIX_SUMMARY_RETRIES + 1) × CORRECTION_WORST_ATTEMPT_CENTS = 9¢ against 0026's default 12¢ —
 * by tests/lib/corrections/correction-ceiling.test.ts (the migration's declared default) and by the
 * cap-soundness case in record-correction-spend.int.test.ts (the live config row). A change to the
 * caps, the prices, the retries or the ceiling turns one of those red instead of losing money here.
 *
 * ⚠ A FAILED RECORDING MUST NOT FAIL THE REQUEST — and it cannot: it NEVER THROWS, and the call is
 * bounded by CORRECTION_RPC_TIMEOUT_MS, so a hung ledger delays the response by at most that, never
 * holds it. The money is already spent; on success the corrected body is already durable, and a 500
 * would invite the user to press again, paying twice to fix a bookkeeping error. That includes
 * hitting the per-owner daily bound. Log loudly instead — there is no durable retry of a failed
 * recording. A timed-out call is not aborted, so it may still land — the safe direction for a
 * record of spend that already happened.
 */
async function recordCorrectionSpend(
  supabase: ReturnType<typeof createServerSupabase>, meter: UsageMeter, ownerId: string, videoId: string,
): Promise<void> {
  if (meter.attempts.length === 0) return;   // bare press, preflight refusal, early 4xx: nothing paid
  const { cents, estimated } = meteredCorrectionCents(meter);
  if (estimated > 0) {
    // Charged at the cap bound, not 0 and not skipped — but still worth seeing, because a bound is
    // not a measurement.
    console.warn(`[correction-spend] ESTIMATED owner=${ownerId} video=${videoId} attempts=${estimated} cents=${cents}`);
  }
  const out = await raceRpc<unknown>(
    () => supabase.rpc('record_correction_spend', { p_cents: cents }), CORRECTION_RPC_TIMEOUT_MS, 'record_correction_spend',
  );
  if (!out.ok) {
    const why = out.reason === 'timeout'
      ? `TIMED OUT after ${CORRECTION_RPC_TIMEOUT_MS}ms`
      : (out.cause as { message?: string } | undefined)?.message ?? errorSummary(out.cause);
    console.error(`[correction-spend] FAILED to record owner=${ownerId} video=${videoId} cents=${cents}: ${why}`);
  }
}
