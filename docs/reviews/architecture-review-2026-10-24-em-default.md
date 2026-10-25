# Architecture review — a shared default for a page-local colour (backlog #226 part c)

> **Anchor:** `explanation-on-demand`

**Armed by THRASHING** (`docs/dev-process.md` Phase 6): on `typography-contract`, component `em-dark-state` carried
findings caused by a fold in round 2 (Codex M1, from r1's fold) and round 3 (Claude M1, from r1's fold, kept by r2).
Convened by the coordinator at `bd9e2cb3` while the owner was away — the decision record for a retreat, every
number below produced in Chromium by one of the three round documents or re-measured here.

## The question

Three committed role-using pages declare no `--em`, so they inherit `brief-compose.py`'s shim value — the LIGHT one
with the OS dark and nothing pressed. Bold text measured **1.78 / 1.79 / 1.78 :1** there (min over every `b`/`strong`,
re-measured on `origin/master`). **Can the shim supply a correct dark `--em` for every page?**

## What three rounds measured

| Attempt | Broke |
|---|---|
| r1: `:root:not([data-theme="light"])` (0,2,0) in the OS-dark media query | r2 Codex: ties a fragment's own OS-dark rule and wins by order — a deliberate dark `--em` 5.74 → 2.86:1 |
| r2: `html:where(:not(…))` (0,0,1), pressed pair lowered to `html[data-theme]` | r3 Claude: a fragment with theme palettes but NO OS-dark block stays light under OS dark, and gets dark `--em` — 1.92:1 |
| r3 reviewer's probe: a `color-mix()` default from the page's own colours | r3 Claude: 1.16:1 on another fixture, through the `--fg` cycle (backlog #351) |

## Finding

**Whether a page is dark in a given state is a fact about that page's palette, which the shim cannot see.** Every
central default guesses, and each guess has a page that contradicts it. `page_chrome.py` already says this, as
its central decision: *mechanism shared, palette local*. The shim's `--em` was a breach of that rule, and the
fixes deepened it.

## Decision

- **SPLIT.** The shim is restored to `master`. The three pages get the family pair in their OWN palette blocks
  (`#2d4a7c` light, `#9db8e8` dark — the owner's 2026-10-05 choice): 7.79–7.98:1 in all six states.
- **The contract says so** (`explainer-delivery.md` §2): a page that opts in declares `--em` in every palette block.
- **Filed, not folded:** a compose-time REFUSAL when the composer would add a live control to a fragment that
  leaves `--em` undeclared in any palette block it has — the r3 reviewer's recommended guard, and part (c)'s
  remaining work on backlog #226. And backlog #351, the `--fg` cycle.
- **Not done:** the lowered pressed pair (r2's second change) is reverted with the rest. r3 measured it did not
  reopen the half-live toggle, but it changes precedence for every page and belongs with the guard, not here.
