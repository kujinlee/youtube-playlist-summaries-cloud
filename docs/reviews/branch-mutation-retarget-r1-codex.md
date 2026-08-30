<!-- codex-review: model=gpt-5.5 -->

Blocking — `scripts/check-dashboard-entry.py:294`: the impure self-test does not assert `collect()`’s `added` result on the successful git path.

What is wrong: I mutated a temp copy from:

```python
added = any(_added_entry_line(l) for l in patch.stdout.split("\n"))
```

to:

```python
added = True
```

Then `python3 scripts/check-plan-code.py --mutate .` still passed:

```text
OK — delivered scripts mutated: 2 file(s), 43 mutation(s), 0 survivor(s)
```

Why it matters: that is a real fail-open defect. `main()` trusts `added`; with this mutation, any branch with tracked code changes passes the dashboard-entry ratchet as if it added an entry.

Fix: extend `_impure_self_test()` to assert `(ch, ad, err)` for both a no-entry diff and a real `+## YYYY-MM-DD` diff, then add a manifest mutation for `added = True` or equivalent.

High — `scripts/check-plan-code.py:355`: `EXPECTED_MUTATIONS` pins only per-file counts, not mutation identity.

What is wrong: I replaced one `gen-dashboard.json` entry in a temp copy with a duplicate of another entry, preserving the count at 32. `python3 scripts/check-plan-code.py --mutate .` still passed with `43 mutation(s), 0 survivor(s)`.

Why it matters: coverage can shrink silently while the exact-count ratchet stays green. A behavior-specific mutation can be deleted and replaced by an already-covered mutation.

Fix: ratchet identity, not just cardinality. At minimum reject duplicate mutation names and duplicate edit anchors; stronger is an expected per-file manifest fingerprint or expected `{name, edits, expect}` digest stored outside the manifest.

Checked: control runs were green before probing: `check-plan-code.py --self-test` `136/136`, `--mutate .` `43/0`, `check-docs.py` OK, `gen-dashboard.py --self-test` `113/113`. I also checked the extraction: both moved `ev["mutations"].append(...)` and `ev["survivors"].append(...)` sites were converted, `check()` preserves `ok` then report/evidence merge ordering, and YAML parses.

NOT CONVERGED — the delivered mutation gate can still pass over a fail-open dashboard-entry defect and a shrunk manifest.
