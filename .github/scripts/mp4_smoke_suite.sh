#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${script_dir}/mp4_smoke_helpers.sh"

smoke_mp4() {
  trap 'status=$?; if [ $status -ne 0 ]; then echo "=== smoke mp4 diagnostics ==="; dump_mp4_diagnostics smoke smoke.mp4; fi; exit $status' EXIT
  make_y4m smoke.y4m 24 16 yuv420p
  if build/all/x265.exe --input smoke.y4m --input-res 128x72 --fps 24 --frames 16 --bframes 4 --keyint 8 --min-keyint 8 --no-open-gop --output smoke.mp4; then
    :
  else
    status=$?
    cat > smoke_lldb.cmd <<'LLDB'
run --input smoke.y4m --input-res 128x72 --fps 24 --frames 16 --bframes 4 --keyint 8 --min-keyint 8 --no-open-gop --output smoke.mp4
process status
thread list
thread backtrace all
frame info
register read
disassemble --pc
image list
quit
LLDB
    lldb -b -s smoke_lldb.cmd build/all/x265.exe || true
    exit $status
  fi
  probe_mp4 smoke smoke.mp4 flags
  assert_common_mp4 smoke 128 72 yuv420p 24/1 16 1/24000
  grep -q "duration=" smoke_format.txt
  awk -F, 'NR == 1 { if ($1 !~ /K/) exit 1 } END { if (NR != 16) exit 1 }' smoke_packets.csv
  awk -F, 'NF >= 3 && $3 != "N/A" { if (seen && ($3+0) < prev) exit 1; prev=$3+0; seen=1 } END { if (!seen) exit 1 }' smoke_frames.csv
  awk -F, 'NF >= 3 && $2 != "N/A" && $3 != "N/A" { if (($2+0) > ($3+0)) diff=1 } END { if (!diff) exit 1 }' smoke_frames.csv
  awk -F, 'NR == 1 { if (NF < 1 || $1 != 1) exit 1 }' smoke_frames.csv
  awk -F, 'NR == 1 { if (NF < 2 || $2 == "N/A") exit 1 }' smoke_frames.csv
  awk -F, 'NR == 1 { if (($2+0) < -0.001 || ($2+0) > 0.05) exit 1 }' smoke_frames.csv
  awk -F, 'NR > 1 && $2 != "N/A" && prev != "" { delta = ($2+0) - prev; if (delta < 0.03 || delta > 0.05) exit 1 } { if ($2 != "N/A") prev = $2+0 } END { if (NR < 2) exit 1 }' smoke_frames.csv
  awk -F, 'NR == 1 { if (NF < 3 || $3 == "N/A") exit 1 }' smoke_frames.csv
  awk -F, 'NR == 1 { if (($2+0) < ($3+0)) exit 1 }' smoke_frames.csv
  awk -F, 'END { if (NR != 16) exit 1; if (NF < 2 || $2 == "N/A") exit 1; if (($2+0) < 0.55 || ($2+0) > 0.75) exit 1 }' smoke_frames.csv
  awk -F, 'NR > 8 && NF >= 3 && $2 != "N/A" && $3 != "N/A" { if (($2+0) > ($3+0)) diff=1 } END { if (!diff) exit 1 }' smoke_frames.csv
  awk -F, '$1 == 1 { kf++; if (kf == 2 && NR != 9) exit 1 } END { if (kf < 2) exit 1 }' smoke_frames.csv
  assert_duration_window smoke 0.60 0.75
}

