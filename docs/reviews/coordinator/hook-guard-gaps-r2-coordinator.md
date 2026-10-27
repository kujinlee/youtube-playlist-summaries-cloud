# Round 2 — `hook-guard-gaps` — coordinator — ✅ bet HELD; one Low (prose) fixed

```yaml
round: 2
fixes_nontrivial: false
subject: hook-guard-gaps
halves:
  codex: ran
  claude: skipped
findings:
  - {id: XL1, severity: Low, aim: deliverable, fix_induced: false, component: prose, disposition: fixed}
```

REVIEW GAP: claude — round 2 alternates to the Codex half (`review-method.md`, *The protocol*, step 4; backlog #339).

`X` = Codex, tree `a87232ee`. The ACCRETE bet HELD: the five types were checked against Claude Code 2.1.309's own
hook-schema factory (`claude --version` 2.1.309); `agent`, `http` and `mcp_tool` each exit 0; a list, object, number, null,
missing or unknown `type` each exit 2 with no crash; reasons `None`, `0`, `False`, `[]`, `{}`, empty and whitespace each
exit 1; 29/29; 16/16 mutations real (killed, attributed, green control and re-control).

- **XL1 (fixed, prose):** the docstring and backlog #368 said a non-default `shell` launches nothing, like `args`. It does
  not: without `args` the command runs through a shell, and `shell: "powershell"` selects `pwsh`. Both now say so.

The decision-log row is closed (`outcome: stopped`, 2 rounds). The prose commit touches a guarded file, so a
confirmation round reviews it before merge.
