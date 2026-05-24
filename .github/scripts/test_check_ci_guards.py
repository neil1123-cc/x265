#!/usr/bin/env python3
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

CHECKER = Path(__file__).with_name('check_ci_guards.py')
BASH_CANDIDATES = (
    Path('D:/msys64/usr/bin/bash.exe'),
    Path('C:/msys64/usr/bin/bash.exe'),
)


def preferred_bash():
    for candidate in BASH_CANDIDATES:
        if candidate.exists():
            return str(candidate)
    return None

BUILD_YML = '''
name: Build
on: push
jobs:
  validate-deps-cache-suffix:
    runs-on: ubuntu-latest
    steps:
      - name: Check CI guardrails
        shell: bash
        run: |
          set -euo pipefail
          python .github/scripts/check_ci_guards.py
          python .github/scripts/test_check_ci_guards.py
      - name: Check CMake contract
        shell: bash
        run: python .github/scripts/check_cmake_cxx20_contract.py source
      - name: Check CMake guardrails
        shell: bash
        run: python .github/scripts/test_check_cmake_cxx20_contract.py
      - name: Check compile command guardrails
        shell: bash
        run: python .github/scripts/test_check_compile_commands.py
      - name: Check dependency suffixes
        shell: bash
        run: |
          before="${{ github.event.before }}"
          after="${{ github.sha }}"
          python .github/scripts/check_dependency_patch_suffixes.py --before "$before" --after "$after"
      - name: Check dependency suffix guardrails
        shell: bash
        run: python .github/scripts/test_check_dependency_patch_suffixes.py
      - name: Check release needs guardrails
        shell: bash
        run: python .github/scripts/check_release_needs.py
      - name: Check PGO metadata/consume guardrails
        shell: bash
        run: python .github/scripts/test_check_pgo_consume_chain.py
      - name: Set Package Version
        shell: bash
        run: |
          set -euo pipefail
          echo "::warning::No numeric version tag found; using $version as CI fallback"
          echo "version=0.0-gabc1234" >> "$GITHUB_OUTPUT"
  cxx20-warning-scan:
    runs-on: windows-latest
    steps:
      - name: Setup Shared Dependencies
        uses: ./x265/.github/actions/setup-windows-deps
        with:
          extra-msys2-packages: >-
            mingw-w64-clang-x86_64-python
            mingw-w64-clang-x86_64-zimg
      - name: Check GNU++20 downgrade guardrail
        shell: bash
        run: |
          set -euo pipefail
          source cxx20-scan-helpers.sh
          configure_cxx20_scan x265/source build/cxx20-downgrade-guard \
            -DCMAKE_CXX_STANDARD=17 \
            -DENABLE_CLI=OFF \
            -DENABLE_ASSEMBLY=OFF
          check_cxx20_commands_clang build/cxx20-downgrade-guard \
            --min-cpp-commands=50 \
            --forbidden-flag-substring=-std=gnu++17 \
            --forbidden-flag-substring=-std=c++17
      - name: Run C++20 CLI and dependency warning scans
        shell: bash
        run: |
          configure_cxx20_scan x265/source build/cxx20-warning-scan \
            -DENABLE_ZIMG=ON
          check_cxx20_commands_clang build/cxx20-warning-scan \
            --required-file-substring=source/filters/zimgfilter.cpp \
            --required-file-flag=source/filters/zimgfilter.cpp=-DENABLE_ZIMG
          build/cxx20-warning-scan/x265.exe --input build/cxx20-warning-scan/smoke_zimg.yuv --input-res 96x96 --fps 1 --frames 1 --vf "zimg:lanczos(64,64)" --output build/cxx20-warning-scan/smoke_zimg.hevc 2>&1 | tee build/cxx20-warning-scan/smoke_zimg.log
          test -s build/cxx20-warning-scan/smoke_zimg.hevc
          grep -Fq 'zimg [info]: Resize: 64x64' build/cxx20-warning-scan/smoke_zimg.log
          grep -Fq 'encoded 1 frames' build/cxx20-warning-scan/smoke_zimg.log
          build/cxx20-warning-scan/x265.exe --input build/cxx20-warning-scan/smoke_zimg.yuv --input-res 96x96 --fps 1 --frames 1 --vf "zimg:crop(0,0,-0,-0)" --output build/cxx20-warning-scan/smoke_zimg_bypass.hevc 2>&1 | tee build/cxx20-warning-scan/smoke_zimg_bypass.log
          test -s build/cxx20-warning-scan/smoke_zimg_bypass.hevc
          grep -Fq 'zimg [info]: Nothing to do. Bypassing' build/cxx20-warning-scan/smoke_zimg_bypass.log
          grep -Fq 'encoded 1 frames' build/cxx20-warning-scan/smoke_zimg_bypass.log
          long_zimg_vf="$(python -c "print('zimg:lanczos(' + '1' * 1100 + ')')")"
          if build/cxx20-warning-scan/x265.exe --input build/cxx20-warning-scan/smoke_zimg.yuv --input-res 96x96 --fps 1 --frames 1 --vf "$long_zimg_vf" --output build/cxx20-warning-scan/smoke_zimg_longparam.hevc > build/cxx20-warning-scan/smoke_zimg_longparam.log 2>&1; then
            echo "ZIMG long-parameter smoke unexpectedly succeeded"
            exit 1
          fi
          grep -Fq 'Filter parameters exceeds supported length' build/cxx20-warning-scan/smoke_zimg_longparam.log
          long_filter_name_vf="$(python -c "print('a' * 1100 + ':x')")"
          if build/cxx20-warning-scan/x265.exe --input build/cxx20-warning-scan/smoke_zimg.yuv --input-res 96x96 --fps 1 --frames 1 --vf "$long_filter_name_vf" --output build/cxx20-warning-scan/smoke_filter_longname.hevc > build/cxx20-warning-scan/smoke_filter_longname.log 2>&1; then
            echo "Filter long-name smoke unexpectedly succeeded"
            exit 1
          fi
          grep -Fq 'Filter name exceeds supported length' build/cxx20-warning-scan/smoke_filter_longname.log
          configure_cxx20_scan x265/source build/cxx20-warning-scan-12bit \
            -DHIGH_BIT_DEPTH=ON \
            -DMAIN12=ON
          check_cxx20_commands_clang build/cxx20-warning-scan-12bit \
            --required-depth-define=-DX265_DEPTH=12
          configure_cxx20_scan x265/source build/cxx20-warning-scan-unity \
            -DENABLE_UNITY_BUILD=ON
          configure_cxx20_scan x265/source build/cxx20-warning-scan-shared-deps \
            -DENABLE_LAVF=ON \
            -DENABLE_LSMASH=ON
          check_cxx20_commands_clang build/cxx20-warning-scan-shared-deps \
            --required-file-flag=source/input/lavf.cpp=-DENABLE_LAVF \
            --required-file-flag=source/output/mp4.cpp=-DENABLE_LSMASH
          configure_cxx20_scan x265/source build/cxx20-warning-scan-shared-deps-asm \
            -DENABLE_ASSEMBLY=ON
      - name: Run C++20 shared and all-bit-depth warning scans
        shell: bash
        run: |
          check_cxx20_commands_clang build/cxx20-warning-scan-shared-library
          ninja -C build/cxx20-warning-scan-shared-library cli x265-shared
          check_cxx20_commands_clang build/cxx20-warning-scan-all-8b-lib
          ninja -C build/cxx20-warning-scan-all-8b-lib x265-static
          configure_cxx20_scan x265/source build/cxx20-warning-scan-all-12b-lib
          ninja -C build/cxx20-warning-scan-all-12b-lib x265-static
          check_cxx20_commands_clang build/cxx20-warning-scan-all \
            --required-file-flag=source/common/version.cpp=-DLINKED_8BIT=1 \
            --required-file-flag=source/common/version.cpp=-DLINKED_12BIT=1 \
            --required-file-flag=source/encoder/api.cpp=-DLINKED_8BIT=1 \
            --required-file-flag=source/encoder/api.cpp=-DLINKED_12BIT=1 \
            --forbidden-file-flag=source/encoder/api.cpp=-DEXPORT_C_API=1
          build/cxx20-warning-scan-12bit/x265.exe --input build/cxx20-warning-scan-12bit/smoke_12bit.yuv --input-res 64x64 --input-depth 12 --output-depth 12 --fps 1 --frames 1 --output build/cxx20-warning-scan-12bit/smoke_12bit.hevc
          test -s build/cxx20-warning-scan-12bit/smoke_12bit.hevc
          build/cxx20-warning-scan-shared-library/x265.exe --input build/cxx20-warning-scan-shared-library/smoke_shared.yuv --input-res 64x64 --fps 1 --frames 1 --output build/cxx20-warning-scan-shared-library/smoke_shared.hevc
          test -s build/cxx20-warning-scan-shared-library/smoke_shared.hevc
          build/cxx20-warning-scan-all/x265.exe --input build/cxx20-warning-scan-all/smoke_all.yuv --input-res 64x64 --input-depth 10 --output-depth 10 --fps 1 --frames 1 --output build/cxx20-warning-scan-all/smoke_all.hevc
          test -s build/cxx20-warning-scan-all/smoke_all.hevc
      - name: Run C++20 CPU and ASM warning scans
        shell: bash
        run: |
          for target_cpu in haswell arrowlake znver5; do
            configure_cxx20_scan x265/source "build/cxx20-warning-scan-${target_cpu}" \
              --target-cpu="${target_cpu}" \
              -DENABLE_CLI=OFF \
              -DENABLE_ASSEMBLY=OFF
            check_cxx20_commands_clang "build/cxx20-warning-scan-${target_cpu}" \
              --required-file-substring=source/common/cpu.cpp \
              --forbidden-file-substring=source/output/
          done
          configure_cxx20_scan x265/source build/cxx20-warning-scan-asm \
            -DENABLE_ASSEMBLY=ON \
            -DENABLE_TESTS=ON \
            -DCMAKE_ASM_NASM_FLAGS=-w-macro-params-legacy
          check_cxx20_commands_clang build/cxx20-warning-scan-asm \
            --required-file-substring=source/test/
          ninja -C build/cxx20-warning-scan-asm TestBench
  cxx20-gcc-compile-commands:
    runs-on: windows-latest
    steps:
      - name: Run GCC C++20 compile command diagnostics
        shell: bash
        run: |
          set -euo pipefail
          check_cxx20_commands_gcc build/cxx20-gcc-compile-commands \
            --required-file-substring=source/output/reconplay.cpp
          ninja -C build/cxx20-gcc-compile-commands cli
          check_cxx20_commands_gcc build/cxx20-gcc-compile-commands-12bit
          ninja -C build/cxx20-gcc-compile-commands-12bit x265-static
          check_cxx20_commands_gcc build/cxx20-gcc-compile-commands-8bit-lib \
            --required-file-substring=source/common/winxp.cpp \
            --required-file-flag=source/common/winxp.cpp=-D_WIN32_WINNT=_WIN32_WINNT_WIN7 \
            --forbidden-file-flag=source/common/winxp.cpp=-D_WIN32_WINNT=_WIN32_WINNT_WINXP
          ninja -C build/cxx20-gcc-compile-commands-8bit-lib x265-static
          check_cxx20_commands_gcc build/cxx20-gcc-compile-commands-all \
            --required-file-flag=source/common/version.cpp=-DLINKED_8BIT=1 \
            --required-file-flag=source/common/version.cpp=-DLINKED_12BIT=1 \
            --required-file-flag=source/encoder/api.cpp=-DLINKED_8BIT=1 \
            --required-file-flag=source/encoder/api.cpp=-DLINKED_12BIT=1 \
            --forbidden-file-flag=source/encoder/api.cpp=-DEXPORT_C_API=1
          ninja -C build/cxx20-gcc-compile-commands-all cli
  cxx20-linux-gcc-compile-commands:
    runs-on: ubuntu-latest
    steps:
      - name: Run Linux GCC C++20 compile command diagnostics
        shell: bash
        run: |
          set -euo pipefail
          check_cxx20_commands_gcc build/cxx20-linux-gcc-compile-commands \
            --forbidden-flag-substring=-Wno-deprecated-declarations \
            --forbidden-flag-substring=-Wno-error=deprecated-declarations \
            --required-file-substring=source/output/reconplay.cpp \
            --forbidden-file-substring=source/common/winxp.cpp
          ninja -C build/cxx20-linux-gcc-compile-commands cli
          python - <<'PY'
          from pathlib import Path
          width = height = 64
          frame = bytes([0]) * (width * height) + bytes([128]) * (width * height // 2)
          Path('build/cxx20-linux-gcc-compile-commands/smoke_linux_gcc.yuv').write_bytes(frame)
          PY
          build/cxx20-linux-gcc-compile-commands/x265 --input build/cxx20-linux-gcc-compile-commands/smoke_linux_gcc.yuv --input-res 64x64 --fps 1 --frames 1 --output build/cxx20-linux-gcc-compile-commands/smoke_linux_gcc.hevc 2>&1 | tee build/cxx20-linux-gcc-compile-commands/smoke_linux_gcc.log
          test -s build/cxx20-linux-gcc-compile-commands/smoke_linux_gcc.log
          test -s build/cxx20-linux-gcc-compile-commands/smoke_linux_gcc.hevc
          grep -Fq 'encoded 1 frames' build/cxx20-linux-gcc-compile-commands/smoke_linux_gcc.log
          configure_cxx20_scan x265/source build/cxx20-warning-scan-all-12b-lib
          ninja -C build/cxx20-warning-scan-all-12b-lib x265-static
          check_cxx20_commands_gcc build/cxx20-gcc-compile-commands-12bit
          ninja -C build/cxx20-gcc-compile-commands-12bit x265-static
          check_cxx20_commands_gcc build/cxx20-gcc-compile-commands-8bit-lib \
            --required-file-substring=source/common/winxp.cpp \
            --required-file-flag=source/common/winxp.cpp=-D_WIN32_WINNT=_WIN32_WINNT_WIN7 \
            --forbidden-file-flag=source/common/winxp.cpp=-D_WIN32_WINNT=_WIN32_WINNT_WINXP
          ninja -C build/cxx20-gcc-compile-commands-8bit-lib x265-static
          check_cxx20_commands_gcc build/cxx20-gcc-compile-commands-all \
            --required-file-flag=source/common/version.cpp=-DLINKED_8BIT=1 \
            --required-file-flag=source/common/version.cpp=-DLINKED_12BIT=1 \
            --required-file-flag=source/encoder/api.cpp=-DLINKED_8BIT=1 \
            --required-file-flag=source/encoder/api.cpp=-DLINKED_12BIT=1 \
            --forbidden-file-flag=source/encoder/api.cpp=-DEXPORT_C_API=1
          configure_cxx20_scan x265/source build/cxx20-linux-gcc-compile-commands-12bit \
            -DHIGH_BIT_DEPTH=ON \
            -DMAIN12=ON
          check_cxx20_commands_gcc build/cxx20-linux-gcc-compile-commands-12bit \
            --required-depth-define=-DX265_DEPTH=12 \
            --forbidden-file-flag=source/encoder/api.cpp=-DEXPORT_C_API=1
          ninja -C build/cxx20-linux-gcc-compile-commands-12bit x265-static
  build:
    runs-on: windows-latest
    steps:
      - name: Get CI Version
        shell: bash
        run: |
          set -euo pipefail
          echo "::warning::No numeric version tag found; using $version as CI fallback"
          echo "version=0.0-gabc1234" >> "$GITHUB_OUTPUT"
      - name: Build
        shell: bash
        run: |
          check_pgo_consume_commands() {
            local build_dir="$1"
            local pgo_flag="$2"
            local min_cpp_commands="$3"
            [ -n "$pgo_flag" ] || return 0
            check_cxx20_commands_pgo_consume "$build_dir" --min-cpp-commands="$min_cpp_commands"
          }
          check_pgo_consume_commands build/8b-lib "$PGO_8B_LIB_FLAG" 50
          check_pgo_consume_commands build/12b-lib "$PGO_12B_LIB_FLAG" 50
          check_pgo_consume_commands build/all-8b-lib "$PGO_ALL_FLAG" 50
          check_pgo_consume_commands build/all-12b-lib "$PGO_ALL_FLAG" 50
          check_pgo_consume_commands build/all "$PGO_ALL_FLAG" 60
          check_cxx20_commands_clang build/all \
            --required-file-flag=source/common/version.cpp=-DLINKED_8BIT=1 \
            --required-file-flag=source/common/version.cpp=-DLINKED_12BIT=1 \
            --required-file-flag=source/encoder/api.cpp=-DLINKED_8BIT=1 \
            --required-file-flag=source/encoder/api.cpp=-DLINKED_12BIT=1 \
            --forbidden-file-flag=source/encoder/api.cpp=-DEXPORT_C_API=1
      - name: Threaded ME Smoke (All CLI)
        shell: bash
        run: |
          ffmpeg -hide_banner -loglevel error -f lavfi -i testsrc2=size=160x90:rate=24 -frames:v 16 -pix_fmt yuv420p smoke_threaded_me.y4m
          build/all/x265.exe --input smoke_threaded_me.y4m --input-res 160x90 --fps 24 --frames 16 --preset medium --threaded-me --pools 32 --frame-threads 1 --no-wpp --no-progress --output smoke_threaded_me.hevc 2>&1 | tee smoke_threaded_me_log.txt
          test -s smoke_threaded_me.hevc
          grep -Fq 'frame threads / pool features       : 1 / threaded-me' smoke_threaded_me_log.txt
          ! grep -Fq 'disabling --threaded-me' smoke_threaded_me_log.txt
          ffprobe -v error -count_frames -select_streams v:0 -show_entries stream=nb_read_frames -of default=noprint_wrappers=1 smoke_threaded_me.hevc > smoke_threaded_me_count.txt
          grep -q 'nb_read_frames=16' smoke_threaded_me_count.txt
      - name: Threaded ME Stress Smoke (All CLI)
        shell: bash
        run: |
          ffmpeg -hide_banner -loglevel error -f lavfi -i testsrc2=size=160x90:rate=24 -frames:v 2 -pix_fmt yuv420p smoke_threaded_me_stress.y4m
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
      - name: QPFile Smoke (All CLI)
        shell: bash
        run: |
          cat > smoke_qpfile.txt <<'EOF'
          0 I 22
          3 P 24
          6 B 26
          9 K 20
          EOF
          ffmpeg -hide_banner -loglevel error -f lavfi -i testsrc2=size=160x90:rate=24 -frames:v 12 -pix_fmt yuv420p smoke_qpfile.y4m
          build/all/x265.exe --input smoke_qpfile.y4m --input-res 160x90 --fps 24 --frames 12 --qpfile smoke_qpfile.txt --output smoke_qpfile.hevc
          test -s smoke_qpfile.hevc
          ffprobe -v error -count_frames -select_streams v:0 -show_entries stream=nb_read_frames -of default=noprint_wrappers=1 smoke_qpfile.hevc > smoke_qpfile_count.txt
          grep -q "nb_read_frames=12" smoke_qpfile_count.txt
      - name: Zonefile Smoke (All CLI)
        shell: bash
        run: |
          cat > smoke_zonefile.txt <<'EOF'
          0 --bitrate 350
          6 --bitrate 500
          EOF
          ffmpeg -hide_banner -loglevel error -f lavfi -i testsrc2=size=160x90:rate=24 -frames:v 12 -pix_fmt yuv420p smoke_zonefile.y4m
          build/all/x265.exe --input smoke_zonefile.y4m --input-res 160x90 --fps 24 --frames 12 --bitrate 400 --zonefile smoke_zonefile.txt --output smoke_zonefile.hevc
          test -s smoke_zonefile.hevc
          ffprobe -v error -count_frames -select_streams v:0 -show_entries stream=nb_read_frames -of default=noprint_wrappers=1 smoke_zonefile.hevc > smoke_zonefile_count.txt
          grep -q "nb_read_frames=12" smoke_zonefile_count.txt
      - name: Recon Smoke (All CLI)
        shell: bash
        run: |
          ffmpeg -hide_banner -loglevel error -f lavfi -i testsrc2=size=160x90:rate=24 -frames:v 12 -pix_fmt yuv420p smoke_recon.y4m
          build/all/x265.exe --input smoke_recon.y4m --input-res 160x90 --fps 24 --frames 12 --recon smoke_recon_out.y4m --output smoke_recon.hevc
          test -s smoke_recon.hevc
          test -s smoke_recon_out.y4m
          grep -q '^YUV4MPEG2 ' smoke_recon_out.y4m
      - name: MKV Smoke (All CLI)
        shell: bash
        run: |
          ffmpeg -hide_banner -loglevel error -f lavfi -i testsrc2=size=160x90:rate=24 -frames:v 12 -pix_fmt yuv420p smoke_mkv.y4m
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
      - name: LAVF Input Smoke (All CLI)
        shell: bash
        run: |
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
      - name: MP4 Smoke (All CLI)
        shell: bash
        run: |
          source ./mp4_smoke_helpers.sh
          make_y4m smoke.y4m 24 16 yuv420p
          build/all/x265.exe --input smoke.y4m --input-res 128x72 --fps 24 --frames 16 --bframes 4 --keyint 8 --min-keyint 8 --no-open-gop --output smoke.mp4
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
      - name: MP4 Smoke (All CLI Open GOP)
        shell: bash
        run: |
          source ./mp4_smoke_helpers.sh
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
      - name: MP4 Smoke (All CLI CRA)
        shell: bash
        run: |
          source ./mp4_smoke_helpers.sh
          make_y4m smoke_cra.y4m 24 16 yuv420p
          build/all/x265.exe --input smoke_cra.y4m --input-res 128x72 --fps 24 --frames 16 --bframes 0 --keyint 1 --min-keyint 1 --cra-nal --output smoke_cra.mp4
          probe_mp4 smoke_cra smoke_cra.mp4 flags
          assert_common_mp4 smoke_cra 128 72 yuv420p 24/1 16 1/24000
          assert_mp4_markers smoke_cra.mp4 iso6 hvc1 hvcC
          awk -F, '$1 == 1 { kf++ } END { if (kf != 16) exit 1 }' smoke_cra_frames.csv
          assert_duration_window smoke_cra 0.60 0.75
      - name: MP4 Smoke (All CLI Single Frame)
        shell: bash
        run: |
          source ./mp4_smoke_helpers.sh
          make_y4m smoke_single.y4m 24 1 yuv420p
          build/all/x265.exe --input smoke_single.y4m --input-res 128x72 --fps 24 --frames 1 --bframes 0 --keyint 1 --min-keyint 1 --output smoke_single.mp4
          probe_mp4 smoke_single smoke_single.mp4 flags
          assert_common_mp4 smoke_single 128 72 yuv420p 24/1 1 1/24000
          assert_mp4_markers smoke_single.mp4 iso6 hvc1 hvcC
          assert_single_frame_mp4 smoke_single 0.05 0.02 0.08
      - name: MP4 Smoke (All CLI Frames=0 Means Encode Available Input)
        shell: bash
        run: |
          source ./mp4_smoke_helpers.sh
          make_y4m smoke_zero.y4m 24 1 yuv420p
          build/all/x265.exe --input smoke_zero.y4m --input-res 128x72 --fps 24 --frames 0 --bframes 0 --keyint 1 --min-keyint 1 --output smoke_zero.mp4
          probe_mp4 smoke_zero smoke_zero.mp4 flags
          assert_common_mp4 smoke_zero 128 72 yuv420p 24/1 1 1/24000
          assert_mp4_markers smoke_zero.mp4 iso6 hvc1 hvcC
          assert_single_frame_mp4 smoke_zero 0.05 0.02 0.08
      - name: MP4 Smoke (All CLI Single Frame 24000/1001)
        shell: bash
        run: |
          source ./mp4_smoke_helpers.sh
          make_y4m smoke_single_frac.y4m 24000/1001 1 yuv420p
          build/all/x265.exe --input smoke_single_frac.y4m --input-res 128x72 --fps 24000/1001 --frames 1 --bframes 0 --keyint 1 --min-keyint 1 --output smoke_single_frac.mp4
          probe_mp4 smoke_single_frac smoke_single_frac.mp4 flags
          assert_common_mp4 smoke_single_frac 128 72 yuv420p 24000/1001 1 1/24000
          assert_mp4_markers smoke_single_frac.mp4 iso6 hvc1 hvcC
          assert_single_frame_mp4 smoke_single_frac 0.06 0.03 0.06
      - name: MP4 Smoke (All CLI VUI Metadata)
        shell: bash
        run: |
          source ./mp4_smoke_helpers.sh
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
      - name: MP4 Smoke (All CLI Strict-CBR Fails)
        shell: bash
        run: |
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
      - name: MP4 Smoke (All CLI 24000/1001)
        shell: bash
        run: |
          source ./mp4_smoke_helpers.sh
          make_y4m smoke_frac.y4m 24000/1001 24 yuv420p
          build/all/x265.exe --input smoke_frac.y4m --input-res 128x72 --fps 24000/1001 --frames 24 --bframes 4 --keyint 12 --min-keyint 12 --no-open-gop --output smoke_frac.mp4
          probe_mp4 smoke_frac smoke_frac.mp4 pts_time,dts_time,flags
          assert_common_mp4 smoke_frac 128 72 yuv420p 24000/1001 24 1/24000
          assert_mp4_markers smoke_frac.mp4 iso6 hvc1 hvcC
          awk -F, '$3 ~ /K/ { kf++; if (kf == 2 && NR != 13) exit 1 } END { if (kf < 2) exit 1 }' smoke_frac_packets.csv
          assert_duration_window smoke_frac 0.95 1.10
      - name: MP4 Smoke (All CLI B-Pyramid)
        shell: bash
        run: |
          source ./mp4_smoke_helpers.sh
          make_y4m smoke_bpyramid.y4m 24 16 yuv420p
          build/all/x265.exe --input smoke_bpyramid.y4m --input-res 128x72 --fps 24 --frames 16 --bframes 4 --b-pyramid --keyint 8 --min-keyint 8 --no-open-gop --output smoke_bpyramid.mp4
          probe_mp4 smoke_bpyramid smoke_bpyramid.mp4 pts_time,dts_time,flags
          assert_common_mp4 smoke_bpyramid 128 72 yuv420p 24/1 16 1/24000
          awk -F, '$3 ~ /K/ { kf++; if (kf == 2 && NR != 9) exit 1 } END { if (kf < 2) exit 1 }' smoke_bpyramid_packets.csv
          assert_duration_window smoke_bpyramid 0.60 0.75
      - name: MP4 Smoke (All CLI AUD Request Stays Valid)
        shell: bash
        run: |
          source ./mp4_smoke_helpers.sh
          make_y4m smoke_aud.y4m 24 16 yuv420p
          build/all/x265.exe --input smoke_aud.y4m --input-res 128x72 --fps 24 --frames 16 --bframes 4 --keyint 8 --min-keyint 8 --aud --output smoke_aud.mp4
          probe_mp4 smoke_aud smoke_aud.mp4 pts_time,dts_time,flags
          assert_common_mp4 smoke_aud 128 72 yuv420p 24/1 16 1/24000
          awk -F, '$3 ~ /K/ { kf++; if (kf == 2) { if ($1 == "N/A") exit 1; if (($1+0) < 0.30 || ($1+0) > 0.38) exit 1 } } END { if (kf < 2) exit 1 }' smoke_aud_packets.csv
          assert_duration_window smoke_aud 0.60 0.75
      - name: MP4 Smoke (All CLI EOS/EOB Request Stays Valid)
        shell: bash
        run: |
          source ./mp4_smoke_helpers.sh
          make_y4m smoke_eos.y4m 24 16 yuv420p
          build/all/x265.exe --input smoke_eos.y4m --input-res 128x72 --fps 24 --frames 16 --bframes 4 --keyint 8 --min-keyint 8 --eos --eob --output smoke_eos.mp4
          probe_mp4 smoke_eos smoke_eos.mp4 pts_time,dts_time,flags
          assert_common_mp4 smoke_eos 128 72 yuv420p 24/1 16 1/24000
          awk -F, '$3 ~ /K/ { kf++; if (kf == 2) { if ($1 == "N/A") exit 1; if (($1+0) < 0.30 || ($1+0) > 0.38) exit 1 } } END { if (kf < 2) exit 1 }' smoke_eos_packets.csv
          assert_duration_window smoke_eos 0.60 0.75
      - name: MP4 Smoke (All CLI IDR Recovery SEI)
        shell: bash
        run: |
          source ./mp4_smoke_helpers.sh
          make_y4m smoke_recovery.y4m 24 16 yuv420p
          build/all/x265.exe --input smoke_recovery.y4m --input-res 128x72 --fps 24 --frames 16 --bframes 0 --keyint 8 --min-keyint 8 --no-open-gop --idr-recovery-sei --output smoke_recovery.mp4
          probe_mp4 smoke_recovery smoke_recovery.mp4 pts_time,dts_time,flags
          assert_common_mp4 smoke_recovery 128 72 yuv420p 24/1 16 1/24000
          assert_mp4_markers smoke_recovery.mp4 iso6 hvc1 hvcC
          awk -F, '$3 ~ /K/ { kf++; if (kf == 2) { if ($1 == "N/A") exit 1; if (($1+0) < 0.30 || ($1+0) > 0.38) exit 1 } } END { if (kf < 2) exit 1 }' smoke_recovery_packets.csv
          assert_duration_window smoke_recovery 0.60 0.75
      - name: GOP Output Smoke (All CLI)
        shell: bash
        run: |
          ffmpeg -hide_banner -loglevel error -f lavfi -i testsrc2=size=128x72:rate=24 -frames:v 16 -pix_fmt yuv420p smoke_gop.y4m
          build/all/x265.exe --input smoke_gop.y4m --input-res 128x72 --fps 24 --frames 16 --bframes 0 --keyint 8 --min-keyint 8 --no-open-gop --output smoke_gop.gop
          test -s smoke_gop.gop
          test -s smoke_gop.options
          test -s smoke_gop.headers
          test -s smoke_gop-000000.hevc-gop-data
          test -s smoke_gop-000008.hevc-gop-data
          printf '%s\\n' smoke_gop-*.hevc-gop-data > smoke_gop_data_files.txt
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

'''

