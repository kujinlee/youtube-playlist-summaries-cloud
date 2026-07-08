-- 1E-c: cancel returns the count of rows it flagged (0 = foreign/missing/terminal),
-- touches only NON-TERMINAL owned rows, and never raises (no ownership oracle).
-- The 0008 function returns void; a return-type change needs DROP first (same as 0009 did
-- for enqueue_job). DROP also drops the old grants — re-issue them below.
drop function if exists request_cancel_job(uuid);

create function request_cancel_job(p_job_id uuid) returns int
  language plpgsql security definer set search_path = public as $$
declare n int;
begin
  update jobs
     set cancel_requested = true,
         status = case when status = 'queued' then 'cancelled' else status end,
         updated_at = now()
   where id = p_job_id
     and owner_id = auth.uid()
     and status in ('queued','active');
  get diagnostics n = row_count;
  return n;
end $$;
revoke all on function request_cancel_job(uuid) from public;
grant execute on function request_cancel_job(uuid) to anon, authenticated, service_role;
