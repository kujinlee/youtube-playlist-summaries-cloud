# Code review r1 — referential entry gate (backlog #82) — Codex half

Branch `backlog-82-referential-gate`, dispatched via `scripts/codex-review.py`, model gpt-5.5.
**2 Blocking, 3 High. NOT CONVERGED. All five folded — see below.**

<!-- codex-review: model=gpt-5.5 -->

Blocking — `scripts/check-dashboard-entry.py:746`  
Concrete failure: a genuinely new broken reference is missed when a branch adds a second entry with the same body-derived title and same dangling reference as a pre-existing broken entry. Duplicate titles are legal, and the spec says the identity is header line, not title.

Code:
```python
return Counter((e.get("title") or "", e["error"])
               for e in parse_entries(text) if e.get("error"))
```

Verified:
```text
duplicate same ref: ['[resolved: missing-a] names no entry in this file']
## 2026-08-28 [resolved: missing-a] 'Same title.' '[resolved: missing-a] names no entry in this file'
## 2026-08-29 [resolved: missing-a] 'Same title.' '[resolved: missing-a] names no entry in this file'
```
Input was:
```text
base = "## 2026-08-28 [resolved: missing-a]\nSame title.\n"
head = base + "## 2026-08-29 [resolved: missing-a]\nSame title.\n"
```
HEAD has two broken entries; the diff reports one, so the newly added one collides with the base one.

High — `scripts/check-dashboard-entry.py:746`  
Concrete failure: a pre-existing broken reference is reported as new when only its title text changes. The header line and error are unchanged, so under the spec key `(header line text, message)` this is not a newly added referential error.

Code:
```python
return Counter((e.get("title") or "", e["error"])
               for e in parse_entries(text) if e.get("error"))
```

Verified:
```text
preexisting error title edited: ['[resolved: missing-a] names no entry in this file']
```
Input was:
```text
base = "## 2026-08-28 [resolved: missing-a]\nOld title.\n"
head = "## 2026-08-28 [resolved: missing-a]\nEdited title.\n"
```

Blocking — `scripts/mutations/gen-dashboard.json:729`  
Concrete failure: delivered mutation mode fails; one mutation survived after the relocation. The mutation restores a page-local `BLOCK`, but `gen-dashboard.py` now imports `parse_entries` from the gate, so mutating `gen-dashboard.py`’s local `BLOCK` does not affect the parser cases named by the mutation.

Code:
```json
"edits": [
  [
    "BLOCK = _GATE.BLOCK",
    "BLOCK = re.compile(r\"^##\\s*\\S\")"
  ]
]
```

Verified on a copied `scripts/` temp tree:
```text
✗ mutation SURVIVED — the page takes back its own block-start rule: the suite stayed green, so no case can fail for what it names
FAILED — delivered scripts mutated: 8 file(s), 187 mutation(s), 1 survivor(s)
```

High — `scripts/mutations/check-dashboard-entry.json:437`  
Concrete failure: a moved gate mutation still names a `gen-dashboard.py` case as one of its required red cases, but `run_mutations()` runs only the mutated file’s suite.

Code:
```json
"expect": [
  "two [resolved:] flags are both kept",
  "two [resolved:] flags clear BOTH items"
]
```

Verified:
```text
✗ mutation 'second [resolved:] dropped': `expect` 'two [resolved:] flags clear BOTH items' matched 0 red case(s) — it was caught by something else: ['two [resolved:] flags are both kept'].
```

High — `scripts/mutations/check-dashboard-entry.json:477`  
Concrete failure: another moved gate mutation names the wrong case. The mutation was caught, but not by the named case, so the manifest attribution fails under the runner’s exact-name rule.

Code:
```json
"expect": [
  "an unrecognised flag is an ERROR, not a crash",
  "...and says WHICH text it could not recognise"
]
```

Verified:
```text
✗ mutation "the page imports the grammar's SYMBOLS but not its MEANING — a new flag crashes every render": `expect` 'an unrecognised flag is an ERROR, not a crash' matched 0 red case(s) — it was caught by something else: ['...and says WHICH text it could not recognise'].
```

Verdict: NOT CONVERGED.

---

## Disposition

| # | Finding | Response |
|---|---|---|
| B1 | duplicate title + same dangling ref hides a NEW broken entry | `parse_entries` now records `entry["header"]`; the diff keys on `(header line, error)` — which is what the spec said before I changed it |
| H1 | editing a pre-existing broken entry's title reported it as new | same fix; both reviewer inputs verified passing |
| B2 | `BLOCK = _GATE.BLOCK` mutation SURVIVED — the relocation made gen-dashboard's alias dead, so mutating it changes nothing | mutation moved onto the gate's real `BLOCK` definition, killed by `the block-start rule excludes a sub-heading`. gen-dashboard 65→64, gate 42→43, **sum still 107** |
| H2 | `second [resolved:] dropped` named a case that no longer exists | `expect` repointed at the case that actually goes red |
| H3 | `the page imports the grammar's SYMBOLS…` was caught by its sibling, not the named case | same |

⛔ **B2 IS A FINDING ABOUT MY VERIFICATION, NOT JUST THE CODE.** I ran the gate's manifest and
never gen-dashboard's, so a mutation the relocation had hollowed out reported nothing. That is the
recorded *a measurement is only as good as its CORPUS* shape — the third instance today. Both
manifests are now run together, controls first: 43/43 and 64/64, zero survivors.

**REVIEW GAP: claude — the Agent tool is disabled this session**, so no independent Claude half
could be dispatched. Recorded as a gap rather than filed as a half: a decaying curve from
one-and-a-half reviewers must not read as convergence.
