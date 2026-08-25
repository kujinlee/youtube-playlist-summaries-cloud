#!/usr/bin/env python3
"""Build the SQL that migration 0027 will contain — the POST-ADR-0011 schema.

    python3 scripts/build-m4-schema.py                     # to stdout
    python3 scripts/build-m4-schema.py --out /tmp/0027.sql
    python3 scripts/build-m4-schema.py --self-test

WHY THIS IS NOT `cat 01 03 04`
------------------------------
ADR-0011 removed corrections from `workspace_videos`. The plan's Tasks 1-2 make those edits to the
spec files; until they land, a bare `cat` produces a schema that still creates
`sync_corrections_to_workspace_video()` and its two triggers on `videos`.

MEASURED 2026-08-25 — that is not a cosmetic difference:

  * `scripts/mutate-live-schema-check.sh` built M4 with a bare `cat` and called it "the REAL pre-M4
    schema", so the live-catalog gate was being mutation-proven against a schema M4 will never ship.
  * A rollback run over that schema left three objects behind and `check-live-schema.py
    --expect-absent` reported **ABSENT — as expected**, because its inventory is post-ADR-0011.

WHAT IT ASSERTS, AND WHY IT IS IDEMPOTENT
-----------------------------------------
Each edit is attempted; a file already in the post-ADR-0011 state reports `already` rather than
failing. The verdict does NOT rest on the edits, though — it rests on the END STATE, which is
asserted regardless of how the file got there. That is deliberate: anchors are a means, and a means
that silently stops matching is exactly the failure this repo keeps measuring.

⛔ EXPIRES when Tasks 1-2 land. At that point every edit reports `already` and this file can be
   reduced to its assertions. Until then it is the only way to build 0027's real content.

FAILS IF
--------
an anchor matches a count the plan does not claim; the end state is reached by neither route (exit
1); or a spec file is unreadable (exit 2 — treat as NOT RUN).
"""
from __future__ import annotations

import argparse
import os
import re
import sys

SCHEMA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                      "docs", "superpowers", "specs", "2026-08-03-stable-blob-addressing", "schema")

SEED_RX = re.compile(
    r"insert into workspace_videos \(workspace_id, video_id, corrections, corrections_hash\)"
    r".*?desc;\n", re.S)
SEED_NEW = ("insert into workspace_videos (workspace_id, video_id)\n"
            "  select distinct workspace_id, video_id from videos;\n")

UPSERT_RX = re.compile(
    r"    insert into public\.workspace_videos \(workspace_id, video_id, corrections,"
    r".*?on conflict \(workspace_id, video_id\) do nothing;\n", re.S)
UPSERT_NEW = ("    insert into public.workspace_videos (workspace_id, video_id)\n"
              "    values (v_ws, new.video_id)\n"
              "    on conflict (workspace_id, video_id) do nothing;\n")

COL_A = re.compile(r"^  corrections        text,\n", re.M)
COL_B = re.compile(r"^  corrections_hash   text not null default no_corrections_hash\(\),\n", re.M)
RANK = re.compile(r"^ *\(g\.card->>'mdCorrectionsHash' = wv\.corrections_hash\) desc,.*\n", re.M)
SYNC_FN = re.compile(
    r"create function sync_corrections_to_workspace_video\(\) returns trigger.*?"
    r"revoke all on function sync_corrections_to_workspace_video\(\) from public, anon, "
    r"authenticated;", re.S)


def trigger_rx(name: str) -> re.Pattern[str]:
    return re.compile(re.escape(f"create trigger {name}") + r".*?"
                      + re.escape("execute function sync_corrections_to_workspace_video();"), re.S)


def strip_comments(sql: str) -> str:
    """Drop `--` comments so assertions read CODE, not prose about code.

    ⟳ r3 LOW (codex) — THE NAIVE VERSION WAS WRONG IN THE DANGEROUS DIRECTION, and its own docstring
    said the opposite. It claimed "an over-eager cut can only make an assertion stricter, never blind
    it". MEASURED, the counter-example:

        strip_comments("select '--' || wv.corrections_hash;")  ->  "select '"
        assert_end_state(... that line ...)                    ->  []      # BLIND

    A `--` inside a string literal truncated the line before the offending reference, so the
    end-state predicate could not see it. That is exactly the blinding the comment ruled out.

    This version tracks single-quoted strings (with `''` escaping) and only honours `--` outside
    one. Codex found no such line in today's schema, so this closes residual risk rather than a live
    bad build — but the predicate is the verdict, and a verdict that can be blinded by a quote is
    not one.
    """
    out = []
    for line in sql.splitlines():
        in_str = False
        i = 0
        while i < len(line):
            ch = line[i]
            if in_str:
                if ch == "'":
                    # '' inside a string is an escaped quote, not a terminator
                    if i + 1 < len(line) and line[i + 1] == "'":
                        i += 1
                    else:
                        in_str = False
            elif ch == "'":
                in_str = True
            elif ch == "-" and i + 1 < len(line) and line[i + 1] == "-":
                break
            i += 1
        out.append(line[:i])
    return "\n".join(out)


