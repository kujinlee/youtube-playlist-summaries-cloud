# Architecture review — detector 2's `install-root` rule in `scripts/check-publishability.py`

Phase 6, convened on THRASHING. Subject `marketplace-task16` (plan Task 16 of
`docs/superpowers/plans/2026-11-11-marketplace-inventory.md`), branch `marketplace-task16`, reviewed head
`1792bd2d`, draft PR 613. Decision log (`docs/reviews/decision-scheme/decision-log.jsonl`, subject
`marketplace-task16`): accrete lost at round 2, redesign lost at round 3; the ladder's next route is `split`.

Every claim below is tagged **[M]** (measured: I ran it, the command or script is named) or **[I]** (inferred from
reading). Prototypes and the corpus live OUTSIDE the repository, in the session scratch directory `t16p6/`
(`harness.py`, `candidates.py`, `corpus.py`, `run_corpus.py`, `run_live.py`, `run_selftest.py`); nothing tracked was
edited except this file. Python 3.14.4.

## The verdict, first

The thrashing is a MECHANISM defect, not a branch-coverage defect, and a redesign removes it. The rule decides
"is this root handed on?" in two decoders that read the same parent node in opposite directions and disagree, and it
has four independent ways to answer with silence. Each fold added a form to one decoder and thereby opened a silent
path through the other. **Recommended: replace the derivation/judgement pair by ONE upward walk from every mention
of a file-anchored value, with ONE decoder of "what does this parent do with this child", in which silence is a
closed list and a name that cannot be followed is reported at its binding.** Names are followed by a file-wide
census, so the rule stops depending on `_Scopes`. `symtable` (b) and a split (d) do not remove the class.

## 1. The arming evidence — per finding, which fold caused it

| Round | Finding | Input | Caused by | Component |
|---|---|---|---|---|
| r1 Codex MAJOR | names bound file-wide | `check-plan-code.py` `_sp.run = _real` shape | the Task 16 build | name following |
| r1 Codex MINOR | every use counted | `relative_to(ROOT)`, a comparison | the build | judgement |
| r1 Claude M3 | `..` form, annotated binding | `Path(__file__).parent / ".."` | the build | derivation |
| r2 Codex X1 | inert list hides a handed-on root | `cwd=f"{ROOT}"`, `os.chdir(os.path.relpath(ROOT))` | **r1 fold** (the inert list) | judgement vs derivation |
| r2 Codex X2 | `nonlocal` filed one level out | a-b-c `nonlocal root` | **r1 fold** (`_Scopes`) | name following |
| r3 Claude M1 | keyword spelling hides the root | `os.chdir(os.path.relpath(path=ROOT))` | **r2 fold** — a regression: `[]` at HEAD, reported at `98efda03` | judgement vs derivation |
| r3 Claude M2 | second path in an f-string lost | `f"{HERE}:{ROOT}"` | **r2 fold**, partly (code the fold added; output was `[]` before too) | derivation + outer skip |
| r3 Claude m1 | walrus in a comprehension mis-scoped | a-b-c with `[(root := 1) for ...]` | **r2 fold** — a regression | name following |
| r3 Claude m2 | `//` tail read as absolute | `open(f"{ROOT}//docs/x.md")` | **r2 fold**, partly | derivation |
| r3 Claude m3 | chained assignment hides the root | `R = X = ROOT` | no — r1 code | binding |
| r3 Claude m4 | committed scan line numbers | — | no — the master merge `70fefa79` | record |

Two consecutive rounds (r2, r3) carry findings caused by the previous round's fold, in one component. **[M]** — I
re-ran every input above against three copies of the script (`07664d06` pre-fold, `98efda03` r1 fold, HEAD); the
"caused by" column matches the round documents in all rows.

## 2. Can a redesign remove it? — the mechanism

Read at HEAD (`scripts/check-publishability.py`, symbols not line numbers):

