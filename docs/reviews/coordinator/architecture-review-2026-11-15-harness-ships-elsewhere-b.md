# Phase 6 architecture review — the path rule in `scripts/mkt_stage.py` (PR #594, `harness-ships-elsewhere` slice B)

- Subject: `plan`, `_real`, `_under`, `_below`, `_tracked`, `_tree`, the `out` check in `stage`, and
  `mkt_isolate.fold` / `_reaches`, branch `harness-ships-elsewhere`, read at `4a957e0d`.
- Armed by THRASHING: round 2 carried Codex 3 (caused by the round-1 fold's `_tracked`) and round 3 carries F2
  (caused by the round-2 fold's `fold`), both in component `staging`
  (`harness-ships-elsewhere-b-r2-coordinator.md`, `claude/harness-ships-elsewhere-b-r3-claude.md`).
- Read first: `CONTEXT.md` (it defines no term for staging, a declared path or a private root), `docs/adr/` (none
  governs this path; ADR-0013's principle, *assert the capability, do not digest the privilege*, is the same move
  and nothing here re-opens it), the four review documents and two coordinator documents of subject
  `harness-ships-elsewhere-b`, `docs/review-method.md` → *The stop condition* and *Can a redesign remove it?*, and
  the precedent `architecture-review-2026-11-15-goal-wait-derive.md`.
- No tracked code was changed. Every fixture is a temporary git repository in the session scratch directory.
  Nothing under `.claude/plans/` was read. No disk image was created or mounted.
- Every claim is tagged **[M]** (measured here: a command was run and its output read) or **[I]** (inferred).
- Where measured: the default volume, APFS case-insensitive, macOS 26.5.2, git 2.49.0, Python 3.14.4 **[M]**.

## Recommendation

1. **The thrashing is a mechanism defect.** The staging rule answers "is this path the private directory, a tracked
   file, inside the repository" by comparing SPELLINGS, after a pipeline of transforms (drop `./`, walk links, fold
   case, normalise Unicode, decode git's bytes). Each round found a spelling the pipeline did not equate, or one it
   equated wrongly. A redesign removes the question, so by the method's one test the redesign is owed.
2. **Do not patch round 3's findings onto the pipeline.** The patch was built and measured here: it closes F1 to F4
   as filed and still gets 2 of 30 fixtures wrong and refuses 26 tracked files in the sweep (section 2).
3. **SOURCE side: decide on IDENTITY.** A source question is about an object that exists now on this machine, so ask
   the filesystem: an object is its `(st_dev, st_ino)`. The private roots, the skills home and the tracked set are
   each resolved ONCE to identities. The walk then compares the identity of every object it steps on with those
   sets. No source path is compared with another path as text.
4. **DESTINATION side: one stated POLICY on spellings.** A destination question is about a filesystem that is not
   known yet (wherever the package is installed), so nothing can be asked. One function, `_dest_key`, canonical
   (never compatibility) fold, applied to every PREFIX of every destination. This is a policy that errs towards
   refusing, not an emulation of a filesystem, and its bound is stated.
5. **Delete `fold` from `mkt_isolate`; `_reaches` and the `out` check become identity.** Both ask about paths that
   exist on this machine.
6. **Two refusals are new and deliberate**: a regular file with more than one name (a hard link), and a link with an
   absolute target. The first retires a stated bound. Neither occurs in this repository (0 and 0, section 3).
7. **F5 and F6 are small and outside the redesign.** Fix both in the same build.

## 1. Is "path checks done on spellings" the right class?

Yes. I tried to refute it three ways.

### The record, finding by finding

Findings in component `staging` over three rounds. **[M]** counted from the round documents.

| Round | Finding | Input that broke it | Direction | Caused by |
|---|---|---|---|---|
| 1 | Codex 1 | `.claude/plans` reached through a skill directory or a link | leak | the first build |
| 1 | Claude M3 | an untracked or gitignored file | ships too much | the first build |
| 2 | Codex 1 | `.CLAUDE/PLANS/secret` | leak | a hole in the r1 rule |
| 2 | Codex 2 | an untracked link in a parent, hidden by `resolve()` | ships too much | a hole in the r1 rule |
| 2 | Codex 3 | a non-UTF-8 name in git's index | crash | the r1 fold (`_tracked`) |
| 3 | F1 | tracked link `.claude -> dot`, declare `.claude/plans/secret` | leak | not a fix; same class |
| 3 | F2 | `x².md` + `x2.md` | wrong refusal | the r2 fold (`fold`, NFKC) |
| 3 | F3 | NFD name on disk, NFC in git's index | wrong refusal | not a fix; same class |
| 3 | F4 | tracked link `.agents -> ag` | wrong place | not a fix; same class |

Eight of the nine are one question asked of two spellings: *are these the same object?* The direction alternates
(leak, wrong refusal, leak), which is what moving a string boundary looks like.

### The three refutation attempts

1. **"It is branch coverage: the rule is right and under-specified."** Refuted. Round 2's fold wrote the rule down
   ("an exclusion compares FOLDED, an inclusion compares EXACT, both err towards refusing"). F1 is an exclusion that
   leaks under that rule as written, because the ORDER of two transforms (follow the link, then test the prefix)
   decides the answer. F3 is an inclusion that refuses a tracked file under that rule as written. **[M]** both
   reproduced, section 2.
2. **"A better fold closes it."** Refuted by measurement. The round-3 reviewer's canonical fold, plus the three other
   round-3 fixes, was built as candidate `patch` and run against the same fixtures and sweep. It still stages a
   private file reached by a hard link, still stages `ag/skills/s/SKILL.md` (the F4 object under its other
   spelling), and refuses 26 tracked files. **[M]** section 2.
3. **"The class is narrower: only Unicode, or only links."** Refuted. The nine inputs need case, Unicode form, git's
   byte encoding, a link in a parent, a link at the private root, and a link at the skills home. A fold fixes the
   first two; a walk fixes the fourth; neither fixes the fifth.

### What the class is not

The other findings of rounds 1 to 3 (isolation, the audit log, the keychain sentence, F5's probe timeout, F6's
sentence) are not this class. Leave `run_isolated`, `measured` and `read_audit` alone.

## 2. Can a redesign remove it, and which one?

Three candidates, one harness (`proto.py` in the scratch directory named under *Bound of this review*):

- `head`: `mkt_stage.plan` as committed.
- `patch`: round 3's four fixes on the spelling pipeline (canonical fold; the declared path tested against the
  private roots and the skills home; each private root's own resolved spelling; NFC membership).
- `ident`: the source side by identity, as in the recommendation.

### Fixtures: 30 temporary repositories' worth of declarations **[M]**

Wrong answers out of 30: **`head` 10, `patch` 2, `ident` 1.**

| Fixture | Want | `head` | `patch` | `ident` |
|---|---|---|---|---|
| F1 `.claude -> dot` tracked, `files=.claude/plans/secret` | REFUSED | STAGED | REFUSED | REFUSED |
| F1 same, `skills=.claude/plans` | REFUSED | STAGED | REFUSED | REFUSED |
| F1 same, `files=dot/plans/secret` | REFUSED | STAGED | REFUSED | REFUSED |
| F2 `x².md` + `x2.md` | STAGED | REFUSED | STAGED | STAGED |
| F2 `Ａ.md` + `A.md` | STAGED | REFUSED | STAGED | STAGED |
| F3 skill directory, NFD name on disk, NFC in the index | STAGED | REFUSED | STAGED | STAGED |
| F3 `files=d/café.md` declared in NFD | STAGED | REFUSED | STAGED | STAGED |
| F4 `.agents -> ag` tracked, `files=.agents/skills/s/SKILL.md` | REFUSED | STAGED | REFUSED | REFUSED |
| F4 same object, `files=ag/skills/s/SKILL.md` | REFUSED | STAGED | **STAGED** | REFUSED |
| hard link `p/h` to a private file, tracked | REFUSED | STAGED | **STAGED** | REFUSED |
| a link with an absolute target spelled below the root | STAGED | STAGED | STAGED | **REFUSED** |
| the other 19 (12 controls that must refuse, 7 that must stage) | | all right | all right | all right |

`ident`'s one "wrong" row is recommendation 6: it refuses every absolute link by rule. The 12 controls include every
closed finding of rounds 1 and 2 (case alias, untracked parent link, link to an untracked file, link through
`.claude/plans` and back out, loop, link out of the repository, non-UTF-8 index name).

Three more inputs, run after the table **[M]**:

- The private root is ITSELF a tracked link (`.claude/plans -> ../dot`): `files=dot/secret` and `skills=dot` are
  STAGED by `head`, REFUSED by `patch` and `ident`. This is a second leak shape beside F1, in `head` today.
- `files=DOCS/a.md` where git tracks `docs/a.md`: REFUSED by `head` and `patch`, STAGED by `ident` at
  `DOCS/a.md`. See *What we decided* below.
- On the real repository (5,311 tracked names): 21 skill directories and 4 files declared one at a time, `head` and
  `ident` return the same plan on 25 of 25.

### The round-3 APFS sweep, re-run **[M]**

Every single-code-point SUBSTITUTION at each position of `.claude/plans` (14,456,794 strings) and every INSERTION
(15,568,868 strings), U+0001 to U+10FFFF minus surrogates and `/`. The filesystem's answer is `os.stat` identity
against the private directory.

| | Substitution | Insertion |
|---|---|---|
| strings the filesystem says ARE the private directory | 12 | 0 |
| NFKC `fold` (head): misses / wrong refusals | 0 / 402 | 0 / 1 |
| canonical fold: misses / wrong refusals | 0 / 0 | 0 / 0 |

The 12 are the 11 single-letter case changes and `.claude/planſ` (long s). Round 3 reported 401 where this
run counts 402; this run's predicate is "is or is below", round 3's was equality, and I did not find which string
differs **[I]**.

Then end to end, through each candidate's real `plan()` in a git repository **[M]**:

| Candidate | The 12 aliases, declared: STAGED (a leak) | 403 distinct directories holding a tracked file: REFUSED (wrong) |
|---|---|---|
| `head` | 0 | 403 |
| `patch` | 0 | 26 |
| `ident` | 0 | 0 |

`patch`'s 26 are all one shape: the declared spelling is a case alias of the spelling git tracks, and exact
membership says "not tracked". That is F3's class surviving F3's fix.

### Why identity removes the question, not only these inputs

The pipeline has to guess the filesystem's equivalence rule (which the sweep shows it guessed wrongly in 403
strings) and has to apply its transforms in the right order (F1). Identity does neither: the filesystem resolves the
name, with its own rule and its own link handling, and returns which object it is. Two spellings of one object
cannot get two answers, because the spelling is not an input to the comparison.

## 3. What the redesign costs, and what stays a stated bound

| Item | Measured or inferred |
|---|---|
| Building the identity set for this repository: `git ls-files` 0.02 s, one `lstat` per name 0.07 s, 5,311 names | **[M]** |
| Tracked regular files with more than one name (would be refused by recommendation 6): 0 of 5,311 | **[M]** |
| Tracked links: 21; with an absolute target (would be refused): 0 | **[M]** |
| `_reaches` by identity agrees with the folded one on 5 of 6 inputs; on the 6th (`Repo２/w` beside `Repo2`, distinct directories) the folded one wrongly says "inside" | **[M]** |

Stated bounds that remain:

- **Other filesystems.** Everything above is APFS case-insensitive. HFS+, case-sensitive APFS, exFAT and Linux ext4
  were not measured. Identity does not depend on the filesystem's naming rule, so the source side should carry
  over; a filesystem that does not give stable inode numbers (some FAT and network mounts) would not **[I]**.
- **The destination policy is a guess about a future filesystem.** It folds case and canonical Unicode form. A
  target that equates more (HFS+'s ignorable code points, Windows's reserved names and trailing dots) is not
  covered **[I]**.
- **Time of check.** Identities are taken when the plan is made; the copy happens after. A tree changed in between
  is not seen. Unchanged from today **[I]**.
- **Type change.** A name git tracks as a file, replaced on disk by an uncommitted link, counts as a tracked link.
  This is the existing bound "a tracked file ships its working-tree bytes, not its committed ones" **[I]**.
- **Hard links** stop being a bound on the source side: more than one name is refused. A hard link whose other
  name was since deleted has one name and ships; nothing can tell it from an ordinary file **[I]**.

## 4. Destination: what was measured

Eleven destination sets, wanted answer against the committed rule (`fold` on the whole path plus `_under(rel,
META)`) and the recommended prefix policy **[M]**: **`head` wrong on 5, prefix policy wrong on 0.**

| Destinations | Want | `head` | prefix policy |
|---|---|---|---|
| `x².md` + `x2.md`; `Ａ.md` + `A.md` | STAGED | REFUSED | STAGED |
| `A.md` + `a.md`; `café.md` NFC + NFD; `planſ.md` + `plans.md`; `.CLAUDE-PLUGIN/x` | REFUSED | REFUSED | REFUSED |
| `Dir/x` + `dir/y` (one directory on a case-insensitive target) | REFUSED | STAGED | REFUSED |
| `a` (a file) + `A/x`; `a` (a file) + `a/x` | REFUSED | STAGED | REFUSED |
| `d/x` + `d/y`; `A.md` + `d/a.md` | STAGED | STAGED | STAGED |

**A new finding, P6-N1, in `head` today** **[M]**: a tracked file named `skills` in `files`, plus any skill, passes
`plan()` and then `stage()` dies with an uncaught `IsADirectoryError` AFTER writing `p/skills/sk/SKILL.md`. That
breaks "everything is planned before anything is written". The prefix policy refuses it in the plan.

I also measured asking the `out` filesystem by exclusive creation (`dest.py`). It works there, but it answers for
the staging volume only, and a package staged on Linux is installed on a Mac. So it is not recommended: the policy
is the part that travels.

## 5. The stop condition — what keeps this from thrashing again

**The bet for round 4:** it finds no input where the SOURCE decision (refused, or staged from which object) differs
between two paths that the filesystem resolves to one object. One such input falsifies the redesign.

Not falsifiers, because they are stated bounds: a filesystem not measured here, a tree changed during staging, a
destination alias on a target that equates more than case and canonical form.

If the bet is lost, the next route on the ladder is `split`: staging stops accepting links at all (every component
of a declared path, and every entry of a skill directory, must be a real directory or a regular file). Measured
cost of that retreat here: this repository's 21 tracked links are all under `.claude/skills/` and none is in a
declared path today **[I]** for the second half; the first half is **[M]**.

## Build brief

For a fresh builder. Test-first: write every red case below against `4a957e0d`, watch it fail, then build.

### The rule, in one paragraph

A declared path is repo-relative with no `..` (`_declared`, unchanged). `plan` resolves three sets ONCE, each as
`(st_dev, st_ino)`: the PRIVATE roots (`os.stat` of each entry of `PRIVATE`, links followed; an absent root
protects nothing because nothing is there), the skills home (`os.stat` of `SKILLS_HOME`), and the tracked objects
(`os.lstat` of every name `git ls-files -z` returns, skipping any name one of whose parent directories is a link on
disk). The walk goes from the repository root one component at a time and `lstat`s each. A link must be a tracked
object, must have a relative target, and is replaced by its target's components; `..` pops, and popping past the
root is refused; more than `MAX_LINKS` links is a loop. Any other object is refused when its identity is a private
root (for `skills` and `files`) or the skills home (for `files`). The regular file at the end must be a tracked
object and have exactly one name. The destination is the declared spelling (for a skill, `skills/<last name>/<names
as `os.listdir` returns them>`). Every prefix of every destination is claimed under `_dest_key`; a claim is refused
when the key is already held under another spelling, when either holder is a file, or when the key is the plugin's
metadata directory.

### Functions

| Function | Action |
|---|---|
| `mkt_stage._under` | DELETE |
| `mkt_stage._below` | DELETE (absolute link targets are refused) |
| `mkt_stage._tracked` | KEEP as the git lister (its env and `os.fsdecode` are right); nothing tests membership of a NAME any more |
| `mkt_stage._tracked_objects(top, names)` | NEW. The identity set, with the parent-is-a-link skip |
| `mkt_stage._roots(top, paths)` | NEW. `{identity: declared name}` for PRIVATE and SKILLS_HOME |
| `mkt_stage._real` | REWRITE as the identity walk. Signature: `(top, rel, tracked, forbidden)` |
| `mkt_stage._tree` | KEEP the shape; it passes `forbidden` through |
| `mkt_stage.plan` | the `_under(real…, SKILLS_HOME)` and `_under(rel, META)` tests go; `add` becomes the prefix claim |
| `mkt_stage._dest_key(text)` | NEW. `NFC(casefold(NFD(text)))`. The ONLY text fold in either script |
| `mkt_stage.stage` | the `out` inside-the-repository test uses the identity `_reaches` |
| `mkt_isolate.fold` | DELETE, with its self-test case (`mkt_isolate.py:601`) |
| `mkt_isolate._reaches` | REWRITE by identity: `realpath`, then walk up to the nearest existing ancestor and every ancestor above it, `samestat` against `top`. Three callers, unchanged |

`proto.py` (`walk`, `tracked_objects`, `plan_ident`), `dest.py` (`inside`) and `destkey.py` (`policy`) in the
scratch directory are working prototypes of these. They are a lead: re-derive, do not paste.

### Red cases to write first (each fails at `4a957e0d` unless marked)

1. F1: tracked link `.claude -> dot`; `files=[".claude/plans/secret"]`, `skills=[".claude/plans"]`,
   `files=["dot/plans/secret"]` are each REFUSED and nothing is written.
2. F1's sibling: `.claude/plans -> ../dot` a tracked link; `files=["dot/secret"]` and `skills=["dot"]` REFUSED.
3. F2: `x².md` + `x2.md` STAGE as two files with their own bytes; so do `Ａ.md` + `A.md`.
4. F3: a skill directory holding a name created in NFD and added under `core.precomposeunicode=true` STAGES; the
   case first asserts the index holds NFC and `os.listdir` returns NFD, else it reports NOT RUN, counted apart.
5. F4: tracked link `.agents -> ag`; `files=[".agents/skills/s/SKILL.md"]` and `files=["ag/skills/s/SKILL.md"]`
   are both REFUSED.
6. Hard link: `p/h`, a tracked second name of a private file, REFUSED, and the message says "names".
7. Absolute link target below the root: REFUSED. (Passes today as STAGED; the existing case that stages it is
   rewritten, not deleted.)
8. A tracked name whose parent became an untracked link (`a/x` tracked, `a -> hidden`): `files=["hidden/x"]` and
   `files=["a/x"]` REFUSED. (Green today; it guards the parent-is-a-link skip.)
9. The sweep as a case: for each position of `.claude/plans`, every code point of the BMP substituted (about
   850,000 strings; the full range took 52 s on 8 processes here, too slow for a self-test); `_dest_key` equality
   with `.claude/plans` must equal `os.stat` identity for every string. It asserts first that the volume is
   case-insensitive (`.CLAUDE` resolves), else NOT RUN, counted apart. Zero misses AND zero wrong refusals.
10. Destination prefixes: `Dir/x` + `dir/y` REFUSED; a file `skills` plus a skill REFUSED with nothing written
    (P6-N1); `a` + `a/x` REFUSED; `A.md` + `d/a.md` STAGED.
11. `_reaches`: a fullwidth sibling `Repo２/w` of checkout `Repo2` is NOT inside; a case alias, a link into the
    checkout and a not-yet-existing path below it ARE.
12. Keep every existing case of rounds 1 and 2 (`.CLAUDE/PLANS`, the untracked parent link, the non-UTF-8 index
    name, the link through `.claude/plans` and back out). They must pass unchanged in meaning.

### Mutations to add (each names the case that kills it)

| Mutation | Killed by |
|---|---|
| the private root taken with `os.lstat`, not `os.stat` | case 2 |
| the private-root identity test removed from the walk | case 1 |
| the skills-home identity left out of `files`' forbidden set | case 5 |
| a link's "is a tracked object" test removed | the untracked parent link case (r2 Codex 2) |
| the final file's "is a tracked object" test removed | the untracked file case (r1 Claude M3) |
| the `st_nlink > 1` refusal removed | case 6 |
| the absolute-target refusal removed | case 7 |
| the parent-is-a-link skip removed from `_tracked_objects` | case 8 |
| `_dest_key` uses NFKC | cases 3 and 9 |
| `_dest_key` drops `casefold` | case 9, and `A.md` + `a.md` |
| the claim tests the full path only, not each prefix | case 10 |
| the metadata directory is not pre-claimed | the `.CLAUDE-PLUGIN/x` case |
| `_reaches` compares text again (`str.startswith` on resolved paths) | case 11 |

Of the 67 mutations in `scripts/mutations/mkt_stage.json`, 20 mention the path rule's symbols **[M]** (a text match
on `_under`, `fold(`, `_below`, `_tracked`, `PRIVATE`, `SKILLS_HOME`, `META`, `readlink`, `isabs`, `hops`). Each is
re-bound or retired with a reason; 15 lines of `scripts/mutations/mkt_isolate.json` mention `fold` or `_reaches`
**[M]**. Run the all-manifest anchor resolve after.

