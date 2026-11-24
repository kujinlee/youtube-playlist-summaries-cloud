<!-- codex-review: model=gpt-6.1-terra -->

No findings in the round-3 fold.

Both self-tests passed with stdin closed: checker 96/96 and generator 51/51. In a scratch copy, both the restored broad orphan mutant and the distinct narrow mutant failed the orphan case. Reverting the F2 fix and removing the control wording each failed the named F2 case. The `.get(...)` rewrites return `None` for a missing card or field; a present value is still compared with the same expected value.

## Loosening answers
LOOSENING-CHECK 9a6218192351: finding: stateless nodes and absent nodes with anchors now pass rules that master refused.
LOOSENING-CHECK c5f9105b20f3: finding: the checker now accepts stateless nodes and absent nodes with anchors that master refused.
LOOSENING-CHECK 63eb21da8cb3: not a loosening
LOOSENING-CHECK 1772e62bc392: finding: the test no longer requires an absent node with an anchor to be refused.
LOOSENING-CHECK bfad4ea759d8: not a loosening
LOOSENING-CHECK 85de8969926d: not a loosening
LOOSENING-CHECK 4372736ccef4: not a loosening
LOOSENING-CHECK 5b1f3022099c: not a loosening
LOOSENING-CHECK 7acb5cec0b67: not a loosening
LOOSENING-CHECK f0cee815b9a8: not a loosening
LOOSENING-CHECK f7017655a633: not a loosening
LOOSENING-CHECK 3c433a4ee523: not a loosening
LOOSENING-CHECK 58d7a82212f7: not a loosening
LOOSENING-CHECK 762281f1f5f0: not a loosening
VERDICT: CONVERGED
