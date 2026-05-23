import type { NextConfig } from "next";
import path from "path";

const nextConfig: NextConfig = {
  outputFileTracingRoot: path.join(__dirname),
  turbopack: {
    root: path.resolve(__dirname),
  },
  // md-to-pdf uses __dirname internally to resolve markdown.css — Turbopack
  // rewrites __dirname to /ROOT which breaks the path. Externalize it so
  // Node requires it from node_modules at runtime instead.
  serverExternalPackages: ['md-to-pdf'],
};

export default nextConfig;
