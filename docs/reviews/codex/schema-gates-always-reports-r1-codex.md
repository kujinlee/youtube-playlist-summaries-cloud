<!-- codex-review: model=gpt-5.5 -->

High: `scripts/check-review-recorded.py:334` / `scripts/check-review-recorded.py:336` silently misses a new docs-hosted gate when its input is not `.sql` or `.txt`. Concrete scenario: add this to `scripts/check-schema-gates.sh`:

```sh
run "16/16 new docs gate" python3 scripts/check-new-docs-gate.py
```

and have `scripts/check-new-docs-gate.py` read `docs/superpowers/specs/new-gate/rules.json`, either as:

```py
RULES = "docs/superpowers/specs/new-gate/rules.json"
```

or as a normal `pathlib` join:

```py
ROOT / "docs" / "superpowers" / "specs" / "new-gate" / "rules.json"
```

That is a realistic gate input shape: JSON/YAML policy/config is ordinary for a new checker. But the anti-drift derivation only adds bound docs paths whose suffix is in `GATE_DATA_SUFFIXES = (".sql", ".txt")`, and the non-empty current result satisfies the cannot-run guard at `scripts/check-review-recorded.py:985`. So `prose_exceptions_cover()` at `scripts/check-review-recorded.py:997` never sees `docs/superpowers/specs/new-gate`, `CODE_UNDER_PROSE` is not forced to grow, and a later PR changing only `docs/superpowers/specs/new-gate/rules.json` is classified as prose and owes no review round.

Observation that proves it: importing the function and feeding exactly that shape returns only the existing stable-blob dir, not the new gate dir:

```text
json via pathlib join: ['docs/superpowers/specs/2026-08-03-stable-blob-addressing']
json assignment: ['docs/superpowers/specs/2026-08-03-stable-blob-addressing']
txt assignment: ['docs/superpowers/specs/2026-08-03-stable-blob-addressing', 'docs/superpowers/specs/new-gate']
```

That is the feared “non-empty but wrong set” fail-open: the present docs gates keep `_dirs` non-empty, while the new gate’s docs directory is invisible.

Verdict: NOT CONVERGED.
