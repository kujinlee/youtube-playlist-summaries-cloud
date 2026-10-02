<!-- codex-review: model=gpt-5.5 -->

**Subject**

Start fingerprint: `b61218a85d1ebd7f833d672c8750c1bd472bd20a51f825ee2a5cbacd02969c33`

End fingerprint: `b61218a85d1ebd7f833d672c8750c1bd472bd20a51f825ee2a5cbacd02969c33`

No subject drift.

Files opened: `docs/reviews/codex/recall-llm-r8-codex.md`, `docs/reviews/claude/recall-llm-r8-claude.md`, `docs/backlog.md`, `scripts/check-surface-recall.py`, `scripts/check-rc-contract.py`, `scripts/check-ratchet-contract.py`, `.claude/hooks/surface-recall.sh`, `.claude/settings.json`, all three mutation manifests, `scripts/check-plan-code.py`, `scripts/check-selftest-counts.py`, `.github/workflows/ci.yml`.

**NOT CONVERGED**: 1 Blocking · 3 High · 0 Medium · 1 Low

**Verified Green**

In an isolated copy, with `node_modules/typescript` included because `HARNESS_TREE` requires it:

```text
$ python3 scripts/check-surface-recall.py --self-test
surface-recall OK — every declared code renders exactly its approved sentence

58/58 self-test cases passed
PIPESTATUS=0

$ python3 scripts/check-rc-contract.py --self-test
rc contract OK — every defined code is handled or declared, and no arm is dead. What the READER sees is check-surface-recall.py's rule, not this one

55/55 self-test cases passed
PIPESTATUS=0

$ python3 scripts/check-ratchet-contract.py --self-test
self-test: 52/52 passed
PIPESTATUS=0

$ python3 scripts/check-selftest-counts.py
self-test counts: 50 script(s) declare a count, every one verified by running it
rc=0
```

Manifest counts re-derived:

```text
scripts/mutations/check-surface-recall.json: 19 entries
scripts/mutations/check-rc-contract.json: 15 entries
scripts/mutations/check-ratchet-contract.json: 15 entries
EXPECTED_MUTATIONS total files=57 total mutations=1177
EXPECTED_MUTATIONS[scripts/check-surface-recall.py]=19
EXPECTED_MUTATIONS[scripts/check-rc-contract.py]=15
EXPECTED_MUTATIONS[scripts/check-ratchet-contract.py]=15
```

Live controls:

```text
$ python3 scripts/check-surface-recall.py
surface-recall: 6 declared sentence(s), run against the REAL hook in the REAL repo
surface-recall OK — every declared code renders exactly its approved sentence
rc=0

$ python3 scripts/check-rc-contract.py
rc contract: 6 code(s) defined, 4 handled by an arm, 2 declared unhandled
rc contract OK — every defined code is handled or declared, and no arm is dead. What the READER sees is check-surface-recall.py's rule, not this one
rc=0

$ python3 scripts/check-ratchet-contract.py
guards discovered (43): ...
ratchet contract OK
rc=0
```

**Findings**

**Blocking B1 — `check-ratchet-contract.py` reintroduced #213 one wrapper higher: `main()` can discard `assess()` and every named case stays green. Structural.**

Premise: [scripts/check-ratchet-contract.py:1063](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-ratchet-contract.py:1063):

```python
    violations = assess(ROOT, ci_path, texts, ratchets)
```

Measurement:

```text
# control with a real violation: removed the two CI callers for check-surface-recall.py
rc 1
  scripts/check-surface-recall.py  [R3_no_caller]
summary: 1 violation(s), baseline 0

# sever: assess(...) still runs, then violations = []
rc 0
ratchet contract OK

$ python3 scripts/check-ratchet-contract.py --self-test
self rc 0
self-test: 52/52 passed
```

Why severity: this voids the entire ratchet verdict from `main()`. It is round 8 B1’s exact class after the fix extracted `assess()` to make the internals testable; the new call site is untested.

Proposed fix: add a `main()`-level wiring case, not only `assess()` cases, over a staged known-positive tree where `assess()` returns violations and `main()` must report them. Add a manifest entry that severs `violations = assess(...)`.

**High H1 — Eighth/ninth #213 instances: both guards can stop reading the matcher’s defined rc tuple and hard-code today’s six codes. Structural.**

Premise: [scripts/check-surface-recall.py:362](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-surface-recall.py:362):

```python
        defined = _defined_codes()
```

