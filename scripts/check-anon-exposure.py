#!/usr/bin/env python3
"""Ratchet: the NEXT `public` object must not arrive anon-accessible unnoticed.

Backlog #54, half (b) — the DETECTION half. The default-revoke half (a) changes grants in
production and is deliberately not here.

WHY THIS EXISTS
---------------
Supabase grants `EXECUTE` to `anon` at CREATE FUNCTION time through `pg_default_acl`, and
`grant all on all tables in schema public` hands the session roles every table verb. Every
migration in this repo writes

    revoke all on function f(...) from public;
    grant execute on function f(...) to authenticated, service_role;

which READS as "anon excluded" and is not: `revoke … from public` removes the PUBLIC pseudo-role,
never the named role `anon`. Measured on prod 2026-08-11 (backlog #33): 26 of 30 `public` functions
are anon-executable.

The live exposure is bounded — of the 10 `security definer` functions anon can call, 8 check
`auth.uid()` (NULL for anon) and the other 2 were read in full and are benign. **But that safety
record is eight authors independently remembering, which is a record, not a mechanism.** Revoking on
the functions that exist today fixes those functions; the next one arrives exposed exactly as they
did. This script is the mechanism.

⭐ IT DEFAULTS TO PROD, AND THAT IS THE WHOLE POINT — MEASURED 2026-08-21.
The local stack and production DISAGREE about this:

    definer + anon-executable      local 5      prod 10
    money tables with TRUNCATE     local 4/5    prod 5/5

Prod is the exposed one. A ratchet pointed at the local container would have reported green over
the environment nobody is worried about — this project's own CLAUDE.md calls that out: *"a green
check over the wrong subject is an assertion in better packaging."* So the default target is prod
via the READ-ONLY `CLAUDE_RO_DATABASE_URL` (zero write grants across all 12 public tables, measured
2026-08-19), `--local` opts into the container, and the banner names which was read BEFORE any
verdict — the habit `scripts/subject_status.py` exists to enforce.

WHAT IT ASSERTS
---------------
RULE 1  Every `security definer` function in `public` that `anon` may EXECUTE is on ALLOW, and its
        stated reason for being safe is MECHANICALLY RE-CHECKED — not merely written down. If a
        future edit strips the `auth.uid()` guard out of an allow-listed function, this fails.
        The row asked for the allow-list to "fail loudly"; a prose reason nobody re-reads is the
        mute button it warned about.
RULE 2  The money tables' TRUNCATE exposure (backlog #30, still open) may not GROW. A hard "must be
        zero" assertion would be red from birth and get disabled; a baseline that can only fall is
        the honest shape while #30 is unfixed.
RULE 3  ⭐ NEW 2026-08-26 — M4's relations are READ-ONLY for the session roles. No `public`, `anon`
        or `authenticated` may hold INSERT, UPDATE, DELETE or TRUNCATE on any relation in the M4
        manifest, at TABLE or COLUMN level; and none may hold anything at all on the one relation the
        spec puts entirely out of reach. **This rule is here rather than in the M4 digest because it
        is the one class of fact a fingerprint cannot carry** — see `m4_catalog.SESSION_GRANTEES`.

        Three things worth knowing before editing it:

        1. **The relation list is DERIVED from the manifest**, not typed here. A hand-list would go
           stale the first time M4 gains a table, and would go stale SILENTLY — the check would keep
           passing over an unlisted relation. If the manifest cannot be read, RULE 3 refuses to run.
        2. **TRUNCATE is the reason this rule exists at all.** r7 M4 (codex) measured
           `grant truncate on video_artifacts to anon` passing BOTH gates: the digest listed only
           SELECT/INSERT/UPDATE/DELETE, and this script's money-table rule covers five tables, none
           of them M4's. TRUNCATE fires neither RLS nor row triggers, so it is the one verb that
           walks past every guard the append-only design puts in the way.
        3. **Pre-M4 it is VACUOUS, and it says so out loud.** Until `0027` applies, none of these
           relations exist and the rule has nothing to check. The banner reports the count it found;
           `0 present` is a fact the reader can see, not a silent pass. What actually proves the rule
           bites is `mutate-live-schema-check.sh`, which runs it against databases where M4 IS
           present and requires exit 1.

Usage:
    ./scripts/check-anon-exposure.py            # prod (read-only) — the subject that matters
    ./scripts/check-anon-exposure.py --local    # the docker stack
    ./scripts/check-anon-exposure.py --local --database <db>   # a named db in the container
    ./scripts/check-anon-exposure.py --self-test
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTAINER = "supabase_db_youtube-playlist-summaries-cloud"

# The five tables backlog #30 names. Kept explicit rather than pattern-matched: a money table that
# stops matching a pattern silently leaves the check, which is the failure mode this file is about.
MONEY_TABLES = ("spend_ledger", "ledger_audit", "serve_owner_budget",
                "serve_model_charge", "guardrail_config")

# Backlog #30 is OPEN: all five are TRUNCATE-able by session roles on prod today. The number is the
# debt, written down where it can only be paid off. Lower it when #30 lands; never raise it.
TRUNCATE_BASELINE = 5

# ── the allow-list ──────────────────────────────────────────────────────────────────────────────
# name -> (kind, why). KIND IS THE LOAD-BEARING FIELD: it selects a check that is re-run against the
# live definition every time, so an entry cannot outlive the property that justified it.
#
#   uid       the body calls auth.uid(), which is NULL for anon, so the function refuses to act
#   trigger   returns `trigger` — PostgREST cannot invoke it at all, so the grant is inert
#   readonly  performs no INSERT/UPDATE/DELETE/TRUNCATE; it can only report, never change anything
ALLOW: dict[str, tuple[str, str]] = {
    "create_share_token":           ("uid",      "mints a token for the caller's own row"),
    "list_share_tokens":            ("uid",      "lists the caller's own tokens"),
    "revoke_share_token":           ("uid",      "revokes a token the caller owns"),
    "revoke_all_share_tokens":      ("uid",      "revokes tokens the caller owns"),
    "request_cancel_job":           ("uid",      "cancels a job the caller owns"),
    "request_cancel_playlist_jobs": ("uid",      "cancels jobs on the caller's playlist"),
    "reserve_serve_model":          ("uid",      "money path — reserves against the caller's budget"),
    "settle_serve_model":           ("uid",      "money path — settles the caller's reservation"),
    "handle_new_user":              ("trigger",  "auth trigger; not reachable over PostgREST"),
    "reserve_serve_model_meta":     ("readonly", "reports its own catalog metadata; writes nothing"),
}

WRITE_VERB = re.compile(r"\b(insert|update|delete|truncate)\b", re.IGNORECASE)

# ── RULE 3 ──────────────────────────────────────────────────────────────────────────────────────
# The verbs no session role may hold on an M4 relation. TRUNCATE is the one that was invisible to
# both gates before today: it is not in the digest's REL_PRIVS and it bypasses RLS and row triggers.
FORBIDDEN_ON_M4 = ("INSERT", "UPDATE", "DELETE", "TRUNCATE")
# Column-level grants exist only for these verbs — has_any_column_privilege rejects the others.
COLUMN_LEVEL = ("INSERT", "UPDATE", "REFERENCES")
MANIFEST = ROOT / "docs/superpowers/specs/m4/live-manifest.txt"


def m4_functions(manifest_text: str) -> list[str]:
    """Every function NAME in the M4 manifest. PURE. Derived, for the same reason as m4_relations."""
    out = []
    for line in manifest_text.splitlines():
        if line.startswith("fn:"):
            out.append(line[3:].split("(", 1)[0])
    return sorted(set(out))


def m4_relations(manifest_text: str) -> list[str]:
    """Every relation name in the M4 manifest. PURE.

    DERIVED, never typed: the manifest is generated from the spec by `gen-m4-manifest.py`, so a table
    added to M4 arrives here without anyone remembering. A hand-list would keep passing over the new
    relation, which is the failure this project has a name for — a vocabulary that silently stops
    matching is worse than no check.
    """
    out = []
    for line in manifest_text.splitlines():
        for prefix in ("table:", "view:"):
            if line.startswith(prefix):
                out.append(line[len(prefix):].split("@", 1)[0])
    return sorted(set(out))


def justification_holds(kind: str, returns: str, body: str) -> bool:
    """Does the reason this function is allow-listed STILL hold, per the live definition?"""
    if kind == "uid":
        return "auth.uid()" in body
    if kind == "trigger":
        return returns.strip().lower() == "trigger"
    if kind == "readonly":
        return not WRITE_VERB.search(body)
    return False                      # an unknown kind is never a justification


# ── the rule — pure; no database, no filesystem ─────────────────────────────────────────────────

def evaluate(
    funcs: list[tuple[str, bool, str, str]],
    money: list[tuple[str, bool]],
    allow: dict[str, tuple[str, str]] | None = None,
    baseline: int = TRUNCATE_BASELINE,
) -> list[str]:
    """(name, anon_exec, returns, body) rows + (table, truncatable) rows  ->  problems.

    Split from the fetch deliberately: the RULE is testable in milliseconds with fixtures, and only
    the FETCH ever needed a database. Three ratchets in this repo went eight days untestable for
    exactly the opposite arrangement (memory: separate-the-rule-from-the-fetch).
    """
    allow = ALLOW if allow is None else allow
    problems: list[str] = []
    present = {name for name, _, _, _ in funcs}

    # RULE 1a — exposed and unlisted. The core assertion.
    for name, anon_exec, *_ in sorted(funcs):
        if not anon_exec or name in allow:
            continue
        problems.append(
            f"UNLISTED           `{name}` is SECURITY DEFINER and anon-EXECUTable, and is not on\n"
            "                   ALLOW. It runs as its owner, so anon calling it bypasses RLS.\n"
            "                   Either revoke EXECUTE from anon, or add it to ALLOW with a kind\n"
            "                   whose check actually proves it is safe.")

    # RULE 1b — an allow-list entry naming a function that no longer exists.
    # NOTE the predicate: "does not exist", NOT "is not currently exposed". A function that exists
    # but is not anon-executable is BETTER than allowed, and calling that stale would make the
    # check fail on the local stack purely because local exposes fewer than prod.
    for name in sorted(set(allow) - present):
        problems.append(
            f"STALE ALLOW ENTRY  `{name}` is on ALLOW but no such function exists here.\n"
            "                   Delete the entry. A list that quietly stops matching is standing\n"
            "                   permission for whatever takes the name next.")

    # RULE 1c — the justification itself, re-checked against the live definition.
    for name, anon_exec, returns, body in sorted(funcs):
        if name not in allow or not anon_exec:
            continue
        kind, why = allow[name]
        if not justification_holds(kind, returns, body):
            problems.append(
                f"JUSTIFICATION GONE `{name}` is allowed as kind '{kind}' ({why}), and that is no\n"
                "                   longer true of its definition. The grant is unchanged; the\n"
                "                   reason it was safe has been edited away.")

    # RULE 2 — the #30 debt may shrink, never grow.
    exposed = sorted(t for t, trunc in money if trunc)
    if len(exposed) > baseline:
        problems.append(
            f"TRUNCATE GREW      {len(exposed)} money tables are TRUNCATE-able by a session role,\n"
            f"                   baseline is {baseline}: {', '.join(exposed)}\n"
            "                   RLS does not cover TRUNCATE. Backlog #30.")
    elif len(exposed) < baseline:
        problems.append(
            f"LOWER THE BASELINE {len(exposed)} money tables are TRUNCATE-able, baseline says\n"
            f"                   {baseline}. Progress — set TRUNCATE_BASELINE = {len(exposed)} so it\n"
            "                   cannot silently come back.")
    return problems


def evaluate_m4(
    m4rel: list[tuple[str, str, str]],
    no_access: tuple[str, ...] = (),
    expect_roles: tuple[str, ...] = (),
) -> list[str]:
    """(relation, role, comma-separated privileges held) rows -> problems. PURE.

    RULE 3. Kept as its own function rather than folded into `evaluate()` so the twenty existing
    self-test cases keep meaning what they meant — and so this rule's own cases read as one subject.
    `main()` calls both; `self_test` asserts that it does, because a rule with no caller is the
    third-most-expensive mistake in this repo's history and has now been made four times.
    """
    problems: list[str] = []
    for rel, role, privs in sorted(m4rel):
        held = {p.strip().upper() for p in privs.split(",") if p.strip()}
        if rel in no_access:
            if held:
                problems.append(
                    f"M4 OUT OF REACH    `{role}` holds {', '.join(sorted(held))} on `{rel}`, which\n"
                    "                   the spec revokes from every session role and grants only to\n"
                    "                   service_role. Any session-role privilege here is a defect.")
            continue
        writes = sorted(held & set(FORBIDDEN_ON_M4))
        if writes:
            problems.append(
                f"M4 NOT READ-ONLY   `{role}` holds {', '.join(writes)} on `{rel}`. M4's session-role\n"
                "                   contract is SELECT and nothing else — the write path is\n"
                "                   service_role via SECURITY DEFINER RPC. TRUNCATE in that list is\n"
                "                   the worst case: it fires neither RLS nor row triggers, so the\n"
                "                   append-only guards never see it.")

    # ⭐ FAIL CLOSED ON A MISSING ROLE. The fetch drops a role that does not exist in this database,
    # which is right for `to_regrole` and wrong as a verdict: "anon holds nothing here" and "anon is
    # not a thing here" produce the same empty result, and only one of them is a passing state.
    # Same shape as `_guard()` in m4_catalog.py, which digests 'ABSENT' rather than skipping.
    seen_rels = {rel for rel, _, _ in m4rel}
    seen_roles = {role for _, role, _ in m4rel}
    if seen_rels:
        for role in sorted(set(expect_roles) - seen_roles):
            problems.append(
                f"ROLE NOT PRESENT   RULE 3 expected to check `{role}` and this database has no such\n"
                f"                   role, while {len(seen_rels)} M4 relation(s) DO exist. The rule\n"
                "                   reported nothing about it, which is not the same as a pass.")
    return problems


def evaluate_m4_functions(m4fn: list[tuple[str, str, bool]]) -> list[str]:
    """(function, role, anon-may-execute) -> problems. PURE. RULE 3, function half.

    There is no allow-list here on purpose. The spec revokes EXECUTE on every M4 function from
    public/anon/authenticated and grants it back to exactly one principal that is not a session role,
    so the correct answer for every row is False and any True is a defect — not a judgement call.
    """
    return [
        f"M4 FN EXECUTABLE   `{role}` may EXECUTE `{fn}()`. Every M4 function is revoked from every\n"
        "                   session role by the spec; there is no allow-list for this and no case\n"
        "                   where it is correct. On production the platform grants EXECUTE at CREATE\n"
        "                   time, so this is the state the schema arrives in unless a revoke lands."
        for fn, role, may in sorted(m4fn) if may
    ]


# ── the fetch ───────────────────────────────────────────────────────────────────────────────────

SQL = r"""
\echo ---FUNCS---
select p.proname
       || E'\t' || has_function_privilege('anon', p.oid, 'EXECUTE')::text
       || E'\t' || replace(pg_get_function_result(p.oid), E'\t', ' ')
       || E'\t' || replace(replace(pg_get_functiondef(p.oid), E'\n', ' '), E'\t', ' ')
  from pg_proc p join pg_namespace n on n.oid = p.pronamespace
 where n.nspname = 'public' and p.prosecdef
 order by p.proname;
