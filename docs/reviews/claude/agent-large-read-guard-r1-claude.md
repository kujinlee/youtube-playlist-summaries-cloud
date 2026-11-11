Reviewed head: 63d77c7b95b8482496ce581a74200ff493da10cd

# PR #469 (backlog #457 re-scoped), round 1, Claude half

**Subject:** branch `agent-large-read-guard`. Dispatched at head `46ce8031`. The security fold `63d77c7b` (a per-user 0700
state directory) was committed while this review ran. Every probe below ran against the working tree, and that tree's
`scripts/check-agent-large-read.py` is byte-identical to `63d77c7b`'s (checked with `diff`). **Verdict head: `63d77c7b`.**

**Harness.** Each payload was piped through `bash .claude/hooks/run-hook.sh agent-large-read.sh` from the worktree, with a
top-level `agent_id` (a subagent) unless noted otherwise, and fixtures in a scratch directory: `a200.txt`/`b200.txt` (200 lines each),
`c500.txt` (500 lines), `long300.txt` (300 lines of 2,000 characters), and `nb.ipynb` (366 JSON lines). Rows below are written
`input -> observed`.

**What holds (RAN):**
- `--self-test`: 70/70.
- `check-plan-code.py --mutate . --only scripts/check-agent-large-read.py`: 54 mutations, 54 killed, 54 attributed.
- The main session (no `agent_id`) running `cat c500.txt` -> allow.
- `tail -n +1 c500.txt` -> deny. `cat "c500.txt"` -> deny.
- `sed -n '1,100p;101,300p'` (300 lines) -> allow. `sed -n 1,400p f | head -n 300` -> allow.
- A directory -> allow. An offset past EOF -> allow. A NUL in a path, via Read or Bash -> allow, with no traceback.
- `offset: 1e400` -> NOT CHECKED, exit 1.
- The 50-line-chunk re-read works: six Reads of 50 lines each over lines 1-300, already read -> all allow.
- Five same-size writes in a row on APFS gave 5 distinct `mtime_ns` values, so "a same-size edit within the same second"
  is not a false refusal on this filesystem. It is one only on a filesystem with 1-second mtimes, or when the edit keeps
  the old mtime: a same-size rewrite followed by `os.utime` back to the old mtime -> deny, by design.
- Performance: `tail -n 20` of a 300 MB file runs in 0.33 s through the launcher.

**Does Claude Code already de-duplicate a Read? Partly. MEASURED in the 2.1.309 binary.**
The Read path returns `{type:"file_unchanged"}`, with the text *"File unchanged since last read. The content from the
earlier Read tool_result in this conversation is still current"*, only when all of these hold:
- there is a prior entry in `readFileState`;
- the read is not a partial view;
- `kt.offset===n&&kt.limit===r`: the same offset and limit;
- the mtime (floored to ms) is unchanged;
- dedup is not turned off.

Dedup is turned off (`dedupUnchangedReads:!1`) when `$jt(...)` reports that old tool results were cleared by
context editing (`clear_tool_uses_20250919`).

So rule (b) on Read is **redundant for an exact repeat** and **not redundant for an overlapping, different range**. The
harness ALSO knows when the earlier content has left the context. The hook does not know this (finding F3).

## Findings

### F1 — MAJOR (fold in r1) — `sed -n` over several files is over-counted, so a 200-line read is refused
`scripts/check-agent-large-read.py:287`: `stream += op([(path, 1, n)])` applies the stage op to each file separately.
That is right for `head` and `tail`, which work per file. Without `-s`, `sed` treats all its files as ONE stream. RAN:
- `sed -n '1,200p' a200.txt b200.txt` -> **DENY**
- the same command in a shell gives `wc -l` = **200**

This refutes "refuses exactly the reads that would put more than 300 lines". Fix: for `sed` without `-s`/`-i`,
concatenate the files and then apply the op once. Add a case for two 200-line files with `'1,200p'` -> allow.

### F2 — MAJOR (fold in r1) — Read of a Jupyter notebook: offset/limit are ignored, so the advice cannot be followed and the guard is bypassed
MEASURED in the binary (`async function NRn`):
- `if(jx(s)){ ... return {type:"notebook",file:{filePath:n,cells:zn}} }` returns every cell.
- `offset`/`limit` are stored, never applied.

RAN:
- Read of `nb.ipynb` (366 lines) -> **DENY**, with advice to use `offset`/`limit`
- the same Read with `limit: 300` -> **allow**, and the tool still returns the whole notebook

Result: one call is refused for no reason, and the next call reads it all anyway. PDFs (`pages`) and the image extensions
(`$_n`) also ignore offset/limit, and they are excluded only by the NUL sniff. A PDF with no NUL byte in its first 8 KB is
not ruled out, though a `cupsfilter` PDF did have one. That is an INFERENCE: no such PDF was found. Fix: allow `.ipynb`
and `.pdf` outright (by extension, the same test the tool uses), or NOT CHECKED for them. Do not count them.

