<!-- codex-review: model=gpt-6.1-terra -->

**MAJOR — a quote split by `<noscript>` can pass `--check` while visible to a reader with scripting enabled.**

- **fix_induced:** false
- **component:** hidden-text
- **Location:** [build-shipped-corpus.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/.claude/worktrees/bl698/scripts/build-shipped-corpus.py:216)
- **Input:** A real six-word group-D fragment, with three words on each side of `<noscript>distractor</noscript>`.
- **Observed:** `--check` returned 0. The text extractor retains the distractor in every reading, so it interrupts the fragment. With scripting enabled, the browser hides the `<noscript>` contents and displays the fragment across it.
- **Expected:** The visible fragment should cause check 1 to fail.
- **Fix:** Add a reading that drops `<noscript>` contents for the scripting-enabled rendering, and cover a real-fragment-shaped split in the self-test.

This is **not a BLOCKER** under the specified definition: the reproducer is constructed; I did not find a real quote shipping in today’s tree or a crash. It does lose the pending hidden-text redesign bet.

In a full external clone, the clean script passed **73/73 self-tests**, `--out`, and `--check`. Three new mutations—end-tag closure, implicit paragraph closure, and NFKC in place of NFKD—each failed their named self-test. The real-fragment normalization invariant passed. Constructed comment, template, `hidden`, and hidden-void probes were refused; CSS hiding and the tested misnested construct also produced misses, consistent with limitations already documented in the script.

The single-line non-self-test CI checks were run in the clone. The Jest count check lacked `jest-results.json`; the self-test-count aggregation and built-site link check timed out at 40 seconds. Multiline CI invocations were not covered by that sweep, so I cannot claim the complete requested CI verification. No review finding was filed, and the original worktree was not changed.

## Loosening answers
LOOSENING-CHECK 169c08d5f317: not a loosening
LOOSENING-CHECK 0e4ccb90eeb2: not a loosening
LOOSENING-CHECK 8c08951f5d7e: not a loosening
LOOSENING-CHECK de62ef368291: not a loosening
LOOSENING-CHECK 3e58e77f52b1: not a loosening
LOOSENING-CHECK ca964ae7f0eb: not a loosening
LOOSENING-CHECK 73d42d6fc6cc: not a loosening
LOOSENING-CHECK ed4660bb0eb7: not a loosening
LOOSENING-CHECK 250c739c54f2: not a loosening
LOOSENING-CHECK eeaff0d7f286: not a loosening
VERDICT: NOT CONVERGED
