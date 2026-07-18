import { reconcileClassA } from '@/lib/cloud-sync/reconcile-class-a';
import type { ClassASignals } from '@/lib/cloud-sync/types';

const S = (o: Partial<ClassASignals>): ClassASignals => ({
  summaryMdKey: 'x.md', mdHash: 'h', docVersionMajor: 3, mdGeneratedAt: '2026-01-01T00:00:00.000Z',
  mdCorrectionsHash: 'C', backfilled: false, ...o,
});
const CUR = 'C'; // reconciled corrections hash

describe('reconcileClassA (§5.3)', () => {
  it('mdHash equal + both corrections-current → skip', () => {
    expect(reconcileClassA({ local: S({ mdHash: 'h' }), cloud: S({ mdHash: 'h' }), reconciledCorrectionsHash: CUR }))
      .toEqual({ action: 'skip', needsRegen: false });
  });
  it('mdHash equal but BOTH stale vs reconciled corrections → skip but needsRegen (round-v8 H-1)', () => {
    const r = reconcileClassA({ local: S({ mdHash: 'h', mdCorrectionsHash: 'OLD' }), cloud: S({ mdHash: 'h', mdCorrectionsHash: 'OLD' }), reconciledCorrectionsHash: CUR });
    expect(r).toEqual({ action: 'skip', needsRegen: true });
  });
  it('mdHash equal but one current, one stale → current wins, NOT skip (Blocking ③ scenario 1)', () => {
    const r = reconcileClassA({ local: S({ mdHash: 'h', mdCorrectionsHash: CUR }), cloud: S({ mdHash: 'h', mdCorrectionsHash: 'OLD' }), reconciledCorrectionsHash: CUR });
    expect(r).toEqual({ action: 'copyToCloud', needsRegen: false }); // local current tuple → cloud
  });
  it('mdHash equal, both stale, DIFFERENT major → higher major wins + needsRegen, NOT skip (Blocking ③ scenario 2)', () => {
    const r = reconcileClassA({ local: S({ mdHash: 'h', mdCorrectionsHash: 'OLD', docVersionMajor: 2 }), cloud: S({ mdHash: 'h', mdCorrectionsHash: 'OLD', docVersionMajor: 3 }), reconciledCorrectionsHash: CUR });
    expect(r).toEqual({ action: 'copyToLocal', needsRegen: true });
  });
  it('one corrections-current, other stale → current wins even if stale side has higher format', () => {
    const local = S({ mdCorrectionsHash: CUR, docVersionMajor: 2, mdHash: 'hl' });
    const cloud = S({ mdCorrectionsHash: 'OLD', docVersionMajor: 3, mdHash: 'hc' });
    expect(reconcileClassA({ local, cloud, reconciledCorrectionsHash: CUR }))
      .toEqual({ action: 'copyToCloud', needsRegen: false }); // local (current) overwrites cloud
  });
  it('both current, different major → higher major wins (never downgrade)', () => {
    const local = S({ docVersionMajor: 2, mdHash: 'hl' });
    const cloud = S({ docVersionMajor: 3, mdHash: 'hc' });
    expect(reconcileClassA({ local, cloud, reconciledCorrectionsHash: CUR }))
      .toEqual({ action: 'copyToLocal', needsRegen: false }); // cloud (major 3) → local
  });
  it('both current, same major, different mdHash → newer mdGeneratedAt unifies', () => {
    const local = S({ mdHash: 'hl', mdGeneratedAt: '2026-05-05T00:00:00.000Z' });
    const cloud = S({ mdHash: 'hc', mdGeneratedAt: '2026-02-02T00:00:00.000Z' });
    expect(reconcileClassA({ local, cloud, reconciledCorrectionsHash: CUR }))
      .toEqual({ action: 'copyToCloud', needsRegen: false }); // local newer → cloud converges
  });
  it('neither current (both stale) → keep higher-major, flag needsRegen', () => {
    const local = S({ mdCorrectionsHash: 'OLD', docVersionMajor: 2, mdHash: 'hl' });
    const cloud = S({ mdCorrectionsHash: 'OLD', docVersionMajor: 3, mdHash: 'hc' });
    const r = reconcileClassA({ local, cloud, reconciledCorrectionsHash: CUR });
    expect(r).toEqual({ action: 'copyToLocal', needsRegen: true }); // cloud higher major → local, but stale
  });
  it('present only one side (current) → copy, no needsRegen (hydrate/publish)', () => {
    expect(reconcileClassA({ local: S({ summaryMdKey: null, mdHash: null }), cloud: S({ mdHash: 'hc' }), reconciledCorrectionsHash: CUR }))
      .toEqual({ action: 'copyToLocal', needsRegen: false });
    expect(reconcileClassA({ local: S({ mdHash: 'hl' }), cloud: S({ summaryMdKey: null, mdHash: null }), reconciledCorrectionsHash: CUR }))
      .toEqual({ action: 'copyToCloud', needsRegen: false });
  });
  it('one-sided hydrate of a corrections-STALE MD flags needsRegen (L2)', () => {
    expect(reconcileClassA({ local: S({ summaryMdKey: null, mdHash: null }), cloud: S({ mdHash: 'hc', mdCorrectionsHash: 'OLD' }), reconciledCorrectionsHash: CUR }))
      .toEqual({ action: 'copyToLocal', needsRegen: true });
  });
  it('neither side has an MD → skip', () => {
    expect(reconcileClassA({ local: S({ summaryMdKey: null, mdHash: null }), cloud: S({ summaryMdKey: null, mdHash: null }), reconciledCorrectionsHash: CUR }))
      .toEqual({ action: 'skip', needsRegen: false });
  });
});