UPDATE_DEPS_YML = '''
name: Update Dependencies
on: workflow_dispatch
jobs:
  update-deps:
    runs-on: ubuntu-latest
    steps:
      - name: Check CI guardrails
        shell: bash
        run: |
          set -euo pipefail
          python .github/scripts/check_ci_guards.py
          python .github/scripts/test_check_ci_guards.py
          python .github/scripts/check_dependency_patch_suffixes.py
      - name: Get Latest L-SMASH Commit
        id: lsmash
        shell: bash
        run: |
          SHA=$(curl -fsSL "https://api.github.com/repos/vimeo/l-smash/commits?sha=master&per_page=1" | jq -r '.[0].sha')
          echo "sha=$SHA" >> $GITHUB_OUTPUT
      - name: Get Latest GOP muxer Commit
        id: gop_muxer
        shell: bash
        run: |
          SHA=$(curl -fsSL "https://api.github.com/repos/msg7086/gop_muxer/commits?sha=master&per_page=1" | jq -r '.[0].sha')
          echo "sha=$SHA" >> $GITHUB_OUTPUT
      - name: Update Dependency Refs
        shell: bash
        run: |
          set -euo pipefail
          for anchor in ffmpeg-ref mimalloc-ref obuparse-ref lsmash-ref lsmash-cache-suffix gop-muxer-ref gop-muxer-cache-suffix; do
            if ! grep -Fq "${anchor}:" .github/actions/setup-windows-deps/action.yml; then
              exit 1
            fi
          done
          lsmash_suffix=$(sed -n '/lsmash-cache-suffix:/,/lsmash-path:/p' "$action" | sed -n 's/^ *default: //p' | head -1)
          gop_muxer_suffix=$(sed -n '/gop-muxer-cache-suffix:/,/gop-muxer-path:/p' "$action" | sed -n 's/^ *default: //p' | head -1)
          echo "Current L-SMASH cache suffix: ${lsmash_suffix}"
          echo "Current GOP muxer cache suffix: ${gop_muxer_suffix}"
          sed -i "/lsmash-ref:/,/lsmash-cache-suffix:/s/default: [0-9a-f]\\{40\\}/default: ${{ steps.lsmash.outputs.sha }}/" "$action"
          sed -i "/gop-muxer-ref:/,/gop-muxer-cache-suffix:/s/default: [0-9a-f]\\{40\\}/default: ${{ steps.gop_muxer.outputs.sha }}/" "$action"
      - name: Update Deps Cache
        shell: bash
        run: |
          cat > .github/deps-cache.json << EOF
          {
            "lsmash": "${{ steps.lsmash.outputs.sha }}",
            "obuparse": "${{ steps.obuparse.outputs.tag }}",
            "gop_muxer": "${{ steps.gop_muxer.outputs.sha }}"
          }
          EOF
      - name: Validate Dependency Ref Diff
        shell: bash
        run: |
          unexpected=$(git diff --name-only | grep -Ev '^(\\.github/actions/setup-windows-deps/action\\.yml|\\.github/deps-cache\\.json)$' || true)
          if [ -n "$unexpected" ]; then
            echo "Unexpected dependency update diff paths:"
            printf '%s\\n' "$unexpected"
            exit 1
          fi
'''

