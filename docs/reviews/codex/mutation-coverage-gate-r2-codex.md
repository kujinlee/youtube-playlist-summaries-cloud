# Codex adversarial review — branch `mutation-coverage-gate`, round 2

**Subject:** `git diff a5bfe9c5..c6d62f6c` — the round-1 fixes (markers assembled, `self_exemption()`
added, `NO_CALLER_RE` tightened, the "TENTH file" ordinal removed, all eight pinned entries
re-measured).

**Gate provenance:** `scripts/codex-review.py`, model `gpt-5.5`, `gate_ran: true` — testimony at
`docs/reviews/verdicts/mutation-coverage-gate-r2-codex.verdict.json`.

**Verdict: NOT-CONVERGED — one Blocking, and BOTH HALVES FOUND IT INDEPENDENTLY.** R4 was still
whole-file scoped, so a comment or string literal granted the exemption in any OTHER guard;
round 1 had closed the route for this file only, with a bespoke `self_exemption()`. Fixed in the
commit that files this review: `check_manifest` now parses the docstring exactly as `check_caller`
has always done, and `self_exemption()` calls the shipped rules rather than re-applying the regexes.

⭐ Its "Round 1 findings — closed or not" section confirms the other four closed, and its evidence
was taken against `git archive HEAD` rather than the dirty checkout — the right instrument.


`NO_CALLER_RE = re.compile(r"NO-CALLER:[ \t]+([A-Za-z][^\n]*)")`; `scripts/mutations/check-ratchet-contract.json` has 8 entries.

**Findings**

**Blocking — R4 still accepts `NO-MUTATIONS:` outside the docstring for every other guard.**  
Where: `scripts/check-ratchet-contract.py:274-284` at committed `HEAD` `c6d62f6c`; the escape rule says “in the docstring” at `:239`, but `check_manifest()` still runs `NO_MUTATIONS_RE.search(text)` over the entire source at `:283`.

What: round 1’s self-exemption was fixed for `check-ratchet-contract.py` specifically by `self_exemption()`, but the underlying R4 rule is still whole-file scoped. A comment, fixture string, or ordinary source literal in any other guard can grant the file a mutation exemption without a docstring declaration.

Concrete failing scenario: a new guard has a normal docstring, no manifest, and this ordinary implementation comment:

```python
# NO-MUTATIONS: temporary note about a future declaration
```

R4 should report `R4_no_mutation_manifest`; at committed `HEAD`, it reports nothing.

Evidence run against a `git archive HEAD` copy, not the dirty checkout:

```text
rules []
NO_MUTATIONS_RE NO-MUTATIONS:[ \t]+([A-Za-z][^\n]*)
check_manifest_source_line     if NO_MUTATIONS_RE.search(text):
```

That result came from calling the shipped `check_manifest("scripts/check-stray.py", text, set())` on a synthetic guard whose docstring did not contain the escape. This is the same relocation class as r1, just no longer in this file because `self_exemption()` is bespoke.

**Round 1 Findings — Closed Or Not**

1. Blocking, R4 self-exemption relocated into `ESCAPE_CASES`: closed for this file, not closed as a class. `self_exemption()` now reads its staged `__file__` and catches this file, but `check_manifest()` still accepts non-docstring escapes in other files.
2. Blocking, `NO_CALLER_RE` had the identical hole: closed. Old/new scan over `scripts/*.py` found exactly one status change, `scripts/check-ratchet-contract.py` old match `NO-CALLER:\`  ENFORCED`, now rejected.
3. High, “TENTH file” and “seven printers”: closed. The ordinal is removed; the docs now say five pre-existing printers.
4. Medium, `m4_catalog.py rc=0` read as success: closed. I re-ran all eight entries; `m4_catalog.py` is recorded as `rc=0` with zero bytes/no suite, `gen-m4-manifest.py` cannot run, and `subject_status.py` is red.
5. Low, missing mutations for `R4W_debt_paid_not_recorded` and R3 escape tightening: closed. Both entries exist and attribute to their named cases.

**Checked And Found Sound**

`self_exemption()` works under a staged copy and from `/`: `__file__` pointed at `/tmp/.../repo/scripts/check-ratchet-contract.py`, `self_exemption()` returned `(False, False)`, and the copy’s source matched neither escape.

Hiding `scripts/mutations/check-ratchet-contract.json` in a temp copy makes the gate red on itself with `scripts/check-ratchet-contract.py [R4_no_mutation_manifest]`, `rc=1`.

The assembled markers are currently effective in committed `HEAD`: direct source scan finds no `NO_MUTATIONS_RE` or `NO_CALLER_RE` match in `scripts/check-ratchet-contract.py`. I found no repo Python formatter config or pre-commit formatter, and `python3 scripts/check-docs.py` is green/read-only.

The eight mutation anchors are unique in `scripts/check-ratchet-contract.py`; each anchor count was `1`. A targeted `run_mutations()` pass imported `parse_fail_names` through the real harness path: all 8 were `caught=True`, `attributed=True`, `measured=True`, no survivors.

Arithmetic checked: manifest length `8`; `EXPECTED_MUTATIONS["scripts/check-ratchet-contract.py"] == 8`; sum `557`; computed ratchet self-test total `35`; `check-selftest-counts` population length `37`; `python3 scripts/check-selftest-counts.py` verified all 37.

Historical claim checked in a temporary git worktree of `master` `7674fe87`: `scripts/subject_status.py --self-test` is red at `16/17`, `rc=1`.

NOT-CONVERGED
