<!-- codex-review: model=gpt-6.1-sol -->

**NOT CONVERGED.** The bet is refuted.

1. **Major — `scripts/check-review-rounds.py:236`: a finding’s first YAML example still becomes the header. Fix-induced: no; round-1 defect incompletely fixed.**

   Concrete input in the sole `p-r1-codex.md`:
   ````markdown
   # Round 1 codex

   ## Major: example input

   ```yaml
   halves:
     claude: "GAP: example only"
   ```
   ````
   `gap_reasons()` returns `{'claude': 'example only'}` and `audit(..., set())` reports zero problems. Removing the outer four-backtick fence from round 1’s reproduction defeats the fix. Changing the example to `codex` also makes `first_codex_gap()` supply a waiver and `tail_verdict({})` return **0**.

2. **Major — `scripts/check-review-rounds.py:276`, `scripts/check-review-recorded.py:1125`: collecting every prose match newly promotes a quoted Codex gap into a waiver. Fix-induced: yes.**

   Concrete document:
   ````markdown
   # Round 1

   REVIEW GAP: claude — quota

   ## Finding: sample input

   ```text
   REVIEW GAP: codex — example only
   ```
   ````
   Before the fold, `first_codex_gap()` returns `None`. After it, the result is `codex: example only`, attributed to this document, and the missing-verdict final-tree rule exits **0**. The new per-half lookup searches examples as declarations.

3. **Major — `scripts/codex-review.py:581–585`, `:916`, `:1337`: normalizing before resolving symlinks bypasses refusal, watching, and overwrite protection. Fix-induced: no; the new realpath comparison leaves this bypass open.**

   Concrete layout:
   ```text
   scratch/alias -> B/docs/reviews/claude/sub
   --out scratch/alias/../victim-r1-claude.md
   ```
   The actual destination is `B/docs/reviews/claude/victim-r1-claude.md`; `abspath()` instead collapses it to `scratch/victim-r1-claude.md` before `realpath()` runs.

   End-to-end CLI reproduction with a stub reviewer **overwrote an existing Claude review without `--allow-overwrite`, returned 0, and emitted no intrusion warning**.

4. **Major — `scripts/codex-review.py:920`: a missing artifact directory is never watched. Fix-induced: no.**

   Concrete input: reviewed repository B initially lacks `docs/reviews/`. Call `watched_dirs(..., reviewed=B)`, snapshot, then create `B/docs/reviews/intruder.md`. The subsequent intrusion result is **`[]`**. `dir_snapshot()` already supports missing directories, but the directory-existence filter prevents that protection.

5. **Minor — `scripts/mutations/codex-review.json:656–668`, `scripts/codex-review.py:2592`: the realpath mutation is killed for an ambient reason. Fix-induced: yes.**

   Applied the manifest’s exact lexical-only mutation, then ran with:
   ```text
   TMPDIR=/private/var/.../T
   ```
   Result: **183/183 passed, exit 0**. The fixture creates no explicit symlink; its normal kill depends on macOS temporary paths using `/var` while reviewed roots resolve through `/private/var`. The mutation survives when those spellings already agree.

Verification completed:

| Required check | Result |
|---|---|
| `codex-review --self-test` | 183/183 |
| `check-review-rounds --self-test` | 110/110 |
| `check-review-recorded --self-test` | 197/197 |
| Live corpus | 618 rounds, 25 total exemptions, zero silent gaps |
| Codex mutation slice | 57/57 killed and attributed |
| Rounds mutation slice | 50/50 killed and attributed |
| Recorded mutation slice | 69/69 killed and attributed |

The seven added exemptions are honest: each is a coordinator-named Codex-stamped document declaring a Claude gap. No additional exemptions were needed. Comparing the old and narrowed readers found no historical YAML-gap documents newly refused; all 87 claimed lines were present. Round-1 inputs and grammar neighbours were replayed.

Reviewed the fold first, then the whole branch against `origin/master`. No file under `.claude/plans/` was read. No review file was written.

**NOT CONVERGED.**
