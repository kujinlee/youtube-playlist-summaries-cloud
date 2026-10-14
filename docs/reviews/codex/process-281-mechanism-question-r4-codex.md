<!-- codex-review: model=gpt-6.1-sol -->

## Blocking

**NOT CONVERGED. The extracted proof can say SAFE when deletion destroys the only content.**

**B1 — The proof never establishes that B contains A’s content.** `docs/memory/verify-the-other-copy-exists-before-deleting.md:69–82`.

After a green control with identical independent copies:

| A | B | Proof | After deleting A |
|---|---|---|---|
| `PRECIOUS-ONLY-CONTENT` | Identical copy | SAFE, rc=0 | Content survives |
| `PRECIOUS-ONLY-CONTENT` | `unrelated` | SAFE, rc=0 | Content lost |
| `PRECIOUS-ONLY-CONTENT` | Empty file | SAFE, rc=0 | Content lost |

The script hashes **B twice**, never A. It proves that B remained unchanged during parking; it does not prove that B is the supposed backup. Require verification of the intended surviving content before treating this as deletion authority.

**B2 — The restore window permits both a destructive SAFE verdict and silent overwrite.** Note lines 75–81; explanatory claims at 52,88,99.

Using the unmodified extracted script, with deterministic interventions inside a transparent `mv` wrapper:

- Immediately before restoration, replace B with a symlink to A, then execute the real restore. The proof prints **SAFE, rc=0**. Deleting A makes B disappear.
- Immediately after the destination check, create `NEW-PRECIOUS` at A, then execute the real restore. It silently overwrites that new content and prints **SAFE, rc=0**.

The same wrapper without either intervention passes. These are reproducible interleavings, not timing-dependent background races.

The claims “survives a race” and “never overwrite anything” exceed the implementation. Another observation alone cannot establish safety through a later deletion; the procedure needs an explicit concurrency boundary.

## High

**H1 — Hash failures still become verdicts, including SAFE.** Note lines 69–82,93–94.

Neither pipeline checks `shasum`’s exit status.

- A controlled second hash exiting 74 without output produces **DO NOT DELETE, rc=1**, despite B remaining readable and unchanged.
- A controlled hash printing a partial result and exiting 74 on both calls produces **SAFE, rc=0**. With B symlinked to A, deleting A then destroys the content.

Thus “Any failure is CANNOT RUN, never a verdict” is false in both directions. Check hashing success independently of captured output.

**H2 — Interruption still leaves A parked without a recovery message.** Note lines 74–80.

A deterministic SIGTERM immediately after the real first `mv` produced:

- Process terminated by signal 15.
- No stdout or stderr.
- A absent from its original name.
- Original content retained at `A.parked.<pid>`.

There is still no `trap`. Round-3 L2 was silently dropped; the FIFO guard fixes the reported hang, but not this damaging interrupted state.

**H3 — The fifth overshoot survives in the frontmatter.** Note line 3 versus lines 35–39; `docs/memory/MEMORY.md:12`.

The body correctly narrows the claim to **the link count cannot answer this**. The frontmatter still declares:

> `stat` CANNOT ANSWER THIS

and “DERIVE NOTHING.” The corrected index row therefore still disagrees with a delivered description of its topic. H2’s fold is incomplete—the same withdrawn claim remains in the same file.

## Medium

**M1 — Ten round-3 findings have no recorded disposition.**

I walked all 15 Claude findings against the fold:

| Round-3 finding | Disposition |
|---|---|
| B1: corrected index row absent from refs | Folded; row now committed. Remaining frontmatter disagreement is H3 above. |
| H1: FIFO/device hangs | Folded; reproduced refusal without tree changes. |
| H2: overbroad `stat` slogan | Folded incompletely; frontmatter retained it. |
| H3: two stale enumerations | Folded at both named sites. |
| M1: CI denominator provenance | Silently dropped. |
| M2: option D continuation | Silently dropped. |
| M3: unsuccessful investigation stopping rule | Silently dropped. |
| M4: evidence of pre-existing scope | Silently dropped. |
| M5: removing/weaking the refutation instrument | Silently dropped; the prior review explicitly bounded this as a proposed rule, not a witnessed incident. |
| M6: unrelated change attributed to removing A | Silently dropped; reproduced. |
| M7: live note missing branch guidance | Folded; note and deletion row now match their live counterparts. |
| L1: missing instrument reported as unreadability | Silently dropped; reproduced. |
| L2: absent interruption trap | Silently dropped; reproduced as H2 above. |
| L3: ambiguous A routing labels | Silently dropped. |
| L4: interactive `$$` reused across invocations | Silently dropped. |

