-- supabase/migrations/0004_test_exec_sql.sql
-- Read-only catalog inspection for the integration suite. Granted to service_role ONLY.
create function exec_sql(sql text) returns jsonb
  language plpgsql security definer set search_path = '' as $$
declare result jsonb;
begin
  execute 'select coalesce(jsonb_agg(t), ''[]''::jsonb) from (' || sql || ') t' into result;
  return result;
end $$;
revoke all on function exec_sql(text) from public, anon, authenticated;
grant execute on function exec_sql(text) to service_role;
