<!-- codex-review: model=gpt-6.1-sol -->

NOT CONVERGED

Reviewed `a4f6d4b5`. **The current tree is not ready to serve as a settled Phase 1 approval contract.** The fold introduced false enforcement claims, leaves reproducible guard bypasses, and still omits an inheritance population. No tracked files were changed.

References: **S** = the spec; **P** = walkthrough fragment; **H** = composed walkthrough; **G** = `scripts/check-claim-propagation.py`.

### B1 — Blocking: the replacement measurement no longer describes HEAD

**Sites:** S §3’s three-stage table and §7 item 8, lines 993–995; P lines 355–371 and corresponding H text.

**Claim:** The same nine files total **6,525 “today” / at `HEAD`**; the three shared contracts total **630**, including a **346-line** delivery contract.

**Refutation:** The fold itself added 17 lines to that contract. At reviewed HEAD:

```text
explainer-delivery.md                  363
corpus-search.md                        73
handoff-path.md                        211
shared total                          647
same nine files                     6,542
larger prose-counted set            11,624
```

The six Python files still total **10,373**, the four skills **604**, and the generators **4,798**. The replacement defect remains real, but its newly repeated measurement is stale.

**Ran/read:** Enumerated all named files; independently summed the nine files with `git show HEAD:<path>`. Historical totals reproduce as **3,599** at `cacbac17` and **3,737** at `100cf498`. Read `d4a72a5f`, which introduces the extra 17 lines.

S’s dated-measurement disclaimer can preserve a historical snapshot. It cannot simultaneously make the explicit **“HEAD”** and **“today”** labels accurate.

### B2 — Blocking: the new delivery contract claims composition enforcement that does not exist

**Site:** `.agents/skills/shared/explainer-delivery.md`, lines 123–138.

**Claim:** The guard “enforces” recomposition and “refuses this” for the marketplace walkthrough pair.

**Refutation:** In a temporary copy of the real S/P/H, I appended this only to P:

```html
<p>The owner must approve a paid support subscription.</p>
```

H remained unchanged. `audit()` returned **`problems: []`**.

The guard expands the **path list** to include H; it neither composes H nor compares its contents with a composition of P. Registered token and figure checks do not establish recomposition.

**Ran/read:** Read the new contract and `audited_sites()`/`audit()`; executed the temporary-tree experiment above. This is a false statement about enforcement, beyond G’s honestly documented semantic limits.

### H1 — High: ordinary whitespace between inline elements hides a retired claim

**Sites:** G `_Blocks.handle_data()`, lines 378–390; `_html_occurrences()`, lines 440–474.

**Claim:** Block accumulation prevents ordinary inline formatting from hiding registered retired wording.

**Refutation:**

```html
<p>A library inherits its support verdict from the entry-points.</p>
```

returns **`(1, 0)`**, while:

```html
<p>A library inherits its <em>support</em> <em>verdict</em> from the entry-points.</p>
```

returns **`(0, 0)`**.

The standalone space between `</em>` and `<em>` is discarded by `if not data.strip(): return`, joining `supportverdict`. Both render the same words to a reader.

**Ran/read:** Called `_html_occurrences()` on both forms. Appended the formatted assertion to P in a temporary copy of the real documents: **the complete audit remained clean**. This attacks the replacement parser, rather than repeating the closed per-text-node finding.

### H2 — High: the new carrier-closure rule ignores carriers without text nodes

**Sites:** G `_Blocks.handle_startendtag()`, lines 367–368; `handle_data()`; closure loop, lines 608–635.

**Claim:** Every `data-derived` key in an audited page must be registered.

**Refutation:** Each of these unregistered carriers passes:

```html
<span data-derived="unknown"></span>
<span data-derived="unknown"/>
<img data-derived="unknown" src="x">
<input data-derived="unknown" value="999">
```

The closure loop examines `_derived_values()`, which acquires keys only while processing text. Opening a carrier is insufficient. The `<input>` can display a value while remaining invisible to closure checking.

**Ran/read:** Appended the examples to temporary copies of the real pages and called `audit()`. All returned **no problems**, including the input appended to both P and H.

### H3 — High: the stated reason for omitting the absent-path mutation is falsified

**Site:** G lines 267–275; `scripts/mutations/check-claim-propagation.json`.

**Claim:** The absent-path check “cannot have a usable” mutation because every disabling change crashes before its named cases can fail.

**Refutation:** This mutation disables refusal without any crash:

```python
if absent_paths:
    return [], []
```

The suite returns failure and prints named failures:

- `audit: an empty tree raises CannotRun`
- `audit: ONE absent registered path raises CannotRun`
- `audit: a DERIVED-only page absence raises CannotRun`
- `main: a tree with no registered document exits 2, not 0`

**Ran/read:** Executed the modified source in memory and ran `_self_test()`: **four named failures, no traceback**. This is precisely a return-to-clean-result regression that the current cases detect and a manifest entry can exercise. The crash from replacing the condition with `False` does not justify omitting all mutations.

### M1 — Medium: measured-plus-argued importers still have no aggregation rule