No written deferral reason resolves those ten. Their presence in the immutable review records testimony, not a fold disposition.

**M2 — D remains unrouted in both cards.** `SKILL.md:162–173`.

Both cards offer D, but the continuation paragraph routes only A/B/C. “Ask before choosing” does not specify how answering D returns to selection or ends the review.

**M3 — Investigation still lacks an unsuccessful stopping condition.** Skill lines 165–169.

Finding a shared assertion is a success condition. “If the round ends without that assertion” supplies no rule for when that happens. State a finite investigation boundary and the unsuccessful continuation.

**M4 — “Scope existed BEFORE the finding” still lacks required evidence.** Skill lines 125–127; `docs/review-method.md:229`.

The instruction does not require quoting a dated, preceding scope record or refusing the dismissal when none exists. Round-3 M4’s escape remains.

**M5 — Changed B is still attributed to removing A.** Note line 82.

A deterministic unrelated append, after a green no-append control, returns **DO NOT DELETE: B vanished or changed without A**, rc=1. A and B are independent; deleting A is safe. Hash difference establishes drift, not its cause. Separate observed disappearance from an inconclusive concurrent change.

**M6 — The diagnostic fails on a native macOS firmlink pair.** Note lines 38–46.

For one file reached through:

```text
/private/tmp/<fixture>/A
/System/Volumes/Data/private/tmp/<fixture>/A
```

Both names reported the same inode. `realpath` returned different strings. The diagnostic printed **“different real files -> deleting A leaves B”**, rc=0; deleting A made B disappear.

The reversible proof correctly refused this fixture. Keeping the diagnostic subordinate limits the damage, but the general “DOES decide aliasing” claim needs this bound. The hard-link caveat does not cover firmlinks.

**M7 — A fresh stale enumeration remains in the dashboard.** `docs/dashboard-entries.md:14876`.

It still says **“two ways … are written down as refusals”** and describes two, while the revised skill explicitly lists three. The two H3 sites were fixed, but this third copy was missed. The branch changes no code-comment files; the comment sweep found no newly introduced instance there.

**M8 — “The CI suite holds 49 distinct commands” names a subset as the suite.**

The number is reproducible:

- **50 inline `python3 scripts/check-*` invocations**
- **49 distinct commands: 26 audits + 23 self-tests**

But `.github/workflows/ci.yml` contains **55 inline Python-script invocations / 54 distinct commands**, including five non-`check-*` commands, plus three multiline Python invocations.

The denominator is therefore derivable, contrary to round-3 M1’s strongest wording. What remains defective is its unexplained scope and its designation as the CI suite.

## Low

**L1 — Missing hashing tools and leading-dash paths receive misleading causes.** Note lines 69–74.

A missing/failing hashing instrument is reported as “B unreadable.” Relative `-B` receives the same message; relative `-A` receives “mv failed.” These refuse safely, but do not identify the actual problem. Absolute paths containing leading dashes pass.

**L2 — Two different A answers remain in one routing paragraph.** Skill lines 163–164.

“A (redesign)” and “A (INVESTIGATE)” belong to different cards. Name the card alongside each continuation.

**L3 — `$$` remains per-shell when pasted or sourced.** Note line 71.

The collision guard refuses safely, but an interrupted invocation can block the next attempt in the same shell. Round-3 L4 remains unresolved.

**L4 — The commit’s “nine-line implementation” has five lines.**

The diagnostic’s own fence contains five executable lines. This figure does not reproduce.

**L5 — Index compaction has regressed.**

`MEMORY.md` is now **25,906 bytes**, versus **25,884** on `origin/master`: **22 bytes larger**. The previous fold’s 37-byte saving was consumed by this correction. The earlier displacement finding’s repair no longer pays for the branch’s additions.

## Checked and found SOUND

- **Both original seven-case sets reproduce**, using the note’s extracted fences:

| Case | Proof | Diagnostic |
|---|---|---|
| Independent files | SAFE | SAFE |
| B symlink to A | REFUSE | REFUSE |
| A symlink to B | SAFE | SAFE |
| Dangling B | CANNOT RUN | CANNOT RUN |
| Mode-000 B | CANNOT RUN | SAFE |
| Third hard link; B through symlinked parent | REFUSE | REFUSE |
| Genuine hard-link pair | SAFE | SAFE, with the stated incorrect explanation |

