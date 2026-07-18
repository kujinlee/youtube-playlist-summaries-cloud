import type { ClassASignals } from './types';

export interface ClassADecision {
  action: 'skip' | 'copyToLocal' | 'copyToCloud';
  needsRegen: boolean;
}

const current = (s: ClassASignals, cur: string): boolean => s.mdCorrectionsHash === cur;
const newer = (a: string | null, b: string | null): boolean => (a ?? '') > (b ?? '');

export function reconcileClassA(args: {
  local: ClassASignals;
  cloud: ClassASignals;
  reconciledCorrectionsHash: string;
}): ClassADecision {
  const { local, cloud, reconciledCorrectionsHash: cur } = args;
  const lHas = local.mdHash != null;
  const cHas = cloud.mdHash != null;

  // Presence (§5.6 one-sided copy) — flag needsRegen when the SOLE MD is corrections-stale (R8, L2)
  if (!lHas && !cHas) return { action: 'skip', needsRegen: false };
  if (!lHas) return { action: 'copyToLocal', needsRegen: !current(cloud, cur) };
  if (!cHas) return { action: 'copyToCloud', needsRegen: !current(local, cur) };

  const lCur = current(local, cur);
  const cCur = current(cloud, cur);
  const bothStale = !lCur && !cCur;

  // Equal MD bodies: skip ONLY when both corrections-current, OR both stale AND same format.
  // If currency OR format disagrees (even with identical bytes), fall through so the winning
  // metadata TUPLE converges onto the identical body — do NOT skip (Blocking ③, spec §5.3 row 1).
  if (local.mdHash === cloud.mdHash) {
    if (lCur && cCur) return { action: 'skip', needsRegen: false };
    if (bothStale && local.docVersionMajor === cloud.docVersionMajor) return { action: 'skip', needsRegen: true };
    // else: fall through to currency/format below.
  }

  // corrections-currency FIRST (a stale MD never overwrites a corrections-current one)
  if (lCur && !cCur) return { action: 'copyToCloud', needsRegen: false };
  if (cCur && !lCur) return { action: 'copyToLocal', needsRegen: false };

  // format (never downgrade)
  if (local.docVersionMajor !== cloud.docVersionMajor) {
    const winnerIsCloud = cloud.docVersionMajor > local.docVersionMajor;
    return { action: winnerIsCloud ? 'copyToLocal' : 'copyToCloud', needsRegen: bothStale };
  }

  // same major, different mdHash → recency-tiebreak (unify prose)
  const winnerIsLocal = newer(local.mdGeneratedAt, cloud.mdGeneratedAt);
  return { action: winnerIsLocal ? 'copyToCloud' : 'copyToLocal', needsRegen: bothStale };
}
