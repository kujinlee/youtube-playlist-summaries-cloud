Reviewed head: 05c139280f6c5d95682185d9bec38a6e137655df

# Round 1 — dashboard-retire-s3 — Claude

Reviewed head: `05c13928` (branch `dashboard-retire-s3`, five commits on `origin/master` `829660eb`).
Copy: a `git clone --no-hardlinks` of the worktree at 05c13928 with origin/master fetched in. I used a clone rather than
`git archive` because the gates need history. I set the origin URL to the GitHub remote, because `check-page-links --build`
renders PR keys from it. node_modules is symlinked. I edited nothing in the worktree.

Stance: refute. Every finding below comes from an input I ran. The scanner probes were run through K8's own `_cats`
entry point (the scratchpad `probe.py` / `probe2.py`), and a result of `[]` means K8 reported nothing.

## Findings

### F1 — MAJOR — `scripts/check-retired-references.py` (`_python_findings`, `_hook_findings`): K8 cannot fail on several real load forms, and its docstring claims more than it checks

The docstring's line 1 says "nothing that RUNS still names a thing" that was retired. The plan's interface says K8 checks
"string constants that are call arguments". The implementation checks a call argument only when the callee is in
`LOADERS = {"with_name","_sibling","_load","spec_from_file_location"}`. It also skips any argv element that contains
whitespace, reads hooks only from the `command` strings in `.claude/settings.json`, and reads workflows only from `run:`
lines that a regex matches.

Each input below was placed in a world and scanned. Every one returned `[]`:

| # | Input that RUNS the retired thing | K8 |
|---|---|---|
| a | `subprocess.run("python3 scripts/gen-dashboard.py --self-test", shell=True)` | `[]` |
| b | `["bash","-c","python3 scripts/gen-dashboard.py --self-test"]` (skipped by the whitespace rule) | `[]` |
| c | a gate-table tuple `("dash","python3 scripts/check-dashboard-entry.py --base master")`. This is the shape `check-merge-ready`'s own gate table uses | `[]` |
| d | `Path("scripts/gen-dashboard.py")`, and `ROOT.joinpath("scripts","gen-dashboard.py")` | `[]` |
| e | an f-string argv element `f"{ROOT}/scripts/gen-dashboard.py"` | `[]` |
| f | a module constant `GEN = "scripts/gen-dashboard.py"`, and a dict value `{"dash": "scripts/gen-dashboard.py"}` | `[]` |
| g | `spec_from_file_location("gd", location="scripts/gen-dashboard.py")`: a LOADER, but with a keyword argument | `[]` |
| h | `REGENERABLE["dashboard"] = "x.py"`, and `REGENERABLE.update({"dashboard": ...})` | `[]` |
| i | a hook script `.claude/hooks/x.sh` whose body runs `python3 scripts/gen-dashboard.py`, registered in settings.json. **This is exactly how the deleted `regen-dashboard.sh` loaded the generator.** Repo hooks routinely do this, for example `.claude/hooks/agent-large-read.sh:10` | `[]` |
| j | a `package.json` script, and `.githooks/pre-push` running the generator | `[]` |
| k | a workflow flow-mapping step `- {name: x, run: python3 scripts/gen-dashboard.py}` | `[]` |
| l | JS hrefs `fetch('/dashboard')`, `"a.href = \"/dashboard\";"`, and a nav tuple `(("Dashboard","/dashboard"),…)` | `[]` |

For contrast, K8 does catch a single-quoted `location.href='/dashboard'` and a folded `run: >-` block. So the category
does exist, but it is narrower than its name.

The live tree is clean: a grep of the live `.sh`, `.json`, `.yml`, `.py` and `.ts` files shows only comment mentions. So
nothing is broken today, but K8 is weaker than the guard it claims to be. Row (i) matters most: K8 lets through the very
form the retired hook used.

Fix direction. Either (1) widen the scan: any string constant anywhere in a `.py` AST, the bodies of hook scripts reached
from settings, `.githooks/*`, package.json scripts, and the `run` key of a parsed workflow. Or (2) narrow the docstring and
the plan's interface to what is actually checked, and list the uncovered forms as a stated bound. Option (1) costs little
for this repo's size.

