# Goal Work Threads Implementation Plan

> **Anchor:** `status-visibility` — **ADR:** none
> **Goal:** A person who was away can see the current state, what changed, and what needs them —
> without reading the chat transcript.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Each goal card on `/goals` shows the work that pursued it as `spec → plan → PR` threads,
with every PR tagged by whether it touched code — so a reader can find the implementation, not just
the documents.

**Architecture:** Pure functions parse and pair; a thin collection layer shells out to `git`; the
renderer consumes records. This mirrors `gen-goals-page.py`'s existing three-band structure
(`pure parsing` / `collection` / `rendering`) and keeps every new rule unit-testable without a repo.

**Tech Stack:** Python 3, stdlib only. `subprocess` for git. No new dependencies.

**Spec:** [`docs/superpowers/specs/2026-09-11-goal-backlog-pr-join-design.md`](../specs/2026-09-11-goal-backlog-pr-join-design.md) **v3**.

⚠ **THIS IS PLAN 1 OF 2.** The spec covers two separable subsystems. This plan needs **no new
declared data** and ships a working improvement alone. Plan 2 — the `Bundle` column becoming
controlled goal names (spec §3.3), and the done/active/dormant lifecycle (§4) which depends on it —
is deliberately not here. Splitting was the writing-plans scope check, not a scope cut: §3.3 and §4
remain owed.

## Global Constraints

Copied verbatim from the spec and the repo's process documents. Every task's requirements include
these.

- **Never re-implement another script's rule.** Call the owner's function. Seven recorded instances
  of a second implementation drifting; **two of them occurred while measuring for this spec**.
- **A gate or deriver that cannot run is a FAILURE, not a pass.** If git cannot answer, the page must
  say *CANNOT RUN* — never render an empty thread as though it were a true absence.
- **`docs/anchors.md` holds names, not state.** Nothing in this plan writes to it. Every value is
  computed at render time.
- **Pure functions take text or records and return records.** Anything touching the filesystem or
  `subprocess` lives in the collection section (`gen-goals-page.py:162` onward), never above it.
- **Self-test style is the file's own:** `eq(label, got, want)` inside `self_test()`
  (`gen-goals-page.py:411-419`), counted dynamically and printed as `N/M self-test cases passed`.
- **Every case must be able to FAIL.** An assertion that deleting the subject would also satisfy is
  not a test — 12 unfalsifiable cases across 8 guards were paid for in this repo already.

---

### Task 1: Thread identity — pairing a spec with its plan

**Files:**
- Modify: `scripts/gen-goals-page.py` — add to the pure-parsing section, after `parse_roots` (ends `:160`)
- Test: `scripts/gen-goals-page.py` `self_test()` (`:411`)

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces: `doc_stem(name: str) -> str` and
  `pair_documents(docs: list[dict]) -> list[dict]`, each thread being
  `{"stem": str, "spec": dict|None, "plan": dict|None, "docs": list[dict]}`.
  Input records are the dicts `collect()` already builds at `:200-205` — keys `name`, `rel`, `goal`,
  `dated`, `touched`, `kind` (`"spec"` or `"plan"`), `milestones`.

- [ ] **Step 1: Write the failing tests**

Add inside `self_test()`, immediately before the `print(f"\n{cases - failures}...")` line:

```python
    eq("stem strips -design", doc_stem("2026-08-29-retarget-design.md"), "2026-08-29-retarget")
    eq("stem strips -plan", doc_stem("2026-08-28-dashboard-plan.md"), "2026-08-28-dashboard")
    eq("a bare name is already a stem", doc_stem("2026-08-29-retarget.md"), "2026-08-29-retarget")
    eq("only a TRAILING suffix is stripped",
       doc_stem("2026-09-01-design-review-notes.md"), "2026-09-01-design-review-notes")

    _s = {"name": "2026-08-29-x-design.md", "kind": "spec"}
    _p = {"name": "2026-08-29-x.md", "kind": "plan"}
    eq("a spec and its plan share one thread", len(pair_documents([_s, _p])), 1)
    eq("the thread names both halves",
       [pair_documents([_s, _p])[0][k]["name"] for k in ("spec", "plan")],
       ["2026-08-29-x-design.md", "2026-08-29-x.md"])
    eq("a spec with no plan is a thread with an empty plan slot",
       pair_documents([_s])[0]["plan"], None)
    eq("a plan with no spec is a thread with an empty spec slot",
       pair_documents([_p])[0]["spec"], None)
    eq("threads sort newest stem first",
       [t["stem"] for t in pair_documents([{"name": "2026-01-01-a.md", "kind": "plan"}, _p])],
       ["2026-08-29-x", "2026-01-01-a"])
    # ⚠ A COLLISION MUST NOT VANISH. Two specs on one stem would fuse two threads
    # silently; the extra is kept in `docs`, so the thread has 3 documents rather than 2.
    _s2 = {"name": "2026-08-29-x-plan.md", "kind": "spec"}
    eq("a second document in a slot is kept, not dropped",
       len(pair_documents([_s, _p, _s2])[0]["docs"]), 3)
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python3 scripts/gen-goals-page.py --self-test`
Expected: FAIL — `NameError: name 'doc_stem' is not defined`

