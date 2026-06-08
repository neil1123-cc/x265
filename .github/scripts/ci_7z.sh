#!/usr/bin/env bash
set -euo pipefail

find_ci_7z() {
  local candidate
  for candidate in 7z 7za 7z.exe; do
    if command -v "$candidate" >/dev/null 2>&1; then
      command -v "$candidate"
      return 0
    fi
  done

  for candidate in \
    "/c/Program Files/7-Zip/7z.exe" \
    "/c/Program Files (x86)/7-Zip/7z.exe"; do
    if [ -x "$candidate" ]; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done

  echo "7zip executable not found" >&2
  return 1
}

ci_7z() {
  local tool
  tool=$(find_ci_7z)
  "$tool" "$@"
}

if [ "${BASH_SOURCE[0]}" = "$0" ]; then
  ci_7z "$@"
fi
