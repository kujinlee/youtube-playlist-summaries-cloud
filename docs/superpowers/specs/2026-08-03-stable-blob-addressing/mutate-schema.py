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
          coalesce(p_source_generation_id, v_src),
          coalesce(p_start_sec, v_start), coalesce(p_end_sec, v_end))
  on conflict (workspace_id, video_id, slot, generation_id) where generation_id is not null
  do update set
       state                = 'recorded',
       lease_expires_at     = null,
       lease_token          = null,
       reserved_at          = null,
       source_generation_id = excluded.source_generation_id,
       start_sec            = excluded.start_sec,
       end_sec              = excluded.end_sec;""",
     # An early `return` makes the real one below unreachable, which is exactly the mutation's
     # intent. The anchor deliberately stops at the statement — extending it through the trailing
     # comment is what broke it when round 7 rewrote this block, and an anchor that spans prose is
     # an anchor that breaks every time someone explains themselves.
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
     # ⟳ round 7: was "PENDING generation reached current", and RED(other) said so. The default
     # flipping to `pending` is caught EARLIER — by the artifact-side trigger, when a fixture that
     # hand-inserts a complete generation tries to record against it. Naming the guard that actually
     # fires is the whole value of comparing `expect`; leaving it stale would have scored a real
     # catch as a miss the moment anything else changed.
     "cannot mark", GEN),

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
     """    insert into public.video_generations
      (workspace_id, video_id, generation_id, kind, state, reserved_by)
    values (p_ws, p_video, p_generation_id, p_kind, 'pending', v_token)
    on conflict (workspace_id, video_id, generation_id) do nothing;
    v_made_generation := found;
""",
     "",
     "cannot reserve a summary slot", ART),

    # ⟳ ROUND 7 H3 — the cleanup on the DENIED paths. Without it every `busy` loser leaves an
    # FK-valid parent no artifact points at, no ranking view reaches, and no sweep collects.
    ("a denied reservation keeps the generation row it created (round 7 H3)",
     """  if v_made_generation then
    delete from public.video_generations
     where workspace_id = p_ws and video_id = p_video and generation_id = p_generation_id
       and state = 'pending';
  end if;
""",
     "",
     "orphan generation row", ART),

    ("record no longer completes the generation",
     """  if p_generation_id is not null then
    update public.video_generations g
       set state             = 'complete',
           card              = coalesce(p_card, g.card),
           md_hash           = coalesce(p_md_hash, g.md_hash),
           doc_version_major = coalesce(p_doc_version_major, g.doc_version_major),
           produced_at       = coalesce(p_produced_at, g.produced_at, now()),
           reserved_by       = null
     where g.workspace_id = p_ws and g.video_id = p_video and g.generation_id = p_generation_id
       and g.state = 'pending'
       and (g.reserved_by = p_token
            or exists (select 1 from public.video_artifacts a
                        where a.workspace_id = p_ws and a.video_id = p_video and a.slot = p_slot
                          and a.state = 'pending' and a.generation_id = p_generation_id));
  end if;
""",
     "",
     "cannot mark", ART),

    # ⟳ ROUND 7 H2 — the ownership fence itself. Removing ONLY the two ownership disjuncts leaves the
    # completion working for every legitimate caller, so nothing but the hijack test can go red.
    ("the generation-completion ownership fence removed (round 7 H2)",
     """       and (g.reserved_by = p_token
            or exists (select 1 from public.video_artifacts a
                        where a.workspace_id = p_ws and a.video_id = p_video and a.slot = p_slot
                          and a.state = 'pending' and a.generation_id = p_generation_id))""",
     "",
     "generation it does not hold", ART),

    # And the other half: fencing on the TOKEN alone breaks the restarted worker (B1a), fencing on
    # the SLOT alone breaks the reclaimed one. Each disjunct is mutated separately, because a
    # compound guard hides which half carries the weight — round 5 H1's rule applied to a predicate.
    ("only the slot-ownership disjunct kept (a restarted worker cannot complete)",
     "       and (g.reserved_by = p_token\n            or exists",
     "       and (false\n            or exists",
     "cannot mark", ART),

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
     "           produced_at       = coalesce(p_produced_at, g.produced_at, now()),",
     "           produced_at       = coalesce(g.produced_at, now()),",
     "produced_at was stamped, not carried", ART),

    # ── round 7: the guards added for this round's own findings ──────────────────
    ("the produced_at future bound removed (a fast clock outranks reality)",
     """  if new.produced_at is not null and new.produced_at > now() then
    raise exception 'video_generations: produced_at % is in the FUTURE — a clock value may not enter the ranking',
      new.produced_at;
  end if;
