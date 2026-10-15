# Round 6 — CLAUDE half, `plugins-handoff-citations` at `1231edcf`

Reviewed the REDESIGN (`a8d92518`) and the Phase 6 record (`1231edcf`), against `dd595394` as base.
**NOT CONVERGED** — five High and six Medium findings, and the headline one is the risk round 6 named
and did not close: **the surviving single copy is not true about the vendor.**

⭐ **The one sentence that matters.** I rebuilt the two controls the record says it accepted without
reproducing, and both reproduce exactly as tabled — but reproducing them *with variation* produces
**two configurations the canon's exception table does not cover**, and in one of them a session's
handoff is silently redirected into **an unrelated repository**. The canon's four stated exceptions
read as exhaustive and are not. Separately, **a fourth hint trigger exists at 0.33.0**, which the
canon reserves for a future vendor bump.

---

## Blocking

**None.** Stated rather than left implicit: nothing here breaks a gate, mis-enforces a rule, or ships
a wrong mechanism into enforcement. H1–H5 are wrong or incomplete *statements* in the single source
and in the record that approves it, which is the class this branch exists to remove, not a live code
defect. The guard itself does what the fold says it does on every shape the fold tested, and I
reproduced all three of its falsification cases plus a retrodictive control the fold did not run.

---

## High

### H1 — The canon's worktree exception table is incomplete, and its summary sentence is FALSE in two measured configurations. One of them redirects the handoff into an unrelated repository.

`.agents/skills/shared/handoff-path.md:97-105`.

I reproduced every row the canon tables, with `=== REMEMBER ===` asserted as a positive control on
each and **an isolated `HOME` *and* `TMPDIR` per row** (the second isolation matters — see H2):

| canon row | my result |
|---|---|
| main checkout, default config | no hint ✓ |
| ordinary linked worktree | hint → main checkout ✓ |
| worktree created from another worktree | hint → original main checkout ✓ |
| subdirectory of a linked worktree | hint → main checkout ✓ |
| main checkout moved, then `git worktree repair` | hint → moved main checkout ✓ |
| **bare-repository worktree**, default config | no hint; store local ✓ |
| **ordinary submodule** | no hint; store stays in the submodule ✓ |
| linked worktree, relative `data_dir=notes` | hint → `<main>/notes/remember.md` ✓ |
| linked worktree, absolute `data_dir` | no hint; store stays in the worktree ✓ |
| main checkout moved **without** repair | completes, store local, no hint ✓ |

Also reproduced: all nine `data_dir` rows (`notes`, `a/b`, `.`, `./notes`, `notes/`, `a//b`, `..`,
`~`, unset) and the `per_session` row. **The canon is accurate about everything it tables.**

⛔ **But the vendor's candidate main checkout is `dirname(common-dir)`, and the canon never says so.**
`lib-memory-dir.sh`'s `_resolve_memory_project_dir` does three things: a `[ -d "$proj/.git" ]`
short-circuit; a `common-dir` vs `git-dir` comparison; then `_main=$(dirname "$_gcd")` followed by
`git -C "$_main" rev-parse --is-inside-work-tree`. The canon states the first two steps and the
*existence* of the third, and omits how the candidate is derived — and **every case below falls out
of exactly that omission:**

**CASE A — a bare-repository worktree whose bare repo sits inside any other work tree. Measured:
HINT FIRES, to a directory that is not a checkout of this repository.**

```
hostrepo/                    <- an unrelated git work tree
  nested/bare.git            <- bare clone of the subject repo
  nested/wt                  <- `git -C nested/bare.git worktree add nested/wt`
```
`dirname(common-dir)` = `hostrepo/nested`, and `git -C hostrepo/nested rev-parse
--is-inside-work-tree` → **true** (it is inside `hostrepo`). Result: `Write next handoff to:
…/hostrepo/nested/.remember/remember.md`, and the store landed there, **not** in `nested/wt`.

This refutes the canon's row as written (*"bare-repository worktree, default config | no hint; the
store stays local"*) and its summary (*"a bare-repo worktree, a submodule, or an unresolvable main
checkout fall back to a local store"*). The bare-repo row is conditional on something the canon does
not state, and the redirect target in this configuration is an arbitrary directory.

**CASE B — a linked worktree of a `--separate-git-dir` repository. Measured: NO HINT, in a worktree
that is ordinary and fully resolvable.**

`git init --separate-git-dir sgd/gitdirs/proj.git sgd/proj`, then `git -C sgd/proj worktree add
sgd/wt`. `dirname(common-dir)` = `sgd/gitdirs`, which is not a work tree → fall through, store stays
in `sgd/wt`. I verified the worktree is ordinary: `git status --short --branch`, `git worktree list`,
`git log` and `rev-parse --show-toplevel` all answer correctly. None of the canon's four exceptions
applies, and the canon's closing sentence — *"The redirect holds for ordinary, resolvable linked
worktrees on default configuration"* — predicts a hint here.