**Site:** S §4 inheritance table, lines 332–338; D5’s evidence-grade definitions.

**Claim:** The table supplies aggregation rules for library evidence.

**Refutation:** Construct a library with two importers:

1. A passes a measured scenario that exercises the library.
2. B’s experiment cannot run, so the new rule classifies B as `argued`.

This population is neither **all passing**, **passing and failing**, **only argued**, **all failing**, nor **no importer**. The new CANNOT RUN classification expressly prevents treating B as failing, so the mixed row cannot resolve it.

Replacing A’s pass with an attributed measured failure produces another uncovered mixed population.

**Ran/read:** Applied the written predicates to these populations and compared them with D5. The successful-scenario requirement constrains an inherited grade but does not supply the missing aggregation rule.

### M2 — Medium: tolerant unwind remains behaviourally unpinned

**Site:** G `_Blocks.handle_endtag()`, lines 370–377.

**Claim under test:** The suite protects tolerant closing-tag unwind.

**Refutation:** Replacing:

```python
del self.stack[i:]
```

with:

```python
self.stack.pop(i)
```

leaves **80/80 tests passing**.

It changes extraction:

```html
<p><span><b data-derived="k">1</span>2</b></p>
```

produces `{'k': '1'}` normally and `{'k': '12'}` under the mutant.

**Ran/read:** Executed both sources in memory, ran their self-tests, and compared `_derived_values()` on that witness. This is a demonstrated coverage gap, not a claim that the current implementation already performs the mutant’s behaviour.

### M3 — Medium: D8’s third correction did not reach its acceptance bound

**Site:** S §7 item 8, lines 986–1004.

**Claim:** D8 delivers **three** remaining corrections.

**Refutation:** The same section still says **“Both are one-line repairs,” “Both repairs,”** and fails when **“either correction”** is missing. The third correction was added to the table without identifying it in the downstream acceptance condition.

A change correcting the ratio and concentration claims while retaining the defective replacement corpus satisfies the old two-correction reading.

**Ran/read:** Compared the three-row table with its immediately following bound and falsifier. This is the specified propagation failure inside the replacement itself.

### L1 — Low: the moved provenance reference was not propagated to the walkthrough

**Sites:** P line 749; H line 826.

**Claim:** The invented-number incident is “recorded in [the spec’s] §9b.”

**Refutation:** S now has a combined §9b/9c forwarding section; the incident itself moved into the coordinator document.

**Ran/read:** Searched §4b/§4c/§9b/§9c references across S/P/H/G and read the destination. The spec’s forwarding link resolves correctly, but the walkthrough still describes the former location.

### What I checked and could not refute

- **Wrong-directory replacement:** Re-ran both commands inside both exact recorded clones. Results were **2, 2, 2, 2**, with missing-file errors naming paths beneath the caller’s working directory. That supports the CWD-resolution mechanism and self-location remedy; it does **not** establish an observed wrong-file execution. **Falsifier:** a different exit/result or resolution outside the caller’s directory.

- **Three remaining index defects:** All remain present: “roughly 3x,” “concentrated in one file,” and the headline’s inconsistent corpus. The six Python addends total **10,373**, plus **604** skills gives **10,977**; generators contribute **4,798**. **Falsifier:** removal of the assertions, different addends, or an enumeration matching the counted corpus. B1 concerns the fold’s newly stale shared-contract and HEAD measurements.

- **Committed guard and scoped mutations:** Self-test **80/80**; real audit clean. Copied the seven actual `HARNESS_TREE` paths with `rsync -aL`, retained only this manifest, reduced the copied expectation to its one key, and ran the scoped harness: **green control, 24 killed, 24 attributed, zero survivors, green re-control**. **Falsifier:** a red control, survivor, or missing named failure.

- **Several repaired branches:** Disabling partial propagation, served-page expansion, carrier multiplicity, closure, and whitespace normalization reddens the suite. Removing each of the four retirement markers independently also reddens it. The doubly marked Markdown fixture remains, but dedicated cases prevent it masking loss of either marker’s behaviour. **Falsifier:** any tested neutering remaining green.

- **Injected chrome:** Fragment/composed extraction yielded **12,472 injected bytes**, no registered phrase, no carrier, and no MIT-containing word. **Falsifier:** any such match in that extraction.

- **Detector 7’s declaration:** The new `invoked-by: user` exemption is mechanically searchable. The existing four skills lack it, so absent another qualifying production invoker or registration they require changes under the newly explicit contract. That is declared migration work, not by itself a false positive. **Falsifier:** an exemption still dependent solely on inferring human intent.

- **Section ordering and backlog:** §4b/§4c retain their decision meanings after moving; their substantive references agree. Backlog 293 records the previously undocumented gate, and 294 explicitly defers attribution migration. **Falsifier:** a reference targeting the other decision, or those rows claiming the deferred work is completed.

**UNVERIFIED:** Actual publishability-detector behaviour, installed-package self-location, and tier-A/tier-B experiments: their implementation/package is not present. The whole-repository mutation sweep was deliberately not run. These results establish the scoped manifest’s behaviour, not all repository gates or every possible branch mutation.
