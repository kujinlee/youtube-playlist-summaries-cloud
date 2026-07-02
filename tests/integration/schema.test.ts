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

  it('defines exactly one owner policy per table, ALL cmd, with a with_check (Codex L1)', async () => {
    const admin = adminClient();
    const { data } = await admin.rpc('exec_sql', {
      // assert cmd + that with_check is present, not just the name — a malformed
      // policy with the right name but no with_check would otherwise pass.
      sql: `select tablename, policyname, cmd, (with_check is not null) as has_with_check
            from pg_policies where schemaname='public' order by tablename`,
    });
    expect(data).toEqual([
      { tablename: 'playlists', policyname: 'playlists_owner', cmd: 'ALL', has_with_check: true },
      { tablename: 'profiles',  policyname: 'profiles_self',   cmd: 'ALL', has_with_check: true },
      { tablename: 'videos',    policyname: 'videos_owner',    cmd: 'ALL', has_with_check: true },
    ]);
  });
});
