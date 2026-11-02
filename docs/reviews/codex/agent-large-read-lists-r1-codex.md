<!-- codex-review: model=gpt-6.1-sol -->

Self-test: **96/96 passed**. All **95 mutations** failed in their named tests. Nevertheless, the payload probes found six defects.

For the inputs below, use a subagent payload:

```json
{"agent_id":"a1","tool_name":"Bash","cwd":"FIXTURE","tool_input":{"command":"COMMAND"}}
```

Feed it to `python3 scripts/check-agent-large-read.py --hook`. In `FIXTURE`, create text files `a` and `b` with 200 lines each, `big` with 500 lines, and a file named `;` with one line. Counts below were verified by executing the commands in Bash.

1. **HIGH — Redirect removal consumes list separators and changes reader semantics.**  
   [scripts/check-agent-large-read.py:298](scripts/check-agent-large-read.py:298), using the regex at line 116.

   ```bash
   sed -n 1,200p a 2>/dev/null; sed -n 1,200p b
   ```

   Bash prints **400 lines**; the hook returns **exit 0, empty stdout and stderr**. The regex’s `\S+` consumes `/dev/null;`, merging two separate `sed` streams into one stream whose range prints only 200 modeled lines.

   The same defect causes a costly false refusal:

   ```bash
   cat a 2>/dev/null; head -n 1 b
   ```

   Bash prints **201 lines**, but the hook **denies, claiming 400**: after merging, it interprets both files as `cat` operands. Redirect parsing must preserve shell separators.

2. **HIGH — `printf` is accepted as state-free even when `-v` changes reader operands.**  
   [scripts/check-agent-large-read.py:376](scripts/check-agent-large-read.py:376).

   With `D=big` in the hook and Bash environments:

   ```bash
   printf -v D a; cat "$D"
   ```

   Bash prints **200 lines**; the hook **denies, claiming 500**. It expands the original environment’s `D`, ignoring the successful assignment.

   Conversely, with initial `D=a`:

   ```bash
   printf -v D big; cat "$D"
   ```

   Bash prints **500 lines**; the hook **allows silently**. This was previously an allowed compound command; the new whitelist introduces the false refusal. Treat state-changing `printf` forms as outside the understood list bound.

3. **HIGH — Quoted operator operands make an entirely understood reader list fail open.**  
   [scripts/check-agent-large-read.py:290](scripts/check-agent-large-read.py:290), reached from line 367.

   ```bash
   cat a ';'; cat b
   ```

   Bash prints **401 lines**; the hook **allows silently**. `shlex` removes quotation information, then `OPERATOR.fullmatch(';')` mistakes the filename operand for a shell operator. `list_spans` consequently treats the first reader as unknown and discards the entire sum. The list contains only simple readers and a quoted filename.

4. **HIGH — Failed `cd` before `;` incorrectly changes the modeled directory.**  
   [scripts/check-agent-large-read.py:375](scripts/check-agent-large-read.py:375).

   Ensure `missing` does not exist:

   ```bash
   cd missing; cat a; cat b
   ```

   Bash leaves its directory unchanged and prints **400 lines**. The hook moves its modeled cwd into `missing`, finds neither file, and **allows silently**. This is distinct from the explicitly documented overcount after an `&&` failure: semicolon-separated readers actually execute.

5. **HIGH — Successive `cd` operations use filesystem traversal instead of Bash’s logical directory semantics.**  
   [scripts/check-agent-large-read.py:375](scripts/check-agent-large-read.py:375).

   Additional fixture:

   ```bash
   mkdir -p logical physical/child
   ln -s ../physical/child logical/link
   cp big logical/big
   ```

   Reproducing input:

   ```bash
   cd logical/link; cd ..; cat big
   ```

   Bash’s logical `cd ..` reaches `logical` and prints **500 lines**. The hook retains `logical/link/..`, which filesystem lookup resolves to `physical`, and **allows silently** because `physical/big` is absent. Normalize logical directory transitions before resolving subsequent operands.

6. **MEDIUM — Empty-part handling accepts invalid shell syntax and falsely refuses it.**  
   [scripts/check-agent-large-read.py:365](scripts/check-agent-large-read.py:365).

   ```bash
   cat big;;
   ```

   Bash rejects this with a syntax error before executing anything: **zero stdout lines**. The hook skips both empty parts and **denies, claiming 500 lines**. Supporting a valid trailing `;` must not also accept `;;` or missing operands around `&&`.

VERDICT: NOT CONVERGED
