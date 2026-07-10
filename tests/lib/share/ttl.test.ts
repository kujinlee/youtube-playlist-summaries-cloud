import { resolveExpiry } from '@/lib/share/ttl';

describe('resolveExpiry', () => {
  it('omitted → 30 days out', () => {
    const r = resolveExpiry(undefined);
    expect(r.ok).toBe(true);
    if (r.ok) expect(r.expiresAt!.getTime()).toBeGreaterThan(Date.now() + 29 * 864e5);
  });
  it("'never' → null", () => {
    expect(resolveExpiry('never')).toEqual({ ok: true, expiresAt: null });
  });
  it('a valid positive int → that many days out', () => {
    const r = resolveExpiry(7);
    expect(r.ok).toBe(true);
    if (r.ok) expect(r.expiresAt!.getTime()).toBeGreaterThan(Date.now() + 6 * 864e5);
  });
  it('365 (max) → ok', () => { expect(resolveExpiry(365).ok).toBe(true); });
  it.each([0, -1, 366, 3.5, NaN])('rejects %p', (v) => {
    expect(resolveExpiry(v as number)).toEqual({ ok: false });
  });
});
