<!-- codex-review: model=gpt-5.5 -->

1. 🟠 High — mutation 22 can still be credited to the wrong problem token.

Premise: `anon_gate` is supposed to match the named problem, not just any red output. The file states the unmutated template is already red and includes `LOWER THE BASELINE 0 money tables are TRUNCATE-able` at `scripts/mutate-live-schema-check.sh:64-77`, and mutation 22 matches only the token `TRUNCATE` at `scripts/mutate-live-schema-check.sh:453`.

Executed evidence:

```text
$ rg -n "anon_gate .*\"TRUNCATE\"|LOWER THE BASELINE|TRUNCATE-able" scripts/mutate-live-schema-check.sh scripts/check-anon-exposure.py
scripts/mutate-live-schema-check.sh:71:#     LOWER THE BASELINE 0 money tables are TRUNCATE-able, baseline says 5
scripts/mutate-live-schema-check.sh:453:    anon_gate "${PREFIX}_trunc" "TRUNCATE" && r=pass || r=fail
scripts/check-anon-exposure.py:279:            f"LOWER THE BASELINE {len(exposed)} money tables are TRUNCATE-able, baseline says
```

And the token is non-discriminating against the documented baseline text:

```text
TRUNCATE: True
M4 NOT READ-ONLY: False
M4 READ LOST: False
M4 OUT OF REACH: False
M4 FN EXECUTABLE: False
```

Consequence: mutation 22 can report “RULE 3 names TRUNCATE on an M4 relation” even if RULE 3 does not name the M4 relation at all, because the unrelated baseline-lowering problem already contains `TRUNCATE-able`. Observable unit: a broken mutation-22 subject can still earn the `anon_gate ... "TRUNCATE"` tick.

Direction: make mutation 22 use the same discriminating problem family as mutation 10/17, preferably `M4 NOT READ-ONLY`, and add `anon_control "$TPL" "M4 NOT READ-ONLY"` or a stricter relation-bearing token such as ``M4 NOT READ-ONLY   `anon` holds TRUNCATE on `video_artifacts` ``.

2. 🟡 Medium — the derived out-of-reach parser is not identifier-normalizing SQL; schema-qualified grants defeat the derivation.

Premise: `GRANT_SELECT` parses grant text and `session_readable()` stores the raw relation token after whitespace splitting, not a normalized relation name: `scripts/check-anon-exposure.py:147-165`. The manifest relation names are bare names from `m4_relations()` at `scripts/check-anon-exposure.py:194-207`.

Executed evidence:

```text
$ python3 - <<'PY'
... load scripts/check-anon-exposure.py ...
print(session_readable("grant select on public.video_artifacts to authenticated, anon;"))
print(derive_no_session_access(["video_artifacts","video_generations_collectable"],
  "grant select on public.video_artifacts to authenticated, anon; "
  "grant select on public.video_generations_collectable to service_role;"))
PY

session_readable: ['public.video_artifacts']
derived_no_session_access: ('video_artifacts', 'video_generations_collectable')
```

Control over current spec spelling:

```text
$ rg -n "grant select on public\.|grant select \(" docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema/*.sql
# no output
```

Consequence: a valid SQL spelling, `grant select on public.video_artifacts ...`, makes an ordinary readable M4 relation derive as out-of-reach because `public.video_artifacts` does not equal manifest name `video_artifacts`. On the current branch this is not silently firing because the shipped spec uses bare names and the derived-vs-declared cross-check is green, but the parser is not robust to normal SQL spelling.

Direction: normalize parsed identifiers before comparing to manifest names: strip optional `public.`, handle quoted identifiers if they are allowed, or stop regex-parsing grants and derive from a catalog built by applying the spec.

**what I checked and did NOT find**

I did not run `verify-schema.sh`, `mutate-schema.py`, or the full gate suite, because the prompt explicitly warned that those contaminate shared `postgres` when run concurrently. I only ran pure/self-test checks and file inspections.

`check-anon-exposure.py --self-test` is green: `62/62 passed`.

I did not find the round-8 total-read-outage hole still open in the pure rule: `evaluate_m4_reads()` is called from `main()` at `scripts/check-anon-exposure.py:875-878`, and its self-test catches a revoked SELECT.

I did not find a current shipped-spec mismatch in the derived out-of-reach set: the self-test case “derive: the SHIPPED spec reproduces the declared out-of-reach set” passed.

I did not find a direct M4 application caller that falsifies the new service-role omission table. The table itself admits the current state: “there is no application code for M4 at all yet” at `docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema/05_assert.sql:1028-1031`.

NOT CONVERGED. The named-token repair still has a concrete false-credit case, and the new spec-derived parser is brittle against ordinary SQL identifier spelling.
