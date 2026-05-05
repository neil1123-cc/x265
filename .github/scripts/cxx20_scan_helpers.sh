#!/usr/bin/env bash
set -euo pipefail

cxx20_common_check_args=(
  --forbidden-flag-substring=-Wno-deprecated
  --forbidden-flag-substring=-Wno-error=deprecated
  --forbidden-flag-substring=-Wno-deprecated-declarations
  --forbidden-flag-substring=-Wno-error=deprecated-declarations
  --forbidden-flag-substring=-Wno-volatile
  --forbidden-flag-substring=-Wno-error=volatile
  --depth-exclude-path=dynamicHDR10/
)

cxx20_clang_check_args=(
  --required-flag=-Wdeprecated
  --required-flag=-Werror=deprecated
  --required-flag=-Wdeprecated-volatile
  --required-flag=-Werror=deprecated-volatile
  --required-flag=-Wdeprecated-enum-enum-conversion
  --required-flag=-Werror=deprecated-enum-enum-conversion
  --required-flag=-Wdeprecated-enum-float-conversion
  --required-flag=-Werror=deprecated-enum-float-conversion
)

cxx20_gcc_check_args=(
  --required-flag=-Wdeprecated
  --required-flag=-Werror=deprecated
  --required-flag=-Wdeprecated-declarations
  --required-flag=-Werror=deprecated-declarations
  --required-flag=-Wvolatile
  --required-flag=-Werror=volatile
)

check_cxx20_commands_clang() {
  local build_dir="$1"
  shift
  python x265/.github/scripts/check_compile_commands.py "$build_dir" \
    "${cxx20_common_check_args[@]}" \
    "${cxx20_clang_check_args[@]}" \
    "$@"
}

check_cxx20_commands_gcc() {
  local build_dir="$1"
  shift
  python x265/.github/scripts/check_compile_commands.py "$build_dir" \
    "${cxx20_common_check_args[@]}" \
    "${cxx20_gcc_check_args[@]}" \
    "$@"
}

check_cxx20_commands_profiling() {
  local build_dir="$1"
  shift
  python "${CXX20_CHECK_SCRIPT:-x265/.github/scripts/check_compile_commands.py}" "$build_dir" \
    --required-flag=-fprofile-instr-generate \
    --required-flag=-fprofile-update=atomic \
    "$@"
}

check_cxx20_commands_pgo_consume() {
  local build_dir="$1"
  shift
  python "${CXX20_CHECK_SCRIPT:-x265/.github/scripts/check_compile_commands.py}" "$build_dir" \
    --required-flag-prefix=-fprofile-instr-use= \
    --forbidden-flag=-fprofile-instr-generate \
    --forbidden-flag=-fprofile-update=atomic \
    "$@"
}

configure_cxx20_scan() {
  local source_dir="$1"
  local build_dir="$2"
  shift 2
  local target_cpu=x86-64
  local cxx_compiler_arg=()
  if [[ "${1:-}" == --target-cpu=* ]]; then
    target_cpu="${1#--target-cpu=}"
    shift
  fi
  if [[ "${1:-}" == --cxx-compiler=* ]]; then
    cxx_compiler_arg=(-DCMAKE_CXX_COMPILER="${1#--cxx-compiler=}")
    shift
  fi
  cmake -GNinja "$source_dir" -B "$build_dir" \
    -DCMAKE_PREFIX_PATH=/usr/local \
    -DCMAKE_BUILD_TYPE=Release \
    -DTARGET_CPU="$target_cpu" \
    -DENABLE_SHARED=OFF \
    -DENABLE_LAVF=OFF \
    -DENABLE_LSMASH=OFF \
    -DUSE_MIMALLOC=OFF \
    -DENABLE_UNITY_BUILD=OFF \
    -DENABLE_CXX20_WARNING_SCAN=ON \
    -DWARNINGS_AS_ERRORS=ON \
    -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
    "${cxx_compiler_arg[@]}" \
    "$@"
}