\echo ---MONEY---
select c.relname || E'\t'
       || (has_table_privilege('anon', c.oid, 'TRUNCATE')
           or has_table_privilege('authenticated', c.oid, 'TRUNCATE'))::text
  from pg_class c join pg_namespace n on n.oid = c.relnamespace
 where n.nspname = 'public' and c.relkind = 'r' and c.relname = any(%s)
 order by c.relname;
\echo ---M4REL---
-- RULE 3. One row per (M4 relation, session role) that EXISTS here. A relation `0027` has not
-- created yet produces no row, and main() reports the count it found rather than passing quietly.
--
-- TWO privilege functions, because a grant can hide at either level. `has_any_column_privilege` is
-- what makes `grant insert (blob_key) on video_artifacts to anon` visible — it moves no table ACL
-- (r6 B2, measured). It accepts only SELECT/INSERT/UPDATE/REFERENCES: DELETE and TRUNCATE have no
-- column-level form and asking for them RAISES rather than returning false.
--
-- The two lists are concatenated and de-duplicated in Python. Doing it in SQL needs LATERAL to
-- correlate the derived table, and a plain sub-select-in-FROM cannot see `r.rolname`.
select c.relname || E'\t' || r.rolname || E'\t' ||
       coalesce((select string_agg(p, ',' order by p)
                   from unnest(%s) p where has_table_privilege(r.rolname, c.oid, p)), '')
       || ',' ||
       coalesce((select string_agg(p, ',' order by p)
                   from unnest(%s) p where has_any_column_privilege(r.rolname, c.oid, p)), '')
  from pg_class c
  join pg_namespace n on n.oid = c.relnamespace
  cross join (select p as rolname from unnest(%s) p
               where p = 'public' or to_regrole(p) is not null) r
 where n.nspname = 'public' and c.relkind in ('r','v','m','p') and c.relname = any(%s)
 order by c.relname, r.rolname;
