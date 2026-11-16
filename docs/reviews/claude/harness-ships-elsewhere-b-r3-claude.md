Reviewed head: 3bd59f0d6a9afb67aab70a3a115ff0a3b8c8fffa

# Adversarial review — `harness-ships-elsewhere` slice B, round 3 (Claude half)

**Subject:** PR #594 at `3bd59f0d`. The round-2 fold is `f065e2ea` (code) and `1196ae9d`..`cec1f444` (prose, the
coordinator record, the dashboard entry). I diffed it against the round-2 head `08dc620b`.
**Mandate:** refute "every round-2 finding is closed, and round 3 finds nothing caused by the fold in `staging`".
Every fixture below is a temporary git repository I built in my scratch space. Nothing under `.claude/plans/` was
read. The "old" runs used `08dc620b`'s `mkt_stage.py` and `mkt_isolate.py`, extracted to a scratch directory.

## Verdict: **NOT CONVERGED**: 1 BLOCKER, 0 MAJOR, 5 MINOR

**The round-3 bet is LOST.** F2 is caused by this fold's folded compare in `staging`. `fold` uses NFKC, a
compatibility normalisation that APFS does not apply, so names that APFS keeps distinct are refused as aliases.
Under the coordinator's own falsifier ("the folded compare") this is the second consecutive round with a fold-induced
finding in `staging`, so **THRASHING arms Phase 6** for that component. The fix for F2 is measured below: it removes
every over-refusal in the corpus and adds no misses.

**The BLOCKER (F1) is not fold-induced.** It is in `08dc620b` as well. It is a private-file leak that the docstring
says cannot happen ("refused … however declared"). It needs a repository whose `.claude` is a tracked link, and this
repository's `.claude` is a real directory with plans gitignored (`.gitignore:103`). So it is reachable by
construction only, not in today's tree. It meets the brief's BLOCKER definition literally. Whoever folds this round
should weigh that.

## Gates run (results)

| Check | Result |
|---|---|
| `python3 scripts/mkt_stage.py --self-test` | `LIVE ok: …claude plugin validate…; not in the count below` / `89/89 self-test cases passed`, rc 0 (read from `$?` directly, no pipe) |
| `python3 scripts/mkt_isolate.py --self-test` | `73/73 self-test cases passed`, rc 0 |
| APFS identity vs `fold` (root volume, APFS case-insensitive): every single-code-point substitution (U+0001..U+10FFFF, minus surrogates and `/`) at each position of `.claude/plans`, `os.path.isdir` vs `fold(s) == fold(".claude/plans")` | NFKC `fold`: **0** FS-equal-but-not-folded (no leak), **401** folded-but-FS-distinct (over-refusal). Candidate `NFC(casefold(NFD(s)))`: **0** and **0** |
| HFS+ ignorables (U+200B/C/D, U+FEFF, U+00AD) inserted into `.claude` on APFS | none resolves to the directory, so on APFS the docstring's stated bound does not bite |

## Round-2 closures, re-attacked with the original breaking inputs

| Finding | Result at `3bd59f0d` |
|---|---|
| Codex 1: `.CLAUDE/PLANS/secret` | REFUSED (`… is under .claude/plans (.CLAUDE/PLANS)`). Closed. Fullwidth `．ｃｌａｕｄｅ` and a trailing space are not the directory on APFS (`does not exist`), so no leak |
| Codex 2: untracked parent dir link `alias -> target`, declare `alias/data` | REFUSED (`not tracked by git (alias)`). Closed |
| Codex 3: tracked `good.py` plus an index entry `bad-\xff.py` | STAGED `good.py`. Closed |
| Codex 4: world `python3 -> /usr/bin/python3`, `run_isolated(python3 -c …)` | CANNOT RUN (`sys.path reaches outside … CommandLineTools …/site-packages`; `installed distributions … pip, setuptools, wheel`). Closed. Cost: `measured` 0.10–0.12 s per run here |
| Codex 5: keychain sentence | The baseline now says only that neither tool reported an identity, and that keychain access is UNVERIFIED. Closed |

Further attacks that held: a tracked link to an untracked file (REFUSED); a link loop `a->b->a` (REFUSED, looping);
relative and absolute links out of the repository, including `<top>/../G/x` (REFUSED); a link `cl -> .claude`,
declared as `cl/plans/secret` or as skill `cl` (REFUSED, private); a tracked link to a directory that holds an
untracked `.DS_Store` (REFUSED, named). A hard link to a private file ships (`p/h=PRIVATE`). The docstring states
this as a bound, and the bound is honest.

## Findings