and [scripts/check-rc-contract.py:445](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-rc-contract.py:445):

```python
        defined = defined_codes(_read_or_refuse(MATCHER))
```

Measurement:

```text
## S_defined_literal
CMD python3 scripts/check-surface-recall.py --self-test rc 0
FAILS <none>
SUMMARY ... 58/58 self-test cases passed
CMD python3 scripts/check-surface-recall.py rc 0
FAILS <none>
SUMMARY surface-recall OK

## R_defined_literal
CMD python3 scripts/check-rc-contract.py --self-test rc 0
FAILS <none>
SUMMARY ... 55/55 self-test cases passed
CMD python3 scripts/check-rc-contract.py rc 0
FAILS <none>
SUMMARY rc contract OK
```

No mutation manifest entry I opened targets these call sites.

Why severity: adding or renumbering an rc in `recall-llm.py` is exactly what these guards exist to catch. The internal tuple readers are tested; their consumption by `main()` is not.

Proposed fix: add end-to-end cases that stage a matcher with `SEVENTH = 7` and prove each `main()` reports it. Add manifest entries replacing these fetches with the six-code literal.

**High H2 — `check-rc-contract.observe`’s env scrub is still not load-bearing. Transitional.**

Premise: [scripts/check-rc-contract.py:295](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-rc-contract.py:295):

```python
            _env = {k: v for k, v in os.environ.items() if k in SUBPROCESS_ENV_KEYS}
```

Measurement:

```text
## R_env_wholesale
CMD python3 scripts/check-rc-contract.py --self-test rc 0
FAILS <none>
SUMMARY ... 55/55 self-test cases passed
CMD python3 scripts/check-rc-contract.py rc 0
FAILS <none>
SUMMARY rc contract OK
```

The one-copy allowlist reconciler works:

```text
## allowlist one-copy drift
rc 1
[FAIL] the subprocess env allowlist is the SAME in both guards — round 8 H1
57/58 self-test cases passed
```

But reverting actual consumption to `dict(os.environ)` is still green, and I found no `check-rc-contract.json` mutation entry for it.

Why severity: this is the exact round 8 H1/H2 drift class in the sibling observer. A future regression restores ambient-env-dependent NOT RUN behavior while the suite stays green.

Proposed fix: add the rc-side equivalent of surface’s `PYTHONVERBOSE` case, with the exception caught into a named `[FAIL]`, plus a manifest entry mutating `_env` to `dict(os.environ)`.

**High H3 — H3’s behavioral fix works, but its live diagnostic names the wrong polarity/table. Transitional.**

Measurement with a hook variant that renders less detail:

```text
replacements 2
CMD python3 scripts/check-surface-recall.py rc 1
FAILED — 2 problem(s):
  ✗ at rc 5 the hook does NOT render the sentence DECLARED_RENDER approves when the matcher printed no detail.
  ✗ at rc 6 the hook does NOT render the sentence DECLARED_RENDER approves when the matcher printed no detail.

CMD python3 scripts/check-surface-recall.py --self-test rc 1
[FAIL] the SHIPPED hook renders exactly its declared WITH-DETAIL text
[FAIL] a with-detail render that is not the approved one is reported
...
53/58 self-test cases passed
```

Why severity: the guard catches the bug, so this is not a false green. But the live error tells the maintainer to inspect `DECLARED_RENDER` and “no detail” when the failing rule is `DECLARED_WITH_DETAIL`.

Proposed fix: split the problem message for `undeclared_detail()` so it names `DECLARED_WITH_DETAIL` and says the matcher did print detail.

**Low L1 — The hook seam is unreachable in production by construction, as intended. Structural, not a new defect.**

Opened code: [.claude/hooks/surface-recall.sh:60](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/.claude/hooks/surface-recall.sh:60):

```bash
MATCHER="${1:-$REPO_ROOT/scripts/recall-llm.py}"
```

Production settings: [.claude/settings.json:57](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/.claude/settings.json:57):

```json
"command": "bash .claude/hooks/surface-recall.sh",
```

Measurement:

```text
.claude/settings.json:57: "command": "bash .claude/hooks/surface-recall.sh",
```

So `$1` is reachable to the test caller and unreachable to current production settings. No hook defect found here.

**Could Not Measure**

I did not independently rerun `python3 scripts/check-plan-code.py --mutate .`; per instruction, I treat the reported 1177/1177 killed result as not independently verified by me. I also did not confirm whether the docs-only delta since that run is load-bearing for any of the 57 mutated scripts.
