#!/usr/bin/env bash
set -euo pipefail

make_runtime_y4m() {
  local output="$1"
  local width="$2"
  local height="$3"
  local rate="$4"
  local frames="$5"
  local pix_fmt="$6"
  ffmpeg -hide_banner -loglevel error -y -f lavfi -i "testsrc2=size=${width}x${height}:rate=${rate}" -frames:v "$frames" -pix_fmt "$pix_fmt" "$output"
}

smoke_raw() {
  make_runtime_y4m smoke_raw.y4m 160 90 24 12 yuv420p
  build/all/x265.exe --input smoke_raw.y4m --input-res 160x90 --fps 24 --frames 12 --output smoke_raw.hevc
  test -s smoke_raw.hevc
  ffprobe -v error -show_entries stream=codec_name,codec_type,width,height -select_streams v:0 -of default=noprint_wrappers=1 smoke_raw.hevc > smoke_raw_probe.txt
  grep -q "codec_name=hevc" smoke_raw_probe.txt
  grep -q "codec_type=video" smoke_raw_probe.txt
  grep -q "width=160" smoke_raw_probe.txt
  grep -q "height=90" smoke_raw_probe.txt
}

smoke_cli_long_input() {
  long_input="$(python -c "print('a' * 1100)")"
  if build/all/x265.exe --input "$long_input" --input-res 96x96 --fps 1 --frames 1 --output smoke_cli_long_input.hevc > smoke_cli_long_input.log 2>&1; then
    echo "CLI long --input smoke unexpectedly succeeded"
    exit 1
  fi
  grep -Fq 'Input filename exceeds supported length' smoke_cli_long_input.log
  if build/all/x265.exe "$long_input" -o smoke_cli_long_positional.hevc --input-res 96x96 --fps 1 --frames 1 > smoke_cli_long_positional.log 2>&1; then
    echo "CLI long positional-input smoke unexpectedly succeeded"
    exit 1
  fi
  grep -Fq 'Input filename exceeds supported length' smoke_cli_long_positional.log
}

smoke_mkv() {
  make_runtime_y4m smoke_mkv.y4m 160 90 24 12 yuv420p
  build/all/x265.exe --input smoke_mkv.y4m --input-res 160x90 --fps 24 --frames 12 --output smoke_mkv.mkv
  test -s smoke_mkv.mkv
  ffprobe -v error -show_entries format=format_name,duration -of default=noprint_wrappers=1 smoke_mkv.mkv > smoke_mkv_format.txt
  ffprobe -v error -show_entries stream=codec_name,codec_type,width,height -select_streams v:0 -of default=noprint_wrappers=1 smoke_mkv.mkv > smoke_mkv_stream.txt
  ffprobe -v error -count_frames -select_streams v:0 -show_entries stream=nb_read_frames -of default=noprint_wrappers=1 smoke_mkv.mkv > smoke_mkv_count.txt
  grep -q "format_name=matroska,webm" smoke_mkv_format.txt
  grep -q "codec_name=hevc" smoke_mkv_stream.txt
  grep -q "codec_type=video" smoke_mkv_stream.txt
  grep -q "width=160" smoke_mkv_stream.txt
  grep -q "height=90" smoke_mkv_stream.txt
  grep -q "nb_read_frames=12" smoke_mkv_count.txt
}