⭐ **The fix is one clause, not a fifth and sixth table row.** The condition the vendor actually
requires is *the PARENT of the shared common dir is itself inside a work tree*. State that and both
cases become predictable from the canon instead of surprises; keep the table as examples rather than
as the boundary. ⚠ And Case A deserves its own line, because it is the only configuration in which
the redirect points somewhere **wrong** rather than merely staying local.

**This is also the answer to claim 7.** The canon's presentation is better than the prose it
replaced — a heading that names the conditions, a bold ⛔, a ten-row table. The residual problem is
not presentation: the sentence a skimmer lands on (`:103-105`) is the one my two cases refute.

### H2 — A FOURTH trigger for the hint exists at 0.33.0. The canon says a fourth needs a vendor bump.

`.agents/skills/shared/handoff-path.md:29-31` (*"Three things print it"*), `:109-118` (triggers ② and
③), and `:124-125` — *"It does not claim the list of triggers is complete — it is the three the
vendor's own test enumerates, at version 0.33.0, and **a vendor bump can add a fourth**."*

**No vendor bump is needed.** Measured, 2/2, with a fresh-`TMPDIR` negative control and a
cache-removal control:

| step | config the session can see | result |
|---|---|---|
| 1 | `HOME=A`, no config file at all | **no hint** |
| 2 | `HOME=B`, `handoff_mode: per_session` | hint → `remember.<sid>.md` (trigger ②) |
| 3 | `HOME=A` again, **still no config anywhere**, same `TMPDIR` | ⛔ **HINT FIRES**, `remember.<sid>.md` |
| 4 | repeat of 3 | ⛔ **HINT FIRES** |
| 5 | `HOME=A`, **fresh `TMPDIR`** | no hint |

Cause, read from the vendor and confirmed from the artefact on disk: `log.sh:273-291` writes a
flattened config cache to `${TMPDIR:-/tmp}/remember-config-cache-<key>` where the key is derived
**from `REMEMBER_DIR` alone**, and the file's only identity line is `#REMEMBER_DIR=…`. Its source
list (`_remember_cfg_flatten_cache_sources`) includes `${HOME}/.remember/config.json` — but an
**absent** layer cannot be newer than the cache, so a cache published under one HOME is served to a
session whose HOME contributes no config at all. The artefact I recovered contains exactly one line:
`_RCFG_handoff_mode=per_session`. `config_into` then reads it through the `_REMEMBER_CFG_STATE = ok`
fast path (`log.sh:671-677`) and `PER_SESSION_HANDOFF` is set from a cached value.

⚠ **Honest bound.** Single-HOME config changes invalidate correctly — I ran the realistic sequence
(add the key, run, remove the key, run, delete the file, run) and the hint stopped immediately. What
is reachable is **two HOMEs over one `REMEMBER_DIR` sharing a `$TMPDIR`**: two users on a host where
`TMPDIR` is unset so both fall back to `/tmp`, or one user whose HOME changes. Narrow — and it is
still a hint the canon's model cannot explain, which matters because the canon's stated job is
answering *"why a path may have been printed at session start"*. A reader following it will inspect
three config layers, find nothing, and conclude the canon is wrong.

**Operational consequence worth one line in the canon:** the hinted path in that state is
`remember.<session-id>.md`, which the *next* session (cache gone) will not read — the original
"handoff with no reader" defect, resurrected by a cache.

### H3 — The mechanism this branch exists for is still described at SIX non-exempt live sites, none of them the canon. #282's own FAILS IF fires at HEAD.

The redesign collapsed two mechanisms. The third — **where a session handoff goes and why that path
is the one that gets read** — is the ⛔ RULE the whole branch is about, and it was not collapsed.
Measured with a **newline-folded** instrument, proved against a known positive the unfolded
instrument cannot see (`injected BEFORE identity and memory so it survives context-preview
truncation` wraps in the hook: folded → 1 match, unfolded → **0**):

| sub-claim | live non-exempt sites | in the canon? |
|---|---|---|
| `REMEMBER_HANDOFF` is the symbol | 6 (+ canon, + exempt dashboard) | partly — "TWO assignments" |
| emitted as `=== LAST HANDOFF ===` | 5 | ⛔ **no** |
| injected **before** identity and memory | 4 | ⛔ **no** |
| delivery fingerprinted on CONTENT | 4 | ⛔ **no** |

The six: `.agents/skills/handoff/SKILL.md:13`, `.claude/hooks/enforce-handoff-path.sh:64-67`,
`scripts/check-handoff-path.py:41-44`, `docs/plugins.md` (the RULE box),
`docs/process-rationale.md:353-356`, `docs/memory/a-vendored-line-number-has-no-owner.md`.