smoke_mp4_open_gop() {
  trap 'status=$?; if [ $status -ne 0 ]; then echo "=== smoke open-gop diagnostics ==="; dump_mp4_diagnostics smoke_open smoke_open.mp4; fi; exit $status' EXIT
  make_y4m smoke_open.y4m 24 16 yuv420p
  build/all/x265.exe --input smoke_open.y4m --input-res 128x72 --fps 24 --frames 16 --bframes 4 --keyint 8 --min-keyint 8 --open-gop --output smoke_open.mp4
  probe_mp4 smoke_open smoke_open.mp4 pts_time,dts_time,flags
  assert_common_mp4 smoke_open 128 72 yuv420p 24/1 16 1/24000
  awk -F, 'NR == 1 { if (NF < 3 || $3 !~ /K/) exit 1 } END { if (NR != 16) exit 1 }' smoke_open_packets.csv
  awk -F, 'NF >= 3 && $1 != "N/A" && $2 != "N/A" { if (($1+0) > ($2+0)) diff=1 } END { if (!diff) exit 1 }' smoke_open_packets.csv
  awk -F, 'NF >= 3 && $3 != "N/A" { if (seen && ($3+0) < prev) exit 1; prev=$3+0; seen=1 } END { if (!seen) exit 1 }' smoke_open_frames.csv
  awk -F, 'NR == 1 { if (NF < 2 || $2 == "N/A") exit 1; if (($2+0) < -0.001 || ($2+0) > 0.05) exit 1 }' smoke_open_frames.csv
  awk -F, 'NR == 1 { if (NF < 1 || $1 != 1) exit 1 }' smoke_open_frames.csv
  awk -F, 'NR == 1 { if (NF < 3 || $2 == "N/A" || $3 == "N/A") exit 1; if (($3+0) < -0.09 || ($3+0) > 0.01) exit 1; if (($2+0) < ($3+0)) exit 1 }' smoke_open_frames.csv
  awk -F, 'NR > 1 && $2 != "N/A" && prev != "" { delta = ($2+0) - prev; if (delta < 0.03 || delta > 0.05) exit 1 } { if ($2 != "N/A") prev = $2+0 } END { if (NR < 2) exit 1 }' smoke_open_frames.csv
  awk -F, 'END { if (NR != 16) exit 1; if (NF < 2 || $2 == "N/A") exit 1; if (($2+0) < 0.55 || ($2+0) > 0.75) exit 1 }' smoke_open_frames.csv
  awk -F, '$3 ~ /K/ { kf++; if (kf == 2) { if ($1 == "N/A") exit 1; if (($1+0) < 0.30 || ($1+0) > 0.38) exit 1 } } END { if (kf < 2) exit 1 }' smoke_open_packets.csv
  assert_mp4_markers smoke_open.mp4 iso6 sgpd sbgp 'rap '
  assert_duration_window smoke_open 0.60 0.75
}

smoke_mp4_cra() {
  make_y4m smoke_cra.y4m 24 16 yuv420p
  build/all/x265.exe --input smoke_cra.y4m --input-res 128x72 --fps 24 --frames 16 --bframes 0 --keyint 1 --min-keyint 1 --cra-nal --output smoke_cra.mp4
  probe_mp4 smoke_cra smoke_cra.mp4 flags
  assert_common_mp4 smoke_cra 128 72 yuv420p 24/1 16 1/24000
  assert_mp4_markers smoke_cra.mp4 iso6 hvc1 hvcC
  awk -F, 'NR == 1 { if ($1 !~ /K/) exit 1 } END { if (NR != 16) exit 1 }' smoke_cra_packets.csv
  awk -F, 'NF >= 3 && $3 != "N/A" { if (seen && ($3+0) < prev) exit 1; prev=$3+0; seen=1 } END { if (!seen) exit 1 }' smoke_cra_frames.csv
  awk -F, 'NF >= 3 && $2 != "N/A" && $3 != "N/A" { if (($2+0) != ($3+0)) exit 1 } END { if (NR != 16) exit 1 }' smoke_cra_frames.csv
  awk -F, 'NR == 1 { if (NF < 3 || $1 != 1 || $2 == "N/A" || $3 == "N/A") exit 1; if (($2+0) < -0.001 || ($2+0) > 0.05) exit 1; if (($3+0) < -0.001 || ($3+0) > 0.05) exit 1 }' smoke_cra_frames.csv
  awk -F, '$1 == 1 { kf++ } END { if (kf != 16) exit 1 }' smoke_cra_frames.csv
  awk -F, 'NR > 1 && $2 != "N/A" && prev != "" { delta = ($2+0) - prev; if (delta < 0.03 || delta > 0.05) exit 1 } { if ($2 != "N/A") prev = $2+0 } END { if (NR < 2) exit 1 }' smoke_cra_frames.csv
  awk -F, 'END { if (NR != 16) exit 1; if (NF < 3 || $2 == "N/A" || $3 == "N/A") exit 1; if (($2+0) < 0.55 || ($2+0) > 0.75) exit 1; if (($3+0) < 0.55 || ($3+0) > 0.75) exit 1 }' smoke_cra_frames.csv
  assert_duration_window smoke_cra 0.60 0.75
  awk -F, 'BEGIN { first=""; last=""; step="" } $2 != "N/A" { curr = $2+0; if (first == "") first = curr; if (last != "" && step == "") step = curr - last; last = curr } END { if (first == "" || last == "" || step == "") exit 1; span = (last - first) + step; if (span < 0.60 || span > 0.75) exit 1 }' smoke_cra_frames.csv
}