### F5 and F6

- F5: `run_isolated` passes each probe in `measured` a timeout no larger than the caller's `timeout`. One red case
  with a probe stand-in that sleeps.
- F6: `docs/marketplace/isolation-baseline.md:27` reads "anything outside the world and its stdlib, or any
  installed distribution".

### Docstring

`mkt_stage.py`'s header replaces the paragraph "The rule for every path comparison here…" with the two-sided rule
(source by identity, destination by one policy) and replaces its *Bounds* sentence with the five bounds of
section 3. The self-test count in the header changes.

## What we decided on this branch that is not written down

1. **A declaration is honoured in any spelling the filesystem accepts.** `files=["DOCS/a.md"]` stages on this Mac
   at `DOCS/a.md` and is "does not exist" on Linux. Both are the filesystem's own answer and neither leaks. The
   alternative, requiring the declared spelling to equal git's byte for byte, is a spelling comparison again and
   brings back F3. I chose the first. If the owner wants manifests that behave the same on every machine, that is
   a manifest lint, not a staging rule.
2. **`fold` was two things under one name**: an emulation of this machine's filesystem (wrong in 403 strings) and a
   portability policy for the destination. Only the second survives, renamed.
3. **PRIVATE protects an object, not a name.** A private directory that is renamed stops being private unless
   `PRIVATE` is updated. That was already true and is nowhere stated.

## Bound of this review

- One volume, one filesystem (section 3). The previous attempt at this review tried others through disk images and
  hung; this one did not attempt them.
- `patch` is my reading of round 3's four fixes, monkeypatched onto `head`, not a build of them.
- The prototypes have no self-test and no mutations; the fixture table is their only evidence.
- Scratch directory with every script and fixture (session-local, not in the repository):
  `/Users/kujinlee/.claude-tmp/claude-501/-Users-kujinlee-code-agentic-ai-docs-youtube-playlist-summaries-cloud/b387c8e6-9003-42f5-a944-1d4eb1de0c9b/scratchpad/p6hse/`
  (`proto.py`, `fixtures.py`, `sweep.py`, `verify.py`, `reasons.py`, `dest.py`, `destkey.py`, `reach.py`,
  `real.py`, `extra.py`, `extra2.py`, `headcrash.py`; this run's fixtures under `apfs3/`).
