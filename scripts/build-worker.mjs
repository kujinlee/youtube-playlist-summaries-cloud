// Bundles the worker entrypoint into a single self-contained CJS file.
//
// WHY: the worker used to run through ts-node (`npm run worker`), which forces the deploy image to
// carry the ENTIRE dependency tree plus typescript at runtime — the web process can ship a trimmed
// `.next/standalone`, but the worker dragged the full install back in, so the trim bought nothing.
// Bundling decouples them: after this, the runtime stage needs no node_modules of its own.
//
// EXTERNALS: playwright/playwright-core ship platform-specific binaries and a browser registry that
// cannot be inlined into a bundle. They are deliberately left as runtime requires, and resolve
// against `.next/standalone/node_modules`, where Next's file tracing already places both (verified:
// the /api/pdf route imports lib/pdf/generate-doc-pdf.ts, and next.config.ts marks playwright as a
// serverExternalPackage). The Dockerfile therefore places worker.js INSIDE the standalone root so
// that node's resolution finds them.
import { build } from 'esbuild';

await build({
  entryPoints: ['worker/main.ts'],
  bundle: true,
  platform: 'node',
  target: 'node22',
  format: 'cjs',
  outfile: 'dist/worker.js',
  sourcemap: true,          // stack traces from a bundled worker are unreadable without this
  external: ['playwright', 'playwright-core'],
  tsconfig: 'tsconfig.worker.json',
  logLevel: 'info',
});
