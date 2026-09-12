# Codex adversarial review — branch `mutation-coverage-gate`, round 1

**Subject:** `git diff 7674fe87..HEAD` at `a5bfe9c5` — R4's population widened to self-tested
non-guards, the `NO-MUTATIONS:` escape regex tightened, 5 failure printers fixed, 12 new cases, a
new 6-entry manifest, and the ratchets that move with them.

**Gate provenance:** `scripts/codex-review.py`, model `gpt-5.5`, `gate_ran: true` — testimony at
`docs/reviews/verdicts/mutation-coverage-gate-r1-codex.verdict.json`.

**Verdict: NOT-CONVERGED — one Low.** Its "Checked and found sound" section is the load-bearing
half: it independently re-ran the OLD regex across all 34 guards and confirmed exactly one prose
self-exemption, confirmed the tightened pattern breaks no real declaration, confirmed zero overlap
between the guard and widened populations, and confirmed all 6 manifest entries kill with
`attributed=True` over a green control.

⚠ **The Low was right and is fixed.** It is also the SIXTH instance in this session of one failure
mode: a count taken from tooling output without asking what population it covered. Five printers
were broken at base; the "seven" counted two loops this branch had itself just added.


"a guard that only DOCUMENTS the escape is not exempted by it"; new `NO_MUTATIONS_RE` pattern is `NO-MUTATIONS:[ \t]+([A-Za-z][^\n]*)`.

**Low**
[docs/dashboard-entries.md](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/dashboard-entries.md:7874) says “Seven printers said `  FAIL {name}`”. I can’t reconcile that with the diff. At base `7674fe87`, `git show 7674fe87:scripts/check-ratchet-contract.py | rg 'print\\(f"  FAIL'` finds 5 broken printers. At head, [scripts/check-ratchet-contract.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-ratchet-contract.py:567) has 8 `[FAIL]` printers total, because three are new loops for new case groups, not old broken printers fixed. This is not a behavior defect, but it is a measured dashboard claim that is wrong or at least unsupported by the artifact.

**Checked and found sound**
Old regex over all 34 current guards found exactly one prose self-exemption: `scripts/check-ratchet-contract.py`, matching line 16’s documented escape. No second guard matched.

The tightened regex found no real existing declaration broken in script docstrings; the only real docstring hit was the prose documentation case, now rejected.

Widened population: 55 `scripts/*.py`, 34 guards, 16 widened non-guards, zero guard overlap, 8 widened violators, exactly equal to `WIDENED_MANIFEST_DEBT`.

Mutation manifest: 6 entries, every `before` anchor unique, control green, all 6 killed with `attributed=True` via `check-plan-code.parse_fail_names`.

Fixture exemptions: removing each of the 4 new exemptions reintroduces exactly its named `check-fixture-variation` finding; with them present, no such findings remain.

Ratchet arithmetic: `EXPECTED_MUTATIONS["scripts/check-ratchet-contract.py"] == 6`, manifest length is 6, declared sum is 555, membership list includes the file.

Required runs were green: `check-ratchet-contract.py`, `check-ratchet-contract.py --self-test`, `check-fixture-variation.py`, and `check-selftest-counts.py`.

NOT-CONVERGED
