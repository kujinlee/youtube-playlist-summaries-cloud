#!/usr/bin/env bash
# Build the database the schema gates read, from the repo, in a container. Local or CI.
#
#   scripts/ci/start-schema-db.sh [container-name]
#     exit 0 = the container is up, every migration applied, and M4 is PRESENT
#     exit 2 = CANNOT RUN (treat as NOT RUN — never a pass)
#
#   scripts/ci/start-schema-db.sh --self-test    # name-guard cases, no Docker required
#
# ⚠ NO STORED CASE COUNT IN THIS HEADER, DELIBERATELY. `check-selftest-counts.py`
# verifies the canonical `--self-test  # N cases` declaration by globbing
# `scripts/*.py` — Python only, top level only — so a count written here would be a
# stored claim with NO outside observer, which is precisely the drift that guard
# exists to refuse. The count below is DERIVED at runtime from the cases that ran.
#
# The gates address Postgres as `docker exec -i "$PGCONTAINER" psql` (`m4_base_db.py:59,107`), NOT
# as a host:port URL — so a GitHub Actions `services:` block is the WRONG shape: service containers
# are reachable by hostname, and their container names are generated. A named `docker run` is what
# this seam actually wants, and it costs one step.
#
# ⛔⛔ `pg_isready` IS NOT A READINESS SIGNAL FOR THIS IMAGE, AND THE IMAGE'S OWN HEALTHCHECK USES IT.
# MEASURED 2026-09-13. `public.ecr.aws/supabase/postgres` runs a TEMPORARY server to execute its init
# scripts, then shuts it down and starts the real one. `pg_isready` answers YES to the temporary one:
#
#     line   42  database system is ready to accept connections   <- the throwaway server
#     line 1207  shutting down
#     line 1215  PostgreSQL init process complete; ready for start up.
#     line 1225  database system is ready to accept connections   <- the real one
#
# `docker inspect --format '{{.Config.Healthcheck.Test}}'` on that image is
# `[CMD-SHELL pg_isready -U postgres -h localhost]`, so `services:` with the documented health
# options inherits the same defect. A run that waits on it gets a connection, loses it mid-migration,
# and fails in the middle: measured here as `20 of 27` migrations failing with cascading
# `relation "profiles" does not exist` — a wall of errors whose real cause is one line of timing.
# This is the repo's `nc -z` lesson in another costume: a listener accepting is not a service ready.
#
# So readiness is TWO conditions, in order: the init marker in the logs, and then a query that
# actually answers.
set -uo pipefail
cd "$(dirname "$0")/../.."

IMAGE="${SCHEMA_DB_IMAGE:-public.ecr.aws/supabase/postgres:17.6.1.147}"
# ⟳ r1 MEDIUM 3 (claude): `${1:-…}` treats an EMPTY argument as absent, so
# `start-schema-db.sh "$SOME_EMPTY_VAR"` silently resolved to the default and `docker rm -f`
# ran against it — while the self-test's "an empty name is REFUSED" case passed by calling
# `refuses_name ""` directly, a path `main()` could never reach. The case would have gone on
# passing if this line were deleted. `${1-…}` (no colon) makes an empty argument EMPTY, which
# `refuses_name` then refuses — and `resolve_name` below makes the resolution itself testable.
resolve_name() { # $1 = the raw argument, possibly absent, possibly empty
  if [ "$#" -eq 0 ]; then printf '%s' "${PGCONTAINER:-m4_schema_gates}"; else printf '%s' "$1"; fi
}
NAME="$(resolve_name ${1+"$1"})"
READY_MARKER="PostgreSQL init process complete"
MIGRATIONS="supabase/migrations"
FIXTURE="scripts/ci/storage-service-fixture.sql"
AUTH_FIXTURE="scripts/ci/auth-service-fixture.sql"
SEED="scripts/ci/seed-corpus.sql"
WAIT_SECONDS="${SCHEMA_DB_WAIT:-180}"
PULL_ATTEMPTS="${SCHEMA_DB_PULL_ATTEMPTS:-5}"