smoke_mp4_single_frame() {
  make_y4m smoke_single.y4m 24 1 yuv420p
  build/all/x265.exe --input smoke_single.y4m --input-res 128x72 --fps 24 --frames 1 --bframes 0 --keyint 1 --min-keyint 1 --output smoke_single.mp4
  probe_mp4 smoke_single smoke_single.mp4 flags
  assert_common_mp4 smoke_single 128 72 yuv420p 24/1 1 1/24000
  assert_mp4_markers smoke_single.mp4 iso6 hvc1 hvcC
  assert_single_frame_mp4 smoke_single 0.05 0.02 0.08
}

smoke_mp4_frames_zero() {
  make_y4m smoke_zero.y4m 24 1 yuv420p
  build/all/x265.exe --input smoke_zero.y4m --input-res 128x72 --fps 24 --frames 0 --bframes 0 --keyint 1 --min-keyint 1 --output smoke_zero.mp4
  probe_mp4 smoke_zero smoke_zero.mp4 flags
  assert_common_mp4 smoke_zero 128 72 yuv420p 24/1 1 1/24000
  assert_mp4_markers smoke_zero.mp4 iso6 hvc1 hvcC
  assert_single_frame_mp4 smoke_zero 0.05 0.02 0.08
}

smoke_mp4_single_frame_frac() {
  make_y4m smoke_single_frac.y4m 24000/1001 1 yuv420p
  build/all/x265.exe --input smoke_single_frac.y4m --input-res 128x72 --fps 24000/1001 --frames 1 --bframes 0 --keyint 1 --min-keyint 1 --output smoke_single_frac.mp4
  probe_mp4 smoke_single_frac smoke_single_frac.mp4 flags
  assert_common_mp4 smoke_single_frac 128 72 yuv420p 24000/1001 1 1/24000
  assert_mp4_markers smoke_single_frac.mp4 iso6 hvc1 hvcC
  assert_single_frame_mp4 smoke_single_frac 0.06 0.03 0.06
}

smoke_mp4_vui() {
  make_y4m smoke_vui.y4m 24 4 yuv420p
  build/all/x265.exe --input smoke_vui.y4m --input-res 128x72 --fps 24 --frames 4 --bframes 0 --keyint 4 --min-keyint 4 --sar 4:3 --range limited --colorprim bt709 --transfer bt709 --colormatrix bt709 --output smoke_vui.mp4
  probe_mp4 smoke_vui smoke_vui.mp4 flags
  assert_common_mp4 smoke_vui 128 72 yuv420p 24/1 4 1/24000
  grep -q "sample_aspect_ratio=4:3" smoke_vui_stream.txt
  grep -q "display_aspect_ratio=64:27" smoke_vui_stream.txt
  grep -q "color_range=tv" smoke_vui_stream.txt
  grep -q "color_space=bt709" smoke_vui_stream.txt
  grep -q "color_transfer=bt709" smoke_vui_stream.txt
  grep -q "color_primaries=bt709" smoke_vui_stream.txt
  assert_mp4_markers smoke_vui.mp4 iso6 colr
  awk -F, 'NR == 1 { if ($1 !~ /K/) exit 1 } END { if (NR != 4) exit 1 }' smoke_vui_packets.csv
}

smoke_mp4_strict_cbr_fails() {
  ffmpeg -hide_banner -loglevel error -f lavfi -i testsrc2=size=128x72:rate=24 -frames:v 16 -pix_fmt yuv420p smoke_strict_cbr.y4m
  if build/all/x265.exe --input smoke_strict_cbr.y4m --input-res 128x72 --fps 24 --frames 16 --bitrate 300 --vbv-bufsize 300 --strict-cbr --hrd --output smoke_strict_cbr.mp4; then
    echo "strict-cbr MP4 encode unexpectedly succeeded"
    exit 1
  fi
  if [ -f smoke_strict_cbr.mp4 ] && [ -s smoke_strict_cbr.mp4 ]; then
    ffprobe -v error smoke_strict_cbr.mp4 >/dev/null 2>&1 && {
      echo "strict-cbr MP4 output should not be a valid playable file"
      exit 1
    }
  fi
}

