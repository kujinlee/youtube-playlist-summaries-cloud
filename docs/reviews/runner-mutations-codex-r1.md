<!-- codex-review: model=gpt-5.5 -->

Found 2 issues. No Blocking findings.

**High** [scripts/check-plan-code.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-plan-code.py:317): `ESCAPE_EXEMPT` is a code-line off switch, and it also matches marker text inside string literals.

Failure scenario: this source is accepted by `home_escapes`:

```python
REAL = pwd.getpwuid(os.getuid()).pw_dir; s = "# not-a-home-escape:"
```

I verified it returns `[]`. The regex sees the `# not-a-home-escape:` inside the string, treats the following quote as the required “reason”, and drops the whole physical line, including the real `pwd.getpwuid` route before it. An explicit inline comment also bypasses the check:

```python
REAL = pwd.getpwuid(os.getuid()).pw_dir  # not-a-home-escape: production escape
```

That is not file-wide for normal multi-line files, but a single crafted physical line can exempt every dangerous route on that line. Since this gate’s purpose is preventing mutation runs from reaching the user’s real home, this is too easy to bypass.

Fix: remove the marker by constructing self-test fixture strings dynamically so `check-plan-code.py` no longer contains literal escape routes, or replace the text filter with a token/AST-aware scheme plus a narrow fixture allowlist. Do not let an inline marker suppress executable code on the same line.

The current exempted lines themselves look like fixtures/prose, not real home escapes: lines 302, 1176-1194, 1760-1775 are rule text, case names, fixture strings, or assertions about reports.

**Medium** [scripts/check-plan-code.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-plan-code.py:633): the excluded mutation `caught = rc == 1` -> `caught = rc != 0` is not equivalent.

Failure scenario: a mutated target exits with `sys.exit(3)`. Current code does not credit that as caught; the excluded mutant would credit any non-timeout nonzero as caught. The preceding `if rc == 2: continue` only excludes timeouts, not arbitrary nonzero exits. I verified the mutant manually:

```text
anchor_count 1
rc 0
152/152 passed
```

So the current self-test suite does not distinguish `rc == 1` from `rc != 0`.

Fix: add a self-test where a mutation makes the target suite exit with a non-1/non-2 code and assert it is not reported as a caught named case. Then include the mutation in the manifest, or intentionally change the contract to “any nonzero except 2 is red” and update the comments/reporting accordingly.

Other checks I ran:

```text
python3 scripts/check-plan-code.py --self-test
152/152 passed

python3 scripts/check-plan-code.py --mutate .
OK — delivered scripts mutated: 4 file(s), 90 mutation(s), 0 survivor(s)
```

I also individually applied all 17 new `check-plan-code.json` entries. Each exited red and included its exact named `expect` case in the failure list. I did not find an included entry that is vacuous/equivalent, or a self-mutation where the outer orchestrator’s judgement is corrupted rather than observing the temp-copy target.

Statefulness: `runs.txt` is created under the temp copied `scripts/` tree and is removed with the tempdir. The two real-home canary cases use per-tempdir names and content-matched cleanup; a crash after writing could still leave debris, and concurrent basename collisions across different temp parents could race, but I’d rate that residual Low given the unique temp names and content check.
