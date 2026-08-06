#!/usr/bin/env bash
# Execute the proposed schema against the LIVE local Postgres inside a transaction that always
# rolls back. Verifies the DDL runs against real, populated tables — the class of defect that cost
# rounds 2, 3 and 4 (a physical rule fixed at one site and recurring at a sibling).
#
#   ./verify-schema.sh          -> exit 0 = every statement executed; 1 = first error, quoted
set -uo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)/schema"
CONTAINER="${PGCONTAINER:-supabase_db_youtube-playlist-summaries-cloud}"
SQL=$(printf 'begin;\n'; cat "$DIR"/0*.sql; printf '\n\\echo ALL_STATEMENTS_OK\nrollback;\n')
OUT=$(printf '%s' "$SQL" | docker exec -i "$CONTAINER" \
        psql -U postgres -d postgres -v ON_ERROR_STOP=1 2>&1)
echo "$OUT"
if grep -q ALL_STATEMENTS_OK <<<"$OUT"; then echo "✅ schema verified (rolled back)"; exit 0; fi
echo "❌ schema FAILED"; exit 1
