import type { FieldState, HumanField, HumanSnapshot, VideoBaseline } from './types';

export interface FieldMerge {
  winner: 'local' | 'cloud' | 'equal';
  value: string | number | undefined;
  editedAt: string | undefined;
  conflict: boolean;
}

type Baseline = { value?: string | number; editedAt?: string };

/** Changed vs baseline is over the (value, editedAt) PAIR, not value alone (§5.4). */
function changed(side: FieldState, base: Baseline): boolean {
  return side.value !== base.value || side.editedAt !== base.editedAt;
}

function newer(a: string | undefined, b: string | undefined): boolean {
  // returns true when a is strictly newer than b; undefined sorts oldest
  return (a ?? '') > (b ?? '');
}

export function reconcileField(local: FieldState, cloud: FieldState, baseline: Baseline): FieldMerge {
  // Equal VALUES never conflict (§5.4 row 1). But if their per-field timestamps differ, CONVERGE:
  // return the newer-timestamp side as a NON-conflicting winner so the older side's editedAt is
  // written forward and both replicas end identical — returning 'equal' here would skip the write
  // and leave baseline/live timestamp drift (round-2 H1). Truly-equal pair → 'equal' (no write).
  if (local.value === cloud.value) {
    if (local.editedAt === cloud.editedAt) {
      return { winner: 'equal', value: local.value, editedAt: local.editedAt, conflict: false };
    }
    return newer(local.editedAt, cloud.editedAt)
      ? { winner: 'local', value: local.value, editedAt: local.editedAt, conflict: false }
      : { winner: 'cloud', value: cloud.value, editedAt: cloud.editedAt, conflict: false };
  }
  const lChanged = changed(local, baseline);
  const cChanged = changed(cloud, baseline);

  if (lChanged && !cChanged) return { winner: 'local', value: local.value, editedAt: local.editedAt, conflict: false };
  if (cChanged && !lChanged) return { winner: 'cloud', value: cloud.value, editedAt: cloud.editedAt, conflict: false };

  // both changed (or neither vs an absent baseline but values differ) → newer per-field ts wins.
  // A backfilled timestamp must never drive a destructive overwrite (§5.5) → conflict skip.
  if (local.backfilled || cloud.backfilled) {
    return { winner: 'equal', value: local.value, editedAt: local.editedAt, conflict: true };
  }
  const localWins = newer(local.editedAt, cloud.editedAt);
  return localWins
    ? { winner: 'local', value: local.value, editedAt: local.editedAt, conflict: true }
    : { winner: 'cloud', value: cloud.value, editedAt: cloud.editedAt, conflict: true };
}

const FIELDS: HumanField[] = ['personalNote', 'personalScore', 'corrections'];

export function reconcileHuman(
  local: HumanSnapshot,
  cloud: HumanSnapshot,
  baseline: VideoBaseline['classB'],
): Record<HumanField, FieldMerge> {
  const out = {} as Record<HumanField, FieldMerge>;
  for (const f of FIELDS) out[f] = reconcileField(local[f], cloud[f], baseline[f] ?? {});
  return out;
}
