<!-- codex-review: model=gpt-5.5 -->

MEDIUM / `scripts/check-review-recorded.py:469`

Concrete failure scenario: `declared_not_derived()` can be satisfied by a derived child directory even when the declared parent directory was not actually found. Today, if the EXECUTED prong stops deriving `docs/superpowers/specs/2026-08-03-stable-blob-addressing` from `$SPEC/verify-schema.sh` / `$SPEC/mutate-schema.py`, the GATE DATA prong still derives `docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema`. That child path makes the parent declaration count as “found,” so the new completeness check passes even though the root-level gate executables vanished from the derivation.

Executed evidence:

```text
$ python3 - <<'PY'
... simulate only the GATE DATA prong over real _gate_sources() ...
PY
only_gate_data_dirs ['docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema', 'docs/superpowers/specs/m4']
declared_not_derived []
coverage []
main would pass anti-drift? True
```

This is not just theoretical: the branch adds a self-test that intentionally blesses this behavior at `scripts/check-review-recorded.py:1269`:

```text
...and a derived path UNDER a declared directory still counts as finding it
```

That makes the completeness guard a coverage check over broad declarations, not evidence that each declared directory was actually derived. The existing mutation manifest does kill the blunt “EXECUTED prong goes” mutation, so I’m not calling this Blocking. But the new mechanism the round-2 fix relies on can pass for the exact spurious-child shape the prompt asked us to attack.

Observation that would prove it fixed: `declared_not_derived(["docs/.../stable-blob-addressing/schema", "docs/.../m4"], CODE_UNDER_PROSE)` reports `docs/superpowers/specs/2026-08-03-stable-blob-addressing/` missing, or the declarations are split so each declared subject corresponds to the exact derived directory/role that proves it.

Additional checks I ran that did not produce findings:

```text
$ python3 scripts/check-review-recorded.py --self-test
157/157 passed

$ python3 scripts/check-plan-code.py --mutate .
OK — delivered scripts mutated: 47 file(s), 723 mutation(s), 723 killed, 723 attributed to the case each names, 0 survivor(s)

$ python3 scripts/check-selftest-counts.py
self-test counts: 40 script(s) declare a count, every one verified by running it

$ python3 scripts/check-ratchet-contract.py
ratchet contract OK
```

I also checked the mutation manifest directly: 52 entries, no duplicate anchor groups, `EXPECTED_MUTATIONS["scripts/check-review-recorded.py"] == 52`, and manifest total `723 == sum(EXPECTED_MUTATIONS)`.

I tried to refute backlog #138’s deferral and failed: accepting bound directories admits `docs/adr`, `docs/reviews/`, and `docs/superpowers/`; content rules do not separate them because `docs/superpowers` itself contains `.sql` and executable gate files. That deferral looks honest.

Verdict: NOT CONVERGED.
