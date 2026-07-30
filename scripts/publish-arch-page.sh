#!/usr/bin/env bash
# Publish docs/architecture.html to GitHub Pages (the gh-pages branch).
#
# Live at: https://kujinlee.github.io/youtube-playlist-summaries-cloud/architecture.html
#
# master's docs/architecture.html is the source of truth; gh-pages is a
# build output holding ONLY the diagram — the rest of docs/ (design spec,
# backlog, 500+ review files) deliberately stays unpublished.
#
# Uses git plumbing so the working tree and current branch are never touched
# — no checkout, no stash, safe to run mid-edit on any branch.
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

SRC="docs/architecture.html"
[ -f "$SRC" ] || { echo "error: $SRC not found" >&2; exit 1; }

REF=$(git rev-parse --short HEAD)

# index.html redirects the bare Pages URL to the diagram.
INDEX=$(cat <<'HTML'
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>YouTube Playlist Summaries — Architecture</title>
<meta http-equiv="refresh" content="0; url=./architecture.html">
<link rel="canonical" href="./architecture.html">
</head>
<body>
<p>Redirecting to the <a href="./architecture.html">architecture diagram</a>&hellip;</p>
</body>
</html>
HTML
)

arch_blob=$(git hash-object -w "$SRC")
index_blob=$(printf '%s\n' "$INDEX" | git hash-object -w --stdin)
# .nojekyll: serve files verbatim, skipping the Jekyll build entirely.
nojekyll_blob=$(printf '' | git hash-object -w --stdin)

tree=$(printf '100644 blob %s\t.nojekyll\n100644 blob %s\tarchitecture.html\n100644 blob %s\tindex.html\n' \
  "$nojekyll_blob" "$arch_blob" "$index_blob" | git mktree)

# Orphan commit each time — gh-pages is disposable output, not history worth keeping.
commit=$(git commit-tree "$tree" -m "Publish architecture diagram (from ${REF})")

git push --force origin "$commit:refs/heads/gh-pages"

echo
echo "Published. Pages rebuild takes ~30-60s:"
echo "  https://kujinlee.github.io/youtube-playlist-summaries-cloud/architecture.html"
