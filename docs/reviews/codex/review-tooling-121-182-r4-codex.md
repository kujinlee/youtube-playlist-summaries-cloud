<!-- codex-review: model=gpt-6.1-sol -->

1. **Major — `scripts/codex-review.py:573`, `:625` — missing artifact trees bypass identity checking. Fix-induced: no.**  
   Concrete input on this case-insensitive volume: create `<B>/docs`, leave `docs/reviews` absent, then run from B with `--out <B>/DOCS/REVIEWS/claude/x.md`. The real CLI with a stub Codex returns **0** and writes into B’s artifact tree. `stat(tree)` fails, and the lexical comparison misses the capitalization. Also reproduced using an NFC root `café` and its NFD spelling in `--out`. Compare existing ancestors and remaining path components using filesystem semantics.

2. **Major — `scripts/codex-review.py:623`, `:1420` — hard-linked scratch output overwrites an unwatched review. Fix-induced: no.**  
   Concrete input: `ln <B>/docs/reviews/claude/victim.md <scratch>/hard.md`, then `--out <scratch>/hard.md --allow-overwrite`. The parent directory passes containment checking; opening the file truncates the filed review through its hard link. Reproduced through the CLI: **rc=0, victim changed, `intrusions: []`**. Write the capture to a new file and replace the scratch directory entry atomically.

3. **Major — `scripts/codex-review.py:1292`, `:1420` — a symlink created during dispatch defeats the frozen resolution. Fix-induced: no.**  
   Concrete input: start with absent `<scratch>/late.md`; have the stub create `late.md -> <B>/docs/reviews/claude/victim.md` before returning a valid review. The wrapper follows that newly created link when writing. Reproduced: **rc=0, victim overwritten, `intrusions: []`**. The watch excludes the output basename and does not inspect the victim’s writer directory. Use exclusive temporary-file creation and atomic replacement instead of following the output entry.

4. **Minor — `scripts/codex-review.py:580`, `:2737` — device identity is untested; an additional mutant survives. Fix-induced: yes.**  
   Replace `(st.st_dev, st.st_ino) == (t.st_dev, t.st_ino)` with `st.st_ino == t.st_ino`: **196/196 self-tests still pass**. The identity fixtures pass for the ambient reason that their directories share a device. Concrete distinguishing input: tree `(dev=1, ino=42)`, ordinary scratch ancestor `(dev=2, ino=42)`. The mutant falsely refuses scratch. Add this cross-device negative fixture.

The requested five-file diff against `origin/master` is empty. Backlog #182 is honestly **REOPENED**, with the split and coordinator-only direction recorded.

Successful CLI probes confirmed that verdict `head` equals the stub’s observed Git HEAD and that Codex runs at the recorded tree. No false scratch refusal was reproduced in the actual implementation; bind/mount aliases were not exercised.

Both requested commands completed:

- Self-test: **196/196 passed**.
- Mutation slice: **64/64 killed and attributed**, exit 0. Its output explicitly calls this a diagnostic slice, not the full gate.

**NOT CONVERGED** — the split’s named failure observation occurred.
