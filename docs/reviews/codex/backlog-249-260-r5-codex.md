<!-- codex-review: model=gpt-6.1-sol -->

## Blocking

None established.

## High

**H1 — The new inline-code mask suppresses live prose.**  
`scripts/check-withdrawal.py`, `mask_inline_code()`:

```python
runs = [m for m in BACKTICK_RUN.finditer(text) if len(m.group(0)) <= 2]
```

The loop pairs escaped backticks and backticks in different paragraphs. Both inputs incorrectly inherit the earlier `was` marker:

```text
the count was \`wrong:
holds 1,414 anchors today \`
```

```text
the count was `wrong

holds 1,414 anchors today`
```

**Ran:** Python 3.12 against `cmarkgfm`’s cmark parser, which rendered both as prose with no `<code>` span. Called the shipped `history_marker()`: both returned `'was '`. Drove shipped `main(--strict)` over temporary documents with a controlled correction diff, `1,414 → 1,416`: both returned **0**, reporting no survivor and one history suppression. The same claim beneath an ordinary colon lead-in returned **1**; a genuine code span returned **0**.

The diff provider was stubbed; document discovery, matching, offsets, suppression and verdict were real. This is another fix becoming the defect, in the expensive direction.

## Medium

**M1 — An unmatched opener prevents later genuine spans from being masked.**  
`scripts/check-withdrawal.py`, `mask_inline_code()`:

```python
if j >= len(runs):
    break
```

Input:

```text
a `unclosed then ``the count was wrong:
holds 1,414 anchors today``
```

The unmatched single backtick stops processing before the valid double-backtick span. Its internal colon newline becomes a sentence boundary.

**Ran:** cmark rendered the double-backtick contents as `<code>`. The shipped mask returned the input unchanged, `history_marker()` returned `''`, and the controlled-diff `main(--strict)` drive returned **1**, incorrectly reporting a survivor.

---

**M2 — The new slug readback still passes when production ignores its argument.**  
`scripts/codex-frontier-model.py`, `_write_config_arm()`:

```python
write_config("gpt-written-through")
```

```python
return (0, "wrote" if 'model = "gpt-written-through"' in written
        else "wrote-without-slug")