| # | Sev | file:line | Breaking input → wrong output | Fix | fix_induced | component |
|---|---|---|---|---|---|---|
| F1 | **BLOCKER** | `scripts/mkt_stage.py:181` (`_real`'s PRIVATE check), docstring `:28` | `dot/plans/secret` = `PRIVATE`, tracked; `.claude -> dot` a TRACKED link. Declare `files=[".claude/plans/secret"]` → **STAGED `p/.claude/plans/secret=PRIVATE`**. Skill `.claude/plans` → **STAGED `p/skills/plans/secret=PRIVATE`**. The walk replaces `.claude` with its target before the prefix `.claude/plans` is ever formed, so it checks only `.claude`, `dot`, `dot/plans`, …. `08dc620b` stages both too (its `lex`/`real` are both `dot/…`) | (a) refuse when the DECLARED `rel` is `_under` a PRIVATE path, before walking (closes both inputs). (b) Resolve each PRIVATE entry through the same walk to its link-free spelling (`dot/plans`) and exclude that too, so `files=["dot/plans/secret"]` is refused as well. Add a red case for each | false | staging |
| F2 | MINOR | `scripts/mkt_isolate.py:148` (`fold` = NFKC + casefold), used by `scripts/mkt_stage.py:94`, `:142` | Tracked `x².md` (`b`) and `x2.md` (`a`), distinct files on APFS (`samefile` False); `files=["x².md","x2.md"]` → **REFUSED `two declarations land on x2.md`**. The same for `Ａ.md` + `A.md`. `08dc620b` STAGED both. The exhaustive corpus above finds 401 such over-refusals at `_under(…, ".claude/plans")` alone. `fold`'s docstring says it compares names "as a case-insensitive, normalisation-insensitive filesystem (macOS's default)" does, and APFS does not apply compatibility forms | Fold with canonical, not compatibility, normalisation: `unicodedata.normalize("NFC", unicodedata.normalize("NFD", s).casefold())`. Measured on the same corpus: 0 misses, 0 over-refusals. Add red cases for `x².md`+`x2.md` staging, and keep the `.CLAUDE/PLANS` case | **true**: the fold introduced NFKC folding at the collision check, `_under` and `_reaches` | staging |
| F3 | MINOR | `scripts/mkt_stage.py:206` (exact `inner not in tracked`), reached from `_tree` `:218` | A skill dir holding `café.md` created with an NFD name on disk; `git add` under `core.precomposeunicode=true` (macOS default) records NFC. `os.listdir` returns NFD → **REFUSED `sk/café.md is not tracked by git`**, a tracked file wrongly refused. Declaring the NFD spelling in `files` is refused the same way. `08dc620b` refuses identically | Compare tracked membership under canonical normalisation (NFC both sides). APFS already treats the two spellings as one file, so this does not widen what is accepted beyond the filesystem's own identity | false | staging |
| F4 | MINOR | `scripts/mkt_stage.py:114` | `ag/skills/s/SKILL.md` tracked, `.agents -> ag` a tracked link; `files=[".agents/skills/s/SKILL.md"]` → STAGED at `p/.agents/skills/s/SKILL.md`. The SKILLS_HOME exclusion tests only the link-free `real`, never the declared `rel`. Not a leak: the file is tracked and not private. It lands in the wrong place. `08dc620b` behaves the same | Test `_under(rel, SKILLS_HOME)` as well as the real path. This is the same shape as F1(a) | false | staging |
| F5 | MINOR | `scripts/mkt_isolate.py:436`, probes `:314`, `:341` | `run_isolated(world, argv, cwd, timeout=5)` now runs `measured` first. Each probe has its own fixed `timeout=60`, so a hung probe blocks the caller for up to 60 s per allow-listed Python, plus 60 s for git, before the caller's 5 s budget even starts. Not observed hanging: in the normal case it costs 0.1 s | Pass a bound derived from the caller's `timeout` to `measured`, or state the extra worst case in `run_isolated`'s docstring | true | isolation |
| F6 | MINOR | `docs/marketplace/isolation-baseline.md:27` | "refuses one that holds a site-packages entry or anything outside the world": `foreign_paths` deliberately ALLOWS the stdlib, which lies outside the world (line 16 says "outside the world and its stdlib"). The sentence states a stricter check than the code runs | "… anything outside the world and its stdlib, or any installed distribution" | true | docs |

## Prose (question 5)

- The baseline's new sentences at lines 17-19 ("repeats the env/layout checks and the two measured ones … HOME and
  bindir entry checks and the explainer port are preflight's alone"; "compared … FOLDED") match `run_isolated` and
  `_reaches` as written. The phrase "Unicode form" hides F2: what the code folds is compatibility form.
- The bound at line 27 ("only the allow-listed Pythons in `bin/` are asked") understates it. Only allow-listed
  names that match `^python[\d.]*$` (`mkt_isolate.py:54`) are asked, so an interpreter allow-listed under another
  name is not probed. This is a wording point, not a separate finding.
- The coordinator record says "Inclusions … stay exact on purpose". That holds for the code. F3 shows that an exact
  inclusion against git's precomposed index refuses a tracked file. The refusal is safe, but the record does not
  state it as a bound.
- `mkt_stage.py`'s bound "an alias that is neither case nor Unicode form (HFS+'s ignorable characters) is not
  folded" is honest. On this APFS volume no ignorable resolves to the directory.

## Phase 6 note

The falsifier the coordinator recorded is "any round-3 finding whose cause is … the folded compare". F2's cause is
that compare (`fold`'s NFKC), in `mkt_stage.py`'s collision check and `_under`. Round 2 carried fold-induced X3 in
`staging`, and round 3 carries F2 in `staging`. That is two consecutive rounds, which is the arming condition in
`docs/dev-process.md` → *THE ARMING CONDITION IS THRASHING*. F1, F3 and F4 are older holes in the same walk. One
redesign question is worth putting to the review: should PRIVATE and SKILLS_HOME be checked against the declared
spelling, the link-free spelling, AND the private directory's own link-free spelling, as one rule?

VERDICT: NOT CONVERGED
