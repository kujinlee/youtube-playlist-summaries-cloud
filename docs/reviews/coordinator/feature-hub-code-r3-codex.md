<!-- codex-review: model=gpt-5.5 -->

**Low** — [scripts/check-features.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-features.py:91): the new duplicate-field instruction is false for scalar fields.

The duplicate guard applies to every field:

```python
if key in seen_fields:
    problems.append(... "Put every value on ONE comma-separated line. " ...)
```

That remedy is correct for duplicate `areas:` / `anchors:`, but not for duplicate `state:`. Trigger:

```markdown
### node
state: built
state: absent
```

The message tells the author to put every value on one comma-separated line, but following that instruction:

```markdown
state: built, absent
```

then fails with:

```text
`node` has state 'built, absent'; expected `built` or `absent`
```

I found no other defects in the edited text. The continuation-line comment now matches what the cases actually prove, the narrowed `regen-backlog-page.sh` precedent claims match the code, the field grammar message is true for the tested malformed lines, and the updated mutation anchor still resolves once.

Ran:
`python3 scripts/check-features.py --self-test`
`python3 scripts/gen-features-page.py --self-test`
`python3 scripts/check-plan-code.py --self-test`
plus targeted malformed-input checks for leading space, tab, capital field, space before colon, stray blockquote, duplicate `areas:`, and duplicate `state:`.