```

The other slug literal is exercised only where writing fails. Consequently, these cases do not distinguish argument propagation from a production constant matching the writable fixture.

**Ran:** In a temporary scripts copy, replaced:

```python
f'model = "{slug}"\n'
```

with:

```python
'model = "gpt-written-through"\n'
```

Confirmed valid syntax with `ast.parse()`. Under empty HOME, the suite returned **0, 46/46**, with no `[FAIL]`. Calling that mutant’s `write_config("gpt-requested")` wrote:

```toml
model = "gpt-written-through"
```

The new probe’s claim that readback proves the argument arrived is false.

---

**M3 — The added config-read refusal path is unmeasured and incomplete.**  
`scripts/codex-frontier-model.py`, `write_config()`:

```python
except OSError as e:
    cannot_run(f"error: cannot read {CONFIG}: {e} ...
```

Neither new probe creates an existing unreadable config. Both enter with `config.toml` absent.

**Ran:** Removed this entire read-side guard in a temporary copy, confirmed valid syntax, and ran under empty HOME: **rc=0, 46/46**, no `[FAIL]`. Separately, an existing chmod-000 config exercised the shipped guard and raised `SystemExit(2)`.

The new refusal boundary also misses decoding failure. With a valid model cache and `config.toml` containing byte `0xff`, the actual command:

```text
python3.12 scripts/codex-frontier-model.py --write-config
```

returned **1 with a UnicodeDecodeError traceback**, rather than CANNOT RUN. The crash predates this fold; the newly added guard and coverage claim leave that class member unresolved.

---

**M4 — The tightened HEAD suffix still accepts malformed tokens as provenance.**  
`scripts/check-provenance.py`, `PROVENANCE_RE`:

```python
r"|`HEAD(?:[~^]\d*)?`|\bHEAD(?:[~^]\d*)+(?![\w~^])"
```

`\d` accepts non-ASCII digits, and the terminal assertion permits matching a prefix before punctuation.

**Ran:** Under Python 3.12, each row containing `**47 s**; measured at` one of:

```text
HEAD~١
HEAD~１
HEAD~1.5
```

produced `findings_for(...) == []`. `git rev-parse --verify` rejected every token with **rc=128**. The Unicode forms are malformed numeric suffixes, independently of ancestry availability.

This is an incomplete repair of the token-validation class, rather than a newly introduced acceptance. It does not challenge the deliberate acceptance of valid `HEAD^2` syntax.

## Low

**L1 — Arm classification can attribute a refusal to text in the temporary path.**  
`scripts/codex-frontier-model.py`, `_refusal_arm()`:

```python
for needle, arm in (("not found", "not-found"),
                   ("cannot read", "cannot-read"),
                   ("parsed but its", "malformed"),
                   ("no LISTED", "no-candidate")):
    if needle in msg:
        return (code, arm)
```

**Ran:** Set `tempfile.tempdir` to a temporary directory named `not found`, then supplied `{"models":"oops"}`. The actual malformed-cache refusal was classified as **`(2, "not-found")`** because the path supplied the first needle.

This causes a false test failure; I did not establish a false pass.

---

**L2 — Duplicate-anchor refusal does not force omission of the FLOOR neighbour mutation.**  
`scripts/check-plan-code.py`, `EXPECTED_MUTATIONS` commentary:

```text
its anchor is already taken ... the harness REFUSES a second entry on one anchor
```

That is true for identical anchor strings, but the stated residual is avoidable.

**Ran:** In a temporary copy, added a FLOOR `12 → 11` entry anchored on `"EXPECT_OVERLAP_FLOOR = 12\n"`, alongside the existing anchor without the newline. `load_manifests()` loaded **1,516 entries with no problems**; `binding_problems()` returned **([], [])**.

In a complete harness-tree copy, FLOOR `12 → 11` and `12 → 13` each produced exactly one intended named `[FAIL]`, with no traceback. The omitted ratchet entry is a choice, not a constraint imposed by the loader.

## Checked and found SOUND

All runs used **Python 3.12**. The reviewed worktree remained clean.

- Diff arithmetic reproduced: **10 files, 666 insertions, 43 deletions**.
- Independently parsed `EXPECTED_MUTATIONS` and every manifest: **62 manifests, 1,515 entries**, every per-file count matching.
- Self-tests returned **0**: find-claim **86/86**, withdrawal **101/101**, provenance **140/140**, plan-code **237/237**, frontier-model **46/46**.
- `--binding` returned **0**, reporting **1,523 anchors / 1,515 entries**.
- Fixture variation, rc contract and review-round checks each returned **0**.
- Executed all **six new manifest mutations** in temporary copies under empty HOME. Every mutation parsed and produced its named `[FAIL]`, without traceback. The fraction mutation was rerun in a complete harness tree: control **237/237**, mutant **236/237**, exactly its intended failure.
- Empty-HOME controls also passed for find-claim, withdrawal, provenance and frontier-model.
- `_refusal_arm()`’s valid-cache control now kills deletion of `CACHE = path` under empty HOME. Its restoration is in `finally`; a normal resolver return cannot satisfy the refusal tuples.
- `_write_config_arm()` uses a fresh directory, so its readback cannot consume a pre-existing stale config. Normal success and captured refusal paths restore permissions and `CONFIG`.
- The top-level named-path mutation produced three named failures. The new unreadable-directory sentinel no longer grants itself a passing value.
- `_nonfile_entry_probe()` establishes dangling-symlink skipping. It does **not** establish vanished-file policy. #263 remains arguable: reporting an unsearched discovered subject need not require refusing every pre-existing dangling link.
- #264 accurately identifies the unchanged caller gap: `resolve_candidates()` can unwind past `emit`. This fold records that gap rather than fixing it.

## CANNOT RUN

None for the requested checks or reported reproductions. I did not execute the entire 1,515-entry mutation sweep; I executed the six added entries and the targeted mutations described above.