1. **Two decoders of one fact.** `_from_file` walks DOWN from an expression and answers "is this a path derived
   from `__file__`"; `_inert` walks UP one step from a node and answers "does the parent merely look at it". Both
   must decode the same parent (a call, its positional and keyword arguments). `_from_file` reads `args[0]` only;
   the r2 fold taught `_inert` to step through a keyword. M1 is exactly that disagreement.
2. **A skip that trusts the outer expression.** `_install_root_uses` skips a node whose parent is itself from-file,
   assuming the parent is derived from THIS node. `_fstring_path` returns the first embedded path only, so for
   `f"{HERE}:{ROOT}"` the parent is from-file at HERE's level, the `ROOT` piece is skipped, and the parent is then
   dropped because its level is not the install depth. M2.
3. **Four silent exits.** A node yields no finding when (i) its name is not followed (stores disagree, chained or
   augmented assignment — m3), (ii) the parent is in the inert lists, (iii) the outer-skip fires, (iv) the level is
   not the install depth. The comment block "THE DERIVATIONS, LISTED" states the direction as "an omission in
   either list therefore errs toward a FINDING, never toward silence". **[M]** that sentence is false at HEAD:
   M1, M2 ×3, m1, m2, m3 ×3 are all omissions that end in `[]`.
4. **The silence reaches the live tree.** **[M]** `scripts/check-plan-code.py` has no `install-root` finding in HEAD's
   live scan, although `_repo = pathlib.Path(__file__).resolve().parent.parent` at
   its line 6355 is handed to `load_manifests(_repo)`. `_Scopes.stores` for the enclosing function holds three
   stores of `_repo`: lines 6355 and 8224 (the root) and a tuple-unpack at 4670 (no value). The stores disagree, so
   the name is not followed, so nothing is reported. The stated bound "a name whose stores disagree is not
   followed … a miss, by design" (limit L5 in `docs/marketplace/experiment-tier-a.md`) hides a real hand-on in a
   shipped file.

A branch-coverage defect would be fixed by adding the missing form. Here every added form is added to ONE decoder
and changes what the OTHER one's silence means; that is why r1's fix produced r2's findings and r2's produced r3's.
The structure, not the list, is what thrashes — so yes, a redesign can remove it. **[I]**, supported by §3.

## 3. The candidates, measured

**The corpus** (`corpus.py`): 49 inputs — every r1–r3 finding input, the r2 negatives, r3's "checked and holding"
list, and 11 neighbours this review added (keyword spelling of another derivation, `relpath` with a start, a star
import, an unused exported root, a shadowing parameter, …). Each is run as a fixture whose header binds `ROOT` two
levels up and `HERE` one level up, at install depth 2. Scores: EXACT (the answer the review called right), COARSE (a
finding names the root, on another line or with target `.`), MISS (wanted a finding, got none), FALSE (wanted none,
got one).

**The live tree:** the 28 shipped `.py` files the scan resolves from `docs/marketplace/components.json` (348 files in
all; 24 of the 28 mention `__file__`). HEAD baseline: 56 `install-root` findings in 20 files.

| Candidate | Corpus EXACT | COARSE | MISS | FALSE | Live findings | Live vs HEAD |
|---|---|---|---|---|---|---|
| r1 fold (`98efda03`), for reference | 30 | 2 | 15 | 2 | 56 | — |
| **HEAD** — and **(d) split**, which changes no behaviour | 38 | 0 | **11** | 0 | 56 | +0 −0 |
| **(b)** HEAD with `_Scopes.owner` answered by `symtable` | 39 | 0 | 10 | 0 | 56 | +0 −0 |
| **(c)** one upward walk, one decoder, names by `_Scopes` | 46 | 1 | **0** | 2 | 58 | +3 −1 |
| (b)+(c) upward walk, names by `symtable` | 47 | 0 | 0 | 2 | 58 | +3 −1 |
| **(a0)** narrowed claim, no name followed at all | 10 | 29 | 0 | 10 | 21 | +18 −53 |
| **(a1)** upward walk, names by a file-wide census — RECOMMENDED | 44 | 3 | **0** | 2 | 58 | +5 −3 |

