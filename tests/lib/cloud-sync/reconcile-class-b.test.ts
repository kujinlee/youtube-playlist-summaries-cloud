import { reconcileField } from '@/lib/cloud-sync/reconcile-class-b';

const F = (value: string | number | undefined, editedAt?: string, backfilled = false) => ({ value, editedAt, backfilled });
const B = (value?: string | number, editedAt?: string) => ({ value, editedAt });

describe('reconcileField (§5.4)', () => {
  it('L == C → no action', () => {
    expect(reconcileField(F('x', 't1'), F('x', 't1'), B('x', 't1'))).toMatchObject({ winner: 'equal', value: 'x', conflict: false });
  });
  it('equal values, equal timestamps → equal, no write', () => {
    expect(reconcileField(F('note', 't2'), F('note', 't2'), B('old', 't1'))).toMatchObject({ winner: 'equal', value: 'note', conflict: false });
  });
  it('equal values, different timestamps → converge to newer ts, no conflict (M5 + round-2 H1)', () => {
    expect(reconcileField(F('note', 't3'), F('note', 't2'), B('old', 't1'))).toMatchObject({ winner: 'local', value: 'note', editedAt: 't3', conflict: false });
    expect(reconcileField(F('note', 't2'), F('note', 't3'), B('old', 't1'))).toMatchObject({ winner: 'cloud', value: 'note', editedAt: 't3', conflict: false });
  });
  it('only local changed vs baseline → take local', () => {
    expect(reconcileField(F('new', 't2'), F('old', 't1'), B('old', 't1'))).toMatchObject({ winner: 'local', value: 'new', conflict: false });
  });
  it('only cloud changed vs baseline → take cloud', () => {
    expect(reconcileField(F('old', 't1'), F('new', 't2'), B('old', 't1'))).toMatchObject({ winner: 'cloud', value: 'new' });
  });
  it('a clear on one side (present→absent vs baseline) propagates', () => {
    expect(reconcileField(F(undefined, 't2'), F('x', 't1'), B('x', 't1'))).toMatchObject({ winner: 'local', value: undefined, conflict: false });
  });
  it('both changed to different values → newer per-field editedAt wins + conflict', () => {
    expect(reconcileField(F('L', 't3'), F('C', 't2'), B('base', 't1'))).toMatchObject({ winner: 'local', value: 'L', conflict: true });
    expect(reconcileField(F('L', 't2'), F('C', 't3'), B('base', 't1'))).toMatchObject({ winner: 'cloud', value: 'C', conflict: true });
  });
  it('a same-value re-add (clear→retype same text, advanced ts) is NOT dropped (round-v8 M-1)', () => {
    // baseline present "x"@t1; local cleared@t2; cloud re-added same "x"@t3.
    // cloud's (value,editedAt) differs from baseline (ts advanced) → cloud changed;
    // local also changed (clear). Both changed → newer wins = cloud's re-add.
    expect(reconcileField(F(undefined, 't2'), F('x', 't3'), B('x', 't1'))).toMatchObject({ winner: 'cloud', value: 'x', conflict: true });
  });
  it('no baseline + differ → newer per-field editedAt wins', () => {
    expect(reconcileField(F('L', 't2'), F('C', 't1'), B(undefined, undefined))).toMatchObject({ winner: 'local', value: 'L' });
  });
  it('present one side, absent other, no baseline → copy (additive)', () => {
    expect(reconcileField(F('L', 't1'), F(undefined, undefined), B(undefined, undefined))).toMatchObject({ winner: 'local', value: 'L', conflict: false });
  });
  it('both changed but a side is backfilled → conflict skip (no destructive overwrite, §5.5)', () => {
    const r = reconcileField(F('L', 't2', true), F('C', 't3'), B('base', 't1'));
    expect(r.conflict).toBe(true);
    expect(r.winner).toBe('equal'); // 'equal' == no write applied
  });
});