\echo ---M4FN---
-- RULE 3, function half. ⟳ FORK (a) STEP 5: `FN_GRANTEES` left the digest with the relation
-- grantees, so this is now the only thing asserting that no session role can EXECUTE an M4 function.
-- The spec revokes every one of them from public/anon/authenticated and grants EXECUTE to exactly
-- one principal (service_role, on record_artifact) — so for a SESSION role the expected answer is
-- ALWAYS false, with no allow-list and no exception.
select p.proname || E'\t' || r.rolname || E'\t'
       || has_function_privilege(r.rolname, p.oid, 'EXECUTE')::text
  from pg_proc p
  join pg_namespace n on n.oid = p.pronamespace
  cross join (select q as rolname from unnest(%s) q
               where q = 'public' or to_regrole(q) is not null) r
 where n.nspname = 'public' and p.proname = any(%s)
 order by p.proname, r.rolname;
"""


def pg_bool(s: str) -> bool:
    """⚠ FAIL-CLOSED PARSE, and it exists because this file shipped with a fail-OPEN one.

    Measured 2026-08-21: `boolean::text` in Postgres yields `true`/`false`, while psql's *display*
    of an uncast boolean is `t`/`f`. The first version of the fetch compared against `"t"`, so every
    row parsed as False and the check reported **0 anon-executable functions on prod** — where ten
    had been measured by hand minutes earlier. A green ratchet over an exposed database.

    It was caught only by comparing against that hand measurement. `--self-test` was 16/16 green
    throughout, because the self-test drives `evaluate()` with fixtures: THE RULE WAS RIGHT AND THE
    FETCH WAS BROKEN, and a rule/fetch split is structurally blind to that. Hence this function —
    the parse is now pure, and therefore testable — and hence it RAISES rather than returning False
    on anything unexpected: defaulting an unparseable privilege to "not exposed" is the same
    fail-open shape one layer down.
    """
    v = s.strip().lower()
    if v in ("t", "true"):
        return True
    if v in ("f", "false"):
        return False
    raise ValueError(f"not a postgres boolean: {s!r}")


def parse_rows(stdout: str) -> tuple[list[tuple[str, bool, str, str]],
                                     list[tuple[str, bool]],
                                     list[tuple[str, str, str]],
                                     list[tuple[str, str, bool]]]:
    """Pure: psql output -> (funcs, money, m4rel, m4fn). The FETCH's own parsing, under test."""
    funcs: list[tuple[str, bool, str, str]] = []
    money: list[tuple[str, bool]] = []
    m4rel: list[tuple[str, str, str]] = []
    m4fn: list[tuple[str, str, bool]] = []
    section = None
    for raw in stdout.splitlines():
        if raw.startswith("---FUNCS---"):
            section = "f"; continue
        if raw.startswith("---MONEY---"):
            section = "m"; continue
        if raw.startswith("---M4REL---"):
            section = "r"; continue
        if raw.startswith("---M4FN---"):
            section = "x"; continue
        if not raw.strip():
            continue
        parts = raw.split("\t")
        if section == "r" and len(parts) >= 3:
            m4rel.append((parts[0], parts[1], parts[2]))
            continue
        if section == "x" and len(parts) >= 3:
            m4fn.append((parts[0], parts[1], pg_bool(parts[2])))
            continue
        if section == "f" and len(parts) >= 4:
            funcs.append((parts[0], pg_bool(parts[1]), parts[2], parts[3]))
        elif section == "m" and len(parts) >= 2:
            money.append((parts[0], pg_bool(parts[1])))
    return funcs, money, m4rel, m4fn