# ⚠ REFUSE TO TOUCH THE SHARED LOCAL STACK. This script's first act is `docker rm -f`, and the
# developer's own Supabase container holds every other agent's work. Same rule, and the same reason,
# as `m4-base-db.sh`'s `valid_name`.
# ⛔⛔ AN ALLOW-LIST, NOT A DENY-LIST — ⟳ r1 MEDIUM (codex), and the deny-list version was live.
# This script's first act is `docker rm -f "$NAME"`, and `NAME` can come from `PGCONTAINER`, which
# is an ENVIRONMENT variable the caller may not even know is set. The old rule refused only
# `supabase_*`, `*_supabase*`, `postgres` and empty — so `PGCONTAINER=redis scripts/ci/start-schema-db.sh`
# destroyed an unrelated container, and the reviewer found a live one on this machine to prove it.
#
# A deny-list is a claim that you have thought of every name worth protecting; an allow-list is a
# claim that you know which names are yours. Only the second is checkable, and only the second fails
# SAFE — an unrecognised name is refused rather than deleted. The `m4_` prefix is the throwaway
# naming discipline the rest of this suite already uses (`m4_gate_mut_$$`, `m4_verify_base_…`).
#
# ⚠ STATED BOUND: this still permits deleting ANY `m4_*` container, including one another agent is
# using. That is deliberate — the alternative is a registry of live containers, which is state this
# script cannot read. The blast radius is now "throwaway databases this project creates" rather than
# "anything on the machine".
refuses_name() { # 0 = REFUSE this name
  case "$1" in
    supabase_*|*_supabase*|postgres|"") return 0 ;;   # kept: explicit, and first
    m4_[a-z0-9_]*) return 1 ;;                        # the only shape this script may destroy
    *) return 0 ;;                                    # unrecognised -> REFUSE, never delete
  esac
}

# The delay sequence, as a PURE function so the policy is testable without a registry. Doubling from
# 5s gives ~75s of patience across 5 attempts — long enough to outlast a burst, short enough that a
# genuinely unreachable registry still fails inside the job's timeout.
backoff_delays() { # $1 = attempts
  local i=1 d=5
  while [ "$i" -lt "$1" ]; do printf '%s ' "$d"; d=$((d * 2)); i=$((i + 1)); done
}

pull_image() {
  # Already local? Then there is nothing to ask the registry for — the common case, and it must not
  # pay for the retry logic.
  docker image inspect "$IMAGE" >/dev/null 2>&1 && return 0
  local attempt=1 err
  for d in $(backoff_delays "$PULL_ATTEMPTS") ""; do
    err=$(docker pull "$IMAGE" 2>&1) && return 0
    # ⛔ REPORT THE ERROR, DO NOT GUESS AT IT. The first version of this loop printed
    # "(registry throttling?)" on every failure — and the first time it ran on this machine the
    # daemon was simply DOWN, so it retried four times over 75 seconds and blamed a registry it had
    # never contacted. A retry message that asserts a cause it cannot observe sends the next person
    # to the wrong problem, which is the same defect this branch has now produced at three scales.
    echo "  pull attempt $attempt/$PULL_ATTEMPTS failed: ${err##*$'\n'}" >&2
    [ -z "$d" ] && break
    echo "  retrying in ${d}s" >&2
    sleep "$d"
    attempt=$((attempt + 1))
  done
  docker image inspect "$IMAGE" >/dev/null 2>&1   # a final, honest re-check
}

apply_sql() { # container file [role] -> 0 ok, 1 failed
  docker exec -i "$1" psql -U "${3:-postgres}" -d postgres -v ON_ERROR_STOP=1 -q < "$2"
}