BUILD_PROFILING_YML = '''
name: Build Profiling
on: push
jobs:
  validate-guardrails:
    runs-on: ubuntu-latest
    steps:
      - name: Check CI guardrails
        shell: bash
        run: |
          set -euo pipefail
          python .github/scripts/check_ci_guards.py
          python .github/scripts/test_check_ci_guards.py
  build:
    needs: validate-guardrails
    runs-on: windows-latest
    steps:
      - name: Get Latest Tag
        shell: bash
        run: |
          set -euo pipefail
          echo "::warning::No numeric version tag found; using $version as CI fallback"
      - name: Get CI Version
        shell: bash
        run: |
          set -euo pipefail
          head_hash=$(git rev-parse --short HEAD)
          version="${{ steps.tag.outputs.version }}-g${head_hash}"
          echo "version=$version" >> "$GITHUB_OUTPUT"
      - name: Setup Shared Dependencies
        uses: ./.github/actions/setup-windows-deps
        with:
          enable-lsmash: 'ON'
      - name: Smoke, Package, and Verify 8b-lib
        shell: bash
        run: |
          case "$llvm_profdata" in
            /clang64/bin/*) ;;
            *) echo "Unexpected llvm-profdata path: $llvm_profdata" >&2; exit 1 ;;
          esac
          test -s smoke_profile_8b.mp4
          ffmpeg -hide_banner -loglevel error -i smoke_profile_8b.mp4 -c:v rawvideo -pix_fmt yuv420p -strict -1 smoke_profile_roundtrip_8b.y4m
          test -s smoke_profile_roundtrip_8b.y4m
          frame_count=$(grep -aob 'FRAME' smoke_profile_roundtrip_8b.y4m | wc -l || true)
          echo "8b-lib roundtrip FRAME tokens: ${frame_count:-missing}"
          test "$frame_count" = "12"
          test -s "$LLVM_PROFILE_FILE"
          test -s profile-smoke-8b.profdata
          ./profdata-dist/llvm-profdata.exe show profile-smoke-8b.profdata >/dev/null
          echo "- standard: gnu++20"
          echo "- mp4_roundtrip_frames: 12"
      - name: Smoke, Package, and Verify 12b-lib
        shell: bash
        run: |
          test -s smoke_profile_12b.mp4
          ffmpeg -hide_banner -loglevel error -i smoke_profile_12b.mp4 -c:v rawvideo -pix_fmt yuv420p12le -strict -1 smoke_profile_roundtrip_12b.y4m
          test -s smoke_profile_roundtrip_12b.y4m
          frame_count=$(grep -aob 'FRAME' smoke_profile_roundtrip_12b.y4m | wc -l || true)
          echo "12b-lib roundtrip FRAME tokens: ${frame_count:-missing}"
          test "$frame_count" = "12"
          test -s "$LLVM_PROFILE_FILE"
          test -s profile-smoke-12b.profdata
          ./profdata-dist/llvm-profdata.exe show profile-smoke-12b.profdata >/dev/null
          echo "- standard: gnu++20"
          echo "- mp4_roundtrip_frames: 12"
      - name: Smoke, Package, and Verify All
        shell: bash
        run: |
          test -s smoke_profile_all.mp4
          ffmpeg -hide_banner -loglevel error -i smoke_profile_all.mp4 -c:v rawvideo -pix_fmt yuv420p10le -strict -1 smoke_profile_roundtrip_all.y4m
          test -s smoke_profile_roundtrip_all.y4m
          frame_count=$(grep -aob 'FRAME' smoke_profile_roundtrip_all.y4m | wc -l || true)
          echo "all roundtrip FRAME tokens: ${frame_count:-missing}"
          test "$frame_count" = "12"
          test -s "$LLVM_PROFILE_FILE"
          test -s profile-smoke-all.profdata
          ./profdata-dist/llvm-profdata.exe show profile-smoke-all.profdata >/dev/null
          echo "- standard: gnu++20"
          echo "- mp4_roundtrip_frames: 12"
  publish-release:
    needs: [build, validate-guardrails]
    runs-on: windows-latest
    steps:
      - name: Publish
        shell: bash
        run: echo publish
'''

