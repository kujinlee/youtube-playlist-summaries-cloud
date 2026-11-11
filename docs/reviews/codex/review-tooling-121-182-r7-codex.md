<!-- codex-review: model=gpt-6.1-sol -->

- **Blocking — scripts/codex-review.py:676–678:** A nested symlink escapes every compared root. Concrete input: `A/docs/reviews/nested -> /tmp/external`, then `--out A/docs/reviews/nested/victim.md --allow-overwrite`. Both `master` and `origin/master` refuse (exit 2); this branch’s real CLI accepts (exit 0) and overwrites the victim. Resolving `--out` erases its route through `docs/reviews`; adding only the resolved review root does not protect deeper symlinks.

Other requested comparisons found no regression: top-level review symlinks inside/outside the checkout, case/NFD variants, hard links, and late file symlinks. Ordinary scratch output was accepted.

Validation:
- Self-test: **205/205 passed**.
- Requested mutation command: exit 0, **67/67 killed and attributed**. Its output explicitly identifies this `--only` run as a diagnostic slice, not the full gate.

**NOT CONVERGED**
