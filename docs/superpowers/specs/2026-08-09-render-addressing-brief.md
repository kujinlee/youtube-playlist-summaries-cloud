# Render addressing — design brief (NOT a design)

> **Anchor:** `stable-blob-addressing` — **ADR:** 0006, 0007
> **Goal:** Render addressing, split out of the addressing design on 2026-08-09 after two proposals were refuted in two rounds. A brief, not a design.

**Status: awaiting Phase 1 brainstorming.** Split out of ADR-0007 by user decision, 2026-08-09, after
two proposed designs were refuted in two consecutive adversarial rounds.

This document deliberately **proposes nothing**. It records the problem, what has been ruled out and
why, and the constraints any design must satisfy — so the design pass starts from evidence instead of
a blank page, and so nobody re-proposes something already measured false.

---

## Why this is its own slice

**The two failed attempts have a common cause that is not "the problem is hard".** Neither ever got a
design pass. Round 13's was written as one paragraph inside a revision answering ten other findings;
round 14's was written as one paragraph inside the fix for round 13's. Both were refuted on first read
by a reviewer who traced the actual write path.

The project's stop condition — *two consecutive rounds whose findings were caused by the previous
round's fixes ⇒ escalate from fix to redesign* — is therefore met for this sub-problem in its own
right. A third paragraph is exactly what that rule exists to prevent.

**It is separable from ADR-0007.** The reservation deletion is about **coordination** (who may write a
slot); render addressing is about **identity** (what an address means, and whether it may be
overwritten). They collide on one column, not on one question.

---

## The problem

A **render** is a derived output — the HTML page or the PDF built from paid content (summary, model,
digs). Renders are **free** (no Gemini call) and **reproducible** (delete one, rebuild it).

Today a render is marked by `generation_id IS NULL`, and that single NULL carries **two independent
meanings**:

- *"this artifact is free"* — a **money** property;
- *"this address may be overwritten"* — an **addressing** property.

`[VERIFIED: docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema/04_artifacts.sql:94-95]`
defines free-ness as the *absence* of a generation id:

```sql
constraint art_paid_has_generation check (
  (kind in ('summary','model','dig','digDeeper')) = (generation_id is not null))
```

**Five findings across rounds 8–12 came out of that one conflation** — the same shape as nullable
`corrections_hash` ("no corrections" vs "never computed") and absent-vs-failed-to-read.

**Current blast radius, stated honestly so the slice is not over-sold.** Most of the harm this
conflation did lived in the reservation code ADR-0007 deletes. What remains is that renders are
overwritable — which is how they already work in production, and they are free and reproducible, so
nothing is at risk but coherence. **This is a correctness-of-model problem, not a money or data-loss
problem.** It should be sequenced accordingly.

---

## RULED OUT — do not re-propose

### 1. Identity assembled by enumerating version constants *(round 13, refuted round 13 B2/H2)*

Proposed: `hash(source_generation_ids, GENERATOR_VERSION)`.

There are **three** independent version constants, and a PDF's bytes depend on all of them, plus a
pinned browser:

| Constant | Evidence | Governs |
|---|---|---|
| `GENERATOR_VERSION` | `[VERIFIED: lib/html-doc/constants.ts:5]` | magazine model shape/prompt — **not** the renderer |
| `PDF_RENDER_VERSION` | `[VERIFIED: lib/pdf/pdf-render-version.ts:10]` | PDF settings **and the pinned Chromium** |
| `DIG_GENERATOR_VERSION` | `[VERIFIED: lib/dig/generate.ts:15]` | dig bodies — decides what a dig-deeper render contains |

`[VERIFIED: lib/pdf/pdf-render-version.ts:5-9]` states the failure mode itself: those bumps *"alter
PDF bytes WITHOUT changing the HTML"*, a missed bump **cannot be detected**, and bumping is *"a
review-time checklist item"*. An identity is only as complete as its enumeration, and this enumeration
has already been got wrong once.

### 2. Identity that lives only in a column while the key is unchanged *(round 14, refuted round 14 B4)*

Proposed: `render_id = sha256(rendered bytes)` as a column, key unchanged.

Nothing binds `render_id` to `blob_key`. `art_key_names_generation` is **vacuously true** when
`generation_id is null`
`[VERIFIED: …/schema/04_artifacts.sql:159-160]`, and `art_key_names_workspace` constrains segments
1–3 only `[VERIFIED: …/schema/04_artifacts.sql:154-157]`. So uniqueness on
`(workspace_id, video_id, slot, render_id)` permits **N rows on one key**, renders are written with
`put` (an overwrite), and N−1 rows point at bytes that no longer exist.

**The precise error, worth keeping because it is subtle:** a render was not *addressed by* the hash —
it was *identified* by it in a column while remaining *addressed* by an unchanged key. The proposal
silently swapped **address** for **identity**. For an append-only log the result is strictly worse
than the status quo, where `video_artifacts_free_uq` at least keeps row↔blob **1:1**
`[VERIFIED: …/schema/04_artifacts.sql:164-165]`.

