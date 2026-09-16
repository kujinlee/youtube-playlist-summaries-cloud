<!-- SUBJECT: master @ 32c56bfa — NOT a review of any branch's fixes -->

# ⚠ WHAT THIS REVIEWED, stated because it was briefly filed as something else

**Subject: `master` at `32c56bfa`** — the merged state of PR #311, *before* the fixes that its own
findings produced. This is the **retroactive Codex half** for backlog #122, whose three rounds all
merged with `REVIEW GAP: codex` because a 900s default timeout was read as Codex being unavailable.
It ran at `--timeout 3600` and completed on the first attempt.

⛔ **It was first filed as `fix-src-viewer-escaping-r1-codex.md`, i.e. as round 1 of the branch that
FIXES what it found — a review of the parent presented as a review of the child.** Caught by that
branch's Claude half, which also measured that `check-review-rounds.py` cannot see this class:
`verdict_problems` returns early on `if rec.get("gate_ran"): continue`, so it only ever asks whether
a review is filed for a gate that did **not** run. A verdict that ran, against a different commit,
naming a review file not on disk, produces zero problems. Renamed so the artifact and its verdict
agree about their subject; the branch's own Codex half is filed separately.

---

<!-- codex-review: model=gpt-5.5 -->

CONVERGED: **No**. I found two real gaps outside backlog #129 and #130.

**Medium — encoded extensions still get the `.html` fallback**
[explainer-serve.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/explainer-serve.py:747)

`resolve_page()` checks for `.` before URL-decoding. Measured:

```text
root contains: secret.env.html
resolve_page('/secret%2eenv', root) -> /.../secret.env.html
```

So the rule “the fallback is not a second chance” is bypassed by encoding the dot. The existing case covers `/secret.env`, not `/secret%2eenv`.

Falsifier: show that encoded path segments are intentionally classified using their raw, pre-decoded spelling, or add a case where `/secret%2eenv` returns `None`.

**Medium — `/src/` source viewer renders the relative path as raw HTML**
[explainer-serve.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/explainer-serve.py:643), [explainer-serve.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/explainer-serve.py:679)

`source_shell()` escapes file contents, but interpolates `rel` directly into `<title>` and `<header><b>`. The `/src/` handler passes a filesystem-derived relative path straight in at [explainer-serve.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/explainer-serve.py:1158).

Measured:

```text
safe_path_allows_special_name True
raw_img_in_html True
<title>evil<img src=x onerror=alert(1)>.md</title>
<header><b>evil<img src=x onerror=alert(1)>.md</b>...
```

Falsifier: prove filenames under `/src/` cannot contain HTML-significant characters, or escape `rel` and add a case with a slash-free payload filename.

**Other Checks**

The recorded gate matches locally:

```text
OK — delivered scripts mutated: 46 file(s), 685 mutation(s), 685 killed,
685 attributed to the case each names, 0 survivor(s)
```

Also green: `explainer-serve.py --self-test` in all three HOME shapes, `check-plan-code.py --self-test`, `check-ratchet-contract.py --self-test`, `check-fixture-variation.py`, `check-selftest-counts.py`, and `check-docs.py`.

I did not find a dishonest manifest entry in the 42-entry attribution sense; the full mutate run attributed all 685 entries exactly. I did find that several test-driver restore deletions still pass, but current code uses `finally` and I did not see an actual leak in the checked-in tree.