def table_body(code: str, table: str) -> str | None:
    """The column list of `create table <table> ( … )`, by PAREN DEPTH. PURE.

    ⟳ The first version of this used the regex `create table X\\s*\\((.*?)\\n\\);`, which passed
    against the real spec — because that file happens to close the block on its own line — and
    failed on a fixture closing `primary key (a, b));`. That is this repo's most-repeated defect
    written into the very check meant to catch it: **a pattern that matches what I READ, not what is
    THERE.** Depth counting has no such preference.

    Expects comment-stripped input, so `--` text cannot contribute parens.
    """
    start = code.find(f"create table {table}")
    if start == -1:
        return None
    open_paren = code.find("(", start)
    if open_paren == -1:
        return None
    depth, in_str, i = 0, False, open_paren
    while i < len(code):
        ch = code[i]
        if in_str:
            if ch == "'":
                if i + 1 < len(code) and code[i + 1] == "'":
                    i += 1
                else:
                    in_str = False
        elif ch == "'":
            in_str = True
        elif ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return code[open_paren + 1:i]
        i += 1
    return None


def apply_edits(s03: str, s04: str) -> tuple[str, str, list[str], list[str]]:
    """Apply Tasks 1-2. Returns (s03, s04, log, errors). PURE."""
    log: list[str] = []
    errors: list[str] = []

    def sub(text: str, rx: re.Pattern[str], repl: str, want: int, label: str) -> str:
        n = len(rx.findall(text))
        if n == want:
            log.append(f"applied  {label}")
            return rx.sub(repl, text)
        if n == 0:
            log.append(f"already  {label}")
            return text
        errors.append(f"{label}: expected {want} or 0 matches, found {n}")
        return text

    s03 = sub(s03, COL_A, "", 1, "T1.2a  workspace_videos.corrections column")
    s03 = sub(s03, COL_B, "", 1, "T1.2b  workspace_videos.corrections_hash column")
    s03 = sub(s03, SEED_RX, SEED_NEW, 1, "T1.3   backfill -> (workspace_id, video_id)")
    s03 = sub(s03, UPSERT_RX, UPSERT_NEW, 1, "T1.4   derive-trigger upsert")
    s03 = sub(s03, SYNC_FN, "", 1, "T1.5a  sync_corrections_to_workspace_video + revoke")
    for trg in ("videos_corrections_sync_ins_trg", "videos_corrections_sync_upd_trg"):
        s03 = sub(s03, trigger_rx(trg), "", 1, f"T1.5b  trigger {trg}")
    s04 = sub(s04, RANK, "", 2, "T2.2   corrections ranking term, both sites")
    return s03, s04, log, errors


def assert_end_state(sql: str) -> list[str]:
    """The verdict. Holds regardless of HOW the file reached this state. PURE."""
    code = strip_comments(sql)
    bad: list[str] = []

    if "sync_corrections_to_workspace_video" in code:
        bad.append("sync_corrections_to_workspace_video() still exists — ADR-0011 deletes it")
    if "videos_corrections_sync_" in code:
        bad.append("a videos_corrections_sync_* trigger still exists — ADR-0011 deletes both")

    # ⛔ r3 B1 (claude) — THE PREDICATE WAS BLIND TO BOTH COLUMN EDITS, WHICH IS HALF ITS JOB.
    # The reference filter below excludes any line containing `no_corrections_hash`. The column it
    # must catch is:
    #
    #     corrections_hash   text not null default no_corrections_hash(),
    #
    # — whose own DEFAULT contains that string, so the guard could never see it. MEASURED: drift the
    # anchor by ONE SPACE and this script exits 0, reports `already`, and emits the ADR-0011 column
    # straight into 0027. The bare `corrections text,` column was unguarded outright.
    #
    # A column DEFINITION is not a reference, so it needs its own assertion over the table block
    # rather than a smarter line filter.
    body = table_body(code, "workspace_videos")
    if body is None:
        bad.append("could not find the `create table workspace_videos (…)` block to check")
    else:
        for ln in body.splitlines():
            if "corrections" in ln:
                bad.append("workspace_videos still DEFINES a corrections column, which ADR-0011 "
                           f"removes: {ln.strip()[:90]}")

    residual = [ln.strip() for ln in code.splitlines()
                if "corrections_hash" in ln
                and "corrections_hash_of" not in ln and "no_corrections_hash" not in ln]
    for ln in residual:
        bad.append(f"workspace_videos.corrections_hash is still referenced: {ln[:90]}")

    for want, label in ((SEED_NEW.strip(), "post-ADR-0011 backfill"),
                        (UPSERT_NEW.strip(), "post-ADR-0011 derive-trigger upsert")):
        first = want.splitlines()[0].strip()
        if first not in code:
            bad.append(f"the {label} is missing: expected a line `{first}`")
    return bad