### F2 — MAJOR — `scripts/check-page-links.py:94,104`: removing `/dashboard#` from `HREF_LITERAL`/`HOME_PATHS` lost coverage that K8 does not replace

The new comment says "`/dashboard` left both — the page is retired; K8 … refuses a literal href to it". Rule 2 of
check-page-links caught a *built* href: concatenation, `%` and `.format`. K8 sees only whole literals. I ran both checks
on the same inputs:

| Input | `check-page-links.built_hrefs` on master | on HEAD | K8 on HEAD |
|---|---|---|---|
| `return "/dashboard" + "#" + slug` | `['x.py:2: /dashboard#']` | `[]` | `[]` |
| `h = "/dashboard#%s" % slug` | `['x.py:1: /dashboard#']` | `[]` | `[]` |
| `h = "/dashboard#{}".format(slug)` | (same family) | `[]` | `[]` |

A built link to the retired page passed check-page-links on master and passes it on HEAD. Before S3 that link was
refused because it bypassed the one link function. After S3, nothing refuses it. The comment's claim that K8 covers this
is false for the built forms. This is a guard loosened by the PR, so I rated it MAJOR rather than MINOR. Any of three fixes
works:
- keep `/dashboard` in `HOME_PATHS` as a retired path, so that any built href to it is refused;
- have K8 call `check-page-links.built_hrefs` for the retired paths;
- correct the comment and file the gap.

### F3 — MINOR — `docs/backlog.md:681` (row 736): not updated, though plan Task 16 lists "docs/backlog.md (this work's row closed)"

The row's status still reads "🏗 **S1 BUILT 2026-11-25** (S2, S3 to go)". Its file list still names
`scripts/check-dashboard-entry.py` and `scripts/gen-dashboard.py`, which this PR deletes. The roadmap
(`docs/roadmap-to-launch.md:1428–1435`) was updated to "S3 built", so the two now disagree. Row 739 is correctly closed as
MOOT, and row 730 (✅) reads as history, which is fine.

### F4 — NIT — stale prose describing the deleted generator as a live consumer

- `scripts/check-ask-store.py:189`: `exemption_reason` "ONE DEFINITION, shared with scripts/gen-dashboard.py, so the page
  displays exactly the exemptions the gate granted".
- `scripts/check-merge-ready.py:702`: "declared 'ONE DEFINITION, shared with gen-dashboard.py'". The function is still
  named `_dashboard_gate`.
- `scripts/check-theme-token-coverage.py:16,32–35`: the problem statement still says `gen-dashboard.py:1290 LINK_SURFACES`
  and `scheme_palettes()`. A note at the top marks this as history, which I accept, but line 16 still reads in the present
  tense.
- `docs/explainers/_restyle.py:11,23`: `GENERATED = ("dashboard", …)` and the docstring "SKIPS THE GENERATED PAGES
  (dashboard, …)". This is a live tool (`_explainer-style.css:2` tells you to run it). It is harmless, because skipping a
  page that no longer exists does nothing. K8 does not see it, because the tuple is not a page table.

## Verified clean (attempted refutations that failed)

- **Staying ask-store behaviour.** I diffed the case lists of origin/master (139 self-test + 56 cannot-run) against HEAD
  (115 + 26).
  - Every case removed is a grammar, cutover (12.8, 12.9, 12.12–12.16) or `730`/post_cutover case.
  - Every staying L1/A1/F1 case is present and unweakened: 12.1–12.7, 12.10, 12.11, r1 F1 and r1 F4.
  - One case was added at line 1350: "S3: an ask git cannot read is CANNOT RUN rc 2, never A1 ok". I hand-applied the
    "unreadable ask object reads as an empty ask" mutation, and that case FAILs.
