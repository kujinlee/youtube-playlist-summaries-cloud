<!-- codex-review: model=gpt-6.1-sol -->

Reviewed the round-1 coordinator and Claude reports and `git diff 9dd8ea99..HEAD` at **8516de43**. Scope: fold only. No `.claude/plans/` reads or GitHub actions.

**F1 — MAJOR — whitespace repair corrupts valid CRLF logs.**  
At `scripts/goal-tree.py:1206`, `fh.read()` normalizes CRLF to LF, but `truncate(len(body.encode()))` uses that shortened length as an offset into the original file.

Concrete failing input, constructed as:

```python
agenda = '{"kind":"agenda","at":"t","id":1,"window":"w","steps":[{"when":"g","text":"free","refs":[]}]}'
tick = '{"kind":"tick","at":"t","of":1,"step":1}'
data = (agenda + "\r\n" + tick + "   ").encode()
```

The log initially replays successfully. Calling `record_agenda` returns success, but truncates the tick’s closing `}` before appending. Subsequent replay raises `Malformed` on line 2. Reproduced against both versions: **9dd8ea99 preserves the record; HEAD corrupts it**.

Fix: calculate truncation offsets from original bytes, preserving newline representation.

**F2 — MINOR — deriving kinds by splitting regex text still permits writer/reader drift.**  
At `scripts/goal-tree.py:1048`, the extraction assumes a flat literal alternation and ignores regex flags.

Concrete reproductions:

| Grammar change | Derived kinds | Failure |
|---|---|---|
| `r"\b(backlog|(?:PR)) #(\d+)\b"` | `('?:PR',)` | Writer emits `["PR",7]`, reader refuses it; reader accepts `["?:PR",7]`, which the writer cannot produce. |
| `r"\b(backlog|PR|foo\|bar) #(\d+)\b"` | `('backlog','PR','foo\\','bar')` | Writer emits `["foo|bar",7]`, reader refuses it; reader accepts nonexistent kinds. |
| Existing pattern compiled with `re.I` | `('backlog','PR')` | `- pr #7` produces `["pr",7]`, which the reader refuses. **All 406 self-tests still pass.** |

An outer noncapturing wrapper preserves behavior. Replacing the kind capture itself with a noncapturing group breaks the writer’s unpacking contract.

These are latent failures requiring a grammar edit. The case-insensitive variant demonstrates drift that also escapes the updated test. Prefer explicit shared kind metadata used to construct the grammar, with a deliberate casing policy.

**F3 — MINOR — a refused incomplete record loses string data.**  
At `scripts/goal-tree.py:1204–1208`, truncation happens before validation.

Concrete file contents, with no final newline:

```text
{"kind":"agenda","text":"unfinished   
```

Attempting to record raises `Malformed`, but first removes the three spaces belonging to the unfinished JSON string. The damaged input is modified despite refusal. Validate before mutating the file.

For **complete JSON records**, trailing spaces inside string fields were preserved, including records without a final newline. Unicode fields and ordinary LF whitespace repair also passed.

All requested mutations were checked in temporary copies:

| Mutation | Anchor count | Named case killed it |
|---|---:|---|
| Lone-newline log retained, re-anchored | 1 | Yes |
| Whitespace-only log not emptied | 1 | Yes |
| Trailing blanks retained | 1 | Yes |
| Non-grammar kind added | 1 | Yes |

Manifest count: **308**, matching the pin. Every mutation exited nonzero.

Requested self-test output:

```text
406/406 self-test cases passed
```

**Findings: 0 BLOCKER, 1 MAJOR, 2 MINOR.**

VERDICT: NOT CONVERGED
