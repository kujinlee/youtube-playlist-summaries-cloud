/**
 * Live-Gemini release verification harness — M1.1 (docs/reservation-release-live-gate.md).
 *
 * Confirms the two premises behind class-A RELEASE before you flip `RELEASE_VERIFIED = true`
 * in `lib/gemini-failure.ts`:
 *   (1) an overloaded / rate-limited call surfaces as a typed error with `.status ∈ {429, 503}`
 *       that the REAL classifier (`classifyGeminiFailure`) routes to 'release'; and
 *   (2) those rejected calls carry NO token billing  ← must be confirmed on the billing dashboard;
 *       this script prints exactly what window to check.
 *
 * It uses the app's OWN classifier and the same SDK the app uses — so a pass here means the real
 * worker path (`worker-runner.ts`) would classify a real outage correctly.
 *
 * RUN (needs a live key; costs a few cheap successful calls):
 *   GEMINI_API_KEY=... npx ts-node -r tsconfig-paths/register scripts/verify-gemini-release.ts
 *   # optional: BURST=80 MODEL=gemini-2.5-flash  (raise BURST until you trip a 429/503)
 *
 * This is a read-only diagnostic — it changes NO code and flips NO flag. If both facts hold,
 * follow docs/reservation-release-live-gate.md step 3 to flip the gate.
 */
import { GoogleGenerativeAI } from '@google/generative-ai';
import { classifyGeminiFailure } from '@/lib/gemini-failure';

const API_KEY = process.env.GEMINI_API_KEY;
const MODEL = process.env.MODEL ?? process.env.GEMINI_SUMMARY_MODEL ?? 'gemini-2.5-flash';
const BURST = Number(process.env.BURST ?? 60);

function line(s = '') { console.log(s); }

async function main() {
  if (!API_KEY) throw new Error('Set GEMINI_API_KEY to run the live verification.');
  const client = new GoogleGenerativeAI(API_KEY);
  const model = client.getGenerativeModel({ model: MODEL });

  line('════════════════════════════════════════════════════════════════');
  line(` Live-Gemini release verification   model=${MODEL}   burst=${BURST}`);
  line('════════════════════════════════════════════════════════════════');

  // ── Fact (2) baseline: what a BILLED call looks like ────────────────────────────
  // A successful call reports usageMetadata (tokens). A 429/503 rejection should report NONE.
  const started = new Date().toISOString();
  line(`\n[baseline] one successful call — usageMetadata is what "billed" looks like:`);
  try {
    const res = await model.generateContent('Reply with the single word: ok');
    line(`  usageMetadata = ${JSON.stringify(res.response.usageMetadata ?? null)}`);
  } catch (e) {
    line(`  baseline call failed (${(e as { constructor?: { name?: string } }).constructor?.name}): ${(e as Error).message}`);
    line('  (if this is already a 429/503 you are rate-limited — good for fact (1), see below)');
  }

  // ── Fact (1): trip a real 429/503 and run it through the REAL classifier ─────────
  line(`\n[burst] firing ${BURST} concurrent minimal calls to provoke a 429/503 …`);
  const results = await Promise.allSettled(
    Array.from({ length: BURST }, () => model.generateContent('ping')),
  );

  const seen = new Map<string, number>();       // "CtorName status=NNN" → count
  let releaseCount = 0, keepCount = 0, targetStatus = 0;
  for (const r of results) {
    if (r.status !== 'rejected') continue;
    const err = r.reason as { constructor?: { name?: string }; status?: number };
    const ctor = err?.constructor?.name ?? 'unknown';
    const status = typeof err?.status === 'number' ? err.status : undefined;
    seen.set(`${ctor} status=${status ?? 'none'}`, (seen.get(`${ctor} status=${status ?? 'none'}`) ?? 0) + 1);
    if (status === 429 || status === 503) targetStatus++;
    // The REAL classifier — this is the exact decision worker-runner.ts makes.
    if (classifyGeminiFailure(err) === 'release') releaseCount++; else keepCount++;
  }
  const ended = new Date().toISOString();

  const ok = results.filter((r) => r.status === 'fulfilled').length;
  const failed = results.length - ok;
  line(`\n[results]  ${ok} ok, ${failed} rejected`);
  line('  rejection shapes:');
  if (seen.size === 0) line('    (none — no call was rejected; raise BURST to exceed your quota)');
  for (const [shape, n] of seen) line(`    ${n.toString().padStart(4)} × ${shape}`);
  line(`  classifier verdict on rejections:  release=${releaseCount}  keep=${keepCount}`);

  // ── Verdict ──────────────────────────────────────────────────────────────────
  line('\n──────────────────────── FACT (1) ────────────────────────');
  if (targetStatus > 0 && releaseCount > 0) {
    line(`  ✅ Saw ${targetStatus} rejection(s) with .status ∈ {429,503}; the real classifier`);
    line(`     routed ${releaseCount} to 'release'. The typed-error + status path matches a live outage.`);
  } else if (failed === 0) {
    line('  ⚠️  Nothing was rate-limited. Raise BURST (e.g. BURST=200) or run against a busier');
    line('     quota/region until you actually trip a 429/503, then re-check.');
  } else {
    line('  ⚠️  Rejections occurred but none were a classifier-releasable 429/503 (see shapes above).');
    line('     If a real outage surfaces as a different shape, RELEASE_STATUSES / the classifier');
    line('     needs revising BEFORE the gate can be flipped (live-gate doc step 4).');
  }

  line('\n──────────────────────── FACT (2) — YOU must confirm on the dashboard ────────────────────────');
  line('  This script cannot read billing. Cross-check the Gemini usage/billing dashboard for the window:');
  line(`     start ≈ ${started}`);
  line(`     end   ≈ ${ended}`);
  line(`  Confirm the ${targetStatus} rejected 429/503 call(s) billed ZERO tokens (only the`);
  line('  successful calls should show usage). If so, fact (2) holds.');

  line('\n──────────────────────── If BOTH facts hold ────────────────────────');
  line('  Flip RELEASE_VERIFIED=false → true in lib/gemini-failure.ts, note the date/evidence in the');
  line('  commit, and run:  npm run test:integration -- reservation-release   (confirm no regression).');
  line('  Also verify the sibling transcript fallback flag (CLOUD_TRANSCRIBE_FALLBACK_VERIFIED,');
  line('  lib/gemini.ts) the same way if you have not already. Record results in');
  line('  docs/local-validation-findings.md.\n');
}

main().catch((e) => { console.error('\n[verify-gemini-release] fatal:', e); process.exit(1); });
