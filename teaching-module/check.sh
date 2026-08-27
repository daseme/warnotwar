#!/usr/bin/env bash
# Parse-check every inline <script> block and shared.js in this module.
# Two of eight labs once shipped with broken JS and nothing caught it;
# this is the gate that would have.
set -e
cd "$(dirname "$0")"

# node on PATH, else the Windows-side node via a UNC path (WSL setups)
if command -v node >/dev/null 2>&1; then
  check() { node --check "$1"; }
elif [ -x "/mnt/c/Program Files/nodejs/node.exe" ]; then
  check() { "/mnt/c/Program Files/nodejs/node.exe" --check "$(wslpath -w "$1")"; }
else
  echo "check.sh: no node found; skipping JS parse check" >&2
  exit 0
fi

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

for f in *.html; do
  python3 - "$f" "$tmp/$(basename "$f" .html).js" <<'EOF'
import re, sys
src = open(sys.argv[1]).read()
blocks = re.findall(r'<script(?![^>]*src=)[^>]*>(.*?)</script>', src, re.S)
open(sys.argv[2], 'w').write("\n".join(blocks))
EOF
done

fail=0
for f in "$tmp"/*.js *.js; do
  [ -e "$f" ] || continue
  if ! check "$f"; then echo "FAIL: $f"; fail=1; fi
done
[ "$fail" = 0 ] && echo "all teaching-module scripts parse"
exit "$fail"