⚠ **They have not drifted yet — I checked all four sub-claims against the vendor and all four are
TRUE.** `=== LAST HANDOFF ===` is emitted first, ahead of `=== REMEMBER ===` and `=== MEMORY ===`
(measured with a handoff file present, isolated HOME and TMPDIR); the fingerprint is `cksum` of the
file content (`session-start-hook.sh:1640-1646`); `REMEMBER_HANDOFF=` matches exactly 2 assignments
against 23 bare-name lines, as the memory note says. **That is the point.** The branch's own thesis
is that six uncompared copies drift within one review round; this set is six, uncompared, and no
token in `CANONS` reaches it — `REMEMBER_HANDOFF` and `=== LAST HANDOFF ===` are not in either token
list, so `check-canonical-source.py` exits 0 over all six.

⛔ **And that makes #282 wrong about its own subject.** Its **FAILS IF** reads: *"a mechanism is
described at two non-exempt live sites and `check-canonical-source.py` exits 0."* That observation
is **already true at HEAD** — four to six sites, guard green. The row's narrative scopes the gap to
the two exemptions plus a missing `CANONS` entry and calls it *"a known bound, not an oversight"*;
its own falsifier says otherwise. Either the FAILS IF must be narrowed to the exemptions it actually
describes, or #282 is an open defect rather than an accepted bound.

**The fix shape** is a third `CANONS` entry (`handoff-rule`, tokens `REMEMBER_HANDOFF`,
`=== LAST HANDOFF ===`) with the canon carrying the four sub-claims the citing sites currently each
restate — not least because the canon is not even a superset of them today.

### H4 — The guard reads four directories and three extensions. The docstring and the commit message both claim "any non-exempt file".

`scripts/check-canonical-source.py:84-96` — `SEARCHED = ("*.md","*.py","*.sh")` over `.agents`,
`.claude`, `docs`, `scripts`. Measured population: **1,897 files**, identical under 3.12.9 and
3.14.4. Falsified on a copy, green control before and green re-control after each probe:

| planted copy (tokens, no citation) | guard |
|---|---|
| `.agents/x.md` — sanity, must catch | rc=1 caught |
| repo-root **`CLAUDE.md`** | rc=0 ⛔ **MISSED** |
| repo-root **`AGENTS.md`** | rc=0 ⛔ **MISSED** |
| repo-root `README.md` | rc=0 ⛔ MISSED |
| `docs/explainers/x.html` | rc=0 ⛔ **MISSED** |
| `docs/x.txt` | rc=0 ⛔ MISSED |
| `scripts/mutations/x.json` | rc=0 ⛔ MISSED |
| `.github/workflows/x.yml` | rc=0 ⛔ MISSED |
| `tests/x.md`, `lib/x.md` | rc=0 ⛔ MISSED |

⛔ **`CLAUDE.md` and `AGENTS.md` are the worst two to miss**: `CLAUDE.md` `@`-imports `AGENTS.md`,
`docs/dev-process.md` and `docs/plugins.md`, so they are the surfaces a session reads *first and
always* — and `docs/plugins.md`, a declared citing site, is reachable only through them.
`docs/explainers/**` is `.html` and this repo *generates* explainer pages, so a seventh copy there is
produced by a tool and read by a human, and the guard never opens it.

**The stated bound is the wrong bound.** The docstring's "⚠ EXEMPTIONS, STATED RATHER THAN HIDDEN"
names two exemptions and says drift inside them is not caught. The real bound is
`{.agents,.claude,docs,scripts} × {md,py,sh}`, which is nowhere stated and is far larger than the
exemptions. This is the repo's own *measure the population the code actually sees*, and the
corroborating tell is two directories over: **`EXEMPT`'s third alternative `\.remember/` is
unreachable** — the walk can only ever yield `.agents/`, `.claude/`, `docs/`, `scripts/`, so that
alternative matches nothing and no case covers it. The exemption list was written against an
imagined population.

⚠ Two more shapes the restatement rule misses, both falsified on the copy:

* **a citation pointing at a path that does not exist** — `REMEMBER_ROOT … See
  docs/nowhere/shared/handoff-path.md.` → rc=0. The test is `cite_token in body`, a 28-character
  substring; nothing checks the link resolves.
* **a sentence that names the canon in order to forbid it** — `REMEMBER_ROOT drifts. (never write
  shared/handoff-path.md here)` → rc=0.

`check-canonical-source.py` demonstrates this on itself: the inverted-restatement mutant reports
*"`scripts/check-canonical-source.py` restates handoff-path (carries `REMEMBER_ROOT`)"* — the file
carries **both** token sets and passes the live rule only because `CANONS` happens to contain both
canon paths as configuration data. A restating site is one substring from compliance.

A full paraphrase with no shared token is also missed (expected — the docstring says it counts
tokens, not mentions, and Codex is right that semantic agreement cannot be checked). That one I do
**not** file; see *Checked and found SOUND* for the measurement that makes the token proxy
defensible.

### H5 — F2 is false as written: the redesign does not GENERALISE `check-explainer-delivery.py`, it is a second implementation of the same rule beside it. The claim is written at three sites.

