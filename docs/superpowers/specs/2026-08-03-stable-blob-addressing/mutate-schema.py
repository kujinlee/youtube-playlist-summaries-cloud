#!/usr/bin/env python3
"""Mutation-check the item-1 guards.

Three outcomes, never two (round-6 process note): a harness that only knows
pass/fail reports its own broken edit as an untested guard.

  RED     - the mutation was CAUGHT by an assertion naming it. The guard works.
  GREEN   - the mutation survived. The guard is documentation, not a guard.
  INVALID - the mutation broke the SQL, so nothing was tested.
"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path("/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud")
SPEC = ROOT / "docs/superpowers/specs/2026-08-03-stable-blob-addressing"
ART = SPEC / "schema/04_artifacts.sql"

# (label, find, replace, assertion-substring we EXPECT to go red)
MUTATIONS = [
    ("art_detached_is_dig dropped",
     "  constraint art_detached_is_dig check (state <> 'detached' or kind = 'dig'),\n",
     "",
     "DETACHED SUMMARY"),

    ("art_detached_has_timestamp dropped",
     "  constraint art_detached_has_timestamp check ((state = 'detached') = (detached_at is not null)),\n",
     "",
     "RECORDED row carrying a detached_at"),

    ("trigger gate narrowed back to recorded-only",
     "  if old.state in ('recorded','detached') and old.generation_id is not null then",
     "  if old.state = 'recorded' and old.generation_id is not null then",
     "DETACHED paid row"),

    ("freeze: only the PROVENANCE clause removed (Codex H5)",
     "    if new.source_generation_id is distinct from old.source_generation_id\n       or new.start_sec",
     "    if (false)\n       or new.start_sec",
     "PROVENANCE"),

    ("freeze: only the SPAN clauses removed (Codex H5)",
     "       or new.start_sec is distinct from old.start_sec\n       or new.end_sec   is distinct from old.end_sec then",
     "       or (false)\n       or (false) then",
     "SPAN"),

    ("clock restarts on every re-detach",
     "      new.detached_at := case when old.state = 'detached' then old.detached_at else now() end;",
     "      new.detached_at := now();",
     "RESTARTED the clock"),

    ("clock not cleared on re-attachment",
     "      new.detached_at := null;",
     "      new.detached_at := old.detached_at;",
     "detached fencing"),
]


def run():
    p = subprocess.run([str(SPEC / "verify-schema.sh")], capture_output=True, text=True, cwd=SPEC)
    return p.returncode, p.stdout + p.stderr


def classify(rc, out, expect):
    if rc == 0:
        return "GREEN", "mutation SURVIVED"
    # Did an assertion catch it, or did we just break the SQL?
    m = re.search(r"ASSERTION FAILED[^\n]*", out)
    if m:
        detail = m.group(0)
        tag = "RED" if expect.lower() in detail.lower() else "RED(other)"
        return tag, detail.strip()
    # A mutation can also be caught by a CONSTRAINT rather than by an assertion — still RED, the
    # guard is still covered. Only a syntax/undefined-object error means the edit broke the SQL.
    m = re.search(r"ERROR:\s*(new row for relation|.*violates .*constraint)[^\n]*", out)
    if m:
        return "RED(constraint)", m.group(0).strip()
    m = re.search(r"ERROR:[^\n]*", out)
    return "INVALID", (m.group(0).strip() if m else "no error captured; SQL did not run")


def main():
    original = ART.read_text()
    results = []
    for label, find, repl, expect in MUTATIONS:
        if find not in original:
            results.append((label, "INVALID", "anchor not found — mutation never applied"))
            continue
        try:
            ART.write_text(original.replace(find, repl, 1))
            rc, out = run()
            results.append((label, *classify(rc, out, expect)))
        finally:
            ART.write_text(original)

    print("\n" + "=" * 78)
    bad = 0
    for label, verdict, detail in results:
        mark = {"RED": "✅", "RED(constraint)": "✅", "RED(other)": "⚠️ ", "GREEN": "❌", "INVALID": "❌"}[verdict]
        print(f"{mark} {verdict:11} {label}")
        print(f"{'':14} {detail[:150]}")
        if verdict not in ("RED", "RED(constraint)"):
            bad += 1
    print("=" * 78)
    print(f"{len(results) - bad}/{len(results)} guards confirmed RED under mutation")

    rc, out = run()
    print("baseline restored:", "GREEN ✅" if rc == 0 else "STILL BROKEN ❌")
    return 1 if bad or rc else 0


if __name__ == "__main__":
    sys.exit(main())
