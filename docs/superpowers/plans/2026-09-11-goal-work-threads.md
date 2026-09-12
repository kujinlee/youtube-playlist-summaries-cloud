# Goal Work Threads Implementation Plan

> **Anchor:** `status-visibility` — **ADR:** none
> **Goal:** A person who was away can see the current state, what changed, and what needs them —
> without reading the chat transcript.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Each goal card on `/goals` shows the work that pursued it as `spec → plan → PR` threads, so
a reader can find the pull requests, not just the documents.

**Architecture:** Pure functions parse and pair; a thin collection layer shells out to `git`; the
renderer consumes records. Mirrors `gen-goals-page.py`'s existing three-band structure
(`pure parsing` / `collection` / `rendering`) so every new rule is unit-testable without a repo.

**Tech Stack:** Python 3, stdlib only. `subprocess` for git. No new dependencies.

**Spec:** [`docs/superpowers/specs/2026-09-11-goal-backlog-pr-join-design.md`](../specs/2026-09-11-goal-backlog-pr-join-design.md) **v4**.

**v2 of this plan, 2026-09-11 — rewritten after Post-Plan Gate round 1.** Both halves returned
NOT-CONVERGED: 3 Blocking, 4 High, 7 Medium, 6 Low, one Codex Blocking refuted. Adjudication in
[`docs/reviews/coordinator/plan-goal-work-threads-r1-coordinator.md`](../../reviews/coordinator/plan-goal-work-threads-r1-coordinator.md).

⭐ **THE BIGGEST CHANGE IS A RETRACTION.** v1 tagged each PR `code` and claimed that identified the
implementation. Measured three ways independently: **PR #147 — the ADR-0010 anchor-header backfill —
is tagged `code` on 22 of 47 documents**, and for 5 of them it is the *only* such PR. The tag is
demoted to what it actually measures (*this commit touched a non-document file*), the thread-level
`n_code` summary and the `⚠ no code PR yet` flag are **deleted**, and each PR renders how many
anchored documents it touched so a bulk edit is visible as one. A threshold was tested and rejected:
`≤2 documents` excludes #147 but also kills **#176**, a real implementation.

⚠ **THIS IS PLAN 1 OF 2** — see *Not in this plan* at the end. Direct (document-less) work is
**explicitly out of scope**, which round 1 raised and which is recorded there rather than implied.

## Global Constraints

- **Never re-implement another script's rule.** Call the owner's function.
- **A deriver that cannot run is a FAILURE, not a pass.** `None` (git could not answer) and `[]` (no
  PRs) must stay distinguishable to the renderer.
- **`docs/anchors.md` holds names, not state.** Nothing here writes to it.
- **Pure functions above `# ---- collection` (`:162`); anything touching the filesystem or
  `subprocess` below it.**
- ⛔ **EVERY TASK'S STEP 4 UPDATES THE DECLARED CASE COUNT** at `gen-goals-page.py:6`
  (`# 15 cases, pure functions only`). `gen-goals-page.py` is pinned in
  `check-selftest-counts.POPULATION` (`:134`) and that guard **runs in CI** (`ci.yml:275`). Round 1
  found this plan adding 50 cases and never touching line 6 — five of six commits would have been
  red on the guard whose entire purpose is catching it.
- **Every case must be able to FAIL.** Where a case can only fail *in company with a sibling*, the
  plan says so, so a later refactor cannot delete the load-bearing half and leave the vacuous one.
- **Counts in this plan are dated corpus measurements**, not contracts. Measured **2026-09-11**:
  187 documents under `docs/superpowers/{specs,plans}`, **47** declaring an anchor, 140 excluded.

---

### Task 1: Thread identity — pairing a spec with its plan

**Files:**
- Modify: `scripts/gen-goals-page.py` — pure-parsing section. **Insert at `:160`**, i.e. after the
  `esc`/`inline_md` bindings at `:158-159` and before the `# ---- collection` banner at `:162`.
  (⚠ round 1 L1: `parse_roots` actually ends at `:141`; `:144-159` is the backlog-#71 comment plus
  those two bindings. The insertion point is right, the old description was not.)
- Test: `scripts/gen-goals-page.py` `self_test()` (`:411`; `eq` at `:414-419`)

**Interfaces:**
- Consumes: nothing.
- Produces: `doc_stem(name: str) -> str`;
  `pair_documents(docs: list[dict]) -> list[dict]` where a thread is
  `{"stem": str, "spec": dict|None, "plan": dict|None, "docs": list[dict]}`.
  Input records are what `collect()` builds at `:200-205` — keys `name`, `rel`, `goal`, `dated`,
  `touched`, `kind` (`"spec"`/`"plan"`), `milestones`.

- [ ] **Step 1: Write the failing tests**

Add inside `self_test()`, before the final `print(...)`:

```python
    eq("stem strips -design", doc_stem("2026-08-29-retarget-design.md"), "2026-08-29-retarget")
    eq("stem strips -plan", doc_stem("2026-08-28-dashboard-plan.md"), "2026-08-28-dashboard")
    eq("a bare name is already a stem", doc_stem("2026-08-29-retarget.md"), "2026-08-29-retarget")
    eq("only a TRAILING suffix is stripped",
       doc_stem("2026-09-01-design-review-notes.md"), "2026-09-01-design-review-notes")

    _s = {"name": "2026-08-29-x-design.md", "kind": "spec"}
    _p = {"name": "2026-08-29-x.md", "kind": "plan"}
    # LOAD-BEARING PAIR. The `None`-slot cases below are satisfied by a pair_documents
    # that never fills a slot at all; this case is what kills that. Do not delete one
    # without the other.
    eq("the thread names both halves",
       [pair_documents([_s, _p])[0][k]["name"] for k in ("spec", "plan")],
       ["2026-08-29-x-design.md", "2026-08-29-x.md"])
    eq("a spec and its plan share one thread", len(pair_documents([_s, _p])), 1)
    eq("a spec with no plan is a thread with an empty plan slot",   # pairs with the above
       pair_documents([_s])[0]["plan"], None)
    eq("a plan with no spec is a thread with an empty spec slot",   # pairs with the above
       pair_documents([_p])[0]["spec"], None)
    eq("threads sort newest stem first",
       [t["stem"] for t in pair_documents([{"name": "2026-01-01-a.md", "kind": "plan"}, _p])],
       ["2026-08-29-x", "2026-01-01-a"])
    _s2 = {"name": "2026-08-29-x-plan.md", "kind": "spec"}
    eq("a second document in a slot is kept, not dropped",
       len(pair_documents([_s, _p, _s2])[0]["docs"]), 3)
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python3 scripts/gen-goals-page.py --self-test`
Expected: FAIL — `NameError: name 'doc_stem' is not defined`

