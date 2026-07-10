// NOTE on mocking technique: the plan's Step 1 draft used `jest.spyOn(modelStore, 'readModelEnvelope')`
// (a namespace-import spy). That throws `TypeError: Cannot redefine property` under this repo's
// SWC-compiled Jest transform (repro'd against the pre-existing, unmodified model-store.ts — not
// something this task introduced; no test in the repo uses that pattern). The repo's established
// convention for mocking a sibling lib module (see tests/lib/html-doc/serve-doc-mapping.test.ts) is a
// full `jest.mock(..., () => ({...}))` factory, used below. Assertions/interfaces are unchanged.
import { readFreshMagazineModel, isFresh } from '@/lib/html-doc/read-model';
import { GENERATOR_VERSION } from '@/lib/html-doc/constants';
import type { ReadOnlyBlobStore } from '@/lib/storage/blob-store';

jest.mock('@/lib/html-doc/model-store', () => ({ readModelEnvelope: jest.fn() }));
import { readModelEnvelope } from '@/lib/html-doc/model-store';
const mockReadModelEnvelope = readModelEnvelope as jest.Mock;

const principal = { id: 'owner-1', indexKey: 'pl-key' };
const fakeModel = { title: 'T', dek: 'd', sections: [] } as any;
const titles = ['A', 'B'];
const roStore: ReadOnlyBlobStore = { get: async () => null };

function envelope(over: Partial<any> = {}) {
  return { sourceMd: 'x.md', generatedAt: 'now', sourceSections: ['A', 'B'],
    generatorVersion: GENERATOR_VERSION, model: fakeModel, ...over };
}

describe('isFresh', () => {
  it('true when titles match and version matches', () => {
    expect(isFresh(envelope(), titles)).toBe(true);
  });
  it('false when a title differs', () => {
    expect(isFresh(envelope({ sourceSections: ['A', 'C'] }), titles)).toBe(false);
  });
  it('false when generatorVersion differs', () => {
    expect(isFresh(envelope({ generatorVersion: 'old' }), titles)).toBe(false);
  });
});

describe('readFreshMagazineModel', () => {
  afterEach(() => mockReadModelEnvelope.mockReset());

  it('returns ok with the model when a fresh envelope exists', async () => {
    mockReadModelEnvelope.mockResolvedValue(envelope());
    const r = await readFreshMagazineModel({ blobStore: roStore, principal, base: 'b', titles });
    expect(r).toEqual({ status: 'ok', model: fakeModel });
    // Arg-passthrough: prove the helper forwards (principal, base, blobStore) unchanged
    // rather than swallowing or reordering them (the mock otherwise hides this).
    expect(mockReadModelEnvelope).toHaveBeenCalledWith(principal, 'b', roStore);
  });

  it('returns not_ready when the envelope is absent', async () => {
    mockReadModelEnvelope.mockResolvedValue(null);
    const r = await readFreshMagazineModel({ blobStore: roStore, principal, base: 'b', titles });
    expect(r).toEqual({ status: 'not_ready' });
  });

  it('returns not_ready when the envelope is stale (version bump)', async () => {
    mockReadModelEnvelope.mockResolvedValue(envelope({ generatorVersion: 'old' }));
    const r = await readFreshMagazineModel({ blobStore: roStore, principal, base: 'b', titles });
    expect(r).toEqual({ status: 'not_ready' });
  });
});

import { readFileSync, existsSync, statSync } from 'fs';
import { join, dirname, basename } from 'path';

describe('B18c — read-model.ts is a generate-free leaf', () => {
  // Matches `import ... from '<spec>'`, `export ... from '<spec>'` (incl. `import type` /
  // `export type`), and side-effect `import '<spec>'`. Character classes match across
  // newlines, so multi-line named-import blocks are covered too.
  const IMPORT_SPEC_RE =
    /(?:import|export)\s+(?:type\s+)?[^'";]*?from\s+['"]([^'"]+)['"]|import\s+['"]([^'"]+)['"]/g;

  // Forbidden if the resolved path OR the raw specifier contains any of these as a substring —
  // deliberately broad so a subpath import (e.g. `@/lib/gemini/foo`) is still caught.
  const FORBIDDEN = ['@/lib/gemini', '@/lib/gemini-cost', 'serve-doc', 'reserve_serve_model'];
  const isForbidden = (spec: string) => FORBIDDEN.some((bad) => spec.includes(bad));

  /** Resolve an import specifier to a file path, or null for a bare npm package
   *  (which cannot be one of this app's own gemini/serve-doc modules by definition). */
  function resolveSpecifier(spec: string, fromFile: string): string | null {
    if (spec.startsWith('.')) return join(dirname(fromFile), spec);
    if (spec.startsWith('@/')) return join(process.cwd(), spec.slice(2));
    return null;
  }

  function resolveToFile(base: string): string | null {
    for (const candidate of [base, `${base}.ts`, `${base}.tsx`, join(base, 'index.ts')]) {
      if (existsSync(candidate) && statSync(candidate).isFile()) return candidate;
    }
    return null;
  }

  it('the entire transitive import graph never reaches gemini/gemini-cost/serve-doc', () => {
    const root = join(process.cwd(), 'lib/html-doc/read-model.ts');
    const visitedFiles = new Set<string>(); // cycle guard + traversal evidence
    const allSpecifiers: string[] = [];

    function walk(file: string) {
      if (visitedFiles.has(file)) return; // guard against import cycles
      visitedFiles.add(file);
      const src = readFileSync(file, 'utf-8');
      for (const m of src.matchAll(IMPORT_SPEC_RE)) {
        const spec = m[1] ?? m[2];
        if (!spec) continue;
        allSpecifiers.push(spec);
        const resolvedBase = resolveSpecifier(spec, file);
        if (!resolvedBase) continue; // bare npm package — nothing further to walk
        const resolved = resolveToFile(resolvedBase);
        if (resolved) walk(resolved);
      }
    }

    walk(root);

    // No specifier anywhere in the reachable graph names a forbidden module...
    for (const spec of allSpecifiers) expect(isForbidden(spec)).toBe(false);
    // ...and no resolved file path in the reachable graph is one either (catches the case
    // where a forbidden module is reached via a relative path that doesn't textually
    // contain the `@/lib/gemini` alias, e.g. a deep `../../gemini` relative import).
    for (const file of visitedFiles) expect(isForbidden(file)).toBe(false);

    // Sanity check: the traversal must be non-trivial. A walker broken by a regex or
    // resolution bug could silently visit only `read-model.ts` itself and pass vacuously —
    // assert it actually descended into both of read-model.ts's real dependencies.
    const visitedBasenames = [...visitedFiles].map((f) => basename(f));
    expect(visitedBasenames).toEqual(expect.arrayContaining(['model-store.ts', 'constants.ts']));
    expect(visitedFiles.size).toBeGreaterThanOrEqual(3);
  });
});
