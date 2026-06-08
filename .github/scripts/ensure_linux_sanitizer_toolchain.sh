#!/usr/bin/env bash
set -euo pipefail

ensure_linux_sanitizer_toolchain() {
  local missing=()
  local tool

  for tool in clang++ ld.lld ninja; do
    if ! command -v "$tool" >/dev/null 2>&1; then
      missing+=("$tool")
    fi
  done

  if [ "${#missing[@]}" -eq 0 ]; then
    echo "Using preinstalled Linux sanitizer toolchain"
    return 0
  fi

  sudo apt-get update
  sudo apt-get install -y clang lld ninja-build
  echo "Installed fallback Linux sanitizer toolchain: ${missing[*]}"
}
