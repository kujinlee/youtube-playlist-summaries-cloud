---
name: scoped-mutation-run-in-four-seconds
description: "FIRES-WHEN: I need to know whether a FEW new mutation entries are killed, and the full `--mutate .` sweep is too slow — ⭐ 8 shards in parallel on a laptop TIMES OUT and reports NOT MEASURED (suites are internally multi-core); a pruned COPY of HARNESS_TREE runs one manifest in 4s. ⚠ And `--shard n/N` does NOT isolate a file: shard_slice is round-robin"
metadata: 
  node_type: memory
  type: project
  originSessionId: cacb274e-95ca-4cc6-b810-ebd8b4fe9634
  modified: 2026-10-07T09:38:38.865Z
---

**Measured 2026-10-06/07, PR #364.** Two ways to run the mutation harness locally, one of which
cannot work on a 12-core laptop.

## ⛔ 8 shards in parallel LOCALLY is a CANNOT RUN, not a slow pass

`SUITE_TIMEOUT = 120` in `check-plan-code.py`. Ran `--mutate . --shard0 i/8` × 8 concurrently;
**6 of 8 shards reported `NOT MEASURED`** because `check-rc-contract.py --self-test` blew the cap
during the *control* pass. Measured alone it is **29.3s wall but 154s of CPU** (user 92 + sys 62) —
it spawns subprocesses, so it wants ~5.3 cores by itself. 8 × that on 12 cores is a ~3.5× stretch.
CI gives each shard its own runner; a laptop does not. **Treat the whole run as NOT RUN** — that is
what it says, and it is right.

## ⚠ `--shard n/N` CANNOT scope to one file

`shard_slice` is `muts[index - 1::total]` — **round-robin, deliberately**, so one expensive file's
contiguous block spreads across all N (a contiguous split hands 183 entries to one shard and blows
the cap while siblings idle; that is what killed #365's first attempt). There is **no per-file
filter**. A handoff told me `--shard` would isolate a file; it does not.

## ✅ The scoped run: a pruned COPY, ~4 seconds

1. `rsync -a` the `HARNESS_TREE` paths into a temp tree. ⛔⛔ **DO NOT TRUST A COUNT HERE, AND THAT
   INCLUDES THIS ONE — DERIVE THE TUPLE WITH `ast` (2026-10-14).** This step said **six** and named
   them; the branch had **seven** (`.agents/skills` was added for the citation-link guard) and the
   run came back `CANNOT RUN`. ⚠ **And "read the tuple, do not guess" did not save me — I DID read
   it, with a line-bounded `grep` whose range stopped one entry short.** A grep over a multi-line
   literal is a guess wearing a measurement's clothes. What works:

       python3 -c "import ast;from pathlib import Path;
       [print(ast.literal_eval(n.value)) for n in ast.parse(Path('scripts/check-plan-code.py').read_text()).body
        if isinstance(n,ast.Assign) and any(getattr(t,'id','')=='HARNESS_TREE' for t in n.targets)]"

   ⭐ Miss one and the harness **refuses and names the missing path** — by design, so that a staged
   tree never degrades into a quieter, smaller one (it caught `.github/workflows` once and
   `.agents/skills` once). That refusal is the only reason a stale recipe costs 2 seconds instead of
   a wrong verdict.
2. In the COPY, delete every `scripts/mutations/*.json` but the one under test.
3. In the COPY, reduce `EXPECTED_MUTATIONS` to that single key (it checks **both** directions, so a
   missing manifest reads as drift).
4. `python3 scripts/check-plan-code.py --mutate .` inside the copy → **4.0s** for 16 entries.

**What this proves and does not.** Staging, `child_env`, subprocess spawn, `parse_fail_names` and
exact-`expect` attribution are all the real instrument — only the *input set* changed. It does NOT
re-prove the whole-manifest ratchet; **CI does that, and CI is also the browserless world**, so push
and let the sweep be authoritative. Both agreed on #364.

## ⭐ The harness is STRUCTURALLY browserless — not an environment you construct

`HARNESS_TREE` stages `node_modules/typescript` **only**, and `page-contrast-probe.mjs` does
`import { chromium } from 'playwright'`, so a staged tree dies at **`ERR_MODULE_NOT_FOUND`** before
any browser is looked for. I wasted effort building a `PLAYWRIGHT_BROWSERS_PATH=<empty>` world; the
harness never had a browser anyway. ⚠ Two environments, two different missing pieces: CI's `verify`
job has full `node_modules` and lacks the **browser**; the harness lacks the **package**. Do not
conflate them — see [[measure-the-population-the-code-actually-sees]].

## ⛔ A kill alone does not discriminate — build the NEGATIVE CONTROL

"16 killed" was true in both worlds and therefore proved nothing about the one I cared about. The
evidence that counted was the **pair**: pre-fix tree → `1 mutation, 0 killed, 1 SURVIVOR`; post-fix
→ `16 killed, 16 attributed`. Same harness, same tree, opposite verdicts.
See [[the-control-refuted-the-premise]], [[a-case-can-pass-for-an-ambient-reason]].