All rows **[M]** (`run_corpus.py`, `run_live.py`).

- **HEAD's 11 misses** are r3 M1, M2 ×3, m1, m2, m3 ×3, and two neighbours (`dirname(p=…)`, an exported root never
  read in its own file).
- **(b) `symtable`** fixes one of the eleven (m1). It cannot touch M1, M2, m2, m3: those are not scope questions.
  Its table shape is version-dependent: **[M]** on 3.14 a comprehension has no symtable child (inlined) and every
  function gains an `__annotate__` child, so an AST-to-symtable mapping written today is a second moving part.
- **(d) split** is behaviour-preserving by definition, so it scores as HEAD. The two MAJORs of r3 are interaction
  defects BETWEEN derivation and judgement; a split adds a seam exactly there. It is the ladder's next route and the
  evidence is against it.
- **(a0)** — report every mention outside an allowlist, follow no name — loses every named target on the live tree
  (53 of 56 findings become 18 `.` findings at binding lines) and 4 of the 6 components the tier-A experiment hit
  keep only one coarse finding, 2 keep none (`regen-pages`, `goal-tree`). The claim is narrowed past usefulness:
  the scan could no longer say WHICH project path a component needs. Rejected.
- **(c) and (a1)** have zero misses. Their two FALSE rows are the same two inputs and are the design working as
  stated, not errors: a root bound to a name that is then rebound to something else (the r2 X2 a-b-c input, and a
  root shadowed by a parameter) is reported at the BINDING line as `.` — HEAD's "stores disagree, not followed"
  silence replaced by a finding. The parameter's own line is NOT reported in either.
- **Live differences, read line by line [M]:**
  - `+ scripts/check-plan-code.py:6355 .` — the hand-on of §2 item 4. A gain, both (c) and (a1).
  - `+ scripts/check-surface-recall.py:519 .claude/hooks/does-not-exist.sh` — `HOOK.parent / "does-not-exist.sh"`
    in a self-test; HEAD's `_from_file` refuses `.parent` on a path that already has parts. An over-report of the
    kind limit L5 already states for fixture strings.
  - `scripts/gen-dashboard.py` `docs/dashboard-entries.md` moves from line 3305 to 3297: a
    `globals()["STORE_DEFAULT"] = …` store is now a reported use, not a followed rebinding. Same target.
  - (a1) only: `scripts/check-docs.py` `docs/backlog.md` 369→368 and `docs/roadmap-to-launch.md` 563→562 — a local
    `path` is reused file-wide, so it is not followed and the finding lands on its binding, one line earlier, with
    the SAME target (the binding already carries the whole derived path).
  - No named target is lost by (c) or (a1). All six components the tier-A experiment hit (`regen-pages`,
    `goal-tree`, `gen-backlog-page`, `gen-features-page`, `gen-goals-page`, `gen-dashboard`) keep exactly their HEAD
    finding counts (2, 4, 3, 7, 3, 2).
- **The script's own self-test with the candidate patched in [M]** (`run_selftest.py`, worktree script loaded
  in-process, `_install_root_uses` replaced): 118 of 121 cases pass under both (c) and (a1). The three that change
  are named in §4.4.

## 4. The recommendation and its build spec

**One structure: the mention walk (a1).** Why (a1) over (c): three of the eleven findings (r1 MAJOR, r2 X2, r3 m1)
lived in scope resolution. (c) keeps the rule dependent on `_Scopes`, so that class can recur as wrong lines or
targets, and m1 itself stays wrong ((c) scores it COARSE). (a1) removes the dependency; its measured cost is two
same-target line shifts on the live tree and three coarser fixture answers. `_Scopes` and `_Bound` STAY in the file:
detector 6 (`_homes`) uses them.

### 4.1 The invariant (the thing a reviewer checks instead of a list of forms)