# ⟳ r5 M4 (claude) — ONE READER OF THIS CONFIG VALUE, NOT TWO THAT DISAGREE.
# `m4_catalog.py` grew a second `read_only_url` "using the same mechanism", and the copies had
# drifted three ways: which lines match (stripped vs unstripped, so an indented assignment was
# missed by one), which quotes are stripped (double-only vs both), and what an empty value returns
# (`""` vs `None`). Two readers of one secret that disagree about which values EXIST is exactly the
# shape `check-vocabulary-collisions.py` hunts, one layer below where that script looks.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from m4_catalog import (M4_NO_SESSION_ACCESS, SESSION_GRANTEES,  # noqa: E402
                        psql_cmd, psql_env, read_only_url)


def pg_array(items) -> str:
    """A Postgres text[] literal. PURE. Values here are identifiers from the repo, never input."""
    return "ARRAY[" + ",".join(f"'{i}'" for i in items) + "]::text[]"


def load_m4_relations() -> list[str]:
    """The manifest's relations, or exit 2. RULE 3 refuses to run rather than run over nothing."""
    if not MANIFEST.is_file():
        print(f"CANNOT RUN — RULE 3 needs the M4 manifest and {MANIFEST} is missing.")
        print("Regenerate it with scripts/gen-m4-manifest.py. TREAT THIS AS NOT RUN.")
        sys.exit(2)
    rels = m4_relations(MANIFEST.read_text())
    if not rels:
        print(f"CANNOT RUN — {MANIFEST} names no tables or views, which is not a state it can be in.")
        print("TREAT THIS AS NOT RUN.")
        sys.exit(2)
    return rels


