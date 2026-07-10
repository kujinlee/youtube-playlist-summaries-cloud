import { generateShareToken, hashShareToken } from '@/lib/share/token';
import { createHash } from 'crypto';

describe('share token crypto', () => {
  it('generates a 43-char base64url token (256-bit) and its 64-char hex sha256 hash', () => {
    const { token, tokenHash } = generateShareToken();
    expect(token).toMatch(/^[A-Za-z0-9_-]{43}$/); // 32 bytes base64url, no padding
    expect(tokenHash).toBe(createHash('sha256').update(token).digest('hex'));
    expect(tokenHash).toMatch(/^[0-9a-f]{64}$/);
  });
  it('two tokens differ', () => {
    expect(generateShareToken().token).not.toBe(generateShareToken().token);
  });
  it('hashShareToken is deterministic and matches sha256(token) hex', () => {
    const { token, tokenHash } = generateShareToken();
    expect(hashShareToken(token)).toBe(tokenHash);
  });
});
