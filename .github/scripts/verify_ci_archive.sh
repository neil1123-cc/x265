#!/usr/bin/env bash
set -euo pipefail

mode="${1:-}"
archive="${2:-}"
extract_dir="${3:-}"
target_cpu="${4:-}"
expected_count="${5:-}"

usage() {
  echo "usage: $0 <x265-release|x265-profiling|llvm-profdata> <archive> <extract_dir> [target_cpu] [expected_count]" >&2
  exit 2
}

verify_clean_dir() {
  local dir="$1"
  rm -rf "$dir"
  mkdir -p "$dir"
}

verify_x265_release() {
  local archive="$1"
  local extract_dir="$2"
  local target_cpu="$3"
  local expected_count="$4"

  test -s "$archive"
  verify_clean_dir "$extract_dir"
  7za t "$archive"
  7za x -o"$extract_dir" "$archive"

  local exe_count
  exe_count=$(find "$extract_dir" -maxdepth 1 -type f -name '*.exe' | wc -l)
  test "$exe_count" -eq "$expected_count"

  local all_exe="$extract_dir/x265-win64-${target_cpu}-all.exe"
  test -s "$all_exe"
  "$all_exe" --version >/dev/null

  if [ "$expected_count" -eq 4 ]; then
    for depth in 8bit 10bit 12bit; do
      local exe="$extract_dir/x265-win64-${target_cpu}-${depth}.exe"
      test -s "$exe"
      "$exe" --version >/dev/null
    done
  fi

  test -z "$(find "$extract_dir" -mindepth 1 -maxdepth 1 ! -name '*.exe' -print -quit)"
}

verify_x265_profiling() {
  local archive="$1"
  local extract_dir="$2"
  local target_cpu="$3"

  test -s "$archive"
  verify_clean_dir "$extract_dir"
  7za t "$archive"
  7za x -o"$extract_dir" "$archive"

  local exe_count
  exe_count=$(find "$extract_dir" -maxdepth 1 -type f -name '*.exe' | wc -l)
  test "$exe_count" -eq 3

  for profile_class in 8b-lib 12b-lib all; do
    local exe="$extract_dir/x265-profiling-win64-${target_cpu}-${profile_class}.exe"
    test -s "$exe"
    "$exe" --version >/dev/null
  done

  test -z "$(find "$extract_dir" -mindepth 1 -maxdepth 1 ! -name '*.exe' -print -quit)"
}

verify_llvm_profdata() {
  local archive="$1"
  local extract_dir="$2"

  test -s "$archive"
  verify_clean_dir "$extract_dir"
  7za t "$archive"
  7za x -o"$extract_dir" "$archive"

  test -s "$extract_dir/llvm-profdata.exe"
  "$extract_dir/llvm-profdata.exe" --version >/dev/null

  local dll_count
  dll_count=$(find "$extract_dir" -maxdepth 1 -type f -iname '*.dll' | wc -l)
  test "$dll_count" -gt 0
  test -z "$(find "$extract_dir" -mindepth 1 -maxdepth 1 ! -iname '*.exe' ! -iname '*.dll' -print -quit)"
}

case "$mode" in
  x265-release)
    [ -n "$target_cpu" ] && [ -n "$expected_count" ] || usage
    verify_x265_release "$archive" "$extract_dir" "$target_cpu" "$expected_count"
    ;;
  x265-profiling)
    [ -n "$target_cpu" ] || usage
    verify_x265_profiling "$archive" "$extract_dir" "$target_cpu"
    ;;
  llvm-profdata)
    verify_llvm_profdata "$archive" "$extract_dir"
    ;;
  *)
    usage
    ;;
esac
