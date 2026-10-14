# Round 5 — CLAUDE half, `process-281-mechanism-question` at `da8375b7`

Reviewed the FOLD. Read, in order: `docs/reviews/codex/process-281-mechanism-question-r5-codex.md`,
`git log -1 --format=%B da8375b7`, `git show da8375b7`, then the delivered note top-to-bottom.

**Headline: the withdrawal of the deletion permission is right and holds. The replacement OBSERVATION
is not honest — it prints `OBSERVED: HEAD held these exact bytes just now` over bytes HEAD has never
held, and it does so on a class the fence it replaces got RIGHT and that the Codex half of this very
round measured as sound.** Two further always-delivered permits survive, and both of the round-5
Codex Lows have no recorded disposition anywhere.

## Blocking

### B1 — `OBSERVED: HEAD held these exact bytes just now` is printed when HEAD does not hold those bytes. `git hash-object` applies clean/eol filters unless `--no-filters`.

Note `:94`; frontmatter `:3`; `docs/memory/MEMORY.md:12`.

The fence was extracted from the committed note by parsing its ```` ```bash ```` blocks (my
extraction agrees with the Codex half on all three carried-over fences — see *Instruments*), then
run with `A` in the environment. Green control first in every fixture.

`git hash-object <path>` **applies the attributes mechanism — clean filter and end-of-line
conversion — unless `--no-filters` is passed.** So `WB` is the hash of the *cleaned* content, not of
A's bytes. When the cleaned form matches HEAD's blob, the fence reports that HEAD holds bytes it
does not hold.

Two fixtures, each with its green control:

| Fixture | Green control (on-disk == HEAD) | Attack | Independent evidence | Verdict |
|---|---|---|---|---|
| `* text=auto`, HEAD has LF, disk has CRLF | `OBSERVED` ✓ | CRLF on disk | HEAD blob `e5c5c558…`; `git hash-object --no-filters` `cf9b2a85…` | **`OBSERVED`** |
| `filter.redact.clean = sed "s/.*/REDACTED/"`, HEAD holds `REDACTED\n` | `OBSERVED` ✓ | disk holds `MY ONLY COPY OF SOMETHING PRECIOUS\n` | HEAD blob `a874c3b2…`; raw-disk `0b438521…`; filtered `a874c3b2…` | **`OBSERVED`** |

The second fixture is also destructive. After the fence said `OBSERVED` I deleted the file:

```text
before rm, on-disk: MY ONLY COPY OF SOMETHING PRECIOUS
after rm, git show HEAD:secret.txt: REDACTED
git cat-file -t 0b4385218edfa90d05bb2433b0c760fe27498914
  -> fatal: git cat-file: could not get object info
