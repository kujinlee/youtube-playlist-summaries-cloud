import { newUser, signInAs, anonSession } from './helpers/clients';

describe('exec_sql is service_role-only', () => {
  it('a user-JWT client cannot call exec_sql', async () => {
    const u = await newUser();
    const { client } = await signInAs(u.email, u.password);
    const { error } = await client.rpc('exec_sql', { sql: 'select 1' });
    expect(error).not.toBeNull();                    // permission denied for authenticated
  });

  it('an anon client cannot call exec_sql', async () => {
    const { client } = await anonSession();
    const { error } = await client.rpc('exec_sql', { sql: 'select 1' });
    expect(error).not.toBeNull();                    // permission denied for anon
  });
});