smoke_lavf() {
  ffmpeg -hide_banner -loglevel error -f lavfi -i testsrc2=size=160x90:rate=24 -frames:v 12 -pix_fmt yuv420p -c:v ffv1 smoke_lavf_input.mkv
  build/all/x265.exe --input smoke_lavf_input.mkv --frames 12 --output smoke_lavf_output.hevc 2>&1 | tee smoke_lavf_log.txt
  test -s smoke_lavf_output.hevc
  grep -Fq "lavf" smoke_lavf_log.txt
  ffprobe -v error -show_entries stream=codec_name,codec_type,width,height -select_streams v:0 -of default=noprint_wrappers=1 smoke_lavf_output.hevc > smoke_lavf_probe.txt
  ffprobe -v error -count_frames -select_streams v:0 -show_entries stream=nb_read_frames -of default=noprint_wrappers=1 smoke_lavf_output.hevc > smoke_lavf_count.txt
  grep -q "codec_name=hevc" smoke_lavf_probe.txt
  grep -q "codec_type=video" smoke_lavf_probe.txt
  grep -q "width=160" smoke_lavf_probe.txt
  grep -q "height=90" smoke_lavf_probe.txt
  grep -q "nb_read_frames=12" smoke_lavf_count.txt
}

smoke_threaded_me() {
  make_runtime_y4m smoke_threaded_me.y4m 160 90 24 16 yuv420p
  build/all/x265.exe --input smoke_threaded_me.y4m --input-res 160x90 --fps 24 --frames 16 --preset medium --threaded-me --pools 32 --frame-threads 1 --no-wpp --no-progress --output smoke_threaded_me.hevc 2>&1 | tee smoke_threaded_me_log.txt
  test -s smoke_threaded_me.hevc
  grep -Fq 'frame threads / pool features       : 1 / threaded-me' smoke_threaded_me_log.txt
  ! grep -Fq 'disabling --threaded-me' smoke_threaded_me_log.txt
  ffprobe -v error -count_frames -select_streams v:0 -show_entries stream=nb_read_frames -of default=noprint_wrappers=1 smoke_threaded_me.hevc > smoke_threaded_me_count.txt
  grep -q 'nb_read_frames=16' smoke_threaded_me_count.txt
}

smoke_threaded_me_stress() {
  make_runtime_y4m smoke_threaded_me_stress.y4m 160 90 24 2 yuv420p
  for iteration in $(seq 1 12); do
    output="smoke_threaded_me_stress_${iteration}.hevc"
    log="smoke_threaded_me_stress_${iteration}.log"
    count="smoke_threaded_me_stress_${iteration}_count.txt"
    build/all/x265.exe --input smoke_threaded_me_stress.y4m --input-res 160x90 --fps 24 --frames 2 --preset medium --threaded-me --pools 32 --frame-threads 1 --no-wpp --no-progress --output "$output" 2>&1 | tee "$log"
    test -s "$output"
    grep -Fq 'frame threads / pool features       : 1 / threaded-me' "$log"
    ! grep -Fq 'disabling --threaded-me' "$log"
    ffprobe -v error -count_frames -select_streams v:0 -show_entries stream=nb_read_frames -of default=noprint_wrappers=1 "$output" > "$count"
    grep -q 'nb_read_frames=2' "$count"
  done
}

smoke_qpfile() {
  cat > smoke_qpfile.txt <<'EOF'
0 I 60

# keep qpfile parser moving across ignored lines
3 P 24
6 B 26
9 K 20
EOF
  make_runtime_y4m smoke_qpfile.y4m 160 90 24 12 yuv420p
  build/all/x265.exe --input smoke_qpfile.y4m --input-res 160x90 --fps 24 --frames 12 --qpmax 69 --no-scenecut --keyint 250 --min-keyint 250 --qpfile smoke_qpfile.txt --output smoke_qpfile.hevc
  test -s smoke_qpfile.hevc
  ffprobe -v error -count_frames -select_streams v:0 -show_entries stream=nb_read_frames -of default=noprint_wrappers=1 smoke_qpfile.hevc > smoke_qpfile_count.txt
  grep -q "nb_read_frames=12" smoke_qpfile_count.txt
  ffprobe -v error -select_streams v:0 -show_entries frame=pict_type -of default=noprint_wrappers=1:nokey=1 smoke_qpfile.hevc > smoke_qpfile_types.txt
  test "$(grep -c '^I$' smoke_qpfile_types.txt)" -eq 2
}