ACTION_YML = '''
name: Setup Windows dependencies
inputs:
  ffmpeg-ref:
    default: n8.1
  mimalloc-ref:
    default: v3.3.2
  obuparse-ref:
    default: v2.0.2
  lsmash-repository:
    default: vimeo/l-smash
  lsmash-ref:
    default: 04e39f1fb232c332d4b04a1043c02c7c2d282d00
  lsmash-cache-suffix:
    default: clang-coff-refptr-v2
  lsmash-patch-check-paths:
    default: codecs/description.c core/isom.c
  lsmash-patch-path:
    default: ../x265/.github/patches/l-smash-clang-coff-refptr.patch
  gop-muxer-repository:
    default: msg7086/gop_muxer
  gop-muxer-ref:
    default: 5677cf5ef905c2412ed31de300cd1a08b341d21d
  gop-muxer-cache-suffix:
    default: lsmash-add-box-v2-clang-gnu20
  gop-muxer-patch-path:
    default: ../x265/.github/patches/gop-muxer-lsmash-add-box.patch
runs:
  using: composite
  steps:
    - name: Verify MSYS2 Toolchain
      shell: msys2 {0}
      run: |
        set -euo pipefail
        case "${MSYSTEM:-}" in
          CLANG64) ;;
          *) echo "Unexpected MSYSTEM: ${MSYSTEM:-unset}" >&2; exit 1 ;;
        esac
        for tool in clang c++ ld.lld llvm-ar llvm-ranlib llvm-profdata cmake ninja pkg-config; do
          tool_path=$(command -v "$tool")
          case "$tool_path" in
            /clang64/bin/*|/usr/bin/*) ;;
            *) echo "Unexpected $tool path: $tool_path" >&2; exit 1 ;;
          esac
        done
        echo "=== Dependency provenance ==="
        echo "lsmash=${{ inputs.lsmash-repository }}@${{ inputs.lsmash-ref }} suffix=${{ inputs.lsmash-cache-suffix }} patch=${{ inputs.lsmash-patch-path }}"
        echo "gop_muxer=${{ inputs.gop-muxer-repository }}@${{ inputs.gop-muxer-ref }} suffix=${{ inputs.gop-muxer-cache-suffix }} patch=${{ inputs.gop-muxer-patch-path }}"
    - name: Compile L-SMASH
      shell: msys2 {0}
      run: |
        key: lsmash-${{ inputs.lsmash-repository }}-${{ inputs.lsmash-ref }}-${{ inputs.lsmash-cache-suffix }}
        git apply --ignore-whitespace --check ${{ inputs.lsmash-patch-path }}
        git apply --ignore-whitespace ${{ inputs.lsmash-patch-path }}
        git diff --check -- ${{ inputs.lsmash-patch-check-paths }}
        grep -Fq 'lsmash_local_isom_box_type' codecs/description.c
        grep -Fq "LSMASH_4CC( 'h', 'v', 'c', 'C' )" codecs/hevc.c
        grep -Fq 'lsmash_isom_box_type_value' core/box.c
        grep -Fq 'lsmash_qtff_box_type_value' core/box.c
        grep -Fq 'return isom_get_sample_group_description_common( list, ISOM_GROUP_TYPE_PROL );' core/isom.c
        grep -Fq 'return isom_get_sample_to_group_common( list, ISOM_GROUP_TYPE_PROL );' core/isom.c
        echo "Validated L-SMASH patch anchors"
    - name: Compile GOP muxer
      shell: msys2 {0}
      run: |
        git -c core.autocrlf=false reset --hard HEAD
        key: gop-muxer-${{ inputs.gop-muxer-repository }}-${{ inputs.gop-muxer-ref }}-${{ inputs.gop-muxer-cache-suffix }}
        git apply --check ${{ inputs.gop-muxer-patch-path }}
        git apply ${{ inputs.gop-muxer-patch-path }}
        git diff --check -- gop_muxer.cpp
        grep -Fq 'lsmash_add_box(lsmash_root_as_box(p_root), free_box)' gop_muxer.cpp
        echo "Validated GOP muxer patch anchors"
        c++ -O2 --std=gnu++20 -I/usr/local/include -c gop_muxer.cpp -o gop_muxer.o
'''

PROFILING_ACTION_YML = '''
name: Build x265 profiling binaries
inputs:
  enable-lsmash:
    default: 'false'
runs:
  using: composite
  steps:
    - name: Build 8b-lib profiling CLI
      shell: msys2 {0}
      run: |
        source build/cxx20_scan_helpers.sh
        CXX20_CHECK_SCRIPT="${{ github.action_path }}/../../scripts/check_compile_commands.py"
        lsmash_args=()
        if [ "${{ inputs.enable-lsmash }}" = 'true' ] || [ "${{ inputs.enable-lsmash }}" = 'ON' ]; then
          lsmash_args=(-DENABLE_LSMASH=ON)
        fi
        cmake -DCMAKE_EXPORT_COMPILE_COMMANDS=ON "${lsmash_args[@]}" -B build/8b
        check_cxx20_commands_profiling build/8b
    - name: Build 12b-lib profiling CLI
      shell: msys2 {0}
      run: |
        source build/cxx20_scan_helpers.sh
        CXX20_CHECK_SCRIPT="${{ github.action_path }}/../../scripts/check_compile_commands.py"
        cmake -DCMAKE_EXPORT_COMPILE_COMMANDS=ON -B build/12b
        check_cxx20_commands_profiling build/12b
    - name: Build all profiling CLI
      shell: msys2 {0}
      run: |
        source build/cxx20_scan_helpers.sh
        CXX20_CHECK_SCRIPT="${{ github.action_path }}/../../scripts/check_compile_commands.py"
        cmake -DCMAKE_EXPORT_COMPILE_COMMANDS=ON -B build/10b
        check_cxx20_commands_profiling .
'''


