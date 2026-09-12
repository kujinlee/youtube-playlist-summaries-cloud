`def excluded_count(total: int, shown: int) -> int:`

# Plan review r1 — `2026-09-11-goal-work-threads.md` (Claude half)

**Subject:** `docs/superpowers/plans/2026-09-11-goal-work-threads.md`
**Against:** `scripts/gen-goals-page.py` @ `a298df4e`, 531 lines, unmodified (verified: the plan's
functions `doc_stem`, `pair_documents`, `prs_from_log`, `files_are_code`, `git_pr_history`,
`annotate_code`, `thread_prs`, `render_threads`, `excluded_count` are all absent from the file).

**Method.** Every line-number claim was checked by printing that exact line range. Every `eq(...)`
case the plan adds was **executed** — the plan's Step-3 implementations were transcribed verbatim
into a scratch harness importing the real `page_markup`, and the plan's Step-1 cases run against
them. Stub experiments were run, not reasoned about.

---

## Q1 — Line-number anchors

Checked against `scripts/gen-goals-page.py` at `a298df4e`.

| # | Plan's claim | Verdict | What is actually there |
|---|---|---|---|
| a | Task 1: "after `parse_roots` … after line 160, before the `# ---- collection` banner at `:162`" | **SPLIT — the banner is right, the function is wrong** | see below |
| b | Task 3: "Insert after `last_touched` (after `:170`)" | **CORRECT** | `last_touched` is `:163-170`, `:170` is its final `        return ""`; `:171-172` blank; `:173` `def collect` |
| c | Task 4: "the record shape `collect()` builds at `:200-205`" | **CORRECT** | `:200` `by_anchor[h["anchor"]].append({` … `:205` `})`; keys are exactly `name, rel, goal, dated, touched, kind, milestones` as Task 1's Interfaces claims |
| d | Task 4: "immediately before `out = []` at `:207`" / "after the `"docs": ds,` line at `:213`" | **BOTH CORRECT** | `:207` is `    out = []`; `:213` is `            "docs": ds,`. (Also correct: `out.append({...})` is `:211-218`, and `collect` is `:173-224`) |
| e | Task 5: "`:362-368` (the Documents band inside `render_goal`)" | **CORRECT as a range, but it under-runs the replacement** | see below |
| f | Task 5: "`:228-302` (CSS)" | **WRONG** | `CSS` is `:228-300` (`:228` `CSS = """`, `:300` the closing `"""`). `:301-302` are two **blank lines**; `:303` is `def render_goal`. Off by two |
| g | Task 6: "`:372-409` (`build`)" | **WRONG** | `build` is `:372-407` (`:407` the closing `"""` of the returned f-string). `:408-409` are two **blank lines**; `:410` is the `# ---- self-test` banner. Off by two |
| g2 | Task 6: "after the existing `docs = sum(...)` line at `:374`" | **CORRECT** | `:374` is `    docs = sum(len(a["docs"]) for a in anchors)` |
| h | Global: "self-test style … (`gen-goals-page.py:411-419`)" | **CORRECT** | `:411` `def self_test`, `:412` `cases = failures = 0`, `:414-419` the `eq` closure ending `failures += 0 if ok else 1` |

Two further anchors, not on the list, are also correct: Task 1's "Test: `self_test()` (`:411`)", and
Task 5's "Add before `render_goal` (`:303`)". The Global constraint "collection section
(`gen-goals-page.py:162` onward)" is correct — `:162` is the banner.

### (a) — Medium. One sentence gives two locations 19 lines apart.

`parse_roots` **ends at `:141`**, not `:160`:

```
137	def parse_roots(text: str) -> tuple[set[str], list[tuple[int, str, str]]]:
...
141	    ]
142
143
144	# ── inline markup is NOT implemented here. Backlog #71.
```

Line `:160` is a **blank line**. What ends at `:159` is `inline_md = page_markup.render_inline`,
the tail of the 16-line backlog-#71 comment block at `:144-159`. Task 1's Files section states
`after parse_roots (ends :160)` — that parenthetical is false twice over.

