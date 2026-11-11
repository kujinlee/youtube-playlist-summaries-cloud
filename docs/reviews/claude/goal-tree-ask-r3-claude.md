Reviewed head: d304538b5e0b5b798a8208a16db8c0d8434854df

# Round 3 — Claude half: PR #558 (goal-tree Ask tray, collapsed answers, (kind, number) ledger matching)

**Subject:** `goal-tree-ask` at `d304538b`. Reviewer: Claude (adversarial, refuting mandate). The r2 Codex half
ran on `1f43cf06`; this is the first Claude pass since r1.

**Self-test at HEAD:** `473/473 self-test cases passed` (run in the worktree, unmodified). One `⚠  goal tree:
answers NOT shown — sa.json: …` line leaks to stderr during a passing run (see L4).

All probes ran against `scripts/goal-tree.py` imported from the worktree, with the last 3 lines of the real
`.claude/goal-tree-log.jsonl` as the log and a `composer=[python, -c, ...]` seam. Mutants ran on a
`git archive HEAD` copy outside the repo; the worktree was not modified.

## Findings

| id | sev | where | finding |
|---|---|---|---|
| M1 | MEDIUM | `scripts/goal-tree.py:2100`, case at `:3364-3379` | The r2 cases pin only `a` and `asked`. Dropping `key` and `q` from the UTF-8 check leaves 473/473 green, and the mutant brings back the exact r2 defect: no page is written |
| L1 | LOW | `scripts/goal-tree.py:2402-2405` | The r1 B "asked of the FILE" check reads whatever `out` already holds. If the composer exits 0 and writes nothing, the previous run's page is reported as `Ask tray lifted` |
| L2 | LOW | `scripts/goal-tree.py:2396` | `text=True` decodes the composer's output strictly. A composer that writes non-UTF-8 bytes to stderr makes `write_page` raise, and no page is written |
| L3 | LOW | `scripts/goal-tree.py:2077`, `:2109` | Edges of `load_answers`: an unreadable file raises `PermissionError`; an uppercase or whitespace-only key is accepted and then lands under Older questions; a whitespace-only `a` is accepted and renders an empty answer |
| L4 | LOW | `scripts/goal-tree.py:3372` | The r2 end-to-end case does not redirect stderr, so every passing self-test prints a `⚠ answers NOT shown` line |

### M1 — the r2 refusal is pinned for 2 of its 4 fields; the other 2 can be deleted with the suite green

Mutation, applied to a copy (`git archive HEAD` → scratch dir), line 2100:

```
- if not all(_encodes(r[f]) for f in ("key", "q", "a", "asked") if isinstance(r.get(f), str))]
+ if not all(_encodes(r[f]) for f in ("a", "asked") if isinstance(r.get(f), str))]
```

Observed on the mutant: `473/473 self-test cases passed`.

What that mutant then does, with an input of one row each (`{"key": "goal:gone\ud800", ...}` and
`{"q": "q\ud800", ...}`), run through `write_page` with a tray-less composer:

```
== MUTANT (copy)
key load_answers err: ''
key write_page RAISED UnicodeEncodeError: 'utf-8' codec can't encode character '\ud800' in position 226461: surrogates not allowed  page_written=False
q load_answers err: ''
q write_page RAISED UnicodeEncodeError: 'utf-8' codec can't encode character '\ud800' in position 36602: surrogates not allowed  page_written=False
== HEAD (worktree)
key load_answers err: 'm-key.json: entry [0] carries text that is not valid UTF-8'
key write_page ok, page_written= True
q load_answers err: 'm-q.json: entry [0] carries text that is not valid UTF-8'
q write_page ok, page_written= True
```

So HEAD is correct, but nothing holds it there for two fields. The `key` field matters most: a key that is not on
the tree is printed under Older questions (`older_qa_html`, `html.escape(k)`), so a surrogate in a key that has
gone stale stops the page from being written. The case comment says *"Two distinct fields and positions, so a
check of one field or entry 0 only stays red"*. That is true for "one field", but false for "two of four".
The manifest's one mutation (`if unenc:` → `if False:`) cannot see this either.

**Fix:** put a surrogate in every one of the four fields, each in its own row, in distinct entries (for example
`key` at entry 2 and `q` at entry 3), and assert the indices that are refused. Add one mutation per dropped field,
or one mutation that drops `key` and `q`.

### L1 — the tray check can read the previous run's page

`write_page` does not remove `out` before composing. Input: `out` already holds
`OLD PAGE id="tray" id="qbox" /questions`, and the composer is `python -c pass`, which exits 0 and writes nothing:

```
w-stale: why='' page_written=True size=39
   stale content kept: OLD PAGE id="tray" id="qbox" /questions
```