### 3. A `<gen>/`-shaped render key *(refuted round 13 B2)*

§8 requires the paid/free split to be derivable **from the key alone**
`[VERIFIED: docs/superpowers/specs/2026-08-03-stable-blob-addressing-design.md:2096-2100]`:

> *"An orphan has no manifest entry — that is what makes it an orphan — so the sweeper cannot ask the
> manifest whether a candidate was paid. It has to read the key. … any future key that does not
> announce its own paid-ness is either **uncollectable or unsafe to collect**."*

The discriminator is path segment 4: a generation id, or the literal `renders`
`[VERIFIED: …-design.md:275-282]`. A generation-shaped render key erases it.

---

## CONSTRAINTS any design must satisfy

1. **Two keys, not one.** `[VERIFIED: app/api/pdf/[id]/route.ts:54]` computes the cache key from the
   HTML and `:60` probes the blob store **before** rendering. **An identity that cannot be computed
   until the bytes exist cannot be the cache key of a path whose entire purpose is to avoid producing
   the bytes.** Any scheme needs an **input-derived probe key** and an **output-derived identity**,
   and must say which is `blob_key` and which is `render_id`.
2. **§8's key-alone rule** (above) — the sweeper must classify paid vs free from the key.
3. **Row↔blob coherence.** Whatever uniqueness is chosen, a row must not claim bytes that another row
   overwrote. This is what attempt 2 broke.
4. **Content hashes are permitted here and only here.**
   `[VERIFIED: …-design.md:893]`: *"A generation id must be chosen before its content, which rules out
   content-hash ids for anything on a spend path; §4.1 already recommends UUIDs there and content
   hashes only for free re-renders."* Renders are the free side.
5. **The paid/free partition is already sound — do not redesign it.** `artifact_kind` is exactly the
   five kinds `[VERIFIED: …/schema/03_generations.sql:264]` and `art_paid_has_generation` puts exactly
   four in the paid set, so *"exactly one of `generation_id` / `render_id` is non-null"* holds for
   every kind including `model` and `digDeeper`. **It is the address that failed, not the partition.**

---

## Facts that surprised both previous attempts

- **`renders/` does not exist in the code.** `grep -rn "renders/" --include=*.ts` returns **zero
  hits**. It exists in the spec's key table and in assertion fixtures only. Production keys are
  `pdfs/{base}.r{V}.{hash}.pdf` `[VERIFIED: lib/pdf/pdf-render-version.ts:22]` and
  `models/{base}.json` `[VERIFIED: lib/html-doc/model-store.ts:31]`. Round 13 called the prefix
  *"existing"*, which was true of the spec and false of the code.
- **Consequently §4.0's classifier classifies nothing live today** — both production key shapes fall
  to *"Anything else → unknown → fail closed"* `[VERIFIED: …-design.md:283]`. The classifier's
  premises hold only **after** ADR-0006's key relocation. Any design here must say whether it targets
  the pre- or post-migration world.
- **No sweeper or classifier is implemented anywhere.** §4.0 is prose, and `video_artifacts` /
  `video_generations` appear in no migration (latest is `0023`). So a key-shape decision costs a spec
  edit today and a migration later — **it is cheap now and expensive after the schema ships.**

---

## Open questions for the design pass

1. What is the probe key, and does it keep the hand-maintained `PDF_RENDER_VERSION` segment (accepting
   a known missed-bump hole) or replace it with something derived?
2. Where does the output identity live — in the key below the `renders/` segment (preserving §8's
   segment-4 discriminator), in a column with a key-binding CHECK, or both?
3. Does a render need append-only semantics at all, or is *"overwritable but honestly labelled"* the
   right model? **Attempt 2 assumed append-only without arguing for it.** Renders are free and
   reproducible; the case for immutability is not self-evident and should be made or dropped
   explicitly.
4. Multi-source provenance — a PDF derived from summary + digs. ADR-0007 settles this as a
   `video_artifact_sources` join table `on delete cascade`; confirm that survives whatever addressing
   is chosen.
5. Does `video_artifacts_free_uq` get replaced, or kept? ADR-0007 currently **keeps** it, because with
   addressing withdrawn there is no successor.

---

## Sequencing

**Not urgent, and the brief says so on purpose.** Renders are free and reproducible; the live harm is
coherence, not money or data loss. **TRIGGER:** before the blob-addressing schema ships a migration —
because a key shape is cheap to change while `video_artifacts` exists only in a spec, and expensive
once rows exist. That is the same "cheap now, unrecoverable later" argument the spec makes for
`detached_at`.

**Blocked by:** nothing. **Blocks:** deleting `video_artifacts_free_uq`, and closing the
`check-sentinel-meanings.py` entry for `video_artifacts.generation_id`.
