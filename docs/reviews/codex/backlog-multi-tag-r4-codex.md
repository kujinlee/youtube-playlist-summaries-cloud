<!-- codex-review: model=gpt-6.1-sol -->

1. **Major — `scripts/gen-backlog-page.py:1111`, consumed by `scripts/check-features.py:189`: rows outside a recognized header still make master red and HEAD green.**

   Append this to each ref’s backlog in temporary copies:

   ```markdown
   ## Probe
   | No | Item | Touches | Size | Bundle | Status |
   |---|---|---|---|---|---|
   | ⭐999 | 🟡 **Probe** | f | S | (not-claimed) | open |
   ```

   Run `python3 scripts/check-features.py`:

   - **origin/master: exit 1**, `(not-claimed)` is claimed by no node.
   - **HEAD: exit 0**, all backlog areas claimed.

   The parser recognizes only a `#` header. With no recognized header, it skips the decorated row before recording `unread`; collecting that list cannot catch it. Omitting the header also reproduces this with `⭐999`, `#999`, `**999**`, `999a` and `abc`. This refutes the SPLIT bet’s second clause.

2. **Minor — `docs/backlog.md:363`, `docs/dashboard-entries.md:17956`, PR #421 body: suite counts became stale when #383 was filed.**

   Reproduction: load `gen-features-page.py`, call `collect()` on the real feature nodes, exclude fragments with `closed=True`, and count unique backlog links across the three suite nodes.

   | Count | Published | Executed |
   |---|---:|---:|
   | status-pages | 14 | 14 — 🟠3 🟡8 🟢3 |
   | feature-map | 2 | **3 — 🟡3** |
   | explainer-pages | 19 | 19 — 🟠4 🟡10 🟢5 |
   | Distinct open rows | 30 | **31** |

   The additional row is #383, tagged `(comprehensibility/feature-map)`.

Other confirmation results:

- **61 paired probes** executed in `/tmp/multitag-r4.XjiWoE/{master,head}`. All five requested number decorations fail correctly under valid headers, both in new tables and the real Items table. Header, fence, alignment, pipe, width and malformed-tag probes found no additional parser-reported problem bypassing validation.
- `()` also produces master-red/HEAD-green, but HEAD explicitly defines and tests it as untagged; this is an intentional grammar difference.
- **#383 is filed with a concrete FAILS IF.** Adding its decorated-row reproduction leaves the rendered features fragment byte-identical to baseline on **both refs**, confirming the pre-existing omission.
- Checker mutations: **30/30 killed and attributed**, including both new mutations by their named cases.
- `EXPECTED_MUTATIONS` and actual manifests both sum to **2329**, with no per-file mismatch.
- Self-tests: checker **47/47**, backlog **182/182**, features **18/18**, mutation harness **246/246**.

Repository unchanged.

VERDICT: NOT CONVERGED