smoke_qpfile_oversized() {
  make_runtime_y4m smoke_qpfile.y4m 160 90 24 12 yuv420p
  python - <<'PY'
from pathlib import Path
Path('smoke_qpfile_longline.txt').write_text('0 I 60\n1 P ' + ('2' * 5000) + '\n', encoding='utf-8')
PY
  if build/all/x265.exe --input smoke_qpfile.y4m --input-res 160x90 --fps 24 --frames 2 --qpmax 69 --no-scenecut --keyint 250 --min-keyint 250 --qpfile smoke_qpfile_longline.txt --output smoke_qpfile_longline.hevc > smoke_qpfile_longline.log 2>&1; then
    echo "QPFile oversized-line smoke unexpectedly succeeded"
    exit 1
  fi
  grep -Fq 'QP file contains a line exceeding supported length' smoke_qpfile_longline.log
  grep -Fq "can't parse qpfile for frame 1 in x265" smoke_qpfile_longline.log
}

smoke_nalu_file() {
  make_runtime_y4m smoke_nalu.y4m 96 64 24 3 yuv420p
  build/all/x265.exe --input smoke_nalu.y4m --input-res 96x64 --fps 24 --frames 2 --no-info --hash 0 --output smoke_nalu_base.hevc > smoke_nalu_base.log 2>&1
  test -s smoke_nalu_base.hevc
  python - <<'PY'
from pathlib import Path
Path('smoke_nalu_future.txt').write_text('1 PREFIX 39/5 ' + ('A' * 800) + '\n', encoding='utf-8')
PY
  build/all/x265.exe --input smoke_nalu.y4m --input-res 96x64 --fps 24 --frames 2 --no-info --hash 0 --nalu-file smoke_nalu_future.txt --output smoke_nalu_future.hevc > smoke_nalu_future.log 2>&1
  test -s smoke_nalu_future.hevc
  test "$(wc -c < smoke_nalu_future.hevc)" -gt "$(wc -c < smoke_nalu_base.hevc)"
  python - <<'PY'
from pathlib import Path
Path('smoke_nalu_long.txt').write_text('0 PREFIX 39/5 ' + ('A' * 5000) + '\n', encoding='utf-8')
PY
  build/all/x265.exe --input smoke_nalu.y4m --input-res 96x64 --fps 24 --frames 2 --no-info --hash 0 --nalu-file smoke_nalu_long.txt --output smoke_nalu_long.hevc > smoke_nalu_long.log 2>&1
  test -s smoke_nalu_long.hevc
  grep -Fq 'User SEI file contains a line exceeding supported length; skipping' smoke_nalu_long.log
  test "$(wc -c < smoke_nalu_long.hevc)" -eq "$(wc -c < smoke_nalu_base.hevc)"
}

smoke_output_depth_invalid() {
  if build/all/x265.exe --output-depth 9 --help > smoke_output_depth_invalid.log 2>&1; then
    echo "Output-depth invalid smoke unexpectedly succeeded"
    exit 1
  fi
  grep -Fq 'invalid argument: output-depth = 9' smoke_output_depth_invalid.log
  ! grep -Fq 'falling back to default bit-depth' smoke_output_depth_invalid.log
}

smoke_chunk_negative() {
  if build/all/x265.exe --chunk-start -1 --help > smoke_chunk_start_negative.log 2>&1; then
    echo "Chunk-start negative smoke unexpectedly succeeded"
    exit 1
  fi
  grep -Fq 'invalid argument: chunk-start = -1' smoke_chunk_start_negative.log
  if build/all/x265.exe --chunk-end -1 --help > smoke_chunk_end_negative.log 2>&1; then
    echo "Chunk-end negative smoke unexpectedly succeeded"
    exit 1
  fi
  grep -Fq 'invalid argument: chunk-end = -1' smoke_chunk_end_negative.log
}