smoke_mp4_frac() {
  trap 'status=$?; if [ $status -ne 0 ]; then echo "=== smoke frac diagnostics ==="; dump_mp4_diagnostics smoke_frac smoke_frac.mp4; fi; exit $status' EXIT
  make_y4m smoke_frac.y4m 24000/1001 24 yuv420p
  build/all/x265.exe --input smoke_frac.y4m --input-res 128x72 --fps 24000/1001 --frames 24 --bframes 4 --keyint 12 --min-keyint 12 --no-open-gop --output smoke_frac.mp4
  probe_mp4 smoke_frac smoke_frac.mp4 pts_time,dts_time,flags
  assert_common_mp4 smoke_frac 128 72 yuv420p 24000/1001 24 1/24000
  assert_mp4_markers smoke_frac.mp4 iso6 hvc1 hvcC
  awk -F, 'NR == 1 { if (NF < 3 || $3 !~ /K/) exit 1 } END { if (NR != 24) exit 1 }' smoke_frac_packets.csv
  awk -F, 'NF >= 3 && $1 != "N/A" && $2 != "N/A" { if (($1+0) > ($2+0)) diff=1 } END { if (!diff) exit 1 }' smoke_frac_packets.csv
  awk -F, '$3 ~ /K/ { kf++; if (kf == 2 && NR != 13) exit 1 } END { if (kf < 2) exit 1 }' smoke_frac_packets.csv
  awk -F, 'NR == 1 { if (NF < 1 || $1 != 1) exit 1 }' smoke_frac_frames.csv
  awk -F, 'NR == 1 { if (NF < 2 || $2 == "N/A") exit 1 }' smoke_frac_frames.csv
  awk -F, 'NR == 1 { if (($2+0) < -0.001 || ($2+0) > 0.06) exit 1 }' smoke_frac_frames.csv
  awk -F, 'NR > 1 && $2 != "N/A" && prev != "" { delta = ($2+0) - prev; if (delta < 0.03 || delta > 0.06) exit 1 } { if ($2 != "N/A") prev = $2+0 } END { if (NR < 2) exit 1 }' smoke_frac_frames.csv
  awk -F, 'NR == 1 { if (NF < 3 || $3 == "N/A") exit 1 }' smoke_frac_frames.csv
  awk -F, 'NR == 1 { if (($2+0) < ($3+0)) exit 1 }' smoke_frac_frames.csv
  awk -F, 'END { if (NR != 24) exit 1; if (NF < 2 || $2 == "N/A") exit 1; if (($2+0) < 0.90 || ($2+0) > 1.10) exit 1 }' smoke_frac_frames.csv
  assert_duration_window smoke_frac 0.95 1.10
}

smoke_mp4_b_pyramid() {
  trap 'status=$?; if [ $status -ne 0 ]; then echo "=== smoke bpyramid diagnostics ==="; dump_mp4_diagnostics smoke_bpyramid smoke_bpyramid.mp4; fi; exit $status' EXIT
  make_y4m smoke_bpyramid.y4m 24 16 yuv420p
  build/all/x265.exe --input smoke_bpyramid.y4m --input-res 128x72 --fps 24 --frames 16 --bframes 4 --b-pyramid --keyint 8 --min-keyint 8 --no-open-gop --output smoke_bpyramid.mp4
  probe_mp4 smoke_bpyramid smoke_bpyramid.mp4 pts_time,dts_time,flags
  assert_common_mp4 smoke_bpyramid 128 72 yuv420p 24/1 16 1/24000
  awk -F, 'NR == 1 { if (NF < 3 || $3 !~ /K/) exit 1 } END { if (NR != 16) exit 1 }' smoke_bpyramid_packets.csv
  awk -F, 'NF >= 3 && $1 != "N/A" && $2 != "N/A" { if (($1+0) > ($2+0)) diff=1 } END { if (!diff) exit 1 }' smoke_bpyramid_packets.csv
  awk -F, '$3 ~ /K/ { kf++; if (kf == 2 && NR != 9) exit 1 } END { if (kf < 2) exit 1 }' smoke_bpyramid_packets.csv
  awk -F, 'NR == 1 { if (NF < 1 || $1 != 1) exit 1 }' smoke_bpyramid_frames.csv
  awk -F, 'NR == 1 { if (NF < 2 || $2 == "N/A") exit 1 }' smoke_bpyramid_frames.csv
  awk -F, 'NR == 1 { if (($2+0) < -0.001 || ($2+0) > 0.06) exit 1 }' smoke_bpyramid_frames.csv
  awk -F, 'NR > 1 && $2 != "N/A" && prev != "" { delta = ($2+0) - prev; if (delta < 0.03 || delta > 0.05) exit 1 } { if ($2 != "N/A") prev = $2+0 } END { if (NR < 2) exit 1 }' smoke_bpyramid_frames.csv
  awk -F, 'END { if (NR != 16) exit 1; if (NF < 2 || $2 == "N/A") exit 1; if (($2+0) < 0.55 || ($2+0) > 0.75) exit 1 }' smoke_bpyramid_frames.csv
  assert_duration_window smoke_bpyramid 0.60 0.75
}