def fetch(local: bool, database: str = "postgres") -> tuple[
        list[tuple[str, bool, str, str]], list[tuple[str, bool]],
        list[tuple[str, str, str]], list[tuple[str, str, bool]], list[str], str]:
    """Returns (funcs, money, m4rel, m4_rels_expected, subject). Exits 2 rather than returning empty
    on any failure — 'cannot run' is a FAILURE, never a pass, and an empty catalog would read as
    'nothing exposed'."""
    m4rels = load_m4_relations()
    m4fns = m4_functions(MANIFEST.read_text())
    if not m4fns:
        print(f"CANNOT RUN — {MANIFEST} names no functions. TREAT THIS AS NOT RUN.")
        sys.exit(2)
    sql = SQL % (pg_array(MONEY_TABLES), pg_array(FORBIDDEN_ON_M4), pg_array(COLUMN_LEVEL),
                 pg_array(SESSION_GRANTEES), pg_array(m4rels),
                 pg_array(SESSION_GRANTEES), pg_array(m4fns))
    url = None
    if local:
        # ⟳ r7 M (codex): the database used to be hard-coded to `postgres`, which is right for the
        # container's own app database and made every OTHER database unreachable — including the
        # mutated clones the harness builds, which is the only place RULE 3 can be proven to bite.
        subject = f"LOCAL container {CONTAINER} db '{database}'"
    else:
        url = read_only_url()
        if not url:
            print("CANNOT RUN — CLAUDE_RO_DATABASE_URL is not set (checked env and .env.local).")
            print("TREAT THIS AS NOT RUN. Use --local only if you mean the container.")
            sys.exit(2)
        subject = "PRODUCTION (read-only claude_ro)"

    # Same one mechanism as --local (docker + psql), a different target. Deliberately not a second
    # driver — and now literally the same function, see the note on read_only_url above. The URL
    # travels in the ENVIRONMENT, not in argv: `ps` used to show the password (r5 L1, MEASURED).
    cmd = psql_cmd(database, url=url, container=CONTAINER)
    p = subprocess.run(cmd, input=sql, capture_output=True, text=True, env=psql_env(url))
    if p.returncode != 0:
        print(f"CANNOT RUN — could not read the catalog from {subject}. TREAT THIS AS NOT RUN.")
        print((p.stderr or p.stdout)[-1200:])
        sys.exit(2)

    try:
        funcs, money, m4rel, m4fn = parse_rows(p.stdout)
    except ValueError as e:
        print(f"CANNOT RUN — unparseable catalog output from {subject}: {e}")
        print("TREAT THIS AS NOT RUN.")
        sys.exit(2)

    if not funcs:
        print(f"CANNOT RUN — {subject} returned no SECURITY DEFINER functions at all, which is not")
        print("a state this schema can be in. TREAT THIS AS NOT RUN.")
        sys.exit(2)
    return funcs, money, m4rel, m4fn, m4rels, subject


