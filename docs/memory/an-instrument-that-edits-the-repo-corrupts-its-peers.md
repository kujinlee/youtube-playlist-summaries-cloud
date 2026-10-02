---
name: an-instrument-that-edits-the-repo-corrupts-its-peers
description: "FIRES-WHEN: running an instrument that writes tracked files; about to git add -A — ⭐⭐ 3 instances. An instrument mutating tracked files (23/44 vs 44/44) — AND, needing no instrument at all: my `git add -A` committed another session's half-finished edit (CI red on a defect not mine), and a reviewer read a tree that moved 3 times while I repaired a different review in it. Stage explicit paths; never repair one review while another reads"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 562085d6-32ed-48ac-9814-b2f5e07b1cfe
  modified: 2026-09-14T00:42:42.301Z
---

**Measured 2026-08-08, during round 8, by the reviewers themselves.**

`mutate-schema.py` wrote each mutation into the **repo-tracked** `schema/*.sql` and restored it in a
`finally`. Two agents running `./scripts/check-schema-gates.sh` at the same time on one checkout
therefore read each other's edits:

```
in the repo, concurrent :  23/44   (21 entries RED(other), carrying detail text
                                    belonging to a DIFFERENT mutation)
isolated copy, same commit: 44/44
```

**It failed LOUD AND WRONG, which is the expensive kind** — a reviewer spent a cycle treating a green
artifact as broken, and the opposite mistake (a concurrent run masking a genuine GREEN as
`RED(other)`) is equally available. The `finally` also does not survive `SIGKILL`, so an interrupted
run left a **mutated, repo-tracked schema file on disk** — one `git commit -a` from becoming the
schema.

**Fix: `cp -r` to a temp dir and mutate the copy.** `verify-schema.sh` already resolves its schema
directory from its own location, so copying it beside the schema is the whole trick. Verified by
running two suites simultaneously: both 58/58, checkout clean.

> **Any instrument that mutates the tree it measures cannot be run twice at once** — and "we only run
> it once" stops being true the moment two reviewers, or a hook and a human, are dispatched in
> parallel. This is the standing dispatch pattern here, so the collision was structural, not bad luck.

**Two siblings found the same day, same shape — an instrument that could not report itself:**

- `classify()`'s `RED(constraint)` branch never compared `expect`, so a mutation aimed at one
  constraint could be caught by **any** constraint and still score as covering its target. Round 6
  added that comparison to the assertion branch and round 7 to the trigger branch, explicitly noting
  that not sweeping was shape #10 — this was the **third** sibling neither round reached.
- `check-guard-coverage.py` enumerated triggers on **two tables**, so it printed ✅ with a brand-new
  guard outside its query, and had never seen round 6's corrections trigger at all.

---

⭐⭐ **THE SAME HAZARD WITHOUT ANY INSTRUMENT — TWICE IN ONE SESSION, 2026-09-13/14 (PR #297), and
both times the writer was ME.** The 2026-08-08 case needed a script that mutates tracked files. These
needed nothing but two agents and one checkout.

**(a) `git add -A` committed another session's work-in-progress.** A second session was mid-edit on
`scripts/codex-review.py` and `scripts/check-review-recorded.py` in the shared tree. My `git add -A`
swept a SNAPSHOT of the first into two of my commits, and CI went red on a defect that was not mine:
`codex-review.py: [DRIFT] the docstring declares 68 cases; the suite ran 73` — a half-finished edit,
frozen mid-keystroke and pushed under my name.

⚠ **Backing it out has a destructive direction and a safe one.** `git checkout master -- <path>`
overwrites the WORKING TREE and destroys work still being typed. The safe form updates only the index:

```bash
git restore --source=master --staged <path>   # index gets master's version
git commit                                    # the commit drops it; their edits stay on disk
```

**(b) A REVIEWER read a tree that moved three times underneath it.** I dispatched the Claude half and
then, in the same tree, fixed the Codex half's findings while it worked. It disclosed the movement
itself, named the `HEAD` at each stage, and re-ran every attack against the final tree — so the review
survived. That was its discipline, not my design; a less careful half would have reported findings
about code that no longer existed.

**How to apply.**

* **Stage explicit paths. `git add -A` is unsafe in a tree any other agent can write to** — and this
  project's standing dispatch pattern means that is the normal case, not the exception.
* **Never repair review A while review B is reading the same tree.** Either serialise, or give the
  second reviewer its own checkout. The fix that lands is exactly what a reviewer needs to see whole.
* **Before committing, look at what is actually staged** — `git diff --cached --name-only` — and ask
  whether every path is yours. Both of these were visible there and neither was looked at.

⚠ backlog #67 records this class from the other side (a subagent's `git stash` taking the
coordinator's work) and states plainly that **none of the must-serialise operations is mechanically
enforced**. Still true. These are conventions, and I broke one of them twice in a day.

See [[what-mutation-testing-proves]], [[test-harness-can-launder-failures]],
[[guard-classification-shape-vs-sequence]], [[blob-addressing-spec-state]],
[[concurrent-agents-go-wrong]], [[concurrent-agents-go-wrong]].
