#!/usr/bin/env bash

make_y4m() {
  local output="$1"
  local rate="$2"
  local frames="$3"
  local pix_fmt="$4"
  ffmpeg -hide_banner -loglevel error -f lavfi -i "testsrc2=size=128x72:rate=${rate}" -frames:v "$frames" -pix_fmt "$pix_fmt" "$output"
}

probe_mp4() {
  local prefix="$1"
  local mp4="$2"
  local packet_entries="$3"
  ffprobe -v error -show_streams -select_streams v:0 "$mp4" > "${prefix}_stream.txt"
  ffprobe -v error -show_entries stream=time_base,r_frame_rate,avg_frame_rate,duration,nal_length_size -select_streams v:0 -of default=noprint_wrappers=1 "$mp4" > "${prefix}_timing.txt"
  ffprobe -v error -show_entries format=format_name,duration -of default=noprint_wrappers=1 "$mp4" > "${prefix}_format.txt"
  ffprobe -v error -count_frames -select_streams v:0 -show_entries stream=nb_read_frames -of default=noprint_wrappers=1 "$mp4" > "${prefix}_count.txt"
  ffprobe -v error -show_packets -select_streams v:0 -show_entries "packet=${packet_entries}" -of csv=p=0 "$mp4" > "${prefix}_packets.csv"
  ffprobe -v error -select_streams v:0 -show_entries frame=pts_time,pkt_dts_time,pkt_duration_time,key_frame -of csv=p=0 "$mp4" > "${prefix}_frames.csv"
}

assert_common_mp4() {
  local prefix="$1"
  local width="$2"
  local height="$3"
  local pix_fmt="$4"
  local fps="$5"
  local frames="$6"
  local time_base="$7"
  grep -q "format_name=mov,mp4,m4a,3gp,3g2,mj2" "${prefix}_format.txt"
  grep -q "codec_name=hevc" "${prefix}_stream.txt"
  grep -q "codec_tag_string=hvc1" "${prefix}_stream.txt"
  grep -q "codec_type=video" "${prefix}_stream.txt"
  grep -q "width=${width}" "${prefix}_stream.txt"
  grep -q "height=${height}" "${prefix}_stream.txt"
  grep -q "pix_fmt=${pix_fmt}" "${prefix}_stream.txt"
  awk -F= '/^extradata_size=/{ if (($2+0) > 0) found=1 } END { if (!found) exit 1 }' "${prefix}_stream.txt"
  grep -q "time_base=${time_base}" "${prefix}_timing.txt"
  if grep -q '^nal_length_size=' "${prefix}_timing.txt"; then grep -q "nal_length_size=4" "${prefix}_timing.txt"; fi
  grep -q "r_frame_rate=${fps}" "${prefix}_timing.txt"
  grep -q "avg_frame_rate=${fps}" "${prefix}_timing.txt"
  grep -q "nb_read_frames=${frames}" "${prefix}_count.txt"
  test -s "${prefix}_timing.txt"
  test -s "${prefix}_format.txt"
  test -s "${prefix}_count.txt"
  test -s "${prefix}_packets.csv"
  test -s "${prefix}_frames.csv"
}

dump_mp4_diagnostics() {
  local prefix="$1"
  local mp4="$2"
  for f in "${prefix}_format.txt" "${prefix}_stream.txt" "${prefix}_timing.txt" "${prefix}_count.txt" "${prefix}_packets.csv" "${prefix}_frames.csv"; do
    if [ -f "$f" ]; then
      echo "--- $f ---"
      cat "$f"
    fi
  done
  if [ -f "$mp4" ]; then
    echo "--- ${mp4} size ---"
    wc -c "$mp4"
    echo "--- ${mp4} markers ---"
    python - "$mp4" <<'PY'
from pathlib import Path
import sys
data = Path(sys.argv[1]).read_bytes()
for marker in (b'ftyp', b'hvc1', b'hvcC', b'colr', b'sgpd', b'sbgp', b'rap '):
    print(f'{marker.decode("ascii")}: {data.find(marker)}')
PY
  fi
}

assert_mp4_markers() {
  local mp4="$1"
  shift
  python - "$mp4" "$@" <<'PY'
from pathlib import Path
import sys
data = Path(sys.argv[1]).read_bytes()
for marker in (arg.encode('ascii') for arg in sys.argv[2:]):
    if marker not in data:
        raise SystemExit(f'missing MP4 marker: {marker!r}')
PY
}

assert_duration_window() {
  local prefix="$1"
  local min_duration="$2"
  local max_duration="$3"
  awk -F= -v min="$min_duration" -v max="$max_duration" '/^duration=/{ d=$2+0 } END { if (d < min || d > max) exit 1 }' "${prefix}_format.txt"
  awk -F= -v min="$min_duration" -v max="$max_duration" '/^duration=/{ d=$2+0 } END { if (d < min || d > max) exit 1 }' "${prefix}_timing.txt"
}

assert_single_frame_mp4() {
  local prefix="$1"
  local max_timestamp="$2"
  local min_duration="$3"
  local max_duration="$4"
  awk -F, 'NR == 1 { if ($1 !~ /K/) exit 1 } END { if (NR != 1) exit 1 }' "${prefix}_packets.csv"
  awk -F, 'NR == 1 { if (NF < 1 || $1 != 1) exit 1 } END { if (NR != 1) exit 1 }' "${prefix}_frames.csv"
  awk -F, -v max="$max_timestamp" 'NR == 1 { if (NF < 3 || $2 == "N/A" || $3 == "N/A") exit 1; if (($2+0) != ($3+0)) exit 1; if (($2+0) < -0.001 || ($2+0) > max) exit 1 } END { if (NR != 1) exit 1 }' "${prefix}_frames.csv"
  assert_duration_window "$prefix" "$min_duration" "$max_duration"
}
