#!/usr/bin/env python3
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

CHECKER = Path(__file__).with_name('check_ci_guards.py')

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
      - name: Run C++20 shared and all-bit-depth warning scans
        shell: bash
        run: |
          configure_cxx20_scan x265/source build/cxx20-warning-scan-all-12b-lib
          ninja -C build/cxx20-warning-scan-all-12b-lib x265-static
          check_cxx20_commands_clang build/cxx20-warning-scan-all \
            --required-file-flag=source/common/version.cpp=-DLINKED_8BIT=1 \
            --required-file-flag=source/common/version.cpp=-DLINKED_12BIT=1 \
            --required-file-flag=source/encoder/api.cpp=-DLINKED_8BIT=1 \
            --required-file-flag=source/encoder/api.cpp=-DLINKED_12BIT=1 \
            --forbidden-file-flag=source/encoder/api.cpp=-DEXPORT_C_API=1
  cxx20-gcc-compile-commands:
    runs-on: windows-latest
    steps:
      - name: Run GCC C++20 compile command diagnostics
        shell: bash
        run: |
          set -euo pipefail
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
          build/cxx20-linux-gcc-compile-commands/x265 --input smoke.yuv --output build/cxx20-linux-gcc-compile-commands/smoke_linux_gcc.hevc 2>&1 | tee build/cxx20-linux-gcc-compile-commands/smoke_linux_gcc.log
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
          ninja -C build/cxx20-gcc-compile-commands-all cli
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
      - name: GOP Output Smoke (All CLI)
        shell: bash
        run: |
          gop_muxer.exe smoke_gop.gop
          test -s smoke_gop.gop
          test -s smoke_gop.options
          test -s smoke_gop.headers
          test -s smoke_gop-000000.hevc-gop-data
          test -s smoke_gop-000008.hevc-gop-data
          printf '%s\\n' smoke_gop-*.hevc-gop-data > smoke_gop_data_files.txt
          grep -Fxq 'smoke_gop-000000.hevc-gop-data' smoke_gop_data_files.txt
          grep -Fxq 'smoke_gop-000008.hevc-gop-data' smoke_gop_data_files.txt
          grep -q 'format_name=mov,mp4,m4a,3gp,3g2,mj2' smoke_gop_mux_format.txt
          test -s smoke_gop.mp4
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
    return subprocess.run(
        [sys.executable, str(CHECKER), '--repo-root', str(repo)],
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
        expect_fail(run_checker(repo), 'PGO consume helper must actively run: check_cxx20_commands_pgo_consume "$build_dir" --min-cpp-commands="$min_cpp_commands"')

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
        replace_text(repo / '.github' / 'workflows' / 'build.yml', 'testsrc2=size=160x90:rate=24', 'testsrc2=size=80x45:rate=24')
        expect_fail(run_checker(repo), 'missing required Build workflow guard snippet: ffmpeg -hide_banner -loglevel error -f lavfi -i testsrc2=size=160x90:rate=24 -frames:v 16 -pix_fmt yuv420p smoke_threaded_me.y4m')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', "grep -Fq 'frame threads / pool features       : 1 / threaded-me' smoke_threaded_me_log.txt", "grep -Fq 'threaded-me' smoke_threaded_me_log.txt\n          # grep -Fq 'frame threads / pool features       : 1 / threaded-me' smoke_threaded_me_log.txt")
        expect_fail(run_checker(repo), 'Threaded ME smoke must require enabled threaded-me log')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', 'grep -q \'nb_read_frames=16\' smoke_threaded_me_count.txt', 'grep -q \'nb_read_frames=2\' smoke_threaded_me_count.txt\n          # grep -q \'nb_read_frames=16\' smoke_threaded_me_count.txt')
        expect_fail(run_checker(repo), 'Threaded ME smoke must require 16 decoded frames')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', "build/all/x265.exe --input smoke_threaded_me.y4m --input-res 160x90 --fps 24 --frames 16 --preset medium --threaded-me --pools 32 --frame-threads 1 --no-wpp --no-progress --output smoke_threaded_me.hevc 2>&1 | tee smoke_threaded_me_log.txt", "build/all/x265.exe --input smoke_threaded_me.y4m --input-res 160x90 --fps 24 --frames 16 --preset medium --threaded-me --pools 16 --frame-threads 1 --no-wpp --no-progress --output smoke_threaded_me.hevc 2>&1 | tee smoke_threaded_me_log.txt\n          # --input-res 160x90 --fps 24 --frames 16 --preset medium --threaded-me --pools 32 --frame-threads 1 --no-wpp --no-progress")
        expect_fail(run_checker(repo), 'Threaded ME smoke --pools must be 32, got 16')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', "build/all/x265.exe --input smoke_threaded_me.y4m --input-res 160x90 --fps 24 --frames 16 --preset medium --threaded-me --pools 32 --frame-threads 1 --no-wpp --no-progress --output smoke_threaded_me.hevc 2>&1 | tee smoke_threaded_me_log.txt", "build/all/x265.exe --input smoke_threaded_me.y4m --input-res 160x90 --fps 24 --frames 16 --preset medium --pools 32 --frame-threads 1 --no-wpp --no-progress --output smoke_threaded_me.hevc 2>&1 | tee smoke_threaded_me_log.txt\n          # --input-res 160x90 --fps 24 --frames 16 --preset medium --threaded-me --pools 32 --frame-threads 1 --no-wpp --no-progress")
        expect_fail(run_checker(repo), 'missing Threaded ME smoke argument: --threaded-me')

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
        expect_fail(run_checker(repo), 'missing required Build workflow guard snippet: check_cxx20_commands_gcc build/cxx20-linux-gcc-compile-commands')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', 'configure_cxx20_scan x265/source build/cxx20-warning-scan-all-12b-lib', 'echo skip-clang-12bit-lib-shape')
        expect_fail(run_checker(repo), 'missing required Build workflow guard snippet: configure_cxx20_scan x265/source build/cxx20-warning-scan-all-12b-lib')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', 'check_cxx20_commands_gcc build/cxx20-gcc-compile-commands-12bit', 'echo skip-gcc-12bit-lib-shape')
        expect_fail(run_checker(repo), 'missing required Build workflow guard snippet: check_cxx20_commands_gcc build/cxx20-gcc-compile-commands-12bit')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', '--required-file-substring=source/output/reconplay.cpp', '--required-file-substring=source/output/')
        expect_fail(run_checker(repo), 'missing required Build workflow guard snippet: --required-file-substring=source/output/reconplay.cpp')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', '--required-file-flag=source/common/winxp.cpp=-D_WIN32_WINNT=_WIN32_WINNT_WIN7', '--required-file-substring=source/common/winxp.cpp')
        expect_fail(run_checker(repo), 'missing required Build workflow guard snippet: --required-file-flag=source/common/winxp.cpp=-D_WIN32_WINNT=_WIN32_WINNT_WIN7')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', '--forbidden-file-flag=source/common/winxp.cpp=-D_WIN32_WINNT=_WIN32_WINNT_WINXP', '--required-file-substring=source/common/winxp.cpp')
        expect_fail(run_checker(repo), 'missing required Build workflow guard snippet: --forbidden-file-flag=source/common/winxp.cpp=-D_WIN32_WINNT=_WIN32_WINNT_WINXP')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', '--forbidden-file-substring=source/common/winxp.cpp', '--required-file-substring=source/common/winxp.cpp')
        expect_fail(run_checker(repo), 'missing required Build workflow guard snippet: --forbidden-file-substring=source/common/winxp.cpp')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', 'check_cxx20_commands_gcc build/cxx20-gcc-compile-commands-all', 'echo skip-gcc-all-bit-depth-shape')
        expect_fail(run_checker(repo), 'missing required Build workflow guard snippet: check_cxx20_commands_gcc build/cxx20-gcc-compile-commands-all')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', 'check_cxx20_commands_gcc build/cxx20-linux-gcc-compile-commands', 'echo skip-linux-gcc-compile-commands\n          # check_cxx20_commands_gcc build/cxx20-linux-gcc-compile-commands')
        expect_fail(run_checker(repo), 'Linux GCC diagnostics must actively check compile commands')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', 'configure_cxx20_scan x265/source build/cxx20-warning-scan-all-12b-lib', 'echo skip-clang-12bit-lib-shape\n          # configure_cxx20_scan x265/source build/cxx20-warning-scan-all-12b-lib')
        expect_fail(run_checker(repo), 'C++20 warning scan must actively configure all 12-bit lib')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build.yml', 'check_cxx20_commands_gcc build/cxx20-gcc-compile-commands-12bit', 'echo skip-gcc-12bit-lib-shape\n          # check_cxx20_commands_gcc build/cxx20-gcc-compile-commands-12bit')
        expect_fail(run_checker(repo), 'Windows GCC diagnostics must actively check 12-bit compile commands')

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