> Every MENTION of a file-anchored value — the `__file__` name, or a load of a followed name — is walked upward.
> At each parent ONE function answers exactly one of **DERIVE** (the parent is a path value again: continue),
> **BIND** (a one-name assignment), **INERT**, **LEFT** (an absolute part left the tree), or **USE**. USE is the
> default. A finding is silenced only by INERT, LEFT, a level that is not the install depth, or a held target —
> four closed, local tests. **Following a name may move a finding's line or sharpen its target; it can never
> remove one:** a BIND whose name is not followed is reported at the binding.

### 4.2 What is deleted

`_from_file`, `_fstring_path`, `_inert`, `_rebinds`, the outer-from-file skip inside `_install_root_uses`, and
`_install_root_uses`'s use of `_Scopes`/`_Bound`. The comment block "THE DERIVATIONS, LISTED" is rewritten to state
§4.1. `FILE_OF`, `SAME_PATH`, `RELATIVE`, `EXISTS`, `EXISTS_CALLS`, `_placed`'s `..` arithmetic and `_dotted` are
reused. If `_from_file` has another caller, keep it for that caller only and say so.

### 4.3 What replaces it (signature unchanged: `_install_root_uses(tree, parent, depth, held)`)

1. **A value** is `(level, parts)`. `__file__` is `(0, ())`. Normalising climbs `..` (pop a part, else `level+1`),
   drops `.` and empty segments, and returns LEFT on a part that starts with `/`.
2. **`_step(node, value)` — the single decoder**, reading `parent[node]`:
   - attribute `.parent` → DERIVE one up; `.parents[k]` (integer constant) → DERIVE `k+1` up;
     `.resolve()`/`.absolute()` with no arguments → DERIVE same; `.joinpath(literal…)` → DERIVE joined, a
     non-literal part → USE; a method in `RELATIVE`, or in `EXISTS` when the value has no parts → INERT;
     any other attribute → USE.
   - `/` with the node on the LEFT and a literal right → DERIVE; otherwise USE.
   - a comparison → INERT.
   - a formatted value inside an f-string → DERIVE to the f-string, **per mention**: when the mention is the first
     piece and exactly one constant piece follows, starting with `/`, join that tail with ALL leading slashes
     stripped (m2); in every other position the string carries the path unchanged. Two paths in one f-string are
     two walks (M2).
   - an argument of a call → looked up in ONE role table keyed `(callee, parameter)`, where a parameter is named by
     position AND keyword in the same row, so the two spellings cannot differ (M1):

     | Callee | Parameter | Role |
     |---|---|---|
     | each of `FILE_OF` | 0 | DERIVE same, when it is the only argument |
     | `os.path.dirname` | 0 / `p` | DERIVE one up, only argument |
     | `os.path.join` | 0 / `a` | DERIVE joined with literal parts; a non-literal part or any keyword → USE |
     | `os.path.relpath` | 0 / `path` | no start: DERIVE same. A start that is itself file-anchored: INERT. Any other start: USE |
     | `os.path.relpath` | 1 / `start` | INERT |
     | each of `EXISTS_CALLS` | 0 / `path` | INERT when the value has no parts, else USE |
     | `print` | any | INERT |
     | either side of a `RELATIVE` method | any | INERT |

     A callee or parameter not in the table → USE.
   - the value of `name = …` or `name: T = …` with exactly one Name target, outside a class body → BIND.
   - everything else (chained or tuple or augmented assignment, subscript store, return, walrus, a container, a
     class-body field) → USE (m3).
3. **The name census, file-wide, no scopes.** A name is FOLLOWED when every identifier-bearing occurrence of it in
   the file other than a load is a one-name assignment (default-deny over every string field of every AST node:
   parameters, `for`/`with`/`except` targets, imports, `global`/`nonlocal`, `del`, a `match` capture, a function or
   class of that name all disqualify), every such assignment BINDs the same value, and the file has no
   `from … import *`. A rebinding from itself (`R = R.resolve()`) is checked by assuming the value and verifying.
   A name bound to one string literal everywhere is a literal part, by the same census.
