<!-- codex-review: model=gpt-5.5 -->

**Findings**

**Blocking: the requested compared plan run is NOT CHECKED in this checkout.**  
Command run:

```bash
python3 scripts/check-plan-code.py docs/superpowers/plans/2026-08-28-project-dashboard-plan.md --compare scripts/
```

Output:

```text
✗ --compare: cannot read scripts/check-dashboard-entry.py ...
✗ --compare: cannot read scripts/gen-dashboard.py ...
FAILED — 2 file(s), 34 mutation(s), 0 survivor(s)
```

`rg --files | rg '(^|/)(gen-dashboard|check-dashboard-entry|check-plan-code)\.py$'` returned only:

```text
scripts/check-plan-code.py
```

The bare plan-copy run does pass:

```text
OK — 2 file(s), 34 mutation(s), 0 survivor(s)
```

And the tool self-test passes:

```text
44/44 passed
```

So the compared subject the command claims to measure is currently absent. That is a loud red, not a false green, but it means the scoped acceptance command did not run successfully.

**High: `--compare` can report two different tagged paths as compared while reading the same delivered file.**  
Source: [scripts/check-plan-code.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-plan-code.py:171)

```python
target = root / pathlib.Path(name).name
```

I built a plan with `one/m.py` and `two/m.py`, and only one delivered `$ship/m.py`. The checker printed:

```text
identical  one/m.py
identical  two/m.py
OK — 2 file(s), 0 mutation(s), 0 survivor(s)
```

That is a false green over a subject it did not uniquely measure. The evidence claims both paths were diffed, but both were compared to the same basename target.

**High: tagged paths can escape the temp assembly directory, including `..` and absolute paths.**  
Source: [scripts/check-plan-code.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-plan-code.py:65), [scripts/check-plan-code.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-plan-code.py:209)

The file tag regex allows `/` and `..`, and assembly writes `(d / name)` directly.

Repro with `<!-- file: ../escape.py -->` printed:

```text
identical  ../escape.py
OK — 1 file(s), 0 mutation(s), 0 survivor(s)
escaped_files:
/var/folders/.../T/escape.py
```

Repro with an absolute tag printed:

```text
identical  /var/folders/.../abs-subject.py
OK — 1 file(s), 0 mutation(s), 0 survivor(s)
absolute_written:
yes
```

So a plan can cause writes outside the temporary directory, and `--compare` still collapses the delivered target to `root / basename`.

**High: mutation application can go green after mutating the wrong occurrence.**  
Source: [scripts/check-plan-code.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-plan-code.py:247)

```python
src = src.replace(find, repl, 1)
```

I created a plan where the first `"1"` is the test oracle, and the production `return 1` is later. The mutation manifest claimed the behavior change, but the checker mutated the oracle, saw the named case fail, and printed:

```text
mutations declared and run: 1, caught 1
  caught   claimed production return changes
OK — 1 file(s), 1 mutation(s), 0 survivor(s)
```

Nothing detects that the intended production occurrence was not changed. This is the same wrong-subject shape inside the mutation engine.

**Medium: `--verify-evidence` cannot satisfy bare local mode and compared CI mode with one pasted block.**  
Source: [scripts/check-plan-code.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-plan-code.py:337), [docs plan](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-08-28-project-dashboard-plan.md:1585)

Observed now:

```bash
python3 scripts/check-plan-code.py ... --verify-evidence
# OK — 2 file(s), 34 mutation(s), 0 survivor(s)
```

But:

```bash
python3 scripts/check-plan-code.py ... --compare scripts/ --verify-evidence
# FAILED ... pasted evidence block is STALE
```

Task 4 Step 5a can resolve the CI form after the delivered files exist: it tells the implementer to regenerate with `--compare scripts/ --evidence` and then verify with the same compared invocation. But after that, the bare `--verify-evidence` form necessarily goes stale. That is only sound if the project treats evidence as invocation-specific and stops advertising the bare command as a durable freshness check.

**Medium: `pasted_evidence()` selects the first marker and can ignore later stale generated blocks.**  
Source: [scripts/check-plan-code.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-plan-code.py:313)

I generated a plan with a fresh evidence block followed by a stale second generated block. The checker printed:

```text
OK — 1 file(s), 0 mutation(s), 0 survivor(s)
```

So a plan can contain stale generated evidence and still pass, as long as the first block is fresh. Quoting the marker earlier in a fenced block also breaks extraction; that repro failed with a stale diff against the quoted `text` fence rather than the real evidence block.

**Low: `[FAIL]` parsing accepts malformed lines that merely contain `[FAIL]`.**  
Source: [scripts/check-plan-code.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-plan-code.py:258)

The collector uses:

```python
for l in out.split("\n") if "[FAIL]" in l
```

and then slices `l.strip()[7:]`. I made a self-test that emits:

```text
prefix [FAIL] named case: got 2 want 1
```

The mutation run was accepted and the checker printed:

```text
caught   malformed fail prefix accepted
OK — 1 file(s), 1 mutation(s), 0 survivor(s)
```

Indentation survives `strip()`, but ANSI prefixes, log prefixes, or no space after `[FAIL]` are not parsed by the stated exact format.

**Self-Test Survivors**

Exact runtime mutants of `scripts/check-plan-code.py` that still printed `44/44 passed`:

```text
unanchor_illustrative        rc=0  44/44 passed
only_last_result             rc=0  44/44 passed
no_timeout_handling          rc=0  44/44 passed
no_docstring_count_enforcement rc=0 44/44 passed
evidence_uses_last_marker    rc=0  44/44 passed
evidence_end_uses_last_fence rc=0  44/44 passed
```

Mutants for unknown mutation target, surviving mutations, compare drift, wrong-case `expect`, colon regression, and bare illustrative tag were caught.

Verdict: NOT CONVERGED.
