#!/usr/bin/env python3
"""Mutation-check the guards in the stable-blob-addressing schema.

A guard that is never mutation-tested is documentation. Round 5 claimed every
guard came back RED and that claim was false, because the assertion harness
caught `when others` and counted a parse error as a rejection (see `3fb6970`).

THREE outcomes, never two — a harness that only knows pass/fail reports its own
broken edit as an untested guard:

  RED            - caught by an assertion naming it. The guard works.
  RED(constraint)- caught by a constraint rather than an assertion. Still covered.
  GREEN          - the mutation survived. The guard is not a guard.
  INVALID        - the mutation broke the SQL, so nothing was tested.

Usage:  ./mutate-schema.py          (exit 0 = every guard confirmed RED)
"""
import re
import subprocess
import sys
from pathlib import Path

SPEC = Path(__file__).resolve().parent
GEN = SPEC / "schema/03_generations.sql"
ART = SPEC / "schema/04_artifacts.sql"

# (label, find, replace, assertion-substring expected to go red, target file)
MUTATIONS = [
    # ── item 1: the `detached` fencing (round 6 B3/H1, Codex B1/H5) ──────────────
    ("art_detached_is_dig dropped",
     "  constraint art_detached_is_dig check (state <> 'detached' or kind = 'dig'),\n",
     "",
     "DETACHED SUMMARY", ART),

    ("art_detached_has_timestamp dropped",
     "  constraint art_detached_has_timestamp check ((state = 'detached') = (detached_at is not null)),\n",
     "",
     "RECORDED row carrying a detached_at", ART),

    ("trigger gate narrowed back to recorded-only",
     "  if old.state in ('recorded','detached') and old.generation_id is not null then",
     "  if old.state = 'recorded' and old.generation_id is not null then",
     "DETACHED paid row", ART),

    ("freeze: only the PROVENANCE clause removed (Codex H5)",
     "    if new.source_generation_id is distinct from old.source_generation_id\n       or new.start_sec",
     "    if (false)\n       or new.start_sec",
     "PROVENANCE", ART),

    ("freeze: only the SPAN clauses removed (Codex H5)",
     "       or new.start_sec is distinct from old.start_sec\n       or new.end_sec   is distinct from old.end_sec then",
     "       or (false)\n       or (false) then",
     "SPAN", ART),

    ("clock restarts on every re-detach",
     "      new.detached_at := case when old.state = 'detached' then old.detached_at else now() end;",
     "      new.detached_at := now();",
     "RESTARTED the clock", ART),

    ("clock not cleared on re-attachment",
     "      new.detached_at := null;",
     "      new.detached_at := old.detached_at;",
     "detached fencing", ART),

    # ── item 2: the corrections representation (round 6 B4) ──────────────────────
    ("corrections_hash nullable again (default kept, so ONLY nullability changes)",
     "  corrections_hash   text not null default no_corrections_hash(),",
     "  corrections_hash   text default no_corrections_hash(),",
     "NULL corrections_hash", GEN),

    ("the seed drops corrections (the original migration)",
     "         nullif(data->>'corrections', ''),\n         corrections_hash_of(data->>'corrections')",
     "         null::text,\n         no_corrections_hash()",
     "backfill lost corrections", GEN),

    ("gen_card_complete stops requiring mdCorrectionsHash",
     "      and card ->> 'mdCorrectionsHash' is not null)),",
     "      )),",
     "ONLY null is mdCorrectionsHash", GEN),

    ("the anti-drift trigger removed (UPDATE half)",
     """create trigger videos_corrections_sync_upd_trg
  after update of data on videos
  for each row
  when (coalesce(old.data->>'corrections','') is distinct from coalesce(new.data->>'corrections',''))
  execute function sync_corrections_to_workspace_video();""",
     "",
     "the copy drifted", GEN),

    # EXPECTED GREEN, and saying so is the point. With both sides NOT NULL,
    # `is not distinct from` and `=` are behaviourally identical, so the `=` change is a
    # clarification whose safety is entirely SUBSUMED by the NOT NULL above. Recording it as an
    # expected no-op is honest; deleting it would hide that the simplification carries no guard,
    # and claiming it RED would be the laundering this harness exists to stop.
    ("rung 1 back to `is not distinct from` (no-op while NOT NULL holds)",
     "         (g.card->>'mdCorrectionsHash' = wv.corrections_hash) desc,\n         g.doc_version_major",
     "         (g.card->>'mdCorrectionsHash' is not distinct from wv.corrections_hash) desc,\n         g.doc_version_major",
     None, ART),

    ("the DEFINED constant silently re-derived",
     "select '01ba4719c80b6fe911b091a7c05124b64eeece964e09c058ef8f9805daca546b'::text",
     "select encode(extensions.digest('[]', 'sha256'), 'hex')::text",
     "constant moved", GEN),
]


def run():
    p = subprocess.run([str(SPEC / "verify-schema.sh")], capture_output=True, text=True, cwd=SPEC)
    return p.returncode, p.stdout + p.stderr


def classify(rc, out, expect):
    if expect is None:
        return ("GREEN(expected)" if rc == 0 else "RED(unexpected)",
                "no-op by construction — subsumed by another guard" if rc == 0
                else "expected a no-op; something else depends on this")
    if rc == 0:
        return "GREEN", "mutation SURVIVED"
    m = re.search(r"ASSERTION FAILED[^\n]*", out)
    if m:
        detail = m.group(0)
        return ("RED" if expect.lower() in detail.lower() else "RED(other)"), detail.strip()
    # Caught by a constraint rather than an assertion — still covered.
    m = re.search(r"ERROR:\s*(new row for relation|.*violates .*constraint)[^\n]*", out)
    if m:
        return "RED(constraint)", m.group(0).strip()
    m = re.search(r"ERROR:[^\n]*", out)
    return "INVALID", (m.group(0).strip() if m else "no error captured; SQL did not run")


def main():
    originals = {ART: ART.read_text(), GEN: GEN.read_text()}
    results = []
    for label, find, repl, expect, target in MUTATIONS:
        original = originals[target]
        if find not in original:
            results.append((label, "INVALID", "anchor not found — mutation never applied"))
            continue
        try:
            target.write_text(original.replace(find, repl, 1))
            rc, out = run()
            results.append((label, *classify(rc, out, expect)))
        finally:
            target.write_text(original)

    print("\n" + "=" * 78)
    ok = {"RED", "RED(constraint)", "GREEN(expected)"}
    bad = 0
    for label, verdict, detail in results:
        mark = "✅" if verdict in ok else ("⚠️ " if verdict == "RED(other)" else "❌")
        print(f"{mark} {verdict:15} {label}")
        print(f"{'':18} {detail[:140]}")
        if verdict not in ok:
            bad += 1
    print("=" * 78)
    print(f"{len(results) - bad}/{len(results)} mutations behaved as expected "
          f"(RED, or GREEN where documented as subsumed)")

    rc, _ = run()
    print("baseline restored:", "GREEN ✅" if rc == 0 else "STILL BROKEN ❌")
    return 1 if bad or rc else 0


if __name__ == "__main__":
    sys.exit(main())