- [ ] **Step 3: Write the minimal implementation**

Insert at `:160`:

```python
STEM_SUFFIX = re.compile(r"-(design|plan)$")


def doc_stem(name: str) -> str:
    """Filename -> the stem a spec and its plan share. PURE.

    `2026-08-29-x-design.md` and `2026-08-29-x.md` both give `2026-08-29-x`.

    ⚠ BOTH suffixes are stripped, measured rather than assumed. 2026-09-11: 91 specs end
    `-design` and 3 are bare; 91 plans are bare and 1 ends `-plan`.

    ⚠ GLOBAL vs ANCHOR-SCOPED, and the difference is large. Over ALL 187 documents this
    rule pairs 61 (stripping `-design` alone pairs 60). But `collect` calls
    `pair_documents` with ONE ANCHOR'S documents, and only 47 documents declare an anchor:
    anchor-scoped the corpus yields 41 threads of which just **6** have both halves. 35
    threads render one side absent, and that is correct — an anchor-less document is
    invisible to this page by design (spec F8) — but do not read 61 as what the page shows.
    """
    base = name[:-3] if name.endswith(".md") else name
    return STEM_SUFFIX.sub("", base)


def pair_documents(docs: list[dict]) -> list[dict]:
    """Documents -> threads, newest stem first. PURE.

    A thread is {stem, spec, plan, docs}. EITHER SIDE MAY BE None and neither is an error:
    a spec with no plan is work not yet planned; a plan with no spec was written without
    one. The card draws them absent rather than omitting them.

    ⛔ A stem claimed by two specs would FUSE two threads invisibly. Measured 2026-09-11:
    0 stems are claimed by more than two files. The extra is kept in `docs` anyway, and
    `render_threads` MUST render it — round 1 found the record kept it while the page
    dropped it, which put the protection somewhere no reader could see.
    """
    by_stem: dict[str, dict] = {}
    for d in docs:
        stem = doc_stem(d["name"])
        t = by_stem.setdefault(stem, {"stem": stem, "spec": None, "plan": None, "docs": []})
        t["docs"].append(d)
        slot = "plan" if d.get("kind") == "plan" else "spec"
        if t[slot] is None:
            t[slot] = d
    return sorted(by_stem.values(), key=lambda t: t["stem"], reverse=True)
```

- [ ] **Step 4: Run the tests, then UPDATE THE DECLARED COUNT**

Run: `python3 scripts/gen-goals-page.py --self-test`
Expected: PASS, `25/25`.

Then edit `gen-goals-page.py:6` so the declaration reads the number just printed:
`python3 scripts/gen-goals-page.py --self-test  # 25 cases, pure functions only`

Run: `python3 scripts/check-selftest-counts.py`
Expected: rc=0. **If this is red, stop — do not commit.**

- [ ] **Step 5: Commit**

```bash
git add scripts/gen-goals-page.py
git commit -m "A spec and its plan are one thread, and a collision cannot vanish"
```

---

### Task 2: Reading pull requests out of a git log — the pure half

**Files:**
- Modify: `scripts/gen-goals-page.py` — pure-parsing section, after `pair_documents`
- Test: `self_test()`

**Interfaces:**
- Consumes: nothing.
- Produces: `prs_from_log(lines) -> list[dict]` giving
  `{"sha", "num", "date", "subject"}` newest first, deduped by `num`;
  `files_are_code(files) -> bool`.

- [ ] **Step 1: Write the failing tests**

```python
    _lg = ["aaa\x012026-08-29\x01Retire the plan dependency (#176)",
           "bbb\x012026-08-31\x01Asks state their choices (#186)",
           "ccc\x012026-08-31\x01Asks state their choices (#186)",
           "ddd\x012026-07-01\x01a direct commit with no PR"]
    eq("a squash subject yields its PR number",
       [p["num"] for p in prs_from_log(_lg)], ["176", "186"])
    eq("the date travels with the PR", prs_from_log(_lg)[0]["date"], "2026-08-29")
    eq("a commit with no PR tail is dropped", len(prs_from_log(_lg)), 2)
    eq("a malformed line is skipped, not crashed on", prs_from_log(["garbage"]), [])
    eq("a PR-looking number mid-subject is not the PR",
       prs_from_log(["e\x012026-01-01\x01mentions (#99) in passing, no tail"]), [])

    eq("a script path is code", files_are_code(["scripts/gen-goals-page.py"]), True)
    eq("one code file among docs makes it a code PR",
       files_are_code(["docs/backlog.md", "lib/storage.ts"]), True)
    # ⭐ ROUND 1 H3 — F7 had ALREADY FIRED before the code was written. Measured over the
    # last 400 PRs: 10 commits whose only non-`docs/` files are markdown — CONTEXT.md and
    # .agents/skills/**. Each was tagged `code`. A single-path case cannot see this class;
    # this one goes red if DOC_PATH loses ANY branch.
    eq("this repo's documentation outside docs/ is not code",
       files_are_code(["docs/x.md", ".remember/remember.md", "README.md",
                       "CONTEXT.md", "AGENTS.md", "CLAUDE.md",
                       ".agents/skills/brief/SKILL.md"]), False)
    # ⭐ ROUND 2 H. The round-1 fix for the above created the OPPOSITE defect: an
    # unanchored `README` also matches `README-generator.ts`, so a real implementation
    # rendered as `docs only`. Latent (no such path exists yet) and fixed by anchoring each
    # literal with `$`. This case dies the moment an anchor is dropped.
    # ⚠ Reported individually, not chained with `and`. Round 3 noted the chain is coarse;
    # a list of results names WHICH path class regressed.
    eq("a code file whose name starts with a doc name is still code",
       [files_are_code([f]) for f in
        ("README-generator.ts", "CONTEXT.md.bak", "CLAUDE.md.old", "READMEs.tsx",
         "src/READMEs.tsx", "a/b/CONTEXT.md.ts")], [True] * 6)
    # ⭐ ROUND 3 H. Anchoring with `$` fixed the above and MISSED nested instruction
    # documents — the third narrowing of one regex in three rounds. `(.*/)?` is the class.
    eq("an instruction document at any depth is not code",
       [files_are_code([f]) for f in
        ("worker/CONTEXT.md", "packages/api/AGENTS.md", "sub/dir/README.md")], [False] * 3)
```

