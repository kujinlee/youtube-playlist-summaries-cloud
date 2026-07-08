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
      sql: `select pg_get_constraintdef(oid) as def from pg_constraint
            where conname = 'jobs_playlist_owner_fk' and conrelid = 'public.jobs'::regclass`,
    });
    expect(fk.error).toBeNull();
    expect(fk.data).toHaveLength(1);
    // Must span BOTH columns — a single-column FK on playlist_id alone is a cross-tenant
    // write-injection hole (attacker enqueues a job citing another owner's playlist UUID).
    // exec_sql runs with search_path='' so the referenced table renders schema-qualified.
    expect(fk.data[0].def).toMatch(
      /FOREIGN KEY \(playlist_id, owner_id\) REFERENCES (?:public\.)?playlists\(id, owner_id\)/,
    );
  });

  it('jobs_idem_active includes playlist_id in its column set (1E-b)', async () => {
    const admin = adminClient();
    const { data, error } = await admin.rpc('exec_sql', {
      sql: `select indexdef from pg_indexes where schemaname = 'public' and indexname = 'jobs_idem_active'`,
    });
    expect(error).toBeNull();
    // Exact unique-key column set (order matters — it is the ON CONFLICT arbiter) + the partial
    // predicate. A weaker `toContain('playlist_id')` would pass even if playlist_id were only in an
    // INCLUDE/predicate but not the unique key, or if the predicate diverged from enqueue_job's.
    expect(data[0].indexdef).toContain('UNIQUE INDEX jobs_idem_active');
    expect(data[0].indexdef).toMatch(
      /\(owner_id, playlist_id, video_id, section_id, job_kind, job_version\)/,
    );
    expect(data[0].indexdef).toMatch(/WHERE .*'queued'.*'active'.*'completed'/);
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
    // Exact three-element array in order — superset-proof. A CHECK permitting a 4th phase (e.g.
    // 'debug') would place it after 'writing'::text and fail the trailing `\]`, so this rejects
    // supersets that a per-value `toContain` would silently accept.
    expect(data[0].def).toMatch(
      /progress_phase = ANY \(ARRAY\['transcribing'::text, 'summarizing'::text, 'writing'::text\]\)/,
    );
  });
});