`page_report` would then print `(Ask tray lifted)` over a page that does not show this run's tree or answers. The
default `out` (`~/explainers/goal-tree.html`) exists after the first run, so this is the deployed shape. The r1 B
case uses a fresh path every time, so it cannot see the problem. **The real `brief-compose.py` cannot reach this
today**: it writes before it returns 0 (`brief-compose.py:1252-1253`) and raises when the page has no tray
(`1255-1256`). So this is LOW: it is a gap in the r1 B claim ("rc 0 with no tray on disk is the failure this
exists for"), not a live defect. **Fix:** unlink `out` before running the composer, or check for a per-run stamp
from the fragment in the written file.

### L2 — non-UTF-8 output from the composer raises, and no page is written

Input: a composer `sys.stderr.buffer.write(b'\xff\xfe boom'); sys.exit(1)`.

```
w-badstderr: write_page RAISED UnicodeDecodeError: 'utf-8' codec can't decode byte 0xff in position 0: invalid start byte page_written=False
```

This breaks the docstring's promise that a missing tray "is NOT fatal". It is LOW because Python's own stderr uses
`backslashreplace`, so the real composer is unlikely to emit such bytes. **Fix:** pass `errors="replace"` to
`subprocess.run`. Not fixed and not pinned either: an `OSError` from launching the composer, and the `OSError`
from L3.

### L3 — edges of `load_answers` (all run)

```
perm.json: load_answers RAISED PermissionError: [Errno 13] Permission denied: 'r3/run/perm.json'
ws.json:   load_answers -> rows=1 err=''                  # key "   ", a "   "
```

- **A `chmod 000` answers file** raises from `load_answers`, so no page is written. r1 A's claim covers *shapes*,
  so this is outside its letter. One `OSError` added to the `except` would close it.
- **Key `"PR-558"`**, which is on the live tree as `pr-558`: `answers_by_key` strips the key but does not lowercase
  it, while `_thread_key` lowercases, so the answer lands in Older questions. A key `"   "` is accepted (the
  non-empty check sees three characters) and renders as an empty `<p class="qa-key"></p>` label under Older
  questions, with an empty answer body. Nothing is dropped, so this is LOW.

### L4 — a passing self-test prints a warning

The r2 end-to-end case (`:3372`) calls `write_page` without `redirect_stderr`. So every green run prints
`⚠  goal tree: answers NOT shown — sa.json: entry [0] carries text that is not valid UTF-8` above
`473/473 self-test cases passed`. The r1 A twin at `:4054` already redirects stderr; do the same here.

## Tried and held (no finding)

- **The other inputs to `load_answers`:**
  - **BOM:** refused by name (`JSONDecodeError: Unexpected UTF-8 BOM`), and the page is still written.
  - **A 5,000-digit integer for `asked`:** refused (`ValueError: Exceeds the limit (4300 digits)`).
  - **100,000-deep nesting:** parsed, then refused (`entry [0] lack key, q or a`).
  - **A surrogate in an extra field, and `1e400`:** accepted, and harmless because the field is never rendered.
  - **NUL, `\x0c`, `￾` and `￿` in `q` and `a`:** accepted and encodable.
  - **A surrogate in `key`:** refused at HEAD.
- **Marker placement on the real log:**
  - I wrote one answer for every thread key on the live tree (185 keys).
  - Every one rendered exactly once (185 `<details class="qa">`), and none landed in Older questions.
  - No `qa` marker sits inside a `fold` `<details>`; I parsed the HTML to check.
  - No key appears in a fold summary line.
- **Ledger matching (`_ledger_refs`):**
  - `pr #558`, `Backlog #12`, `PR#13` and `PR  #14` name nothing, and a thread line that does not parse names
    nothing. Both are as documented.
  - The real `.claude/inflight.jsonl` has no unthreaded entry whose reference differs only in case or spacing, so
    nothing live is mis-hung.
- **The stale-page source:** `explainer-serve.py` `PAGE_SOURCES["goal-tree"]` now includes the answers file. The
  caveat that answers only show after the PR merges is stated in the comment.
- **The 30 s compose timeout:** INFERRED, not re-measured. On POSIX, `subprocess.run` calls `wait()` rather than
  `communicate()` after the kill, so a grandchild that holds the pipe cannot extend the timeout past 30 s.

## Verdict rationale

M1 is a test that cannot fail over the exact defect r2 folded: the mutant brings that defect back, and it was run.
This is round 3, so it is folded. L1-L4 are LOW. L2 and L3's `PermissionError` contradict "the page is still
written", but only for inputs this repo's own scripts do not produce.

VERDICT: NOT CONVERGED
