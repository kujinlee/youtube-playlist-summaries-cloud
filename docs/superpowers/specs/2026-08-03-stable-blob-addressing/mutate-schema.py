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
    # ── item 4: the reservation protocol (round 6 H5 / Codex B2) ─────────────────
    ("live-lease-first classification inverted (exhausted before busy)",
     """  if v_row.lease_expires_at > now() then
    return query select 'busy'::text, null::uuid, v_row.lease_attempts; return;
  end if;
""",
     "",
     "LIVE lease at the attempt bound reported", ART),

    ("the attempt bound removed from the reclaim predicate",
     "       and public.video_artifacts.lease_attempts   < v_max",
     "       and true",
     "past dig_max_attempts", ART),

    ("the attempt increment made non-durable (reset instead of bumped)",
     "       lease_attempts       = public.video_artifacts.lease_attempts + 1,",
     "       lease_attempts       = 1,",
     "attempt bound did not survive reclaim", ART),

    ("renewal not fenced by the token (anyone may renew)",
     "     and state = 'pending' and lease_token = p_token\n     and reserved_at > now()",
     "     and state = 'pending' and (lease_token = p_token or true)\n     and reserved_at > now()",
     "STRANGER renewed the lease", ART),

    ("the renewal ceiling removed (a hung worker renews forever)",
     "     and reserved_at > now() - make_interval(secs => v_ceiling);",
     "     and true;",
     "renewed past the ceiling", ART),

    ("record refuses when the token is stale (H5's declined fix)",
     """  insert into public.video_artifacts
    (workspace_id, video_id, slot, generation_id, kind, state, blob_key,
     source_generation_id, start_sec, end_sec)
  values (p_ws, p_video, p_slot, p_generation_id, p_kind, 'recorded', p_blob_key,
          p_source_generation_id, p_start_sec, p_end_sec);
  return 'recorded_after_loss';""",
     "  return 'refused';",
     "PAID work was discarded", ART),

    ("art_pending_has_token dropped",
     "  constraint art_pending_has_token check ((state = 'pending') = (lease_token is not null)),\n",
     "",
     "NO TOKEN", ART),

    ("art_pending_has_reserved_at dropped",
     "  constraint art_pending_has_reserved_at check ((state = 'pending') = (reserved_at is not null)),\n",
     "",
     "NO reserved_at", ART),

    ("the idempotency short-circuit removed",
     """  if exists (select 1 from public.video_artifacts
              where workspace_id = p_ws and video_id = p_video and slot = p_slot
                and generation_id = p_generation_id and state in ('recorded','detached')) then
    return query select 'already_recorded'::text, null::uuid, null::int; return;
  end if;
""",
     "",
     "already-recorded generation is idempotent", ART),

    # ── item 3: the generation-write API (round 6 B5, Codex B3) ──────────────────
    # The four CHECK gates are mutated INDIVIDUALLY. Restoring any one of them alone
    # re-locks the door item 3 opened, and the point is that each is separately
    # load-bearing — round 5 H1's lesson was that a compound guard hides which half works.
    ("gen_card_complete gate removed (back to unconditional)",
     "    state <> 'complete' or kind <> 'summary' or (\n      card is not null",
     "    kind <> 'summary' or (\n      card is not null",
     "cannot reserve a summary slot", GEN),

    ("gen_summary_has_hash gate removed",
     "  constraint gen_summary_has_hash check\n    (state <> 'complete' or kind <> 'summary' or md_hash is not null),",
     "  constraint gen_summary_has_hash check (kind <> 'summary' or md_hash is not null),",
     "cannot reserve a summary slot", GEN),

    ("gen_summary_has_format gate removed",
     "  constraint gen_summary_has_format check\n    (state <> 'complete' or kind <> 'summary' or doc_version_major is not null),",
     "  constraint gen_summary_has_format check (kind <> 'summary' or doc_version_major is not null),",
     "cannot reserve a summary slot", GEN),

    ("gen_complete_has_produced_at dropped",
     "  constraint gen_complete_has_produced_at check (state <> 'complete' or produced_at is not null),\n",
     "",
     "no produced_at", GEN),

    # THE DEFAULT. `pending` is the tempting default (it reads as "safer"), and it is the
    # fail-open one: every completeness CHECK becomes optional for a producer that simply
    # omits the column. This mutation is what makes that argument checkable rather than asserted.
    ("state defaults to pending instead of complete",
     "  state             text not null default 'complete'",
     "  state             text not null default 'pending'",
     "PENDING generation reached current", GEN),

    ("freeze: complete is no longer terminal",
     "    if new.state <> 'complete' then\n      raise exception 'video_generations: % is COMPLETE and cannot return to %',\n        old.generation_id, new.state;\n    end if;\n",
     "",
     "reverting a COMPLETE generation to pending", GEN),

    ("freeze: the CONTENT clause removed (md_hash/doc_version_major re-writable)",
     "    if new.card              is distinct from old.card\n       or new.md_hash           is distinct from old.md_hash",
     "    if (false)\n       or (false)",
     "rewriting the md_hash", GEN),

    # The artifact-side half. Without this the four gates above ARE a bypass, so this is the
    # single most load-bearing line item 3 adds.
    ("generation-complete guard removed (the gates become a bypass)",
     "  if v_state is distinct from 'complete' then\n    raise exception 'video_artifacts: cannot mark % as % — generation % is %',\n      new.slot, new.state, new.generation_id, coalesce(v_state, '<absent>');\n  end if;\n",
     "",
     "generation is still PENDING", ART),

    ("detached_at lower bound removed (backdating the retention clock)",
     "    if new.detached_at < v_produced then",
     "    if (false) then",
     "backdated BEFORE its generation", ART),

    ("detached_at future bound removed (postponing the retention clock)",
     "    if new.detached_at > now() then",
     "    if (false) then",
     "clock starts in the FUTURE", ART),

    ("reserve no longer creates the pending generation (the measured defect)",
     """  if p_generation_id is not null then
    insert into public.video_generations (workspace_id, video_id, generation_id, kind, state)
    values (p_ws, p_video, p_generation_id, p_kind, 'pending')
    on conflict (workspace_id, video_id, generation_id) do nothing;
  end if;
""",
     "",
     "cannot reserve a summary slot", ART),

    ("record no longer completes the generation",
     """  if p_generation_id is not null then
    update public.video_generations
       set state             = 'complete',
           card              = coalesce(p_card, card),
           md_hash           = coalesce(p_md_hash, md_hash),
           doc_version_major = coalesce(p_doc_version_major, doc_version_major),
           produced_at       = coalesce(p_produced_at, produced_at, now())
     where workspace_id = p_ws and video_id = p_video and generation_id = p_generation_id;
  end if;
""",
     "",
     "generation is still PENDING", ART),

    # produced_at is a PARAMETER, not a clock read. Stamping now() is item 1's detached_at
    # defect in a different column, and J2-3 forbids a clock read anywhere the ranking reads.
    #
    # ⚠ THE MUTATION DROPS THE PARAMETER, it does not assign now() outright — and the
    # difference is the whole test. `produced_at = now()` is caught by the FREEZE trigger on
    # an already-complete fixture (gOTHER) long before G9 runs, so it proves the freeze works
    # and says NOTHING about whether the parameter is honoured. Ignoring the parameter leaves
    # every complete generation untouched, so the freeze never fires and G9 is the only thing
    # that can go red. Round 5 H1's masking rule applies to mutations, not just to fixtures.
    ("produced_at ignores the caller and reads the clock (sync cannot replicate a time)",
     "           produced_at       = coalesce(p_produced_at, produced_at, now())",
     "           produced_at       = coalesce(produced_at, now())",
     "produced_at was stamped, not carried", ART),
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
    # ⟳ ROUND 6 B5 — A FOURTH VERDICT, and it was added because this harness made the
    # mistake its own docstring warns about, one layer up. Item 3's guards are TRIGGERS,
    # and a trigger's `raise exception` is an ERROR that matches neither the assertion
    # pattern nor the constraint pattern — so three working guards were reported INVALID
    # ("the mutation broke the SQL"), which is indistinguishable from an untested guard.
    # Same shape as round 5's `when others`: an instrument that cannot name what caught
    # something will eventually report a catch as a miss.
    # Anchored on the schema's OWN raise-exception prefixes, so a genuine runtime error
    # (a missing function, a bad cast) still classifies as INVALID rather than being
    # laundered into a pass.
    m = re.search(r"ERROR:\s*video_(artifacts|generations):[^\n]*", out)
    if m:
        return "RED(trigger)", m.group(0).strip()
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
    ok = {"RED", "RED(constraint)", "RED(trigger)", "GREEN(expected)"}
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