The claim: Phase 6 record F2 (*"The redesign generalises that guard rather than inventing a
mechanism"*), the commit message (*"this generalises it to any mechanism and any kind of citing
file"* — also at `check-canonical-source.py:16-18`), and `.github/workflows/ci.yml:301`
(*"Generalises the step above"*). Measured, both guards are live and independent:

| | `check-explainer-delivery.py` | `check-canonical-source.py` |
|---|---|---|
| table | `PAGE_SKILLS` (5 names), hardcoded | `CANONS` (2 dicts), hardcoded |
| canon marker | **none** | `<!-- canon: NAME -->` |
| citation token | `shared/explainer-delivery.md` | `shared/<name>.md` |
| restatement oracle | regex over **fenced code blocks** | token substring anywhere |
| population | `.agents/skills/*/SKILL.md` | 1,897 files, 4 dirs × 3 extensions |
| CI | its own step (`ci.yml:299`) | two more steps (`:305`, `:308`) |

And the older one is **invisible to the newer**: `.agents/skills/shared/explainer-delivery.md`
carries no `<!-- canon: -->` marker (grep: 0) and `explainer-delivery` appears in
`check-canonical-source.py` only at `:16` and `:114`, as prose — **never as a `CANONS` entry**. The
only two markers in the repo are `handoff-path` and `corpus-search`. So the delivery procedure can be
copied anywhere outside a `SKILL.md` with neither guard objecting, and `explainer-serve.py` already
appears at nine live non-review sites.

⛔ **This is the branch's own most-cited defect — *a second implementation of one rule drifts*, 17
recorded instances — committed at the guard layer, in the commit that exists to remove it.** It is
also the composition finding Phase 6 should have produced and did not (see M6): `dev-process.md` says
per-task review is structurally blind to composition defects, and this is one.

Either fold the explainer rule into `CANONS` (give `shared/explainer-delivery.md` a marker, keep the
fenced-code oracle as a second token kind) and delete the older guard, or drop "generalises" from all
three sites and say plainly that there are now two guards for one rule and why.

---

## Medium

### M1 — M3's withdrawal is NOT complete. The withdrawn sentence still stands at `docs/process-rationale.md:371`, beside the provenance it contradicts.

The commit message: *"M3 — 'each version was checked against the binaries the author happened to
have' is withdrawn in the canon, where it contradicted the source-only provenance beside it."*

Codex's M3 named two sites. One is genuinely fixed: `scripts/check-handoff-path.py` no longer carries
the GNU provenance at all (the whole block moved to the canon). The other is **not touched** —
`a8d92518`'s diff of `process-rationale.md` changes one line, and the sentence survives verbatim in
both the `-` and `+` sides:

> ⭐ Each version was checked against the binaries the author happened to have and published for
> every reader's

It sits in the same paragraph as *"the GNU leg came from GNU grep 3.12's source option table, not a
runtime probe, because that round could not build the binary"*. So the repo now contains a sentence
the canon explicitly declares **WITHDRAWN** (`corpus-search.md:64-66`) and still asserts at a live
non-exempt site — a withdrawal applied at one site and not its neighbour, which is finding r4 M1's
class and the exact shape this redesign was built to end. ⚠ The new guard cannot see it: "binaries
the author" is not a token.

**Fix:** delete or re-qualify that sentence at `process-rationale.md:371`, and amend the commit
record, since "withdrawn in the canon" is true of the canon and false of the repo.

### M2 — The second instance of "one claim written twice and drifting", inside the redesign and in the delivered code: `check-plan-code.py:240`.

> *"its canonical sources live in `.agents/skills/shared/` and **three of its five citing sites are
> skill files**."*

Derived from the live `CANONS` by importing it: **9 citing-site declarations across 6 distinct files,
of which exactly 1 is a skill file** (`.agents/skills/handoff/SKILL.md`). Per-canon the counts are 4
and 5, each with one skill file. No reading makes "three of five" true. The same sentence is in the
commit message — written twice, both wrong, nothing comparing them. That is claim 4's class, and the
copy in `check-plan-code.py` is in a file the new guard reads and cannot check, because it is a
number rather than a token.

⛔ **And the miscounted half is not merely wrong, it is unreachable.** I verified the entry's
operative claim by removing it on a copy: with `.agents/skills` staged, `--self-test` is **15/15**;
without it, **14/15**, the `the REAL repository is clean` case failing with *both canons MISSING*. The
control does go red — but **only** from the absent canon files, because `audit()` does
`if not path.is_file(): … continue` and never reaches the citing-site loop. The citing sites
contribute nothing to the red the comment offers them as the reason for.

**Fix:** `.agents/skills/shared/` holds the two canonical sources, whose absence alone reddens the
control; drop the citing-site clause.

### M3 — "33 commands green / 0 red" names no set, so it cannot be replayed. Same class as #283, one paragraph above it.

The commit message's verification section gives a count and an interpreter and no enumeration; the
Phase 6 record gives seven script names and no count. Measured for comparison: the population is
**45 `scripts/check-*.py`**; bare invocation under `/usr/local/bin/python3.12` with stdin closed,
90 s cap, gives **32 rc=0 and 13 not** (4 × rc=1, 8 × rc=2, 1 timeout). So 33 is a *selected* set of
commands (bare plus `--self-test` variants) drawn from a population containing reds, and a reader
cannot tell which 33. The fold discloses two exclusions by name, which is better than silence — but
the repo's own rule is that a figure needs its invocation, and #283 is filed four lines later for
precisely this.

**Fix:** list the invocations, as the Codex half did for its 29.

### M4 — Three review gates are red; the fold discloses one.

Disclosed: `check-review-rounds.py` (round 6's missing Claude half — correct, verified, and the brief
rightly says not to file it) and `check-memory-link.py` (rc=0 while reporting its corpus absent).
Undisclosed:

* `check-review-decision.py` → **`ROUND_OWED`** — `rounds=0 tree_reviewed=False scope=full-loop`.
* `check-review-recorded.py` → **`FAILED — 6 round(s) ran and guarded code was committed after every
  one of them`**, naming `scripts/check-canonical-source.py`, both canons,
  `.claude/hooks/enforce-handoff-path.sh`, `.agents/skills/handoff/SKILL.md`, `ci.yml` *(+4 more)*.

The second is red *because of* the redesign: 574 new lines landed after the last recorded round,
which is the exact condition that gate exists to catch. ⚠ **All three go green once this document
lands** — so the finding is the disclosure, not the reds: "33 green / 0 red" with one red excused
reads as a clean tree, over a tree where the gate that asks *has any round seen this code?* says no.

### M5 — The `EXAMINED_KEYS` correction is unprotected in the direction it was wrong in.

Re-derived rather than trusted: `check-fixture-variation.py scripts/check-canonical-source.py` prints
**"4 parameter(s) examined"**, matching the four pinned keys (`audit.canons`, `audit.root`,
`main.argv`, `main.root`) — which are exactly the parameters of `audit` and `main`. The corrected
value is right.

⛔ **But the guard cannot detect the staleness the fold reports fixing.** Falsified on a copy, green
control and green re-control:

| mutation to the pin | guard |
|---|---|
| **remove `main.argv`** (the exact earlier defect) | rc=0 — ⛔ **undetected** |
| add a bogus `main.bogus` | rc=1 — caught |

`check-fixture-variation.py:1174-1180` compares `pinned - keys` only; a key missing *from the pin* is
not the `new`-file path either, so under-pinning is silent. The fold presents re-derivation as what
established the value, which is true and is also all there is: the next parameter added to `audit` or
`main` with no pin update produces no signal. ⚠ The comment beside the entry says **"Three
parameters"** where the guard that reads it says four — minor on its own, and the third instance of a
number sitting beside the data it contradicts.

**Fix:** either say at the pin that the under-pinned direction is unguarded, or add the
`keys - pinned` direction for files already in `EXAMINED_KEYS`.

### M6 — The Phase 6 record is a record AND a justification, and the tell is which claims it verified by hand.

Claim 13 asks me to argue the other side. Here it is.

The record's own concession (`:115-117`) is that it did **not** reproduce the bare-repository-worktree
or submodule controls and wrote the redirect's conditions from round 6's table. The three things it
*did* verify by hand are F1 (the thrashing), the two "load-bearing" round-6 findings, and F4 (the
signature story). **Every hand-verified claim supports the redesign; the two it declined to reproduce
are the two that CONSTRAIN its scope.** That asymmetry is the signature of a justification, and it is
not hypothetical: I reproduced those two controls and the variation turned up H1's Cases A and B, which
change what the canon should say. `dev-process.md` says agent output is a lead, not a finding — verify
every load-bearing claim by hand — and F3, the stated residual risk, is accepted from round 6 verbatim.

Second tell: **the document is titled after the backlog item it filed** (*"(backlog #282)"*), and all
six findings are about the redesign's own premises — the problem, the precedent, the limit, the
signature, the residual, the undocumented decision. Phase 6 exists because per-task review is
structurally blind to **composition** defects, and asks *"what did we decide this milestone that isn't
written down?"*. F6 answers the second half. Nothing answers the first: there is no finding about how
the new canon directory composes with what is already in it — and H5 is sitting right there, one
`ls .agents/skills/shared/` away.

**In fairness**, these are record behaviours and they are real: provenance marked per finding, two
backlog items with FAILS IF on each, the roadmap updated in the same turn, and the owner's approval
reported as preceding the document. My verdict is not "it is a justification" but **"it is both, and a
Phase 6 review that produces no composition finding about anything other than the change that armed it
has done per-task review at milestone scale."**

**Fix:** reproduce the two scope-constraining controls (H1 does it; fold the result), and require of
this record at least one finding whose subject is not the redesign.

---

## Low

**L1 — the `/` `data_dir` row calls a library-load failure an abort of the mechanism.** The canon:
*"`/` | ⛔ outside the mechanism: the hook **ABORTS**, printing neither block"*. Measured: rc=**127**
and a single line, `session-start-hook: ERROR -- failed to source …/log.sh`. The hook did not reach
the mechanism; it failed to load. Codex classified this row **CANNOT RUN** (*"its absent hint is not a
negative behavioral result"*), and the canon adopts it as a tabled outcome. The adjacent sentence
("true of 13 of 13 rows where the hook completes") does exclude it from the claim, so this is wording,
not arithmetic — but the row should carry the rc and the reason, because this is the one row where
*why* is the whole content.

**L2 — the canon's explanation attributes two different branches to one.** *"The vendor compares
common-dir against git-dir and then **verifies a candidate main checkout** — a `.git` FILE alone is
not sufficient"*, offered for both the bare-repo and the submodule rows. Measured: for the submodule,
`git-dir == common-dir == <super>/.git/modules/sub`, so it returns at `lib-memory-dir.sh:120` and
**never reaches the verification**. Only the bare-repo case exercises it. The conclusion stands; the
reason given for half of it is the wrong half.

**L3 — a dead exemption.** `EXEMPT`'s `\.remember/` alternative can never match (population above);
no case covers it, and its presence implies the store directory is scanned.

**L4 — `_tracked_textfiles` reads untracked files and never consults git.** Demonstrated: an untracked
`docs/sneak-r6.md` was flagged. Harmless in CI, misleading as a name, and it means a local red can come
from a scratch file while a CI green says nothing about untracked content.

**L5 — the per-site character figures are characters, not bytes, and say neither.** Re-derived:
`process-rationale.md` and the memory note each move **−1,388 characters** / **−1,404 bytes**; the
claimed `1,691 → 303` is −1,388, so the figures are character counts. A reader reaching for `wc -c`
gets −1,404 and concludes they are wrong. `plugins.md` 785 → 421 = −364 matches its whole-file
−364 exactly; the skill, hook and guard-comment pairs are within 2/45/33 characters of their
whole-file deltas, consistent with the other edits in those files. All six are defensible — and none
names its instrument, which is #283's class applied to the fold's own numbers.

**L6 — "one UNDER its 260 budget" is still TIGHT.** `docs/plugins.md` is **259** lines (260 at base)
✓, and `check-docs.py:193` does budget it at 260 ✓. But `budget_warn_slack(260)` is **18**, so
`budget_verdict(259,260)` = `tight`, the same verdict class as `260/260`, and the live run prints
*"⚠ WARN — docs/plugins.md has 1 line(s) of runway"*. The fold lists `check-docs` as green (rc=0 —
correct, it is warn-only) without the warn on the file it edited.

**L7 — characters compared to lines.** *"Roughly 19,000 characters of parallel copy collapsed into 202
lines of canon."* The 202 lines ✓ (129 + 73) and the removed sum ✓ (6,957+3,812+4,133+785+1,691+1,691
= **19,069**). The canon is **11,188 characters**; the comparable sentence is 19,069 → 11,188 plus the
citations retained at each site.

**L8 — "round 7 is owed" has reached the tracked tree.** `docs/roadmap-to-launch.md`, in the block
added by `1231edcf`: *"**Round 7 is owed on that branch**"*. This is the known instance (commit header
vs its own verification section) propagated into a file a reader will act on. The tracked copy is
actionable: the debt at `1231edcf` was round 6's Claude half.

**L9 — the content-fingerprint claim is unconditional at five sites; the vendor has a byte-count
fallback.** `session-start-hook.sh:1640-1646` uses `cksum` when available and otherwise `wc -c`. Under
the fallback, two handoffs of equal length are indistinguishable, so *"fingerprinted on the handoff's
CONTENT, so reading one does not consume it"* holds only where `cksum` exists. `cksum` is POSIX, so
this is small — and it is five copies of one sentence, which is H3's point in miniature.

---

## Checked and found SOUND

* **The guard's three falsification cases all reproduce**, on a `tar` copy with `node_modules`
  symlinked, green control first and green re-control after each: a new doc carrying `REMEMBER_ROOT`
  → rc=1; the hook's citation removed (the r6 M1 shape) → rc=1; a duplicated canon file → rc=1 (both
  the `appears in 2 files` and the restatement finding).
