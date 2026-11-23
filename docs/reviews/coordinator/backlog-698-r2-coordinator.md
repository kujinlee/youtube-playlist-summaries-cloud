# Round 2 — `backlog-698` — coordinator — one decision per run cannot cover a boundary per word; read letters, not words

```yaml
round: 2
fixes_nontrivial: true
subject: backlog-698
halves:
  codex: ran
  claude: "GAP: alternation"
findings:
  - {id: X1, severity: Major, aim: deliverable, fix_induced: false, component: corpus-views, disposition: accepted}
  - {id: X2, severity: Major, aim: deliverable, fix_induced: false, component: corpus-views, disposition: accepted}
  - {id: X3, severity: Minor, aim: deliverable, fix_induced: true, component: renderer-call, disposition: accepted}
  - {id: X4, severity: Minor, aim: deliverable, fix_induced: false, component: corpus-views, disposition: accepted}
```

The Codex half reviewed 5745b83f, the round-1 fold (`git diff 49bae7e2..HEAD`): [`codex/backlog-698-r2-codex.md`](../codex/backlog-698-r2-codex.md). Verdict NOT CONVERGED.

REVIEW GAP: claude — alternation

**What held:**

- the real build passes `--check`;
- the self-test passes 51/51;
- in a full external clone, six new mutations each die on the case they name;
- the 38-shard estimates are 978–995 s, under the 1800 s budget;
- the canonical-source prefix keeps its trailing slash, so it does not admit `markdown-it-extra`;
- the probe catches ordinary renderer failures, non-UTF-8 output included.

Codex judges a substitute node that answers only the probe correctly to be a limit of any liveness check, not a defect. It goes under *What this cannot see*.

## The class, again, and why the round-1 fix could not close it

Round 1 read every boundary one way per view: all joined (tight) or all split (loose). X1 mixes the two in one run: `ne<em>v</em>er` must join while `er<center>pay` must split. Neither global reading sees it. Covering every combination per boundary is exponential, so more views will not close it either.

**The structural fix is a view in which boundaries do not exist.** Reduce both the rendered text and each six-word quote run to their letters and digits:

1. casefold;
2. delete Cf characters, whitespace and punctuation;
3. search the run as a SUBSTRING of the text.

That view covers every combination of joins and splits at once.

**Over-refusal bound.** A six-word run reduces to roughly 25 or more letters. A substring match across unrelated words that long is not a realistic false positive. The fold MEASURES this on the real build (180 files) and on the adjacent negatives, rather than asserting it. If a short run (for example under 20 letters) refuses a benign line, the minimum letter length is a stated threshold with its measurement.

The existing views stay, because they are add-only.

## Dispositions

- **X1 (MAJOR): mixed boundaries in one run pass. ACCEPT; fix with the letters-only view above.**
  - Cases: Codex's `I [almost](https://x) ne<em>v</em>er<center>pay attention to`, plus a format character beside an inline tag (Codex's second probe).
  - Each case goes red on 5745b83f first. Add a plant-corpus disguise that mixes boundaries, and a mutation per new clause.
- **X2 (MAJOR): master's link-reduced view was dropped, a loosening. ACCEPT.**
  - Restore master's link-reduced reading, link destinations and titles removed, as add-only views on BOTH sides: the source quote and the output.
  - Cases: Codex's `[I](https://x) [almost](https://x) never [pay](extra words) attention to`, which must refuse as master does, and its source-quote twin.
  - The fold checks the six LOOSENING-CHECK lines that name this, and says in its report that each now reads "not a loosening".
- **X3 (MINOR, fix-induced): whitespace-only stderr is accepted. ACCEPT.** Test `r.stderr` itself, not `.strip()`, and add a whitespace-only case.
- **X4 (MINOR): a closed `<details>` body can split a visible run. ACCEPT.** In the hidden-text view, drop a closed `<details>` element's body and keep its `<summary>`. An `open` attribute keeps the body. Add a case.
- **The substitute-node limit:** add one line to *What this cannot see*: a renderer built to answer the probe correctly and nothing else defeats the probe.

## Thrashing watch

X3 is fix-induced, in `renderer-call`. X1, X2 and X4 are not fix-induced: they were present on 0fb65173. **If round 3 carries a fix-induced finding in `renderer-call`, that is two consecutive rounds, and Phase 6 arms.** Round 3 alternates to the Claude half, and the round cap applies from round 4.
