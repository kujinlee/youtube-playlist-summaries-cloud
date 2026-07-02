// tests/integration/schema.test.ts
import { adminClient } from './helpers/clients';

describe('core schema', () => {
  it('has RLS enabled AND forced on every owned table (Codex M1)', async () => {
    const admin = adminClient();
    const { data, error } = await admin.rpc('exec_sql', {
      // helper defined in Task 7 harness; or query pg_class via a SQL function
      sql: `select relname, relrowsecurity, relforcerowsecurity from pg_class
            where relname in ('profiles','playlists','videos')
              and relnamespace = 'public'::regnamespace and relkind = 'r'
            order by relname`,
    });
    expect(error).toBeNull();
    // both flags must be true: `enable` alone lets the table owner bypass RLS;
    // `force` makes even the owner obey it.
    expect(data).toEqual([
      { relname: 'playlists', relrowsecurity: true, relforcerowsecurity: true },
      { relname: 'profiles',  relrowsecurity: true, relforcerowsecurity: true },
      { relname: 'videos',    relrowsecurity: true, relforcerowsecurity: true },
    ]);
  });
});