* ⭐ **A retrodictive control the fold did not run, and it is the best evidence for the token proxy.**
  I rebuilt the pre-redesign state — the `dd595394` text of all six sites, dropped into a tree that
  has the canons — and ran the new guard: **rc=1 with 17 findings, flagging all six sites**. Every one
  of the six historical copies carries at least one `CANONS` token. So the guard would have refused
  the six-copy state it was built to prevent. That answers the "could a paraphrase evade it?" worry
  empirically rather than by argument: the actual corpus was not paraphrase-shaped.
* **`check-canonical-source.py --self-test` 15/15** under both 3.12.9 and 3.14.4, matching the
  docstring's declared 15; **`check-plan-code.py --self-test` 178/178** under both;
  **`check-selftest-counts.py`** green (52 scripts declare a count, each verified by running it).
* **Declared sum 1409** ✓, `EXPECTED_MUTATIONS["scripts/check-canonical-source.py"] = 1` ✓, pinned
  name list +1 ✓ — and the sum is asserted by a live case inside the 178.
* **The new mutation binds and kills through the case it names.** The anchor
  `if hit and cite_token not in body:` occurs exactly **once** in the delivered file; inverting it
  fails `a RESTATEMENT without a citation is detected` (plus two collateral cases), 12/15, over a
  15/15 control and a 15/15 re-control.
