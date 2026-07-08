// tests/integration/schema.test.ts
import { adminClient } from './helpers/clients';

describe('core schema', () => {
  it('has RLS enabled AND forced on every owned table (Codex M1)', async () => {
    const admin = adminClient();
    const { data, error } = await admin.rpc('exec_sql', {
      // helper defined in Task 7 harness; or query pg_class via a SQL function
      sql: `select relname, relrowsecurity, relforcerowsecurity from pg_class
            where relname in ('profiles','playlists','videos','jobs')
              and relnamespace = 'public'::regnamespace and relkind = 'r'
            order by relname`,
    });
    expect(error).toBeNull();
    // both flags must be true: `enable` alone lets the table owner bypass RLS;
    // `force` makes even the owner obey it.
    expect(data).toEqual([
      { relname: 'jobs',      relrowsecurity: true, relforcerowsecurity: true },
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
      { tablename: 'jobs',      policyname: 'jobs_owner',      cmd: 'ALL', has_with_check: true },
      { tablename: 'playlists', policyname: 'playlists_owner', cmd: 'ALL', has_with_check: true },
      { tablename: 'profiles',  policyname: 'profiles_self',   cmd: 'ALL', has_with_check: true },
      { tablename: 'videos',    policyname: 'videos_owner',    cmd: 'ALL', has_with_check: true },
    ]);
  });

  it('jobs.playlist_id is a not-null uuid coordinate with a composite owner FK (1E-b)', async () => {
    const admin = adminClient();
    const { data, error } = await admin.rpc('exec_sql', {
      sql: `select is_nullable, data_type from information_schema.columns
            where table_schema = 'public' and table_name = 'jobs' and column_name = 'playlist_id'`,
    });
    expect(error).toBeNull();
    expect(data).toEqual([{ is_nullable: 'NO', data_type: 'uuid' }]);

    const fk = await admin.rpc('exec_sql', {
      sql: `select conname from pg_constraint
            where conname = 'jobs_playlist_owner_fk' and conrelid = 'public.jobs'::regclass`,
    });
    expect(fk.error).toBeNull();
    expect(fk.data).toEqual([{ conname: 'jobs_playlist_owner_fk' }]);
  });

  it('jobs_idem_active includes playlist_id in its column set (1E-b)', async () => {
    const admin = adminClient();
    const { data, error } = await admin.rpc('exec_sql', {
      sql: `select indexdef from pg_indexes where schemaname = 'public' and indexname = 'jobs_idem_active'`,
    });
    expect(error).toBeNull();
    expect(data[0].indexdef).toContain('playlist_id');
  });

  it('jobs.progress_phase has a check constraint limiting it to the three known phases (1E-b)', async () => {
    const admin = adminClient();
    const { data, error } = await admin.rpc('exec_sql', {
      sql: `select pg_get_constraintdef(oid) as def from pg_constraint
            where conrelid = 'public.jobs'::regclass and contype = 'c'
              and pg_get_constraintdef(oid) like '%progress_phase%'`,
    });
    expect(error).toBeNull();
    expect(data).toHaveLength(1);
    expect(data[0].def).toContain('transcribing');
    expect(data[0].def).toContain('summarizing');
    expect(data[0].def).toContain('writing');
  });
});