⚠ **`files_are_code([]) == False` and `prs_from_log([]) == []` are NOT in this set.** Round 1 named
both vacuous: `any()` over an empty iterable is `False` for every predicate, so the first passes even
if the body is `return False`. They document; they cannot fail.

- [ ] **Step 2: Run it to verify it fails**

Run: `python3 scripts/gen-goals-page.py --self-test`
Expected: FAIL — `NameError: name 'prs_from_log' is not defined`

- [ ] **Step 3: Write the minimal implementation**

```python
PR_TAIL = re.compile(r"\(#(\d+)\)\s*$")
# ⚠ NOT just `docs/`. Round 1 measured 10 PRs in the last 400 whose only non-`docs/`
# changes were CONTEXT.md or .agents/skills/**, every one wrongly tagged `code`.
# ⚠ THREE ROUNDS OF THIS ONE REGEX, and each fix was narrower than the class.
#   r1: `^docs/` alone missed CONTEXT.md and .agents/  -> 10 real mis-taggings
#   r2: adding bare `README` matched README-generator.ts -> 4 the other way
#   r3: anchoring with `$` missed worker/CONTEXT.md      -> nested instruction docs
# `(.*/)?` is the class: an instruction document at ANY depth, and only when the
# whole basename matches. Verified 0 wrong over 19 adversarial paths.
DOC_PATH = re.compile(
    r"^(docs/|\.remember/|\.agents/"
    r"|(.*/)?(README(\.md)?|CONTEXT\.md|AGENTS\.md|CLAUDE\.md)$)")


def prs_from_log(lines) -> list[dict]:
    """`%H\\x01%as\\x01%s` lines -> PR records, newest first, deduped by number. PURE.

    ⚠ ANCHORED AT THE SUBJECT TAIL. `check-backlog-closure.py:107` already paid for this:
    an any-occurrence match fired on 10 of 18 ids, the tail rule on 1, a true positive.
    A commit with no tail was pushed direct to master and is not a PR.
    """
    out, seen = [], set()
    for line in lines:
        parts = line.split("\x01")
        if len(parts) != 3:
            continue
        sha, date, subject = parts
        m = PR_TAIL.search(subject)
        if not m or m.group(1) in seen:
            continue
        seen.add(m.group(1))
        out.append({"sha": sha, "num": m.group(1), "date": date, "subject": subject})
    return out


def files_are_code(files) -> bool:
    """True if any path lies outside this repo's documentation. PURE.

    ⛔ THIS IS A CLAIM ABOUT ONE COMMIT, NOT ABOUT A THREAD. v1 of this plan called the
    result `code` and treated it as "this PR implemented the thread". Measured: PR #147
    (the ADR-0010 header backfill) touches ~26 documents plus three scripts, so it returns
    True on 22 of 47 documents and implemented none of them. The renderer therefore says
    `touched code` and shows the PR's document fan-out; it makes no implementation claim.
    """
    return any(f and not DOC_PATH.match(f) for f in files)
```

- [ ] **Step 4: Run the tests, then UPDATE THE DECLARED COUNT**

Run: `python3 scripts/gen-goals-page.py --self-test` → PASS, `35/35`. Set `:6` to `# 35 cases`.
Run: `python3 scripts/check-selftest-counts.py` → rc=0, or stop.

- [ ] **Step 5: Commit**

```bash
git add scripts/gen-goals-page.py
git commit -m "Read pull requests off a git log, and tell code from documentation"
```

---

### Task 3: The collection layer — asking git, and failing loudly when it cannot answer

**Files:**
- Modify: `scripts/gen-goals-page.py` — collection section, after `last_touched` (`:163-170`; `:170`
  is `return ""`)
- Test: `self_test()`

**Interfaces:**
- Consumes: `prs_from_log`, `files_are_code`.
- Produces: `git_pr_history(path) -> list[dict] | None`; `git_show_files(sha) -> list[str] | None`;
  `annotate_code(prs, show=git_show_files) -> list[dict]` adding `"code": bool | None`.

⚠ **`None` and `[]` must stay distinguishable to the renderer.** Round 1 traced this end to end and
confirmed nothing collapses — keep it that way.

- [ ] **Step 1: Write the failing tests**

```python
    _prs = [{"sha": "aaa", "num": "186", "date": "2026-08-31", "subject": "s"},
            {"sha": "bbb", "num": "187", "date": "2026-08-31", "subject": "t"}]
    _shown = {"aaa": ["scripts/gen-dashboard.py", "docs/x.md"], "bbb": ["docs/x.md"]}
    _out = annotate_code(_prs, lambda sha: _shown.get(sha))
    eq("a PR touching a script is tagged code", _out[0]["code"], True)
    eq("a doc-only PR is not", _out[1]["code"], False)
    eq("an unreadable commit is unknown, not False",
       annotate_code(_prs[:1], lambda sha: None)[0]["code"], None)
    eq("annotate does not lose or reorder records", [p["num"] for p in _out], ["186", "187"])
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python3 scripts/gen-goals-page.py --self-test`
Expected: FAIL — `NameError: name 'annotate_code' is not defined`

- [ ] **Step 3: Write the minimal implementation**

Insert after `:170`:

```python
def git_pr_history(path: pathlib.Path) -> list[dict] | None:
    """PRs that touched `path`, newest first — or None when git cannot answer.

    ⛔ None IS NOT []. None is CANNOT RUN. [] means git answered and found no PR — for a
    path git has never tracked it also exits 0 with empty output, so [] is precisely
    "git names no PR for this path", which is a slightly weaker claim than "no PR touched
    this document". That is the right answer for an unmerged document.

    `--follow` keeps a renamed document's history. Measured 2026-09-11: it currently adds
    PRs for 0 of 47 documents, because nothing has been renamed — so its justification is
    real but untested today. ⚠ Its known hazard is live even so: rename detection is
    similarity-based, and this repo writes dated specs derived from predecessors, so
    --follow can jump into an ancestor's history and inherit its PRs.
    """
    try:
        r = subprocess.run(
            ["git", "log", "--format=%H\x01%as\x01%s", "--follow", "--", str(path)],
            cwd=ROOT, capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0:
        return None
    return prs_from_log(r.stdout.splitlines())


def git_show_files(sha: str) -> list[str] | None:
    """The file list of one commit, or None when git cannot answer.

    ⚠ `.splitlines()`, NOT `.split()`. `git show --name-only` emits one path per line, and
    a path containing a space would split into two entries whose tail matches no DOC_PATH
    branch — turning a documentation PR into a `code` one. No such path exists in this
    repo today; the sibling `git_pr_history` already uses `.splitlines()`, and round 1
    caught the two halves of one insertion disagreeing.
    """
    try:
        r = subprocess.run(["git", "show", "--name-only", "--format=", "-1", sha],
                           cwd=ROOT, capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout.splitlines() if r.returncode == 0 else None


def annotate_code(prs: list[dict], show=git_show_files) -> list[dict]:
    """Add `code`: True / False / None to each PR. `show` is injected so this is testable.

    None means the commit could not be read — NOT that it was documentation.
    """
    cache: dict[str, bool | None] = {}
    out = []
    for p in prs:
        sha = p["sha"]
        if sha not in cache:
            files = show(sha)
            cache[sha] = None if files is None else files_are_code(files)
        out.append({**p, "code": cache[sha]})
    return out
```