* **The `HARNESS_TREE` red-control claim holds** — 15/15 with `.agents/skills`, 14/15 without, failing
  on `the REAL repository is clean`. (The count beside it does not: M2.)
* **The refusal's DELIVERY, read rather than inferred.** Severing `SKILL.md` on the copy: guard rc=1,
  hook rc=**2**, stdout empty, and the stderr a blocked reader sees names `.remember/remember.md`,
  points at **both** canons, and contains **no claim-and-withdrawal pair**. M1 is fixed by
  construction, confirmed by reading the text. Intact control: rc=0, 0 bytes of stderr.
* **Wired into CI** — `ci.yml:304-308`, both the gate and its own cases, beside the explainer step.
  `check-rc-contract.py` and `check-ratchet-contract.py` are both green, so the new guard has a
  caller, a `--self-test`, and no fail-open handler.
* **No interpreter divergence in the walk.** `_tracked_textfiles` yields the same 1,897 files under
  3.12.9 and 3.14.4, and neither follows the `.claude/skills/*` symlinks into `.agents/skills` — so no
  double-counted canon and no `check-python-pin` class hazard here. (I went looking for one.)
* **The vendor sub-claims at the six H3 sites are all TRUE** — block order, the `cksum` fingerprint,
  two `REMEMBER_HANDOFF` assignments against 23 bare-name lines. H3 is structural, not an observed
  drift, and says so.