```

The unique content is not in HEAD, not in the object store, and gone. The smudge filter (`cat`)
cannot reconstruct it. The CRLF fixture is a **false statement** that is not by itself destructive
(checkout smudges the CRLF form back); the clean-filter fixture is a false statement **and** a
destroyed only copy.

⛔ **This is a fix-caused regression, measured head-to-head.** I extracted the pre-fold byte rule
from `07b307cf` — its SHA-256 is `7355cff4e77ad259ddeacbf692efc9ac7f5376355574af1abbb77e75de82996f`,
identical to the hash the Codex half declared — and ran both fences over both fixtures:

| Fixture | OLD fence (`git show | shasum` vs `shasum`) | NEW fence |
|---|---|---|
| clean filter, green control | `HEAD holds this exact content` | `OBSERVED` |
| clean filter, **attack** | `CANNOT SAY HEAD HOLDS IT` | **`OBSERVED`** |
| CRLF, green control | `HEAD holds this exact content` | `OBSERVED` |
| CRLF, **attack** | `CANNOT SAY HEAD HOLDS IT` | **`OBSERVED`** |

The Codex half of this round recorded exactly this class under *Checked and found SOUND* —
*"`core.autocrlf`, text/eol attributes, clean filter changing bytes | Refusal when blob/worktree
bytes differ"* — about the old fence. The fold replaced the fence and did not re-run the row, so the
one case a reviewer had certified as sound is the case the replacement breaks.

⛔ **And it is in all three delivered copies.** `grep -c 'no-filters'` over the note and `MEMORY.md`
returns **0** and **0**: the frontmatter `:3` (`git hash-object -- "$A"`), `MEMORY.md:12`
(`git hash-object $A`) and the note's fence `:94` all carry the defective spelling. Two of those
three are always-delivered text.

**Verified remedy, one flag.** `git hash-object --no-filters -- "$A"` refuses both fixtures and
reproduces all nine outcomes I had measured from the shipped fence unchanged
(tracked/empty-tracked → `OBSERVED`; modified / assume-unchanged / skip-worktree / symlink →
`DIFFERENT`; untracked / empty-untracked / nonexistent → `CANNOT SAY`). **I am not proposing this as
an eighth rule and it restores no permission** — the claim it repairs is the *sentence's truth*, which
is a separate thing from the permission the fold correctly withdrew. The fold's own framing is what
hid this: having concluded that no rule can close the permission gap, it stopped testing whether the
remaining sentence was true.

## High

### H1 — `fails closed` and the stronger *"the only step whose failure mode is a REFUSAL"* survive at `:67-68` as first-person assertions, and the fold's sweep could not see them.

Note `:67`, `:68`.

```text
67: comparison above does, and fails closed. **Nothing in this note is an authority. The byte
68: comparison is the only step whose failure mode is a REFUSAL.**
```

The fold's message says the phrase was swept *"AFTER the three known sites were fixed"* and that
*"the two survivors are now withdrawal QUOTES only."* Measured on the delivered file:

| Instrument | Count | Lines |
|---|---:|---|
| `grep 'FAILS CLOSED'` (case-sensitive — matches the fold's reported result exactly) | 2 | `:87`, `:106` — both genuine withdrawal quotes |
| `grep -i 'fails closed'` | **3** | `:67`, `:87`, `:106` |
| `grep 'failure mode is a REFUSAL'` | 1 | `:68` |

Pre-fold the note held three occurrences (`:67`, `:68`, `:88`); the fold fixed `:88` and left `:67`
and `:68` byte-identical — confirmed by `git diff 07b307cf da8375b7`, in which no added or removed
line contains either phrase. **The sweep was case-sensitive on an upper-case spelling, and the
survivor is lower-case.** A known-positive control for that instrument would have been the
lower-case instance itself.

Why this is High rather than Low:

* `:68` is the *stronger* claim, not a softer one. *"The only step whose failure mode is a REFUSAL"*
  is the same assertion as *"both directions are refuse, never permit"*, which `:106` quotes and
  declares false in the same file.
* It sits **twenty lines above** its own refutation — and the paragraph it lives in (`:61-68`) is
  the record of r4 CLAUDE B2, whose finding was *"the demotion was written and then not carried
  through the text a reader actually meets."* That paragraph now carries an uncarried demotion of
  its own.
* Its referent no longer exists. *"The byte comparison above"* names a fence the fold deleted; what
  ships is a blob-id comparison, which (B1) is not a byte comparison at all. The direction is also
  wrong — the fence is **below** `:67`, and was below it pre-fold too.

### H2 — a surviving permit at `:235`: *"rm only once the survivor is confirmed by sha."*

Note `:229-236`, the note's last executable block:

```text
229: ## ⚠ A cleanup instruction is still an irreversible action
232: **Tidying that uses `rm` is a delete.** The safe form costs nothing:
235: mv <path> "$SCRATCH/"   # reversible; rm only once the survivor is confirmed by sha
```

This is the deletion permission, intact, in the section a reader reaches last, under a heading that
reads as the note's safety advice. "Confirmed by sha" is precisely the rule round 5 refuted twice:
r3's proof sha-confirmed the survivor and said SAFE while the only copy was destroyed (`:137-140`,
still in this file), and B2 shows a successful sha confirms earlier bytes and licenses nothing about
later ones. The fold touched no part of this block — `git diff` over the note shows the only line it
changed containing a permit phrase was the frontmatter.

It also directly contradicts the row the same fold wrote into `MEMORY.md:12` — *"Can't lose it?
`mv` it aside, don't delete"* — so the always-delivered index and the note's closing advice now
disagree about whether `rm` is licensed.

The Codex half listed this fence under CANNOT RUN (*"`<path>` is a placeholder"*) and so never read
the comment on it. Parsing it establishes nothing about what it tells a reader to do.

## Medium

### M1 — Codex r5 L1 and L2 have no recorded disposition anywhere, and both reproduce.

Measured, not inferred:

* `git log -1 --format=%B da8375b7 | grep -E '\bL1\b|\bL2\b|stopping rule|B unreadable|ten-row|Low'`
  → **rc=1, no output.**
* The fold's only use of the word "disposition" is the reviewer's recommended disposition for B1/B2.
* `07b307cf` opens *"All 14 findings folded or dispositioned"*; `da8375b7` makes no such statement,
  so the convention exists on this branch and this fold drops it.
* The diffstat is three files. `.agents/skills/improve-codebase-architecture/SKILL.md` (L1's
  subject) is absent, and the readability bullet (L2's subject) is unchanged in the diff.

Both findings are live, and I established each independently rather than taking Codex's word.

**L1 reproduces.** `SKILL.md`, newline-folded, with a positive control (`shared assertion`, 2) and a
negative (`ZZZ-NO-SUCH-PHRASE-ZZZ`, 0); `docs/review-method.md` has 0 of all three:

```text
1  'if that pass does not yield the shared assertion'   (SKILL.md:174)
1  'If the round ends without that assertion'           (SKILL.md:177)
```

Three lines apart, both prescribing *say so and card B or C*. That is the duplication r4 L1
alleged. `07b307cf`'s *"the stopping rule appears exactly ONCE, newline-folded"* counted one
**spelling** once — the instrument cannot reach the conclusion, exactly as Codex said, and the
duplicate text is in a live skill today. The only durable record still says NOT REPRODUCED.

**L2 reproduces,** against the extracted proof fence, with a green control first. PATH built from a
shim directory plus `/bin` (which has no `shasum`), so only `shasum` is removed:

```text
GREEN CONTROL (shasum present): SAFE: B unchanged without A                            rc=0
ATTACK  (shasum absent):        CANNOT RUN: B unreadable BEFORE anything moved …       rc=2
independent: B readable = [B CONTENT] ; A still present = yes
```

The verdict names a false **cause**. It refuses safely, so it is a diagnostic defect — but the
bullet at `:189-191` still advertises this very check as the thing that prevents a false verdict,
and that advertisement is what L2 asked to be qualified.

### M2 — the M2 fix inverted the enumeration: the dashboard's "opposite" is its LAST member, not its middle one.

`docs/dashboard-entries.md:14876`.

The fold wrote *"TWO are cheats to refuse and the middle one is the OPPOSITE"* — and its own
immediately-following list is ordered:

1. narrowing the scope — a cheat
2. dropping the wording while keeping the behaviour — a cheat
3. the reverse, a rebuild that makes a promise TRUE — *"the right answer anyway"*

So the member that is the opposite is the **third**. The sentence is correct for `SKILL.md:116-121`,
whose list is ordered (1) withdraw the assertion, (2) **the inverse: a redesign that makes the
guarantee TRUE**, (3) a third cheat: narrowing the scope — there the opposite genuinely is in the
middle. The fold copied the skill's *sentence* onto a list with a different *order*.

The Codex half had said which member it was: *"its final member is expressly 'the right answer
anyway'."* So the two copies now agree in words and disagree in fact, which is the same class the
skill's own annotation calls *"this branch's own recurring class appearing in the sentence that
enumerates cheats"* — instantiated again, by the fix for it. Fix-caused.

### M3 — the reading-order half of Codex M1 was not folded, and the fold's message does not mention it.

Codex M1 had three parts. The fold addressed the two positive guarantees and is silent on the third:
*"executable instructions at `:45` precede the firmlink warning at `:53` and subordination at
`:61`."* Confirmed unchanged in the delivered note:

* `:45-51` — a runnable block whose success paths are
  `echo "different real files -> deleting A leaves B" && exit 0` and
  `echo "A is a symlink to it -> deleting A leaves the content" && exit 0`.
* `:53-57` — *then* the firmlink refutation: *"both names report the SAME inode while `realpath`
  returns DIFFERENT strings … and deleting A made B disappear."*

The concrete, actionable form of this: the fold added an in-block self-label to the new fence
(`:91`, *"An OBSERVATION, never a permission"*) and did not add one to the fence Codex flagged. The
diagnostic block carries no marker inside it at all, so a reader who copies the block out of the
note takes the permit-shaped sentences and leaves the refutation behind. The `:26` heading warns in
advance, which is a partial mitigation and is why this is Medium and not High.

### M4 — the two section headings still name a mechanism that no longer ships.

`:26` — *"The check — ⛔ VERIFY BY COMPARING BYTES"* — and `:73` — *"ASK GIT — BUT COMPARE BYTES"*.
What ships compares blob ids, and per B1 it does **not** compare A's on-disk bytes whenever an
attribute or clean filter applies. Both headings survive the fold untouched. A reader who trusts the
heading believes the thing B1 measures as false.

### M5 — the new fence re-instantiates L2's false-cause class, in text this fold wrote.

Measured on the extracted fence:

| Condition | Verdict printed | Truth |
|---|---|---|
| `git` absent from PATH (`PATH` = one empty dir), A **tracked and unmodified** | `CANNOT SAY: HEAD has no such path` | HEAD *does* have the path |
| `git` wrapper printing `partial` and exiting 74 on both calls, A tracked | `CANNOT SAY: HEAD has no such path` | HEAD *does* have the path |

Both refuse, so the direction is safe. But the message attributes the refusal to the repository
state when the real cause is the instrument — the same defect Codex filed as L2 against the old
procedure, reproduced in the replacement. `HB=$(… 2>/dev/null) || { … }` cannot distinguish
"absent from HEAD" from "git did not run", because `--quiet` and `2>/dev/null` discard the only
evidence that separates them.

### M6 — `MEMORY.md` delivery is being truncated right now, so the five-byte argument answers the wrong question.

The fold argues the branch's additions *"stay paid for"* because `MEMORY.md` is 25,879 bytes against
master's 25,884 — five smaller. I re-derived all of that and it is correct (see *Checked and found
SOUND*). But the delivery channel's own report, in this session, is:

```text
WARNING: MEMORY.md is 24.5KB (limit: 24.4KB) — index entries are too long.
Only part of it was loaded.
```

And it is measurably true. The file's last line is
`[1F-a](stage-1f-a-design-state.md) · [1D](stage-1d-merged-followups.md)`; the copy delivered into
this session's context ends one line earlier, at `[1F-b](stage-1f-b-design-state.md) ·`. **Two index
rows were dropped from delivery.** I am a consumer of this channel, which is why I can measure what
`check-memory-link.py` cannot.

This is not caused by this branch — `origin/master` is larger and would truncate at least as much —
and the subject's own row at `:12` is near the top and survives. The finding is narrower: *five
bytes smaller than master* is offered as evidence that the additions cost nothing, while the budget
that actually governs delivery is already exceeded and the loader says so. The claim should either
cite the loader's limit or stop being an argument about affordability.

## Low

### L1 — the categorical row *"tracked symlink → DIFFERENT"* is fixture-dependent.

`git hash-object` follows the link (it hashed the target's `GREEN\n`, not the link text), so the row
holds only while link text and target content differ. Constructed a tracked, unmodified symlink
`selfsame.lnk -> payload.txt` whose target content is the string `payload.txt`:

```text
HEAD:selfsame.lnk blob = ab892e34…   content: [payload.txt]
link target content              : [payload.txt]
fence: OBSERVED: HEAD held these exact bytes just now
```

The *statement* is true here — HEAD does hold those bytes — so this is presentation, not dishonesty.
But the Codex half warned in this same round that *"the categorical symlink outcome is
fixture-dependent"* about the old fence, and the fold reproduced a categorical row anyway.

### L2 — `fatal:` still leaks to stderr on the second call's failure paths.

The fold's claim *"outside a repository → CANNOT SAY **with no leaked `fatal:`**"* is correct — I
isolated stderr and it is empty, because `rev-parse` fails first and `exit 2` runs before
`hash-object`. But the second call carries no `2>/dev/null`, so every `CANNOT RUN` leaks:

```text
A=adir (tracked directory)  -> fatal: Unable to hash adir
                               CANNOT RUN: cannot hash adir
