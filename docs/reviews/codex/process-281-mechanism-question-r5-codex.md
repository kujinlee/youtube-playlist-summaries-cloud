<!-- codex-review: model=gpt-6.1-sol -->

## Blocking

**NOT CONVERGED. The seventh rule permits destructive deletion.**

**B1 — Failed instruments can produce “HEAD holds this exact content.”** `docs/memory/verify-the-other-copy-exists-before-deleting.md:92`.

The extracted, unchanged fence passed a tracked-file green control, then produced these results:

| Attack | Independent evidence | Shipped verdict |
|---|---|---|
| Empty untracked file | `git show HEAD:empty` exits **128**, emits zero bytes | **HEAD holds this exact content** |
| Empty file, execution outside any repository | No HEAD lookup succeeds | **HEAD holds this exact content** |
| Hashing tool prints `partial`, exits **74** on both calls | HEAD contains `CONTROL`; working file contains `ONLY PRECIOUS CONTENT` | **HEAD holds this exact content** |

In the last case, deleting the working file destroyed the unique content. The transparent hashing wrapper passed first without the intervention.

The pipeline hashes failed `git show` output as an empty stream. Neither pipeline checks the producer’s status; equal partial hash output also passes. This refutes “FAILS CLOSED” at `:88` and “both directions are refuse, never permit” at `:106`.

**B2 — Successful hashing does not establish safety through deletion.** Note `:93`, `:95`, `:108`.

A transparent wrapper ran the real `shasum`, preserved its successful status, then deterministically changed A immediately after hashing:

- Control: fence permits; A contains `CONTROL`.
- Intervention: fence permits; A now contains `AFTER-HASH-UNCOMMITTED`.
- Delete A: unique new content disappears; HEAD still contains only `CONTROL`.

This is a deterministic interleaving, not a flaky timing test. The fence observes earlier bytes and promises safety for later bytes without a stability boundary.

**Recommended disposition: withdraw the deletion-permission verdict and its guarantees. This is a refusal remedy, not an eighth rule.** Another classifier or extra observation would leave the demonstrated interval between observation and deletion. The owner’s separate decision about deleting the demoted procedure remains open.

## High

**H1 — Both false guarantees remain in always-delivered text.** Note frontmatter `:3`; `docs/memory/MEMORY.md:12`; dashboard `:14929`.

The frontmatter promises equality means “`rm` cannot destroy it”; MEMORY says “equal ⇒ `rm` can’t destroy it”; the dashboard says the replacement “FAILS CLOSED.”

B1 and B2 refute those claims. Branch/live byte identity is established, so these are committed and live defects, not corrections stranded in an uncommitted checkout.

## Medium

**M1 — Demotion still leaves affirmative endorsements beside the broken proof.** Note `:168`, `:190`.

The explanatory bullets still promise:

- Hashing catches “a replacement race.”
- The procedure refuses restoration over “anything new at A.”

The same note’s B2 at `:124` describes replacement and destination-check interleavings that defeat those promises. The old “authority,” “survives a race,” and instrument-failure guarantees are explicitly withdrawn, but these two positive guarantees survive.

The diagnostic also appears before the byte-comparison fence: executable instructions at `:45` precede the firmlink warning at `:53` and subordination at `:61`. A hurried reader reaches its false deletion verdict before its limitation.

**M2 — M3’s dashboard correction is incomplete.** `docs/dashboard-entries.md:14876`.

It still says **“THREE ways … fixing nothing … refusals”**, while its final member is expressly “the right answer anyway.” The skill at `.agents/skills/improve-codebase-architecture/SKILL.md:116` correctly says two cheats and an opposite. The copies disagree.

**M3 — The CI-count withdrawal conflates different populations.** `git log -1 --format=%B 07b307cf`.

Both original Codex figures reproduce when their stated inline scope is retained:

| Invocation population | Occurrences | Distinct commands |
|---|---:|---:|
| All Python-script command starts, including multiline starts | 58 | 57 raw starts |
| Inline Python-script commands | **55** | **54** |
| Inline `check-*` commands | **50** | **49** |
| Inline `check-* --self-test` commands | 23 | 23 |

There are **37 distinct script paths**. All-script self-tests number **28**, rather than 23; 23 belongs to `check-*`.

Thus 54 and 49 are reproducible subset counts. Calling either the whole CI suite was defective; treating 58/37 as evidence that 54 cannot reproduce is also defective. The ten-row table’s “49 IS derivable” disposition is supported.

## Low

**L1 — “Duplicated stopping rule NOT REPRODUCED” uses an instrument that cannot establish that conclusion.** Skill `:173`, `:176`.

With newlines folded, and a known-positive control for each phrase:

- “if that pass does not yield the shared assertion” occurs once.
- “If the round ends without that assertion” also occurs once.

Both prescribe failure reporting and card B or C. Counting one spelling once does not refute semantic duplication. Round-4 L1 reproduces.

**L2 — The ten-row table’s r3 L1 disposition remains partial.** Note `:129`, `:150`, `:169`.

H1 records verdict corruption from failed hashing. It still does not identify the separate false **cause**, “B unreadable,” when the hashing instrument is absent.

After a green proof control, removing `shasum` from PATH produced:

```text
CANNOT RUN: B unreadable BEFORE anything moved — nothing tested
```

B remained readable. This refuses safely; it is a diagnostic defect, not a destructive permit.