smoke_mp4_aud() {
  make_y4m smoke_aud.y4m 24 16 yuv420p
  build/all/x265.exe --input smoke_aud.y4m --input-res 128x72 --fps 24 --frames 16 --bframes 4 --keyint 8 --min-keyint 8 --aud --output smoke_aud.mp4
  probe_mp4 smoke_aud smoke_aud.mp4 pts_time,dts_time,flags
  assert_common_mp4 smoke_aud 128 72 yuv420p 24/1 16 1/24000
  awk -F, 'NR == 1 { if (NF < 3 || $3 !~ /K/) exit 1 } END { if (NR != 16) exit 1 }' smoke_aud_packets.csv
  awk -F, 'NF >= 3 && $1 != "N/A" && $2 != "N/A" { if (($1+0) > ($2+0)) diff=1 } END { if (!diff) exit 1 }' smoke_aud_packets.csv
  awk -F, 'NF >= 3 && $3 != "N/A" { if (seen && ($3+0) < prev) exit 1; prev=$3+0; seen=1 } END { if (!seen) exit 1 }' smoke_aud_frames.csv
  awk -F, 'NR == 1 { if (NF < 1 || $1 != 1) exit 1 }' smoke_aud_frames.csv
  awk -F, 'NR > 1 && $2 != "N/A" && prev != "" { delta = ($2+0) - prev; if (delta < 0.03 || delta > 0.05) exit 1 } { if ($2 != "N/A") prev = $2+0 } END { if (NR < 2) exit 1 }' smoke_aud_frames.csv
  awk -F, 'END { if (NR != 16) exit 1; if (NF < 2 || $2 == "N/A") exit 1; if (($2+0) < 0.55 || ($2+0) > 0.75) exit 1 }' smoke_aud_frames.csv
  awk -F, '$3 ~ /K/ { kf++; if (kf == 2) { if ($1 == "N/A") exit 1; if (($1+0) < 0.30 || ($1+0) > 0.38) exit 1 } } END { if (kf < 2) exit 1 }' smoke_aud_packets.csv
  assert_duration_window smoke_aud 0.60 0.75
}

smoke_mp4_eos_eob() {
  make_y4m smoke_eos.y4m 24 16 yuv420p
  build/all/x265.exe --input smoke_eos.y4m --input-res 128x72 --fps 24 --frames 16 --bframes 4 --keyint 8 --min-keyint 8 --eos --eob --output smoke_eos.mp4
  probe_mp4 smoke_eos smoke_eos.mp4 pts_time,dts_time,flags
  assert_common_mp4 smoke_eos 128 72 yuv420p 24/1 16 1/24000
  awk -F, 'NR == 1 { if (NF < 3 || $3 !~ /K/) exit 1 } END { if (NR != 16) exit 1 }' smoke_eos_packets.csv
  awk -F, 'NF >= 3 && $1 != "N/A" && $2 != "N/A" { if (($1+0) > ($2+0)) diff=1 } END { if (!diff) exit 1 }' smoke_eos_packets.csv
  awk -F, 'NF >= 3 && $3 != "N/A" { if (seen && ($3+0) < prev) exit 1; prev=$3+0; seen=1 } END { if (!seen) exit 1 }' smoke_eos_frames.csv
  awk -F, 'NR == 1 { if (NF < 1 || $1 != 1) exit 1 }' smoke_eos_frames.csv
  awk -F, 'NR > 1 && $2 != "N/A" && prev != "" { delta = ($2+0) - prev; if (delta < 0.03 || delta > 0.05) exit 1 } { if ($2 != "N/A") prev = $2+0 } END { if (NR < 2) exit 1 }' smoke_eos_frames.csv
  awk -F, 'END { if (NR != 16) exit 1; if (NF < 2 || $2 == "N/A") exit 1; if (($2+0) < 0.55 || ($2+0) > 0.75) exit 1 }' smoke_eos_frames.csv
  awk -F, '$3 ~ /K/ { kf++; if (kf == 2) { if ($1 == "N/A") exit 1; if (($1+0) < 0.30 || ($1+0) > 0.38) exit 1 } } END { if (kf < 2) exit 1 }' smoke_eos_packets.csv
  assert_duration_window smoke_eos 0.60 0.75
}