A="" / A unset              -> fatal: could not open '' for reading: No such file or directory
                               CANNOT RUN: cannot hash
A=mysub (submodule path)    -> fatal: Unable to hash mysub
```

r4 L5's class, at the site the fold's no-leak claim does not cover, in a fence the fold says was
*"fixed before it could recur."*

### L3 — `HEAD:$A` is repo-root-relative while `hash-object` is CWD-relative, so running the fence from a subdirectory answers about a different path.

```text
cwd = <root>/sub , A = tracked.txt
  <root>/tracked.txt     in HEAD, content GREEN
  <root>/sub/tracked.txt UNTRACKED on disk, content GREEN
fence: OBSERVED: HEAD held these exact bytes just now
independent: HEAD:sub/tracked.txt -> NO
```

The statement is again true of the *bytes*, so this is not B1 — but the fence's whole purpose is a
question about **a path**, and the recorded row *"untracked → CANNOT SAY"* does not hold once CWD is
not the repo root. With differing content it correctly reports `DIFFERENT`, so the failure is
silent only when the contents coincide. `./`-prefixed and absolute paths both behave correctly
(`OBSERVED` and `CANNOT SAY` respectively).

### L4 — M1's second withdrawal keeps the promise in the bolded, scannable half.

`:210` reads *"it refuses to restore over **anything new at A** that exists AT THE MOMENT OF THE
CHECK"*. The bold runs out before the qualifier does. I measured the narrowed residue and it is
**accurate** (see *Checked and found SOUND*), so this is purely presentational — but in a note whose
thesis is that readers meet the permit before the limitation, the emphasis is on the permit.

### L5 — M3's correction lives only in commit messages; nothing delivered carries the figures.

`git grep` finds the CI-count claim in `docs/reviews/claude/…-r4-claude.md:166` and in `07b307cf`'s
message; the correction is in `da8375b7`'s message. **"NOT FIXABLE BY EDIT" is sound** — filed
testimony is not rewritten and a commit message cannot be edited without rewriting history. But the
record as written does not state the two figures that reproduce (54 inline distinct, 49 inline
`check-*` distinct), so a reader of the correction cannot tell which numbers survived, and it does
not carry Codex's sharper half (all-script self-tests are **28**; 23 belongs to `check-*`). The
record is accurate as far as it goes and **undershoots** by omitting the numbers it vindicates.

### L6 — a `git` that exits 0 with empty or constant stdout yields `OBSERVED`.

```text
git -> {exit 0, no output}        : OBSERVED
git -> {echo deadbeef; exit 0}    : OBSERVED
git -> {echo partial; exit 74}    : CANNOT SAY   (safe — status checked)
git absent                        : CANNOT SAY   (safe)
```

Stated with its premise: this needs a `git` that lies, which is a strictly stronger premise than the
one that killed rule seven (there, *real* git failing produced empty output and the pipeline never
looked at the status). I could not construct a real-`git` invocation of either subcommand that exits
0 with empty stdout. A transparent wrapper that merely *prefixes* stdout does not break the fence,
because the contamination is identical on both calls. Recording it because the class is in scope on
this branch, not because I established a realistic instance.

## Checked and found SOUND

**The 8-of-8 table reproduces exactly as the fold states**, fence extracted from the committed note
and run, green control first:

| Case | Fold's claim | Measured |
|---|---|---|
| tracked + unmodified | OBSERVED | `OBSERVED` ✓ |
| tracked EMPTY file | OBSERVED | `OBSERVED` ✓ |
| empty untracked | CANNOT SAY | `CANNOT SAY` rc=2 ✓ |
| untracked | CANNOT SAY | `CANNOT SAY` rc=2 ✓ |
| nonexistent | CANNOT SAY | `CANNOT SAY` rc=2 ✓ |
| `assume-unchanged` + edited | DIFFERENT | `DIFFERENT` ✓ |
| tracked symlink | DIFFERENT | `DIFFERENT` ✓ (but see Low L1) |
| tracked + modified | DIFFERENT | `DIFFERENT` ✓ |
| outside a repository | CANNOT SAY, no leaked `fatal:` | `CANNOT SAY` rc=2, **stderr empty** ✓ |

Also sound, each measured:

* **The empty-file collision that killed rule seven is genuinely closed.** `git hash-object` of an
  empty file is a real blob id and a missing path makes `rev-parse` *fail*, so the two can no longer
  both be the empty string. The fold's reasoning here is correct; B1 is a different channel.
* **Hostile path shapes all behave.** Leading dash (`-weird.txt` → `OBSERVED`; `--` → `CANNOT SAY`),
  spaces, an embedded newline, absolute path (`CANNOT SAY`), `./`-prefixed (`OBSERVED`), tracked
  directory (`CANNOT RUN`), submodule path from the parent (`CANNOT SAY` / `CANNOT RUN`), the same
  file from inside the submodule (`OBSERVED`), `A` unset or empty (`CANNOT RUN`).
* **Byte counts, all three attributed to their trees.** `git cat-file -s`:
  `da8375b7` = **25,879**; `07b307cf` = **25,873** (this is the Codex half's number — it reviewed
  the pre-fold tree, so the third number is accounted for); `origin/master` = **25,884**. Local
  `master` is stale at 24,356, so the fold's "master" means `origin/master`, which is the correct
  base.
* **Branch and live store are byte-identical.** `diff` reports no difference for both
  `MEMORY.md` (25,879) and the note (19,228) against
  `/Users/kujinlee/code/.../docs/memory/`, with a known-positive control proving `diff` reports a
  difference between two genuinely different files. No `git` command was run in the main checkout.
  Incidentally, the plugin's memory path is a **symlink** into that directory and `stat` gives both
  names `dev=16777220 ino=158338009 links=1` — one file, two paths, `links=1`: the exact shape this
  note exists for.
* **19/19 green under both interpreters.** The set named in the Codex half (14 bare + 5
  `--self-test`), stdin closed on every call: 19/19 on Python 3.14.4 and 19/19 on 3.12.9. The fold
  says plainly this is not the CI suite and that the difference is not a pass; I found nothing in the
  fold treating it as one.
* **Every figure in Codex M3 reproduces,** derived independently from
  `.github/workflows/ci.yml` (766 lines) with a known-positive control
  (`scripts/check-python-pin.py` must be found):

  | population | occ | distinct |
  |---|---:|---:|
  | all python-script command starts, incl. multiline | 58 | 57 |
  | of which multiline (line ends `\`) | 3 | 3 |
  | inline python-script commands | **55** | **54** |
  | inline `check-*` commands | **50** | **49** |
  | inline `check-* --self-test` | 23 | 23 |
  | all-script `--self-test`, any form | **28** | 28 |
  | distinct script paths | **37** | (32 `check-*`) |

  So the recorded withdrawal is **accurate in substance** — both original figures reproduce under
  their stated inline scope and only the "not the CI suite" half stands — and undershoots only in
  what it writes down (Low L5).
* **M1's two withdrawals are genuine, and I verified the residue by measurement rather than
  reading.** The first (`:185-188`) is a full withdrawal: the clause is quoted, marked WITHDRAWN,
  and contradicted outright (*"it does not catch a race"*). The second (`:210-214`) narrows the
  sentence and the narrowed form is true. Both halves of the window, each with a green control
  (fully transparent wrappers → `SAFE`, A restored, no stray park):

  ```text
  new content at A AT the destination check -> ⛔ NOT RESTORED: something NEW is at A.txt.
                                                 Your original is at A.txt.parked.84968   rc=2
  new content at A AFTER the check (wrapper
  creates it on mv call 2, the restore)     -> SAFE: B unchanged without A                rc=0
                                               A.txt = [A ORIG]; the new content is GONE
  ```

  That is Codex B2's second interleaving, independently reproduced — the fold recorded it as NOT RUN
  on its side, and it holds.
* **M2 is folded in substance** — the dashboard now says two cheats and an opposite, which is what
  the skill says, even though the ordinal is wrong (Medium M2).
* **"NOT FIXABLE BY EDIT" is the right call for M3's subject** (a filed review and a commit message).
* **All four bash fences in the note parse** (`bash -n`), over a malformed control that exits 2. My
  extraction of the three carried-over fences agrees byte-for-byte with the Codex half's declared
  hashes: diagnostic `da5070c7…`, proof `3137ca8a…`, cleanup `ffc92fe8…`, and the pre-fold byte rule
  `7355cff4…`.
* **The permission language is out of the frontmatter, `MEMORY.md:12` and the dashboard entry.** My
  newline-folded sweep over all three delivered files, with a known-positive control, found no
  surviving permit in `MEMORY.md` and none in the dashboard entry; the dashboard's 13 `fail-closed`
  hits are unrelated project idiom about other subjects. The survivors are in the **note body**
  (`:67`, `:68`, `:235`) — High H1 and H2.

## CANNOT RUN

**These are verification failures; treat each as NOT RUN.**

* **`check-memory-link.py` as corpus-delivery evidence.** It exits 0 while printing *"the harness
  memory path does not exist, so the assistant reads NO corpus here."* Its subject is the
  worktree's path, not the live one, and its green is advisory — **treat this as NOT RUN.** It is
  *not* the source of my M6 measurement, which came from comparing the delivered context against
  the file on disk; I am keeping the two strictly separate.
* **The mutation sweep** (`scripts/check-plan-code.py --mutate .`) — not attempted here.
* **The remaining CI invocations**, and the exact PR-event forms. I counted `ci.yml`'s invocations;
  I did not execute them.
* **`check-test-counts.py`** — needs `jest-results.json`, absent.
* **`check-review-rounds.py` as a gate** exits 1 for this round's missing Claude half — that is this
  file's absence at the time I ran it, not a defect, and is disclosed in my brief. I did not re-run
  it after writing.
* **`check-withdrawal.py` / `check-provenance.py`** — I did not find them; absent is not passing.
* **Native macOS firmlink reproduction** of the `:53-57` case — not attempted. M3 relies on the note's
  own recorded measurement and on reading order, not on re-measuring the firmlink claim.
* **The Codex half's B1 `shasum`-wrapper interleavings in their original form** — I reproduced the
  *class* against the new fence (M5, L6) and reproduced B2's destination-check window and L2's
  false cause directly, but I did not re-run Codex's own wrappers against the retired fence.
* **Bind mounts, genuine ENOSPC, a natively partial `mv`.**
* **Literal execution of the cleanup fence** (`:235`) — `<path>` is a placeholder. H2 is about the
  comment's instruction, which needs no execution; nothing about its *behaviour* is established.

## Instruments

Worktree `wt-281` at `da8375b7`, clean before and after except this review file. **No `git` command
ran in the main checkout**; the live memory store was read with `wc`, `cat`, `diff` and `stat` only.
`node_modules` symlink used as provided; no `.venv`.

* Both interpreters: `python3` = 3.14.4, `/usr/local/bin/python3.12` = 3.12.9. **Every guard
  invocation had stdin closed (`</dev/null`).**
* Fences were **extracted from the committed note** by parsing its ```` ```bash ```` blocks and
  written to disk, then run as scripts with `A` (and `$1`/`$2`) supplied — never retyped. SHA-256s
  above.
