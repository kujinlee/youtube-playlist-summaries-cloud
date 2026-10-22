<!-- codex-review: model=gpt-6.1-sol -->

**FAIL — changes required.** Reviewed disk at `0cb448cb`, including both commits. No repository files changed.

1. **High: the shipped harness suite is red.**  
   `python3 scripts/check-plan-code.py --self-test` returns **1: 176/178 passed**. Its pinned manifest-name list omits the new guard, and [line 5185](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-plan-code.py:5185) still expects **1545**, while `EXPECTED_MUTATIONS` sums to **1552**. CI invokes this suite. The claimed total update is incomplete.

2. **High: C4’s tests permit measuring the wrong file.**  
   Independently executed mutations that retain **26/26 green**:
   
   - Change `INDEX` from `MEMORY.md` to `slice-history.md`.
   - Subtract one byte from the size passed to `budget_verdict`; an actual 24,986-byte index then passes.
   - Replace the repo-relative diagnostic label with `"WRONG"`.
   
   The first defeats the guard’s purpose; the second misses its exact failure boundary. Add independent subject-path assertions, adjacent integration boundaries, and captured-output assertions.

   Further probes: changing `WARN_FRACTION` to `0.95` **is caught**. Replacing `n_bytes is None` with `not n_bytes` survives, but preserves failure behavior for both supported inputs; its loss is diagnostic specificity.

3. **Medium: C5’s corpus arithmetic is false.**  
   Using the live matcher’s `memory_files`, `frontmatter_description`, and `parse_trigger`:
   
   | Revision | Entries | Triggered | Triggerless |
   |---|---:|---:|---:|
   | Before move | 162 | 158 | 4 |
   | Current | 163 | 159 | 4 |
   
   Besides the two acknowledged entries, `cannot-die-may-mean-a-second-clause` and `the-apparatus-outgrew-its-subject` lack triggers. The move adds one valid trigger; it does not produce 161. `corpus_verdict` remains green because it requires only nonzero files and nonzero triggers.

4. **Medium: C1/C7’s supporting measurements are inaccurate, and truncation semantics remain unverified.**  
   Confirmed **27,805 → 22,333 bytes**. Before the move, counting lines beginning `- ` gives **146 rows**, **35 over 200 characters**, **38 over 200 bytes**; maxima are **602 characters / 620 bytes**. The historical section contains 28 linked bullets plus the “Older slices” bullet and continuation lines.

   Under a hypothetical 24,985-byte prefix cut, the remaining suffix spans **24 physical lines**, beginning mid-row—not evidence of “~30 of 118 rows.” Also, the guard’s claim that character counting would have reported the old index as fitting is false: **26,930 characters still exceeds 24,985**.

   **I could not interrogate the actual injection harness. Its byte-versus-row truncation behavior is NOT VERIFIED; that part of this gate fails verification.** A quoted warning establishes reported truncation, not its precise algorithm.

5. **Medium: C2 understates uncertainty and overclaims success.**  
   The constant can also be wrong through KB-unit interpretation, changed harness/version configuration, or budgeting after text transformation or added framing. Raising the real limit creates false failures. A measured producer specification or controlled boundary experiment can refute the constant; a warning alongside green output is not the “ONLY” observation.

   A 90% advisory band comfortably exceeds ±51-byte rounding uncertainty, but does not resolve it: sizes near the declared limit can still print “Nothing is being dropped YET.” Treat the bound as provisional rather than asserting “Every row arrives.”

6. **Medium: unreadable files violate the advertised exit contract.**  
   At [index_size](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-memory-index-budget.py:123), `read_bytes()` errors escape. Injecting `PermissionError` produces an exception instead of a named `CANNOT RUN` with rc **2**. Catch filesystem read failures and test that path.

7. **Low: argument validation is bypassed by self-test.**  
   `main(["--self-test", "--bogus"])` returns **0**, contradicting its unknown-flag contract. A bare `-` returns **2**; rejecting it is not inherently wrong for a command accepting no operands. Plain positional garbage is silently accepted. Validate arguments before dispatch.

8. **Medium: C6 confuses retention with an immutable citation.**  
   PR #376 is currently **OPEN**; its advertised pull head is `2e0ad1ef35ef87bf96e91757ea2cc143b6d2b010`. Locally, `d06da80c` is not an ancestor of `master`, and the script is absent from `master`.

   However, `refs/pull/376/head` follows the PR head; it does not pin the measured implementation. GitHub documents fetching the pull ref, but that is not an unconditional archival guarantee. [GitHub documentation](https://docs.github.com/en/pull-requests/how-tos/review-pull-requests/checking-out-pull-requests-locally?tool=webui).

   Cite the exact full commit and file, with the PR as retrieval context. After a squash merge that includes the script, the entries’ present-tense “NOT on master” claims become false, while their pull-head citation remains a historical copy. Date those claims and distinguish historical evidence from the current implementation.

Other requested checks:

- The entire old history body is preserved **verbatim**. Both files have zero broken Markdown relative-file links. My repository search found no incoming `MEMORY.md` fragment references to the removed heading.
- The destination is correct for recall’s flat `glob("*.md")` discovery. Firing prints the name and trigger, **not the 7,386-byte body**; it introduces no automatic body injection in this implementation. It does add a trigger to every matching prompt, so “cost nothing otherwise” is too strong.
- The literal default label duplicates `INDEX`’s path. `check-vocabulary-collisions` examines database coordination vocabulary and cannot detect this duplication.
- Local execution reads working-tree bytes and detects uncommitted overflow. CI protects committed growth; it cannot observe later local corruption. No automatic local invocation of this guard was found.
- No existing equivalent byte-budget gate was found. The link guard and docs check passed; their green results do not establish successful injection.

Execution: guard **rc 0**, guard suite **26/26**, recall suite **201/201**, docs check passed, symlink resolved. The pruned `HARNESS_TREE` mutation run independently reproduced **7 killed, 7 attributed, 0 survivors**, with green controls. That result holds for the shipped seven mutations; it does not cover the surviving failures above.