smoke_zonefile() {
  cat > smoke_zonefile.txt <<'EOF'
0 --bitrate 350
6 --bitrate 500
EOF
  make_runtime_y4m smoke_zonefile.y4m 160 90 24 12 yuv420p
  build/all/x265.exe --input smoke_zonefile.y4m --input-res 160x90 --fps 24 --frames 12 --bitrate 400 --zonefile smoke_zonefile.txt --output smoke_zonefile.hevc
  test -s smoke_zonefile.hevc
  ffprobe -v error -count_frames -select_streams v:0 -show_entries stream=nb_read_frames -of default=noprint_wrappers=1 smoke_zonefile.hevc > smoke_zonefile_count.txt
  grep -q "nb_read_frames=12" smoke_zonefile_count.txt
}

smoke_zonefile_oversized() {
  make_runtime_y4m smoke_zonefile.y4m 160 90 24 12 yuv420p
  python - <<'PY'
from pathlib import Path
tokens = ' '.join(f'--bitrate {100 + i}' for i in range(260))
Path('smoke_zonefile_oversized.txt').write_text('0 ' + tokens + '\n', encoding='utf-8')
PY
  if build/all/x265.exe --input smoke_zonefile.y4m --input-res 160x90 --fps 24 --frames 12 --bitrate 400 --zonefile smoke_zonefile_oversized.txt --output smoke_zonefile_oversized.hevc > smoke_zonefile_oversized.log 2>&1; then
    echo "Zonefile oversized-argument smoke unexpectedly succeeded"
    exit 1
  fi
  grep -Fq 'Zone file entry exceeds supported argument count' smoke_zonefile_oversized.log
  python - <<'PY'
from pathlib import Path
Path('smoke_zonefile_longline.txt').write_text('0 --bitrate 100 ' + ('A' * 5000) + '\n', encoding='utf-8')
PY
  if build/all/x265.exe --input smoke_zonefile.y4m --input-res 160x90 --fps 24 --frames 12 --bitrate 400 --zonefile smoke_zonefile_longline.txt --output smoke_zonefile_longline.hevc > smoke_zonefile_longline.log 2>&1; then
    echo "Zonefile oversized-line smoke unexpectedly succeeded"
    exit 1
  fi
  grep -Fq 'Zone file line 1 exceeds supported length' smoke_zonefile_longline.log
}

smoke_recon() {
  make_runtime_y4m smoke_recon.y4m 160 90 24 12 yuv420p
  build/all/x265.exe --input smoke_recon.y4m --input-res 160x90 --fps 24 --frames 12 --recon smoke_recon_out.y4m --output smoke_recon.hevc
  test -s smoke_recon.hevc
  test -s smoke_recon_out.y4m
  grep -q '^YUV4MPEG2 ' smoke_recon_out.y4m
}

smoke_analysis_save_load() {
  make_runtime_y4m smoke_analysis.y4m 128 72 24 4 yuv420p
  build/all/x265.exe --input smoke_analysis.y4m --input-res 128x72 --fps 24 --frames 4 --preset medium --analysis-save smoke_analysis.dat --analysis-save-reuse-level 10 --bitrate 800 --no-progress --output smoke_analysis_save.hevc 2>&1 | tee smoke_analysis_save.log
  build/all/x265.exe --input smoke_analysis.y4m --input-res 128x72 --fps 24 --frames 4 --preset medium --analysis-load smoke_analysis.dat --analysis-load-reuse-level 10 --bitrate 800 --no-progress --output smoke_analysis_load.hevc 2>&1 | tee smoke_analysis_load.log
  test -s smoke_analysis.dat
  test -s smoke_analysis_save.hevc
  test -s smoke_analysis_load.hevc
  grep -Fq 'encoded 4 frames' smoke_analysis_save.log
  grep -Fq 'encoded 4 frames' smoke_analysis_load.log
  ffprobe -v error -count_frames -select_streams v:0 -show_entries stream=nb_read_frames -of default=noprint_wrappers=1 smoke_analysis_save.hevc > smoke_analysis_save_count.txt
  ffprobe -v error -count_frames -select_streams v:0 -show_entries stream=nb_read_frames -of default=noprint_wrappers=1 smoke_analysis_load.hevc > smoke_analysis_load_count.txt
  grep -q 'nb_read_frames=4' smoke_analysis_save_count.txt
  grep -q 'nb_read_frames=4' smoke_analysis_load_count.txt
}

