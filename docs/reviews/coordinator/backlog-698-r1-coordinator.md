# Round 1 — `backlog-698` — coordinator — the renderer is right; word boundaries and renderer liveness are not

```yaml
round: 1
fixes_nontrivial: true
subject: backlog-698
halves:
  codex: ran
  claude: ran
findings:
  - {id: X1, severity: Major, aim: deliverable, fix_induced: false, component: corpus-views, disposition: accepted}
  - {id: X2, severity: Major, aim: deliverable, fix_induced: false, component: renderer-call, disposition: accepted}
  - {id: X3, severity: Minor, aim: deliverable, fix_induced: false, component: renderer-call, disposition: accepted}
  - {id: X4, severity: Minor, aim: deliverable, fix_induced: false, component: corpus-views, disposition: accepted}
  - {id: C1, severity: Major, aim: deliverable, fix_induced: false, component: corpus-views, disposition: accepted}
  - {id: C2, severity: Major, aim: deliverable, fix_induced: false, component: corpus-views, disposition: accepted}
  - {id: C3, severity: Minor, aim: deliverable, fix_induced: false, component: corpus-views, disposition: accepted}
  - {id: C4, severity: Minor, aim: deliverable, fix_induced: false, component: renderer-call, disposition: accepted}
  - {id: C5, severity: Nit, aim: deliverable, fix_induced: false, component: cannot-see-doc, disposition: accepted}
```

Both halves reviewed 0fb65173 (PR #620), concurrently:

- [`codex/backlog-698-r1-codex.md`](../codex/backlog-698-r1-codex.md): X1 and X2 MAJOR, X3 and X4 MINOR. NOT CONVERGED.
- [`claude/backlog-698-r1-claude.md`](../claude/backlog-698-r1-claude.md): C1 and C2 MAJOR, C3 and C4 MINOR, C5 NIT. NOT CONVERGED.

This is round 1, so no finding is fix-induced.

**What held.** Both halves confirmed these:

- the real build passes `--check`;
- the self-test passes 41/41;
- in a full clone, the mutations die on their named cases (Claude ran all 34, Codex ran 6);
- the staging reaches the bundle;
- missing node, a missing bundle, a killed node and a timeout are all rc 2;
- the sweep re-price breaks no shard budget.

The CommonMark renderer choice stands.

## The class, before the dispositions

X1, C1 and C2 are one defect in three forms. **The views decide where word boundaries fall, and each guess can be wrong in one direction:**

- an image in a word gets spaces it should not (X1);
- an invisible format character becomes a break (C1);
- a block tag missing from a hand list gets no break (C2).

Extending the hand lists will not close this; it is the regex-model failure this row exists to end. **Fix it structurally:** for every boundary the renderer cannot settle, cover BOTH readings with add-only views:

- **tight:** delete Unicode Cf characters; an image's alt text and every inline tag boundary JOIN the text around them;
- **loose:** every tag boundary and every image SEPARATES words.

A six-word run in either view is a hit. The fold states the rule in *What this cannot see*: "a boundary is read both ways". It also checks that the existing adjacent negatives still pass, because a tight view that joins too much would over-refuse.

## Dispositions

- **X1 (MAJOR) + C1 (MAJOR) + C2 (MAJOR): word boundaries. ACCEPT.** Fix with the both-readings rule above, not with more list entries. The cases:
  - Codex's `ne![ver](x.png)`;
  - Claude's 5 Cf spellings: `&shy;`, U+00AD, `&#8203;`, U+200D, `&#x2060;`;
  - Claude's 2 unlisted block tags.

  Each case goes red on 0fb65173 first. Add matching disguises to the plant corpus, and add a mutation per new clause.
- **X2 (MAJOR): a renderer that returns well-shaped but wrong output passes. ACCEPT.** Shape checks cannot prove the renderer worked. **Fix:** every renderer call carries a KNOWN PROBE, a fixed Markdown snippet whose rendered text is pinned, and the run is CANNOT RUN (rc 2) unless the probe comes back exactly. Non-empty stderr from node is also rc 2. Add Codex's substitute-node cases (an empty document; plausible strings with stderr noise) as self-test cases.
- **X3 (MINOR) = C4 (MINOR): non-UTF-8 output crashes. ACCEPT.** Pass `encoding="utf-8"` instead of locale `text=True`, and catch decode errors as CANNOT RUN rc 2.
- **X4 (MINOR): the source quote's plain view was dropped, a loosening. ACCEPT.** Restore it as an additional, add-only source-fragment view, so master's refusal of Codex's case returns.
- **C3 (MINOR): text a browser never shows breaks a run.** That is text inside `<style>`, `<script>`, `<template>` or a `hidden` element. ACCEPT: add an add-only view that drops that text. The loose view can carry it.
- **C5 (NIT): look-alike letters pass. ACCEPT.** Name homoglyphs in *What this cannot see*.

## Round topology

Round 2 alternates to one half. The round cap applies: from round 4, findings are FILED unless a BLOCKER.