""",
     "",
     "produced_at in the FUTURE", GEN),

    # EXPECTED GREEN, and measuring it changed what I believe about my own fix.
    #
    # B2 had two halves: bound `produced_at` to the past, and scope the detached_at bound to INSERT.
    # I shipped both. The mutation says the second carries NO GUARD OF ITS OWN: once produced_at
    # cannot be in the future, `detached_at = now()` on the UPDATE path is necessarily within
    # [produced_at, now()], so running the bound there is a guaranteed no-op and restoring the
    # "broken" form breaks nothing.
    #
    # So `tg_op = 'INSERT'` is a CLARIFICATION riding on the produced_at bound — exactly the status
    # of item 2's rung-1 `=`, and recorded the same way rather than quietly asserted. It stays,
    # because it says truthfully where the guard lives; but if the produced_at bound were ever
    # relaxed, this line would silently start carrying weight it is not tested for.
    ("the detached_at bound runs on UPDATE again (no-op once produced_at is bounded)",
     "  if tg_op = 'INSERT' and new.state = 'detached' then",
     "  if new.state = 'detached' then",
     None, ART),

    # ── round 8: the guard-classification fixes. Each converts a SEQUENCE guard from a rejecter
    # into a reconciler, so each mutation restores the REJECTER and must go red.
    ("the free-render reconciler removed (re-render collides on free_uq again)",
     """  if p_generation_id is null then
    insert into public.video_artifacts
      (workspace_id, video_id, slot, generation_id, kind, state, blob_key)
    values (p_ws, p_video, p_slot, null, p_kind, 'recorded', p_blob_key)
    on conflict (workspace_id, video_id, slot) where generation_id is null
    do update set blob_key = excluded.blob_key, state = 'recorded';
    return 'recorded_free';
  end if;
""",
     "",
     "first free render", ART),

    # The `do update` specifically — keeping the branch but making the insert blind. Without this,
    # deleting the whole branch is the only thing tested, and "the branch exists" is weaker than
    # "the branch reconciles".
    ("the free-render upsert made blind (branch kept, conflict handling dropped)",
     """    on conflict (workspace_id, video_id, slot) where generation_id is null
    do update set blob_key = excluded.blob_key, state = 'recorded';""",
     "    ;",
     "RE-render was refused", ART),

    # C3: the sweeper's predicate. Dropping the currency test makes the view select rows the
    # backstop trigger then refuses — i.e. the batch aborts again, which is the original defect.
    ("the collectable view stops excluding CURRENT generations",
     """   and not exists (select 1 from video_artifacts_current c
                    where c.workspace_id = g.workspace_id and c.video_id = g.video_id
                      and c.generation_id = g.generation_id)""",
     "",
     "refusing to collect", ART),

    ("forbid_collecting_current disabled (round 5 H3 — never mutated until round 7 M3)",
     """  if new.body_collected and not old.body_collected
     and exists (select 1 from public.video_artifacts_current c
                  where c.workspace_id = new.workspace_id and c.video_id = new.video_id
                    and c.generation_id = new.generation_id)
  then""",
     "  if (false) then",
     "collecting the CURRENT generation", ART),
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
    # ⟳ ROUND 7 — this branch was WRONG IN BOTH DIRECTIONS, and both were found by review rather
    # than by the harness, which is the point of shape #11 (an instrument that misreports itself).
    #
    #  TOO PERMISSIVE (Codex, High): it returned success WITHOUT comparing `expect`, so a mutation
    #    aimed at one guard could be caught by a different trigger entirely and still count. The
    #    assertion branch above has carried that comparison since round 6 — and it is exactly what
    #    caught two masked negatives the day before. Not sweeping it here is shape #10, in the fix
    #    written hours earlier for the previous instance of shape #11.
    #  TOO NARROW (Claude, M2): the anchor missed two of the schema's own raise messages —
    #    `video_artifacts is append-only:` (no colon after the table name) and
    #    `refusing to collect generation …` (no prefix at all). No mutation landed on either, so
    #    35/35 was honest — but round 7 adds a mutation for each, and without this they would have
    #    been reported INVALID, i.e. a working guard scored as an untested one. Again.
    m = re.search(r"ERROR:\s*(video_artifacts|video_generations|refusing to collect)[^\n]*", out)
    if m:
        detail = m.group(0).strip()
        return ("RED(trigger)" if expect.lower() in detail.lower() else "RED(other)"), detail
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
