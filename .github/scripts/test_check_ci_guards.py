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
  cxx20-linux-gcc-compile-commands:
    runs-on: ubuntu-latest
    steps:
      - name: Smoke
        shell: bash
        run: |
          set -euo pipefail
          build/cxx20-linux-gcc-compile-commands/x265 --input smoke.yuv --output smoke_linux_gcc.hevc 2>&1 | tee smoke_linux_gcc.log
          test -s build/cxx20-linux-gcc-compile-commands/smoke_linux_gcc.hevc
          grep -Fq 'encoded 1 frames' smoke_linux_gcc.log
  build:
    runs-on: windows-latest
    steps:
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
      - name: Threaded ME Smoke
        shell: bash
        run: |
          build/all/x265.exe --threaded-me --pools 32 --frame-threads 1 --no-wpp --no-progress --output smoke_threaded_me.hevc 2>&1 | tee smoke_threaded_me_log.txt
          grep -Fq 'frame threads / pool features       : 1 / threaded-me' smoke_threaded_me_log.txt
          ! grep -Fq 'disabling --threaded-me' smoke_threaded_me_log.txt
          grep -q 'nb_read_frames=16' smoke_threaded_me_count.txt

'''

UPDATE_DEPS_YML = '''
name: Update Dependencies
on: workflow_dispatch
jobs:
  update-deps:
    runs-on: ubuntu-latest
    steps:
      - name: Update Dependency Refs
        shell: bash
        run: |
          set -euo pipefail
          python .github/scripts/check_ci_guards.py
          python .github/scripts/check_dependency_patch_suffixes.py
          for anchor in ffmpeg-ref mimalloc-ref obuparse-ref lsmash-ref lsmash-cache-suffix gop-muxer-ref gop-muxer-cache-suffix; do
            if ! grep -Fq "${anchor}:" .github/actions/setup-windows-deps/action.yml; then
              exit 1
            fi
          done
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
  build:
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
      - name: Setup Windows deps
        uses: ./.github/actions/setup-windows-deps
        with:
          enable-lsmash: 'ON'
      - name: Smoke, Package, and Verify 8b-lib
        shell: bash
        run: |
          test -s "$LLVM_PROFILE_FILE"
          test -s profile-smoke-8b.profdata
          ./profdata-dist/llvm-profdata.exe show profile-smoke-8b.profdata >/dev/null
          echo "- standard: gnu++20"
          echo "- mp4_roundtrip_frames: 12"
      - name: Smoke, Package, and Verify 12b-lib
        shell: bash
        run: |
          test -s "$LLVM_PROFILE_FILE"
          test -s profile-smoke-12b.profdata
          ./profdata-dist/llvm-profdata.exe show profile-smoke-12b.profdata >/dev/null
          echo "- standard: gnu++20"
          echo "- mp4_roundtrip_frames: 12"
      - name: Smoke, Package, and Verify All
        shell: bash
        run: |
          test -s "$LLVM_PROFILE_FILE"
          test -s profile-smoke-all.profdata
          ./profdata-dist/llvm-profdata.exe show profile-smoke-all.profdata >/dev/null
          echo "- standard: gnu++20"
          echo "- mp4_roundtrip_frames: 12"
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
  lsmash-ref:
    default: 04e39f1fb232c332d4b04a1043c02c7c2d282d00
  lsmash-cache-suffix:
    default: clang-coff-refptr-v2
  lsmash-patch-path:
    default: ../x265/.github/patches/l-smash-clang-coff-refptr.patch
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
        echo "=== Dependency provenance ==="
        echo "lsmash=${{ inputs.lsmash-repository }}@${{ inputs.lsmash-ref }} suffix=${{ inputs.lsmash-cache-suffix }} patch=${{ inputs.lsmash-patch-path }}"
        echo "gop_muxer=${{ inputs.gop-muxer-repository }}@${{ inputs.gop-muxer-ref }} suffix=${{ inputs.gop-muxer-cache-suffix }} patch=${{ inputs.gop-muxer-patch-path }}"
    - name: Compile L-SMASH
      shell: msys2 {0}
      run: |
        git apply --ignore-whitespace --check ${{ inputs.lsmash-patch-path }}
    - name: Compile GOP muxer
      shell: msys2 {0}
      run: |
        git -c core.autocrlf=false reset --hard HEAD
        git apply --check ${{ inputs.gop-muxer-patch-path }}
        git apply ${{ inputs.gop-muxer-patch-path }}
        c++ -O2 --std=gnu++20 -I/usr/local/include -c gop_muxer.cpp -o gop_muxer.o
'''

PROFILING_ACTION_YML = '''
name: Build x265 profiling binaries
runs:
  using: composite
  steps:
    - name: Probe
      shell: bash
      run: echo profiling
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
    (scripts / 'cxx20_scan_helpers.sh').write_text('#!/usr/bin/env bash\nset -euo pipefail\n')
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
        replace_text(repo / '.github' / 'workflows' / 'build.yml', "grep -Fq 'frame threads / pool features       : 1 / threaded-me' smoke_threaded_me_log.txt", "grep -Fq 'threaded-me' smoke_threaded_me_log.txt")
        expect_fail(run_checker(repo), 'missing required Build workflow guard snippet: frame threads / pool features       : 1 / threaded-me')

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
        replace_text(repo / '.github' / 'workflows' / 'build-profiling.yml', 'enable-lsmash: \'ON\'', 'enable-lsmash: \'OFF\'')
        expect_fail(run_checker(repo), "missing required Build Profiling workflow guard snippet: enable-lsmash: 'ON'")

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'workflows' / 'build-profiling.yml', './profdata-dist/llvm-profdata.exe show profile-smoke-all.profdata >/dev/null', 'test -s profile-smoke-all.profdata')
        expect_fail(run_checker(repo), 'missing required Build Profiling workflow guard snippet: ./profdata-dist/llvm-profdata.exe show profile-smoke-all.profdata >/dev/null')

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        replace_text(repo / '.github' / 'actions' / 'setup-windows-deps' / 'action.yml', 'c++ -O2 --std=gnu++20 -I/usr/local/include -c gop_muxer.cpp -o gop_muxer.o', 'c++ -O2 -I/usr/local/include -c gop_muxer.cpp -o gop_muxer.o')
        expect_fail(run_checker(repo), 'missing required setup-windows-deps guard snippet: c++ -O2 --std=gnu++20 -I/usr/local/include -c gop_muxer.cpp -o gop_muxer.o')

    print('CI guard script guardrails validated')


if __name__ == '__main__':
    main()