def build(schema: str) -> tuple[str, list[str]]:
    """Returns (sql, log). Raises RuntimeError on any failure, with every reason."""
    try:
        with open(os.path.join(schema, "01_workspaces.sql")) as f:
            s01 = f.read()
        with open(os.path.join(schema, "03_generations.sql")) as f:
            s03 = f.read()
        with open(os.path.join(schema, "04_artifacts.sql")) as f:
            s04 = f.read()
    except OSError as e:
        raise FileNotFoundError(str(e)) from e

    s03, s04, log, errors = apply_edits(s03, s04)
    sql = s01 + s03 + s04
    errors += assert_end_state(sql)
    if errors:
        raise RuntimeError("\n".join(f"  ✗ {e}" for e in errors))
    return sql, log


# ---------------------------------------------------------------- self-test
PRE = """create table workspace_videos (
  workspace_id uuid not null,
  video_id     text not null,
  corrections        text,
  corrections_hash   text not null default no_corrections_hash(),
  primary key (workspace_id, video_id));
insert into workspace_videos (workspace_id, video_id, corrections, corrections_hash)
  select distinct on (workspace_id, video_id) workspace_id, video_id, x, y
    from videos order by workspace_id, video_id, (z) desc;
create function sync_corrections_to_workspace_video() returns trigger as $$ begin end $$;
revoke all on function sync_corrections_to_workspace_video() from public, anon, authenticated;
create trigger videos_corrections_sync_ins_trg after insert on videos
  execute function sync_corrections_to_workspace_video();
create trigger videos_corrections_sync_upd_trg after update on videos
  execute function sync_corrections_to_workspace_video();
"""
PRE_FN = """  if tg_table_name = 'videos' then
    insert into public.workspace_videos (workspace_id, video_id, corrections, corrections_hash)
    values (v_ws, new.video_id, a, b)
    on conflict (workspace_id, video_id) do nothing;
  end if;
"""
PRE_04 = """select 1,
         (g.card->>'mdCorrectionsHash' = wv.corrections_hash) desc,
         2;
select 3,
         (g.card->>'mdCorrectionsHash' = wv.corrections_hash) desc,   -- comment
         4;
"""


