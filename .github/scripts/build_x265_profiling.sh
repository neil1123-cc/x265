#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

profile_class="${1:-}"
target_cpu="${2:-}"
use_mimalloc="${3:-}"
source_dir="${4:-x265/source}"
build_prefix_path="${5:-/usr/local}"
profiling_cxx_flags="${6:-}"
output_name="${7:-x265-profiling.exe}"
enable_lsmash="${8:-false}"

if [ -z "$profile_class" ] || [ -z "$target_cpu" ] || [ -z "$use_mimalloc" ] || [ -z "$profiling_cxx_flags" ]; then
  echo "usage: $0 <8b-lib|12b-lib|all> <target-cpu> <use-mimalloc> <source-dir> <build-prefix-path> <profiling-cxx-flags> <output-name> <enable-lsmash>" >&2
  exit 2
fi

source build/cxx20_scan_helpers.sh
CXX20_CHECK_SCRIPT="${script_dir}/check_compile_commands.py"

lsmash_args=()
if [ "$enable_lsmash" = 'true' ] || [ "$enable_lsmash" = 'ON' ]; then
  lsmash_args=(-DENABLE_LSMASH=ON)
fi

init_cmake_common_args() {
  cmake_common_args=(
    -GNinja "$source_dir"
    -DCMAKE_PREFIX_PATH="$build_prefix_path"
    -DENABLE_LAVF=ON
    -DENABLE_STATIC_LAVF=ON
    -DENABLE_MKV=ON
    -DTARGET_CPU="$target_cpu"
    -DENABLE_AVISYNTH=OFF
    -DENABLE_VPYSYNTH=OFF
    -DUSE_MIMALLOC="$use_mimalloc"
    -DENABLE_UNITY_BUILD=ON
    -DENABLE_CXX20_WARNING_SCAN=ON
    -DWARNINGS_AS_ERRORS=ON
    -DCMAKE_ASM_NASM_FLAGS=-w-macro-params-legacy
    -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
  )
  if [ "$#" -gt 0 ]; then
    cmake_common_args+=("$@")
  fi
  if [ "${#lsmash_args[@]}" -gt 0 ]; then
    cmake_common_args+=("${lsmash_args[@]}")
  fi
}

configure_x265() {
  local build_dir="$1"
  shift
  cmake "${cmake_common_args[@]}" -B "$build_dir" "$@"
}

wait_for_jobs() {
  local status=0
  local pid

  for pid in "$@"; do
    if ! wait "$pid"; then
      status=1
    fi
  done

  return "$status"
}

build_single_profile() {
  local build_dir="$1"
  shift
  configure_x265 "$build_dir" "$@"
  check_cxx20_commands_profiling "$build_dir"
  ninja -C "$build_dir"
  mv "${build_dir}/x265.exe" "${build_dir}/${output_name}"
}

build_8b_lib_profile() {
  init_cmake_common_args
  build_single_profile \
    build/8b \
    -DENABLE_SHARED=OFF \
    -DCMAKE_CXX_FLAGS="$profiling_cxx_flags" \
    -DCMAKE_EXE_LINKER_FLAGS=-flto=thin
}

build_12b_lib_profile() {
  init_cmake_common_args
  build_single_profile \
    build/12b \
    -DHIGH_BIT_DEPTH=ON \
    -DMAIN12=ON \
    -DENABLE_SHARED=OFF \
    -DCMAKE_CXX_FLAGS="$profiling_cxx_flags" \
    -DCMAKE_EXE_LINKER_FLAGS=-flto=thin
}

build_all_profile() {
  local nproc
  local ninja_jobs_pair
  local ninja_8b_pid
  local ninja_12b_pid

  nproc=$(nproc)
  ninja_jobs_pair=$(( (nproc + 1) / 2 ))
  echo "Ninja job limit for paired profiling helper builds: ${ninja_jobs_pair}"

  init_cmake_common_args -DEXPORT_C_API=OFF -DENABLE_SHARED=OFF -DENABLE_CLI=OFF

  configure_x265 build/8b -DCMAKE_CXX_FLAGS="$profiling_cxx_flags"
  check_cxx20_commands_profiling build/8b
  ninja -C build/8b -j "$ninja_jobs_pair" &
  ninja_8b_pid=$!

  configure_x265 build/12b \
    -DHIGH_BIT_DEPTH=ON \
    -DMAIN12=ON \
    -DCMAKE_CXX_FLAGS="$profiling_cxx_flags"
  check_cxx20_commands_profiling build/12b
  ninja -C build/12b -j "$ninja_jobs_pair" &
  ninja_12b_pid=$!

  wait_for_jobs "$ninja_8b_pid" "$ninja_12b_pid"

  cp build/8b/libx265.a build/10b/libx265_8b.a
  cp build/12b/libx265.a build/10b/libx265_12b.a

  init_cmake_common_args
  configure_x265 build/10b \
    -DEXTRA_LIB="x265_8b.a;x265_12b.a" \
    -DEXTRA_LINK_FLAGS=-L. \
    -DLINKED_8BIT=ON \
    -DLINKED_12BIT=ON \
    -DENABLE_HDR10_PLUS=ON \
    -DHIGH_BIT_DEPTH=ON \
    -DENABLE_SHARED=OFF \
    -DCMAKE_CXX_FLAGS="$profiling_cxx_flags" \
    -DCMAKE_EXE_LINKER_FLAGS=-flto=thin
  check_cxx20_commands_profiling build/10b
  ninja -C build/10b
  mv build/10b/x265.exe "build/10b/${output_name}"
}

case "$profile_class" in
  8b-lib)
    build_8b_lib_profile
    ;;
  12b-lib)
    build_12b_lib_profile
    ;;
  all)
    build_all_profile
    ;;
  *)
    echo "unknown profiling class: $profile_class" >&2
    exit 2
    ;;
esac
