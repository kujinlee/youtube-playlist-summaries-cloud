<!-- codex-review: model=gpt-6.1-sol -->

No actionable round-2 findings.

- Both requested self-tests passed: **60/60** each.
- All **23 mutations** were killed by their declared assertions; the six re-bound anchors still match their named behaviors.
- Forced failures of both scratch and HOME `mkdtemp` restored the environment and cache exactly, leaving no scratch entries. Nested raising and refused blocks also restored exactly.
- Cleanup uses the captured scratch path before restoring HOME/TMPDIR.
- Environment restoration is exact within the documented scope. Concurrent threads and children outliving the block remain explicitly excluded; this provides no thread-safety guarantee.

VERDICT: CONVERGED
