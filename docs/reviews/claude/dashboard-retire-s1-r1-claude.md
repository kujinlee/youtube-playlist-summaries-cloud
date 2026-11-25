Reviewed head: 3ef5166e209558c7a1e6963eabc585dd5cd0ed49

# Round 1 — dashboard-retire-s1 — claude — 6 findings

**Subject:** branch `dashboard-retire-s1`, head `3ef5166e`, diffed with `git diff origin/master...HEAD`.
**Scope:** backlog #736 slice S1 (plan `docs/superpowers/plans/2026-11-24-dashboard-retire.md`, Tasks 1–6), checked
against spec `docs/superpowers/specs/2026-11-24-dashboard-retire-design.md` §2.1–§2.4 and §3 (A1, F1, K4, K5, K6).
The `check-shipping-sets.py` edge pin was skipped as instructed.

**Severity count:** 0 BLOCKER, 0 HIGH, 2 MEDIUM, 4 LOW.

## Self-tests (run at `3ef5166e`, foreground, all rc 0)

| Script | Result |
|---|---|
| `check-dashboard-entry.py --self-test` | 176/176 pure, 23/23 cannot-run |
| `goal-tree.py --self-test` | 607/607 |
| `compaction-state.py --self-test` | 130/130 |
| `explainer-serve.py --self-test` | 297/297 |
| `regen-pages.py --self-test` | 123/123 |
| `check-reference-namespace.py --self-test` | 51/51 |
| `check-shipping-sets.py --self-test` | 170/170 |
| `check-merge-ready.py --self-test` (it copies the gate file into fixtures, `:4171`) | 467/467 |

## Probes that the code got RIGHT (no finding)

The probe scripts were run from the scratchpad against the worktree's modules, each world in a fresh `mktemp` directory.

