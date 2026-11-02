<!-- codex-review: model=gpt-6.1-sol -->

Reviewed head: 46ce8031198cc9043924bc9b793b6c66bd75f4bd75f4bd

Correction: reviewed head is `46ce8031198cc9043924bc9b793b6c66bd75f4bd`.

Read the PR body and diff. The shared checkout advanced during review, so reproductions were repeated against an isolated copy of the requested commit, through `bash .claude/hooks/run-hook.sh agent-large-read.sh`. No `.claude/plans/` files were accessed. The known state-file security finding is excluded.

Reproduction notation: `big` contains 500 lines, `small` 100, and `a200`/`z200` 200 each. Payloads have top-level `agent_id`, `tool_name`, `cwd`, and the stated `tool_input`; sequences reuse the same agent.

1. **Medium — BLOCKER (Q4c): downstream file operands bypass the limit and poison read history.**  
   `scripts/check-agent-large-read.py:285`

   Ran Bash input `{"command":"cat small | head -n 400 big"}`. Hook returned exit **0, silent**; executing Bash produced **400 lines**. The parser discards the downstream stage’s filenames and applies its operation to upstream content.

   Also ran `cat big | head -n 100 small`, followed by Read `{"file_path":"<absolute big>","limit":100}`. First call passed; second was denied: **“you already read 100 of these lines”**. Actual pipeline output contained only `small`, so those `big` lines were never delivered.

   Siblings searched: inspected downstream `cat`, `sed`, `head`, and `tail`; all use this discarded-file result. Local correction in the changed parser satisfies Q4c.

2. **Medium — BLOCKER (Q4c): globbed reads silently evade the guard.**  
   `scripts/check-agent-large-read.py:280`

   Ran `{"command":"cat b*"}` with matching `big`, `b301`, and `book.ipynb`. Hook returned **0, silent**; Bash produced **1,216 lines**. Each glob is treated as a literal nonexistent pathname.

   Siblings searched: all four supported readers share this path-resolution loop, so this affects `sed`, `head`, and `tail` too. Glob handling is absent from the PR’s declared exclusions. A local parser correction satisfies Q4c.

3. **Medium — FILE: Read counts notebook/PDF serialization instead of tool output.**  
   `scripts/check-agent-large-read.py:300`

   Ran Read on a valid one-cell notebook containing `x=1`, with trailing JSON whitespace making 415 physical lines. Hook denied it: **“this call puts 415 lines … into your context”**. Ran Read `{"file_path":"<valid.pdf>","pages":"1"}` on a valid, one-page ASCII PDF; denied as **371 lines**.

   `strings` on installed Claude Code **2.1.309** shows notebook handling resets `offset`/`limit` with `if(jx(it))n=1,r=void 0` and returns parsed cells. Consequently, accepting notebook reads with `limit:1`—which I also ran—does not limit actual notebook output.

   Siblings searched: inspected notebook, image, and PDF dispatch. The first-8-KB NUL heuristic is not equivalent to those tool types. This needs a local Read-specific correction; false refusals alone do not meet Q4c.

4. **Medium — FILE: supported `sed` commands receive false refusals.**  
   `scripts/check-agent-large-read.py:206`, `:283`

   Ran `sed -n '1,400p;1q' big`: hook denied **400 lines**; actual Bash output was **one line**. Quit instructions are explicitly recognized and then discarded.

   Ran `sed -n '1,200p' a200 z200`: hook denied **400 lines**; actual output was **200 lines**. The operation is applied separately per file, although this `sed` invocation numbers the combined input.

   Siblings searched: inspected quit handling, multiple ranges, multiple files, and negative `head` counts. Negative `head` counts also use an upper bound rather than an exact output count. Fix locally or return NOT CHECKED for unsupported semantics.

5. **Medium — FILE: identical Read calls already have native de-duplication.**  
   `scripts/check-agent-large-read.py:360`

   Ran the same whole-file Read of `small` twice: first passed; second received **“you already read 100 …”**.

   The installed binary’s `FNr` checks matching `offset`, `limit`, and timestamp and returns `type:"file_unchanged"`. Its renderer returns **“Wasted call — file unchanged since your last Read. Refer to that earlier tool_result instead.”** The hook therefore refuses an identical Read that normally returns a short stub.

   Siblings searched: inspected the seeded-read path and disabling conditions. De-duplication is conditional, so rule (b) is redundant for ordinary identical reads, **not universally redundant** for all overlapping ranges or configurations. The PR’s cost premise needs narrowing.

6. **Low — FILE: malformed payload/state shapes escape with tracebacks.**  
   `scripts/check-agent-large-read.py:321`, `:339`, `:389`

   Ran Bash payload with `cwd:23` and `{"command":"cat big"}`: exit **1**, traceback ending **`TypeError: expected str, bytes or os.PathLike object, not float`**, no NOT CHECKED message.

   Separately placed `{"reads":null}` in the isolated agent cache and ran Read of `small`: exit **1**, **`TypeError: 'NoneType' object is not iterable`**. A cache entry with `"at":"yesterday"` likewise produced a subtraction traceback.

   Siblings searched: checked cache container and timestamp validation; both are unchecked. This concerns schema recovery, independently of the excluded symlink/ownership issue.

7. **Low — FILE: clause-removal coverage claim is false.**  
   `scripts/check-agent-large-read.py:206`, `:352`, `:529`

   Against the pinned source, independently:
   - Removed `SED_QUIT.fullmatch(part)` recognition: **67/67 passed**, exit 0.
   - Removed size comparison while retaining mtime comparison: **67/67 passed**, exit 0.

   Siblings searched: inspected the mutation manifest and changed-file fixture. The manifest tests removal of the entire freshness comparison, while the fixture changes only mtime; neither proves the size clause independently.

Main-session exemption, 300/301 boundaries, beyond-EOF reads, and 50/51-line overlap behaved as intended in the probes. A same-size edit advancing mtime by **one nanosecond within the same second** was allowed; that suspected truncation defect did not reproduce.

VERDICT: NOT CONVERGED