smoke_2pass_stats() {
  make_runtime_y4m smoke_2pass_stats.y4m 160 90 24 8 yuv420p
  make_runtime_y4m smoke_2pass_stats_mismatch.y4m 128 72 24 8 yuv420p
  build/all/x265.exe --input smoke_2pass_stats.y4m --input-res 160x90 --fps 24 --frames 8 --bitrate 500 --pass 1 --stats smoke_2pass_stats.stats --no-progress --output smoke_2pass_stats_pass1.hevc 2>&1 | tee smoke_2pass_stats_pass1.log
  build/all/x265.exe --input smoke_2pass_stats.y4m --input-res 160x90 --fps 24 --frames 8 --bitrate 500 --pass 2 --stats smoke_2pass_stats.stats --no-progress --output smoke_2pass_stats_pass2.hevc 2>&1 | tee smoke_2pass_stats_pass2.log
  test -s smoke_2pass_stats.stats
  test -s smoke_2pass_stats_pass1.hevc
  test -s smoke_2pass_stats_pass2.hevc
  grep -Fq ' input-res=160x90' smoke_2pass_stats.stats
  grep -Fq ' conformance-window-offsets right=0 bottom=0' smoke_2pass_stats.stats
  grep -Fq 'encoded 8 frames' smoke_2pass_stats_pass1.log
  grep -Fq 'encoded 8 frames' smoke_2pass_stats_pass2.log
  ffprobe -v error -count_frames -select_streams v:0 -show_entries stream=nb_read_frames -of default=noprint_wrappers=1 smoke_2pass_stats_pass2.hevc > smoke_2pass_stats_pass2_count.txt
  grep -q 'nb_read_frames=8' smoke_2pass_stats_pass2_count.txt
  if build/all/x265.exe --input smoke_2pass_stats_mismatch.y4m --input-res 128x72 --fps 24 --frames 8 --bitrate 500 --pass 2 --stats smoke_2pass_stats.stats --no-progress --output smoke_2pass_stats_mismatch.hevc > smoke_2pass_stats_mismatch.log 2>&1; then
    echo "2pass stats mismatch smoke unexpectedly succeeded"
    exit 1
  fi
  grep -Fq 'input-res mismatch with 1st pass (128 x 72 vs 160 x 90)' smoke_2pass_stats_mismatch.log
}