- [ ] **Step 3: Write the minimal implementation**

Insert after `parse_roots` (i.e. after line 160, before the `# ---- collection` banner at `:162`):

```python
STEM_SUFFIX = re.compile(r"-(design|plan)$")


def doc_stem(name: str) -> str:
    """Filename -> the stem a spec and its plan share. PURE.

    `2026-08-29-x-design.md` and `2026-08-29-x.md` both give `2026-08-29-x`.

    ⚠ BOTH suffixes are stripped, and the second one was measured rather than assumed.
    2026-09-11: 91 specs end `-design` and 3 are bare; 91 plans are bare and 1 ends `-plan`.
    Stripping `-design` alone pairs 60; stripping both pairs 61.
    """
    base = name[:-3] if name.endswith(".md") else name
    return STEM_SUFFIX.sub("", base)


def pair_documents(docs: list[dict]) -> list[dict]:
    """Documents -> threads, newest stem first. PURE.

    A thread is {stem, spec, plan, docs}. EITHER SIDE MAY BE None and neither is an error:
    a spec with no plan is work not yet planned; a plan with no spec was written without
    one. Both are real states and the card draws them as absent rather than omitting them.

    ⛔ A stem claimed by two specs would FUSE two threads invisibly. Measured 2026-09-11:
    no stem is claimed by more than two files across the corpus. The extra is nonetheless
    kept in `docs`, so a future collision surfaces as a three-document thread instead of a
    disappearance — the failure this project keeps paying for is the silent one.
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

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 scripts/gen-goals-page.py --self-test`
Expected: PASS, case count risen by 10.

- [ ] **Step 5: Commit**

```bash
git add scripts/gen-goals-page.py
git commit -m "A spec and its plan are one thread, and a collision cannot vanish"
```

---

### Task 2: Reading pull requests out of a git log — the pure half

**Files:**
- Modify: `scripts/gen-goals-page.py` — pure-parsing section, after `pair_documents`
- Test: `scripts/gen-goals-page.py` `self_test()`

**Interfaces:**
- Consumes: nothing.
- Produces: `prs_from_log(lines: Sequence[str]) -> list[dict]` returning
  `{"sha": str, "num": str, "date": str, "subject": str}` newest first, deduped by `num`;
  and `files_are_code(files: Iterable[str]) -> bool`.

- [ ] **Step 1: Write the failing tests**

