# doc-citations-guard — round 1, Claude half

**VERDICT: NOT CONVERGED** — 2 High, 4 Medium, 3 Low.

Subject: `scripts/check-doc-citations.py` (new, backlog #49), its manifest, CI wiring, the pins it
moved, and the documentation edits that ride with it. Reviewed at working-tree state on branch
`doc-citations-guard` (commit `31bf821a` plus uncommitted edits to `scripts/check-merge-ready.py`
and `docs/backlog.md`).

**What holds.** The guard works. Its core predicate is sound, the suffix exemption is derived from
real firings rather than imagined, `main()` is genuinely drivable to all three exit codes, there is
no fail-open path, and the ambient-pass class that previously infected the suite is now clean — I
checked every citation literal in the suite against the shipped regex and only the deliberate
grammar-boundary case fails to match. The documentation's suite-size arithmetic is exactly right
(10,373 + 604 = 10,977). The findings below are about the *claims* made for it and three reachable
edge paths, not about the idea.

---

## H1 — An untracked but PRESENT file is reported as unresolvable, and `.claude/` is where this project's harness lives

`resolve()` uses `git ls-files` as its only oracle for "does this file exist". A citation into a
real, readable file that git does not track is reported as *"does not resolve — no tracked file"*.

Evidence:

```
$ test -f .claude/skills/shared/explainer-delivery.md && wc -l < .claude/skills/shared/explainer-delivery.md
     346
$ sed -n '80p' .claude/skills/shared/explainer-delivery.md
## 1. Where the file goes
$ git ls-files --error-unmatch .claude/skills/shared/explainer-delivery.md ; echo rc=$?
rc=1
```

The guard fires on that citation. The file exists, has 346 lines, and line 80 is a real heading —
the citation is **correct**. Running the shipped `violations()` over the last 40 commits produces
this as one of its ten firings:

```
2413b003 docs/backlog.md: `.claude/skills/shared/explainer-delivery.md:80` does not resolve — no tracked file
```

Across the living corpus, 3 citations are in this class (2 distinct paths: `.claude/skills/...`
and `scratchpad/b3-raw.ts`), against 27 that are genuinely absent. `.claude/skills/` and
`.claude/hooks/` hold this project's own harness and are cited routinely in `docs/`; the
marketplace-inventory work will cite them heavily.

**Why it matters beyond the count:** this contradicts the branch's own claim that every firing is a
true positive, and it fires on the *correct* behaviour it is meant to encourage.

**Fix:** make existence the oracle rather than tracking — accept when `(root / path).is_file()`,
falling back to the suffix search only when it does not. Keep the suffix rule for genuine
non-repo-relative citations.

---

## H2 — None of the three headline numbers in the docstring reproduces against the shipped code

The docstring presents these as measurements that chose the scope. Re-derived with the shipped
`CITE` regex and the shipped `resolve()`:

| Claim (docstring) | Re-derived | Why it differs |
|---|---|---|
| reviews hold **37,071 of 39,312** citations (94%) | **32,000 of 32,897** (97.3%) | measured with a looser prototype regex (bare filenames, no `[]` in the path class) |
| living corpus fires **175 on 838 (20.9%)** | **105 on 838 (12.5%)**, or 113/897 with the shipped regex | the 175 was measured **before the suffix exemption existed**; it describes a rule that does not ship |
| **6 firings over 40 commits (0.15/commit)** | **10 firings (0.25/commit)** | `md` was added to the extension list *after* calibration; the 4 extras are all `.md` targets |

Commands: a sweep importing the shipped module and calling `g.violations()` over
`git rev-list -n 40 origin/master` yields 10 findings; the corpus sweep applying the shipped
`resolve()` yields 105/838.

Every conclusion survives — reviews still dominate overwhelmingly, the corpus rate is still far too
high to gate on, and 0.25/commit is still below the 0.50 at which `check-reference-namespace`
shipped. But the figures are not reproducible from the delivered code, and this repository treats a
number without provenance as a defect in its own right. The commit message for this very branch
says the scope was *"measured before it was adopted"*; two of the three numbers measure something
else, and the third measures a narrower regex.

**Fix:** re-derive all three with the shipped code and restate them, or state explicitly that they
were measured against the pre-exemption prototype and give both figures. Also correct *"All six were
hand-classified as TRUE positives"* — there are ten, and the four unexamined ones include H1.

---

## M1 — A tracked file missing from the worktree crashes with a traceback instead of CANNOT RUN

`violations(...)` is called **outside** the `try/except` that guards the git calls, while `_reader`
is documented to raise. A file present in the index but absent from the worktree therefore produces
an uncaught `FileNotFoundError`.

Reproduced in a clean scratch repo:

```
  in index:  1
  on disk:   NO
  REAL rc=1
    FileNotFoundError: [Errno 2] No such file or directory: '/private/tmp/cit2/lib/a.ts'
```

This is not a fail-open — rc is non-zero, so CI still fails — but the guard's own FAILS IF section
promises *"`git` cannot be run … which is CANNOT RUN (rc=2), never a pass"*, and this path returns
1 with a traceback, which reads as "citations have drifted" to anything parsing the exit code.
Reachable for any author who deletes a file and runs the guard before staging.

**Fix:** bring `violations(...)` inside the `try`, or have `_reader` wrap `OSError` in a
`RuntimeError` naming the path, so the existing handler reports CANNOT RUN.

---

## M2 — Mutation 1 crashes the suite at case 2, so its "exclusive attribution" is an artifact

Applying the first manifest entry (the blank-line clause removed) and running the suite:

```
  File ".../m.py", line 215, in self_test
    "lands on nothing" in violations(diff("docs/x.md", "`lib/a.ts:2`"), tracked, read)[0])
IndexError: list index out of range
```

The case *"the blank message names the reader's experience"* indexes `[0]` on a list the mutation
makes empty. The process dies at case 2, so cases 3–30 never execute. The harness records one red
and reads it as exclusive — but nothing else *could* have gone red.

This is the same class the branch already fixed once: a kill by crash names no case. Here it names
one by accident.

**Fix:** guard the index — `(violations(...) or [""])[0]` — so the case fails rather than raises.
Then re-run the sweep and confirm mutation 1's attribution is real.

---

## M3 — Mutation 7 kills four cases, which is the defect corrected for mutation 3

Applying the last entry (the injected reader ignored) produces four reds:

```
  the blank message names the reader's experience
  the out-of-range message states the file length
  line 3 (last line) is in range
  the verdict follows the INJECTED reader — blank at line 1 fires
```

The named case is among them, so the harness accepts it. But the harness's own refusal text, quoted
in this branch's history, is *"An expect must name EXACTLY ONE, or it cannot show which case is the
guard"* — the standard applied when mutation 3's expect was corrected. Mutation 7 does not isolate.

**Fix:** narrow the mutation so only the reader-varying case can see it, or accept it explicitly in
the manifest entry with the reason, rather than leaving it looking isolated.

---

## M4 — `portable-practices.md` now claims 14 anchors; this branch has 13

```
$ grep -cE '^\| `[a-z-]+` \|' docs/anchors.md
13
```

The 14th (`harness-ships-elsewhere`) exists only on the unmerged `marketplace-inventory` branch. If
this branch merges first, master carries a document asserting a count its own registry contradicts —
the precise failure the same edit was written to correct.

**Fix:** say 13, or make the claim branch-independent ("one per goal, see the registry"), or land
the two branches in a defined order.

---

## L1 — 41% of living citations are RANGES, and only the start line is checked

```
  total                                897
  RANGE (only the start is checked)    372
```

`lib/pipeline.ts:46-48` matches as `:46`; the trailing `-48` is ignored because `\b` sits between
the digits and the hyphen. Checking the start line is defensible, but the docstring says *"the cited
line must exist and carry content"* and for 41% of citations there is no single cited line. A range
whose start is fine and whose end is past EOF passes silently.

**Fix:** a sentence in WHAT IT ASSERTS; optionally validate the end of a range too.

---

## L2 — It cannot see fenced code blocks, by construction

`--unified=0` carries no surrounding context, so the rule cannot know whether an added line sits
inside a fence. Measured over fence-balanced living documents: **40 of 896 citations (4.5%)** are
inside fences, e.g. `// lib/doc-version.ts:8` in a plan's code block. None of the ten PR-scoped
firings is one, so this is latent rather than live — but a document pasting example output
containing a `path.ts:NN` string would be refused with no way to express intent.

**Fix:** none required now; record it as a stated limit, and consider an inline-code or
fence-escape exemption if it ever fires.

---

## L3 — The guard can only ever inspect its own repository

`ROOT = pathlib.Path(__file__).resolve().parent.parent` and there is no `--root`. Running it from
another checkout silently audits the wrong tree — I hit this while testing and it reported OK about
a different repository. Defensible for a repo-local gate, but it cost one invalid experiment here,
and the marketplace inventory contemplates shipping this harness elsewhere.

**Fix:** a `--root` argument defaulting to `ROOT`, which also makes the CANNOT RUN path testable
against a real but empty tree.

---

## What I could not break

- The suffix exemption: I could not construct a wrong answer from it. Ambiguous suffixes fire, and
  the one-match case is exercised by cases that genuinely depend on it (removing the tracked file
  flips the verdict).
- `in_scope`: prefix matching is not foolable in either direction that I could find.
- Fail-open: every unresolvable path produces a finding; no branch returns 0 on an unresolved
  citation.
- Ambient passes: only the deliberate grammar-boundary literal fails to match the regex.
- The ci.yml wiring and both pins (`EXPECTED_MUTATIONS` 1426, merge-ready allowance 4) are
  consistent with the workflow as written.