4. **Reporting.** USE at the install depth, target not held → finding at that node's line, first line per target
   (as today). A BIND whose name is not followed → finding at the binding. A followed name with no load in the
   file → finding at the binding (an exported root).

The prototype (`candidates.py`, `walkup(mod, "pooled")`, about 200 lines, replacing roughly 120) is a LEAD for
the implementer, not code to paste: it was never reviewed. Its `relpath` rule is cruder than the table row above
(any explicit start → INERT); **[M]** the two extremes (always INERT, always USE) give identical live results, so
the row above cannot change the live scan.

### 4.4 Cases, mutations and limits that change

- **Self-test — three cases change expectation [M]** (run under (a1)):
  - "S1 (r1 m2, Codex MAJOR): a name is looked up in Python's scope…" — fixture `scope_like` reuses `x`, `y` and
    `ROOT` as a local, a rebound name and a parameter. Rewrite the fixture so each claim has its own name, and assert
    the new rule: a reused name is reported at its binding; the non-root function's line is never reported.
  - "S1 (r1 m2): a `global` rebinding is the module's…" and "S1 (r2 X2, Codex MAJOR): `nonlocal` rebinds the
    NEAREST…" — each gains a `.` finding at the binding of the root that is rebound elsewhere (lines 2 and 3 of
    their fixtures). The `nonlocal`/`global` distinctions these cases drew no longer exist for this rule; keep the
    scope fixtures for detector 6 if it needs them, and replace the install-root assertions by ONE case: "a root
    whose name is rebound anywhere in the file is reported where it is bound".
- **New cases, one per r3 finding** (inputs verbatim from `docs/reviews/claude/marketplace-task16-r3-claude.md`):
  M1 `relpath(path=ROOT)`; M2 the three two-path f-strings plus the swapped control; m2 the `//` tail; m3 the two
  chained assignments and `R = ROOT; R /= "docs"; open(R)`. Plus: `dirname(p=…)`; an exported root never read; the
  `check-plan-code.py` shape (same name bound to the root twice and unpacked once in one function).
- **One invariant case, not a form case:** for every row of the role table, drive it positionally AND by keyword in
  one case and assert the two answers are equal. This is the case that would have caught M1 before a reviewer did.
- **Mutations:** `scripts/mutations/check-publishability.json` has 237 entries; **[M]** by text search 4 anchor in
  `_from_file`, 1 in `_fstring_path`, 1 in `_rebinds`, 1 each on `_install_root_uses`, `INERT_CALLS`, `_Bound`,
  3 on `RELATIVE`, 6 on `EXISTS`. Those anchors die with the deleted code: re-author each against `_step`, the
  role table or the census, and add one mutation per silent exit of §4.1 (drop INERT → a named case goes red;
  make an unfollowed BIND silent → the rebound-root case goes red).
- **Limit L5** in `docs/marketplace/experiment-tier-a.md` is rewritten: delete "a name is looked up in Python's
  scope", "a name whose stores disagree is not followed — a miss, by design" and the `nonlocal` sentence; state
  instead "a name reused anywhere in the file is not followed: its root is reported where it is bound, as `.`,
  and the paths built from it later are not named" — a coarser finding, never a miss. Keep the fixture-string
  over-report sentence and add `check-surface-recall.py:519` as its second example.
- **The scan record** `docs/marketplace/scan-2026-11-21.json` is regenerated after the build. Expected against HEAD:
  58 findings, the five differences of §3. That regeneration also closes r3 m4.
- **Self-test count** in the script's docstring (`# 121 cases`) moves with the cases above.

### 4.5 What the r3 findings become

