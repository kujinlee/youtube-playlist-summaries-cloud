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

Usage:
    ./scripts/check-anon-exposure.py            # prod (read-only) — the subject that matters
    ./scripts/check-anon-exposure.py --local    # the docker stack
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


def parse_rows(stdout: str) -> tuple[list[tuple[str, bool, str, str]], list[tuple[str, bool]]]:
    """Pure: psql output -> (funcs, money). Split out so the FETCH's own parsing is under test."""
    funcs: list[tuple[str, bool, str, str]] = []
    money: list[tuple[str, bool]] = []
    section = None
    for raw in stdout.splitlines():
        if raw.startswith("---FUNCS---"):
            section = "f"; continue
        if raw.startswith("---MONEY---"):
            section = "m"; continue
        if not raw.strip():
            continue
        parts = raw.split("\t")
        if section == "f" and len(parts) >= 4:
            funcs.append((parts[0], pg_bool(parts[1]), parts[2], parts[3]))
        elif section == "m" and len(parts) >= 2:
            money.append((parts[0], pg_bool(parts[1])))
    return funcs, money


# ⟳ r5 M4 (claude) — ONE READER OF THIS CONFIG VALUE, NOT TWO THAT DISAGREE.
# `m4_catalog.py` grew a second `read_only_url` "using the same mechanism", and the copies had
# drifted three ways: which lines match (stripped vs unstripped, so an indented assignment was
# missed by one), which quotes are stripped (double-only vs both), and what an empty value returns
# (`""` vs `None`). Two readers of one secret that disagree about which values EXIST is exactly the
# shape `check-vocabulary-collisions.py` hunts, one layer below where that script looks.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from m4_catalog import psql_cmd, psql_env, read_only_url  # noqa: E402


def fetch(local: bool) -> tuple[list[tuple[str, bool, str, str]], list[tuple[str, bool]], str]:
    """Returns (funcs, money, subject). Exits 2 rather than returning empty on any failure —
    'cannot run' is a FAILURE, never a pass, and an empty catalog would read as 'nothing exposed'."""
    tables = "ARRAY[" + ",".join(f"'{t}'" for t in MONEY_TABLES) + "]"
    sql = SQL % tables
    url = None
    if local:
        subject = f"LOCAL container {CONTAINER}"
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
    cmd = psql_cmd("postgres", url=url, container=CONTAINER)
    p = subprocess.run(cmd, input=sql, capture_output=True, text=True, env=psql_env(url))
    if p.returncode != 0:
        print(f"CANNOT RUN — could not read the catalog from {subject}. TREAT THIS AS NOT RUN.")
        print((p.stderr or p.stdout)[-1200:])
        sys.exit(2)

    try:
        funcs, money = parse_rows(p.stdout)
    except ValueError as e:
        print(f"CANNOT RUN — unparseable catalog output from {subject}: {e}")
        print("TREAT THIS AS NOT RUN.")
        sys.exit(2)

    if not funcs:
        print(f"CANNOT RUN — {subject} returned no SECURITY DEFINER functions at all, which is not")
        print("a state this schema can be in. TREAT THIS AS NOT RUN.")
        sys.exit(2)
    return funcs, money, subject


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
         parse_rows("---FUNCS---\nf\tfalse\tboolean\tb\n---MONEY---\nt1\tfalse\n")
         == ([("f", False, "boolean", "b")], [("t1", False)]))

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


def main() -> int:
    funcs, money, subject = fetch(local="--local" in sys.argv)

    # Say what was READ before saying whether it passed — subject_status.py's rule, applied here
    # because this check has two possible subjects that genuinely disagree.
    exposed = [n for n, a, _, _ in funcs if a]
    print(f"subject: {subject}")
    print(f"         {len(funcs)} SECURITY DEFINER function(s) in public, "
          f"{len(exposed)} anon-EXECUTable")
    print(f"         money tables TRUNCATE-able by a session role: "
          f"{sum(1 for _, t in money if t)}/{len(money)} (baseline {TRUNCATE_BASELINE})\n")

    problems = evaluate(funcs, money)
    if not problems:
        print("Anon exposure OK — every anon-callable SECURITY DEFINER function is allow-listed")
        print("with a justification that still holds, and the TRUNCATE debt has not grown.")
        return 0
    print(f"FAILED — {len(problems)} problem(s):\n")
    for p in problems:
        print(p + "\n")
    return 1


if __name__ == "__main__":
    sys.exit(self_test() if "--self-test" in sys.argv else main())