- **FIFO regression reproduced:** the pre-fix fence, with one FIFO writer, timed out at rc=137 after parking A. The current fence returns rc=2 immediately, leaves A intact and creates no parked file. Regular-file controls pass.
- `-f` accepts symlinks to regular files. FIFOs, character devices, sockets, directories, B inside directory A, and dangling symlinks are refused unchanged.
- Spaces, newlines, relative ordinary paths, symlink chains, a 16 MiB binary file and a 1 GiB sparse file were exercised. Successful proof runs restored A.
- A read-only parent refuses the first move. Making the parent read-only after parking causes the real restore to fail, rc=2, with the parked location reported. Restoration is **not guaranteed**.
- Existing dangling parking names are refused. New content already present at A when the destination check runs is preserved and reported.
- APFS clones survive source deletion. The case-only alias fixture on this case-insensitive filesystem was correctly refused by both procedures.
- **B1’s committed-row repair is real:** 29 refs contain `MEMORY.md`; the corrected row occurs in both the local branch and its remote ref. The note’s live copy is byte-identical, and deletion-index line 12 is identical. The live memory directory resolves through the stated symlink. **The complete `MEMORY.md` files differ** in other rows; whole-file byte identity is not established.
- The deletion row retains a recognisable cleanup situation. Its title alone is not the entire retrieval cue.
- Both instantiated four-option cards pass the checker and hook under both interpreters. A green control passed first; a malformed negative control was refused. Their substantive actions are distinct: redesign/investigate, another local repair, or recorded acceptance.
- Thrashing-armed execution encounters the prerequisite before presentation. An unarmed milestone review explicitly skips it; that permitted path is sound.
- H3’s two named corrections now read **THREE/all** and **5/four reviews**. The pinned `b310c470` measurement reproduces **5/195**; its pin remains valid.
- The claimed review inventory reproduces **1 Blocking / 3 High / 7 Medium / 4 Low**. Dashboard source contains **307 sections**.
- **The named 19-invocation set passes under Python 3.14.4 and 3.12.9.** Initial 50-second timeouts on `check-main-drivable` were inconclusive; longer retries passed under both. No timeout was counted green.

## CANNOT RUN

**These are verification failures; treat each as NOT RUN.**

- Full mutation sweep, remaining CI commands, and exact PR-event/body-payload forms: NOT RUN.
- `check-test-counts.py --results jest-results.json`: rc=1 under both interpreters; results file absent. Treat this as NOT RUN.
- Bind mounts: NOT RUN. Native firmlinks were exercised separately.
- Genuine ENOSPC/read-only-volume and native partially completed `mv` failures: NOT RUN. Directory-permission and deterministic intervention cases do not establish those cases.
- Original owner-facing Phase 6 card and historical dirty-checkout/ref snapshots: not independently recovered. Current ref and live-copy checks do not recreate those historical snapshots.
- Actual corpus delivery: `check-memory-link` returns its missing-harness-path warning with rc=0. Treat delivery verification as NOT RUN.

## Instruments

Reviewed committed HEAD `a75ab8ff`; read commit messages in the required order, all six prior reviews, the subject diff and whole-branch diff. No Git command ran in the main checkout; live-store inspection was read-only.

Extracted fence SHA-256:

```text
proof:      3137ca8af87027c374fccb8a3836bf239111ed515b0fc814a7ba0ea84e50d591
diagnostic: da5070c7d4750538e424f8157d3285ed52c46ca4a8829c6d35033f478e3e44d4
```

The named guard set was the bare invocations of `check-docs`, `check-anchors`, `check-arch-findings`, `check-backlog-closure`, `check-explainer-delivery`, `check-features`, `check-gate-falsifiability`, `check-main-drivable`, `check-memory-link`, `check-plan-file-tags`, `check-producer-enumeration`, `check-rc-contract`, `check-review-rounds`, `check-roadmap-consistency`, `check-surface-recall`; plus `--self-test` for `check-anchors`, `check-features`, `check-rc-contract`, `check-selection-card`.

Every non-card guard had stdin closed; cards received saved JSON. Python 3.12 subprocesses used a matching PATH shim. Deterministic attacks had green controls; the timeout harness reproduced both completion and a known hang.

**Worktree remains clean. No review file was written.**
