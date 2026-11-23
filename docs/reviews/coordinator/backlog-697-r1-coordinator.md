# Round 1 — `backlog-697` — coordinator — the declaration holds the Fails-if; the guard must read CONTENT, not bytes

```yaml
round: 1
fixes_nontrivial: true
subject: backlog-697
halves:
  codex: ran
  claude: ran
findings:
  - {id: X1, severity: Minor, aim: deliverable, fix_induced: false, component: corpus-declaration, disposition: accepted}
  - {id: X2, severity: Major, aim: deliverable, fix_induced: false, component: closure-guard, disposition: accepted}
  - {id: X3, severity: Minor, aim: deliverable, fix_induced: false, component: docs, disposition: accepted}
  - {id: M1, severity: Minor, aim: deliverable, fix_induced: false, component: corpus-declaration, disposition: accepted}
  - {id: M2, severity: Minor, aim: deliverable, fix_induced: false, component: closure-guard, disposition: accepted}
  - {id: M3, severity: Minor, aim: deliverable, fix_induced: false, component: mutations, disposition: accepted}
  - {id: N1, severity: Nit, aim: deliverable, fix_induced: false, component: docs, disposition: accepted}
```

Both halves reviewed aac34e33.
- Codex: [`codex/backlog-697-r1-codex.md`](../codex/backlog-697-r1-codex.md). Verdict NOT CONVERGED, with 2 MAJOR and 1 MINOR.
- Claude: [`claude/backlog-697-r1-claude.md`](../claude/backlog-697-r1-claude.md). Verdict CONVERGED, with 3 MINOR and 1 NIT.

**What held:** both halves confirm row 697's **Fails if** at aac34e33.
- No group A–C file ships.
- No raw group-D file ships.
- The 179 declared files equal `build-shipped-corpus.py --out` byte for byte, except `MEMORY.md`.

## Where the halves disagree — X1 (Codex MAJOR) vs M1 (Claude MINOR): the index and the layout

I traced this myself, and the finding has two parts.

**The layout part is not this PR's.** `scripts/mkt_stage.py` `plan()` lands every `files` entry at its own repo-relative path (`add(real, rel)`), and it has no destination mapping.
- No declaration can put the paraphrases in `~/.claude/projects/<slug>/memory`, which is where `recall-llm.py` reads. A plugin cannot install there at all.
- That is the recall package's portability gap, already recorded in the inventory. Codex says the same: "this does not establish a new complete recall failure".

**The index part is real but small.**
- `recall-llm.py` excludes `MEMORY.md` from matching.
- The builder's filtered index links no excluded file. So the dashboard's reason for dropping it is wrong, which is M1.

**Disposition:** downgraded to MINOR and accepted as a recorded decision plus a filed row.
- Correct the stated reason in the component notes and the dashboard entry.
- File a backlog row: "the recall package ships no filtered index, and its install layout does not reach recall-llm's memory directory", with Task 21 as its trigger.
- The owner sees that row at Task 21, which is their stop anyway.
- Building a committed copy of the corpus here would duplicate 173 files that go stale on every memory edit. That is a dev-speed cost I will not buy without the owner.

## Dispositions

- **X2 (MAJOR): a raw group-D file with one added frontmatter line passes `--closure` with 0 gaps. ACCEPT.**
  - The cause: `_canon_sha` folds only line endings and trailing whitespace, so it compares bytes, not the property.
  - The property is decision 5's: no group-D quote ships unparaphrased.
  - Fix: `--closure` runs the builder's OWN quote check over the files the recall package ships. Copy them flat by basename into a scratch dir and call `build-shipped-corpus.py --check DIR` as a subprocess. That is one rule in one place, through the script's CLI, which PR #620 keeps stable, and never its internals.
  - A nonzero rc or unreadable output from that call means CANNOT RUN, never `0 gaps`.
  - Case: X2's constructed input (a D source plus one frontmatter line), red on aac34e33 first, plus the adjacent paraphrase that passes.
- **X3 (MINOR):** the `inventory.json` recall row (~line 514) still says 196 raw files and that backlog #697 is to come. ACCEPT: rewrite it to the new declaration, keeping the separate portability and content-review status.
- **M2 (MINOR):** if `groups` or `_canon_sha` moves, or the builder is removed, `--closure` raises a traceback (rc 1) instead of CANNOT RUN (rc 2). ACCEPT. PR #620 is rewriting that file now.
  - Move the load inside the `try`, and catch `ImportError`/`AttributeError`/`OSError`.
  - Add a case with a builder stub missing a name.
- **M3 (MINOR):** a mutation replacing `_canon_sha` with `_sha` at the `decision5_gaps` call sites survives. ACCEPT: add a case shipping a CRLF and trailing-whitespace copy of an A–C source, plus that mutation.
- **N1 (NIT):** the dashboard entry says "140 -> 148", but the suite prints 149. ACCEPT: derive the count from the run.

Round 2 alternates to ONE half. Codex runs it, because it reported the MAJOR (`review-method.md` → *Round topology*).

REVIEW GAP: claude — alternation (round 2)