def run_checker(repo):
    command = [sys.executable, str(CHECKER), '--repo-root', str(repo)]
    bash = preferred_bash()
    if bash:
        command.extend(['--bash', bash])
    return subprocess.run(
        command,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def expect_pass(result):
    if result.returncode != 0:
        raise AssertionError(result.stdout)


def expect_fail(result, expected):
    if result.returncode == 0:
        raise AssertionError(f'expected failure containing {expected!r}')
    if expected not in result.stdout:
        raise AssertionError(result.stdout)


def write_repo(repo):
    workflows = repo / '.github' / 'workflows'
    setup_action = repo / '.github' / 'actions' / 'setup-windows-deps'
    profiling_action = repo / '.github' / 'actions' / 'build-x265-profiling'
    scripts = repo / '.github' / 'scripts'
    patches = repo / '.github' / 'patches'
    workflows.mkdir(parents=True)
    setup_action.mkdir(parents=True)
    profiling_action.mkdir(parents=True)
    scripts.mkdir(parents=True)
    patches.mkdir(parents=True)

    (workflows / 'build.yml').write_text(BUILD_YML)
    (workflows / 'build-profiling.yml').write_text(BUILD_PROFILING_YML)
    (workflows / 'update-deps.yml').write_text(UPDATE_DEPS_YML)
    (setup_action / 'action.yml').write_text(ACTION_YML)
    (profiling_action / 'action.yml').write_text(PROFILING_ACTION_YML)
    (scripts / 'check_dependency_patch_suffixes.py').write_text(Path(__file__).with_name('check_dependency_patch_suffixes.py').read_text())
    helper_text = Path(__file__).with_name('cxx20_scan_helpers.sh').read_text()
    (scripts / 'cxx20_scan_helpers.sh').write_text(helper_text)
    (repo / '.github' / 'deps-cache.json').write_text('''{
  "lsmash": "04e39f1fb232c332d4b04a1043c02c7c2d282d00",
  "obuparse": "v2.0.2",
  "gop_muxer": "5677cf5ef905c2412ed31de300cd1a08b341d21d"
}\n''')
    (patches / 'l-smash-clang-coff-refptr.patch').write_text('lsmash patch\n')
    (patches / 'gop-muxer-lsmash-add-box.patch').write_text('gop patch\n')


def replace_text(path, old, new):
    text = path.read_text()
    if old not in text:
        raise AssertionError(f'missing text {old!r}')
    path.write_text(text.replace(old, new, 1))


def replace_generated_text(path, old, new):
    text = path.read_text()
    generated = text.replace('\\\n            ', '            ')
    if old not in generated:
        raise AssertionError(f'missing generated text {old!r}')
    path.write_text(generated.replace(old, new, 1))


def main():
    if not shutil.which('bash'):
        print('bash is unavailable; skipping CI guard tests')
        return

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        expect_pass(run_checker(repo))

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'scripts' / 'cxx20_scan_helpers.sh', '--forbidden-flag=-fprofile-instr-use', '--forbidden-flag=-fprofile-instr-generate')
        expect_fail(run_checker(repo), 'missing profiling compile_commands guard: --forbidden-flag=-fprofile-instr-use')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'scripts' / 'cxx20_scan_helpers.sh', '--forbidden-flag-substring=-fprofile-instr-use=', '--forbidden-flag-substring=-fprofile-instr-generate=')
        expect_fail(run_checker(repo), 'missing profiling compile_commands guard: --forbidden-flag-substring=-fprofile-instr-use=')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', 'check_cxx20_commands_pgo_consume "$build_dir" --min-cpp-commands="$min_cpp_commands"', ': # check_cxx20_commands_pgo_consume "$build_dir" --min-cpp-commands="$min_cpp_commands"')
        expect_fail(run_checker(repo), 'missing required Build workflow guard snippet: check_cxx20_commands_pgo_consume "$build_dir" --min-cpp-commands="$min_cpp_commands"')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', 'build/all/x265.exe --input smoke_threaded_me.y4m', 'build/8b/x265.exe --input smoke_threaded_me.y4m')
        expect_fail(run_checker(repo), 'Threaded ME smoke must run build/all/x265.exe, got build/8b/x265.exe')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'actions' / 'setup-windows-deps' / 'action.yml', 'c++ -O2 --std=gnu++20 -I/usr/local/include -c gop_muxer.cpp -o gop_muxer.o', 'c++ -O2 --std=gnu++20 --std=gnu++17 -I/usr/local/include -c gop_muxer.cpp -o gop_muxer.o')
        expect_fail(run_checker(repo), 'missing required setup-windows-deps guard snippet: c++ -O2 --std=gnu++20 -I/usr/local/include -c gop_muxer.cpp -o gop_muxer.o')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', '--forbidden-flag-substring=-std=gnu++17', '# --forbidden-flag-substring=-std=gnu++17')
        expect_fail(run_checker(repo), 'GNU++20 downgrade guard must reject GNU++17 flags')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', 'configure_cxx20_scan x265/source build/cxx20-downgrade-guard', 'configure_cxx20_scan x265/source build/cxx20-warning-scan')
        expect_fail(run_checker(repo), 'GNU++20 downgrade guard must actively configure downgrade build')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', 'check_cxx20_commands_clang build/cxx20-downgrade-guard', 'check_cxx20_commands_clang build/cxx20-warning-scan')
        expect_fail(run_checker(repo), 'GNU++20 downgrade guard must actively check compile commands')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', 'for target_cpu in haswell arrowlake znver5; do', 'for target_cpu in haswell znver5; do')
        expect_fail(run_checker(repo), 'CPU warning scan must actively cover haswell/arrowlake/znver5 loop')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', '-DCMAKE_ASM_NASM_FLAGS=-w-macro-params-legacy', '# -DCMAKE_ASM_NASM_FLAGS=-w-macro-params-legacy')
        expect_fail(run_checker(repo), 'ASM warning scan must preserve NASM legacy macro warning flag')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', 'check_cxx20_commands_clang build/cxx20-warning-scan-asm', 'check_cxx20_commands_clang build/cxx20-warning-scan')
        expect_fail(run_checker(repo), 'ASM warning scan must actively check asm compile commands target')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', '--required-file-substring=source/test/', '--required-file-substring=source/common/')
        expect_fail(run_checker(repo), 'ASM warning scan must actively require test sources')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', '--required-file-flag=source/input/lavf.cpp=-DENABLE_LAVF', '--required-file-substring=source/input/lavf.cpp')
        expect_fail(run_checker(repo), 'C++20 warning scan must actively require LAVF macro')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', 'check_cxx20_commands_gcc build/cxx20-linux-gcc-compile-commands-12bit', 'echo skip-linux-gcc-12bit-shape')
        expect_fail(run_checker(repo), 'Linux GCC diagnostics must actively check 12-bit compile commands')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', "grep -Fq 'frame threads / pool features       : 1 / threaded-me' smoke_threaded_me_log.txt", "grep -Fq 'threaded-me' smoke_threaded_me_log.txt\n          # grep -Fq 'frame threads / pool features       : 1 / threaded-me' smoke_threaded_me_log.txt")
        expect_fail(run_checker(repo), "missing required Build workflow guard snippet: frame threads / pool features       : 1 / threaded-me")

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', 'grep -q \'nb_read_frames=16\' smoke_threaded_me_count.txt', 'grep -q \'nb_read_frames=2\' smoke_threaded_me_count.txt\n          # grep -q \'nb_read_frames=16\' smoke_threaded_me_count.txt')
        expect_fail(run_checker(repo), 'missing required Build workflow guard snippet: grep -q \'nb_read_frames=16\' smoke_threaded_me_count.txt')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', "build/all/x265.exe --input smoke_threaded_me.y4m --input-res 160x90 --fps 24 --frames 16 --preset medium --threaded-me --pools 32 --frame-threads 1 --no-wpp --no-progress --output smoke_threaded_me.hevc 2>&1 | tee smoke_threaded_me_log.txt", "build/all/x265.exe --input smoke_threaded_me.y4m --input-res 160x90 --fps 24 --frames 16 --preset medium --threaded-me --pools 16 --frame-threads 1 --no-wpp --no-progress --output smoke_threaded_me.hevc 2>&1 | tee smoke_threaded_me_log.txt\n          # --input-res 160x90 --fps 24 --frames 16 --preset medium --threaded-me --pools 32 --frame-threads 1 --no-wpp --no-progress")
        expect_fail(run_checker(repo), 'missing required Build workflow guard snippet: --input-res 160x90 --fps 24 --frames 16 --preset medium --threaded-me --pools 32 --frame-threads 1 --no-wpp --no-progress')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', "build/all/x265.exe --input smoke_threaded_me.y4m --input-res 160x90 --fps 24 --frames 16 --preset medium --threaded-me --pools 32 --frame-threads 1 --no-wpp --no-progress --output smoke_threaded_me.hevc 2>&1 | tee smoke_threaded_me_log.txt", "build/all/x265.exe --input smoke_threaded_me.y4m --input-res 160x90 --fps 24 --frames 16 --preset medium --pools 32 --frame-threads 1 --no-wpp --no-progress --output smoke_threaded_me.hevc 2>&1 | tee smoke_threaded_me_log.txt\n          # --input-res 160x90 --fps 24 --frames 16 --preset medium --threaded-me --pools 32 --frame-threads 1 --no-wpp --no-progress")
        expect_fail(run_checker(repo), 'missing required Build workflow guard snippet: --input-res 160x90 --fps 24 --frames 16 --preset medium --threaded-me --pools 32 --frame-threads 1 --no-wpp --no-progress')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', 'for iteration in $(seq 1 12); do', 'for iteration in $(seq 1 1); do')
        expect_fail(run_checker(repo), 'missing required Build workflow guard snippet: for iteration in $(seq 1 12); do')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', 'build/all/x265.exe --input smoke_threaded_me_stress.y4m --input-res 160x90 --fps 24 --frames 2 --preset medium --threaded-me --pools 32 --frame-threads 1 --no-wpp --no-progress --output "$output" 2>&1 | tee "$log"', 'build/all/x265.exe --input smoke_threaded_me_stress.y4m --input-res 160x90 --fps 24 --frames 2 --preset medium --pools 32 --frame-threads 1 --no-wpp --no-progress --output "$output" 2>&1 | tee "$log"')
        expect_fail(run_checker(repo), 'missing required Build workflow guard snippet: --input-res 160x90 --fps 24 --frames 2 --preset medium --threaded-me --pools 32 --frame-threads 1 --no-wpp --no-progress')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', 'grep -q \'nb_read_frames=2\' "$count"', 'grep -q \'nb_read_frames=1\' "$count"')
        expect_fail(run_checker(repo), 'missing required Build workflow guard snippet: grep -q \'nb_read_frames=2\'')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', 'check_pgo_consume_commands build/all-8b-lib "$PGO_ALL_FLAG" 50', 'echo skip-all-8b-pgo-consume')
        expect_fail(run_checker(repo), 'missing required Build workflow guard snippet: check_pgo_consume_commands build/all-8b-lib "$PGO_ALL_FLAG" 50')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', 'check_pgo_consume_commands build/all-12b-lib "$PGO_ALL_FLAG" 50', 'echo skip-all-12b-pgo-consume')
        expect_fail(run_checker(repo), 'missing required Build workflow guard snippet: check_pgo_consume_commands build/all-12b-lib "$PGO_ALL_FLAG" 50')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', 'python .github/scripts/check_cmake_cxx20_contract.py source', 'echo skip-cmake-contract\n          # python .github/scripts/check_cmake_cxx20_contract.py source')
        expect_fail(run_checker(repo), 'missing job validate-deps-cache-suffix step: Check CMake C++20 contract')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', '--required-file-flag=source/common/version.cpp=-DLINKED_8BIT=1', '--required-file-substring=source/output/output.cpp')
        expect_fail(run_checker(repo), 'missing required Build workflow guard snippet: --required-file-flag=source/common/version.cpp=-DLINKED_8BIT=1')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', '--forbidden-file-flag=source/encoder/api.cpp=-DEXPORT_C_API=1', '--required-file-substring=source/encoder/api.cpp')
        expect_fail(run_checker(repo), 'missing required Build workflow guard snippet: --forbidden-file-flag=source/encoder/api.cpp=-DEXPORT_C_API=1')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', 'check_cxx20_commands_gcc build/cxx20-linux-gcc-compile-commands', 'echo skip-linux-gcc-compile-commands')
        expect_fail(run_checker(repo), 'Linux GCC diagnostics must actively check compile commands')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', 'configure_cxx20_scan x265/source build/cxx20-warning-scan-all-12b-lib', 'echo skip-clang-12bit-lib-shape')
        expect_fail(run_checker(repo), 'missing required Build workflow guard snippet: configure_cxx20_scan x265/source build/cxx20-warning-scan-all-12b-lib')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_generated_text(repo / '.github' / 'workflows' / 'build.yml', 'check_cxx20_commands_clang build/cxx20-warning-scan-all             --required-file-flag=source/common/version.cpp=-DLINKED_8BIT=1', 'check_cxx20_commands_clang build/cxx20-warning-scan-12bit             --required-file-flag=source/common/version.cpp=-DLINKED_8BIT=1')
        expect_fail(run_checker(repo), 'C++20 warning scan must actively check all-bit-depth warning-scan compile commands target')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', 'check_cxx20_commands_gcc build/cxx20-gcc-compile-commands-12bit', 'check_cxx20_commands_gcc build/cxx20-gcc-compile-commands')
        expect_fail(run_checker(repo), 'missing required Build workflow guard snippet: check_cxx20_commands_gcc build/cxx20-gcc-compile-commands-12bit')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', 'check_cxx20_commands_gcc build/cxx20-gcc-compile-commands', 'echo skip-windows-gcc-base')
        expect_fail(run_checker(repo), 'Windows GCC diagnostics must actively check base compile commands')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', '--required-file-flag=source/common/winxp.cpp=-D_WIN32_WINNT=_WIN32_WINNT_WIN7', '--required-file-substring=source/common/winxp.cpp')
        expect_fail(run_checker(repo), 'Windows GCC diagnostics must actively require Win7 winxp.cpp macro')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', '--forbidden-file-flag=source/common/winxp.cpp=-D_WIN32_WINNT=_WIN32_WINNT_WINXP', '--required-file-substring=source/common/winxp.cpp')
        expect_fail(run_checker(repo), 'Windows GCC diagnostics must actively reject WinXP winxp.cpp macro')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', '--forbidden-file-substring=source/common/winxp.cpp', '--required-file-substring=source/common/winxp.cpp')
        expect_fail(run_checker(repo), 'Linux GCC diagnostics must actively reject winxp.cpp')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', 'check_cxx20_commands_gcc build/cxx20-gcc-compile-commands-all', 'check_cxx20_commands_gcc build/cxx20-gcc-compile-commands-12bit')
        expect_fail(run_checker(repo), 'missing required Build workflow guard snippet: check_cxx20_commands_gcc build/cxx20-gcc-compile-commands-all')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', 'check_cxx20_commands_gcc build/cxx20-linux-gcc-compile-commands-12bit', 'check_cxx20_commands_gcc build/cxx20-linux-gcc-compile-commands')
        expect_fail(run_checker(repo), 'Linux GCC diagnostics must actively check 12-bit compile commands')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', 'check_cxx20_commands_gcc build/cxx20-linux-gcc-compile-commands', 'echo skip-linux-gcc-compile-commands\n          # check_cxx20_commands_gcc build/cxx20-linux-gcc-compile-commands')
        expect_fail(run_checker(repo), 'missing required Build workflow guard snippet: --required-file-substring=source/output/reconplay.cpp')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', 'build/cxx20-linux-gcc-compile-commands/x265 --input build/cxx20-linux-gcc-compile-commands/smoke_linux_gcc.yuv --input-res 64x64', 'build/cxx20-linux-gcc-compile-commands/x265 --input build/cxx20-linux-gcc-compile-commands/smoke_linux_gcc.yuv --input-res 128x128')
        expect_fail(run_checker(repo), 'Linux GCC smoke --input-res must be 64x64, got 128x128')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', '--output build/cxx20-linux-gcc-compile-commands/smoke_linux_gcc.hevc', '--output build/cxx20-linux-gcc-compile-commands/wrong.hevc')
        expect_fail(run_checker(repo), 'Linux GCC smoke --output must be build/cxx20-linux-gcc-compile-commands/smoke_linux_gcc.hevc, got build/cxx20-linux-gcc-compile-commands/wrong.hevc')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', 'ninja -C build/cxx20-gcc-compile-commands cli', 'echo skip-windows-gcc-base-cli\n          # ninja -C build/cxx20-gcc-compile-commands cli')
        expect_fail(run_checker(repo), 'Windows GCC diagnostics must actively build base CLI')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', 'check_cxx20_commands_clang build/cxx20-warning-scan-shared-library', 'echo skip-clang-shared-library-shape\n          # check_cxx20_commands_clang build/cxx20-warning-scan-shared-library')
        expect_fail(run_checker(repo), 'C++20 warning scan must actively check shared-library compile commands')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', 'check_cxx20_commands_clang build/cxx20-warning-scan-all-8b-lib', 'echo skip-clang-all-8b-lib-shape\n          # check_cxx20_commands_clang build/cxx20-warning-scan-all-8b-lib')
        expect_fail(run_checker(repo), 'C++20 warning scan must actively check all 8-bit lib compile commands')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', 'test -s build/cxx20-linux-gcc-compile-commands/smoke_linux_gcc.log', '# test -s build/cxx20-linux-gcc-compile-commands/smoke_linux_gcc.log')
        expect_fail(run_checker(repo), 'missing required Build workflow guard snippet: test -s build/cxx20-linux-gcc-compile-commands/smoke_linux_gcc.log')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_generated_text(repo / '.github' / 'workflows' / 'build.yml', 'configure_cxx20_scan x265/source build/cxx20-warning-scan             -DENABLE_ZIMG=ON', 'configure_cxx20_scan x265/source build/cxx20-warning-scan-12bit             -DENABLE_ZIMG=ON')
        expect_fail(run_checker(repo), 'C++20 warning scan must actively configure base warning-scan target')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_generated_text(repo / '.github' / 'workflows' / 'build.yml', 'check_cxx20_commands_clang build/cxx20-warning-scan             --required-file-substring=source/filters/zimgfilter.cpp', 'check_cxx20_commands_clang build/cxx20-warning-scan-12bit             --required-file-substring=source/filters/zimgfilter.cpp')
        expect_fail(run_checker(repo), 'C++20 warning scan must actively check base warning-scan compile commands target')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_generated_text(repo / '.github' / 'workflows' / 'build.yml', 'check_cxx20_commands_clang build/cxx20-warning-scan-shared-deps             --required-file-flag=source/input/lavf.cpp=-DENABLE_LAVF', 'check_cxx20_commands_clang build/cxx20-warning-scan-12bit             --required-file-flag=source/input/lavf.cpp=-DENABLE_LAVF')
        expect_fail(run_checker(repo), 'C++20 warning scan must actively check shared-deps warning-scan compile commands target')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_generated_text(repo / '.github' / 'workflows' / 'build.yml', 'configure_cxx20_scan x265/source build/cxx20-warning-scan-shared-deps-asm             -DENABLE_ASSEMBLY=ON', 'configure_cxx20_scan x265/source build/cxx20-warning-scan-shared-deps             -DENABLE_ASSEMBLY=ON')
        expect_fail(run_checker(repo), 'C++20 warning scan must actively configure shared deps asm build')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', 'mingw-w64-clang-x86_64-zimg', 'mingw-w64-clang-x86_64-python')
        expect_fail(run_checker(repo), 'C++20 warning scan dependency setup must install mingw-w64-clang-x86_64-zimg')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', '--required-file-flag=source/filters/zimgfilter.cpp=-DENABLE_ZIMG', '--required-file-substring=source/filters/zimgfilter.cpp')
        expect_fail(run_checker(repo), 'missing required Build workflow guard snippet: --required-file-flag=source/filters/zimgfilter.cpp=-DENABLE_ZIMG')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(
            repo / '.github' / 'workflows' / 'build.yml',
            'build/cxx20-warning-scan/x265.exe --input build/cxx20-warning-scan/smoke_zimg.yuv --input-res 96x96 --fps 1 --frames 1 --vf "zimg:lanczos(64,64)" --output build/cxx20-warning-scan/smoke_zimg.hevc 2>&1 | tee build/cxx20-warning-scan/smoke_zimg.log',
            '# build/cxx20-warning-scan/x265.exe --input build/cxx20-warning-scan/smoke_zimg.yuv --input-res 96x96 --fps 1 --frames 1 --vf "zimg:lanczos(64,64)" --output build/cxx20-warning-scan/smoke_zimg.hevc 2>&1 | tee build/cxx20-warning-scan/smoke_zimg.log',
        )
        expect_fail(run_checker(repo), 'missing required Build workflow guard snippet: --vf "zimg:lanczos(64,64)"')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(
            repo / '.github' / 'workflows' / 'build.yml',
            'build/cxx20-warning-scan/x265.exe --input build/cxx20-warning-scan/smoke_zimg.yuv --input-res 96x96 --fps 1 --frames 1 --vf "zimg:lanczos(64,64)" --output build/cxx20-warning-scan/smoke_zimg.hevc 2>&1 | tee build/cxx20-warning-scan/smoke_zimg.log',
            'build/cxx20-warning-scan/x265.exe --input build/cxx20-warning-scan/wrong.yuv --input-res 96x96 --fps 1 --frames 1 --vf "zimg:lanczos(64,64)" --output build/cxx20-warning-scan/smoke_zimg.hevc 2>&1 | tee build/cxx20-warning-scan/smoke_zimg.log',
        )
        expect_fail(run_checker(repo), 'ZIMG smoke --input must be build/cxx20-warning-scan/smoke_zimg.yuv, got build/cxx20-warning-scan/wrong.yuv')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(
            repo / '.github' / 'workflows' / 'build.yml',
            'build/cxx20-warning-scan/x265.exe --input build/cxx20-warning-scan/smoke_zimg.yuv --input-res 96x96 --fps 1 --frames 1 --vf "zimg:lanczos(64,64)" --output build/cxx20-warning-scan/smoke_zimg.hevc 2>&1 | tee build/cxx20-warning-scan/smoke_zimg.log',
            'build/cxx20-warning-scan/x265.exe --input build/cxx20-warning-scan/smoke_zimg.yuv --input-res 128x128 --fps 1 --frames 1 --vf "zimg:lanczos(64,64)" --output build/cxx20-warning-scan/smoke_zimg.hevc 2>&1 | tee build/cxx20-warning-scan/smoke_zimg.log',
        )
        expect_fail(run_checker(repo), 'ZIMG smoke --input-res must be 96x96, got 128x128')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(
            repo / '.github' / 'workflows' / 'build.yml',
            'build/cxx20-warning-scan/x265.exe --input build/cxx20-warning-scan/smoke_zimg.yuv --input-res 96x96 --fps 1 --frames 1 --vf "zimg:lanczos(64,64)" --output build/cxx20-warning-scan/smoke_zimg.hevc 2>&1 | tee build/cxx20-warning-scan/smoke_zimg.log',
            'build/cxx20-warning-scan/x265.exe --input build/cxx20-warning-scan/smoke_zimg.yuv --input-res 96x96 --fps 1 --frames 2 --vf "zimg:lanczos(64,64)" --output build/cxx20-warning-scan/smoke_zimg.hevc 2>&1 | tee build/cxx20-warning-scan/smoke_zimg.log',
        )
        expect_fail(run_checker(repo), 'ZIMG smoke --frames must be 1, got 2')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(
            repo / '.github' / 'workflows' / 'build.yml',
            'build/cxx20-warning-scan/x265.exe --input build/cxx20-warning-scan/smoke_zimg.yuv --input-res 96x96 --fps 1 --frames 1 --vf "zimg:lanczos(64,64)" --output build/cxx20-warning-scan/smoke_zimg.hevc 2>&1 | tee build/cxx20-warning-scan/smoke_zimg.log',
            'build/cxx20-warning-scan/x265.exe --input build/cxx20-warning-scan/smoke_zimg.yuv --input-res 96x96 --fps 1 --frames 1 --vf "zimg:lanczos(64,64)" --output build/cxx20-warning-scan/wrong.hevc 2>&1 | tee build/cxx20-warning-scan/smoke_zimg.log',
        )
        expect_fail(run_checker(repo), 'expected exactly two ZIMG x265 commands, found 1')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', 'test -s build/cxx20-warning-scan/smoke_zimg.hevc', '# test -s build/cxx20-warning-scan/smoke_zimg.hevc')
        expect_fail(run_checker(repo), 'ZIMG smoke must require non-empty HEVC output')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', "grep -Fq 'encoded 1 frames' build/cxx20-warning-scan/smoke_zimg.log", "grep -Fq 'encoded' build/cxx20-warning-scan/smoke_zimg.log")
        expect_fail(run_checker(repo), 'missing required Build workflow guard snippet: grep -Fq \'encoded 1 frames\' build/cxx20-warning-scan/smoke_zimg.log')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', 'test -s build/cxx20-warning-scan/smoke_zimg_bypass.hevc', '# test -s build/cxx20-warning-scan/smoke_zimg_bypass.hevc')
        expect_fail(run_checker(repo), 'ZIMG bypass smoke must require non-empty HEVC output')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', "grep -Fq 'zimg [info]: Nothing to do. Bypassing' build/cxx20-warning-scan/smoke_zimg_bypass.log", "grep -Fq 'Nothing to do' build/cxx20-warning-scan/smoke_zimg_bypass.log")
        expect_fail(run_checker(repo), 'missing required Build workflow guard snippet: grep -Fq \'zimg [info]: Nothing to do. Bypassing\' build/cxx20-warning-scan/smoke_zimg_bypass.log')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', "grep -Fq 'Filter parameters exceeds supported length' build/cxx20-warning-scan/smoke_zimg_longparam.log", "grep -Fq 'supported length' build/cxx20-warning-scan/smoke_zimg_longparam.log")
        expect_fail(run_checker(repo), 'missing required Build workflow guard snippet: grep -Fq \'Filter parameters exceeds supported length\' build/cxx20-warning-scan/smoke_zimg_longparam.log')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', "grep -Fq 'Filter name exceeds supported length' build/cxx20-warning-scan/smoke_filter_longname.log", "grep -Fq 'supported length' build/cxx20-warning-scan/smoke_filter_longname.log")
        expect_fail(run_checker(repo), 'missing required Build workflow guard snippet: grep -Fq \'Filter name exceeds supported length\' build/cxx20-warning-scan/smoke_filter_longname.log')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', '--input-depth 12 --output-depth 12 --fps 1', '--input-depth 10 --output-depth 12 --fps 1')
        expect_fail(run_checker(repo), '12-bit warning-scan smoke --input-depth must be 12, got 10')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', 'test -s build/cxx20-warning-scan-12bit/smoke_12bit.hevc', '# test -s build/cxx20-warning-scan-12bit/smoke_12bit.hevc')
        expect_fail(run_checker(repo), '12-bit warning-scan smoke must require non-empty HEVC output')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', '--output build/cxx20-warning-scan-shared-library/smoke_shared.hevc', '--output build/cxx20-warning-scan-shared-library/wrong.hevc')
        expect_fail(run_checker(repo), 'shared-library warning-scan smoke --output must be build/cxx20-warning-scan-shared-library/smoke_shared.hevc, got build/cxx20-warning-scan-shared-library/wrong.hevc')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', '--input-depth 10 --output-depth 10 --fps 1', '--input-depth 10 --output-depth 8 --fps 1')
        expect_fail(run_checker(repo), 'all-bit-depth warning-scan smoke --output-depth must be 10, got 8')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', 'test -s build/cxx20-warning-scan-all/smoke_all.hevc', '# test -s build/cxx20-warning-scan-all/smoke_all.hevc')
        expect_fail(run_checker(repo), 'all-bit-depth warning-scan smoke must require non-empty HEVC output')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', 'build/all/x265.exe --input smoke_mkv.y4m --input-res 160x90', 'build/all/x265.exe --input smoke_mkv.y4m --input-res 128x72')
        expect_fail(run_checker(repo), 'MKV smoke --input-res must be 160x90, got 128x72')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', '--frames 12 --output smoke_mkv.mkv', '--frames 8 --output smoke_mkv.mkv')
        expect_fail(run_checker(repo), 'MKV smoke --frames must be 12, got 8')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', 'build/all/x265.exe --input smoke_mkv.y4m', 'build/8b/x265.exe --input smoke_mkv.y4m')
        expect_fail(run_checker(repo), 'MKV smoke must run build/all/x265.exe, got build/8b/x265.exe')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', 'test -s smoke_mkv.mkv', '# test -s smoke_mkv.mkv')
        expect_fail(run_checker(repo), 'MKV smoke must require non-empty MKV output')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', 'grep -q "nb_read_frames=12" smoke_mkv_count.txt', 'grep -q "nb_read_frames=8" smoke_mkv_count.txt')
        expect_fail(run_checker(repo), 'MKV smoke must require 12 decoded frames')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', 'ffprobe -v error -show_entries stream=codec_name,codec_type,width,height -select_streams v:0 -of default=noprint_wrappers=1 smoke_mkv.mkv > smoke_mkv_stream.txt', 'ffprobe -v error -show_entries stream=codec_name,codec_type -select_streams v:0 -of default=noprint_wrappers=1 smoke_mkv.mkv > smoke_mkv_stream.txt')
        expect_fail(run_checker(repo), 'MKV smoke must capture video stream probe output')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', '-c:v ffv1 smoke_lavf_input.mkv', '-c:v rawvideo smoke_lavf_input.mkv')
        expect_fail(run_checker(repo), 'LAVF input generator -c:v must be ffv1, got rawvideo')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', 'build/all/x265.exe --input smoke_lavf_input.mkv', 'build/8b/x265.exe --input smoke_lavf_input.mkv')
        expect_fail(run_checker(repo), 'LAVF smoke must run build/all/x265.exe, got build/8b/x265.exe')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', '--input smoke_lavf_input.mkv --frames 12', '--input smoke_lavf_wrong.mkv --frames 12')
        expect_fail(run_checker(repo), 'LAVF smoke --input must be smoke_lavf_input.mkv, got smoke_lavf_wrong.mkv')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', 'grep -Fq "lavf" smoke_lavf_log.txt', 'grep -Fq "hevc" smoke_lavf_log.txt')
        expect_fail(run_checker(repo), 'LAVF smoke must require lavf runtime log')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', '2>&1 | tee smoke_lavf_log.txt', '2>&1')
        expect_fail(run_checker(repo), 'LAVF smoke must capture x265 log to smoke_lavf_log.txt')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', 'grep -q "nb_read_frames=12" smoke_lavf_count.txt', 'grep -q "nb_read_frames=1" smoke_lavf_count.txt')
        expect_fail(run_checker(repo), 'LAVF smoke must require 12 decoded frames')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', 'build/all/x265.exe --input smoke_gop.y4m', 'build/8b/x265.exe --input smoke_gop.y4m')
        expect_fail(run_checker(repo), 'GOP smoke must run build/all/x265.exe, got build/8b/x265.exe')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', '--frames 16 --bframes 0 --keyint 8 --min-keyint 8 --no-open-gop --output smoke_gop.gop', '--frames 16 --bframes 0 --keyint 16 --min-keyint 8 --no-open-gop --output smoke_gop.gop')
        expect_fail(run_checker(repo), 'GOP smoke --keyint must be 8, got 16')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', 'gop_muxer.exe smoke_gop.gop', 'gop_muxer.exe wrong.gop')
        expect_fail(run_checker(repo), 'missing required Build workflow guard snippet: gop_muxer.exe smoke_gop.gop')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', '9 K 20', '9 K 18')
        expect_fail(run_checker(repo), 'QPFile smoke must require frame 9 K 20 entry')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', '--qpfile smoke_qpfile.txt --output smoke_qpfile.hevc', '--qpfile wrong_qpfile.txt --output smoke_qpfile.hevc')
        expect_fail(run_checker(repo), 'QPFile smoke --qpfile must be smoke_qpfile.txt, got wrong_qpfile.txt')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', '6 --bitrate 500', '6 --bitrate 450')
        expect_fail(run_checker(repo), 'Zonefile smoke must require frame 6 bitrate override')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', '--bitrate 400 --zonefile smoke_zonefile.txt --output smoke_zonefile.hevc', '--bitrate 350 --zonefile smoke_zonefile.txt --output smoke_zonefile.hevc')
        expect_fail(run_checker(repo), 'Zonefile smoke --bitrate must be 400, got 350')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', '--recon smoke_recon_out.y4m --output smoke_recon.hevc', '--output smoke_recon.hevc')
        expect_fail(run_checker(repo), 'missing Recon smoke value for --recon')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', "grep -q '^YUV4MPEG2 ' smoke_recon_out.y4m", "grep -q '^FRAME' smoke_recon_out.y4m")
        expect_fail(run_checker(repo), 'Recon smoke must require YUV4MPEG2 header in recon output')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', 'test "$(wc -l < smoke_gop_data_files.txt)" -eq 2', '# test "$(wc -l < smoke_gop_data_files.txt)" -eq 2')
        expect_fail(run_checker(repo), 'GOP smoke must require exactly two gop-data sidecars')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', "awk -F= '/^extradata_size=/{ if (($2+0) > 0) found=1 } END { if (!found) exit 1 }' smoke_gop_mux_stream.txt", "# awk -F= '/^extradata_size=/{ if (($2+0) > 0) found=1 } END { if (!found) exit 1 }' smoke_gop_mux_stream.txt")
        expect_fail(run_checker(repo), 'GOP smoke must require positive extradata_size in muxed MP4 stream')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', '--no-open-gop --output smoke.mp4', '--open-gop --output smoke.mp4')
        expect_fail(run_checker(repo), 'missing MP4 smoke argument: --no-open-gop')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', 'assert_common_mp4 smoke 128 72 yuv420p 24/1 16 1/24000', 'assert_common_mp4 smoke 128 72 yuv420p 24/1 12 1/24000')
        expect_fail(run_checker(repo), 'MP4 smoke must require common MP4 stream properties')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', "awk -F, '$1 == 1 { kf++; if (kf == 2 && NR != 9) exit 1 } END { if (kf < 2) exit 1 }' smoke_frames.csv", "# awk -F, '$1 == 1 { kf++; if (kf == 2 && NR != 9) exit 1 } END { if (kf < 2) exit 1 }' smoke_frames.csv")
        expect_fail(run_checker(repo), 'MP4 smoke must require second keyframe at frame 9')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', 'build/all/x265.exe --input smoke_open.y4m', 'build/8b/x265.exe --input smoke_open.y4m')
        expect_fail(run_checker(repo), 'expected exactly one MP4 open-GOP smoke x265 command, found 0')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', "assert_mp4_markers smoke_open.mp4 iso6 sgpd sbgp 'rap '", 'assert_mp4_markers smoke_open.mp4 iso6 hvc1 hvcC')
        expect_fail(run_checker(repo), 'MP4 open-GOP smoke must require sample-group markers')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', 'if (($1+0) < 0.30 || ($1+0) > 0.38) exit 1', 'if (($1+0) < 0.10 || ($1+0) > 0.20) exit 1')
        expect_fail(run_checker(repo), 'MP4 open-GOP smoke must require second key packet timing window')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', '--cra-nal --output smoke_cra.mp4', '--output smoke_cra.mp4')
        expect_fail(run_checker(repo), 'missing MP4 CRA smoke argument: --cra-nal')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', "awk -F, '$1 == 1 { kf++ } END { if (kf != 16) exit 1 }' smoke_cra_frames.csv", "awk -F, '$1 == 1 { kf++ } END { if (kf != 1) exit 1 }' smoke_cra_frames.csv")
        expect_fail(run_checker(repo), 'MP4 CRA smoke must require every frame keyframe-marked')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', 'make_y4m smoke_single.y4m 24 1 yuv420p', 'make_y4m smoke_single.y4m 24 2 yuv420p')
        expect_fail(run_checker(repo), 'MP4 single-frame smoke must generate 1-frame yuv420p input')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', '--frames 1 --bframes 0 --keyint 1 --min-keyint 1 --output smoke_single.mp4', '--frames 2 --bframes 0 --keyint 1 --min-keyint 1 --output smoke_single.mp4')
        expect_fail(run_checker(repo), 'MP4 single-frame smoke --frames must be 1, got 2')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', 'make_y4m smoke_single_frac.y4m 24000/1001 1 yuv420p', 'make_y4m smoke_single_frac.y4m 24000/1001 2 yuv420p')
        expect_fail(run_checker(repo), 'MP4 single-frame 24000/1001 smoke must generate 1-frame yuv420p input')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', 'assert_single_frame_mp4 smoke_single_frac 0.06 0.03 0.06', 'assert_single_frame_mp4 smoke_single_frac 0.04 0.01 0.04')
        expect_fail(run_checker(repo), 'MP4 single-frame 24000/1001 smoke must require single-frame timing window')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', '--frames 0 --bframes 0 --keyint 1 --min-keyint 1 --output smoke_zero.mp4', '--frames 1 --bframes 0 --keyint 1 --min-keyint 1 --output smoke_zero.mp4')
        expect_fail(run_checker(repo), 'MP4 frames=0 smoke --frames must be 0, got 1')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', '--sar 4:3 --range limited --colorprim bt709 --transfer bt709 --colormatrix bt709 --output smoke_vui.mp4', '--sar 1:1 --range limited --colorprim bt709 --transfer bt709 --colormatrix bt709 --output smoke_vui.mp4')
        expect_fail(run_checker(repo), 'MP4 VUI smoke --sar must be 4:3, got 1:1')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', 'grep -q "color_primaries=bt709" smoke_vui_stream.txt', 'grep -q "color_primaries=unknown" smoke_vui_stream.txt')
        expect_fail(run_checker(repo), 'MP4 VUI smoke must require bt709 primaries metadata')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', '--strict-cbr --hrd --output smoke_strict_cbr.mp4', '--strict-cbr --output smoke_strict_cbr.mp4')
        expect_fail(run_checker(repo), 'missing MP4 strict-CBR smoke argument: --hrd')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', 'echo "strict-cbr MP4 encode unexpectedly succeeded"', 'echo "strict-cbr unexpectedly succeeded"')
        expect_fail(run_checker(repo), 'MP4 strict-CBR smoke must fail if strict-CBR MP4 encode unexpectedly succeeds')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', 'make_y4m smoke_frac.y4m 24000/1001 24 yuv420p', 'make_y4m smoke_frac.y4m 24 24 yuv420p')
        expect_fail(run_checker(repo), 'MP4 24000/1001 smoke must generate 24-frame yuv420p input')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', "awk -F, '$3 ~ /K/ { kf++; if (kf == 2 && NR != 13) exit 1 } END { if (kf < 2) exit 1 }' smoke_frac_packets.csv", "awk -F, '$3 ~ /K/ { kf++; if (kf == 2 && NR != 9) exit 1 } END { if (kf < 2) exit 1 }' smoke_frac_packets.csv")
        expect_fail(run_checker(repo), 'MP4 24000/1001 smoke must require second key packet at packet 13')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', '--bframes 4 --b-pyramid --keyint 8', '--bframes 4 --keyint 8')
        expect_fail(run_checker(repo), 'missing MP4 B-pyramid smoke argument: --b-pyramid')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', '--aud --output smoke_aud.mp4', '--output smoke_aud.mp4')
        expect_fail(run_checker(repo), 'missing MP4 AUD smoke argument: --aud')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', '--eos --eob --output smoke_eos.mp4', '--eos --output smoke_eos.mp4')
        expect_fail(run_checker(repo), 'missing MP4 EOS/EOB smoke argument: --eob')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', '--no-open-gop --idr-recovery-sei --output smoke_recovery.mp4', '--no-open-gop --output smoke_recovery.mp4')
        expect_fail(run_checker(repo), 'missing MP4 IDR recovery smoke argument: --idr-recovery-sei')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'update-deps.yml', 'python .github/scripts/check_ci_guards.py', 'python .github/scripts/check_dependency_patch_suffixes.py')
        expect_fail(run_checker(repo), 'missing required update-deps guard snippet: python .github/scripts/check_ci_guards.py')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'actions' / 'setup-windows-deps' / 'action.yml', 'gop-muxer-cache-suffix:', 'gop-muxer-cache-label:')
        expect_fail(run_checker(repo), 'missing dependency update anchor: gop-muxer-cache-suffix:')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build-profiling.yml', 'needs: validate-guardrails', '# needs removed')
        expect_fail(run_checker(repo), 'Build Profiling build job must need validate-guardrails')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build-profiling.yml', '/clang64/bin/*) ;;', '/usr/local/bin/*) ;;')
        expect_fail(run_checker(repo), 'missing required Build Profiling workflow guard snippet: /clang64/bin/*) ;;')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build-profiling.yml', './profdata-dist/llvm-profdata.exe show profile-smoke-all.profdata >/dev/null', 'test -s profile-smoke-all.profdata')
        expect_fail(run_checker(repo), 'missing required Build Profiling workflow guard snippet: ./profdata-dist/llvm-profdata.exe show profile-smoke-all.profdata >/dev/null')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build-profiling.yml', 'test -s profile-smoke-8b.profdata', 'echo skip-profile-8b-profdata')
        expect_fail(run_checker(repo), 'missing required Build Profiling workflow guard snippet: test -s profile-smoke-8b.profdata')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build-profiling.yml', 'test -s smoke_profile_12b.mp4', 'echo skip-profile-12b-mp4')
        expect_fail(run_checker(repo), 'missing required Build Profiling workflow guard snippet: test -s smoke_profile_12b.mp4')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build-profiling.yml', 'test -s smoke_profile_all.mp4', 'echo skip-profile-all-mp4')
        expect_fail(run_checker(repo), 'missing required Build Profiling workflow guard snippet: test -s smoke_profile_all.mp4')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'actions' / 'setup-windows-deps' / 'action.yml', 'c++ -O2 --std=gnu++20 -I/usr/local/include -c gop_muxer.cpp -o gop_muxer.o', 'c++ -O2 -I/usr/local/include -c gop_muxer.cpp -o gop_muxer.o')
        expect_fail(run_checker(repo), 'missing required setup-windows-deps guard snippet: c++ -O2 --std=gnu++20 -I/usr/local/include -c gop_muxer.cpp -o gop_muxer.o')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'actions' / 'build-x265-profiling' / 'action.yml', 'check_cxx20_commands_profiling build/12b', 'echo skip-12b-guard')
        expect_fail(run_checker(repo), 'missing required Build Profiling action guard snippet: check_cxx20_commands_profiling build/12b')

    print('CI guard script guardrails validated')


if __name__ == '__main__':
    main()
