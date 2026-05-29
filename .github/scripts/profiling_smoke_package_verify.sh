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
    runtime_input=smoke_profile_mp4_8b.y4m
    runtime_output=smoke_profile_8b.mp4
    roundtrip_output=smoke_profile_roundtrip_8b.y4m
    roundtrip_pix_fmt=yuv420p
    profile_smoke_input=profile_smoke_input_8b.y4m
    profile_smoke_output=profile_smoke_8b.hevc
    profraw=profile-smoke-8b.profraw
    profdata=profile-smoke-8b.profdata
    dist_exe=dist/x265-profiling-win64-${target_cpu}-8b-lib.exe
    summary_title='8b-lib profiling smoke'
    summary_roundtrip_label='8b-lib'
    output_depth=8
    ;;
  12b-lib)
    build_dir=build/12b
    runtime_input=smoke_profile_mp4_12b.y4m
    runtime_output=smoke_profile_12b.mp4
    roundtrip_output=smoke_profile_roundtrip_12b.y4m
    roundtrip_pix_fmt=yuv420p12le
    profile_smoke_input=profile_smoke_input_12b.y4m
    profile_smoke_output=profile_smoke_12b.hevc
    profraw=profile-smoke-12b.profraw
    profdata=profile-smoke-12b.profdata
    dist_exe=dist/x265-profiling-win64-${target_cpu}-12b-lib.exe
    summary_title='12b-lib profiling smoke'
    summary_roundtrip_label='12b-lib'
    output_depth=12
    ;;
  all)
    build_dir=build/10b
    runtime_input=smoke_profile_mp4_all.y4m
    runtime_output=smoke_profile_all.mp4
    roundtrip_output=smoke_profile_roundtrip_all.y4m
    roundtrip_pix_fmt=yuv420p10le
    profile_smoke_input=profile_smoke_input_all.y4m
    profile_smoke_output=profile_smoke_all.hevc
    profraw=profile-smoke-all.profraw
    profdata=profile-smoke-all.profdata
    dist_exe=dist/x265-profiling-win64-${target_cpu}-all.exe
    summary_title='all profiling smoke'
    summary_roundtrip_label='all'
    output_depth=10
    ;;
  *)
    echo "unknown profiling class: $profile_class" >&2
    exit 2
    ;;
esac

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
ffmpeg -hide_banner -loglevel error -f lavfi -i testsrc2=size=64x64:rate=1 -frames:v 1 -c:v rawvideo -pix_fmt "$roundtrip_pix_fmt" -strict -1 "$profile_smoke_input"
"./${build_dir}/x265-profiling.exe" --output-depth "$output_depth" --crf 28 --preset ultrafast "$profile_smoke_input" -o "$profile_smoke_output"
test -s "$LLVM_PROFILE_FILE"
./profdata-dist/llvm-profdata.exe merge -o "$profdata" "$LLVM_PROFILE_FILE"
test -s "$profdata"
./profdata-dist/llvm-profdata.exe show "$profdata" >/dev/null

if [ -n "${GITHUB_STEP_SUMMARY:-}" ]; then
  {
    echo "### $summary_title"
    echo "- target_cpu: $target_cpu"
    echo "- standard: gnu++20"
    echo "- mp4_roundtrip_frames: $frame_count"
    echo "- profraw: $profraw"
    echo "- profdata: $profdata"
  } >> "$GITHUB_STEP_SUMMARY"
fi

strip -s "${build_dir}/x265-profiling.exe"
cp "${build_dir}/x265-profiling.exe" "$dist_exe"
