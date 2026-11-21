Reviewed head: 7f54a324b20ed034ba2f9bb9c079cbbf4021dd5b

# Marketplace Task 16, round 4 (Claude half): refuting §4.1 of the install-root mention walk

Scope: `git diff b79d4bad..7f54a324`, briefed to REFUTE the invariant of
`docs/reviews/architecture-review-2026-11-21-publishability-install-root.md` §4.1.

Method: I copied `scripts/` at HEAD and at b79d4bad (the pre-build tree, extracted with `git archive`) into a
scratchpad outside the repository. Each input below is a file that a harness parses and passes to
`_install_root_uses(tree, parent, depth=2, held=lambda t: False)`, so it sits at the position of
`scripts/x.py`. Every output quoted below was observed from that run; none is inferred.
The harness and cases are at
`/Users/kujinlee/.claude-tmp/claude-501/-Users-kujinlee-code-agentic-ai-docs-youtube-playlist-summaries-cloud/b387c8e6-9003-42f5-a944-1d4eb1de0c9b/scratchpad/t16r4c/`
(`h.py`, `cases/`).

## Findings

### BLOCKER B1: an unfollowed name bound BELOW the install depth goes silent (caused by the build; regression)

`scripts/check-publishability.py:819-826` (the binding report) together with `:811` (the level filter in
`report`).

§4.1 says a BIND whose name is not followed "is reported at the binding". The build does report it, but at the
binding's own value, and `report` drops any value whose level is not `depth`. When the unfollowed name holds an
INTERMEDIATE directory (level 1, the script's own directory) and the install root is built from it later
(`REPO = SCRIPT_DIR.parent`), the binding is dropped by the level test. The name is not followed, so
`REPO`'s assignment is never walked and never BINDs, and the later `cwd=REPO` is not a mention. Nothing is reported.

```python
# c25: the intermediate name is rebound in a function
import subprocess, os
from pathlib import Path
SCRIPT_DIR = Path(__file__).resolve().parent
REPO = SCRIPT_DIR.parent
def main(argv):
    SCRIPT_DIR = Path(argv[0]).parent
    subprocess.run(["git", "status"], cwd=REPO)
```
HEAD: `[]`. b79d4bad: `[(7, '.')]`.

```python
# c26: the intermediate name reused as a parameter (a common `def f(x=X)` idiom)
SCRIPT_DIR = Path(__file__).resolve().parent
REPO = SCRIPT_DIR.parent
def load(SCRIPT_DIR=SCRIPT_DIR):
    return SCRIPT_DIR
subprocess.run(["git", "status"], cwd=REPO)
```
HEAD: `[]`. b79d4bad: `[(7, '.')]`.

```python
# c05: the same, with HERE as a parameter
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
def helper(HERE):
    return HERE
subprocess.run(["git", "status"], cwd=ROOT)
```
HEAD: `[]`. b79d4bad: `[(7, '.')]`.

Control c27 is the same program with no reuse of `SCRIPT_DIR`. HEAD: `[(5, '.')]`. The silence therefore comes
from the reuse alone.

Why this is observation 3 of §5 and not a precision point: the handed-on value (`REPO`, at `cwd=`) IS at the
install depth. The level test of §4.1 is meant to judge the value that is handed on. Here it judges an
intermediate binding the rule stopped following. The documented bound, "its root is reported AT THE BINDING, as
`.` … coarser, never silent" (`docs/marketplace/experiment-tier-a.md:219-221`, and the
`_install_root_uses` docstring), holds only when the unfollowed binding is itself at the install depth. Under
§6 this stops the fold on this rule and goes to the owner.

### MAJOR M1: the same mechanism with a climbing rebinding (refutes §4.1; also silent before the build)

Same lines, `:797-799` (the "rebinding from itself" verification accepts only a value-preserving rebinding).

```python
# c04
root = os.path.dirname(os.path.abspath(__file__))
root = os.path.dirname(root)
subprocess.run(["git", "status"], cwd=root)
```
```python
# c06
p = Path(__file__).resolve()
for _ in range(2):
    p = p.parent
subprocess.run(["git", "status"], cwd=p)
```
```python
# c11: a for-target reusing the intermediate name
HERE = Path(__file__).parent
for HERE in []:
    pass
ROOT = HERE / ".."
subprocess.run(["git", "status"], cwd=ROOT)
```
HEAD: `[]` for all three. b79d4bad: `[]` for all three. These are not caused by the build, but they are silent
hand-ons that §4.1 says cannot exist. The unfollowed name is reported at its first binding at level 0 or 1, and
the level test drops it.

### MAJOR M2: an unrecognised derivation stops the walk below the install depth, and the USE is dropped (also silent before the build)

`:663-681` (`_role` returns USE for an unknown callee) together with `:817-818` (the USE is reported at the value
the walk had reached so far) and `:811`.