# ── --self-test ─────────────────────────────────────────────────────────────────────────────────

def self_test() -> int:
    cases: list[tuple[str, bool]] = []

    def case(name: str, ok: bool) -> None:
        cases.append((name, ok))

    UID = ("f", True, "boolean", "create function f() ... where owner_id = auth.uid() ...")
    ALLOW1 = {"f": ("uid", "checks the caller")}
    MONEY_OK = [(t, True) for t in MONEY_TABLES]

    case("a clean catalog produces no problems", evaluate([UID], MONEY_OK, ALLOW1) == [])

    # RULE 1a
    case("an exposed, unlisted definer function FAILS",
         any("UNLISTED" in p for p in evaluate([("g", True, "boolean", "body")], MONEY_OK, ALLOW1)))
    # ⚠ `UID` is in the catalog here on purpose. The first draft of this case passed only `g`, and
    # the STALE ALLOW ENTRY rule correctly fired for `f` — the fixture was wrong, not the rule.
    case("an unlisted definer function that anon CANNOT call is fine",
         evaluate([UID, ("g", False, "boolean", "body")], MONEY_OK, ALLOW1) == [])

    # RULE 1b — and the predicate that keeps it environment-robust
    case("an ALLOW entry naming a nonexistent function FAILS",
         any("STALE ALLOW ENTRY" in p for p in evaluate([], MONEY_OK, {"gone": ("uid", "x")})) )
    # ⭐ measured 2026-08-21: local exposes 5 definer functions, prod 10. If "stale" meant "not
    # currently exposed", the prod-derived list would fail on the local stack for no real reason.
    case("a function that EXISTS but is not exposed is NOT stale",
         evaluate([("f", False, "boolean", "no guard here")], MONEY_OK, ALLOW1) == [])

    # RULE 1c — the justification is re-checked, not trusted
    case("kind 'uid' FAILS when auth.uid() is edited out",
         any("JUSTIFICATION GONE" in p
             for p in evaluate([("f", True, "boolean", "no guard at all")], MONEY_OK, ALLOW1)))
    case("kind 'trigger' passes only for a trigger return type",
         evaluate([("f", True, "trigger", "x")], MONEY_OK, {"f": ("trigger", "y")}) == []
         and any("JUSTIFICATION GONE" in p for p in
                 evaluate([("f", True, "boolean", "x")], MONEY_OK, {"f": ("trigger", "y")})))
    case("kind 'readonly' FAILS when a write verb appears",
         any("JUSTIFICATION GONE" in p for p in
             evaluate([("f", True, "jsonb", "begin insert into t values (1); end")],
                      MONEY_OK, {"f": ("readonly", "reads only")})))
    case("kind 'readonly' passes a genuinely read-only body",
         evaluate([("f", True, "jsonb", "select count(*) from pg_proc")],
                  MONEY_OK, {"f": ("readonly", "reads only")}) == [])
    case("an UNKNOWN kind is never a justification",
         any("JUSTIFICATION GONE" in p for p in
             evaluate([("f", True, "boolean", "auth.uid()")], MONEY_OK, {"f": ("vibes", "trust me")})))
    # A word-boundary check, not a substring one: `updated_at` must not read as UPDATE.
    case("'readonly' is not fooled by updated_at / deleted_at column names",
         evaluate([("f", True, "jsonb", "select updated_at, deleted_at from t")],
                  MONEY_OK, {"f": ("readonly", "reads only")}) == [])

    # RULE 2
    case("TRUNCATE growth FAILS",
         any("TRUNCATE GREW" in p for p in
             evaluate([UID], MONEY_OK + [("new_money_table", True)], ALLOW1)))
    case("TRUNCATE shrink asks for the baseline to be lowered",
         any("LOWER THE BASELINE" in p for p in
             evaluate([UID], [(t, i > 0) for i, t in enumerate(MONEY_TABLES)], ALLOW1)))
    case("a table without TRUNCATE is not counted",
         evaluate([UID], [(t, False) for t in MONEY_TABLES], ALLOW1) != []  # asks to lower to 0
         and "LOWER THE BASELINE" in evaluate([UID], [(t, False) for t in MONEY_TABLES], ALLOW1)[0])

    # ⭐ THE PARSE — the half the rule/fetch split was blind to. These cases exist because this
    # file shipped with `parts[1] == "t"`, which reads `boolean::text` output (`true`/`false`) as
    # False for every row and reported prod as clean while ten functions were exposed.
    def raises(fn) -> bool:
        try:
            fn()
            return False
        except ValueError:
            return True

    case("pg_bool reads Postgres's ::text form", pg_bool("true") and not pg_bool("false"))
    case("pg_bool still reads psql's display form", pg_bool("t") and not pg_bool("f"))
    case("pg_bool RAISES on anything else rather than defaulting to False",
         raises(lambda: pg_bool("yes")) and raises(lambda: pg_bool("")))
    case("parse_rows returns exposure as TRUE for a true row",
         parse_rows("---FUNCS---\nf\ttrue\tboolean\tbody\n")[0] == [("f", True, "boolean", "body")])
    case("parse_rows reads the money section",
         parse_rows("---MONEY---\nspend_ledger\ttrue\n")[1] == [("spend_ledger", True)])
    case("parse_rows keeps the two sections separate",
         parse_rows("---FUNCS---\nf\tfalse\tboolean\tb\n---MONEY---\nt1\tfalse\n")[:2]
         == ([("f", False, "boolean", "b")], [("t1", False)]))

    # ── RULE 3 ──────────────────────────────────────────────────────────────────────────────────
    ROLES = ("public", "anon", "authenticated")
    CLEAN = [(r, g, "SELECT,") for r in ("video_artifacts", "workspaces") for g in ROLES]

    case("RULE 3: SELECT-only on every M4 relation is clean",
         evaluate_m4(CLEAN, (), ROLES) == [])
    case("RULE 3: a table-level INSERT to anon FAILS",
         any("M4 NOT READ-ONLY" in p for p in
             evaluate_m4([("video_artifacts", "anon", "INSERT,SELECT,")], (), ())))
    # ⭐ r7 M4 (codex) — the case NEITHER gate caught before today.
    case("RULE 3: TRUNCATE FAILS, and it is named in the message",
         any("TRUNCATE" in p and "M4 NOT READ-ONLY" in p for p in
             evaluate_m4([("video_artifacts", "anon", "SELECT,TRUNCATE,")], (), ())))
    # ⭐ r6 B2 — the grant that moves no table ACL. The column-level list arrives after the comma.
    case("RULE 3: a COLUMN-level insert FAILS just like a table-level one",
         any("M4 NOT READ-ONLY" in p for p in
             evaluate_m4([("video_artifacts", "anon", "SELECT,INSERT")], (), ())))
    case("RULE 3: authenticated is checked too, not only anon",
         any("`authenticated`" in p for p in
             evaluate_m4([("workspaces", "authenticated", "SELECT,DELETE,")], (), ())))
    case("RULE 3: the out-of-reach relation FAILS on a mere SELECT",
         any("M4 OUT OF REACH" in p for p in
             evaluate_m4([("video_generations_collectable", "anon", "SELECT,")],
                         ("video_generations_collectable",), ())))
    case("RULE 3: the out-of-reach relation is clean when NOTHING is held",
         evaluate_m4([("video_generations_collectable", "anon", ",")],
                     ("video_generations_collectable",), ()) == [])
    # ⭐ the fail-closed half: silence is not agreement.
    case("RULE 3: an EXPECTED role that produced no row FAILS when relations exist",
         any("ROLE NOT PRESENT" in p for p in
             evaluate_m4([("workspaces", "anon", "SELECT,")], (), ROLES)))
    case("RULE 3: a missing role is NOT an error when no M4 relation exists yet",
         evaluate_m4([], (), ROLES) == [])
    case("RULE 3: pre-0027 (no relations at all) is vacuous, not a failure",
         evaluate_m4([], (), ()) == [])
    case("parse_rows reads the M4REL section",
         parse_rows("---M4REL---\nvideo_artifacts\tanon\tSELECT,\n")[2]
         == [("video_artifacts", "anon", "SELECT,")])
    case("m4_relations DERIVES names from the manifest, tables and views alike",
         m4_relations("table:workspaces@abc\nview:video_summary_current@def\nfn:x()@ghi\n")
         == ["video_summary_current", "workspaces"])
    case("m4_relations ignores every non-relation line",
         m4_relations("col:a.b@1\ntrg:c.d@2\nidx:e@3\npol:f.g@4\ncon:h.i@5\n") == [])

    # ── RULE 3, function half (fork (a) step 5: FN_GRANTEES left the digest) ────────────────────
    case("RULE 3 fn: no session role executing any M4 function is clean",
         evaluate_m4_functions([("record_artifact", "anon", False),
                                ("slot_kind", "authenticated", False)]) == [])
    case("RULE 3 fn: anon EXECUTE on an M4 function FAILS",
         any("M4 FN EXECUTABLE" in p for p in
             evaluate_m4_functions([("record_artifact", "anon", True)])))
    case("RULE 3 fn: authenticated and public are checked too",
         len(evaluate_m4_functions([("slot_kind", "authenticated", True),
                                    ("slot_kind", "public", True)])) == 2)
    # ⚠ there is deliberately NO allow-list here — assert that, so one cannot be added silently.
    case("RULE 3 fn: no function is exempt, not even record_artifact",
         any("record_artifact" in p for p in
             evaluate_m4_functions([("record_artifact", "authenticated", True)])))
    case("RULE 3 fn: an empty catalog is vacuous, not a failure",
         evaluate_m4_functions([]) == [])
    case("m4_functions DERIVES names from the manifest, stripping the signature",
         m4_functions("fn:record_artifact(a uuid, b text)@x\nfn:slot_kind(p text)@y\ntable:z@w\n")
         == ["record_artifact", "slot_kind"])
    case("parse_rows reads the M4FN section and its boolean",
         parse_rows("---M4FN---\nslot_kind\tanon\tfalse\n")[3]
         == [("slot_kind", "anon", False)])
    case("main() calls evaluate_m4_functions too",
         "evaluate_m4_functions(" in Path(__file__).read_text().split("def main()", 1)[-1])

    # ⭐⭐ THE CALLER CHECK. `evaluate_m4` being correct proves nothing if main() never calls it, and
    # this repo has now shipped a working gate with no caller three times. Assert the wiring, not
    # just the rule — and assert it at BOTH ends, since the schema-gate suite is the only thing that
    # runs this file without a human typing its name.
    main_src = Path(__file__).read_text().split("def main()", 1)[-1]
    case("main() calls evaluate_m4 — a rule with no caller is not a gate",
         "evaluate_m4(" in main_src)
    case("main() passes the out-of-reach list and the expected roles",
         "M4_NO_SESSION_ACCESS" in main_src and "SESSION_GRANTEES" in main_src)
    gates = ROOT / "scripts/check-schema-gates.sh"
    case("check-schema-gates.sh runs this file",
         gates.is_file() and "check-anon-exposure.py" in gates.read_text())

    # the shipped config must itself be coherent
    case("every shipped ALLOW entry uses a known kind",
         all(k in ("uid", "trigger", "readonly") for k, _ in ALLOW.values()))
    case("the shipped ALLOW list is non-empty and reasoned",
         len(ALLOW) >= 10 and all(why.strip() for _, why in ALLOW.values()))

    failed = [n for n, ok in cases if not ok]
    for name, ok in cases:
        print(f"  {'✓' if ok else '✗'} {name}")
    print(f"\n{len(cases) - len(failed)}/{len(cases)} passed")
    return 1 if failed else 0