### F3 — MAJOR (FILE or fold) — a re-read is refused after the earlier content has LEFT the context, and the refusal says it has not
The denial at `:373` says *"They are still in your context"*. A record lives 24 h (`STATE_TTL_S`). Three cases make that
false:
- a subagent's auto-compaction;
- context editing that clears old tool results (the harness's own dedup turns itself off for exactly this case, see above);
- a record from a call whose result the agent never received (F4).

In each case the agent cannot see the lines, and the hook still refuses a re-read of more than 50 of them.

A path exists: read in 50-line chunks (RAN: allowed). But the message does not say so, and it states something false.

INFERENCE, not measured: whether context editing is enabled for subagents in this account (`Sr()` mode). Fix candidates:
- name the 50-line-chunk path in the message, and drop "still in your context";
- or clear the agent's record on a compaction signal, if one is available to a hook.

### F4 — MEDIUM (FILE) — a call that FAILS still records its lines, so the retry is refused
A read is recorded when the hook allows it (`:375`), even if the tool then errors. The PR body states this only for a
refusal by a later hook or the permission check. Two other ways, both RAN:
- `long300.txt` (300 lines x 2,000 characters, 600 KB): a Read with no limit -> allow, recorded; a retry with `limit: 100`
  -> **DENY**. The 2.1.309 Read tool rejects content over its `maxTokens` (a `maxTokens` argument is passed through
  `NRn`; the error text was not checked). So the first call returns an error and no content, and the narrower retry is
  refused.
- `cat --bogus a200.txt` (BSD cat exits 1 and prints nothing) -> allow, recorded; then Read of `a200.txt` -> **DENY**.

Fix candidates: give a Read with no `limit` a size bound; and state this case in the docstring's BOUND (2).

### F5 — MEDIUM (FILE) — a Read needed before Edit is refused after a `sed -n` read
The Edit tool refuses a file "not been read yet" (binary string: *"File has not been read yet. Read it first before
writing to it."*). A Bash read does not populate `readFileState`. RAN, agent `e1`:
- `sed -n '1,120p' a200.txt` -> allow
- Read `a200.txt` -> **DENY**
- Read with `limit: 1` -> allow

So an implementer that reads with `sed` and then edits gets a refusal that is NOT for a re-read the agent "could get no
other way". It can recover with a narrow Read, but nothing tells it to. INFERENCE, not RAN: Edit accepts a partial Read
(`limit: 1`). Fix: mention in the denial that a 1-line Read satisfies Edit. Or exempt a Read whose `readFileState` would
be empty, which the hook cannot see, so the first fix is the practical one.

### F6 — MINOR (FILE) — a bash grammar the parser does not have becomes a false refusal
RAN:
- `cat c500.txt |& grep c` -> **DENY**. `|&` is one token, so the whole pipeline is read as `cat` with files
  `c500.txt |& grep c`, and `grep` never filters it.
- `(cd /tmp && cat c500.txt)` -> **DENY**. The first segment starts with `(`, so the `cd` is skipped, and `c500.txt`
  resolves against the payload cwd.

Both are rare. `|&` should be a pipe separator, and a segment that opens with `(` should be NOT CHECKED.

### F7 — MINOR (FILE) — NOT CHECKED forms that real agents type
RAN: `head -q -n 5 a200.txt` -> NOT CHECKED (*"the line count 'q' is not a number"*). `-q`, `-v` and `-s` on head/tail are
flags, not counts. Not a refusal, just stderr noise on every such call. Fix: skip known no-argument flags.

### F8 — MINOR (FILE) — a corrupt state record gives a TRACEBACK, not NOT CHECKED
This refutes "every unparseable input prints NOT CHECKED with no traceback". `load_state` (`:331`) checks only that a
record is a dict. RAN, writing the agent's own state file:
- `{"reads":[{"at":"x"}]}` -> rc=1 with a **Traceback** (`now - "x"`)
- `{"reads":[{"at":9e18}]}` -> rc=1 with a **Traceback** (`r["path"]` KeyError at `:367`)

Non-blocking, and the file is now same-user only (0700). Fix: validate each record's keys and types, or catch
`(KeyError, TypeError)` as Unreadable.

### Not findings (checked)
- **Globs** (`cat *.txt` -> allow): a missed refusal, stated as NOT COVERED territory. Not a false refusal.
- **`tee`** (`cat c500.txt | tee /dev/null` -> allow): prints to stdout, so it is a missed refusal. Fold it into the
  NOT COVERED list.
- **A relative Read `file_path`**: resolved against the hook process's cwd, not the payload cwd. Read requires absolute
  paths, so this is moot.
- **Settings registration**: a second `matcher: "Read"` block, launched through `run-hook.sh` like every other hook. CI
  step added, population pinned, fixture-variation keys pinned.
- **Doc drift**: the PR body still says 67 cases and 51 mutations; the code and backlog row say 70 and 54 after the fold.
  Update the body.

## Severity summary
None of these is a BLOCKER: the hook never blocks the main session, and every false refusal has a recovery path. In
round 1 the fold should fix F1 and F2, which are wrong counts with a simple fix, and the F3/F5 message text. F4 and F6-F8
can be filed.

VERDICT: NOT CONVERGED
