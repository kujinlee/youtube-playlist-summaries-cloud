<!-- codex-review: model=gpt-5 -->

# Round 10 design review — §3.6 vault write protocol

Subject: `docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md` v10, §3.6 only.
Branch: `fix/cloud-blob-key-encoding`.

This is a design review, not a fifth defect hunt. I read rounds 6-9 from both reviewers, the
2026-08-09 blob-addressing retrospective, the v10 §3.6 text, and the current storage/sync code around
`BlobStore`, `LocalFsBlobStore`, `SupabaseBlobStore`, `copyAdditiveVideo`, and `transferClassA`.

APFS measurement repeated in `/tmp` and cleaned up: a file created as `003_café.md` is readable via the
NFD path `003_café.md`; `writeFileSync(NFD, { flag: 'wx' })` returns `EEXIST`; and `readdirSync`
returns the original NFC byte sequence. This matches round 9: path resolution and exclusive create see
only the alias class; directory enumeration reveals the stored name.

## 1. Name the coordination problem

This is an **alias-aware receiver-namespace admission problem**, not a generic write guard. The sync
protocol carries a logical blob key, but the receiving vault namespace may decide that two different
logical keys occupy one physical address. The missing fact is not "does anything exist at this path?"
and not "may I overwrite?"; it is "which logical name, byte-for-byte, currently owns this receiver
namespace slot?" Additive create, Class-A overwrite, APFS identity, staging verification, and Supabase
absence ambiguity are all consequences of that one mismatch between logical-key addressing and
backend namespace equivalence.

## 2. Recommended shape

Keep the receiver blob store as the collision authority, but do not let sync reach through the seam to
`fs.readdirSync`. The seam should grow an explicit namespace-identity primitive owned by `BlobStore`,
because only the receiver adapter knows its path equivalence relation, whether stored names are
preserved, and which create/promote operation is atomic for that backend.

The primitive I would add is a lookup, not a raw directory listing:

```ts
type BlobNameOccupancy =
  | { ok: true; state: 'absent'; absenceProven: boolean }
  | { ok: true; state: 'present'; storedKey: string; exact: boolean }
  | { ok: false; reason: 'unreadable'; cause: unknown };

lookupStoredKey(p: Principal, key: string): Promise<BlobNameOccupancy>;
```

Semantics:

- `present.exact === true` means the receiver namespace slot resolves to a stored logical key
  byte-equal to `key`.
- `present.exact === false` means the slot resolves, but the stored key differs byte-for-byte: this is
  an aliasing collision and must be treated as a different logical key.
- `absent.absenceProven` carries the existing `provesAbsence` distinction forward instead of hiding it.
- `unreadable` remains fail-closed.

Adapter behavior:

- `LocalFsBlobStore`: resolve the path, enumerate the containing directory, and return the actual
  stored entry name byte-for-byte. For the summary-md case this is the single filename component; if
  generalized to nested keys, the implementation must compare path segments as stored, not normalized
  strings. APFS makes this possible because it is normalization-preserving.
- `SupabaseBlobStore`: there is no aliasing, so a readable hit returns
  `{ state: 'present', storedKey: key, exact: true }`. A 404-shaped miss returns
  `{ state: 'absent', absenceProven: false }`, because this backend still cannot distinguish genuine
  absence from denial under the existing contract. Non-404/transport failures return `unreadable`.
- `InMemoryBlobStore`: default exact string-key semantics, with optional test support for an aliasing
  equivalence relation so §3.6 behavior tests do not require APFS for every assertion.

Then the writers use that primitive according to their intent:

- `copyAdditiveVideo`: this is namespace admission for a row that does not yet exist locally. It must
  refuse any present receiver slot, exact or alias, and it should preserve the existing
  `putStaged -> verify -> promote` durability protocol. The final promote on local must be no-clobber:
  `link(temp, final) + unlink(temp)` is the right shape because it keeps the verified staged bytes and
  closes the race where an alias appears between preflight and final create.