- [ ] **Step 4: Run the tests, then UPDATE THE DECLARED COUNT**

Run: `--self-test` → PASS, `39/39`. Set `:6` to `# 39 cases`. Run `check-selftest-counts.py` → rc=0.

- [ ] **Step 5: Commit**

```bash
git add scripts/gen-goals-page.py
git commit -m "Ask git for a document's pull requests, and say so when it cannot answer"
```

---

### Task 4: Assembling threads inside `collect()`, and counting each PR's fan-out

**Files:**
- Modify: `scripts/gen-goals-page.py:173-224` (`collect`); `out = []` is `:207`, the `out.append({…})`
  block is `:211-218`, `"docs": ds,` is `:213`
- Test: `self_test()`

**Interfaces:**
- Consumes: `pair_documents`, `git_pr_history`, `annotate_code`.
- Produces: `thread_prs(thread, history) -> dict` adding `"prs"` and `"pr_error"`; each anchor record
  gains `"threads": list[dict]`; `collect` returns a second value
  `fanout: dict[str, int]` — PR number → how many anchored documents it touched.

⭐ **The fan-out is the retraction's mechanism.** It is global, so it is computed once across all
anchors, not per card.

- [ ] **Step 1: Write the failing tests**

```python
    _t = {"stem": "s", "spec": {"name": "s-design.md", "rel": "a"},
          "plan": {"name": "s.md", "rel": "b"}, "docs": []}
    # ⚠ REAL DATES. Round 1 Blocking B1: the first version used "d" and "e", and since the
    # sort is (date, num) reverse=True, "e" > "d" put PR 2 first — the case asserted
    # ["1","2"] and the implementation produced ["2","1"]. With real dates the ordering is
    # observable, and this case now also dies if `sorted(...)` is deleted.
    _hist = {"a": [{"sha": "x", "num": "1", "date": "2026-08-29", "subject": "u"}],
             "b": [{"sha": "x", "num": "1", "date": "2026-08-29", "subject": "u"},
                   {"sha": "y", "num": "2", "date": "2026-08-31", "subject": "v"}]}
    eq("a thread's PRs are the union over its documents, deduped, NEWEST FIRST",
       [p["num"] for p in thread_prs(_t, _hist.get)["prs"]], ["2", "1"])
    eq("one unreadable document poisons the thread's verdict",
       thread_prs(_t, lambda rel: None if rel == "b" else _hist["a"])["pr_error"], True)
    eq("a fully readable thread reports no error", thread_prs(_t, _hist.get)["pr_error"], False)
    eq("a thread with no documents has no PRs and no error",
       thread_prs({"stem": "s", "spec": None, "plan": None, "docs": []}, _hist.get),
       {"stem": "s", "spec": None, "plan": None, "docs": [], "prs": [], "pr_error": False})

    eq("fan-out counts the documents a PR touched",
       pr_fanout([[{"num": "147"}, {"num": "9"}], [{"num": "147"}]]), {"147": 2, "9": 1})
    # ⭐ ROUND 2 H. This is the case that distinguishes documents from threads: one PR
    # touching BOTH halves of one thread is TWO documents, and the thread-level dedupe
    # would have reported 1 under the label "on N documents".
    eq("a PR touching both halves of one thread counts as two documents",
       pr_fanout([[{"num": "5"}], [{"num": "5"}]]), {"5": 2})
    eq("an unreadable document contributes nothing, and does not crash",
       pr_fanout([None, [{"num": "5"}]]), {"5": 1})

    # ⭐ ROUND 3 H. thread_prs asked only for spec and plan, so a collision's third
    # document never got a history: a PR touching only it vanished from the thread and
    # from the fan-out. This case dies if the loop goes back to the two named slots.
    _t3 = {"stem": "s", "spec": {"name": "a-design.md", "rel": "a"},
           "plan": {"name": "a.md", "rel": "b"},
           "docs": [{"name": "a-design.md", "rel": "a"}, {"name": "a.md", "rel": "b"},
                    {"name": "a-plan.md", "rel": "c"}]}
    _h3 = {"a": [], "b": [], "c": [{"sha": "z", "num": "7", "date": "2026-09-01", "subject": "w"}]}
    eq("a PR reachable only through a collision's extra document is still found",
       [p["num"] for p in thread_prs(_t3, _h3.get)["prs"]], ["7"])
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python3 scripts/gen-goals-page.py --self-test`
Expected: FAIL — `NameError: name 'thread_prs' is not defined`

- [ ] **Step 3: Write the minimal implementation**

Add above the collection banner:

```python
def thread_prs(thread: dict, history) -> dict:
    """Thread + a rel->PRs lookup -> the thread with `prs` and `pr_error`. PURE.

    The union over spec and plan, deduped by PR number, newest first. `history` returns
    None when that document could not be read; ONE such document sets `pr_error`, because
    a shorter list that looks complete is worse than a stated gap.
    """
    merged: dict[str, dict] = {}
    error = False
    # ⚠ EVERY document on the thread, not just spec and plan. `pair_documents` appends
    # all of them to `docs` — spec and plan are members of it — so iterating `docs` is a
    # superset. Round 3: iterating the two named slots meant a collision's third document
    # never got a history, so a PR touching only it vanished from the thread AND from the
    # fan-out that `hist_cache` feeds.
    for d in thread.get("docs") or [x for x in (thread.get("spec"), thread.get("plan")) if x]:
        if not d or not d.get("rel"):
            # ⚠ A document the page cannot ADDRESS is not a document git failed to read,
            # so this does not set `pr_error` — but it is a second place where a missing
            # `rel` means "quietly nothing", and round 3 named it. Unreachable in
            # production: every record built at `:200-205` carries a `rel`.
            continue
        got = history(d["rel"])
        if got is None:
            error = True
            continue
        for p in got:
            merged.setdefault(p["num"], p)
    prs = sorted(merged.values(), key=lambda p: (p["date"], p["num"]), reverse=True)
    return {**thread, "prs": prs, "pr_error": error}


def pr_fanout(histories) -> dict[str, int]:
    """PR number -> how many ANCHORED documents reach it. PURE.

    ⚠ ANCHORED, and the qualifier is load-bearing. A document declaring no anchor never
    enters `collect`'s history cache, so it cannot be counted. `on 22 documents` therefore
    means 22 of the 47 documents this page can see, not 22 of 187. An unqualified
    denominator is the failure this project records most often.

    ⛔ DOCUMENTS, NOT THREADS, and round 2 caught it counting threads while the rendered
    label said documents. `thread_prs` dedupes a PR that touched BOTH a spec and its plan,
    so counting threads under-reports by one for every such PR. Takes the per-document PR
    lists straight from `collect`'s history cache, before any thread-level dedupe.

    ⭐ WHY THIS EXISTS. A PR that touches twenty-two documents did not implement any one of
    them. PR #147 backfilled `Anchor:` headers across the corpus and also touched three
    scripts, so it is `touched code` on 22 of 47 documents. The page renders this number
    beside each PR so a bulk edit is visible as one. A THRESHOLD WAS TESTED AND REJECTED:
    discounting PRs above 2 documents also discards #176, a genuine implementation, and the
    distribution (40/12/3/1/1 documents per PR) gives any cut exactly one data point.
    """
    out: dict[str, int] = {}
    for prs in histories:
        if not prs:                      # None (unreadable) and [] alike contribute nothing
            continue
        for num in {p["num"] for p in prs}:   # one vote per DOCUMENT, not per commit
            out[num] = out.get(num, 0) + 1
    return out
```

In `collect()`, insert immediately **before** `out = []` at `:207`:

```python
    # ⚠ MEASURED COST, round 1 B-perf. This is NOT "double last_touched". `last_touched`
    # is `git log -1`; this is `git log --follow` over full history plus one `git show`
    # per unique sha. Measured 2026-09-11: build 2.4s -> ~10s, about 4.5x, on a hook that
    # fires on every write to any spec, plan, ADR or the registry.
    hist_cache: dict[str, list[dict] | None] = {}

    def history(rel: str):
        if rel not in hist_cache:
            got = git_pr_history(ROOT / rel)
            hist_cache[rel] = None if got is None else annotate_code(got)
        return hist_cache[rel]
```

Add **one** key inside the existing `out.append({...})` dict, immediately after `"docs": ds,` (`:213`):

```python
            "threads": [thread_prs(t, history) for t in pair_documents(ds)],
```

⚠ **`"docs": ds` STAYS** — `build` counts it at `:374` and Task 6 needs that count.

Finally, after `out.sort(...)` and before `return out`, compute the global fan-out and attach it:

```python
    fan = pr_fanout(hist_cache.values())
    for a in out:
        a["fanout"] = fan
```

- [ ] **Step 4: Run the tests, then UPDATE THE DECLARED COUNT**

Run: `--self-test` → PASS, `47/47`. Set `:6` to `# 47 cases`. `check-selftest-counts.py` → rc=0.

Run: `python3 scripts/gen-goals-page.py --out /tmp/goals-check.html && echo BUILD-OK`
Expected: `BUILD-OK`, no traceback on stderr.

- [ ] **Step 5: Commit**

```bash
git add scripts/gen-goals-page.py
git commit -m "Every goal carries its work threads, and a bulk edit is counted as one"
```

---

### Task 5: Rendering the WORK band, and retiring the Documents band

**Files:**
- Modify: `scripts/gen-goals-page.py:362-369` — the Documents band **and** the `</article>` +
  `return` that follow it. ⚠ Round 1 L3: the band is `:362-368` but `:369` is
  `return "\n".join(parts)`, which the replacement block also ends in; replacing `:362-368` alone
  leaves a duplicate unreachable `return`.
- Modify: `scripts/gen-goals-page.py:228-300` (`CSS`; `CSS = """` at `:228`, closing `"""` at `:300`)
- Test: `self_test()`

**Interfaces:**
- Consumes: `collect()`'s `threads` and `fanout`.
- Produces: `render_threads(threads: list[dict], fanout: dict[str, int]) -> str`.

⚠ `<details>/<summary>` is the house pattern — 21 uses in `gen-dashboard.py`, 6 in
`gen-backlog-page.py`, 0 here. Escaping goes through the existing `esc` / `inline_md`.

⛔ **NO `n_code` SUMMARY AND NO `no code PR yet` FLAG.** Both are deleted by the retraction. The only
thread-level flags are `history could not be read` (CANNOT RUN) and `no pull requests`.

- [ ] **Step 1: Write the failing tests**

