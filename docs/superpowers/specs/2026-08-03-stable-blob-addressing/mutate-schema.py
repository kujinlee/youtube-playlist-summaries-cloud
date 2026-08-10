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
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SPEC = Path(__file__).resolve().parent
GEN = SPEC / "schema/03_generations.sql"
ART = SPEC / "schema/04_artifacts.sql"

# ⟳ ROUND 8 M3 — THIS HARNESS USED TO MUTATE THE REPO-TRACKED FILES AND PUT THEM BACK IN A
# `finally`, and that is shape #11 (an instrument that misreports its own result) in the
# instrument built to catch shape #11.
#
# MEASURED during round 8, when two reviewers ran `./scripts/check-schema-gates.sh` at the same
# time on the same checkout: 23/44 in the repo against 44/44 in an isolated copy of the SAME
# COMMIT, with 21 entries reported `RED(other)` carrying detail text belonging to a different
# mutation. Each run was reading the other's edits. The failure was loud and WRONG — a reviewer
# spent a cycle treating a green artifact as broken, and the opposite mistake (a concurrent run
# masking a genuine GREEN as RED(other)) is equally available.
#
# The `finally` also does not survive SIGKILL, so an interrupted run left a MUTATED, repo-tracked
# schema file on disk — a mutation one `git commit -a` away from being the schema.
#
# So the mutation now lands on a COPY and the repo files are opened read-only. `verify-schema.sh`
# resolves its schema directory from its own location, so copying it beside the schema is the
# whole trick.

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

    # ⟳ ADR-0007 — RE-ANCHORED, NOT RETIRED, AND THE DIRECTION FLIPPED. The gate used to read
    # `if old.state in ('recorded','detached') and old.generation_id is not null then`, and this
    # mutation RESTORED round 6 B3/H1's `old.state = 'recorded'` — the version under which a detached
    # row was completely unprotected and every append-only guarantee was reachable in two statements.
    # ADR-0007 deleted the two permitted transitions that clause carried, so the gate is now
    # `old.generation_id is not null` alone. The defect it protected against is unchanged and still
    # reachable, so the mutation now ADDS the narrowing instead of restoring it. Same rule, same
    # assertions (the DETACHED-paid-row negatives), new anchor.
    ("trigger gate narrowed back to recorded-only (round 6 B3/H1)",
     "  if old.generation_id is not null then",
     "  if old.generation_id is not null and old.state = 'recorded' then",
     "DETACHED paid row", ART),

    # ⟳ T3 RE-ANCHORED — the PROVENANCE half of this branch moved to `video_artifact_sources`, so the
    # mutation moved with it. Codex H5's rule is unchanged: provenance is a ranking input, so a stale
    # model that rewrites it wins the currency rung without regenerating a byte. Only the spelling
    # changed — with a set, "rewrite" is UPDATE, DELETE-then-insert, or an alien INSERT, and each gets
    # its own entry below rather than one anchor covering three mechanisms.
    ("vas freeze: the UPDATE branch removed (Codex H5 — provenance rewritten in place)",
     "  raise exception 'video_artifact_sources: the PROVENANCE of artifact % is immutable — % may not become %',\n    old.artifact_id, old.source_generation_id, new.source_generation_id;",
     "  return new;",
     "rewriting the PROVENANCE", ART),

    ("vas freeze: the DELETE branch removed (the two-statement route back to a rewrite)",
     """  if tg_op = 'DELETE' then
    if exists (select 1 from public.video_artifacts a where a.artifact_id = old.artifact_id) then
      raise exception 'video_artifact_sources: cannot DELETE the provenance of a live artifact % (source %)',
        old.artifact_id, old.source_generation_id;
    end if;
    return old;
  end if;""",
     "  if tg_op = 'DELETE' then\n    return old;\n  end if;",
     "DELETING the provenance", ART),

    # ⚠ THE OTHER DIRECTION OF THE SAME BRANCH, and it is here because round 14 B3 measured what an
    # over-broad rule on this path costs. Making the DELETE raise unconditional is the tempting
    # "stricter is safer" edit; it re-breaks account erasure through the FREE-render cascade, which is
    # the live caller `on delete cascade` was chosen for in the first place. A guard is load-bearing in
    # two directions and only one of them is a missing raise.
    ("vas freeze: the DELETE raise made unconditional (account erasure blocked again)",
     "    if exists (select 1 from public.video_artifacts a where a.artifact_id = old.artifact_id) then",
     "    if true then",
     "cannot DELETE the provenance", ART),

    # ⚠ ROUND 17 H3, AS A MUTATION. This is the guard whose ABSENCE was measured: with only the
    # update/delete freeze above, a re-record naming a different source is an INSERT, which fires no
    # such trigger, and the probe got a silent UNION — neither the same set nor a raise.
    ("vas: the INSERT enforcer removed (round 17 H3 — the silent UNION returns)",
     """create trigger video_artifact_sources_insert_once_trg
  after insert on video_artifact_sources
  referencing new table as ins
  for each statement execute function video_artifact_sources_insert_once();""",
     "",
     "ADDING a source to an artifact", ART),

    # The other direction: an enforcer that refuses a legitimate multi-row set would make the table's
    # own purpose unreachable. `>` becomes `>=`, so every insert looks like an addition.
    ("vas: the INSERT enforcer refuses the FIRST set too (multi-source unrepresentable)",
     "       > (select count(*) from ins j where j.artifact_id = i.artifact_id)",
     "       >= (select count(*) from ins j where j.artifact_id = i.artifact_id)",
     "the PROVENANCE of artifact", ART),

    ("freeze: only the SPAN clauses removed (Codex H5)",
     "    if new.start_sec is distinct from old.start_sec\n       or new.end_sec   is distinct from old.end_sec then",
     "    if (false)\n       or (false) then",
     "SPAN", ART),

    # ⟳ T3 — `art_summary_has_no_source` IS A CONSTRAINT TRIGGER NOW, and it had never been mutated as
    # a CHECK either: the old entry list has no line for it. Neutralised rather than deleted, so the
    # trigger still exists and only its verdict changes.
    ("art_summary_has_no_source neutralised (a summary may record a source again)",
     "  if v_kind = 'summary' then",
     "  if false then",
     "a SUMMARY artifact recording a source", ART),

    # ── ⟳ T3: the source-currency rung, which had NO mutation for seventeen rounds ────────────────
    # ⚠ THE RUNG WAS UNTESTED, NOT UNDER-TESTED. The only assertion touching it was the FLOOR ("a
    # stale model must still serve"), which a rung that does nothing at all satisfies. Both directions
    # get an entry, because the two ways to break a rung are to make it decide nothing and to make it
    # decide the wrong thing.
    ("T3: the source-currency rung neutralised (staleness stops ranking)",
     """         (a.slot = 'summary'
          or not exists (select 1""",
     """         (a.slot = 'summary'
          or true
          or not exists (select 1""",
     "the source-currency rung did not decide", ART),

    # ⟳ ROUND 15 M3, AS A MUTATION. `video_summary_current` has no row for a dig generation, so
    # scoring a non-summary source against it marks it stale FOREVER — and the artifact that carries
    # dig sources is `digDeeper`, the multi-source case the table exists for.
    ("T3: every source kind ranks, not only summary (round 15 M3's undefined case)",
     "                            and sg.kind = 'summary'\n",
     "",
     "a NON-SUMMARY source was scored for currency", ART),

    ("T3: the GC reachability check removed (a referenced generation is collectable again)",
     """   and not exists (select 1 from video_artifact_sources vas
                    where vas.workspace_id = g.workspace_id and vas.video_id = g.video_id
                      and vas.source_generation_id = g.generation_id)""",
     "",
     "was offered to the sweeper", ART),

    # ── ⟳ T3: record_artifact's half of the re-record rule ───────────────────────────────────────
    # ⚠ THE FIRST OF THESE IS ROUND 15 B3 ITSELF — "drop the column, leave the RPC unchanged, and the
    # table is always empty, at which point BOTH new guards go vacuously true." It is the failure this
    # ADR names three times ("a guard that never started, arriving by subtraction"), so it gets a
    # mutation rather than a paragraph. Note which assertion catches it: the RUNG, not a provenance
    # negative — an empty table breaks no rule, it just stops deciding anything.
    ("T3: record_artifact stops writing provenance (round 15 B3 — both guards go vacuous)",
     """      insert into public.video_artifact_sources
        (artifact_id, workspace_id, video_id, source_generation_id)
      values (v_art, p_ws, p_video, p_source_generation_id);""",
     "      null;",
     "the source-currency rung did not decide", ART),

    ("T3: the re-record set comparison removed (a shrink the trigger cannot see)",
     """    elsif v_recorded is distinct from array[p_source_generation_id] then
      raise exception 'video_artifact_sources: the PROVENANCE of % (slot %, gen %) is immutable — it records {%}, and this record presents {%}',
        v_art, p_slot, p_generation_id,
        array_to_string(v_recorded, ', '), p_source_generation_id;""",
     "",
     "re-recording with a DIFFERENT source", ART),

    # ⟳ ROUND 16 H2, AS A MUTATION: the rule said REPLACE until round 16 corrected it to "present the
    # same set, or raise". This restores the replace — delete the recorded set, then write the
    # presented one — and the verdict is the interesting part: it dies on the child table's own DELETE
    # freeze, which is precisely the contradiction H2 identified ("a replace is a delete-and-insert,
    # and the trigger being moved forbids exactly that"). The draft was not merely wrong about intent;
    # it was unimplementable beside the other half of the same fix.
    #
    # ⚠ AND THE OMISSION HALF OF THE RULE HAS NO MUTATION, WHICH IS A PROPERTY AND NOT A GAP — said
    # out loud because an absence here is indistinguishable from an oversight. "An omitted
    # p_source_generation_id carries the recorded set forward unchanged" is carried by NOTHING
    # EXECUTING: the block is gated on `p_source_generation_id is not null`, so on the omission path
    # there is no statement to remove and no predicate to invert. The first version of this entry
    # tried to force one by widening that gate, and it measured a NOT NULL violation rather than a
    # wiped set — a mutation modelling a defect the code cannot have. What actually protects the
    # omission path is the DELETE branch mutated above; the assertion is still worth its place,
    # because a FUTURE writer that adds a statement there would have nothing else to catch it.
    ("T3: a re-record REPLACES the source set (round 16 H2's withdrawn draft)",
     """    if v_recorded = '{}'::text[] then""",
     """    delete from public.video_artifact_sources where artifact_id = v_art;
    if true then""",
     "cannot DELETE the provenance", ART),

    # ── ⟳ T3: the table's own shape ──────────────────────────────────────────────────────────────
    ("T3: the source row's tenant coordinate no longer FK'd to its artifact",
     """  constraint vas_artifact_fk foreign key (artifact_id, workspace_id, video_id)
    references video_artifacts (artifact_id, workspace_id, video_id) on delete cascade,""",
     """  constraint vas_artifact_fk foreign key (artifact_id)
    references video_artifacts (artifact_id) on delete cascade,""",
     "tenant coordinate is not its artifact", ART),

    # RLS on the join table is not symmetry: `video_artifacts_current` is security_invoker and reads
    # this table inside the rung, so without the policy the owner and service_role rank the SAME
    # manifest differently. Round 6 H3's lesson — a policy's removal is only visible from the OWNER's
    # side — is why the assertion this kills is an owner-side read, not a cross-tenant one.
    ("T3: the owner-read policy on video_artifact_sources removed",
     """create policy video_artifact_sources_owner_read on video_artifact_sources for select to authenticated
  using (workspace_id in (select id from workspaces where owner_id = (select auth.uid())));""",
     "",
     "the owner cannot read their own base tables", ART),

    ("clock restarts on every re-detach",
     "      new.detached_at := case when old.state = 'detached' then old.detached_at else now() end;",
     "      new.detached_at := now();",
     "RESTARTED the clock", ART),

    ("clock not cleared on re-attachment",
     "      new.detached_at := null;",
     "      new.detached_at := old.detached_at;",
     "art_detached_has_timestamp", ART),

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
    # ── ⛔ item 4: the reservation protocol (round 6 H5 / Codex B2) — RETIRED BY ADR-0007 ─────────
    # SEVEN mutations stood here. Their anchors went with `reserve_artifact_slot`,
    # `renew_artifact_lease`, the `pending` state, the lease columns and the two `pending`
    # biconditional CHECKs. They are listed by what each PROVED rather than deleted silently,
    # because in this harness a dangling anchor reports INVALID and INVALID reads as *untested*:
    #
    #   "video_artifacts_inflight_uq: live-lease-first classification inverted" (round 6 H5)
    #       At attempts = max AND a live lease, the answer had to be `busy`, not `exhausted` — the
    #       ONLY case where the two orderings differ. The whole suite stayed GREEN under this
    #       mutation until the assertion for it existed, which is why it was written.
    #   "the attempt bound removed from the reclaim predicate" (round 6 H5)
    #       A reclaim past the per-kind `dig_max_attempts` was refused.
    #   "the attempt increment made non-durable (reset instead of bumped)" (round 6 H5)
    #       The count survived a reclaim, because the increment lived in the statement that took
    #       the slot rather than in a separate update the next caller could reset.
    #   "renewal not fenced by the token (anyone may renew)" (round 6 H5)
    #   "the renewal ceiling removed (a hung worker renews forever)" (round 6 H5)
    #       The two halves of `renew_artifact_lease`: a stranger got `lost`, and a live holder could
    #       not renew past `max_duration_seconds`.
    #   "art_pending_has_token dropped" / "art_pending_has_reserved_at dropped" (round 6 H5)
    #       Biconditionals on `state = 'pending'` over columns that no longer exist. Their negatives
    #       are retired in 05 for the same reason, and replaced there by the stronger claim: a row
    #       can no longer BE pending.
    #
    # ⚠ ONE OF THE SEVEN IS A COVERAGE LOSS, NOT A RETIREMENT, AND SAYING SO IS THE POINT.
    # `video_artifacts_inflight_uq` was also the single-flight guard for the `model` serve path, and
    # 04's tombstone names the successor that has NOT been built (`doc_key` re-keyed to
    # `(workspace_id, video_id)`). No mutation can cover that here: the mechanism lives in
    # `supabase/migrations/`, outside this schema and outside this suite's reach.
    #
    # ⚠ AND TWO MORE ARE RE-ANCHORED RATHER THAN RETIRED — the two entries immediately below.

    # ⟳ ADR-0007 RE-ANCHORED. This was "video_artifacts_paid_uq: record refuses when the token is
    # stale (H5's declined fix)". Round 6 H5 proposed making `record_artifact` refuse a writer whose
    # token had gone stale; the fix was DECLINED because the charge happens at reserve time, so
    # refusing the loser's record discards paid work without preventing the cost. There is no token
    # and no staleness left — but the DECISION that mutation guarded is still live and still
    # load-bearing. 04 states it in its own words ("THE APPEND — and it never refuses a writer its
    # own paid work"), and ADR-0007's whole dissolution rests on it: writers do not contend because
    # the append accepts all of them. So the mutation still injects a refusal into the append; only
    # the anchor moved to the statement that survived, which no longer clears any lease column.
    # An early `return` makes the real one below unreachable, which is exactly the intent. The
    # anchor deliberately stops at the statement — extending it through the trailing comment is what
    # broke it when round 7 rewrote this block, and an anchor that spans prose is an anchor that
    # breaks every time someone explains themselves.
    # ⟳ T3 — ANCHOR UPDATED, RULE UNTOUCHED. `source_generation_id` left the column list and the
    # `do update` set with the column, and the statement gained `returning artifact_id into v_art`
    # because provenance now needs the surrogate key.
    ("record_artifact refuses instead of appending (round 6 H5's declined fix)",
     """  insert into public.video_artifacts
    (workspace_id, video_id, slot, generation_id, kind, state, blob_key,
     start_sec, end_sec)
  values (p_ws, p_video, p_slot, p_generation_id, p_kind, 'recorded', p_blob_key,
          coalesce(p_start_sec, v_start), coalesce(p_end_sec, v_end))
  on conflict (workspace_id, video_id, slot, generation_id) where generation_id is not null
  do update set
       state                = 'recorded',
       start_sec            = excluded.start_sec,
       end_sec              = excluded.end_sec
  returning artifact_id into v_art;""",
     "  return 'refused';",
     "the first writer of a slot got", ART),

    # ⟳ ADR-0007 RE-ANCHORED, AND IT CHANGES OWNER. This was "the idempotency short-circuit removed",
    # which deleted `reserve_artifact_slot`'s `already_recorded` early return and expected a raw
    # [23505] on `video_artifacts_paid_uq`. The entry point is gone; the QUESTION it answered is not,
    # and `record_artifact` now answers it itself through round 7 B1's `on conflict … do update`
    # (05 says so out loud: "it is the same word, because it is the same question").
    # ⚠ AND THIS CLOSES A REAL HOLE RATHER THAN PRESERVING A NOMINAL ONE. Round 7 B1 — a worker
    # retrying its own record collided with its own row, [23505] instead of a typed outcome, shape #8
    # on the money path — never had a mutation of its own. It was covered only incidentally, by the
    # ANCHOR of the entry above, which happened to span the `do update` while testing something else.
    # Making the paid append blind tests it directly, and the expected verdict is the original one.
    # ⟳ T3 — ANCHOR UPDATED for the same two reasons as the entry above, and the replacement keeps
    # `returning artifact_id into v_art` rather than dropping to a bare `;`: without it the mutated
    # function does not compile and the harness reports INVALID, which this project has measured reads
    # as *untested* rather than as *a broken edit*.
    ("the paid append made blind (round 7 B1 — a retry collides with its own row)",
     """  on conflict (workspace_id, video_id, slot, generation_id) where generation_id is not null
  do update set
       state                = 'recorded',
       start_sec            = excluded.start_sec,
       end_sec              = excluded.end_sec
  returning artifact_id into v_art;""",
     "  returning artifact_id into v_art;",
     "video_artifacts_paid_uq", ART),

    # ── item 3: the generation-write API (round 6 B5, Codex B3) ──────────────────
    # ⛔ ⟳ T4 — THREE MUTATIONS STOOD HERE AND ARE REPLACED, NOT RETIRED, AND THE MEASUREMENT THAT
    # FORCED IT IS THE MOST USEFUL THING IN THIS FILE THIS ROUND.
    #
    # They were "gen_card_complete / gen_summary_has_hash / gen_summary_has_format gate removed",
    # each dropping the `state <> 'complete' or` disjunct round 6 B5 added, and each had been RED for
    # eleven rounds. The moment T4 narrowed `state` to a single value and retired the hand-built
    # `pending` fixture that G3 used, ALL THREE WENT GREEN — measured, in this harness, in one run.
    #
    # ⚠ THEY WERE NEVER TESTING THESE CONSTRAINTS. Their red came entirely from one fixture row: a
    # `pending` summary generation carrying no card. Remove the disjunct and that row was rejected;
    # remove the row and the disjunct proves nothing, because with `state` single-valued the disjunct
    # is constantly false and deleting it cannot change which rows are accepted. That is the exact
    # shape T2 recorded when it retired the collectable floor's mutation — "a mutation that can no
    # longer alter behaviour proves nothing" — arriving a second time, by subtraction, in the same
    # slice. 03 deletes the disjunct for the same reason.
    #
    # ⚠ WHAT REPLACES THEM IS THE QUESTION ROUND 17 H1 ACTUALLY ASKED, and the answer is the reverse
    # of the obvious repair. H1 found these three CHECKs gated `kind <> 'summary'`, so a model, dig or
    # digDeeper row carrying only `produced_at` is accepted. The tempting fix is to extend them to
    # every kind. THESE MUTATIONS ARE THAT FIX, and each must go RED against the real fixtures —
    # because no producer of those three kinds computes a card, a doc version or a hash (03's T4 block
    # quotes each one). A gate is load-bearing in two directions and this only ever tested one.
    ("gen_card_complete extended to every kind (round 17 H1's tempting repair)",
     "  constraint gen_card_complete check (\n    kind <> 'summary' or (\n      card is not null",
     "  constraint gen_card_complete check (\n    (\n      card is not null",
     "gen_card_complete", GEN),

    ("gen_summary_has_hash extended to every kind (a dig has no md_hash to give)",
     "  constraint gen_summary_has_hash check\n    (kind <> 'summary' or md_hash is not null),",
     "  constraint gen_summary_has_hash check (md_hash is not null),",
     "gen_summary_has_hash", GEN),

    ("gen_summary_has_format extended to every kind (a dig has no doc version)",
     "  constraint gen_summary_has_format check\n    (kind <> 'summary' or doc_version_major is not null),",
     "  constraint gen_summary_has_format check (doc_version_major is not null),",
     "gen_summary_has_format", GEN),

    ("gen_complete_has_produced_at dropped",
     "  constraint gen_complete_has_produced_at check (produced_at is not null),\n",
     "",
     "no produced_at", GEN),

    # THE DEFAULT. `pending` is the tempting default (it reads as "safer"), and it is the
    # fail-open one: every completeness CHECK becomes optional for a producer that simply
    # omits the column. This mutation is what makes that argument checkable rather than asserted.
    ("state defaults to pending instead of complete",
     "  state             text not null default 'complete'",
     "  state             text not null default 'pending'",
     # ⟳ round 7: was "PENDING generation reached current", and RED(other) said so. The default
     # flipping to `pending` was then caught by the artifact-side trigger, when a fixture that
     # hand-inserts a complete generation tried to record against it. Naming the guard that actually
     # fires is the whole value of comparing `expect`; leaving it stale would have scored a real
     # catch as a miss the moment anything else changed.
     # ⟳ T4 — AND IT MOVED AGAIN, ONE GUARD EARLIER, FOR THE THIRD TIME. With the domain narrowed to
     # `check (state in ('complete'))` the fail-open default is no longer merely caught downstream by
     # something that notices its consequence — it is UNREPRESENTABLE, and the very first generation
     # fixture is rejected by the CHECK itself. That is strictly the better catch (every writer, at
     # the write, naming the column) and re-pointing `expect` at it is what keeps this entry honest
     # rather than scoring a stronger guard as a regression.
     "video_generations_state_check", GEN),

    # ── ⟳ T4: the per-kind invariant ─────────────────────────────────────────────
    # THE RESIDUE T2 NAMED AND LEFT. `state` was single-valued in PRACTICE — no producer of
    # `pending` — while the CHECK still admitted it, and T2 had just deleted the GC floor's
    # `state = 'complete'` predicate as vacuous. Widening this line restores exactly the state T2
    # described: a hand-written pending generation, legal, and collectable with nothing to stop it.
    ("state admits `pending` again (T2's named residual)",
     "                    check (state in ('complete')),",
     "                    check (state in ('pending','complete')),",
     "written PENDING", GEN),

    # The two halves of T4's per-kind measurement, mutated INDIVIDUALLY — round 5 H1's rule, that a
    # compound guard hides which half works. `check (true)` rather than deleting the line, because
    # `gen_major_is_summary_only` is the LAST constraint in the table and removing it would orphan
    # the preceding comma into a syntax error, i.e. INVALID, which this harness has measured reads as
    # *untested* rather than as *retired*.
    ("gen_card_is_summary_only neutralised (a dig may carry a summary card)",
     "constraint gen_card_is_summary_only  check (kind = 'summary' or card is null)",
     "constraint gen_card_is_summary_only  check (true)",
     "carrying a summary card", GEN),

    ("gen_major_is_summary_only neutralised (a model may carry the format rung)",
     "constraint gen_major_is_summary_only check (kind = 'summary' or doc_version_major is null)",
     "constraint gen_major_is_summary_only check (true)",
     "carrying doc_version_major", GEN),

    # ⚠ THE ONLY MUTATION HERE THAT ADDS A WRITER RATHER THAN REMOVING A GUARD, because for
    # `model`, `dig` and `digDeeper` the invariant IS the writer set — no column in those rows
    # witnesses production, so there is no CHECK to delete. This injects a second, perfectly ordinary
    # generation writer and expects 05's enumeration over `pg_proc` to name it.
    # ⚠ IT IS ALSO DELIBERATELY INVISIBLE TO THE R8 SWEEP, which is the point of having both. R8
    # checks a HAND-MAINTAINED list for a leaked PUBLIC EXECUTE; this function is `security definer`,
    # keeps the default PUBLIC EXECUTE, and R8 stays green — because nobody added it to the list. A
    # second writer is exactly the thing nobody adds to a list.
    ("a SECOND function writes video_generations (T4's carried invariant, broken)",
     "revoke all on function ensure_workspace_for_profile() from public, anon, authenticated;",
     """revoke all on function ensure_workspace_for_profile() from public, anon, authenticated;
create function t4_shadow_writer(p_ws uuid, p_video text, p_gen text) returns void
  language plpgsql security definer set search_path = '' as $t4$
begin
  insert into public.video_generations (workspace_id, video_id, generation_id, kind, produced_at)
  values (p_ws, p_video, p_gen, 'dig', now());
end $t4$;""",
     "a SECOND writer of video_generations exists", GEN),

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
     # ⟳ ADR-0007 — was "generation is still PENDING", and RED(other) said so the moment T1 landed.
     # The mutation is unchanged and the guard is unchanged; G3's assertion text moved, because with
     # `pending` unreachable by any RPC the fixture is now a hand-built generation and the assertion
     # names the CONDITION (not COMPLETE) rather than the state. Comparing `expect` is what turns a
     # renamed assertion into a loud mismatch instead of a silently mis-attributed pass.
     "generation is not COMPLETE", ART),

    ("detached_at lower bound removed (backdating the retention clock)",
     "    if new.detached_at < v_produced then",
     "    if (false) then",
     "backdated BEFORE its generation", ART),

    ("detached_at future bound removed (postponing the retention clock)",
     "    if new.detached_at > now() then",
     "    if (false) then",
     "clock starts in the FUTURE", ART),

    # ⟳ ADR-0007 RE-ANCHORED — SAME DEFECT, DIFFERENT WRITER. This was "reserve no longer creates the
    # pending generation (the measured defect)": round 6 B5 measured that with nothing inserting the
    # FK parent, a cloud summarize could not record at all. `record_artifact` is now the ONLY
    # production writer of `video_generations` (04's round 17 B1 note — every other INSERT in the
    # repo is a fixture in 05), so the same defect is reproduced by disabling ITS insert.
    # ⚠ THE EXPECTED ERROR MOVED WITH THE WRITER, and that is the interesting half. The reservation
    # inserted the parent BEFORE the artifact, so removing it hit the artifact's FK [23503]. The
    # record path writes both in one transaction, so removing the parent now hits
    # `video_artifacts_generation_complete` FIRST — a typed P0001 naming the absent generation,
    # verbatim what round 17 T1 measured with the reservation deleted and this INSERT not yet
    # written. Anchoring on the `if` rather than on the statement keeps the mutation valid SQL.
    ("record_artifact no longer creates the generation (round 17 B1's measured defect)",
     "  if not found then\n    insert into public.video_generations",
     "  if false then\n    insert into public.video_generations",
     "cannot mark", ART),

    # ⛔ RETIRED BY ADR-0007 — "a denied reservation keeps the generation row it created" (round 7 H3).
    # It proved the cleanup on the DENIED paths: without it every `busy` loser left an FK-valid parent
    # that no artifact pointed at, no ranking view reached and no sweep collected — unbounded growth
    # for a worker looping on `busy` with a fresh id per attempt. There is no denial path left:
    # `record_artifact` writes the generation and the artifact in one transaction, so either both
    # land or neither does. Retired rather than re-anchored because there is nothing to clean up.
    #
    # ⛔ RETIRED BY ADR-0007 — "record no longer completes the generation". It disabled the UPDATE
    # that flipped a pending generation to complete and expected the artifact-side trigger to refuse.
    # ⚠ IT IS NOT LOST, IT IS MERGED: insert-then-complete became ONE statement, so the mutation that
    # removes the generation write is the entry directly above. Keeping both would have been two
    # anchors on one statement, drifting apart — the failure mode round 11 recorded when it deleted
    # the duplicated free-render reconciler rather than repairing its anchor.

    # ⛔ A round 7 H2 note stood here describing the ownership fence's two disjuncts and why each was
    # mutated separately. It was already stale — round 11 collapsed the fence to one condition and
    # moved its mutations down the file — and ADR-0007 retires the fence entirely. The account now
    # lives in one place, with the three mutations it explains: see "THE OWNERSHIP FENCE, ALL THREE
    # MUTATIONS OF IT" below. Left as a pointer rather than deleted, because a reader who remembers
    # the fence will look for it here first.
    #
    # produced_at is a PARAMETER, not a clock read. Stamping now() is item 1's detached_at
    # defect in a different column, and J2-3 forbids a clock read anywhere the ranking reads.
    #
    # ⚠ ⟳ ADR-0007 RE-ANCHORED, AND THE MASKING ARGUMENT THAT SHAPED IT NO LONGER APPLIES — which is
    # worth saying, because the old form was deliberately convoluted for a reason that has expired.
    # Under the reservation this was an UPDATE of an existing generation, so assigning `now()`
    # outright was caught by the FREEZE trigger on an already-complete fixture long before G9 ran:
    # it proved the freeze works and said nothing about whether the parameter is honoured. The
    # mutation therefore had to DROP the parameter rather than stamp the clock (round 5 H1's masking
    # rule, applied to a mutation instead of a fixture).
    # The write is now an INSERT of a generation that did not exist, so there is no old row and no
    # freeze to mask it: stamping the clock is the honest, direct form of the same mutation, and G9
    # is still the only assertion that can go red for it.
    ("produced_at ignores the caller and reads the clock (sync cannot replicate a time)",
     "            p_card, p_md_hash, p_doc_version_major, coalesce(p_produced_at, now()))",
     "            p_card, p_md_hash, p_doc_version_major, now())",
     "produced_at was stamped, not carried", ART),

    # ── round 7: the guards added for this round's own findings ──────────────────
    ("the produced_at future bound removed (a fast clock outranks reality)",
     """  if new.produced_at is not null and new.produced_at > now() + interval '5 minutes' then
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
    # ⟳ ROUND 11 — "the free-render reconciler removed" was DELETED here, not repaired. Round 11 put a
    # non-holder check above the free INSERT, which broke its anchor; rewriting it produced a mutation
    # that no longer removed anything (GREEN). It was always the same test as "the free upsert made
    # blind" below — both delete the ON CONFLICT handling on the free path — so one is kept rather
    # than two anchors drifting apart. `video_artifacts_free_uq` stays mutation-covered by that entry.
        # The `do update` specifically — keeping the branch but making the insert blind. Without this,
    # deleting the whole branch is the only thing tested, and "the branch exists" is weaker than
    # "the branch reconciles".
    # ⟳ ADR-0007 RE-ANCHORED — the mutation and the rule are untouched; only the lease columns left
    # the `do update` list, and they took the anchor with them.
    ("video_artifacts_free_uq: the free upsert made blind (branch kept, conflict handling dropped)",
     """    on conflict (workspace_id, video_id, slot) where generation_id is null
    do update set blob_key = excluded.blob_key, state = 'recorded';""",
     "    ;",
     "video_artifacts_free_uq", ART),

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

    # ── ⟳ ROUND 9 B3: the workspace resolver, whose absence made ingest impossible ────
    # Each of the trigger's three jobs is mutated separately, because they fail in three
    # different places and a single "disable the trigger" mutation would prove only that
    # SOMETHING in it matters.
    ("B3: workspace_id no longer derived (the [23502] half of the measured defect)",
     "  new.workspace_id := v_ws;",
     "  new.workspace_id := new.workspace_id;",
     'column "workspace_id" of relation "videos"', GEN),

    ("B3: the manifest parent no longer created (the [23503] half)",
     "  if tg_table_name = 'videos' then",
     "  if false then",
     "videos_workspace_video_fk", GEN),

    ("B3: a disagreeing workspace_id silently repaired instead of refused",
     "  if new.workspace_id is not null and new.workspace_id <> v_ws then",
     "  if false then",
     "disagreeing with the playlist", GEN),

    # Restores the EXACT original defect — the confinement re-gated on a non-null generation —
    # rather than deleting the constraint. Deleting it makes a PAID assertion fail first, which
    # would leave the free-row coverage untested by the very mutation added to prove it.
    ("H5: tenant confinement re-gated on a non-null generation (free rows escape again)",
     """  constraint art_key_names_workspace check (
        split_part(blob_key, '/', 1) = workspace_id::text""",
     """  constraint art_key_names_workspace check (
    generation_id is null or
        split_part(blob_key, '/', 1) = workspace_id::text""",
     "a FREE row may not carry a key under another workspace", ART),

    # ── ⟳ ROUND 9: the three schema fixes both reviewers' findings converged on ──────
    # ⛔ RETIRED BY ADR-0007 (round 13 H1 → round 16 B1) — "B1: the collectable floor drops
    # `state = complete` (GC buries in-flight paid work)" (round 9). It removed the predicate from
    # `video_generations_collectable` and expected the R9-3 assertion to fail with "IN-FLIGHT
    # generation is collectable": with a reservation in flight the generation had no current row,
    # so the sweeper was offered a generation whose paid call was still running.
    # ⚠ RETIRED BECAUSE IT WENT GREEN, AND GREEN IS NOW THE CORRECT RESULT. That is the whole reason
    # it is retired rather than repaired. ADR-0007 deletes `reserve_artifact_slot` and the `pending`
    # state, so nothing produces a non-`complete` generation and removing the predicate can no longer
    # change which rows the view returns. A mutation that cannot alter behaviour proves nothing, and
    # left in place its anchor would vanish with the predicate and the harness would report INVALID —
    # which this project has measured reads as *untested* rather than *retired*.
    # ⚠ AND NO SUCCESSOR MUTATION REPLACES IT, because there is no successor guard to cover: no
    # `video_generations` row exists while the paid call runs (`record_artifact` creates it after),
    # so the window is closed by subtraction. Rounds 14-16 costed three covering mechanisms and
    # withdrew all three. An entry here would be the first place one gets silently reintroduced.
    # The currency half of the same view is still mutated — "the collectable view stops excluding
    # CURRENT generations" above — so the floor itself remains covered.

    ("H4: the produced_at tolerance removed (zero-width bound against a txn timestamp)",
     "new.produced_at > now() + interval '5 minutes'",
     "new.produced_at > now()",
     "is in the FUTURE", GEN),

    # The reverse direction matters as much: a tolerance wide enough to swallow round 7 B2 would be
    # a regression wearing a fix's clothes, so widening it must ALSO go red.
    ("H4: the tolerance widened to a week (round 7 B2 undone)",
     "new.produced_at > now() + interval '5 minutes'",
     "new.produced_at > now() + interval '7 days'",
     "should have been rejected: a genuinely future produced_at", GEN),

    # ⛔ RETIRED BY ADR-0007 — "H2: the free short-circuit back to `=` (unreachable for NULL
    # generations)" (round 8 H2). It restored `generation_id = p_generation_id` inside
    # `reserve_artifact_slot`'s idempotency test, where both sides are NULL for a free slot: the
    # comparison was NULL, never true, and the branch could not run at all.
    # ⚠ RETIRED BECAUSE THE CLASS IS NOW UNREPRESENTABLE, NOT BECAUSE IT STOPPED MATTERING.
    # `record_artifact` branches on `if p_generation_id is null then … return` and every surviving
    # `generation_id = p_generation_id` predicate sits below that early return, so no free row can
    # ever reach a three-valued comparison on the generation. A structural fix leaves nothing for a
    # mutation to remove — which is a strictly better outcome than a guard, and worth recording as
    # the reason rather than letting the absence look like an oversight.
    #
    # ⛔ RETIRED BY ADR-0007 — "Claude H2: the free branch stops clearing the lease columns (a
    # reserved free slot is stuck)" (round 9). Round 9's own lease-clearing fix had left a reserved
    # free slot failing `art_pending_has_reserved_at` on every retry, forever. There are no lease
    # columns to clear and no reserved free slot to be stuck. The free `do update` that survives is
    # still mutated — by the free-upsert entry above.

    ("Claude H3: a divergent blob_key silently kept instead of refused",
     "                and generation_id = p_generation_id and blob_key is distinct from p_blob_key) then",
     "                and generation_id = p_generation_id and false) then",
     # ⟳ ADR-0007 — was "differs from the reserved one", and RED(other) said so. The guard is
     # byte-identical; R9-8's fixture stopped laying the first key down with a RESERVATION and now
     # lays it down with a RECORD, so its assertion says "the one this slot already holds".
     "differs from the one this slot already holds", ART),

    # ── ⛔ RETIRED BY ADR-0007 — THE OWNERSHIP FENCE, ALL THREE MUTATIONS OF IT ──────────────────
    # Round 11 wrote these when the fence became ONE condition (`g.reserved_by = p_token`), replacing
    # round 9's pair, which had replaced round 7's disjunct. What each proved:
    #
    #   "the completion fence removed entirely (any caller completes any generation)" — round 11
    #   "a permissive second disjunct reintroduced (the round 7 / round 9 shape)" — round 11
    #       Deliberately a PAIR, in both directions the fence could fail, because round 8 measured
    #       the round-7 fence too permissive AND too strict in one round. The second mutation does
    #       not restore a specific old predicate; it restores the SHAPE — any second condition a
    #       non-holder can satisfy — so the class could not be reintroduced unnoticed.
    #   "round 12 B1: the generation keeps the PREVIOUS caller's token after a reclaim" — round 12
    #       The token the RPC handed out had to be the token the fence accepted. A caller was told
    #       `reserved`, PAID, presented that very token, and was refused.
    #
    # ⚠ THE PAIR IS THE EVIDENCE FOR THE DELETION, WHICH IS WHY IT IS LISTED AND NOT JUST DROPPED.
    # Five successive credentials over six rounds, each round's fix producing the next round's
    # Blocking, because the fence had to be permissive (a reclaimed writer must record work it has
    # already paid for) and strict (a stranger must not complete a generation) at once. ADR-0007
    # removes the credential instead of choosing a sixth: `record_artifact` INSERTs the generation
    # `on conflict do nothing`, so nobody's content can be overwritten by anybody, holder or not.
    # There is no fence, so there is nothing to mutate — the surviving guarantee is a PROPERTY, and
    # its mutation is `completed_by_another` below.

    # ⟳ ADR-0007 RE-ANCHORED — the ONE round-10/11/12 entry whose mechanism survives intact. The
    # guard moved out of the completion UPDATE and into `record_artifact`'s read-then-decide block,
    # and 05 records that it carries MORE weight now, not less: with `reserved_by` deleted it is the
    # whole of what round 7 H2's fence used to promise — a writer whose content was not adopted is
    # TOLD, rather than handed a success string over another writer's hash.
    ("round 10 B1: success reported while another writer's content stands",
     """  if not v_made_gen and v_gen_state = 'complete'
     and p_md_hash is not null and v_gen_hash is distinct from p_md_hash then
    return 'completed_by_another';
  end if;
""",
     "",
     "was NOT adopted was told", ART),

    # ⛔ RETIRED BY ADR-0007 — "round 10 H2: a non-holder may take a live free reservation again".
    # Round 9's lease-clearing fix let a TOKENLESS caller clear a holder's lease and repoint a free
    # slot (measured: pending rows left = 0, key replaced) — the fifth face of the free/paid seam.
    # A free slot can no longer be reserved, held or taken: free renders are unpaid, overwritable and
    # one-per-slot, and that is what the free-upsert mutation above tests.

    ("B3: a new profile gets no workspace (the TOP of the chain)",
     "  insert into public.workspaces (id, owner_id) values (new.id, new.id)\n"
     "  on conflict (owner_id) do nothing;",
     "  insert into public.workspaces (id, owner_id) select new.id, new.id where false;",
     "a NEW profile got no workspace", GEN),

    # The reconciler that makes `sync_corrections_to_workspace_video` SHAPE rather than a guard that
    # destroys data when a caller is merely SECOND. Removing the WHEN clause restores round 6's
    # unconditional INSERT-half sync — harmless for as long as B3 made inserts impossible, and a
    # measured clobber the moment ingest worked.
    ("the INSERT-half sync unguarded (round 6's version, live once ingest worked)",
     "  for each row\n  when (coalesce(new.data->>'corrections','') <> '')\n"
     "  execute function sync_corrections_to_workspace_video();",
     "  for each row execute function sync_corrections_to_workspace_video();",
     "CLOBBERED the shared corrections", GEN),
]


def run(script):
    """Run the verifier that lives beside the schema being mutated — never the repo's."""
    p = subprocess.run([str(script)], capture_output=True, text=True, cwd=script.parent)
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
    # ⟳ ROUND 9 — AND IT NOW COMPARES `expect`, LIKE THE OTHER TWO BRANCHES. Round 6 added the
    # comparison to the assertion branch; round 7 added it to the trigger branch and wrote that not
    # sweeping it was "shape #10, in the fix written hours earlier for the previous instance of shape
    # #11". This branch was the third sibling, and neither round swept to it — so a mutation aimed at
    # one constraint could be caught by ANY constraint and still be scored as covering its target.
    # Found while writing round 9's own mutations, which is the only reason it is not a fourth.
    m = re.search(r"ERROR:\s*(new row for relation|.*violates .*constraint)[^\n]*", out)
    if m:
        detail = m.group(0).strip()
        return ("RED(constraint)" if expect.lower() in detail.lower() else "RED(other)"), detail
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
    # ⟳ T3 — A FOURTH PREFIX, AND IT IS THE THIRD TIME THIS ANCHOR HAS BEEN TOO NARROW.
    # `video_artifact_sources` is NOT matched by `video_artifacts` — the next character is `_`, not
    # `s` — so every one of T3's five trigger guards would have been reported INVALID, i.e. a working
    # guard scored as an untested one, which is the exact failure round 6 B5 and round 7 M2 both
    # recorded here. The list is hand-maintained and that is its standing weakness: a new table's
    # raise prefix is invisible until someone adds it. Ordered longest-first so the intent is legible.
    m = re.search(r"ERROR:\s*(video_artifact_sources|video_artifacts|video_generations|refusing to collect)[^\n]*", out)
    if m:
        detail = m.group(0).strip()
        return ("RED(trigger)" if expect.lower() in detail.lower() else "RED(other)"), detail
    m = re.search(r"ERROR:[^\n]*", out)
    return "INVALID", (m.group(0).strip() if m else "no error captured; SQL did not run")


def main():
    with tempfile.TemporaryDirectory(prefix="mutate-schema-") as tmp:
        return run_suite(Path(tmp))


def run_suite(tmp: Path):
    # The repo files are READ here and never written. Everything the verifier touches lives in
    # `tmp`, so two agents running this at once cannot see each other's mutations (round 8 M3).
    work = tmp / "spec"
    work.mkdir()
    shutil.copytree(SPEC / "schema", work / "schema")
    shutil.copy2(SPEC / "verify-schema.sh", work / "verify-schema.sh")
    (work / "verify-schema.sh").chmod(0o755)
    script = work / "verify-schema.sh"
    copy_of = {GEN: work / "schema" / GEN.name, ART: work / "schema" / ART.name}

    originals = {ART: ART.read_text(), GEN: GEN.read_text()}
    results = []
    for label, find, repl, expect, target in MUTATIONS:
        original = originals[target]
        if find not in original:
            results.append((label, "INVALID", "anchor not found — mutation never applied"))
            continue
        # No `finally` restore is needed to protect the repo — nothing repo-tracked was ever
        # opened for writing. The copy is rewritten wholesale before each mutation instead, so a
        # crash mid-suite leaves a temp directory behind and the checkout untouched.
        copy_of[target].write_text(original.replace(find, repl, 1))
        rc, out = run(script)
        results.append((label, *classify(rc, out, expect)))
        copy_of[target].write_text(original)

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

    # The baseline now proves the COPY is unmutated, which is the only thing this suite could have
    # broken. That the repo is untouched is guaranteed structurally rather than checked.
    rc, _ = run(script)
    print("baseline restored:", "GREEN ✅" if rc == 0 else "STILL BROKEN ❌")
    return 1 if bad or rc else 0


if __name__ == "__main__":
    sys.exit(main())