- `transferClassA` / `copyToLocal`: this is reconciliation of an existing receiver row and is required
  to overwrite that row's divergent blob. It should call `lookupStoredKey` before the overwrite:
  absent is acceptable if the loser blob is missing, exact is the intended overwrite, alias is a
  refusal because it would overwrite a different logical key. The final write remains a deliberate
  `put` overwrite after staging verification. The residual window between identity lookup and overwrite
  cannot be closed with `wx` because the destination is occupied by design; §3.6 should state that
  limitation honestly.

This does not force a change to §3.1-§3.5. It makes §3.6 the local/vault-specific receiver namespace
rule that becomes newly necessary once cloud can carry non-ASCII keys into the vault.

## 3. Cost

Interface cost:

- `BlobStore` gains one required method or a required capability object. I prefer required: optional
  would recreate the current "caller guesses what the backend can prove" failure mode.
- Existing adapters affected: local, Supabase, in-memory test store, and any test fakes that currently
  implement only part of `BlobStore`.
- The method needs contract documentation as strong as `tryGet`, because callers must not collapse
  alias, absent, and unreadable into one boolean.

Implementation cost:

- Local needs a careful stored-name lookup. For a single summary filename, `readdir(dirname)` plus
  byte-for-byte comparison is enough; for general nested keys, the implementation should walk segment
  by segment or otherwise prove it returns the stored spelling of the resolved path.
- Local additive promote needs a no-clobber form that preserves staging verification. `link + unlink`
  is the measured candidate; `rename` is the clobbering operation to retire for this path.
- Class-A needs an explicit pre-overwrite identity check and an accepted residual race note.

Test cost:

- Real APFS tests for NFC/NFD aliasing: exact stored name writes, different stored name aliases,
  `link` failing with `EEXIST`, and `rename`/`put` clobber risk.
- Contract tests for Supabase returning exact-present and unproven-absent without claiming alias
  detection it does not need.
- Sync behavior tests for additive refusing alias occupancy without dropping staged verification, and
  Class-A overwriting exact occupancy while refusing alias occupancy.

What it makes impossible:

- Sync code cannot treat `tryGet.ok` or `EEXIST` as a name-identity credential.
- `LocalFsBlobStore.promote` can no longer have one undifferentiated "rename overwrites" meaning for
  all local callers if additive promotion becomes no-clobber. Either `promote` grows mode/intent, or a
  new `promoteExclusive`/`promoteIfAbsent` operation is added.
- A backend that cannot report stored-name identity cannot safely be a receiver for alias-sensitive
  overwrite decisions unless it can prove no aliasing exists.

## 4. Strongest argument against this recommendation

This makes `BlobStore` less pure. The original interface is a logical-key object store; stored-name
identity is a filesystem-shaped concern, and adding it to every adapter could be read as letting APFS
leak into the abstraction. A receiver-side disambiguating filename would avoid asking object storage
to expose identity at all: on collision, local could choose a readable suffixed vault name and update
the receiver index to that name. That might be a better user-facing outcome than refusing a sync.

I still would not choose that for this slice. It changes the protocol from "replicate the winning
summary key" to "the receiver may rename the artifact", which then has to interact with base
reconciliation, companion model/dig keys, serial semantics, and local-authoritative cloud repair. That
is a larger naming design than §3.6, and it risks disturbing §3.1-§3.5 after they have converged. The
smaller honest seam is to say the receiver store owns namespace identity and expose exactly that fact.

## 5. Verdict on v10 `readdir` + `link`/`unlink`

Keep the v10 shape, with one adjustment: keep `readdir` and `link`/`unlink` as the **LocalFsBlobStore
implementation** of named `BlobStore` capabilities, not as sync-run special cases. The measured
primitive is right. The abstraction boundary should be raised just enough that sync asks the receiver
store, "who owns this namespace slot?" and "promote this staged blob without clobbering", without
knowing that APFS answers the first question through `readdir`.

So my verdict is: **ship the `readdir` + `link`/`unlink` protocol, but do not ship it as a reach-through
from sync into local filesystem mechanics.** Make namespace identity a first-class storage capability,
return exact-present for Supabase, return unproven-absent for Supabase misses, and keep Class-A's
residual overwrite window explicit rather than pretending the no-clobber primitive covers it.
