<!-- codex-review: model=gpt-6.1-sol -->

## Blocking

None established.

## High

None established.

## Medium

1. **`scripts/check-withdrawal.py`, `mask_inline_code`: escaping the first backtick incorrectly discards the entire run.**

   Code:
   ```python
   if backtick_escaped(text, open_run.start()):
       i += 1
       continue
   ```

   Input: `"the count was \\``v1:\n2` and 1,414 today"`.

   The backslash escapes the first backtick; the second opens a valid single-backtick span. Both **cmark-gfm and markdown-it-py** render `v1: 2` as code. The shipped mask leaves its newline unmasked, so `history_marker` returns `''`; masking that actual code-span newline returns `'was '`. This produces a false survivor.

   **Ran:** both parsers and the shipped `mask_inline_code`/`history_marker` under Python 3.12. The opener-only rule still operates on the wrong lexical unit: the maximal run before escaping is resolved.

2. **`scripts/codex-frontier-model.py`, `_write_config_arm`: the new preservation test accepts invalid or incorrectly scoped configuration.**

   Code:
   ```python
   if pre == "keep" and 'keep_me = "yes"' not in second:
       return (0, "wrote-discarding-the-rest")
   ```

   Two concrete mutations survived:
   ```python
   f.write(block + block + existing.lstrip("\n"))
   f.write(existing.lstrip("\n") + block)
   ```

   The first duplicates `model` and produces invalid TOML. The second places the managed model after `[profile]`, making it `profile.model` instead of the required top-level `model`. Both retain the checked substring.

   **Ran:** AST-validated temporary copies, each complete `--self-test`: **rc=0, 51/51, zero `[FAIL]`**. Parsed their actual output with Python 3.12 `tomllib`: duplicate rejected with “Cannot overwrite a value”; appended block parsed as `{'profile': {'keep_me': 'yes', 'model': 'test'}}`.

   **Known-positive control:** replacing the write with `f.write(block)` produced **rc=1, 50/51**, with the named preservation `[FAIL]`.

## Low

**`scripts/check-provenance.py`, `PROVENANCE_RE`: the stated malformed-token residual is incomplete.**

Code:
```python
(?=\s|$|`|[.,;:!?)\]](?![\d.]))
```

`"measured at HEAD~?"` is accepted, although `git rev-parse --verify 'HEAD~?'` returns **128**. This is another malformed token besides the stated `HEAD~!`.

**Ran:** the shipped regex under Python 3.12 and Git verification. Prose punctuation creates ambiguity here; this is a limitation of the residual accounting, not an established high-impact regression.

## Checked and found SOUND

- **Arithmetic reproduced:** 62 manifests, declared sum **1,526**, disk total **1,526**, every per-file count matches.
- **Python 3.12.9 suites:** find-claim **86/86**; withdrawal **112/112**; provenance **152/152**; plan-code **237/237**; frontier-model **51/51**. All rc=0.
- **Binding:** rc=0, **1,534 anchors / 1,526 entries**.
- **Diff:** exactly **8 files, 609 insertions, 100 deletions**.
- **Historical CI:** `gh run list` and `gh run view 37778056716` confirm all eight mutation shards and `mutation-sweep-complete` succeeded at `6e829059`. The overall CI run failed because `verify` failed.
- **Document-mask call site:** `win` and `masked_win` use identical bounds. `main` retains document strings in `blobs`, preventing identity recycling during that invocation. Length validation alone does not prove mask identity, but this caller supplies it correctly.
- **Retired mutation’s successor:** disabling the opener escape guard in a temporary scripts copy parsed successfully and produced **two attributed `[FAIL]` lines**, rc=1, **110/112**.
- **Backlog #265:** preferring a descendant dispatch head is reasonable for ancestor-related ties. Reversing filename order fails for double-digit rounds. Recency alone does not establish coverage dominance when dispatch overlays differ; the candidate remains appropriately marked unverified.

## CANNOT RUN

None outstanding. All reported probes completed. The reviewed worktree was left unchanged.
