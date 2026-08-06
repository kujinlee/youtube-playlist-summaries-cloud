# Round 5 — cross-derivation of the fixes, run BEFORE writing any of them

Round 3's lesson was that fixes fail *as a set* — each written into its own section, none re-derived
against the others. Round 5 produced 7 Blocking and 11 High across three reviewers. Deriving them
against each other first found **five** conflicts, one of which makes two findings a single fix.

---

## C1 — B4's index and H4's dead lease are ONE fix, not two. Landing B4 alone makes things worse.

B4 says: add `unique (workspace_id, video_id, slot) where state = 'pending'`, or two writers both pay.
H4 says: nothing ever reads `lease_expires_at`; a writer that dies leaves `pending` forever.

Today a dead lease is a **soft** failure — the slot reads `busy`, nobody re-spends, nobody can
produce. Add B4's index without H4's reclaim and it becomes a **hard uniqueness violation on every
future attempt, forever**. The money guard would be perfect and the feature permanently dead.

**Resolution: one fix.** The index lands *with* a reclaim, and the reclaim is `delete` the expired row
then insert — not `update` — because the unique index is on the *existence* of a pending row, so the
expired one must stop existing before the next can be created.

The index cannot be `where state='pending' and lease_expires_at > now()`: `now()` is not immutable and
Postgres rejects it in an index predicate. The expiry check has to live in the RPC. **Verified by
executing it.**

## C2 — B1's "require non-null values" would break the corrections rung for every video with no corrections

B1 correctly says `card ?& array[…]` tests key **existence**, so `{"tldr":null,…}` passes. The
proposed fix — require all six values non-null — collides with rung 1:

`mdCorrectionsHash` is legitimately **null** when a video has no corrections, and `wv.corrections_hash`
is null too, so `null is not distinct from null` is TRUE and that is the *correct* answer. Requiring it
non-null makes rung 1 false for every generation of every uncorrected video — the common case — and
silently demotes the whole ranking to format-only.

**Resolution:** require non-null **values** for the five facts that always exist (`tldr`, `takeaways`,
`docVersion`, `mdGeneratedAt`, `processedAt`), and require `mdCorrectionsHash` to be **present as a
key** while permitting a null value. The all-null placeholder card still dies — on the other five.

This also kills the specific live hazard B1 found: `sync-run.ts:534-542`'s
`{docVersionMajor: 0, mdGeneratedAt: null, …}` "honest placeholder" can never become a generation.

## C3 — H2's two proposed fixes are independent, and both are needed

Codex would constrain the data (`check (kind <> 'summary' or source_generation_id is null)`); Claude
would constrain the query (exclude `slot='summary'` from the source-currency rung). They look like
alternatives and are not: the check stops a bad row being written, the rung change stops a bad row
already in the table (or arriving via `service_role`, which bypasses every policy) from making the two
views disagree. **Take both.** Neither implies the other, and they fail independently.

## C4 — M1's append-only trigger must permit exactly the two mutations the other fixes require

M1 observes that "APPEND-ONLY" is enforced by nothing — `grant update, delete to service_role` and no
trigger. But a blanket immutability trigger breaks two things the design needs:

| Mutation | Needed by | Must be |
|---|---|---|
| `update` a `pending` row → `recorded` | rule 19's record-first order | **permitted** |
| `delete` an expired `pending` row | C1's reclaim | **permitted** |
| `update` / `delete` a **recorded paid** row | nothing | **rejected** |

So the trigger is scoped to recorded paid rows, not to the table. Append-only is a claim about *paid
history*, never about in-flight reservations — and stating it as a table-wide property is what made it
look enforceable-by-nothing in the first place.

## C5 — H3's `body_collected` exemption for free renders is not a second bug, it is the first one's mirror

`not coalesce(g.body_collected, false)` is **always true** for a free render, because a free render has
no generation. So when a body is collected, every summary generation vanishes from `current` (H3's
measurement: 2 rows → 0) while its **PDF keeps serving** — a rendered copy of bytes that no longer
exist. Shape #4.

So the §8 rule cannot only be *"GC never collects the current generation"*. It must also be *"collecting
a body collects the renders derived from it"* — otherwise the fix for the summary half deepens the
render half by making the surviving PDF the only thing left.

---

## What this pass changed about the batch

- B4 and H4 merged into one fix and one prose section; landing B4 alone is now recorded as harmful.
- B1's fix is **weaker** than the reviewer proposed, deliberately, and the reason is written down.
- H2 takes both proposed fixes rather than choosing.
- M1's trigger is scoped by the two mutations C1 and rule 19 require.
- H3 grew a second half that neither reviewer stated, because it only appears when you ask what the
  first half does to the *other* rows.

Four of the five conflicts are between findings from **different** reviewers, which is the argument for
running the pass at all: no single reviewer could have seen them, because each saw only their own set.

---

## Round-5 findings NOT yet applied (recorded so they are not lost a fourth time)

§4.0's own lesson: *recording a finding and fixing one look identical in a review document.* These are
recorded as **open**, not as handled.

| # | Finding | Why deferred |
|---|---|---|
| M3 | A nested `relDir` key can enter the bucket via `sync-run.ts:263/:381` `putStaged`, which skips the single-segment assertion the serve path enforces (`assert-cloud-summary-md-key.ts:14-19`). §4.0 then classifies it *unknown → fail closed*, so a routine sync permanently reports "a migration that is not finished". | A code fix in `lib/`, not a spec fix. Belongs to the implementation slice |
| M4 | The content-addressed PDF cache (`pdf-render-version.ts:22` mints `pdfs/<base>.r<V>.<sha16>.pdf`, deliberately many per video) cannot be represented: §4.0 maps them all to one `slot='pdf:<kind>'`, which `video_artifacts_free_uq` caps at one row. | A real design question — does the render hash belong in the slot? — that should be decided, not patched |
| M6 | The `anon`/`authenticated` grant on the raw manifest is now backed by a policy, but it still points a maintainer at the *unfiltered* table (pending rows, superseded generations, detached digs) rather than at `current`. | Cosmetic given B2's policy; revisit when the serve path is written |
| C5 | **Collecting a body must collect the renders derived from it.** A free render has no generation, so `not coalesce(g.body_collected,false)` exempts it structurally: the PDF of a collected body keeps serving. H3's fix (GC may not collect the *current* generation) closes the summary half and leaves this one. | Needs a §8 rule and a sweeper change; no schema expression is obvious |
| L1 | `slot_kind` is a plain function used inside a CHECK: `create or replace` changes the constraint's meaning without revalidating rows, and it has no pinned `search_path`. | Low, but genuinely a foot-gun for a later migration |
| L4 | `lib/storage/supabase/consistency.ts:17-42` (`writeArtifact`) takes an arbitrary caller-supplied key with no shape validation. Zero production callers today. | Open hole in §4.0's totality claim; cheap to close in the implementation slice |

**M2 was NOT deferred — it dissolved.** §4.0 and §6.2 gave different slot formats for a detached dig
(`dig:<id>` vs `dig:<id>@<generationId>`). Cross-deriving the append-only trigger against §6.2 showed
the suffix was an address rewrite, and that append-only removes the need for it entirely. See §6.2.