The *placement* the parenthetical in Step 3 describes ("after line 160, before the banner at
`:162`") is correct and is where the code should go. But an implementer following the **words**
("after `parse_roots`") inserts at `:142`, which drops two new top-level functions into the middle
of the `# ── inline markup is NOT implemented here` comment block, separating that comment from the
`esc`/`inline_md` bindings it documents. The two readings of one sentence disagree.

Also minor: `:160` and `:161` are both blank. "Insert after line 160" leaves one blank line above
the new `STEM_SUFFIX` and one below the last new function — PEP 8 wants two. Insert after `:161`.

### (e) — Low, but it produces dead code as written.

The Documents band occupies **exactly `:362-368`**, so the range is right:

```
362	    parts.append('<div class="band"><span class="blab">Documents</span><div class="docs">')
363	    for d in a["docs"]:
364-367	        parts.append(f'<div class="doc">…')
368	    parts.append("</div></div></article>")
369	    return "\n".join(parts)
```

Note `:368` does double duty — it closes the band *and* the `<article>` — so the band is not
cleanly separable from the end of `render_goal`. The plan's replacement handles that correctly by
re-emitting `</div></div></article>`.

**The line inside 362..369 that the plan does not replace is `:369`**, `    return "\n".join(parts)`.
The plan's replacement block already ends with its own `    return "\n".join(parts)`. Replacing
`:362-368` literally therefore yields **two consecutive identical `return` statements**; the second
is unreachable dead code. Harmless at runtime, but `render_goal` ends with a line no test can reach.
The fix is one character in the plan: the range to replace is **`:362-369`**.

### (h) — adjacent, one line: the declared case count.

`python3 scripts/gen-goals-page.py --self-test` currently prints `15/15 self-test cases passed`, and
the module docstring at `:6` says `--self-test  # 15 cases`. The plan adds 10+10+4+4+10+3 = **41**
cases (each task's "risen by N" matches its own `eq` count), taking the file to **56**. No task in
the plan updates the `:6` docstring, and `check-selftest-counts.py` pins declared counts — this
repo has already recorded three declared-count drifts. Not a line-anchor error, but it is the one
gate the Global-constraints section cites and the plan never touches.

---

## Q2 — Can each test fail?

I transcribed the plan's Step-3 implementations verbatim and **ran all 41 cases**. Result:

```
--- Task 1   10/10 OK
--- Task 2   10/10 OK
--- Task 3    4/4  OK
--- Task 4    FAIL a thread's PRs are the UNION over its documents, deduped   got ['2', '1'] want ['1', '2']
              3/4  OK
--- Task 5   10/10 OK
--- Task 6    2/3  OK  (+1 NameError, see below)
```

### 🔴 BLOCKING — Task 4, `"a thread's PRs are the UNION over its documents, deduped"`

The plan's own test contradicts the plan's own implementation. Plan line 383:

```python
    eq("a thread's PRs are the UNION over its documents, deduped",
       [p["num"] for p in thread_prs(_t, _hist.get)["prs"]], ["1", "2"])
```

against plan line 424:

```python
    prs = sorted(merged.values(), key=lambda p: (p["date"], p["num"]), reverse=True)
```

The fixture gives PR `1` the date `"d"` and PR `2` the date `"e"`. `"e" > "d"`, so
`reverse=True` puts `2` first. **Measured:** `got ['2', '1'] want ['1', '2']`.

Task 4's Step 4 says *"Expected: PASS, case count risen by 4."* It will not pass. An implementer
following `subagent-driven-development` hits a red at Step 4 with no guidance on which side is
wrong, and the cheapest way out — flipping `reverse=True` to `reverse=False` — silently inverts the
documented "newest first" ordering for **every** thread on the page, which no other case would
catch. Fix the *expectation* to `["2", "1"]`, or give the fixture dates that make the intended
order unambiguous (e.g. `2026-01-01` / `2026-02-01`) so the case is about the union rather than
about which of `"d"`/`"e"` sorts higher.

### 🟠 HIGH — six cases pass against a constant stub. Measured, not argued.

The mandate's exact question — *would this case still PASS if the function it names were stubbed to
return a constant?* — is **yes** for these. I ran the substitution:

| Case label | Stub that satisfies it |
|---|---|
| `a malformed line is skipped, not crashed on` | `prs_from_log = lambda lines: []` |
| `an empty log yields no PRs` | `prs_from_log = lambda lines: []` |
| `a PR-looking number mid-subject is not the PR` | `prs_from_log = lambda lines: []` |
| `a doc path is not code` | `files_are_code = lambda files: False` |
| `an empty file list is not code` | `files_are_code = lambda files: False` |
| `and it does NOT also claim there is no code PR` | `render_threads = lambda th: ""` |

All six are **absence assertions** — they assert a value is `[]`/`False`, or that a substring is
*not* present. That does not make them worthless: each *can* fail for the specific defect it is
aimed at, and I verified the two that matter most —

- `a PR-looking number mid-subject is not the PR`: dropping `$` from `PR_TAIL` makes it return
  `[{... "num": "99" ...}]` ≠ `[]` → the case goes red. It genuinely defends the tail anchor.
- `a doc path is not code`: dropping `docs/` from `DOC_PATH` returns `True` ≠ `False` → red.

The two that are **structurally unfalsifiable**, in that no plausible weakening of the subject can
turn them red while the surrounding cases stay green:

1. **`an empty log yields no PRs`** — `prs_from_log([])` is `[]` for every implementation whose loop
   body is skipped. There is no mutation of `prs_from_log`'s *rules* that changes this. It is a
   restatement of `for line in []`, not a test.
2. **`and it does NOT also claim there is no code PR`** — this is the weakest case in the plan and
   it guards the most important behaviour (CANNOT RUN must not read as a measured absence). It is
   satisfied by an empty string, a traceback-free stub, a renderer that emits nothing for
   `pr_error` threads, and by any future refactor that renames the phrase `no code PR yet` in *both*
   branches. It cannot distinguish "the renderer correctly abstained" from "the renderer produced
   nothing". Assert the **positive** instead: that `render_threads(_broken)` contains
   `could not be read` **and** its summary contains neither `no code PR yet` nor
   `code PR(s)` — i.e. pin the branch that ran, not the branch that didn't.

### 🟡 MEDIUM — `a commit with no PR tail is dropped` measures a conjunction

```python
    eq("a commit with no PR tail is dropped", len(prs_from_log(_lg)), 2)
```

`_lg` has four lines: `#176`, `#186`, a **duplicate** `#186`, and a tailless commit. The result `2`
is produced by two independent rules — the tail drop *and* the dedup. Delete either one and this
case goes red, so its label names a cause it cannot isolate. The dedup is already asserted by the
first case (`["176", "186"]` from three tailed lines), so the fix is to give this case its own
one-line input: `prs_from_log(["ddd\x012026-07-01\x01a direct commit with no PR"]) == []`.

### 🟡 MEDIUM — `_raises` does not exist in this file, and the plan's fallback is ordered wrong

Plan line 656: *"`_raises` already exists in this file's self-test idiom; if absent, add:"*

**Measured:** `grep -n "_raises" scripts/gen-goals-page.py` → no match. It exists in 7 *other*
scripts (`gen-backlog-page.py`, `brief-compose.py`, `gen-dashboard.py`, `check-live-schema.py`,
`explainer-serve.py`, `check-selection-card.py`, `begin-plan.py`), so it is a house idiom — but not
this file's. The hedge saves the plan from being wrong, at the cost of leaving the implementer to
notice.

Worse is the ordering. Every task instructs *"Add inside `self_test()`, immediately before the
`print(f"\n{cases - failures}...")` line"*, and Task 6 prints the `eq(...)` that **calls** `_raises`
*before* the `def _raises` that defines it. Appending both in the order written puts the call above
the definition inside the same function body — and because it is a call at module-execution time
inside `self_test`, Python raises `NameError: name '_raises' is not defined`. I hit exactly this in
the harness run above. State that `_raises` goes near the top of `self_test`, beside `eq`.

### 🟢 LOW — three smaller weaknesses

- **`the implementing PR is marked code`** asserts `"#186" in _h and ">code<" in _h` as one boolean.
  On failure `eq` prints `got False want True` and the reader cannot tell which conjunct broke. Two
  cases, or a tuple, costs nothing. Same shape in `the two PRs are distinguishable in the markup`.
- **`a PR whose files could not be read is tagged unknown`** asserts `"unknown" in _h`. The rendered
  markup is `<span class="tag unknown">unknown</span>` — the substring appears in *both* the class
  attribute and the text, so the case cannot tell a styled-but-unlabelled tag from a labelled one.
  `">unknown<" in _h` distinguishes them, and matches how the sibling case already tests `">code<"`.
- **Nothing tests the Task-4 wiring.** `thread_prs` is tested; the `history` closure and the
  `"threads": [...]` key inside `collect()` are covered only by the `BUILD-OK` smoke run at Task 4
  Step 4, which passes whether or not `threads` contains anything. A `collect()` returning
  `"threads": []` for every anchor would satisfy every `eq` in the plan and print `BUILD-OK`.
  The Task 5 Step 4 `grep -c '<details class="thread"' … # expect > 20` is the only thing standing
  between that and a shipped empty band — and it is a manual step, not a case.

### Cases that are sound

All 10 Task-1 cases, the 4 remaining Task-2 `files_are_code`/`prs_from_log` positives, all 4 Task-3
cases, Task 4's three `pr_error` cases, 9 of 10 Task-5 cases, and Task 6's `140` and refusal cases
each read a real value out of real output and go red under a plausible weakening. Task 6's refusal
case correctly names `ValueError` rather than catching bare `Exception`, which this repo has paid
for before.

---

## Q3 — `None` vs `[]`, traced end to end

**Answer up front: the `git log` half of the chain preserves the distinction at every step, and
`render_threads` can tell them apart. The `git show` half does not — and the page renders that
unmeasured case as a measured absence.**

### Step 1 — `git_pr_history` (plan lines 300-317). Distinguishable. ✅

```python
    try:
        r = subprocess.run(
            ["git", "log", "--format=%H\x01%as\x01%s", "--follow", "--", str(path)],
            cwd=ROOT, capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0:
        return None
    return prs_from_log(r.stdout.splitlines())
```

Verified against real git in this repo:

```
$ git log --follow --format=%H -- docs/does-not-exist-xyz.md ; echo $?
0                      # -> stdout empty -> prs_from_log([]) -> []   TRUE ABSENCE
```

so an uncommitted or PR-less document yields `[]`, and a broken git (not a repo, bad object, OSError)
yields `None`. The two are correctly separated here.

### Step 2 — the `history()` closure inside `collect()` (plan lines 437-441). Distinguishable. ✅

```python
    def history(rel: str):
        if rel not in hist_cache:
            got = git_pr_history(ROOT / rel)
            hist_cache[rel] = None if got is None else annotate_code(got)
        return hist_cache[rel]
```

`None` is passed through untouched; `[]` goes through `annotate_code([])` which returns `[]`. The
`rel not in hist_cache` guard (rather than `hist_cache.get(rel)`) is the right choice: a cached
`None` is not re-fetched, so a transient git failure stays one failure rather than becoming N.

### Step 3 — `thread_prs` (plan lines 412-425). **This is where `None` is converted — deliberately, and correctly.** ✅

```python
    for side in ("spec", "plan"):
        d = thread.get(side)
        if not d:
            continue
        got = history(d["rel"])
        if got is None:
            error = True
            continue
        ...
    return {**thread, "prs": prs, "pr_error": error}
```

`None` stops being a value and becomes the boolean `pr_error`; `prs` is `[]` in both the unreadable
and the genuinely-empty case. That is a real collapse, but it is not a loss, because `pr_error`
carries the distinction forward at the level it is true at (the thread). The plan says as much at
line 452-454 and it is right to.

One dead spot: a thread with **no spec and no plan** never calls `history` at all, so it returns
`pr_error: False, prs: []` — indistinguishable from a measured empty. `pair_documents` cannot
produce such a thread (every thread is created from a document), so this is unreachable in
production and reachable only from the plan's own fixture. **Low.**

### Step 4 — `render_threads` (plan lines 551-560). Distinguishable — *for `git log`*. ✅

```python
        n_code = sum(1 for p in t["prs"] if p.get("code") is True)
        if t["pr_error"]:
            flag = '<span class="absent">history could not be read — treat as NOT MEASURED</span>'
        elif not n_code:
            flag = '<span class="absent">⚠ no code PR yet</span>'
```

`pr_error` is tested **first**, so an unreadable history renders *NOT MEASURED* and never
*no code PR yet*. `render_threads` can tell them apart, and the ordering of that `if`/`elif` is the
whole mechanism.

---

### 🟠 HIGH — the second CANNOT RUN, one layer down, is laundered into a finding

`pr_error` only ever records a failure of **`git log`**. A failure of **`git show`** takes a
different route: `git_show_files` returns `None` → `annotate_code` sets `"code": None` → and
`n_code` counts only `p.get("code") is True`. An unknown is counted as *not code*.

Measured — this is `git show` failing on a sha (exit 128, so `git_show_files` returns `None`), which
happens on a shallow clone, a partial fetch, or a `--follow` history reaching a commit not present
locally:

```
$ git show --name-only --format= -1 deadbeef...  ; echo $?
128
```

Rendering the plan's own `_unknown` fixture through the plan's own `render_threads`:

```html
<details class="thread"><summary>s <span class="absent">⚠ no code PR yet</span></summary>
<div class="prline"><span class="t">spec</span><a href="/src/r">s-design.md</a></div>
<div class="prline"><span class="t">plan</span><span class="absent">no plan</span></div>
<div class="prline"><span class="tag unknown">unknown</span><span class="t">#9 · d</span>…</div>
</details>
```

The summary asserts **⚠ no code PR yet** — a finding, in the warning colour — over a thread whose
only PR was never measured. The row below it says `unknown`. The card contradicts itself, and the
line a reader scans is the summary.

This is precisely the failure the plan's own Global Constraint forbids: *"If git cannot answer, the
page must say CANNOT RUN — never render an empty thread as though it were a true absence."* The
plan built the guard for `git log` and left the identical hole in `git show`. Task 5's docstring
even says *"a thread with no code PR is a real finding; a thread whose history could not be READ is
not a finding at all"* — and `code: None` is exactly the second thing being drawn as the first.

**And no case can see it.** The plan's `_unknown` fixture is the one that exercises this path, and
its only assertion is `"unknown" in render_threads(_unknown)` — the per-PR tag. Nothing asserts what
the *summary* says. The plan's mutation list at line 730 covers `git_pr_history`'s None-vs-`[]` and
`thread_prs`' `pr_error`; it does not cover this one, because the plan does not know it exists.

**Fix** — make the summary abstain when any PR is unknown, and give it a case:

```python
        n_unknown = sum(1 for p in t["prs"] if p.get("code") is None)
        if t["pr_error"]:
            flag = '…history could not be read — treat as NOT MEASURED…'
        elif n_unknown and not n_code:
            flag = '<span class="absent">code/docs unknown for ' \
                   f'{n_unknown} PR(s) — treat as NOT MEASURED</span>'
        elif not n_code:
            flag = '<span class="absent">⚠ no code PR yet</span>'
```

with the case the plan is missing:

```python
    eq("an unknown PR does not become a 'no code PR' finding",
       "no code PR yet" in render_threads(_unknown), False)
```

which is red against the plan as written and green against the fix.

### 🟡 MEDIUM — `git_show_files` splits on whitespace, so a path with a space flips the verdict

Not a `None`/`[]` question, but it is on the same trace and it corrupts the same discriminator:

```python
    return r.stdout.split() if r.returncode == 0 else None
```

`.split()` with no argument splits on **all** whitespace, not newlines. A tracked path containing a
space — `docs/my notes.md` — becomes `["docs/my", "notes.md"]`, and `files_are_code` matches
`DOC_PATH` against `"notes.md"`, which does not start with `docs/`, so a documentation-only PR is
tagged **code**. Use `r.stdout.splitlines()`. (This repo has a memory note on exactly this class:
use the splitter the consumer's data actually requires, and a whitespace `split()` over
newline-delimited git output is the recorded instance.) Note also that `git show --name-only`
quotes and escapes non-ASCII paths by default unless `core.quotePath=false`; `--no-renames -z`
would be sturdier still, but `splitlines()` closes the measured hole.

### Summary of the trace

| Step | `None` vs `[]` | Verdict |
|---|---|---|
| `git_pr_history` | returns `None` on exception or `rc != 0`; `[]` on `rc == 0` with no tailed subjects | preserved ✅ |
| `history()` closure | `None if got is None else annotate_code(got)` | preserved ✅ |
| `thread_prs` | `None` → `pr_error = True`, `prs` collapses to `[]` | converted, not lost ✅ |
| `render_threads` | `if t["pr_error"]` tested **before** `elif not n_code` | **can tell them apart** ✅ |
| **`git_show_files` → `code: None`** | **`None` is counted as not-code by `n_code`; no `pr_error`, no case** | **indistinguishable 🟠** |

---

## Verdict

**NOT-CONVERGED.**

Must fix before implementation starts:

1. **Blocking** — Task 4's union case expects `["1", "2"]` and the plan's own `sorted(...,
   reverse=True)` returns `["2", "1"]`. Step 4 cannot go green as written.
2. **High** — `code: None` from a failed `git show` renders as `⚠ no code PR yet`. The CANNOT-RUN
   guarantee holds for `git log` and fails for `git show`, and the plan's `_unknown` case is blind
   to it.
3. **High** — six cases pass against a constant stub; two of those (`an empty log yields no PRs`,
   `and it does NOT also claim there is no code PR`) cannot fail for any weakening of their subject.
   The second is the guard on the plan's central invariant.
4. **Medium** — `_raises` is called before it is defined in Task 6's stated insertion order
   (`NameError`, reproduced); it does not exist in this file despite the plan's claim.
5. **Medium** — Task 1's "after `parse_roots` (ends `:160`)" is wrong by 19 lines and disagrees with
   the correct placement given in the same sentence; `git_show_files` should use `splitlines()`.
6. **Low** — CSS is `:228-300` not `:228-302`; `build` is `:372-407` not `:372-409`; the Task 5
   replacement should cover `:362-369` or it leaves a duplicate `return`; the module docstring's
   `15 cases` needs to become `56`.
