<!-- codex-review: model=gpt-5.5 -->

**Findings**

**Medium: `expect` still accepts substrings, not exact case names.**  
Source: [scripts/check-plan-code.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-plan-code.py:366):

```python
unnamed = [(w, [f for f in fails if w in f]) for w in wants]
```

Command run: targeted fixture importing `scripts/check-plan-code.py`.

Output:

```text
bare substring unique ok= True fails= ['f returns one', 'unrelated unique case'] report= []
list one substring ok= True fails= ['f returns one', 'unrelated unique case'] report= []
unrelated unique ok= True fails= ['f returns one', 'unrelated unique case'] report= []
```

So round 5’s “exactly one red case” guard is cardinality-only. A unique substring, or a unique unrelated red case, still certifies the mutation. This is better than round 5’s many-match hole, but not exact naming.

**Low: `expect: []` is silently equivalent to no `expect`.**  
Same source: [scripts/check-plan-code.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-plan-code.py:360):

```python
wants = [want] if isinstance(want, str) else list(want or [])
```

Command output:

```text
empty list ok= True fails= ['f returns one', 'unrelated unique case'] report= []
```

If an empty list is meant to be a declared set of expected cases, this should be invalid. If it is meant to mean “no expectation”, current behavior is coherent but should be documented.

**Checked, no defect filed**

Baseline:

```text
python3 scripts/check-plan-code.py --self-test
92/92 passed

python3 scripts/check-plan-code.py docs/superpowers/plans/2026-08-28-project-dashboard-plan.md
OK — plan's copy only, NOT compared: 2 file(s), 34 mutation(s), 0 survivor(s)
```

`INVISIBLE_FENCE`: no issue found on the plan. Command output:

```text
extract problems 0
invisible fence problems []
tally {'python_fences': 13, 'tagged': 12, 'illustrative': 1, ...}
```bash 8
```json 1
```yaml 2
```python 13
```

Bare `bash/json/yaml/text` fences are not flagged. Info-string and indented fences are flagged. Inside an already-open python block, `INVISIBLE_FENCE` is not consulted; only a bare column-0 closing fence closes the block.

Tag sanitisation: `a/../b.py` is refused. Absolute POSIX paths are refused. `a//b.py` is accepted. `a/b.py/` fails loudly at execution, not green:

```text
FAILED — plan's copy only, NOT compared: 1 file(s), 0 mutation(s), 0 survivor(s)
```

`--compare .`: with repo root `.` and `./`, it fails loudly today because files do not exist, as expected. From a non-root cwd, `--compare .` is just the wrong directory and also fails, not a false green.

**Mutation Run**

Command run: 27 scoped mutants against `python3 <mutant> --self-test`.

Result:

```text
valid mutants 27 caught 21 survived 6 invalid 1
```

Survivors:

```text
missing_anchor_allowed         92/92 passed
expect_requires_exact_string   92/92 passed
mut_tag_unanchored             92/92 passed
final_mode_drops_compared_verified 92/92 passed
count_drift_disabled           92/92 passed
evidence_uses_last_marker      92/92 passed
```

`expect_requires_exact_string` is stricter than current behavior, so not a defect. `evidence_uses_last_marker` is equivalent under the new `md.count(EV_MARK) > 1` guard. The remaining four are non-equivalent test gaps, but only `expect` produced a current false-green behavior in my fixtures.

NOT CONVERGED.
