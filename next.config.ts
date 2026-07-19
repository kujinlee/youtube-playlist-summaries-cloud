import type { NextConfig } from "next";
import path from "path";

const nextConfig: NextConfig = {
  // Emit .next/standalone — a self-contained server with ONLY the node_modules files @vercel/nft
  // traces as reachable, plus a minimal server.js. Without this the deploy image has to carry the
  // whole install (492 MB) because `next start` needs the full dependency tree present.
  // Docs: node_modules/next/dist/docs/01-app/03-api-reference/05-config/01-next-config-js/output.md
  // NOTE: standalone deliberately does NOT copy `public/` or `.next/static` — the Dockerfile copies
  // both explicitly, per that doc's "Automatically Copying Traced Files" section.
  output: 'standalone',
  outputFileTracingRoot: path.join(__dirname),
  turbopack: {
    root: path.resolve(__dirname),
  },
  // Keep the Playwright driver external — it is a Node library loaded at runtime by the PDF
  // export route (lib/pdf/generate-doc-pdf.ts), not something to bundle into the server build.
  serverExternalPackages: ["playwright"],
};

export default nextConfig;
