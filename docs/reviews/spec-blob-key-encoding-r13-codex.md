# Round 13 adversarial review — cloud blob key encoding v15

Subject: `docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md` in the working tree, v15.

## Findings

### M1 — `promoteIfAbsent` is specified as `Promise<void>` but still required to return/resolve `'already-exists'`

**Severity:** Medium

**Evidence:**

`docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:649`

```ts
promoteIfAbsent(ref): Promise<void>        // RESOLVES when the final exists; never throws EEXIST
```

`docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:652-655`

```md
> **Round-12 M1 — v14 typed this `'created' | 'already-exists'` and no caller in this spec consumes
> it.** R2 branches entirely on the `tryGet` read-back. The load-bearing property is
> **resolves-rather-than-throws**; a discriminant nobody reads is decoration that invites an
> implementer to trust the label instead of the read. Either give it a consumer or drop it — dropped.
```

`docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:657-660`

```md
**It RESOLVES when the final object exists — it does not throw** (round-11 H1). `linkSync` *does*
throw `EEXIST` (measured), so the adapter must catch it, leave the occupant untouched, remove the
staging temp and `rmdir` its `_staging/<uuid>/`, and return `'already-exists'`. Without that sentence
```

`docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:1075`

```md
| 18d2 | **`promoteIfAbsent` RESOLVES `'already-exists'` rather than throwing**, and removes the staging temp **and** its `_staging/<uuid>/` directory (round-11 H1) | contract |
```

I also checked TypeScript directly:

```ts
async function f(): Promise<void> {
  return 'already-exists';
}
```

`tsc --strict --lib esnext` reports:

```text
Type 'string' is not assignable to type 'void'.
```

**Concrete failure scenario:** the implementer follows the signature and silently returns on `EEXIST`; behavior 18d2 still expects the observable value `'already-exists'` and the contract test is unwriteable. Or the implementer follows line 659 and returns `'already-exists'`; the implementation fails TypeScript against the specified `Promise<void>` contract. This is not a paid-artifact loss by itself, but it makes the new seam contract internally unsatisfiable.

**Proposed fix:** keep v15's decision to drop the discriminant and remove the stale value everywhere:

```md
...remove the staging temp and `rmdir` its `_staging/<uuid>/`, and resolve.
```

Change behavior 18d2 to:

```md
`promoteIfAbsent` resolves rather than throwing on an already-existing final...
```

Leave the mutation as "Make `promoteIfAbsent` throw on EEXIST".

**Classification:** mechanism. Two requirements contradict: `Promise<void>` and required `'already-exists'` result.

**Caused by v15's own fixes:** yes. v15's own Round-12 M1 repair drops the discriminant but does not remove all of its remaining required observations.

### M2 — behavior 18f requires changing `promote`, contradicting behavior 18d4 and R1

**Severity:** Medium

**Evidence:**

`docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:646`

```md
**R1 — a NEW primitive, `promoteIfAbsent`. `promote` itself is not touched.**
```

`docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:743-744`

```md
> **Not attributable to this change:** the orphaned `_staging/<uuid>/` directory. `renameSync` leaves
> it too (measured). Worth fixing here; not caused here.
```

`docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:1077`

```md
| 18d4 | `promote` is **unchanged** — its existing callers' behaviour is byte-identical before and after this slice | contract |
```

`docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:1080`

```md
| 18f | `promote` leaves no orphaned `_staging/<uuid>/` **directory** behind (`unlink` removes only the file) | unit |
```

Current local `promote` does not remove the staging directory:

`lib/storage/local/local-blob-store.ts:58-62`

```ts
  async promote(ref: StagedRef): Promise<void> {
    const from = this.abs(ref.principal, ref.tempKey); const to = this.abs(ref.principal, ref.finalKey);
    if (!fs.existsSync(from) && fs.existsSync(to)) return;   // idempotent: already promoted
    fs.mkdirSync(path.dirname(to), { recursive: true }); fs.renameSync(from, to);
  }
```

**Concrete failure scenario:** if the implementation keeps `promote` byte-identical, behavior 18d4 passes and behavior 18f fails. If it changes `promote` to remove `_staging/<uuid>/`, behavior 18f passes and behavior 18d4 fails. The intended cleanup belongs to `promoteIfAbsent` in R1, not to the unchanged primitive.

**Proposed fix:** change behavior 18f to name `promoteIfAbsent`, or explicitly split this into a separate out-of-scope cleanup for `promote` and remove it from this slice's behavior table. The narrow fix is:

```md
| 18f | `promoteIfAbsent` leaves no orphaned `_staging/<uuid>/` directory behind ... |
```

**Classification:** mechanism. The behavior table contains mutually exclusive requirements for the same primitive.

**Caused by v15's own fixes:** no. This is a stale §3.6 behavior-table contradiction retained in v15; it is not introduced by the v15 branch-coverage repair itself.

### L1 — behavior 4 still demands hash-branch injectivity that §3.2 explicitly retracts

**Severity:** Low

**Evidence:**

`docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:219-222`

```md
**Contract:** total; bounded (65 chars); and **injective on the identity branch, collision-*resistant*
on the hash branch** — the two branches are provably disjoint because `=` ∉ `SAFE`, but 22 base64url
characters is a 132-bit truncation of SHA-256, not an injection (round-9 L6; task #96 recorded this
overclaim and v9 still stated it flat).
```

`docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:1049`

```md
| 4 | `encodeSegment` is injective over arbitrary segments | property + crafted preimage |
```

**Concrete failure scenario:** a test author follows behavior 4 literally and writes a property asserting injectivity over arbitrary strings. That property is mathematically false for a 132-bit truncated hash over an unbounded input domain. If they instead weaken the test to collision resistance, the behavior no longer says what the test proves.

**Proposed fix:** replace behavior 4 with the actual contract, for example:

```md
| 4 | Identity-branch outputs and hash-branch outputs are disjoint, and the hash branch is stable and collision-resistant under the chosen 132-bit truncation | property + crafted marker preimage |
```

Keep any crafted preimage test focused on the `=` marker disjointness, not arbitrary injectivity.

**Classification:** mechanism. The stated behavior cannot be satisfied.

**Caused by v15's own fixes:** no. This is an older encoder-contract overclaim that v15 correctly retracts in §3.2 but leaves stale in §5.

## Notes From Targeted Attacks

No finding on the v15 `slugify` repair. I checked the runtime and filesystem premises:

```text
node -v                         -> v20.18.2
Node 22.14.0                    -> v22.14.0
typeof ''.isWellFormed          -> function on both
```

The one-line repair changes only ill-formed post-slice results in the measured boundary case:

```text
"a".repeat(59) + "\u{20000}" -> old slug ends "\ud840", isWellFormed false
new slug drops that final code unit, isWellFormed true
```

On the real `/tmp` filesystem, writing the old ill-formed slug returns a well-formed mojibake filename from `readdir`:

```text
"003_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa�.md" true
```

That supports v15's pairing: `slugify` stops producing the class; the guard remains a backstop; `readdir` strings are well-formed.

I also did not find a remaining branch-coverage gap in the specific §3.6 branch sets named in the brief: R2 covers the byte-equal, byte-different, unreadable and absent read-back outcomes; the companion table covers envelope-present, `none` and `unknown`; R3 names the name-match/no-probe and non-match/probe branches; `canonicallyEqualName(null, key)` is covered; and the Class-A return space maps to copy-to-cloud, copy-to-local and skip.

NOT CONVERGED
