# Stable blob addressing — round 3, coordinator's own pass (JOB A)

**Artifact:** `docs/superpowers/specs/2026-08-03-stable-blob-addressing-design.md` @ `82a1a0e`
**Date:** 2026-08-06. Written before either reviewer reported.
**Scope:** JOB A only — attacking the 12 chosen invariants, asking of each *"is what it buys still
worth what it forbids?"* rather than *"is it true?"*

---

## BLOCKING

### A1 — Rule 13's ordering silently discards the reconcile hierarchy this project already settled

**Invariant attacked:** *13 — `current` is derived from the generation set*, ordered by
`(created_at, generation_id)`.

**The defect is the ORDER, not the derivation.** Deriving `current` is sound and dissolved three
findings. But I specified the ordering as flat recency, and this project decided years-of-review ago
that **recency is not the decider**.

`lib/cloud-sync/reconcile-class-a.ts:41-50` — merged, reviewed, in production:

```
// format (never downgrade)
if (local.docVersionMajor !== cloud.docVersionMajor) { … }
// same major, different mdHash → recency-tiebreak
const winnerIsLocal = newer(local.mdGeneratedAt, cloud.mdGeneratedAt);
```

and the Stage 3 spec states it as a principle, not an implementation detail:
*"Class A — generated … reconciled by **format**, not recency."*

The established hierarchy is **corrections-currency → format (never downgrade) → recency as a tiebreak
within one major**. Rule 13 keeps only the last one.

**Failure scenario.** `CURRENT_DOC_VERSION` advances to 4.0. A video is regenerated at 4.0 (generation
*def*, 10:00). A retry of an older queued job, or a replica still pinned to 3.3, records generation
*ghi* at 10:05 — same slot, complete card, corrections current, therefore **eligible**. Rule 13 makes
*ghi* current. **The video silently downgrades a format version**, which the code path being replaced
explicitly refuses to allow. §8 then starts a 90-day clock on the 4.0 generation.

**Second failure, and it is why the hierarchy exists.** `created_at` is not comparable across
independent replicas. A local machine with a fast clock wins every tiebreak, permanently. Today's code
avoids this by making the *format* the decider and using recency only inside one major, where the two
bodies are equivalent in kind and picking wrongly is cheap.

**Change.** Rule 13's ordering must be the existing hierarchy, not flat recency:
`(corrections_current desc, doc_version_major desc, created_at desc, generation_id desc)`.
Then "newest eligible" is safe, because the dimensions that must never regress are ranked above the one
that is only a tiebreak. **Cite `reconcile-class-a.ts` in §5.1.1** so the next reader does not
re-derive flat recency from first principles as I did.

---

## HIGH

### A2 — Rule 15 leaks assets: "explicit delete only" is unreachable for the last-playlist case

**Invariant attacked:** *15 — assets are sources, outside the manifest, never age-swept, removed only
by an explicit delete of the video or playlist that owns them.*

The rule is right — the bytes are unrecreatable (ADR-0005), so age-sweeping them is wrong. But
**"removed by explicit delete" is not actually reachable for every asset**, so the rule guarantees a
leak rather than a bound.

**Failure scenario.** Video V is in playlists P1 and P2 of one workspace. Assets live at
`<ws>/videos/V/assets/…`, keyed on `videoId` and **shared by both** (§4 puts them outside generations,
and §5.0.1 makes the video a workspace-level entity). Delete P1 — V survives in P2, so assets must
stay. Delete P2 — the last `videos` row for V is gone, `workspace_videos` can be unreferenced, the
artifact manifest rows are removed transactionally (§8) — **and nothing deletes `assets/V/`**, because
assets deliberately have no manifest row for the unreference RPC to walk.

They are now unreachable by every path: no manifest row (rule 15), never age-swept (rule 15), and no
playlist or video delete will ever fire for them again.

**Change.** The unreference RPC must delete the `assets/<videoId>/` prefix when it removes the **last**
`workspace_videos` row for that video — the one place refcounting is genuinely required, and the one
the current design skips precisely because assets are outside the manifest. State it in §8 beside the
rule, or rule 15 reads as a retention policy while behaving as a leak.

---

## MEDIUM

### A3 — Rule 17 is unverifiable for five of the nine artifact kinds

**Invariant attacked:** *17 — paid/free (and artifact/source) must be derivable from the key alone.*

§4 defines **four** key shapes. §3's inventory lists **nine** kinds. HTML, cloud PDF, local PDF,
dig-deeper companion and `_staging` have no shape under the new addressing, so the classification rule
that the GC sweeper depends on **cannot be checked** for them — and the sweeper is what decides whether
paid bytes live or die.

This is Claude's round-1 M5, which I never fixed and which round 2 did not re-raise. Recording it so it
is not lost a third time.

**Change.** Extend §4's template to all nine kinds, then re-derive rule 17 against the full set.

---

## Not a defect — a benefit rule 13 has that the spec does not claim

**Derived `current` makes sync convergent by construction, and §5.3 should say so.** If `current` is a
function of the generation set, then two replicas that exchange generation sets compute the *same*
answer — set union is commutative, associative and idempotent, so no tiebreak protocol, no
last-writer-wins, no ordering negotiation is needed between replicas at all. §5.3 still describes sync
as "comparing two manifests and producing one", which is the old pointer-reconciliation framing.

**This only holds once A1 is fixed.** Flat recency across replicas is not a deterministic function of
the set — it depends on clocks. The hierarchy in A1 *is* deterministic: `corrections_current`,
`doc_version_major` and `generation_id` are all replica-independent facts. So A1 is not merely a
correctness fix; it is what makes this property true.