```python
    _fan = {"186": 1, "187": 1, "147": 22}
    # ⚠ THREE PRs, one per tag. Round 3: with only two, the case named "only the three
    # measured tags can be rendered" was satisfied by a renderer emitting a fourth label
    # for the third state — it constrained two of the three it claimed. Mutation-verified
    # there: renaming the `unknown` branch stayed GREEN with two PRs.
    _th = [{"stem": "2026-08-31-asks", "spec": {"name": "a-design.md", "rel": "ra"},
            "plan": {"name": "a.md", "rel": "rb"}, "docs": [], "pr_error": False,
            "prs": [{"num": "186", "date": "2026-08-31", "subject": "impl", "code": True},
                    {"num": "187", "date": "2026-08-31", "subject": "docs", "code": False},
                    {"num": "188", "date": "2026-08-30", "subject": "unread", "code": None}]}]
    _h = render_threads(_th, _fan)
    eq("the thread renders inside a details element", "<details" in _h, True)
    # ⭐ THE CASE THE USER ASKED FOR: two PRs on one thread must LOOK different.
    eq("the two PRs are distinguishable in the markup",
       _h.count(">touched code<") == 1 and _h.count(">docs only<") == 1, True)
    # ⭐ ROUND 2 M. This was `"implement" not in html`, which passes for `shipped`,
    # `done` or `landed` — the same false claim in other words. Pinning the SET of rendered
    # tag texts fails on any label that is not one of the three measured states.
    eq("only the three measured tags can be rendered",
       sorted(set(re.findall(r'<span class="tag [a-z]+">([^<]+)</span>', _h))),
       ["docs only", "touched code", "unknown"])
    # ⭐ THE RETRACTION, ASSERTED: a 22-document PR is shown as a bulk edit.
    _bulk = [{"stem": "s", "spec": {"name": "s-design.md", "rel": "r"}, "plan": None,
              "docs": [], "pr_error": False,
              "prs": [{"num": "147", "date": "2026-08-01", "subject": "backfill", "code": True}]}]
    eq("a PR touching many documents renders its fan-out",
       "on 22 documents" in render_threads(_bulk, _fan), True)
    # ⭐ ROUND 2 L. This was `"on 1 documents" not in html`, which a renderer saying
    # "on 1 document" passes. Counting the fan-out spans cannot be evaded by wording.
    eq("only the multi-document PR renders a fan-out",
       render_threads(_bulk, _fan).count(" documents</span>"), 1)
    eq("and a single-document thread renders none", _h.count(" documents</span>"), 0)

    _empty = [{"stem": "s", "spec": {"name": "s-design.md", "rel": "r"}, "plan": None,
               "docs": [], "prs": [], "pr_error": False}]
    eq("a missing plan is drawn as absent, not omitted", "no plan" in render_threads(_empty, {}), True)
    eq("a thread git found no PR for says so", "no pull requests" in render_threads(_empty, {}), True)

    # LOAD-BEARING PAIR. The negative below is an absence assertion and passes on an empty
    # string; the positive above it is what kills that. Neither may be deleted alone.
    _broken = [{"stem": "s", "spec": {"name": "s-design.md", "rel": "r"}, "plan": None,
                "docs": [], "prs": [], "pr_error": True}]
    eq("an unreadable history says so instead of showing nothing",
       "could not be read" in render_threads(_broken, {}), True)
    eq("and it does NOT also claim there are no pull requests",
       "no pull requests" in render_threads(_broken, {}), False)

    _unknown = [{"stem": "s", "spec": {"name": "s-design.md", "rel": "r"}, "plan": None,
                 "docs": [], "pr_error": False,
                 "prs": [{"num": "9", "date": "d", "subject": "s", "code": None}]}]
    # `>unknown<` asserts the TEXT NODE. Round 1: `"unknown" in html` also matched the CSS
    # class, so it passed however the visible label changed.
    eq("a PR whose files could not be read is tagged unknown",
       ">unknown<" in render_threads(_unknown, {}), True)

    # ⭐ ROUND 1 H1. Task 1 keeps a collision's extra document; the page must show it.
    _extra = {"name": "s-plan.md", "rel": "rx", "kind": "spec"}
    _coll = [{"stem": "s", "spec": {"name": "s-design.md", "rel": "r"}, "plan": None,
              "docs": [{"name": "s-design.md", "rel": "r"}, _extra],
              "prs": [], "pr_error": False}]
    eq("an extra document on a stem is rendered, not silently dropped",
       "extra document" in render_threads(_coll, {}) and "s-plan.md" in render_threads(_coll, {}),
       True)
    # ⭐ ROUND 2 L. `d["rel"]` raised KeyError on a record without one. `.get` throughout.
    # ⭐ ROUND 3 BLOCKING. The r2 fix changed two `.get` sites and left two `d["rel"]`
    # renders, so this very fixture crashed on the SPEC branch before reaching the
    # extra-document branch it was written to exercise. Both renders now use `.get`.
    eq("a document record with no rel does not crash the renderer",
       "extra document" in render_threads(
           [{"stem": "s", "spec": {"name": "s.md"}, "plan": None,
             "docs": [{"name": "s.md"}, {"name": "other.md"}],
             "prs": [], "pr_error": False}], {}), True)
    eq("and the crash-free path still names the document",
       "other.md" in render_threads(
           [{"stem": "s", "spec": {"name": "s.md"}, "plan": None,
             "docs": [{"name": "s.md"}, {"name": "other.md"}],
             "prs": [], "pr_error": False}], {}), True)

    eq("no threads renders the absence, not an empty box",
       "No spec or plan" in render_threads([], {}), True)
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python3 scripts/gen-goals-page.py --self-test`
Expected: FAIL — `NameError: name 'render_threads' is not defined`

- [ ] **Step 3: Write the minimal implementation**

Add before `render_goal` (`:303`):

```python
def render_threads(threads: list[dict], fanout: dict[str, int]) -> str:
    """The WORK band's body: one collapsible block per spec/plan thread.

    ⛔ MAKES NO IMPLEMENTATION CLAIM. The tag says what the commit touched; the fan-out
    says how many documents it touched. v1 said `code` and summarised `N code PR(s)`, which
    presented PR #147 — a 22-document header backfill — as the implementation of 22
    different goals.
    """
    if not threads:
        return '<span class="absent">No spec or plan declares this goal.</span>'
    parts = []
    for t in threads:
        # TWO thread-level states only, and they are not the same claim: CANNOT RUN beats
        # "git named no PR", because rendering a broken deriver as an honest absence is the
        # failure this project records most often.
        if t["pr_error"]:
            flag = '<span class="absent">history could not be read — treat as NOT MEASURED</span>'
        elif not t["prs"]:
            flag = '<span class="absent">no pull requests</span>'
        else:
            flag = f'<span class="t">{len(t["prs"])} PR(s)</span>'
        parts.append(f'<details class="thread"><summary>{esc(t["stem"])} {flag}</summary>')
        for side, missing in (("spec", "no spec"), ("plan", "no plan")):
            d = t.get(side)
            if d:
                parts.append(f'<div class="prline"><span class="t">{side}</span>'
                             f'<a href="/src/{esc(d.get("rel", ""))}">'
                             f'{esc(d.get("name", "?"))}</a></div>')
            else:
                parts.append(f'<div class="prline"><span class="t">{side}</span>'
                             f'<span class="absent">{missing}</span></div>')
        # A stem claimed by a third document. Kept by `pair_documents`, and rendered here
        # so the collision is visible rather than merely recorded.
        # ⛔ IDENTITY, NOT A KEY, and round 3 paid for the alternative twice. Keying on
        # `d["rel"]` crashed on a record without one; keying on `d.get("rel")` made EVERY
        # rel-less document collapse to the same `None`, so the extra document matched the
        # spec and was dropped — the case written to prove extras render proved the
        # opposite. `pair_documents` appends the SAME dict object it assigns to the slot,
        # so `is` is exact and needs no field at all.
        named = [x for x in (t.get("spec"), t.get("plan")) if x]
        for d in t.get("docs", []):
            if not any(d is x for x in named):
                parts.append(f'<div class="prline"><span class="absent">⚠ extra document '
                             f'on this stem</span>'
                             f'<a href="/src/{esc(d.get("rel", ""))}">'
                             f'{esc(d.get("name", "?"))}</a></div>')
        for p in t["prs"]:
            tag = ("unknown" if p.get("code") is None
                   else "touched code" if p["code"] else "docs only")
            cls = "unknown" if p.get("code") is None else ("code" if p["code"] else "docs")
            n = fanout.get(p["num"], 1)
            fan = f'<span class="t">on {n} documents</span>' if n > 1 else ""
            parts.append(f'<div class="prline"><span class="tag {cls}">{tag}</span>'
                         f'<span class="t">#{esc(p["num"])} · {esc(p["date"])}</span>{fan}'
                         f'<span class="g">{inline_md(p["subject"])}</span></div>')
        parts.append("</details>")
    return "\n".join(parts)
```