main() {
  if refuses_name "$NAME"; then
    echo "CANNOT RUN — refusing container name '$NAME'." >&2
    echo "  This script's first act is \`docker rm -f\`, so it destroys ONLY names it recognises as" >&2
    echo "  its own: \`m4_<lowercase/digits/underscores>\`. Anything else — including an unrelated" >&2
    echo "  container inherited from \$PGCONTAINER — is refused rather than deleted." >&2
    return 2
  fi
  command -v docker >/dev/null 2>&1 || { echo "CANNOT RUN — no docker on PATH." >&2; return 2; }
  # ⚠ THE CLI EXISTING IS NOT THE DAEMON RUNNING, and the difference costs 75 seconds of backoff
  # against a registry that will never be reached. Measured: with Docker Desktop stopped, every
  # `docker pull` fails instantly and the retry loop blamed throttling. Ask the daemon directly.
  docker info >/dev/null 2>&1 || {
    echo "CANNOT RUN — the Docker daemon is not reachable (the CLI exists; the daemon is not up)." >&2
    echo "  On macOS: \`open -a Docker\`, then re-run. This is NOT a registry or schema problem." >&2
    return 2; }
  [ -d "$MIGRATIONS" ] || { echo "CANNOT RUN — no $MIGRATIONS directory." >&2; return 2; }
  [ -r "$FIXTURE" ]    || { echo "CANNOT RUN — no $FIXTURE." >&2; return 2; }
  [ -r "$AUTH_FIXTURE" ] || { echo "CANNOT RUN — no $AUTH_FIXTURE." >&2; return 2; }
  [ -r "$SEED" ]       || { echo "CANNOT RUN — no $SEED." >&2; return 2; }

  local n_mig
  n_mig=$(find "$MIGRATIONS" -name '*.sql' | wc -l | tr -d ' ')
  # An empty corpus is CANNOT RUN, not a clean sweep — a zero over nothing is not a result.
  [ "$n_mig" -gt 0 ] || { echo "CANNOT RUN — $MIGRATIONS holds no .sql files." >&2; return 2; }

  # ⛔ THE IMAGE PULL IS A DEPENDENCY ON SOMEONE ELSE'S RATE LIMITER — measured in CI 2026-09-14:
  #     docker: Error response from daemon: toomanyrequests: Rate exceeded
  # `public.ecr.aws` throttles unauthenticated pulls per source IP, and GitHub's runners share
  # addresses. The script FAILED CORRECTLY (rc=2, CANNOT RUN, no silent green) — but a gate that goes
  # red on someone else's traffic teaches people to re-run rather than to read, and a gate people
  # re-run reflexively is one they will eventually re-run past a real failure.
  # ⚠ A retry is right ONLY because the failure is transient AND distinguishable. Pulling is not
  # idempotent-ish guesswork: either the image is local afterwards or it is not, and `docker image
  # inspect` answers that. Nothing here retries the DATABASE build, which would mask real defects.
  pull_image || {
    echo "CANNOT RUN — could not obtain $IMAGE after $PULL_ATTEMPTS attempt(s)." >&2
    echo "  The last error is above. If it says 'toomanyrequests', the registry throttled us and" >&2
    echo "  this is NOT a schema failure — but treat it as NOT RUN, never as a pass." >&2
    return 2; }

  docker rm -f "$NAME" >/dev/null 2>&1
  docker run -d --name "$NAME" -e POSTGRES_PASSWORD=postgres "$IMAGE" >/dev/null || {
    echo "CANNOT RUN — could not start $IMAGE as '$NAME'." >&2; return 2; }

  # ⛔⛔ NO PIPE INTO `grep -q` — CAPTURE FIRST, MATCH SECOND. This file runs under `set -o pipefail`,
  # and `grep -q` exits the instant it matches, which SIGPIPEs `docker logs`; pipefail then returns
  # the PRODUCER's status. MEASURED 2026-09-13 against a container that was still streaming:
  #
  #     i=4  piped_rc=1    capture=absent
  #     i=5  piped_rc=141  capture=FOUND     <- SIGPIPE, on the very iteration that matched
  #
  # So the piped form returns 0 or 141 for the SAME true condition, depending on whether docker has
  # finished writing when grep exits — non-deterministic, and it reports failure exactly when the
  # thing was found. `mutate-live-schema-check.sh:97-102` carries this warning already, from the same
  # defect costing a whole review round; I reproduced it here by writing the piped form anyway.
  #
  # ⚠ AND THE LOOP'S RESULT IS REMEMBERED, NOT RE-DERIVED. The first version re-ran the check after
  # the loop, so one transient `docker logs` failure was read as proof the marker never appeared —
  # a second measurement standing in for the one that mattered.
  local i seen=no elapsed=0
  for i in $(seq 1 "$WAIT_SECONDS"); do
    local logs
    logs=$(docker logs "$NAME" 2>&1)
    case "$logs" in *"$READY_MARKER"*) seen=yes; elapsed=$i; break ;; esac
    sleep 1
    elapsed=$i
  done
  if [ "$seen" != yes ]; then
    # ⚠ Report the time that ACTUALLY elapsed, not the budget. The first version said "never appeared
    # in 180s" after waiting 10 — a false number inside the error message whose whole job is to tell
    # the next person what happened.
    echo "CANNOT RUN — '$READY_MARKER' did not appear within ${elapsed}s (budget ${WAIT_SECONDS}s)." >&2
    echo "  Treat this as NOT RUN. Last 20 log lines:" >&2
    docker logs "$NAME" 2>&1 | tail -20 >&2
    return 2
  fi

  local answered=no
  for i in $(seq 1 "$WAIT_SECONDS"); do
    if docker exec -i "$NAME" psql -U postgres -d postgres -tAc 'select 1' >/dev/null 2>&1; then
      answered=yes; break
    fi
    sleep 1
  done
  [ "$answered" = yes ] || {
    echo "CANNOT RUN — the post-init server never answered a query in ${WAIT_SECONDS}s." >&2; return 2; }

  # As `supabase_admin`: it owns the `storage` schema and `postgres` is not a superuser in this
  # image. The fixture hands ownership back to `postgres` itself — see its header.
  apply_sql "$NAME" "$FIXTURE" supabase_admin || {
    echo "CANNOT RUN — the storage fixture did not apply. Treat as NOT RUN." >&2; return 2; }

  # `auth.users` is owned by `supabase_auth_admin`, and the column is read by a trigger the
  # behavioural gate exercises — see the fixture's header for why exactly one column is added.
  apply_sql "$NAME" "$AUTH_FIXTURE" supabase_admin || {
    echo "CANNOT RUN — the auth fixture did not apply. Treat as NOT RUN." >&2; return 2; }

  local f fails=0
  for f in $(find "$MIGRATIONS" -name '*.sql' | sort); do
    if ! apply_sql "$NAME" "$f" 2>/tmp/schema-db-mig.err; then
      fails=$((fails + 1))
      echo "❌ $(basename "$f")"
      head -3 /tmp/schema-db-mig.err | sed 's/^/     /'
    fi
  done
  if [ "$fails" -ne 0 ]; then
    echo "❌ $fails of $n_mig migration(s) failed — the gates would read a schema that is not ours." >&2
    return 1
  fi

  # AFTER the migrations: the seed depends on the provisioning triggers they create, and it
  # asserts its own postcondition — see its header.
  apply_sql "$NAME" "$SEED" || {
    echo "CANNOT RUN — the corpus seed did not apply. Treat as NOT RUN." >&2; return 2; }

  # ⛔ THE POSTCONDITION, because "every migration exited 0" is not the same claim as "M4 is here".
  # This is the same discipline `m4-base-db.sh` applies to its rollback: assert the STATE, never
  # trust the exit codes that were supposed to produce it.
  local n_rel
  n_rel=$(docker exec -i "$NAME" psql -U postgres -d postgres -tAc \
    "select count(*) from pg_class where relname in ('video_artifacts','video_generations') and relnamespace='public'::regnamespace;" | tr -d '[:space:]')
  if [ "$n_rel" != "2" ]; then
    echo "❌ migrations applied but M4 is not present (video_artifacts+video_generations = ${n_rel:-<empty>}, wanted 2)." >&2
    return 1
  fi

  echo "✅ '$NAME' ready — $n_mig migrations applied, M4 PRESENT. Export:"
  echo "     PGCONTAINER=$NAME M4_PHASE=post"
}

