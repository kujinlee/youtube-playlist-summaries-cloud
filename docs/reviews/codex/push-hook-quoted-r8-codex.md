<!-- codex-review: model=gpt-6.1-sol -->

### R8-F1 — Blocking — Oversized refusal reason makes the hook fail open

At `.claude/hooks/block-default-branch-push.sh:241`, `deny` passes the reason through `jq --arg`. An oversized unknown option produces an oversized reason, exceeding the OS argument limit. `jq` never runs, but `deny` exits 0 with empty stdout: **allow**. The detector already refused, so the floor cannot prevent this adapter failure.

Repro using payload files, without executing their commands:

```bash
tmp="$(mktemp -d)"
git show origin/master:.claude/hooks/block-default-branch-push.sh > "$tmp/master.sh"

python3 - "$tmp" <<'PY'
import json, pathlib, sys
p = pathlib.Path(sys.argv[1])
for name, tail in [
    ("force", "--force"),
    ("verify", "--no-verify"),
    ("default", "master"),
    ("refspec", "HEAD:master"),
]:
    command = "git push origin feat/x --" + "z" * 1100000 + " " + tail
    (p / (name + ".json")).write_text(
        json.dumps({"tool_input": {"command": command}})
    )
PY

for name in force verify default refspec; do
  bash "$tmp/master.sh" < "$tmp/$name.json"
  bash .claude/hooks/block-default-branch-push.sh < "$tmp/$name.json"
done
```

**Observed for all four files:** master prints a deny decision; branch prints nothing, exits 0, and reports `jq: Argument list too long` on stderr.

**Fix:** bound refusal reasons before passing them as arguments, and print a fixed literal deny if serialization fails. Add these file-based payloads as regression cases.

Validation: hook self-test **65/65**, Python self-test **352/352**. Another **230** crafted file-based comparisons found no loosening. Neither existing suite detects this failure.

## Loosening answers
LOOSENING-CHECK f090c90de19b: not a loosening
LOOSENING-CHECK 2d51171ccc52: not a loosening
LOOSENING-CHECK a37789af0a0d: finding: oversized unknown option followed by --force yields silent allow where master denies (R8-F1)
LOOSENING-CHECK 19e3cb6a182b: finding: oversized unknown option followed by --force yields silent allow where master denies (R8-F1)
LOOSENING-CHECK 6a9e243ccfd4: not a loosening
LOOSENING-CHECK e6c86a86ce2e: not a loosening
LOOSENING-CHECK 30d52ad23ac7: not a loosening
LOOSENING-CHECK 4a4c20c73163: not a loosening
LOOSENING-CHECK e886704a5c48: not a loosening
LOOSENING-CHECK 727e65f884c9: not a loosening
LOOSENING-CHECK 484e60231961: not a loosening
LOOSENING-CHECK 2fec52dc562d: not a loosening
LOOSENING-CHECK c361c21aa22d: not a loosening
LOOSENING-CHECK 1c483d300bca: finding: oversized unknown option followed by --no-verify yields silent allow where master denies (R8-F1)
LOOSENING-CHECK 0639175f96f3: finding: oversized unknown option followed by --no-verify yields silent allow where master denies (R8-F1)
LOOSENING-CHECK 6ed1cdc83491: finding: oversized unknown option followed by HEAD:master yields silent allow where master denies (R8-F1)
LOOSENING-CHECK 475f8e419a00: finding: oversized unknown option followed by master yields silent allow where master denies (R8-F1)
LOOSENING-CHECK b4c2d38505b1: finding: oversized unknown option followed by master yields silent allow where master denies (R8-F1)
VERDICT: NOT CONVERGED