Replace `:362-369` (the Documents band **through** the existing `return`) with:

```python
    n_pr = sum(len(t["prs"]) for t in a["threads"])
    parts.append(f'<div class="band"><span class="blab">Work</span>'
                 f'<span class="t">{len(a["threads"])} thread(s) · {n_pr} PR(s) · '
                 f'derived from git at {esc(a.get("head", "?")[:8])}</span>'
                 f'<div class="docs">')
    parts.append(render_threads(a["threads"], a.get("fanout", {})))
    parts.append("</div></div></article>")
    return "\n".join(parts)
```

⚠ **`head` is round 1 M4.** The page now has a **sixth** source — the git log — and
`regen-goals-page.sh` watches five *files*. Merging a PR changes what this band should say and fires
no hook, because a merge is not a `Write`. Rendering the sha the PRs were derived from lets the
reader see the input. Set it in `collect()` beside `fanout`:

```python
    # Guarded like every other git call in this file. Round 2: this was the one new
    # deriver that would abort the whole page build on FileNotFoundError.
    try:
        _r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                            capture_output=True, text=True, timeout=20)
        head = (_r.stdout.strip() if _r.returncode == 0 else "") or "unknown"
    except (OSError, subprocess.SubprocessError):
        head = "unknown"
    for a in out:
        a["fanout"], a["head"] = fan, head
```

and add one sentence to `.claude/hooks/regen-goals-page.sh`'s comment naming git as a source no
`case` arm can match.

Add to `CSS` before the closing `"""` at `:300`:

```css
  .thread{border-top:1px solid var(--rule);padding:.4rem 0}
  .thread summary{cursor:pointer;font-family:ui-monospace,monospace;font-size:.86rem}
  .prline{display:flex;gap:.5rem;align-items:baseline;padding:.15rem 0 .15rem 1rem}
  .tag{font-size:.72rem;padding:.05rem .35rem;border-radius:3px;
       background:var(--structure-bg);color:var(--structure)}
  .tag.docs{background:var(--pending-bg);color:var(--pending)}
  .tag.unknown{background:var(--rule);color:var(--ink)}
```

⚠ **`.tag.unknown` uses `--ink`, not `--ink-faint`.** Round 1 M3 measured `--rule`/`--ink-faint` at
**2.45:1 light and 3.47:1 dark** — both fail WCAG AA at this 11.5px size, and it is the tag for
CANNOT RUN, the one state this design argues hardest for.

- [ ] **Step 4: Run the tests, verify contrast, then UPDATE THE DECLARED COUNT**

Run: `--self-test` → PASS, `62/62`. Set `:6` to `# 62 cases`. `check-selftest-counts.py` → rc=0.

**Measure the contrast — do not assume the fix worked:**

```bash
python3 - <<'PY'
def lum(h):
    c=[int(h[i:i+2],16)/255 for i in (1,3,5)]
    c=[(x/12.92 if x<=.03928 else ((x+.055)/1.055)**2.4) for x in c]
    return .2126*c[0]+.7152*c[1]+.0722*c[2]
def ratio(a,b):
    L1,L2=sorted((lum(a),lum(b)),reverse=True); return (L1+.05)/(L2+.05)
# read the real values out of CSS rather than retyping them
import re,pathlib
css=pathlib.Path('scripts/gen-goals-page.py').read_text()
v={m.group(1):m.group(2) for m in re.finditer(r'--([a-z-]+):(#[0-9a-f]{6})',css)}
for name,bg,fg in [("tag","structure-bg","structure"),("tag.docs","pending-bg","pending"),
                   ("tag.unknown","rule","ink")]:
    r=ratio(v[bg],v[fg]); print(f"  {name:12s} {r:5.2f}:1 {'PASS' if r>=4.5 else 'FAIL'}")
PY
```

Expected: all three **PASS** (≥4.5:1) in the light block. Repeat for the dark block's values.
**A FAIL here is a stop.** This repo shipped PR #175 with a link-contrast defect no test could see.

**Build and check the real page:**

```bash
python3 scripts/gen-goals-page.py --out /tmp/goals-check.html
grep -c '<details class="thread"' /tmp/goals-check.html   # expect 41 (measured 2026-09-11)
grep -c '>no plan<'              /tmp/goals-check.html    # expect 21   (measured 2026-09-11)
grep -c '>no spec<'              /tmp/goals-check.html    # expect 14   — 21+14 = the 35 unpaired
grep -c '>touched code<'         /tmp/goals-check.html    # expect > 0
grep -c '>docs only<'            /tmp/goals-check.html    # expect >= 1
grep -c 'on 22 documents'        /tmp/goals-check.html    # expect 22 — PR #147's fan-out
```

⚠ **The `>no plan<` count is round 1 M2** — 35 of 41 threads show one half absent, and nothing
watched it before. ⚠⚠ **It splits 21 missing a plan and 14 missing a spec**; round 3 measured this
against a built page after the plan asserted a flat 35 for the `no plan` grep alone. Checking one
arm and calling it the pairing rate is how a half-measurement passes for a whole one. ⚠ **The `on 22 documents` count is the retraction's falsifier in anger**: a zero
means `pr_fanout` is not discriminating and the page is back to presenting a bulk edit as an
implementation.

- [ ] **Step 5: Commit**

```bash
git add scripts/gen-goals-page.py .claude/hooks/regen-goals-page.sh
git commit -m "A goal shows the work that pursued it, and a bulk edit cannot pose as an implementation"
```

---

### Task 6: Saying what the page cannot see

**Files:**
- Modify: `scripts/gen-goals-page.py:372-407` (`build`; the single `return f"""…"""` is `:376-407`,
  and the existing `<strong>{docs}</strong> documents` phrasing is at `:385`)
- Test: `self_test()`

**Interfaces:**
- Consumes: `collect()` output.
- Produces: `excluded_count(total: int, shown: int) -> int` — pure, refusing on `shown > total`.