smoke_mp4_idr_recovery() {
  make_y4m smoke_recovery.y4m 24 16 yuv420p
  build/all/x265.exe --input smoke_recovery.y4m --input-res 128x72 --fps 24 --frames 16 --bframes 0 --keyint 8 --min-keyint 8 --no-open-gop --idr-recovery-sei --output smoke_recovery.mp4
  probe_mp4 smoke_recovery smoke_recovery.mp4 pts_time,dts_time,flags
  assert_common_mp4 smoke_recovery 128 72 yuv420p 24/1 16 1/24000
  assert_mp4_markers smoke_recovery.mp4 iso6 hvc1 hvcC
  awk -F, 'NR == 1 { if (NF < 3 || $3 !~ /K/) exit 1 } END { if (NR != 16) exit 1 }' smoke_recovery_packets.csv
  awk -F, 'NF >= 3 && $3 != "N/A" { if (seen && ($3+0) < prev) exit 1; prev=$3+0; seen=1 } END { if (!seen) exit 1 }' smoke_recovery_frames.csv
  awk -F, 'NF >= 3 && $2 != "N/A" && $3 != "N/A" { if (($2+0) != ($3+0)) exit 1 } END { if (NR != 16) exit 1 }' smoke_recovery_frames.csv
  awk -F, 'NR == 1 { if (NF < 3 || $1 != 1 || $2 == "N/A" || $3 == "N/A") exit 1; if (($2+0) < -0.001 || ($3+0) < -0.001) exit 1; if (($2+0) > 0.05 || ($3+0) > 0.05) exit 1 }' smoke_recovery_frames.csv
  awk -F, '$3 ~ /K/ { kf++; if (kf == 2) { if ($1 == "N/A") exit 1; if (($1+0) < 0.30 || ($1+0) > 0.38) exit 1 } } END { if (kf < 2) exit 1 }' smoke_recovery_packets.csv
  awk -F, 'NR > 1 && $2 != "N/A" && prev != "" { delta = ($2+0) - prev; if (delta < 0.03 || delta > 0.05) exit 1 } { if ($2 != "N/A") prev = $2+0 } END { if (NR < 2) exit 1 }' smoke_recovery_frames.csv
  awk -F, 'END { if (NR != 16) exit 1; if (NF < 2 || $2 == "N/A") exit 1; if (($2+0) < 0.60 || ($2+0) > 0.75) exit 1 }' smoke_recovery_frames.csv
  assert_duration_window smoke_recovery 0.60 0.75
}

main() {
  case "${1:-}" in
    smoke)
      smoke_mp4
      ;;
    open-gop)
      smoke_mp4_open_gop
      ;;
    cra)
      smoke_mp4_cra
      ;;
    single-frame)
      smoke_mp4_single_frame
      ;;
    frames-zero)
      smoke_mp4_frames_zero
      ;;
    single-frame-24000-1001)
      smoke_mp4_single_frame_frac
      ;;
    vui)
      smoke_mp4_vui
      ;;
    strict-cbr-fails)
      smoke_mp4_strict_cbr_fails
      ;;
    frac-24000-1001)
      smoke_mp4_frac
      ;;
    b-pyramid)
      smoke_mp4_b_pyramid
      ;;
    aud)
      smoke_mp4_aud
      ;;
    eos-eob)
      smoke_mp4_eos_eob
      ;;
    idr-recovery)
      smoke_mp4_idr_recovery
      ;;
    *)
      echo "unknown MP4 smoke suite target: ${1:-<empty>}" >&2
      exit 2
      ;;
  esac
}

main "$@"