* Disposable repositories via `git init` under the session scratchpad; four separate fixtures
  (plain, clean-filter, `text=auto`, submodule). Nothing was created inside the repository under
  review.
* Transparent wrappers (`git`, `mv`, `shasum`) that `exec` the real tool, each with a
  no-intervention green control run first. PATH isolation via `env -i` and shim directories, with
  the absence of the removed tool proved by `command -v` inside the constrained environment.
* `/usr/bin/grep` explicitly throughout. Every prose instrument folded whitespace (`\s+ -> " "`)
  and carried a known-positive and a known-negative control; the one sweep whose control I could
  not justify (project-wide `fail-closed`, 720 hits of unrelated idiom) I narrowed rather than
  reported.
* Deletions performed only inside disposable fixtures, to establish destructiveness. No tracked file
  was severed, moved or restored.

**Measurement I had to correct mid-review:** my first `ci.yml` counter returned 0 for every
population. A known-positive control (`grep -c 'scripts/' ci.yml` = 72) caught it — the regex
required a command separator immediately before `python3` and YAML spells it `run: python3`. The
counts above are from the corrected instrument, re-run with the control asserting inside the script.

## Where I disagree with the Codex half

1. **Its *Checked and found SOUND* row on filters is the row the fold needed to re-run.** Codex
   recorded *"`core.autocrlf`, text/eol attributes, clean filter changing bytes | Refusal when
   blob/worktree bytes differ."* That was true of the fence Codex reviewed and is **false of the
   fence that shipped** (B1). I do not count this against the Codex half — it reviewed `07b307cf`
   faithfully — but a "found sound" row attached to a mechanism that is then replaced is a
   measurement about a deleted artifact, and the fold inherited it as if it transferred.