* **`docs/plugins.md`** 259 lines, 260 at base, budget 260 ✓. **Canons** 129 + 73 = 202 lines ✓.
* **Reviewed worktree remains clean**; one file written, nothing else changed; every mutation on a
  `tar` copy, never on this tree; no `git` command run in the main checkout.

---

## CANNOT RUN

**These are validation failures; treat each as NOT RUN, not as a pass.**

* **The `294/297` / `297/297` derivation (claim 9).** I tried four ways and failed: no script in
  `scripts/` declares 297 cases; `git log -S"297/297"` and `--grep="294/297"` return only this
  branch's own review and fold documents; `git grep -ln "297/297"` finds only the backlog row, the
  memory note and the r6 Codex review. **Verdict: not derivable from what the note states, so #283
  is correctly filed — not mis-filed.** To become replayable the row needs four things it lacks: the
  script, the exact invocation (including `--self-test`), the interpreter, and a SHA. ⚠ A fifth is
  needed for this particular figure: whether `294/297` is one script's self-test or a harness-wide
  control, and which `HARNESS_TREE` subset `scripts/ docs/ supabase/` was. Note the suite totals have
  moved since (the declared sum changed 1408 → 1409 in this very commit), so the ref is load-bearing.
* **A full `--mutate .` shard matrix.** Not attempted; per the brief this is a CANNOT RUN here, not a
  slow pass. I measured the one new mutation directly instead (above), which is narrower.
* **Host or UI delivery of the refusal.** I read the stderr bytes; that establishes what the hook
  wrote, never what a reader sees. Unchanged from every prior round.
* **`check-test-counts.py`** — rc=1, `jest-results.json` absent, and it says so itself.
* **`check-memory-link.py`** — rc=0 while reporting its corpus absent. Not a measurement.
* **`check-anon-exposure.py`** (rc=2, needs the container) and **`check-selftest-counts.py` under my
  90 s cap** (completed only in the longer background run) — both out of this review's subject, listed
  so the 32/45 figure in M3 is not read as a clean sweep.
* **`check-withdrawal.py` and `check-provenance.py` do not exist on this branch.** Absent is not
  passing — and M1 is a withdrawal defect those two would be the guards for.

---

## Instruments

Read first, in order: the r6 Codex review; `git log -1 --format=%B a8d92518`; `git show a8d92518`;
`git log -1 --format=%B 1231edcf`; the Phase 6 record. Then the delivered canons, guard, hook, skill,
`check-handoff-path.py`, the `plugins.md` RULE box, `process-rationale.md:350-395`, the memory note,
`ci.yml`, `check-plan-code.py`'s `HARNESS_TREE` and `EXPECTED_MUTATIONS`,
`check-fixture-variation.py`'s `EXAMINED_KEYS`, `check-explainer-delivery.py`, and backlog rows
#282/#283.