- **The departure: deleting post_cutover was right.**
  - Task 13 had already run the cutover on master, so the only reason to keep the code was a one-shot check that had
    already been spent.
  - Keeping it would have left `store_edit_prs`, a `gh` runner, dangling after Task 16.
  - Row 739 is closed as MOOT with that reason, the roadmap is updated, and plan Task 16 is annotated. The S2 tasks
    describe Task 12 as built, which is history and fine.
  - The one stale description is row 736 (F3).
- **The theme check's new subject is real.**
  - `PAGE_SRC` is `goal-tree.py`, and `css_block_tokens` reads its `:root[data-theme="light"]` block.
  - I deleted `--structure-bg` from that block in the copy, and the check reported
    `✗ --structure-bg: declared by the OS-dark shim, never overridden by the light palette`. So the check fires.
  - I put a space before `{` and the block still parses: 14 light tokens.
  - The added `--structure-br:#33607a;--structure-bg:#eaf0f4` values match the old dashboard's light values.
- **The `/dashboard` → archive route.** `RETIRED_FILES` in explainer-serve sends it to the archive, and explainer-serve's
  self-test passes 301/301, including the `retired_target` cases.
- **The contrast formula moved to page_chrome.**
  - `_luminance` and `contrast_ratio` gained 7 cases.
  - `brief-compose._contrast` now calls `page_chrome.contrast_ratio`, and a stub case patches it to 0.5, which proves the
    call site is used.
  - I hand-applied all 3 new page_chrome mutations, and each made its named case FAIL.
- **Mutations: counts equal their pins.**

  | Manifest | Count = pin |
  |---|---|
  | check-ask-store | 54 |
  | check-retired-references | 10 |
  | page_chrome | 117 |
  | check-merge-ready | 212 |
  | check-publishability | 232 |
  | check-theme-token-coverage | 4 |

  - The all-manifest anchor resolve found 0 unbound entries.
  - `check-plan-code.py --mutate . --only scripts/check-retired-references.py` killed 10 of 10, each by the case it names.
  - The plan's figures (45 after S3, a scanner pin of 9) differ from the actual 54 and 10. The plan's Task 16 Step 2 note
    and the comments in `expected_mutations.py` account for the difference. That is not a finding.
- **Edge counts and fixtures.**
  - The `check-shipping-sets` edge pin (361 / `6e70bc13894e54c2`) carries a written derivation. The `six` fixture now
    uses `compaction-state` → `check-ask-store`, which is a live load.
  - The `check-fixture-variation` entries for the deleted generator were removed, and the new `scan.root` entry was added.
  - check-merge-ready's C1 replay was removed together with ci.yml's C1 command, and the replay case now expects 1
    command.

## Gate lines (run in the copy at 05c13928)

| Command | rc | Last line |
|---|---|---|
| `python3 scripts/check-ask-store.py --self-test` | 0 | `115/115 passed` / `26/26 cannot-run cases passed` |
| `python3 scripts/check-retired-references.py --self-test` | 0 | `31/31 passed` |
| `python3 scripts/check-retired-references.py` | 0 | `check-retired-references: ok — no load, path, argv, page-table, link, hook, workflow or manifest names a retired thing` |
| `python3 scripts/check-merge-ready.py --self-test` | 0 | `463/463 self-test cases passed` |
| `python3 scripts/check-plan-code.py --self-test` | 0 | `506/506 passed` |
| `python3 scripts/check-docs.py` | 0 | `Documentation integrity OK` |

These other self-tests also passed, all with rc 0:

| Check | Result |
|---|---|
| `page_markup` | 204/204 |
| `check-page-links` | 96/96 |
| `check-fixture-variation` | 67/67 |
| `check-publishability` | 177/177 |
| `check-review-decision` | 130/130 |
| `check-ratchet-contract` | OK |
| `explainer-serve` | 301/301 |
| `regen-pages` | 123/123 |
| `goal-tree` | 606/606 |
| theme check, self-test | 14/14 |
| theme check, live run | 11 shim / 14 light / 0 KNOWN_GAP |
| `check-page-links --build --ci` | rc 0, with the GitHub remote set |

I did not examine `check-shipping-sets --self-test` (it ran in the background past 120 s), so treat it as NOT RUN by me.

VERDICT: NOT CONVERGED
