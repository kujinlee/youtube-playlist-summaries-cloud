import { findLeakedSecrets } from '@/lib/security/bundle-secret-scan';

/** Build a real JWT-shaped token (header.payload.signature, base64url) for the given claims.
 *  Real encoding, not a mock — the scanner has to decode this for the test to mean anything. */
function jwt(claims: Record<string, unknown>): string {
  const b64 = (o: unknown) =>
    Buffer.from(JSON.stringify(o)).toString('base64url');
  return `${b64({ alg: 'HS256', typ: 'JWT' })}.${b64(claims)}.c2lnbmF0dXJlLWJ5dGVz`;
}

const ANON = jwt({ iss: 'supabase', ref: 'abcdefghijklmnop', role: 'anon', iat: 1784567049 });
const SERVICE = jwt({ iss: 'supabase', ref: 'abcdefghijklmnop', role: 'service_role', iat: 1784567049 });

describe('findLeakedSecrets', () => {
  it('flags a service_role JWT', () => {
    const leaks = findLeakedSecrets(`const k="${SERVICE}";`);
    expect(leaks).toHaveLength(1);
    expect(leaks[0].kind).toBe('service_role_jwt');
  });

  // THE load-bearing case. The anon key is SUPPOSED to ship in the browser bundle — it is
  // public by design and gated by RLS. A scanner that flags it fires on every build, gets
  // muted, and then detects nothing. Flagging "a JWT" is not the requirement.
  it('does not flag the anon JWT that legitimately ships in the bundle', () => {
    expect(findLeakedSecrets(`const k="${ANON}";`)).toEqual([]);
  });

  it('flags a new-style sb_secret_ key', () => {
    const leaks = findLeakedSecrets('const k="sb_secret_dzJzAbCd1234_EfGhIjKl";');
    expect(leaks).toHaveLength(1);
    expect(leaks[0].kind).toBe('secret_api_key');
  });

  it('does not flag the publishable key alongside it', () => {
    expect(findLeakedSecrets('const k="sb_publishable_NAZ0C1jJ_nfh0iTZ3ZA9NA_W_2-0_Fg";')).toEqual([]);
  });

  it('returns no leaks for ordinary bundle text', () => {
    expect(findLeakedSecrets('export function x(){return "eyJhbGciOi"}')).toEqual([]);
  });

  it('reports every occurrence when a bundle leaks more than one secret', () => {
    const leaks = findLeakedSecrets(`a="${SERVICE}";b="sb_secret_dzJzAbCd1234_EfGhIjKl";c="${ANON}";`);
    expect(leaks.map((l) => l.kind).sort()).toEqual(['secret_api_key', 'service_role_jwt']);
  });

  // A leak report that prints the secret leaks it a second time — into CI logs, which are
  // retained and often world-readable on public repos.
  it('never puts the secret itself in the finding', () => {
    const [leak] = findLeakedSecrets(`const k="${SERVICE}";`);
    expect(JSON.stringify(leak)).not.toContain(SERVICE);
    expect(JSON.stringify(leak)).not.toContain(SERVICE.split('.')[1]);
  });
});
