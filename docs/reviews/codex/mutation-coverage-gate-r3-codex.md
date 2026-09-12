# Codex adversarial review — branch `mutation-coverage-gate`, round 3 (narrow)

**Scope:** two questions only — *is the round-2 fix itself defective?* and *is any claim
contradicted by an artifact?* Style, wording and completeness were OUT of scope, so this is not a
general review. **Subject:** `git diff c6d62f6c..7684c965`.

**Gate provenance:** `scripts/codex-review.py`, model `gpt-5.5`, `gate_ran: true` — testimony at
`docs/reviews/verdicts/mutation-coverage-gate-r3-codex.verdict.json`.

**Verdict: NOT-CONVERGED — one Low**, a stale enumeration in `check-plan-code.py`, fixed in the
commit that files this review. ⚠ That Low was filed in round 2 and the first fix **silently did not
happen**: it asserted on one string and called `.replace()` on another, and `str.replace` on a
missing needle does nothing.

⭐ Its closure audit probed the routes that matter and found them all closed: comments, string
literals, **nested function docstrings, class docstrings, runtime `__doc__` assignment, and
multiline declarations** do not exempt; a module docstring declaration still does. All 9 anchors
unique, `run_mutations()` over a `git archive HEAD` copy returning `attributed=True` with no
survivors. It also correctly reported `--mutate .` as **NOT MEASURED** from the archived tree
(no `node_modules/typescript`) rather than as a pass.


`NO_MUTATIONS_RE = re.compile(r"NO-MUTATIONS:[ \t]+(?!<)(\S[^\n]*)")`; `scripts/mutations/check-ratchet-contract.json` has 9 entries.

**Findings**

Low — stale coverage claim in `check-plan-code.py` contradicts the manifest.  
[scripts/check-plan-code.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-plan-code.py:2986) says `check-ratchet-contract.py` joins with **NINE**, but [scripts/check-plan-code.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-plan-code.py:2988) still says “The six cover …” and enumerates only the original six mechanisms. Evidence from disk: `scripts/mutations/check-ratchet-contract.json` length is 9, and `EXPECTED_MUTATIONS["scripts/check-ratchet-contract.py"] == 9`; the new entries include the R3 escape, debt-paid arm, and whole-file-vs-docstring R4 scope mutations. This is the same round-2 Low, not closed, just made staler by 8 → 9.

**Round 2 findings — closed or not**

R4 whole-file scope: closed. `check_manifest()` now parses `ast.get_docstring(...)` and searches only `doc` at [scripts/check-ratchet-contract.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-ratchet-contract.py:293). Probes showed comments, string literals, nested function docstrings, class docstrings, runtime `__doc__` assignment, and multiline declarations do not exempt; module docstring declarations still do.

Self-exemption reimplementation drift: closed. `self_exemption()` calls `check_manifest(rel, own, set())` and `check_caller(rel, own, "")` at [scripts/check-ratchet-contract.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-ratchet-contract.py:546). Probe result: `(False, False)`.

Too-strict `[A-Za-z]` escape pattern/messages: closed. Backtick, digit, glyph, dash, and quote-initial docstring reasons exempt; `<why>` is refused.

`check-plan-code.py` “six cover …” stale claim: not closed. See finding.

Self-test `+1` count vulnerability: closed. `SELF_EXEMPTION_CASES` is table-driven and counted by `len(...)` at [scripts/check-ratchet-contract.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-ratchet-contract.py:700).

Fixture-variation exemption split: closed. `check_manifest.path` is not exempt; `check_manifest.text` remains exempt with the written reason at [scripts/check-fixture-variation.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-fixture-variation.py:505).

**Checked and found sound**

Green runs: `check-ratchet-contract.py`, `check-ratchet-contract.py --self-test` `40/40`, `check-fixture-variation.py`, `check-selftest-counts.py`, and `check-plan-code.py --self-test` `128/128`.

All 9 anchors occur exactly once. Direct `run_mutations()` over the 9 `check-ratchet-contract` entries from a `git archive HEAD` copy returned `ok=True`, no survivors, and all entries `measured=True` / `attributed=True`.

Arithmetic: manifest 9, `EXPECTED_MUTATIONS == 9`, sum 558, calculated self-test total 40, guard population 34. No current `scripts/*.py` module docstring declares either escape.

Full `check-plan-code.py --mutate .` from `git archive` was not checked: the archived tree lacks `node_modules/typescript`, so the harness correctly returned `NOT MEASURED`.

NOT-CONVERGED