2. **"No further rule can close it" is right about the permission and over-general about the
   sentence.** B2's interval argument is sound and I reproduced half of it. But the fold read it as
   closing the whole subject, and so shipped a *statement* whose truth is closeable by one flag and
   was never retested. The honest decomposition is two claims — *is this sentence true?* (closeable,
   and currently false) and *does any observation license an `rm`?* (not closeable) — and collapsing
   them is what let B1 through.
3. **M2: I agree with the finding and the repair went wrong in a way Codex's own text would have
   prevented.** Codex named the *final* member as the opposite; the fold wrote *middle*.
4. **L1 and L2: I agree with both, and reproduced both independently.** My disagreement is with the
   fold, which recorded no disposition for either.
5. **Its CANNOT RUN on the cleanup fence** stops at "the placeholder cannot execute" and so never
   reads the comment beside it, which is H2 — the clearest surviving permit in the note.

---

**Verdict: NOT CONVERGED. Round 6 is owed** (which the fold states; that is not a finding).

⚠ **Evidence for round 6's thrashing determination, since the arming question has to be answered
with per-finding evidence:** two of my findings are caused by this round's own fix — B1 (the
replacement breaks a class the retired fence handled, and which this round's reviewer had certified)
and M2 (the correction inverted the enumeration it was correcting). B1 is the fourth consecutive
round in which this component's shipped artifact was wrong in a direction the previous round had
closed, and the third in which the fix introduced the next instance. H1 and H2, by contrast, are
pre-existing text the fold's sweep missed, not fix-caused. I state the split rather than the count,
because a count is what the branch's own rule says not to arm on.