**Vendor controls.** The installed `remember` **0.33.0** (one match under
`~/.claude/plugins/cache/claude-plugins-official/remember/*/scripts/`, discovered with the `ls` form
the canon prescribes). `lib-memory-dir.sh` (385 lines), `lib-memory-context.sh:84-96` (the
`REMEMBER_ROOT` derivation — all five branches as tabled), `session-start-hook.sh:1164-1176`,
`:1544-1551`, `:1640-1646`, `log.sh:273-291` and `:633-700`, `lib-env-cache.sh:150-191`.

**Every hook execution** ran the real 0.33.0 hook under `env -i` with an isolated `HOME`, a
`SessionStart` JSON payload on stdin, and `=== REMEMBER ===` asserted as a positive control on every
row that is claimed to complete. ⚠ **After finding H2 I re-ran the four canon rows and both new cases
with an isolated `TMPDIR` as well**, because the cache I found can fabricate a hint — all six
reproduce, so H1 does not rest on it. Git fixtures built from scratch per case: ordinary repo, linked
worktree, worktree-of-worktree, subdirectory, moved checkout ± `worktree repair`, bare-repo worktree,
bare-repo worktree nested in another work tree, `git -c protocol.file.allow=always submodule add`, and
`git init --separate-git-dir`.

**Every guard execution** used `</dev/null` (`check-selection-card.py` hangs otherwise) and ran under
**both** `/usr/local/bin/python3.12` (CI's pin) and `python3` 3.14.4 wherever an interpreter could
matter. **Every mutation was applied to a `tar` copy** (`--exclude=.venv --exclude=node_modules
--exclude=.git`, 3,008 files, `node_modules` symlinked at the main checkout), with the control proved
**rc=0 / 15-15** before any sever and a re-control after; the reviewed worktree was never modified.

**Prose counts were taken newline-folded** (`tr '\n' ' '`) and the instrument was proved against a
known positive the unfolded form cannot see (H3). **Every `grep` was `/usr/bin/grep` explicitly.**
⚠ One self-correction: my first `EXAMINED_KEYS` measurement read `$?` after a pipe and reported rc=0
on a failing gate; re-measured without the pipe, and M5's table is the corrected run.

No `git` command ran in `/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud`.

---

## Where I disagree with the Codex half

* ⛔ **Its *Checked and found SOUND* item "No fourth trigger or suppression on a completing controlled
  row was established" is refuted.** H2 establishes a fourth, at 0.33.0, reproduced 2/2 with a
  fresh-`TMPDIR` negative control. Codex enumerated all eight truth-table combinations of the
  *emission block*, which is sound as far as it goes — the gap is that `PER_SESSION_HANDOFF` can be
  set from a `$TMPDIR` cache rather than from any config the session can see, so the truth table was
  exercised over the wrong input space.
* ⛔ **Its H1 table is itself overbroad in the way H1 accuses the clause of being.** Codex published
  *"Bare-repository worktree, default configuration | **No hint; store remains local**"* as a flat
  result, the canon copied it as a flat row, and Case A refutes it. I reproduce Codex's measurement
  exactly — and a bare repo is only "local" when its parent directory is not inside a work tree, a
  condition neither Codex nor the canon states. The reviewer that found the conditionality published
  the one row that needed a condition without one.
* **Its M3 is now half-fixed and should be re-scoped, not re-filed.** `check-handoff-path.py:68/:73`
  no longer exists in that form; only `process-rationale.md:371` survives (M1). The commit message
  treats the whole of M3 as closed.
* ⭐ **I side with Codex against the canon on the `/` row.** Codex filed it CANNOT RUN; the canon
  tables it as a behaviour. rc=127 from `failed to source log.sh` is a load failure (L1).
* **Where I confirm it.** Its thrashing verdict, its six-row causation table, its five derivation
  branches, its fourteen `data_dir` rows, the copy-only enforcement discipline, and
  `check-explainer-delivery.py:45` as the structural precedent — all hold, and the last one is the
  seed of H5: Codex pointed at the precedent, the redesign cited it, and nobody checked whether the
  precedent was now a duplicate.

---

**Verdict: NOT CONVERGED.** The redesign's machinery is sound and better evidenced than the fold
claims — H5's duplicate aside, the guard refuses every shape the fold tested, kills its mutation
through the named case, and would have refused the historical six-copy state. What is not closed is
the thing round 6 said it could not close: **the surviving single description is wrong in two
configurations and silent about a third trigger, and the mechanism the branch exists for was never
collapsed at all.** Round 7 should fold H1–H3 first; H4 and H5 are the structural pair, and H5 is the
one that will otherwise be rediscovered as a seventh instance of the class this branch is about.
