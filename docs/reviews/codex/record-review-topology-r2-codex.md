<!-- codex-review: model=gpt-5.5 -->

**Blocking**

`scripts/check-review-recorded.py:228-230`, with `scripts/codex-review.py:307-309` and `scripts/check-review-recorded.py:286-288`: the dirty/final comparison records only blob content, so a mode-only change after review is credited as reviewed.

```py
missed = [p for p in guarded_changes(after)
          if not (reviewed.get(p) and final.get(p) == reviewed.get(p))]
```

Concrete scratch sequence:

1. `bin/tool.sh` committed as `100644`, content `base`.
2. Before review, change content to `reviewed`, still `100644`; `reviewed_state()` records dirty blob `556db78...`.
3. After review, change only mode to executable `100755`.
4. Commit code, review doc, and verdict.

The gate returned rc 0:

```text
ok — the final tree was reviewed by mode-r1-codex.verdict.json
```

But the final tree contains `100755 blob 556db78... bin/tool.sh`; the reviewer saw the bytes, not the executable-bit change. This is the r1 blocking class in another form: a path is credited whose final tree state the reviewer did not see.

**High**

`scripts/check-review-recorded.py:354-359` accepts any `REVIEW GAP:` from any added review doc, and `scripts/check-review-recorded.py:251-256` lets that clear “no Codex verdict was added” without checking that the gap names Codex.

```py
if reason := mod.has_gap_line(p.read_text(encoding="utf-8", errors="replace")):
    return reason
```

```py
if gap:
    return 0, f"final-tree rule NOT CHECKED — {why}; declared: REVIEW GAP: {gap}"
```

Concrete scratch sequence:

1. Change `lib/x.py`.
2. Add only `docs/reviews/claude/topic-r1-claude.md`.
3. Put `**REVIEW GAP:** claude — not invoked; ran as r2` in that doc.
4. Add no Codex verdict.

The gate returned rc 0:

```text
ok — final-tree rule NOT CHECKED — no Codex verdict was added by this branch; declared: REVIEW GAP: claude: not invoked; ran as r2
```

A Claude gap does not explain why the Codex verdict needed for this final-tree rule is absent. This reopens the cannot-run fix as a false pass.

**Medium**

`scripts/codex-review.py:302-309` does not faithfully record some reviewed working-tree states, causing false failures on careful branches.

```py
names = git("diff", "--name-only", "-z", "--no-renames", "HEAD") or ""
...
blob = git("hash-object", "--", path)
```

Two verified cases:

- Symlink: changing `link -> target1` to `link -> target2` while both targets already exist records the hash of `target2`’s contents, but the committed Git blob is the link text `target2`. The gate returned rc 1 and named `link` as unseen, even though the reviewer saw the symlink change before commit.
- Untracked new file: a new `lib/new.py` present during review is omitted because `git diff HEAD` excludes untracked files. After committing it with the review artifacts, the gate returned rc 1 and named `lib/new.py` as unseen.

This is fail-closed, but it contradicts the documented careful path of holding fixes uncommitted for review.

**Verification**

Ran:

```text
python3 scripts/check-review-recorded.py --self-test  # 52/52 passed
python3 scripts/codex-review.py --self-test           # 68/68 passed
```

I also inspected the 15 `scripts/mutations/check-review-recorded.json` entries. I did not find an equivalent mutation among them; the issue is missing behaviours around mode, gap ownership, symlink, and untracked-file state rather than an existing listed mutation being bogus. I verified clean filters and `ident` in scratch repos and could not reproduce a blob mismatch there.

NOT CONVERGED.