## Checked and found SOUND

The explicit eight-case population reproduces from the extracted fence:

| Case | Result |
|---|---|
| Tracked, unmodified | Holds |
| Untracked, nonempty | CANNOT SAY |
| Nonexistent | CANNOT SAY |
| Tracked, modified | CANNOT SAY |
| Assume-unchanged, edited | CANNOT SAY |
| Skip-worktree, edited | CANNOT SAY |
| Ordinary tracked symlink with distinct target bytes | CANNOT SAY |
| In HEAD, removed from index | Holds |

These eight observations do **not** establish fail-closed behavior. A tracked symlink whose target bytes equal its stored link text can also report holds; the categorical symlink outcome is fixture-dependent.

Additional extracted-fence observations:

| Attack | Result and implication |
|---|---|
| Spaces; binary; literal digest text; unnormalized CRLF; 1 GiB sparse file | Holds for matching HEAD bytes |
| Newline; leading dash | Refusal on tested nonempty tracked files |
| Absolute path; nonempty outside-repository path | Refusal |
| Root-relative and `./`-prefixed ordinary path | Holds |
| Directory | Refusal |
| Submodule-internal path from parent repository | Refusal |
| Same file from inside submodule | Holds |
| `core.autocrlf`, text/eol attributes, clean filter changing bytes | Refusal when blob/worktree bytes differ |
| `shasum` absent | Refusal, with command-not-found stderr |
| Nonempty content only in another ref, stash, or reflog | Refusal |

The latter HEAD-only cases support that limited bound. They do not rescue the erroneous conservative-failure guarantee.

Other checks:

- Both branch memory files are **byte-identical** to the live store by `diff`. MEMORY is **25,873 bytes**, versus master’s **25,884**.
- Walked **92 refs** with a working positive and bogus-pattern negative control. The corrected row exists in both local and remote process-281 refs; bogus pattern finds none.
- The old fence extracted from `26697f70` permits assume-unchanged edited content. After deletion, `AU-EDITED-ON-DISK` is gone and HEAD contains only `AU`.
- Native firmlink reproduction: same device/inode, different resolved strings; diagnostic permits, deletion removes B. The extracted proof refuses. The stated firmlink bound reproduces.
- All **four extracted fences parse**; a malformed parse control exits 2. Diagnostic and proof green controls execute successfully.
- r3 M6’s drift-versus-cause defect and r3 L4’s per-shell `$$` limitation are now recorded beside the procedure at `:177` and `:172`.
- Ten-row disposition audit: M1 answered; M2/M3/M4/L3 folded; M5 explicitly refused on the witnessed-incident ground; M6/L2/L4 recorded; L1 partial as above.
- L4’s correction properly excludes the previously dropped no-trap finding from fix-caused evidence. L6’s narrowed refusal ground matches r3 testimony.
- No current shipped-fence `fatal:` leak reproduced. The branch-diff occurrences are filed testimony.
- Step 2’s presentation gate, finite investigation bound and D continuation are present.

The named guard invocation set returned **status 0 under both Python 3.14.4 and 3.12.9**:

- Bare: `check-docs`, `check-anchors`, `check-arch-findings`, `check-backlog-closure`, `check-explainer-delivery`, `check-features`, `check-gate-falsifiability`, `check-main-drivable`, `check-memory-link`, `check-plan-file-tags`, `check-producer-enumeration`, `check-rc-contract`, `check-roadmap-consistency`, `check-surface-recall`.
- `--self-test`: `check-anchors`, `check-features`, `check-rc-contract`, `check-review-rounds`, `check-selection-card`.

These are `scripts/<name>.py`: 19 invocations per interpreter. `check-memory-link`’s zero status is **not delivery verification**.

## CANNOT RUN

**These are verification failures; treat this as NOT RUN.**

- Actual corpus delivery: `check-memory-link` reports its corpus absent.
- Full mutation sweep, remaining CI invocations and exact PR-event forms.
- Jest-dependent test-count audit: no `jest-results.json`.
- Bind mounts, genuine ENOSPC and native partially completed `mv`.
- Fresh independent reproduction of every retained proof interleaving and signal case; the new byte-fence interventions do not establish those older measurements.
- Literal execution of fence 3, `mv <path> "$SCRATCH/"`, fails because `<path>` is a placeholder. Parsing it establishes no correctness.
- Fresh instantiated-card/hook validation beyond the selection checker’s self-test.

## Instruments

Reviewed `07b307cf`; read commit messages in the required order. Used extracted shipped fences, disposable Git repositories, stdlib Python subprocess harnesses, transparent tool wrappers and read-only live-store comparisons.

Used **`/usr/bin/grep` explicitly**, never the shell function. Prose instruments folded newlines and included known-positive controls.

Extracted fence SHA-256:

```text
diagnostic da5070c7d4750538e424f8157d3285ed52c46ca4a8829c6d35033f478e3e44d4
byte rule  7355cff4e77ad259ddeacbf692efc9ac7f5376355574af1abbb77e75de82996f
proof      3137ca8af87027c374fccb8a3836bf239111ed515b0fc814a7ba0ea84e50d591
cleanup    ffc92fe8036407deea4a181be05224da492f44f3cd803dcba3bcd2722189d715
```

Every guard had stdin closed. No Git command ran in the main checkout. No tracked file was severed or restored; memory hashes still match committed blobs. Worktree remains clean. No review file was written.
