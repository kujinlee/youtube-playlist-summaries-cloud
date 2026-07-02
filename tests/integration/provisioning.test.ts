// tests/integration/provisioning.test.ts
import { adminClient, anonSession, newUser } from './helpers/clients';

describe('provisioning trigger', () => {
  it('creates exactly one profiles row for a Google-style (email) sign-up', async () => {
    const admin = adminClient();
    const { user } = await newUser();                 // admin.auth.admin.createUser
    const { data } = await admin
      .from('profiles').select('id,is_anonymous').eq('id', user.id);
    expect(data).toEqual([{ id: user.id, is_anonymous: false }]);
  });

  it('creates a profiles row with is_anonymous=true for an anonymous sign-up', async () => {
    const { client, userId } = await anonSession();   // client.auth.signInAnonymously
    const { data } = await client.from('profiles').select('id,is_anonymous').eq('id', userId);
    expect(data).toEqual([{ id: userId, is_anonymous: true }]);
  });

  it('is SECURITY DEFINER (else the RLS-protected profiles insert would abort signup)', async () => {
    const admin = adminClient();
    const { data } = await admin.rpc('exec_sql', {
      sql: `select prosecdef from pg_proc
            where proname = 'handle_new_user' and pronamespace = 'public'::regnamespace`,
    });
    expect(data).toEqual([{ prosecdef: true }]);
  });

  it('rejects a client attempt to flip is_anonymous', async () => {
    const { client, userId } = await anonSession();
    const { error } = await client.from('profiles')
      .update({ is_anonymous: false }).eq('id', userId);
    expect(error?.message).toMatch(/is_anonymous is immutable/);
  });
});
