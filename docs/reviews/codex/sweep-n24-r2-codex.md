<!-- codex-review: model=gpt-6.1-sol -->

### R2-F1 — Low — Estimated completion time remains inside a MEASURED claim

[ci.yml:1171](.github/workflows/ci.yml#L1171) places “~1,881s needed” under **MEASURED**, before the **PREDICTED** label. The shard was cancelled at 1,814s; round 1 derives 1,881s by extrapolating unfinished re-control. Label this value “estimated total” explicitly.

### R2-F2 — Low — Future threshold crossing is stated as measured certainty

[ci.yml:1185](.github/workflows/ci.yml#L1185) ends the **MEASURED** paragraph with “The next manifest growth crosses it.” That is an unlabelled prediction. A 1,499s maximum cannot establish that the next addition crosses 1,500s: its cost, shard assignment and runner variation matter. Replace with “PREDICTED: further manifest growth risks exceeding 1,500s.”

The cited run otherwise confirms 24 successful shards, mean **1,300.42s**, and longest durations **1,499 / 1,460 / 1,459s**; **1.20×** is correct. Both YAML versions parse identically, all noncomment text is unchanged, and the matrix remains **1–24**. The dashboard preserves both entries without loss or duplication.

VERDICT: NOT CONVERGED