def self_test() -> int:
    cases = failures = 0

    def check(label: str, got: object, want: object) -> None:
        nonlocal cases, failures
        cases += 1
        ok = got == want
        print(("  ✓ " if ok else f"  ✗ [{got!r} != {want!r}] ") + label)
        failures += 0 if ok else 1

    s03, s04, log, errors = apply_edits(PRE + PRE_FN, PRE_04)
    check("a PRE-ADR-0011 spec produces no anchor errors", errors, [])
    check("every edit reports `applied` on a pre-state file",
          all(e.startswith("applied") for e in log), True)
    check("the pre-state file reaches a clean end state", assert_end_state(s03 + s04), [])

    # idempotency: feeding the OUTPUT back in must be a no-op, not a failure
    s03b, s04b, log2, errors2 = apply_edits(s03, s04)
    check("re-running on the OUTPUT reports no errors", errors2, [])
    check("re-running reports every edit as `already`",
          all(e.startswith("already") for e in log2), True)
    check("re-running changes nothing", (s03b, s04b) == (s03, s04), True)

    # the end-state assertion is the verdict, so it must fire on each removed object
    check("end state REJECTS a surviving sync function",
          any("sync_corrections_to_workspace_video" in b
              for b in assert_end_state(s03 + s04 + "\nselect sync_corrections_to_workspace_video();")),
          True)
    check("end state REJECTS a surviving sync trigger",
          any("videos_corrections_sync_" in b for b in assert_end_state(
              s03 + s04 + "\ncreate trigger videos_corrections_sync_ins_trg on videos;")), True)
    check("end state REJECTS a residual wv.corrections_hash reference",
          any("corrections_hash is still referenced" in b
              for b in assert_end_state(s03 + s04 + "\nselect wv.corrections_hash from x;")), True)
    check("end state IGNORES corrections_hash inside a COMMENT",
          assert_end_state(s03 + s04 + "\n-- wv.corrections_hash was removed by ADR-0011\n"), [])
    check("end state TOLERATES corrections_hash_of, which ADR-0011 keeps",
          assert_end_state(s03 + s04 + "\nselect public.corrections_hash_of('x');"), [])
    check("end state REJECTS a missing backfill",
          any("backfill is missing" in b for b in assert_end_state("select 1;")), True)

    # ⟳ r3 LOW (codex) — a `--` inside a STRING LITERAL used to truncate the line before the
    # offending reference, blinding the predicate. Verbatim from the review.
    check("strip_comments does NOT cut at a -- inside a string literal",
          strip_comments("select '--' || wv.corrections_hash;"),
          "select '--' || wv.corrections_hash;")
    check("end state REJECTS a residual reference hidden behind a quoted --",
          any("corrections_hash is still referenced" in b for b in
              assert_end_state(s03 + s04 + "\nselect '--' || wv.corrections_hash;")), True)
    check("strip_comments STILL cuts a real trailing comment",
          strip_comments("select 1; -- wv.corrections_hash was removed"), "select 1; ")
    check("strip_comments handles an escaped '' inside a string",
          strip_comments("select 'it''s -- fine'; -- gone"), "select 'it''s -- fine'; ")

    # ⛔ r3 B1 (claude) — THE TWO COLUMN EDITS WERE UNGUARDED, which is half this predicate's job.
    # MEASURED: drift the corrections_hash anchor by one space and the script exited 0, reported
    # `already`, and emitted the ADR-0011 column into 0027.
    drifted = PRE.replace(
        "  corrections_hash   text not null default no_corrections_hash(),",
        "  corrections_hash    text not null default no_corrections_hash(),")
    d03, d04, _, derr = apply_edits(drifted + PRE_FN, PRE_04)
    check("a DRIFTED corrections_hash anchor still reports no anchor error", derr, [])
    check("…but the END STATE rejects it — the column survived",
          any("still DEFINES a corrections column" in b for b in assert_end_state(d03 + d04)), True)
    drifted_a = PRE.replace("  corrections        text,", "  corrections   text,")
    a03, a04, _, _ = apply_edits(drifted_a + PRE_FN, PRE_04)
    check("a DRIFTED bare corrections anchor is caught by the end state too",
          any("still DEFINES a corrections column" in b for b in assert_end_state(a03 + a04)), True)
    check("a missing workspace_videos block is a failure, not a silent pass",
          any("could not find" in b for b in assert_end_state("select 1;")), True)

    # an anchor that matches an unexpected NUMBER of times is an error, never a silent skip
    _, _, _, errors3 = apply_edits(PRE + PRE_FN + PRE, PRE_04)
    check("a DOUBLED anchor is an error, not a silent partial edit", bool(errors3), True)
    _, _, _, errors4 = apply_edits(PRE + PRE_FN, PRE_04 + PRE_04)
    check("the two-site ranking anchor rejects FOUR sites", bool(errors4), True)

    print(f"\n{cases - failures}/{cases} self-test cases passed")
    return 1 if failures else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", help="write here instead of stdout")
    ap.add_argument("--schema", default=SCHEMA)
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--quiet", action="store_true", help="suppress the per-edit log on stderr")
    a = ap.parse_args()

    if a.self_test:
        return self_test()

    try:
        sql, log = build(a.schema)
    except FileNotFoundError as e:
        print(f"CANNOT RUN — could not read the spec schema: {e}\nTreat this as NOT RUN.",
              file=sys.stderr)
        return 2
    except RuntimeError as e:
        print("FAILED — the spec is in neither the pre- nor the post-ADR-0011 state:\n",
              file=sys.stderr)
        print(e, file=sys.stderr)
        return 1

    if not a.quiet:
        for line in log:
            print(f"  {line}", file=sys.stderr)
    if a.out:
        with open(a.out, "w") as f:
            f.write(sql)
        if not a.quiet:
            # len(sql) counts CHARACTERS; the spec is full of multi-byte ⟳ ⛔ ⚠, so that number
            # disagrees with `wc -c` by ~1.5 KB. Report what the filesystem will report.
            print(f"  -> {a.out} ({len(sql.encode('utf-8'))} bytes)", file=sys.stderr)
    else:
        sys.stdout.write(sql)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
