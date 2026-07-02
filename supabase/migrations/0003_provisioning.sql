-- supabase/migrations/0003_provisioning.sql
create function handle_new_user() returns trigger
  language plpgsql security definer set search_path = '' as $$
begin
  insert into public.profiles (id, is_anonymous)
  values (new.id, coalesce(new.is_anonymous, false));
  return new;
end $$;

create trigger on_auth_user_created
  after insert on auth.users for each row execute function handle_new_user();

-- is_anonymous is set once at provisioning; reject client attempts to change it.
create function guard_is_anonymous() returns trigger
  language plpgsql as $$
begin
  if new.is_anonymous is distinct from old.is_anonymous then
    raise exception 'is_anonymous is immutable';
  end if;
  return new;
end $$;

create trigger profiles_is_anonymous_immutable
  before update on profiles for each row execute function guard_is_anonymous();
