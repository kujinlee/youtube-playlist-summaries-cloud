# Plan review round 1 — Codex — cloud blob key encoding (backlog #36)

Subject: `docs/superpowers/plans/2026-08-15-cloud-blob-key-encoding.md` (15 tasks, 77 steps).
Model: gpt-5.5. Dispatched via `scripts/codex-review.py --prompt-file`.

**Blocking — T1 — property test cannot pass**

Evidence in plan [docs/superpowers/plans/2026-08-15-cloud-blob-key-encoding.md](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-08-15-cloud-blob-key-encoding.md:174):

```ts
expect(SAFE.test(out) || out === seg).toBe(true);
```

and the produced encoder:

```ts
export const SAFE = /^[A-Za-z0-9._-]+$/;
return `${head}=h${digest.slice(0, 22)}${ext}`;
```

Failure scenario: for any non-ASCII swept code point, `encodeSegment(seg)` returns a hash-branch value containing `=h`; `SAFE.test(out)` is false because `=` is excluded, and `out === seg` is false. T1 step 5 goes red after the implementation is correct.

Proposed fix: test the physical alphabet separately, e.g. `expect(out).toMatch(/^[A-Za-z0-9._=-]+$/)` and keep `expect(out.length).toBeLessThanOrEqual(65)`.

**Blocking — T6 — implementation snippet does not type-check against `StagedRef`**

Plan evidence [docs/superpowers/plans/2026-08-15-cloud-blob-key-encoding.md](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-08-15-cloud-blob-key-encoding.md:651):

```ts
async promoteIfAbsent(ref: StagedRef): Promise<void> {
  const final = this.abs(ref.principal, ref.key);
```

Code evidence [lib/storage/blob-store.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/storage/blob-store.ts:5):

```ts
export interface StagedRef { principal: Principal; tempKey: string; finalKey: string; }
```

and existing adapter evidence [lib/storage/local/local-blob-store.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/storage/local/local-blob-store.ts:58):

```ts
const from = this.abs(ref.principal, ref.tempKey); const to = this.abs(ref.principal, ref.finalKey);
```

Failure scenario: an engineer copies T6 literally and `tsc` fails with `Property 'key' does not exist on type 'StagedRef'`.

Proposed fix: change the plan snippet to `this.abs(ref.principal, ref.finalKey)`.

**Blocking — T13 — Class-A ownership guard required by §3.6.2 has no executable implementation step**

Plan evidence [docs/superpowers/plans/2026-08-15-cloud-blob-key-encoding.md](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-08-15-cloud-blob-key-encoding.md:1216):

```md
**Behaviors:** 18, 18b, 18c, 18c2, 18e, 18g, 18h, 18i, 18k, 19, 20.
```

but its protocol step only says [same file](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-08-15-cloud-blob-key-encoding.md:1261):

```md
`putStaged` → **verify the read-back hash** → `promoteIfAbsent` → read back and classify...
```

Spec evidence [docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:1427):

```ts
if (!canonicallyEqualName(loserVideo.summaryMd, key)) {
  const dest = await loser.blob.tryGet(loser.p, key);
  if (dest.ok || dest.reason === 'unreadable') throw …;
}
await loser.blob.put(loser.p, key, staged, 'text/markdown');
```

Current code still unconditionally overwrites [lib/cloud-sync/sync-run.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/sync-run.ts:381):

```ts
const ref = await loser.blob.putStaged(loser.p, key, Buffer.from(body, 'utf8'), 'text/markdown');
...
await loser.blob.put(loser.p, key, staged, 'text/markdown');
```

Failure scenario: a Class-A transfer writes the winner body over a loser address the loser row does not claim. That can destroy a paid artifact. The task names behaviors 18g/18h, but a literal implementer gets no signature change, no caller change, and no loser-record guard.

Proposed fix: add explicit T13 steps and tests for R3: change `transferClassA` to accept `loserVideo`, update both call sites, use `canonicallyEqualName(loserVideo.summaryMd, key)`, and probe/refuse occupied or unreadable destination only on the non-owned branch.

**Blocking — T13 — `check-encoder-gate-sql.py` is not executable as written**

Plan evidence [docs/superpowers/plans/2026-08-15-cloud-blob-key-encoding.md](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-08-15-cloud-blob-key-encoding.md:1265):

```python
#!/usr/bin/env python3
"""Behavior 20 — the section-4 gate's SQL predicate DERIVES from the encoder module.
...
"""
```

Self-review evidence [same file](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-08-15-cloud-blob-key-encoding.md:1357):

```md
T13's `check-encoder-gate-sql.py` gives the docstring and the required behavior but not the body
```

Failure scenario: an engineer following the plan creates a file containing only a docstring; `python3 scripts/check-encoder-gate-sql.py --self-test` exits 0 unless they invent the missing script. That leaves behavior 20 untested.

Proposed fix: include the actual script body in T13, including `--self-test`, regex extraction from `encode-segment.ts`, SQL predicate extraction, and non-zero exits when either side cannot be found or differs.

**Medium — T9 — metadata seam predicate is stricter than the spec’s advertised-state rule**

Spec evidence [docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:778):

```md
refuse any patch that sets `summaryMd` or `artifacts.summaryMd.status =
'promoted'` to a key failing `isServableSummaryKey`
```

Plan evidence [docs/superpowers/plans/2026-08-15-cloud-blob-key-encoding.md](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-08-15-cloud-blob-key-encoding.md:931):

```ts
const advertised = [patch.summaryMd, patch.artifacts?.summaryMd?.key]
  .filter((k): k is string => typeof k === 'string');
for (const key of advertised) {
  if (!isServableSummaryKey(key)) {
```

Failure scenario: a patch carrying `artifacts.summaryMd.key = 'nested/evil.md'` with non-promoted status is refused even though the spec’s seam rule is about `summaryMd` or `status:'promoted'` advertisement. That can reject non-advertising repair/pending states the spec did not forbid.

Proposed fix: guard top-level `summaryMd` always; guard `artifacts.summaryMd.key` only when `artifacts.summaryMd.status === 'promoted'`, unless the spec is explicitly amended.

**Medium — T13 — ratchet command masks failure exit codes**

Plan evidence [docs/superpowers/plans/2026-08-15-cloud-blob-key-encoding.md](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-08-15-cloud-blob-key-encoding.md:1281):

```bash
for c in check-docs check-roadmap-consistency check-test-counts check-producer-enumeration; do
  python3 scripts/$c.py || echo "RED: $c"; done
```

Failure scenario: a ratchet fails, prints `RED: ...`, and the loop still exits 0 because `echo` succeeds. A literal engineer can commit a red ratchet set.

Proposed fix: use fail-fast or accumulate status:

```bash
for c in check-docs check-roadmap-consistency check-test-counts check-producer-enumeration; do
  python3 scripts/$c.py
done
```

Checked T12 specifics: the `origin` predicate matches the real ternary. Current code uses truthiness at [lib/cloud-sync/reconcile-serial.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/reconcile-serial.ts:152), and the plan uses the same predicate at plan line 1168. Behavior 26d3 is constructible: `999_` + 124 ASCII chars + `.md` is 131 code points and servable; `applySerial(..., 1000)` widens the prefix by one and makes 132.

NOT CONVERGED