| r3 finding | Under the recommendation |
|---|---|
| M1 keyword `relpath(path=ROOT)` | cannot be expressed: position and keyword share one table row. Corpus EXACT |
| M2 two paths in one f-string | dissolves: each mention walks on its own, there is no outer skip. EXACT ×3 |
| m1 walrus scope | no longer a question the rule asks. Corpus COARSE: `.` at the binding instead of `docs/x.md` at the use. `_Scopes` keeps the defect for detector 6 — FILE it as a backlog row against `home-path` |
| m2 `//` tail | one line in the f-string step. EXACT |
| m3 chained / augmented assignment | USE by default; the "stated bound that fails toward silence" is deleted. Found ×3 |
| m4 scan line drift | closed by the regenerated scan |

## 5. FAILS IF

The recommendation is wrong, and the review must be reconvened rather than folded, if any ONE of these is observed
on the built rule:

1. an input in `corpus.py`'s r1–r3 rows whose wanted answer is a finding returns `[]` (today: zero under (a1));
2. the regenerated scan loses a NAMED target that HEAD's scan has, in any of the six components the tier-A
   experiment hit — measured today as none lost;
3. a review round finds an input where the root is handed on and the rule is silent for a reason that is NOT one of
   the four closed tests of §4.1 — that would mean a fifth silent exit exists and the invariant is not what was
   built.

A finding that a form is reported too coarsely (`.` at a binding) or too eagerly (a false positive) does NOT fail
it: that is the stated direction, and it is filed, not folded.

## 6. The stop condition

Build once from §4, then ONE review round of both halves, briefed to REFUTE §4.1 (find a silent hand-on), not to
enumerate forms. Converged when that round reports no silent hand-on. Findings about precision are filed. If the
round finds a silent hand-on caused by the build, that is observation 3 above: stop, do not fold a second time on
this rule, and take it to the owner with the input — the remaining option is (a0)'s direction for the affected form
only (report the mention itself).

## 7. What did we decide this milestone that is not written down?

1. **The scan's failure direction.** "A false negative publishes a broken component, a false positive costs one
   reading" exists only as a code comment inside the block this review deletes. It is the premise every trade-off
   above rests on and it belongs in the spec (`docs/superpowers/specs/2026-10-15-marketplace-inventory-design.md`,
   next to the §5 falsifier), where a reviewer of ANY detector will read it.
2. **A stated bound was allowed to be a miss.** Limit L5 calls "stores disagree, not followed" a miss "by design".
   Nobody measured it against the live tree until now; it hides `check-plan-code.py:6355`. The unwritten decision
   was "a documented limit may fail toward silence". §4.1 reverses it for this rule; whether it holds for the other
   detectors is unasked.
3. **Fixtures are the only witnesses of the r2 forms.** The r2 coordinator note records that the 28 shipped files
   hold no f-string over a file-derived root, no `joinpath`, no multi-level `nonlocal`. Three rounds were spent on
   forms with zero live instances while a live miss sat unreported. The unwritten rule worth writing: a round on a
   detector runs the candidate on the live tree and reads the DIFFERENCE, before arguing fixture forms.
4. **`_Scopes` is shared.** It was built for `install-root` and silently became detector 6's dependency; r3 m1 is
   therefore also a `home-path` defect nobody filed.
5. **The committed scan is pinned to a commit, not to the branch head** (r3 m4): which of the two the tier-A record
   cites is not stated anywhere.

## 8. Stated bounds of this review

- The corpus's wanted answers are mine, taken from the round documents; one (r2 X2 a-b-c) is contested by design and
  is counted FALSE against the recommendation rather than re-labelled.
- The prototype is unreviewed scratch code. The measured tables are of the PROTOTYPE; the built rule must reproduce
  them, which is what §5 observations 1 and 2 check.
- "Cannot recur" is claimed only for the silent class. Precision findings will keep arriving and are filed.
- Live tree = the 28 `.py` files the scan resolves today. A file added later is not covered by these counts.
- Not run: the mutation sweep against the prototype (the anchors do not exist in it), and the other detectors.
- ADRs read by title only (`docs/adr/` 0001–0015); none governs this rule and none is re-opened. `CONTEXT.md` has no
  entry for `install-root`.