⚠ **Spec falsifier F8.** Measured 2026-09-11: the page renders **47 of 187** documents; **140** are
excluded for declaring no anchor. That is the registry's deliberate living/dead split, but an
unstated denominator is how a partial view reads as a complete one.

- [ ] **Step 1: Write the failing test**

`_raises` does **not** exist in this file (round 1 M6 — it lives in four *other* scripts). Add it
**above** its first use, inside `self_test()`:

```python
    def _raises(fn, exc) -> bool:
        try:
            fn()
        except exc:
            return True
        return False

    eq("the excluded count is total minus shown", excluded_count(10, 4), 6)
    eq("nothing excluded reads as zero", excluded_count(4, 4), 0)
    eq("showing more than exist is a refusal, not a negative",
       _raises(lambda: excluded_count(4, 10), ValueError), True)
```

⚠ **Deliberately synthetic numbers.** v1 used `excluded_count(186, 46)`, which reads as a corpus
claim and invites someone to "correct" it when the corpus moves. These are arithmetic.

- [ ] **Step 2: Run it to verify it fails**

Run: `python3 scripts/gen-goals-page.py --self-test`
Expected: FAIL — `NameError: name 'excluded_count' is not defined`

- [ ] **Step 3: Write the minimal implementation**

```python
def excluded_count(total: int, shown: int) -> int:
    """Documents present but not rendered, because they declare no anchor. PURE.

    ⛔ REFUSES on shown > total. That can only mean the two numbers were counted over
    different populations, which is the most-recorded measurement defect in this repo.
    A negative rendered as "-36 excluded" would be believed. Note the branch is
    unreachable in production, since both counts come from SUBDIRS — the case exercises it
    directly and the guard is there for a future caller, not for today's.
    """
    if shown > total:
        raise ValueError(f"shown ({shown}) exceeds total ({total}) — populations disagree")
    return total - shown
```

In `build`, after `docs = sum(...)` at `:374`, add:

```python
    total_docs = sum(1 for sub in SUBDIRS for _ in (DOCS / sub).glob("*.md"))
    hidden = excluded_count(total_docs, docs)
```

⚠ **`total_docs` counts `SUBDIRS`, i.e. `superpowers/specs` and `superpowers/plans` — not all of
`docs/superpowers/`.** Today those are the only two subdirectories, so a sentence saying "under
`docs/superpowers/`" would be true by coincidence of the tree's shape. **Name the two directories in
the rendered text**, as below.

Then the literal edit inside the `return f"""…"""`. `:385` currently reads:

```html
    <strong>{docs}</strong> documents, <strong>{spined}</strong> with a milestone spine.
```

Replace that one line with:

```html
    <strong>{docs}</strong> documents, <strong>{spined}</strong> with a milestone spine.
    <span class="absent">{hidden} more under docs/superpowers/specs and /plans declare no
    anchor and are not shown.</span>
```

⚠ It is inside an existing f-string — do **not** add an `f` prefix or extra quotes, and keep the
`<strong>` markup. Round 1 H2: v1 gave a bare `f"…"` fragment here, which is not an edit an
implementer can apply mechanically.

- [ ] **Step 4: Run the tests, then UPDATE THE DECLARED COUNT**

Run: `--self-test` → PASS, `65/65`. Set `:6` to `# 65 cases`. `check-selftest-counts.py` → rc=0.

Run: `python3 scripts/gen-goals-page.py --out /tmp/goals-check.html && grep -o '[0-9]* more under docs/superpowers' /tmp/goals-check.html`
Expected: `140 more under docs/superpowers` **as measured 2026-09-11** — and note it passes today
partly by cancellation, since both the total and the anchored count rose by one when this plan was
written. Re-derive rather than trusting the constant.

- [ ] **Step 5: Commit**

```bash
git add scripts/gen-goals-page.py
git commit -m "The goals page says how many documents it cannot see"
```

---

## After the last task

- [ ] Full gate set: `check-docs.py`, `check-anchors.py`, `check-ratchet-contract.py`,
      `check-selftest-counts.py`, `check-review-rounds.py`. **A gate that cannot run is a failure.**
- [ ] **Browser pass, not optional.** Open `/goals`, confirm a thread expands; that `#186` and `#187`
      on the ask-choices thread read differently; that PR #147 shows `on 22 documents`; that the
      theme toggle still works and all three tags stay legible in both themes.
- [ ] Record a dashboard entry (`check-dashboard-entry.py` refuses a branch without one).
- [ ] **Measure the real build time** and record it against the 2.4s baseline. If it exceeds ~10s,
      cache `git log --follow` output by `HEAD` sha before merging — the regen hook is synchronous
      and fires on every write to a spec, plan, ADR or the registry.
- [ ] `scripts/mutations/` — ⟳ **CORRECTED 2026-09-12, and the correction matters.** This said the
      obligation was *"under `check-ratchet-contract.py`"*. **It is not.** That guard discovers
      `check-*.py` GUARDS and `gen-goals-page.py` is not in its population, which is why it returns
      rc=0 here. The real mechanism is `EXPECTED_MUTATIONS` in `check-plan-code.py`: **40 files
      pinned, and `gen-goals-page.py` is not one of them** — while five of its six sibling generators
      are (`gen-dashboard`, `gen-backlog-page`, `brief-compose`, `page_chrome`, `page_markup`).
      ⚠ **The gap is PRE-EXISTING, not introduced by this plan** — but this plan adds ~540 lines of
      new rules to the one generator nothing mutates, so it is now the largest unmutated surface of
      its kind in the repo. Cover the rules
      that can silently weaken: `PR_TAIL`'s `$` anchor, each `DOC_PATH` branch, `git_show_files`'
      `.splitlines()`, `git_pr_history`'s `None`-vs-`[]` return, `thread_prs`' `pr_error`,
      `pr_fanout`'s counting, and the extra-document render. **Each must go red via the case it
      names.** Round 1 also suggests one worth more than any of these: rename a fixture document and
      assert `--follow` does not inherit its ancestor's PRs.

## Not in this plan — owed by the spec

- **Direct work — PRs with no spec or plan.** Spec §5's card has a `direct work, no document` bucket
  and this plan does not build it, which round 1 raised. It needs §3.2's path-attribution rules,
  which are their own body of work. **Named as owed, not dropped.** Round 1 measured that removing
  the Documents band does *not* orphan the Backlog band, so the card is coherent without it.
- **§3.3** — the `Bundle` column becoming controlled goal names (~70 rows to classify).
- **§4** — the done/active/dormant lifecycle, which depends on §3.3.
- **§5's BACKLOG section**, which depends on §3.3.
