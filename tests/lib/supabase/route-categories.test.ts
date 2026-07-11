import { classifyRoute, needsAnonProvision } from '@/lib/supabase/route-categories';

describe('route categories', () => {
  it('marketing paths are public', () => {
    expect(classifyRoute('/')).toBe('public');
    expect(classifyRoute('/about')).toBe('public');
  });
  it('/auth/* paths are public so OAuth callback and auth-error are reachable pre-session', () => {
    expect(classifyRoute('/auth')).toBe('public');
    expect(classifyRoute('/auth/callback')).toBe('public');
    expect(classifyRoute('/auth/auth-error')).toBe('public');
  });
  it('the guest try-it path is anon-allowed', () => {
    expect(classifyRoute('/try')).toBe('anon-allowed');
    expect(classifyRoute('/try/abc')).toBe('anon-allowed');
  });
  it('/s/<token> share links are public (route self-authorizes via the share token; middleware must not gate anon recipients)', () => {
    expect(classifyRoute('/s')).toBe('public');
    expect(classifyRoute('/s/AbC-1234567890_AbC-1234567890_AbC-1234567890abc')).toBe('public');
    // A sibling path that merely starts with "/s" must NOT be swept in (prefix is boundary-aware).
    expect(classifyRoute('/settings')).toBe('authenticated');
  });
  it('library paths require authentication', () => {
    expect(classifyRoute('/library')).toBe('authenticated');
    expect(classifyRoute('/library/playlists/abc')).toBe('authenticated');
  });
});

describe('needsAnonProvision (Codex H1)', () => {
  it('true only on anon-allowed with no existing user', () => {
    expect(needsAnonProvision('anon-allowed', false)).toBe(true);
    expect(needsAnonProvision('anon-allowed', true)).toBe(false);   // already has a session
    expect(needsAnonProvision('public', false)).toBe(false);
    expect(needsAnonProvision('authenticated', false)).toBe(false); // redirect, don't provision
  });
});