smoke_abr_ladder() {
  ffmpeg -hide_banner -loglevel error -y -f lavfi -i "testsrc2=size=64x36:rate=24" -frames:v 4 -pix_fmt yuv420p10le -f rawvideo smoke_abr_ladder.yuv
  cat > smoke_abr_ladder.txt <<'EOF'
[base:0:nil] --input smoke_abr_ladder.yuv --input-res 64x36 --fps 24 --frames 4 --input-csp i420 --input-depth 10 --ctu 16 --preset medium --bitrate 400 --no-progress -o smoke_abr_base.hevc
[scaled:10:base] --input smoke_abr_ladder.yuv --input-res 128x72 --fps 24 --frames 4 --input-csp i420 --input-depth 10 --ctu 16 --preset medium --bitrate 700 --no-progress -o smoke_abr_scaled.hevc
EOF
  build/all/x265.exe --abr-ladder smoke_abr_ladder.txt 2>&1 | tee smoke_abr_ladder.log
  test -s smoke_abr_base.hevc
  test -s smoke_abr_scaled.hevc
  test "$(grep -Fc 'encoded 4 frames' smoke_abr_ladder.log)" -eq 2
  ffprobe -v error -count_frames -select_streams v:0 -show_entries stream=nb_read_frames -of default=noprint_wrappers=1 smoke_abr_base.hevc > smoke_abr_base_count.txt
  ffprobe -v error -count_frames -select_streams v:0 -show_entries stream=nb_read_frames -of default=noprint_wrappers=1 smoke_abr_scaled.hevc > smoke_abr_scaled_count.txt
  ffprobe -v error -show_entries stream=width,height -select_streams v:0 -of default=noprint_wrappers=1 smoke_abr_base.hevc > smoke_abr_base_probe.txt
  ffprobe -v error -show_entries stream=width,height -select_streams v:0 -of default=noprint_wrappers=1 smoke_abr_scaled.hevc > smoke_abr_scaled_probe.txt
  grep -q 'nb_read_frames=4' smoke_abr_base_count.txt
  grep -q 'nb_read_frames=4' smoke_abr_scaled_count.txt
  grep -q 'width=64' smoke_abr_base_probe.txt
  grep -q 'height=36' smoke_abr_base_probe.txt
  grep -q 'width=128' smoke_abr_scaled_probe.txt
  grep -q 'height=72' smoke_abr_scaled_probe.txt
}

smoke_video_signal_type_preset_oversized() {
  make_runtime_y4m smoke_recon.y4m 160 90 24 1 yuv420p
  long_vst="$(python -c "print('A' * 200 + ':P3D65x1000n0005')")"
  if build/all/x265.exe --input smoke_recon.y4m --input-res 160x90 --fps 24 --frames 1 --video-signal-type-preset "$long_vst" --output smoke_vst_oversized.hevc > smoke_vst_oversized.log 2>&1; then
    echo "Video-signal-type-preset oversized smoke unexpectedly succeeded"
    exit 1
  fi
  grep -Fq 'Incorrect system-id, aborting' smoke_vst_oversized.log
}

smoke_gop_output() {
  trap 'status=$?; if [ $status -ne 0 ]; then echo "=== smoke gop diagnostics ==="; for f in smoke_gop.gop smoke_gop.options smoke_gop.headers smoke_gop_data_files.txt smoke_gop_mux_format.txt smoke_gop_mux_stream.txt smoke_gop_mux_count.txt; do if [ -f "$f" ]; then echo "--- $f ---"; cat "$f"; fi; done; fi; exit $status' EXIT
  make_runtime_y4m smoke_gop.y4m 128 72 24 16 yuv420p
  build/all/x265.exe --input smoke_gop.y4m --input-res 128x72 --fps 24 --frames 16 --bframes 0 --keyint 8 --min-keyint 8 --no-open-gop --output smoke_gop.gop
  test -s smoke_gop.gop
  test -s smoke_gop.options
  test -s smoke_gop.headers
  test -s smoke_gop-000000.hevc-gop-data
  test -s smoke_gop-000008.hevc-gop-data
  printf '%s\n' smoke_gop-*.hevc-gop-data > smoke_gop_data_files.txt
  grep -Fxq 'smoke_gop-000000.hevc-gop-data' smoke_gop_data_files.txt
  grep -Fxq 'smoke_gop-000008.hevc-gop-data' smoke_gop_data_files.txt
  test "$(wc -l < smoke_gop_data_files.txt)" -eq 2
  grep -Fxq '#options smoke_gop.options' smoke_gop.gop
  test "$(grep -Fxc '#options smoke_gop.options' smoke_gop.gop)" -eq 1
  grep -Fxq '#headers smoke_gop.headers' smoke_gop.gop
  grep -Fxq 'smoke_gop-000000.hevc-gop-data' smoke_gop.gop
  grep -Fxq 'smoke_gop-000008.hevc-gop-data' smoke_gop.gop
  grep -Fxq 'b-frames 0' smoke_gop.options
  grep -Fxq 'b-pyramid 0' smoke_gop.options
  grep -Fxq 'output-fps-num 24000' smoke_gop.options
  grep -Fxq 'output-fps-den 1000' smoke_gop.options
  grep -Fxq 'source-width 128' smoke_gop.options
  grep -Fxq 'source-height 72' smoke_gop.options
  grep -Fxq 'sar-width 1' smoke_gop.options
  grep -Fxq 'sar-height 1' smoke_gop.options
  gop_muxer.exe smoke_gop.gop
  test -s smoke_gop.mp4
  ffprobe -v error -show_entries format=format_name,duration -of default=noprint_wrappers=1 smoke_gop.mp4 > smoke_gop_mux_format.txt
  ffprobe -v error -show_streams -select_streams v:0 smoke_gop.mp4 > smoke_gop_mux_stream.txt
  ffprobe -v error -count_frames -select_streams v:0 -show_entries stream=nb_read_frames -of default=noprint_wrappers=1 smoke_gop.mp4 > smoke_gop_mux_count.txt
  grep -q 'format_name=mov,mp4,m4a,3gp,3g2,mj2' smoke_gop_mux_format.txt
  grep -q 'codec_name=hevc' smoke_gop_mux_stream.txt
  grep -q 'codec_type=video' smoke_gop_mux_stream.txt
  grep -q 'width=128' smoke_gop_mux_stream.txt
  grep -q 'height=72' smoke_gop_mux_stream.txt
  awk -F= '/^extradata_size=/{ if (($2+0) > 0) found=1 } END { if (!found) exit 1 }' smoke_gop_mux_stream.txt
  grep -q 'nb_read_frames=16' smoke_gop_mux_count.txt
}

