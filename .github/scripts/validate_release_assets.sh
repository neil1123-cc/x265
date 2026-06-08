#!/usr/bin/env bash
set -euo pipefail

mode="${1:-}"
asset_dir="${2:-release-assets}"
tag_name="${3:-${GITHUB_REF_NAME:-}}"

mapfile -t assets < <(find "$asset_dir" -type f -name '*.7z' -printf '%f\n' | sort)
release_cpus='x86-64 haswell skylake alderlake raptorlake arrowlake znver2 znver3 znver4 znver5'

case "$mode" in
  release)
    expected_count=10
    count_label='release'
    prefix='x265'
    ;;
  profiling)
    expected_count=11
    count_label='profiling release'
    prefix='x265-profiling'
    profdata_count=0
    ;;
  *)
    echo "usage: $0 <release|profiling> [asset-dir] [tag-name]" >&2
    exit 2
    ;;
esac

if [ "${#assets[@]}" -ne "$expected_count" ]; then
  printf 'Expected %d %s archives, found %d:\n' "$expected_count" "$count_label" "${#assets[@]}" >&2
  printf '  %s\n' "${assets[@]}" >&2
  exit 1
fi

for asset in "${assets[@]}"; do
  matched=false
  for cpu in $release_cpus; do
    if [ "$asset" = "${prefix}-win64-${cpu}-clang.${tag_name}.7z" ]; then
      matched=true
      break
    fi
  done
  if [ "$matched" = true ]; then
    continue
  fi
  case "$mode:$asset" in
    profiling:llvm-profdata-win64-clang.*.7z)
      profdata_count=$((profdata_count + 1))
      ;;
    release:*)
      echo "Unexpected release archive: $asset" >&2
      exit 1
      ;;
    profiling:*)
      echo "Unexpected profiling release archive: $asset" >&2
      exit 1
      ;;
  esac
done

if [ "$mode" = 'profiling' ] && [ "$profdata_count" -ne 1 ]; then
  echo "Expected exactly one llvm-profdata archive, found $profdata_count" >&2
  exit 1
fi