```python
    _lg = ["aaa\x012026-08-29\x01Retire the plan dependency (#176)",
           "bbb\x012026-08-31\x01Asks state their choices (#186)",
           "ccc\x012026-08-31\x01Asks state their choices (#186)",
           "ddd\x012026-07-01\x01a direct commit with no PR"]
    eq("a squash subject yields its PR number",
       [p["num"] for p in prs_from_log(_lg)], ["176", "186"])
    eq("the date travels with the PR", prs_from_log(_lg)[0]["date"], "2026-08-29")
    # A commit with no `(#N)` tail was pushed straight to master. It is not a PR, and
    # counting it would inflate every thread.
    eq("a commit with no PR tail is dropped", len(prs_from_log(_lg)), 2)
    eq("a malformed line is skipped, not crashed on", prs_from_log(["garbage"]), [])
    eq("an empty log yields no PRs", prs_from_log([]), [])
    # ⚠ `(#N)` must be at the TAIL. `check-backlog-closure.py:107` pays for this rule
    # already: an any-occurrence match fired on 10 of 18 ids, the tail rule on 1.
    eq("a PR-looking number mid-subject is not the PR",
       prs_from_log(["e\x012026-01-01\x01mentions (#99) in passing, no tail"]), [])

    eq("a script path is code", files_are_code(["scripts/gen-goals-page.py"]), True)
    eq("a doc path is not code", files_are_code(["docs/superpowers/specs/x.md"]), False)
    eq("one code file among docs makes it a code PR",
       files_are_code(["docs/backlog.md", "lib/storage.ts"]), True)
    eq("an empty file list is not code", files_are_code([]), False)
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python3 scripts/gen-goals-page.py --self-test`
Expected: FAIL — `NameError: name 'prs_from_log' is not defined`

- [ ] **Step 3: Write the minimal implementation**

```python
PR_TAIL = re.compile(r"\(#(\d+)\)\s*$")
DOC_PATH = re.compile(r"^(docs/|\.remember/|README)")


def prs_from_log(lines) -> list[dict]:
    """`%H\\x01%as\\x01%s` lines -> PR records, newest first, deduped by number. PURE.

    ⚠ ANCHORED AT THE SUBJECT TAIL, and the alternative was measured elsewhere in this
    repo: `check-backlog-closure.py:107` records that an any-occurrence match fired on 10
    of 18 ids while the tail rule fired on 1, which was a true positive. A commit with no
    tail was pushed direct to master and is not a PR.
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
    """True if any path lies outside the documentation tree. PURE.

    THE DISCRIMINATOR the spec's v3 rests on: it separates the PR that IMPLEMENTED a
    thread from a documentation follow-up touching the same spec. Measured 2026-09-11 on
    one thread — `git log --follow` reaches both #186 (touches code) and #187 (docs only),
    and they are indistinguishable without this.
    """
    return any(f and not DOC_PATH.match(f) for f in files)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 scripts/gen-goals-page.py --self-test`
Expected: PASS, case count risen by 10.

- [ ] **Step 5: Commit**

```bash
git add scripts/gen-goals-page.py
git commit -m "Read pull requests off a git log, and tell code from documentation"
```

---

### Task 3: The collection layer — asking git, and failing loudly when it cannot answer

**Files:**
- Modify: `scripts/gen-goals-page.py` — collection section, beside `last_touched` (`:163-170`)
- Test: `scripts/gen-goals-page.py` `self_test()`

**Interfaces:**
- Consumes: `prs_from_log`, `files_are_code` (Task 2).
- Produces: `git_pr_history(path: pathlib.Path) -> list[dict] | None` — `None` means **git could not
  answer**, an empty list means **no PRs**; and
  `annotate_code(prs: list[dict], show: Callable[[str], list[str] | None]) -> list[dict]`, adding
  `"code": bool | None` to each record.

⚠ **`None` and `[]` must stay distinguishable all the way to the renderer.** They are the CANNOT RUN
and the true-absence cases, and this project has recorded a check reporting a clean verdict over a
population it could not read.

- [ ] **Step 1: Write the failing tests**

`annotate_code` takes its `git show` as a parameter precisely so it can be tested without a repo.

```python
    _prs = [{"sha": "aaa", "num": "186", "date": "2026-08-31", "subject": "s"},
            {"sha": "bbb", "num": "187", "date": "2026-08-31", "subject": "t"}]
    _shown = {"aaa": ["scripts/gen-dashboard.py", "docs/x.md"], "bbb": ["docs/x.md"]}
    _out = annotate_code(_prs, lambda sha: _shown.get(sha))
    eq("the implementing PR is tagged code", _out[0]["code"], True)
    eq("the doc-only follow-up is not", _out[1]["code"], False)
    # ⚠ CANNOT RUN is a THIRD value. If `git show` fails, the tag is unknown — rendering
    # that as `docs only` would assert something never measured.
    eq("an unreadable commit is unknown, not False",
       annotate_code(_prs[:1], lambda sha: None)[0]["code"], None)
    eq("annotate does not lose or reorder records", [p["num"] for p in _out], ["186", "187"])
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python3 scripts/gen-goals-page.py --self-test`
Expected: FAIL — `NameError: name 'annotate_code' is not defined`

- [ ] **Step 3: Write the minimal implementation**

Insert after `last_touched` (after `:170`):

```python
def git_pr_history(path: pathlib.Path) -> list[dict] | None:
    """PRs that touched `path`, newest first — or None when git cannot answer.

    ⛔ None IS NOT []. None is CANNOT RUN; [] is a document no PR has touched, which is
    the true state of an unmerged document. Collapsing them would render a broken deriver
    as an honest absence, and that is the failure this repo names most often.

    `--follow` so a renamed document keeps its history.
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
    """The file list of one commit, or None when git cannot answer."""
    try:
        r = subprocess.run(["git", "show", "--name-only", "--format=", "-1", sha],
                           cwd=ROOT, capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout.split() if r.returncode == 0 else None


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

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 scripts/gen-goals-page.py --self-test`
Expected: PASS, case count risen by 4.

- [ ] **Step 5: Commit**

```bash
git add scripts/gen-goals-page.py
git commit -m "Ask git for a document's pull requests, and say so when it cannot answer"
```

---

### Task 4: Assembling threads inside `collect()`

**Files:**
- Modify: `scripts/gen-goals-page.py:173-224` (`collect`)
- Test: `scripts/gen-goals-page.py` `self_test()`

**Interfaces:**
- Consumes: `pair_documents` (Task 1), `git_pr_history` + `annotate_code` (Task 3).
- Produces: each anchor record in `collect()`'s output gains
  `"threads": list[dict]` — every thread from Task 1 plus `"prs": list[dict] | None` — and
  `"pr_error": bool`, True when any document's history could not be read.

- [ ] **Step 1: Write the failing test**

`thread_prs` is factored out as a pure merge so it is testable without git.

```python
    _t = {"stem": "s", "spec": {"name": "s-design.md", "rel": "a"},
          "plan": {"name": "s.md", "rel": "b"}, "docs": []}
    _hist = {"a": [{"sha": "x", "num": "1", "date": "d", "subject": "u"}],
             "b": [{"sha": "x", "num": "1", "date": "d", "subject": "u"},
                   {"sha": "y", "num": "2", "date": "e", "subject": "v"}]}
    eq("a thread's PRs are the UNION over its documents, deduped",
       [p["num"] for p in thread_prs(_t, _hist.get)["prs"]], ["1", "2"])
    # ⚠ If ANY half is unreadable the thread's PR list is a partial view, and saying so
    # beats showing a shorter list that looks complete.
    eq("one unreadable document poisons the thread's verdict",
       thread_prs(_t, lambda rel: None if rel == "b" else _hist["a"])["pr_error"], True)
    eq("a fully readable thread reports no error",
       thread_prs(_t, _hist.get)["pr_error"], False)
    eq("a thread with no documents has no PRs and no error",
       thread_prs({"stem": "s", "spec": None, "plan": None, "docs": []}, _hist.get),
       {"stem": "s", "spec": None, "plan": None, "docs": [], "prs": [], "pr_error": False})
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python3 scripts/gen-goals-page.py --self-test`
Expected: FAIL — `NameError: name 'thread_prs' is not defined`

- [ ] **Step 3: Write the minimal implementation**

Add beside the other pure functions (before the collection banner):

```python
def thread_prs(thread: dict, history) -> dict:
    """Thread + a rel->PRs lookup -> the thread with `prs` and `pr_error`. PURE.

    The union over the thread's spec and plan, deduped by PR number and newest first.
    `history` returns None when that document could not be read; ONE such document sets
    `pr_error`, because a shorter list that looks complete is worse than a stated gap.
    """
    merged: dict[str, dict] = {}
    error = False
    for side in ("spec", "plan"):
        d = thread.get(side)
        if not d:
            continue
        got = history(d["rel"])
        if got is None:
            error = True
            continue
        for p in got:
            merged.setdefault(p["num"], p)
    prs = sorted(merged.values(), key=lambda p: (p["date"], p["num"]), reverse=True)
    return {**thread, "prs": prs, "pr_error": error}
```

Then in `collect()`, replace the `out.append({...})` block at `:211-218` so each record carries
threads. Insert immediately before `out = []` at `:207`:

```python
    # One git call per document, cached by rel: `collect` already pays one per document for
    # `last_touched`, so this doubles that cost rather than multiplying it. The PR->files
    # lookup behind `annotate_code` caches by sha across every thread.
    hist_cache: dict[str, list[dict] | None] = {}

    def history(rel: str):
        if rel not in hist_cache:
            got = git_pr_history(ROOT / rel)
            hist_cache[rel] = None if got is None else annotate_code(got)
        return hist_cache[rel]
```

and add **one** key inside the existing `out.append({...})` dict, immediately after the
`"docs": ds,` line at `:213`:

```python
            "threads": [thread_prs(t, history) for t in pair_documents(ds)],
```

⚠ **`"docs": ds` STAYS.** `build` counts it at `:374` and Task 6 needs that count; removing it here
would break Task 6 while its own tests still pass, because they never touch `collect`. There is no
separate `pr_error` key on the anchor record — the renderer reads it per thread, which is the level
it is true at.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 scripts/gen-goals-page.py --self-test`
Expected: PASS, case count risen by 4.

Then run the real generator to confirm it still builds against the live repo:

Run: `python3 scripts/gen-goals-page.py --out /tmp/goals-check.html && echo BUILD-OK`
Expected: `BUILD-OK`, and stderr carries no traceback.

- [ ] **Step 5: Commit**

```bash
git add scripts/gen-goals-page.py
git commit -m "Every goal carries its work threads, and a partial history says so"
```

---

### Task 5: Rendering the WORK band, and retiring the Documents band

**Files:**
- Modify: `scripts/gen-goals-page.py:362-368` (the Documents band inside `render_goal`)
- Modify: `scripts/gen-goals-page.py:228-302` (`CSS`) — add `.thread`, `.prline`, `.tag` rules
- Test: `scripts/gen-goals-page.py` `self_test()`

**Interfaces:**
- Consumes: `collect()`'s `threads` key (Task 4).
- Produces: `render_threads(threads: list[dict]) -> str`.

⚠ **`<details>/<summary>` is the house pattern — 21 uses in `gen-dashboard.py`, 6 in
`gen-backlog-page.py`, 0 here.** Reuse the markup; do not invent a collapsible.

⚠ **Escaping goes through the file's existing `esc` and `inline_md`.** A second escaper would be a
second implementation of one rule.

- [ ] **Step 1: Write the failing tests**

```python
    _th = [{"stem": "2026-08-31-asks", "spec": {"name": "a-design.md", "rel": "ra"},
            "plan": {"name": "a.md", "rel": "rb"}, "docs": [], "pr_error": False,
            "prs": [{"num": "186", "date": "2026-08-31", "subject": "impl", "code": True},
                    {"num": "187", "date": "2026-08-31", "subject": "docs", "code": False}]}]
    _h = render_threads(_th)
    eq("the thread renders inside a details element", "<details" in _h, True)
    eq("the implementing PR is marked code", "#186" in _h and ">code<" in _h, True)
    eq("the doc-only PR is marked as such", "docs only" in _h, True)
    # ⭐ THE CASE THE USER ASKED FOR: two PRs on one thread must LOOK different.
    eq("the two PRs are distinguishable in the markup",
       _h.count(">code<") == 1 and _h.count(">docs only<") == 1, True)

    _empty = [{"stem": "s", "spec": {"name": "s-design.md", "rel": "r"}, "plan": None,
               "docs": [], "prs": [], "pr_error": False}]
    eq("a missing plan is drawn as absent, not omitted", "no plan" in render_threads(_empty), True)
    eq("a thread with no code PR is called out",
       "no code PR yet" in render_threads(_empty), True)

    _broken = [{"stem": "s", "spec": {"name": "s-design.md", "rel": "r"}, "plan": None,
                "docs": [], "prs": [], "pr_error": True}]
    # ⛔ CANNOT RUN must not read as "nothing shipped".
    eq("an unreadable history says so instead of showing nothing",
       "could not be read" in render_threads(_broken), True)
    eq("and it does NOT also claim there is no code PR",
       "no code PR yet" in render_threads(_broken), False)

    _unknown = [{"stem": "s", "spec": {"name": "s-design.md", "rel": "r"}, "plan": None,
                 "docs": [], "pr_error": False,
                 "prs": [{"num": "9", "date": "d", "subject": "s", "code": None}]}]
    eq("a PR whose files could not be read is tagged unknown",
       "unknown" in render_threads(_unknown), True)

    eq("no threads renders the absence, not an empty box",
       "No spec or plan" in render_threads([]), True)
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python3 scripts/gen-goals-page.py --self-test`
Expected: FAIL — `NameError: name 'render_threads' is not defined`

- [ ] **Step 3: Write the minimal implementation**

Add before `render_goal` (`:303`):

```python
def render_threads(threads: list[dict]) -> str:
    """The WORK band's body: one collapsible block per spec/plan thread.

    ⚠ `<details>/<summary>` is this project's existing collapsible — 21 uses in
    `gen-dashboard.py`, 6 in `gen-backlog-page.py`. Reused, not reinvented.
    """
    if not threads:
        return '<span class="absent">No spec or plan declares this goal.</span>'
    parts = []
    for t in threads:
        n_code = sum(1 for p in t["prs"] if p.get("code") is True)
        # THREE outcomes, and the third is why `pr_error` exists: a thread with no code PR
        # is a real finding; a thread whose history could not be READ is not a finding at
        # all, and rendering them the same would launder a broken deriver into a fact.
        if t["pr_error"]:
            flag = '<span class="absent">history could not be read — treat as NOT MEASURED</span>'
        elif not n_code:
            flag = '<span class="absent">⚠ no code PR yet</span>'
        else:
            flag = f'<span class="t">{n_code} code PR(s)</span>'
        parts.append(f'<details class="thread"><summary>{esc(t["stem"])} {flag}</summary>')
        for side, missing in (("spec", "no spec"), ("plan", "no plan")):
            d = t.get(side)
            if d:
                parts.append(f'<div class="prline"><span class="t">{side}</span>'
                             f'<a href="/src/{esc(d["rel"])}">{esc(d["name"])}</a></div>')
            else:
                parts.append(f'<div class="prline"><span class="t">{side}</span>'
                             f'<span class="absent">{missing}</span></div>')
        for p in t["prs"]:
            tag = "unknown" if p.get("code") is None else ("code" if p["code"] else "docs only")
            parts.append(f'<div class="prline"><span class="tag {tag.split()[0]}">{tag}</span>'
                         f'<span class="t">#{esc(p["num"])} · {esc(p["date"])}</span>'
                         f'<span class="g">{inline_md(p["subject"])}</span></div>')
        parts.append("</details>")
    return "\n".join(parts)
```

Then replace the Documents band at `:362-368` with:

```python
    n_pr = sum(len(t["prs"]) for t in a["threads"])
    parts.append(f'<div class="band"><span class="blab">Work</span>'
                 f'<span class="t">{len(a["threads"])} thread(s) · {n_pr} PR(s)</span>'
                 f'<div class="docs">')
    parts.append(render_threads(a["threads"]))
    parts.append("</div></div></article>")
    return "\n".join(parts)
```

Add to `CSS` (inside the existing string, after the `.doc` rules):

```css
  .thread{border-top:1px solid var(--rule);padding:.4rem 0}
  .thread summary{cursor:pointer;font-family:ui-monospace,monospace;font-size:.86rem}
  .prline{display:flex;gap:.5rem;align-items:baseline;padding:.15rem 0 .15rem 1rem}
  .tag{font-size:.72rem;padding:.05rem .35rem;border-radius:3px;
       background:var(--structure-bg);color:var(--structure)}
  .tag.docs{background:var(--pending-bg);color:var(--pending)}
  .tag.unknown{background:var(--rule);color:var(--ink-faint)}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 scripts/gen-goals-page.py --self-test`
Expected: PASS, case count risen by 10.

Then build and eyeball the real page:

```bash
python3 scripts/gen-goals-page.py --out /tmp/goals-check.html
grep -c '<details class="thread"' /tmp/goals-check.html   # expect > 20
grep -c 'class="tag code"' /tmp/goals-check.html          # expect > 0
grep -c 'class="tag docs"' /tmp/goals-check.html          # expect >= 1
```

⚠ **The third count is the falsifier-in-anger.** Measured 2026-09-11 there is exactly one doc-only
thread in the corpus; a zero here means `files_are_code` is not discriminating and F7a has failed.

- [ ] **Step 5: Commit**

```bash
git add scripts/gen-goals-page.py
git commit -m "A goal shows the work that pursued it, and which PR carried the code"
```

---

### Task 6: Saying what the page cannot see

**Files:**
- Modify: `scripts/gen-goals-page.py:372-409` (`build`)
- Test: `scripts/gen-goals-page.py` `self_test()`

**Interfaces:**
- Consumes: `collect()` output.
- Produces: `excluded_count(total: int, shown: int) -> int` — pure, refusing on `shown > total` —
  and a rendered line in the page header. The two populations are counted in `build`, not inside the
  function, so the function stays testable without a filesystem.

⚠ **Spec falsifier F8.** The page renders 46 of 186 documents under `docs/superpowers/`. That is the
registry's deliberate living/dead split, but an unstated denominator is how a partial view is read as
a complete one.

- [ ] **Step 1: Write the failing test**

```python
    eq("the excluded count is total minus shown", excluded_count(186, 46), 140)
    eq("nothing excluded reads as zero", excluded_count(46, 46), 0)
    # ⛔ A NEGATIVE would mean the two populations were counted differently — which is this
    # repo's most-recorded measurement bug. Refuse rather than render a nonsense number.
    eq("showing more than exist is a refusal, not a negative",
       _raises(lambda: excluded_count(10, 46), ValueError), True)
```

`_raises` already exists in this file's self-test idiom; if absent, add:

```python
    def _raises(fn, exc) -> bool:
        try:
            fn()
        except exc:
            return True
        return False
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python3 scripts/gen-goals-page.py --self-test`
Expected: FAIL — `NameError: name 'excluded_count' is not defined`

- [ ] **Step 3: Write the minimal implementation**

```python
def excluded_count(total: int, shown: int) -> int:
    """Documents present but not rendered, because they declare no anchor. PURE.

    ⛔ REFUSES on shown > total. That can only mean the two numbers were counted over
    different populations, which is the single most-recorded measurement defect in this
    repo. A negative rendered as "-36 excluded" would be believed.
    """
    if shown > total:
        raise ValueError(f"shown ({shown}) exceeds total ({total}) — populations disagree")
    return total - shown
```

In `build`, after the existing `docs = sum(...)` line at `:374`, add:

```python
    total_docs = sum(1 for sub in SUBDIRS for _ in (DOCS / sub).glob("*.md"))
    hidden = excluded_count(total_docs, docs)
```

and render it in the page's intro paragraph beside the existing `{docs} documents` phrasing:

```python
    f"{docs} documents carry an anchor; {hidden} more under docs/superpowers/ do not "
    f"and are not shown."
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 scripts/gen-goals-page.py --self-test`
Expected: PASS, case count risen by 3.

Run: `python3 scripts/gen-goals-page.py --out /tmp/goals-check.html && grep -o '[0-9]* more under docs/superpowers/' /tmp/goals-check.html`
Expected: a non-zero count (140 as measured 2026-09-11).

- [ ] **Step 5: Commit**

```bash
git add scripts/gen-goals-page.py
git commit -m "The goals page says how many documents it cannot see"
```

---

## After the last task

- [ ] Run the full gate set: `python3 scripts/check-docs.py`, `check-anchors.py`,
      `check-ratchet-contract.py`, `check-selftest-counts.py`. **A gate that cannot run is a
      failure.**
- [ ] Open `/goals` in a browser against the rebuilt page and confirm by eye that a thread expands,
      that `#186` and `#187` on the ask-choices thread read differently, and that the theme toggle
      still works. **The browser pass is not optional** — this project has shipped a page whose
      contrast defect no test could see.
- [ ] Record a dashboard entry (`check-dashboard-entry.py` refuses a branch without one).
- [ ] `scripts/mutations/` — this file has a manifest obligation under
      `check-ratchet-contract.py`. Add mutations for the rules that can silently weaken:
      `PR_TAIL`'s tail anchor, `files_are_code`'s negation, `git_pr_history`'s None-vs-[] return,
      and `thread_prs`' `pr_error`. **Each must go red via the case it names.**

## Not in this plan — owed by the spec

- **§3.3** — the `Bundle` column becoming controlled goal names (~70 rows to classify).
- **§4** — the done/active/dormant lifecycle, which depends on §3.3 for open-item counts.
- **§5's BACKLOG section** of the card, which depends on §3.3.

These are Plan 2. Nothing here blocks them and nothing here makes them harder.
