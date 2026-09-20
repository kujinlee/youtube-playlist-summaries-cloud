<!-- codex-review: model=gpt-5.5 -->

**Findings**

**Low — `.claude/hooks/regen-features-page.sh:40` still silently ignores valid JSON whose path field moved.**

The malformed-stdin instance is fixed, but the “payload shape changed” class is only closed for invalid JSON. A valid JSON payload with the edited path under a renamed key exits `0`, prints nothing, and does not regenerate even when it names `docs/features.md`.

Quoted code:

```bash
print(d.get('tool_input', {}).get('file_path', '') or '')
```

Exact inputs I ran:

```bash
printf '{"tool_input":{"path":"docs/features.md"}}' | bash .claude/hooks/regen-features-page.sh
printf '{"file_path":"docs/features.md"}' | bash .claude/hooks/regen-features-page.sh
printf '{"toolInput":{"filePath":"docs/features.md"}}' | bash .claude/hooks/regen-features-page.sh
```

Observed for each: `rc=0`, empty stdout/stderr. By contrast, `printf 'not json' | bash ...` now warns, so the literal malformed-stdin repro is addressed.

**Round-1 Verdicts**

Blocking: **ADDRESSED.** I reran the original repro with `> currently broken, see #322.` and additional inert-looking shapes: bare `-`, indented continuation, backticks, table row, HTML non-comment, and indented blockquote. All are refused by `scripts/check-features.py:66-71` as “neither a field nor a heading.”

High: **ADDRESSED.** Duplicate exact fields are refused and the first value stands. I reran both bypass shapes: `anchors: cloud-publishing` followed by blank `anchors:`, and status-bearing `for:` followed by clean `for:`. Both now produce parse problems; the anchor case also still reaches the absent-with-fragment rule.

Low: **ADDRESSED for the exact reported malformed-stdin repro; residual Low above for valid-JSON shape drift.**

**Other Checks Run**

`python3 scripts/check-features.py` passed: 26 nodes, all anchors/areas claimed once.

`python3 scripts/check-features.py --self-test` passed: 30/30.

`python3 scripts/gen-features-page.py --self-test` passed: 12/12. Its hook cases do not reach the generator, so they did not write the real `~/explainers/features.html`.

Hook-absent simulation did not silently pass: it returned rc `1` with `[FAIL]` lines and CANNOT RUN text in the hook-call failures.

For the three new mutation-manifest entries, each `edits` anchor occurs exactly once. I ran the repo’s own `run_mutations` path against those three entries: all three were caught, attributed, measured, and had zero survivors.

Full `python3 scripts/check-plan-code.py --mutate .`: **NOT RUN**. Targeted mutation checks for the three new entries were run.
