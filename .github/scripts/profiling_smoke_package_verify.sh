#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
profile_class="${1:-}"
target_cpu="${TARGET_CPU:-}"

if [ -z "$profile_class" ] || [ -z "$target_cpu" ]; then
  echo "usage: TARGET_CPU=... $0 <8b-lib|12b-lib|all>" >&2
  exit 2
fi

case "$profile_class" in
  8b-lib)
    build_dir=build/8b
    smoke_suffix=8b
    output_depth=8
    roundtrip_pix_fmt=yuv420p
    ;;
  12b-lib)
    build_dir=build/12b
    smoke_suffix=12b
    output_depth=12
    roundtrip_pix_fmt=yuv420p12le
    ;;
  all)
    build_dir=build/10b
    smoke_suffix=all
    output_depth=10
    roundtrip_pix_fmt=yuv420p10le
    ;;
  *)
    echo "unknown profiling class: $profile_class" >&2
    exit 2
    ;;
esac

runtime_input="smoke_profile_mp4_${smoke_suffix}.y4m"
runtime_output="smoke_profile_${smoke_suffix}.mp4"
roundtrip_output="smoke_profile_roundtrip_${smoke_suffix}.y4m"
profile_smoke_input="profile_smoke_input_${smoke_suffix}.y4m"
profile_smoke_output="profile_smoke_${smoke_suffix}.hevc"
profraw="profile-smoke-${smoke_suffix}.profraw"
profdata="profile-smoke-${smoke_suffix}.profdata"
dist_exe="dist/x265-profiling-win64-${target_cpu}-${profile_class}.exe"
summary_title="${profile_class} profiling smoke"
summary_roundtrip_label="$profile_class"

runtime_smoke_enabled=0
linked_8b_smoke_status=n/a
linked_12b_smoke_status=n/a

linked_8b_smoke_input=profile_smoke_input_all_8b.y4m
linked_8b_smoke_output=profile_smoke_all_8b.hevc
linked_12b_smoke_input=profile_smoke_input_all_12b.y4m
linked_12b_smoke_output=profile_smoke_all_12b.hevc

run_profile_smoke() {
  local depth="$1"
  local pix_fmt="$2"
  local input="$3"
  local output="$4"

  ffmpeg -hide_banner -loglevel error -f lavfi -i testsrc2=size=64x64:rate=1 -frames:v 1 -c:v rawvideo -pix_fmt "$pix_fmt" -strict -1 "$input"
  "./${build_dir}/x265-profiling.exe" --output-depth "$depth" --crf 28 --preset ultrafast "$input" -o "$output"
  test -s "$output"
}

case "$target_cpu" in
  x86-64|alderlake|znver4)
    runtime_smoke_enabled=1
    ;;
  *)
    runtime_smoke_enabled=0
    ;;
esac

if [ "$runtime_smoke_enabled" -eq 1 ]; then
  ffmpeg -hide_banner -loglevel error -f lavfi -i testsrc2=size=128x72:rate=24 -frames:v 12 -c:v rawvideo -pix_fmt "$roundtrip_pix_fmt" -strict -1 "$runtime_input"
  "./${build_dir}/x265-profiling.exe" --output-depth "$output_depth" --crf 28 --preset medium "$runtime_input" -o "$runtime_output"
  test -s "$runtime_output"
  ffmpeg -hide_banner -loglevel error -i "$runtime_output" -c:v rawvideo -pix_fmt "$roundtrip_pix_fmt" -strict -1 "$roundtrip_output"
  test -s "$roundtrip_output"
  frame_count=$(grep -aob 'FRAME' "$roundtrip_output" | wc -l || true)
  echo "${summary_roundtrip_label} roundtrip FRAME tokens: ${frame_count:-missing}"
  test "$frame_count" = "12"
else
  frame_count=skipped
  echo "Skipping runtime smoke for target CPU $target_cpu; GitHub runner host may not support the emitted instructions"
fi

./profdata-dist/llvm-profdata.exe --version
rm -f "$profraw" "$profdata"
export LLVM_PROFILE_FILE="$PWD/$profraw"
run_profile_smoke "$output_depth" "$roundtrip_pix_fmt" "$profile_smoke_input" "$profile_smoke_output"
test -s "$LLVM_PROFILE_FILE"
./profdata-dist/llvm-profdata.exe merge -o "$profdata" "$LLVM_PROFILE_FILE"
test -s "$profdata"
./profdata-dist/llvm-profdata.exe show "$profdata" >/dev/null

if [ "$profile_class" = all ]; then
  run_profile_smoke 8 yuv420p "$linked_8b_smoke_input" "$linked_8b_smoke_output"
  linked_8b_smoke_status=ok

  run_profile_smoke 12 yuv420p12le "$linked_12b_smoke_input" "$linked_12b_smoke_output"
  linked_12b_smoke_status=ok
fi

if [ -n "${GITHUB_STEP_SUMMARY:-}" ]; then
  {
    echo "### $summary_title"
    echo "- target_cpu: $target_cpu"
    echo "- standard: gnu++20"
    echo "- mp4_roundtrip_frames: $frame_count"
    echo "- linked_8b_smoke: $linked_8b_smoke_status"
    echo "- linked_12b_smoke: $linked_12b_smoke_status"
    echo "- profraw: $profraw"
    echo "- profdata: $profdata"
  } >> "$GITHUB_STEP_SUMMARY"
fi

strip -s "${build_dir}/x265-profiling.exe"
cp "${build_dir}/x265-profiling.exe" "$dist_exe"