self_test() {
  local pass=0 fail=0
  t() { # name expected actual
    if [ "$2" = "$3" ]; then pass=$((pass + 1)); else fail=$((fail + 1)); echo "  ✗ $1 — wanted '$2', got '$3'"; fi
  }
  # The name guard is the destructive one, so it gets most of the cases.
  refuses_name "supabase_db_youtube-playlist-summaries-cloud" && r=REFUSE || r=allow
  t "the shared local stack is REFUSED" REFUSE "$r"
  refuses_name "supabase_db_anything" && r=REFUSE || r=allow
  t "any supabase_ container is REFUSED" REFUSE "$r"
  refuses_name "my_supabase_db" && r=REFUSE || r=allow
  t "an embedded _supabase is REFUSED" REFUSE "$r"
  refuses_name "postgres" && r=REFUSE || r=allow
  t "the bare name 'postgres' is REFUSED" REFUSE "$r"
  refuses_name "" && r=REFUSE || r=allow
  t "an empty name is REFUSED, never defaulted" REFUSE "$r"
  # ⟳ r1 MEDIUM 3: assert on the RESOLUTION, not on `refuses_name` alone. These are the cases that
  # go red if `${1-…}` is written `${1:-…}` again — the ones the old case could not see.
  t "an EMPTY argument stays empty, so refuses_name gets to refuse it" "" "$(resolve_name "")"
  t "an ABSENT argument falls back to the default" "m4_schema_gates" "$(PGCONTAINER= resolve_name)"
  t "an explicit argument wins" "m4_review_x" "$(resolve_name m4_review_x)"
  # ⟳ 2026-09-14: the pull-retry policy. The I/O cannot be unit-tested without a registry; the
  # SCHEDULE can, and it is the part with a decision in it.
  t "five attempts means four waits" "5 10 20 40 " "$(backoff_delays 5)"
  t "one attempt means no wait at all" "" "$(backoff_delays 1)"
  t "the delays double, so patience grows without a long fixed sleep" "5 10 " "$(backoff_delays 3)"

  # ⟳ r1 MEDIUM (codex): the allow-list's own cases. Each of these was ALLOWED by the deny-list.
  refuses_name "redis" && r=REFUSE || r=allow
  t "an unrelated container name is REFUSED" REFUSE "$r"
  refuses_name "my-app-db" && r=REFUSE || r=allow
  t "a plausible foreign database is REFUSED" REFUSE "$r"
  refuses_name "M4_UPPER" && r=REFUSE || r=allow
  t "a name that only looks like ours is REFUSED" REFUSE "$r"
  refuses_name "m4" && r=REFUSE || r=allow
  t "the bare prefix with nothing after it is REFUSED" REFUSE "$r"
  refuses_name "m4_schema_gates" && r=REFUSE || r=allow
  t "the CI name is allowed" allow "$r"
  refuses_name "m4_ci_probe" && r=REFUSE || r=allow
  t "a throwaway probe name is allowed" allow "$r"
  echo "self-test: $((pass + fail)) cases, $pass passed, $fail failed"
  [ "$fail" -eq 0 ]
}

case "${1:-}" in
  --self-test) self_test; exit $? ;;
esac
main; exit $?