def arg_value(flag: str, default: str) -> str:
    """`--flag value` from argv, or the default. PURE enough; argv is the only input."""
    if flag in sys.argv:
        i = sys.argv.index(flag)
        if i + 1 < len(sys.argv):
            return sys.argv[i + 1]
    return default


def main() -> int:
    funcs, money, m4rel, m4fn, m4rels, subject = fetch(
        local="--local" in sys.argv, database=arg_value("--database", "postgres"))

    # Say what was READ before saying whether it passed — subject_status.py's rule, applied here
    # because this check has two possible subjects that genuinely disagree.
    exposed = [n for n, a, _, _ in funcs if a]
    present = sorted({rel for rel, _, _ in m4rel})
    print(f"subject: {subject}")
    print(f"         {len(funcs)} SECURITY DEFINER function(s) in public, "
          f"{len(exposed)} anon-EXECUTable")
    print(f"         money tables TRUNCATE-able by a session role: "
          f"{sum(1 for _, t in money if t)}/{len(money)} (baseline {TRUNCATE_BASELINE})")
    # ⚠ RULE 3's coverage is stated as a COUNT, never as a verdict. Pre-0027 it is 0 of N and the
    # rule checks nothing — which is fine and must be VISIBLE, because a rule that silently checks
    # an empty set reads exactly like a rule that passed.
    print(f"         M4 functions present: {len({f for f, _, _ in m4fn})}"
          f"  [{len(m4fn)} (function, role) pairs read]")
    print(f"         M4 relations present: {len(present)}/{len(m4rels)}"
          + ("  — RULE 3 has nothing to check here (pre-0027)" if not present else "")
          + f"  [{len(m4rel)} (relation, role) pairs read]\n")

    problems = evaluate(funcs, money)
    problems += evaluate_m4(m4rel, M4_NO_SESSION_ACCESS, SESSION_GRANTEES)
    problems += evaluate_m4_functions(m4fn)
    if not problems:
        print("Anon exposure OK — every anon-callable SECURITY DEFINER function is allow-listed")
        print("with a justification that still holds, the TRUNCATE debt has not grown, and no")
        print(f"session role can write to any of the {len(present)} M4 relation(s) present.")
        return 0
    print(f"FAILED — {len(problems)} problem(s):\n")
    for p in problems:
        print(p + "\n")
    return 1


if __name__ == "__main__":
    sys.exit(self_test() if "--self-test" in sys.argv else main())
