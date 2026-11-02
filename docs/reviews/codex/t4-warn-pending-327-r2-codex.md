<!-- codex-review: model=gpt-6.1-sol -->

- **Low — `docs/dashboard-entries.md:17499`: stale verification counts after the fold.** The entry says “three mutations, 128/128.” The fold adds a fourth mutation; parsing the manifest gives **129 entries**, matching `EXPECTED_MUTATIONS`. Update the entry to reflect the fold’s reported 129/129 sweep, or explicitly label 128/128 as pre-fold evidence.

Executed verification:

- Decision-scheme self-test: **274/274 passed**. CLI: **exit 0**.
- Ten independent mutations in a temporary copy each failed **both** CLI cases: exit code, prefix, duplicate line, median, comparator, backlog reference, ending, ambient `FAIL`, suffix-only output, and hard wrapping. Each produced **272/274**, exit 1. Current `print()`/`StringIO` output cannot acquire terminal wrapping.
- CM1: manual suspension expiry is stated in `main()`, backlog #327, and the dashboard.
- CL3 against `65e9263a`’s log: excluded subjects have **7, 6, 6, 7** rounds. The qualifying window is **[4,7,4,5,4]**; including those four raises the median to **6**. The split claim is labelled an inference.
- Explainer diff contains only the two trigger-4 notes, master’s backlog #105 shim comment, and timestamp.
- Decision log: `invalid_rows(...) == []`; the new row validates with its unit history. Its prediction names a falsifiable observation: any Medium+ finding or a fold-caused finding in the named components.
- Plan-code self-test: **215/215 passed**. `git diff --check` passed.

No Medium-or-higher defect found. The stale dashboard counts remain a Low record defect.

VERDICT: NOT CONVERGED