When the climb goes through a callee or a part the table does not know, the walk stops at USE with the value it
had reached at that point (level 0 or 1). The level test then drops it, and the name it was bound to is never
followed.

| case | input (then `subprocess.run([...], cwd=ROOT)`) | HEAD | b79d4bad |
|---|---|---|---|
| c01 | `from os.path import dirname, abspath`; `ROOT = dirname(dirname(abspath(__file__)))` | `[]` | `[]` |
| c02 | `import os.path as osp`; `ROOT = osp.dirname(osp.dirname(osp.abspath(__file__)))` | `[]` | `[]` |
| c03 | `ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))` | `[]` | `[]` |
| c07 | `ROOT = os.path.split(os.path.split(os.path.abspath(__file__))[0])[0]` | `[]` | `[]` |
| c10 | `from pathlib import Path as P`; `ROOT = P(__file__).resolve().parents[1]` | `[]` | `[]` |

`os.pardir` (c03) and `from os.path import dirname` (c01) are common idioms. USE is the default, so the default
does not protect these: a USE below the install depth is a silent exit. The closed list of §4.1 counts it under
"a level that is not the install depth", but the level here is wrong because the walk stopped early. One
direction that would close M1, M2 and B1 together is to report a USE or an unfollowed BIND whose level is BELOW
the install depth as an "unjudged" finding instead of dropping it. That changes the rule, so it is a decision
for the owner, not something to fold.

### MINOR m1: a root exported to an importer is silenced by any inert read in its own file (spec-conformant)

`:821-823` (`quiet` needs only one load outside the binding's own value).

```python
# c08 (paths.py; another module does `from paths import ROOT; subprocess.run(..., cwd=ROOT)`)
ROOT = Path(__file__).resolve().parents[1]
if __name__ == "__main__":
    print(ROOT)
```
HEAD: `[]`. c09 (`assert ROOT.is_dir()` in place of the print): `[]`. Control c24 (no read): `[(2, '.')]`.

§4.3 item 4 defines an exported root as "no load in the file". A load that is INERT still counts as a load, so
the export goes unreported, and the importing file has no `__file__` for the rule to see. b79d4bad was silent on
all three, so the build is an improvement here.

## Breadth checks that held (each reported; no finding)

All of these reported at HEAD and at b79d4bad: `self.root = ROOT` then `cwd=self.root` `[(6,'.')]`;
`functools.partial(subprocess.run, cwd=ROOT)` `[(4,'.')]`; `PurePath(ROOT)` `[(4,'.')]`;
`os.path.normpath(ROOT)` `[(3,'.')]`; `glob.glob(ROOT + "/docs/*.md")` and
`shutil.copytree(os.path.join(ROOT, "docs"), …)` `[(3,'.'),(4,'docs')]`; `"cd %s" % ROOT` and
`"{}".format(ROOT)` `[(3,'.')]`; `**{"cwd": ROOT}` `[(3,'.')]`; `os.chdir(*[ROOT])` `[(3,'.')]`; an
`@lru_cache` function returning the root `[(4,'.')]`; a root bound and used inside `if __name__ == "__main__":`
`[(4,'.')]`; `os.environ["PROJECT"] = …` `[(2,'.')]`; `os.chdir(ROOT if os.path.isdir(ROOT) else ".")`
`[(3,'.')]`.

## Build against the spec

- §4.2: `_from_file`, `_fstring_path`, `_inert`, `_rebinds` and `INERT_CALLS` are gone (grep). `_Scopes` and
  `_Bound` remain, and only detector 6 uses them (`:1131-1134`). OK.
- §4.4 L5 is rewritten as the spec asked (`experiment-tier-a.md:214-225`), and `check-surface-recall:519` is added.
  Its sentence "coarser, never silent" is refuted by B1 and M1.
- The backlog row 691 for r3 m1 is filed against `_Scopes`. OK.
- Self-test: `174/174 self-test cases passed`, rc 0. The docstring on line 5 says `# 174 cases`. They match.
- Mutations: I applied three on a scratch copy. Each made the self-test exit rc 1 on the case it names:
  "detector 2 report: an unfollowed binding is silent", "detector 2 role: relpath against ANY start is inert", and
  "detector 2 walk: a comparison hands the root on". No mutation and no case covers B1, because no case
  has an unfollowed binding below the install depth.
- The scan record: a fresh `--out` scan, compared with `docs/marketplace/scan-2026-11-21.json` with `measured_at`
  removed from both, is EQUAL. 46 components were scanned, 0 CANNOT RUN. Install-root findings went from 56 to 58
  against the b79d4bad record. No named target was lost: the changes are same-target line shifts, plus the new
  `check-plan-code:6355 .` and `check-surface-recall:519`.

VERDICT: NOT CONVERGED