- A tracked subdirectory `docs/asks/sub/` is a PROBLEM (name rule). A tracked symlink ask is a PROBLEM ("is a
  symlink, not a regular file"), both via `ask_store_problems`.
- A removed answer (answered at the base, unanswered at HEAD) is refused by F1 end to end through git.
- BOM, blank `#    `, and `## Q?` first lines are PROBLEMS. CRLF `## Answer` closes the ask.
- An unclosed fence before `## Answer` leaves the ask OPEN (fail-visible).
- Each mutation manifest entry added for the gate (19 names), goal tree (5) and compaction snapshot (2) names a case
  that the neutered line would turn red. I read each one against its case; I did not run the harness.

---

## M1 — MEDIUM — an ask that declares `decision: backlog #N` loses its options and its warning when it merges

**Where:** `scripts/goal-tree.py:1411` (`consolidate` copies only `source, ref, href, text, multi` into `also`),
reached from `scripts/goal-tree.py:1610`. The options and warning are set at `scripts/goal-tree.py:1339`–`:1341`.

**Spec:** §2.4 says an item read from `docs/asks/` "shows, under the question, its options as a plain list", and a
malformed ask "stays visible, with its diagnosis … printed under the title as a warning line — the ask is KEPT".

**Input:** an ask file whose text carries an identity token, the convention dashboard asks already use:

```
docs/asks/2026-11-25-pick.md
# Which name? decision: backlog #5

**Decide:** which name?
- needs-you [recommended]
- asks
```

with `BACKLOG_FIXTURE` (row 5 is NEEDS-OWNER) as the backlog source.

**Observed:** `needs_from_asks` builds the item with `identity=[5, 'decision']` and
`options=['needs-you [recommended]', 'asks']`. After `consolidate(backlog + asks)`, the only surviving item is
`backlog #5` with `options=None, warn=None, also=[('asks', '2026-11-25-pick')]`. The options are not printed
anywhere, because `_item_details` (`scripts/goal-tree.py`, added in this diff) reads `n["options"]` of the top item
only. The same path drops a `decision_warning`, so a malformed ask that names a backlog row loses its diagnosis.

**Expected:** the ask's options and its warning appear in NEEDS YOU whether or not the ask merged into a backlog row.

**Fix:** carry `options` and `decision_warning` into the `also` record. Then either render them under the merged item
(`_item_details` and `_details_html` walk `also`), or exclude `asks` items from merging. Add a case: an ask file with
`decision: backlog #5` and a malformed block shows its options and its warning under the merged backlog item.

## M2 — MEDIUM — A1 passes when `docs/asks/` is absent at HEAD, which both readers treat as a PROBLEM

**Where:** `scripts/check-dashboard-entry.py:684`–`:693` (`ask_store_problems`). An empty `git ls-tree` listing gives
`present = []`. `read_asks(dir, [])` then never lists the directory, so its "missing directory" problem
(`read_asks`, the `names is None` branch) cannot fire. Separately, F1 skips `.gitkeep` at
`scripts/check-dashboard-entry.py:627`.

**Spec:** A1 FAILS IF "any entry of `docs/asks/` at HEAD is a PROBLEM to `read_asks`". §2.3 lists "a missing
directory" first among the PROBLEM cases. K5 requires that a missing `docs/asks/` is never shown as an empty NEEDS
YOU.

**Input:**
- (a) a repository whose HEAD has no `docs/asks/`;
- (b) a branch that `git rm`s `docs/asks/.gitkeep` while no ask file exists. This is the state of master right after
  S1 merges.

**Observed:**
- (a) `ask_store_problems(None, root)` returns `([], None)`, so A1 passes.
- (b) `ask_store_problems("HEAD~1", root)` returns `([], None)`, so A1 and F1 both pass. In both cases
  `read_asks(root/"docs/asks")` returns `['docs/asks/ is missing … — no ask could be read']`.

So the PR merges green, and on master the goal tree is NOT READ and the compaction snapshot is CANNOT RUN on every run
until someone restores the directory. This is loud, not silent, but the gate lets through the one state its two
consumers refuse.

**Expected:** A1 refuses a HEAD with no tracked entry under `docs/asks/`. The directory must exist for the store to be
readable.

**Fix:** in `ask_store_problems`, when the `ls-tree` listing is empty, append
`docs/asks/ is not tracked at HEAD — keep .gitkeep until the first ask lands`. Add a case to the git fixture
(`_repo({})` refused). An F1 change is not needed.

## L1 — LOW — F1's byte-prefix rule accepts an edit to the LAST line when the base has no trailing newline

**Where:** `scripts/check-dashboard-entry.py:633` (`head_files[name].startswith(base_files[name])`).

**Spec:** the F1 falsifier is literally "the base text is not a prefix of HEAD's text", so the code conforms to the
letter. But the stated intent ("an edited question, a rewritten answer … are refused") is not met for this shape. A1
accepts the shape: the case "a question with no body is OPEN" (`:1587`) uses `"# Which form?"` with no newline.

**Input / observed:**
- `f1_problems({"2026-11-25-a.md": b"# Which form?"}, {"2026-11-25-a.md": b"# Which form? Actually, which colour?\n"})`
  returns `[]`. The question was edited and F1 passed it.
- `f1_problems({…: Q + b"## Answer\na"}, {…: Q + b"## Answer\na -- no, b\n"})` returns `[]`. The answer was rewritten
  and F1 passed it.

**Expected:** both are refused.

**Fix:** refuse the edit when the base is non-empty, does not end in `\n`, and HEAD's next byte after the prefix is not
`\n`. Alternatively, have A1 require a trailing newline. This is not a fix-induced defect, so the §3 pre-committed
retreat (delete F1) does not apply.

## L2 — LOW — the name rule admits a trailing newline and non-ASCII digits

**Where:** `scripts/check-dashboard-entry.py:503`, which is used with `.match`. `$` matches before a final `\n`, and
`\d` is Unicode-aware on a `str` pattern.

**Input / observed:**
- `read_asks` over a file named `"2026-11-25-a.md\n"` (git can track that name) returns an OPEN ask with stem
  `'2026-11-25-a.'`. The stem has a stray dot, and the item `ref` is wrong.
- A file named `٢٠٢٦-11-25-a.md` (Arabic-Indic digits) is accepted as a valid ask.

**Expected:** both are refused as PROBLEMS. §2.3 says the name begins with "the date the ask was written".

**Fix:** use `ASK_NAME.fullmatch` with `[0-9]` (or `re.ASCII`). Add the two names to the "name that fails the rule"
case's `_bad` list. `2026-99-99-a.md` is also accepted; a calendar check is optional.

## L3 — LOW — no case witnesses the directory's own mtime in `source_mtime`

**Where:** `scripts/explainer-serve.py:286` (`return max([own, *children])`).

**Spec:** §2.3c says the staleness time is "the max `st_mtime_ns` over the directory itself and its `*.md` children".

**Input:** in a scratch copy (`git archive HEAD`, outside the repo), `return max([own, *children])` was replaced with
`return max(children or [own])`, which drops the directory's own term.

**Observed:** `explainer-serve.py --self-test` gives 297/297, still green. 5.1's fixture moves the directory to 900
and the new child to 950, so the child alone answers the case.

**Expected:** a case in which only the directory moved, for example an ask file removed or renamed with its mtime
kept, goes stale. With the mutation, that case reads fresh.

**Fix:** add a fourth world, `"removed"`, that deletes a child and sets the directory's mtime to 900. Expect
`stale docs/asks`. Add a manifest entry for the mutation above.

## L4 — LOW — A1 reads HEAD's names but the WORKING TREE's bytes, while spec A1 says "Reads HEAD's tree only"

**Where:** `scripts/check-dashboard-entry.py:689`–`:693`. Names come from `git ls-tree HEAD`, and content comes from
`read_asks(root/ASKS_REL, present)`, which opens the files on disk.

**Input:** commit an ask holding a conflict marker, then fix the file in the working tree without committing.

**Observed:** by reading the code, not run, a local `check-dashboard-entry.py` (and `check-merge-ready.py`'s local
replay of it, `:2198`) passes. CI's merge ref then fails it. This is the vacuous local pass that `docs/CLAUDE.md`
item 3 warns about for this same script. The reverse direction (a dirty bad edit over a good commit) fails locally,
which is merely conservative.

**Expected:** A1 judges HEAD's bytes, as the spec row says.

**Fix:** pass the bytes from `git cat-file` (already fetched by `_ask_blobs(root, "HEAD")`) and the modes from
`ls-tree` into the content rules. The `read_asks` FIFO and symlink checks stay for the directory view. Alternatively,
state the bound in the docstring and refuse a dirty `docs/asks/` (`git status --porcelain -- docs/asks`).

---

## Not counted as findings (spec-conformant, noted for the record)

- A `## Answer` line inside a multi-line HTML comment closes the ask (`([], [])`), so the ask leaves NEEDS YOU while
  rendering nothing. This follows §2.1's "one fence rule" deliberately. It is the owner's call whether comments
  should count.
- An untracked `.DS_Store` in the main checkout's `docs/asks/` makes the goal tree NOT READ and the snapshot CANNOT
  RUN. This is loud and documented in `read_asks`'s docstring ("an untracked file IS what the owner sees"). Finder
  creates that file on its own, so the owner may meet it.

VERDICT: NOT CONVERGED
