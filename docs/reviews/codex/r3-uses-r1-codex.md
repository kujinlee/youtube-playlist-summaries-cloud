<!-- codex-review: model=gpt-5.5 -->

## HIGH

### H1 · `import_re` counts multiline string contents as real imports

`scripts/check-ratchet-contract.py:159`

> `_LINE_START = r"^"        # excludes `# import x` and an import inside a string literal`

Reproduction:

```bash
python3 - <<'PY'
import importlib.util, sys
from pathlib import Path
p = Path("scripts/check-ratchet-contract.py")
spec = importlib.util.spec_from_file_location("crc", p)
m = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = m
spec.loader.exec_module(m)

blob = 'fixture = """\nimport lib\n"""\n'
print([v.rule for v in m.check_caller("scripts/lib.py", '"""x --self-test"""\n', blob)])
PY
```

Observed: `[]`.

That is a false green: there is no import in the Python program, only a line inside a triple-quoted string. The anchor excludes inline string literals like `X = "import lib\n"`, but it does not exclude multiline string bodies whose contents begin at column 0. This directly falsifies the comment’s claim and gives an unused self-tested library a way to satisfy R3 through a fixture/prose blob in another caller source.

What would prove this wrong: the reproduction above returning `['R3_no_caller']`, or an implementation that parses Python caller sources and ignores `ast.Constant` string bodies while still accepting real indented imports.

## MEDIUM

### M1 · `import_re` misses valid `import` forms, so real users can be forced into fake `NO-CALLER` debt

`scripts/check-ratchet-contract.py:200`

> `+ rf"(?:import[ \t]+{re.escape(stem)}|from[ \t]+{re.escape(stem)}[ \t]+import)\b",`

Reproduction:

```bash
python3 - <<'PY'
import importlib.util, sys
from pathlib import Path
p = Path("scripts/check-ratchet-contract.py")
spec = importlib.util.spec_from_file_location("crc", p)
m = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = m
spec.loader.exec_module(m)

for blob in ["import os, lib\n", "from . import lib\n", "from scripts import lib\n"]:
    print(blob.strip(), "=>",
          [v.rule for v in m.check_caller("scripts/lib.py", '"""x --self-test"""\n', blob)])
PY
```

Observed:

```text
import os, lib => ['R3_no_caller']
from . import lib => ['R3_no_caller']
from scripts import lib => ['R3_no_caller']
```

At least `import os, lib` is plain valid Python and imports `lib`; the regex only accepts the target as the first module after `import`. Relative/package forms are also real import shapes if this population ever moves under a package. The failure mode is a false red, which pressures authors toward `NO-CALLER:` declarations for code that is in fact used.

What would prove this wrong: an AST-based importer check reporting those forms out of scope by contract, or `check_caller` accepting `import os, lib` as a use without also re-opening the string-literal false positive above.

## LOW

### L1 · `isidentifier()` is not the same as “legal import statement name”

`scripts/check-ratchet-contract.py:195`

> `if not stem.isidentifier():`

Reproduction:

```bash
python3 - <<'PY'
import keyword
print("class".isidentifier(), keyword.iskeyword("class"))
PY
```

Observed: `True True`.

A filename stem such as `class.py` passes the identifier guard even though `import class` is not legal Python syntax. Combined with the current regex-over-text approach, a blob containing `import class` can satisfy the import arm even though no AST import statement could exist. This is lower severity because the multiline-string issue is the practical false-positive route, but it is a hole in the stated discriminator.

What would prove this wrong: rejecting `keyword.iskeyword(stem)` before building the regex, or switching the discriminator to parsed import syntax rather than lexical identifier syntax.

## Could Not Establish

I verified the claimed gates on the current working tree:

```text
check-ratchet-contract --self-test: 52/52 passed
check-ratchet-contract: rc=0, ratchet contract OK
check-plan-code --self-test: 131/131 passed
check-selftest-counts: rc=0
check-plan-code --mutate .: 53 files, 1041 mutations, 1041 killed, 1041 attributed, 0 survivors
```

I did not find a concrete defect in the three `NO-CALLER:` reasons; they read as real “should not have an executable caller” arguments, not placeholders.

One scope caveat: `git diff master...HEAD` is four files, but the 52-case suite, `caller_blob_targets`, and the mutation count update are present in the dirty working tree, not in that committed four-file diff. I reviewed the working tree behavior because it matches the prompt’s claimed gates.
