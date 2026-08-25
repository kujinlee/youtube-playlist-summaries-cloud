# Anchor registry

**An anchor is the name of a goal that does not change when the mechanism does.** Every living spec
and plan declares which one it belongs to, and the index over documents is derived from those
declarations rather than maintained by hand. The reasoning, and the three alternatives that were
rejected, are in [ADR-0010](adr/0010-documents-declare-their-anchor.md).

**This file holds NAMES, not STATE.** That is the whole reason it is safe to keep centrally — a name,
once allocated, does not change, so nothing here can silently go stale. Do **not** add status,
progress, or "what's next" columns: for state, follow the anchor to `docs/roadmap-to-launch.md` and
`docs/backlog.md`. A central file that holds state drifts, and this project has measured that twice.

**Rendered** by `scripts/gen-goals-page.py` as the standing page at
**http://127.0.0.1:7391/goals** — one card per goal, everything on it derived from this file,
the headers, `docs/adr/`, the milestone spines and `git log`. Rebuilt by
`.claude/hooks/regen-goals-page.sh` whenever any of those changes.

Enforced by `scripts/check-anchors.py` (`--self-test`). An anchor that no document claims is a
failure, not a placeholder — allocate the name when the first document needs it.

## The registry

| Anchor | ADR(s) | Goal |
|---|---|---|
| `cloud-publishing` | 0001, 0005 | Summaries are produced and published by a hosted service, not only by a local vault. |
| `cloud-sync` | 0002 | The same video reconciles coherently between the local vault and the cloud replica. |
| `share-and-download` | 0003 | A summary can be read by someone without an account, and taken away as a file. |
| `serve-path-bounding` | — | The serve path's work is bounded, and its lease outlives the work it protects. |
| `serve-money-guard` | 0008 | Serving a summary cannot spend money twice, and the protection is enforced rather than accidental. |
| `stable-blob-addressing` | 0006, 0007 | A blob's address stops moving when a title or a serial number changes. |
| `cloud-blob-key-encoding` | 0009 | A video titled in any language can be stored and served from cloud storage. |
| `corrections-in-cloud` | — | A cloud user corrects a summary and gets the same result a local user would. |
| `prod-smoke` | — | Every deploy is proven by machine to serve the real application, against the deployed URL. |

## Declaring the anchor in a document

Two lines, inside the first 10, immediately under the `# Title`:

```md
> **Anchor:** `stable-blob-addressing` — **ADR:** 0006, 0007
> **Goal:** A blob's address stops moving when a title or a serial number changes.
```

Where no decision has been recorded yet, write `**ADR:** none`. The `Goal:` line is written **from the
document's own opening**, never from memory — the derived index renders it as fact, and a wrong goal
line is a claim rather than an omission.

## Scope — which documents must carry one

`scripts/check-anchors.py` requires the header on any spec or plan dated **2026-08-25 or later**, and
validates it wherever it appears. The **22 living documents** backfilled on 2026-08-24 — those
referenced by the roadmap, backlog, an ADR or the process spine, plus those edited in the preceding
30 days — carry one already, and a floor in the checker stops that set being silently emptied.

The ~140 older specs and plans, and all 716 files in `docs/reviews/`, deliberately carry **no**
header. They are point-in-time artifacts; nobody navigates *to* a goal through them. They are reached
through the document that cites them.