run_runtime_smoke_target() {
  local target="$1"
  case "$target" in
    raw)
      smoke_raw
      ;;
    cli-long-input)
      smoke_cli_long_input
      ;;
    mkv)
      smoke_mkv
      ;;
    lavf)
      smoke_lavf
      ;;
    threaded-me)
      smoke_threaded_me
      ;;
    threaded-me-stress)
      smoke_threaded_me_stress
      ;;
    qpfile)
      smoke_qpfile
      ;;
    nalu-file)
      smoke_nalu_file
      ;;
    output-depth-invalid)
      smoke_output_depth_invalid
      ;;
    chunk-negative)
      smoke_chunk_negative
      ;;
    qpfile-oversized)
      smoke_qpfile_oversized
      ;;
    zonefile)
      smoke_zonefile
      ;;
    zonefile-oversized)
      smoke_zonefile_oversized
      ;;
    recon)
      smoke_recon
      ;;
    analysis-save-load)
      smoke_analysis_save_load
      ;;
    2pass-stats)
      smoke_2pass_stats
      ;;
    abr-ladder)
      smoke_abr_ladder
      ;;
    video-signal-type-preset-oversized)
      smoke_video_signal_type_preset_oversized
      ;;
    gop-output)
      smoke_gop_output
      ;;
    *)
      echo "unknown runtime smoke suite target: ${target}" >&2
      exit 2
      ;;
  esac
}

run_runtime_smoke_targets() {
  local target
  for target in "$@"; do
    echo "=== Running runtime smoke: ${target} ==="
    run_runtime_smoke_target "$target"
  done
}

main() {
  case "${1:-}" in
    '')
      echo "missing runtime smoke suite target" >&2
      exit 2
      ;;
    all)
      run_runtime_smoke_targets raw cli-long-input mkv lavf threaded-me threaded-me-stress qpfile nalu-file output-depth-invalid chunk-negative qpfile-oversized zonefile zonefile-oversized recon analysis-save-load 2pass-stats abr-ladder video-signal-type-preset-oversized gop-output
      ;;
    *)
      run_runtime_smoke_targets "$@"
      ;;
  esac
}

main "$@"
