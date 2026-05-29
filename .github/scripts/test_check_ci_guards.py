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

    github_dir = Path(__file__).resolve().parents[1]
    (workflows / 'build.yml').write_text((github_dir / 'workflows' / 'build.yml').read_text())
    (workflows / 'build-profiling.yml').write_text((github_dir / 'workflows' / 'build-profiling.yml').read_text())
    (workflows / 'update-deps.yml').write_text((github_dir / 'workflows' / 'update-deps.yml').read_text())
    (setup_action / 'action.yml').write_text((github_dir / 'actions' / 'setup-windows-deps' / 'action.yml').read_text())
    (profiling_action / 'action.yml').write_text((github_dir / 'actions' / 'build-x265-profiling' / 'action.yml').read_text())
    (scripts / 'check_dependency_patch_suffixes.py').write_text(Path(__file__).with_name('check_dependency_patch_suffixes.py').read_text())
    helper_text = Path(__file__).with_name('cxx20_scan_helpers.sh').read_text()
    (scripts / 'cxx20_scan_helpers.sh').write_text(helper_text)
    mp4_helper_text = Path(__file__).with_name('mp4_smoke_helpers.sh').read_text()
    (scripts / 'mp4_smoke_helpers.sh').write_text(mp4_helper_text)
    profiling_helper_text = Path(__file__).with_name('profiling_smoke_package_verify.sh').read_text()
    (scripts / 'profiling_smoke_package_verify.sh').write_text(profiling_helper_text)
    archive_helper_text = Path(__file__).with_name('verify_ci_archive.sh').read_text()
    (scripts / 'verify_ci_archive.sh').write_text(archive_helper_text)
    runtime_suite_text = Path(__file__).with_name('runtime_smoke_suite.sh').read_text()
    (scripts / 'runtime_smoke_suite.sh').write_text(runtime_suite_text)
    mp4_suite_text = Path(__file__).with_name('mp4_smoke_suite.sh').read_text()
    (scripts / 'mp4_smoke_suite.sh').write_text(mp4_suite_text)
    (repo / '.github' / 'deps-cache.json').write_text('''{
  "lsmash": "04e39f1fb232c332d4b04a1043c02c7c2d282d00",
  "obuparse": "v2.0.2",
  "gop_muxer": "5677cf5ef905c2412ed31de300cd1a08b341d21d"
}\n''')
    (patches / 'l-smash-clang-coff-refptr.patch').write_text('lsmash patch\n')
    (patches / 'gop-muxer-lsmash-add-box.patch').write_text('gop patch\n')


def replace_text(path, old, new, count=1):
    text = path.read_text()
    if old not in text:
        repo = path.parents[2]
        for fallback in sorted((repo / '.github').rglob('*')):
            if not fallback.is_file():
                continue
            fallback_text = fallback.read_text()
            if old in fallback_text:
                fallback.write_text(fallback_text.replace(old, new, count))
                return
        raise AssertionError(f'missing text {old!r}')
    path.write_text(text.replace(old, new, count))


def main():
    if not shutil.which('bash'):
        print('bash is unavailable; skipping CI guard tests')
        return

    def build_workflow(repo):
        return repo / '.github' / 'workflows' / 'build.yml'

    def profiling_workflow(repo):
        return repo / '.github' / 'workflows' / 'build-profiling.yml'

    def update_deps_workflow(repo):
        return repo / '.github' / 'workflows' / 'update-deps.yml'

    def windows_deps_action(repo):
        return repo / '.github' / 'actions' / 'setup-windows-deps' / 'action.yml'

    def profiling_action(repo):
        return repo / '.github' / 'actions' / 'build-x265-profiling' / 'action.yml'

    def scan_helper(repo):
        return repo / '.github' / 'scripts' / 'cxx20_scan_helpers.sh'

    def runtime_suite(repo):
        return repo / '.github' / 'scripts' / 'runtime_smoke_suite.sh'

    def mp4_suite(repo):
        return repo / '.github' / 'scripts' / 'mp4_smoke_suite.sh'

    def profiling_smoke_helper(repo):
        return repo / '.github' / 'scripts' / 'profiling_smoke_package_verify.sh'

    def archive_verify_helper(repo):
        return repo / '.github' / 'scripts' / 'verify_ci_archive.sh'

    def fail_case(modifier, expected):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            write_repo(repo)
            modifier(repo)
            expect_fail(run_checker(repo), expected)

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo)
        expect_pass(run_checker(repo))

    fail_case(
        lambda repo: replace_text(scan_helper(repo), '--forbidden-flag=-fprofile-instr-use', '--forbidden-flag=-fprofile-instr-generate'),
        'missing profiling compile_commands guard: --forbidden-flag=-fprofile-instr-use',
    )
    fail_case(
        lambda repo: replace_text(scan_helper(repo), '--forbidden-flag-substring=-fprofile-instr-use=', '--forbidden-flag-substring=-fprofile-instr-generate='),
        'missing profiling compile_commands guard: --forbidden-flag-substring=-fprofile-instr-use=',
    )
    fail_case(
        lambda repo: replace_text(build_workflow(repo), 'check_cxx20_commands_pgo_consume "$build_dir" --min-cpp-commands="$min_cpp_commands"', ': # check_cxx20_commands_pgo_consume "$build_dir" --min-cpp-commands="$min_cpp_commands"'),
        'missing required Build workflow guard snippet: check_cxx20_commands_pgo_consume "$build_dir" --min-cpp-commands="$min_cpp_commands"',
    )
    fail_case(
        lambda repo: replace_text(windows_deps_action(repo), 'c++ -O2 --std=gnu++20 -I/usr/local/include -c gop_muxer.cpp -o gop_muxer.o', 'c++ -O2 --std=gnu++20 --std=gnu++17 -I/usr/local/include -c gop_muxer.cpp -o gop_muxer.o'),
        'missing required setup-windows-deps guard snippet: c++ -O2 --std=gnu++20 -I/usr/local/include -c gop_muxer.cpp -o gop_muxer.o',
    )
    fail_case(
        lambda repo: replace_text(windows_deps_action(repo), 'git -c core.autocrlf=false reset --hard HEAD\n        git apply --ignore-whitespace --check ${{ inputs.lsmash-patch-path }}', 'git apply --ignore-whitespace --check ${{ inputs.lsmash-patch-path }}'),
        'missing required setup-windows-deps guard snippet: git -c core.autocrlf=false reset --hard HEAD',
    )
    fail_case(
        lambda repo: replace_text(build_workflow(repo), '--forbidden-flag-substring=-std=gnu++17', '# --forbidden-flag-substring=-std=gnu++17'),
        'GNU++20 downgrade guard must reject GNU++17 flags',
    )
    fail_case(
        lambda repo: replace_text(build_workflow(repo), 'configure_cxx20_scan x265/source build/cxx20-downgrade-guard', 'configure_cxx20_scan x265/source build/cxx20-warning-scan'),
        'GNU++20 downgrade guard must actively configure downgrade build',
    )
    fail_case(
        lambda repo: replace_text(build_workflow(repo), 'for target_cpu in haswell arrowlake znver5; do', 'for target_cpu in haswell znver5; do'),
        'CPU warning scan must actively cover haswell/arrowlake/znver5 loop',
    )
    fail_case(
        lambda repo: replace_text(build_workflow(repo), 'check_cxx20_commands_clang build/cxx20-warning-scan-asm', 'check_cxx20_commands_clang build/cxx20-warning-scan'),
        'ASM warning scan must actively check asm compile commands target',
    )
    fail_case(
        lambda repo: replace_text(build_workflow(repo), '--required-file-substring=source/test/', '--required-file-substring=source/common/'),
        'ASM warning scan must actively require test sources',
    )
    fail_case(
        lambda repo: replace_text(
            build_workflow(repo),
            '--required-file-flag=source/input/lavf.cpp=-DENABLE_LAVF',
            '--required-file-substring=source/input/lavf.cpp',
            count=2,
        ),
        'C++20 warning scan must actively require LAVF macro',
    )
    fail_case(
        lambda repo: replace_text(build_workflow(repo), 'check_cxx20_commands_gcc build/cxx20-linux-gcc-compile-commands-12bit', 'echo skip-linux-gcc-12bit-shape'),
        'Linux GCC diagnostics must actively check 12-bit compile commands',
    )
    fail_case(
        lambda repo: replace_text(build_workflow(repo), 'check_cxx20_commands_gcc build/cxx20-gcc-compile-commands', 'echo skip-windows-gcc-base'),
        'Windows GCC diagnostics must actively check base compile commands',
    )
    fail_case(
        lambda repo: replace_text(build_workflow(repo), 'mingw-w64-clang-x86_64-zimg', 'mingw-w64-clang-x86_64-python'),
        'C++20 warning scan dependency setup must install mingw-w64-clang-x86_64-zimg',
    )
    fail_case(
        lambda repo: replace_text(build_workflow(repo), 'build/cxx20-linux-gcc-compile-commands/x265 --input build/cxx20-linux-gcc-compile-commands/smoke_linux_gcc.yuv --input-res 64x64', 'build/cxx20-linux-gcc-compile-commands/x265 --input build/cxx20-linux-gcc-compile-commands/smoke_linux_gcc.yuv --input-res 128x128'),
        'Linux GCC smoke --input-res must be 64x64, got 128x128',
    )
    fail_case(
        lambda repo: replace_text(build_workflow(repo), '  pull_request:', '  pull_request_disabled:'),
        'Build workflow must define pull_request trigger for pre-merge CI',
    )
    fail_case(
        lambda repo: replace_text(build_workflow(repo), "    if: github.event_name != 'pull_request'\n    runs-on: windows-latest", "    runs-on: windows-latest", count=1),
        'Build workflow job cxx20-warning-scan must be skipped for pull_request fast gate',
    )
    fail_case(
        lambda repo: replace_text(build_workflow(repo), '  linux-clang-sanitizers:', '  linux-clang-sanitizers-disabled:'),
        'Build workflow must include linux-clang-sanitizers PR fast gate job',
    )
    fail_case(
        lambda repo: replace_text(build_workflow(repo), '            enable_hdr10_plus=OFF', '            enable_hdr10_plus=ON', count=1),
        'sanitizer PR fast gate must disable HDR10+ for speed',
    )
    fail_case(
        lambda repo: replace_text(build_workflow(repo), '      - build\n    if: github.event_name', '      - build\n      - linux-clang-sanitizers\n    if: github.event_name'),
        'publish-release must not depend on PR fast-gate sanitizer job',
    )
    fail_case(
        lambda repo: replace_text(update_deps_workflow(repo), 'python .github/scripts/check_ci_guards.py', 'python .github/scripts/check_dependency_patch_suffixes.py'),
        'missing required update-deps guard snippet: python .github/scripts/check_ci_guards.py',
    )
    fail_case(
        lambda repo: replace_text(windows_deps_action(repo), 'gop-muxer-cache-suffix:', 'gop-muxer-cache-label:'),
        'missing dependency update anchor: gop-muxer-cache-suffix:',
    )
    fail_case(
        lambda repo: replace_text(profiling_workflow(repo), 'needs: validate-guardrails', '# needs removed'),
        'Build Profiling build job must need validate-guardrails',
    )
    fail_case(
        lambda repo: replace_text(profiling_smoke_helper(repo), './profdata-dist/llvm-profdata.exe show "$profdata" >/dev/null', 'test -s "$profdata"'),
        'profiling smoke helper missing detail: ./profdata-dist/llvm-profdata.exe show "$profdata" >/dev/null',
    )
    fail_case(
        lambda repo: replace_text(profiling_action(repo), 'check_cxx20_commands_profiling build/12b', 'echo skip-12b-guard'),
        'missing required Build Profiling action guard snippet: check_cxx20_commands_profiling build/12b',
    )
    fail_case(
        lambda repo: replace_text(archive_verify_helper(repo), 'verify_x265_release()', 'verify_x265_release_disabled()'),
        'archive verification helper missing function: verify_x265_release()',
    )

    fail_case(
        lambda repo: replace_text(runtime_suite(repo), 'build/all/x265.exe --input smoke_raw.y4m', 'build/8b/x265.exe --input smoke_raw.y4m'),
        'RAW smoke must run build/all/x265.exe, got build/8b/x265.exe',
    )
    fail_case(
        lambda repo: replace_text(runtime_suite(repo), "grep -Fq 'frame threads / pool features       : 1 / threaded-me' smoke_threaded_me_log.txt", "grep -Fq 'threaded-me' smoke_threaded_me_log.txt"),
        'Threaded ME smoke must require enabled threaded-me log',
    )
    fail_case(
        lambda repo: replace_text(runtime_suite(repo), 'for iteration in $(seq 1 12); do', 'for iteration in $(seq 1 1); do'),
        'Threaded ME stress smoke must run a 12-iteration loop',
    )
    fail_case(
        lambda repo: replace_text(runtime_suite(repo), "grep -Fq 'Input filename exceeds supported length' smoke_cli_long_input.log", "grep -Fq 'supported length' smoke_cli_long_input.log"),
        'CLI long-input smoke must require oversized --input error log',
    )
    fail_case(
        lambda repo: replace_text(runtime_suite(repo), '--frames 12 --output smoke_mkv.mkv', '--frames 8 --output smoke_mkv.mkv'),
        'MKV smoke --frames must be 12, got 8',
    )
    fail_case(
        lambda repo: replace_text(runtime_suite(repo), '2>&1 | tee smoke_lavf_log.txt', '2>&1'),
        'LAVF smoke must capture x265 log to smoke_lavf_log.txt',
    )
    fail_case(
        lambda repo: replace_text(runtime_suite(repo), '9 K 20', '9 K 18'),
        'QPFile smoke must require frame 9 K 20 entry',
    )
    fail_case(
        lambda repo: replace_text(runtime_suite(repo), '--bitrate 400 --zonefile smoke_zonefile.txt --output smoke_zonefile.hevc', '--bitrate 350 --zonefile smoke_zonefile.txt --output smoke_zonefile.hevc'),
        'Zonefile smoke --bitrate must be 400, got 350',
    )
    fail_case(
        lambda repo: replace_text(runtime_suite(repo), "grep -Fq 'Zone file entry exceeds supported argument count' smoke_zonefile_oversized.log", "grep -Fq 'supported argument count' smoke_zonefile_oversized.log"),
        'Zonefile oversized smoke must require argument-count error log',
    )
    fail_case(
        lambda repo: replace_text(runtime_suite(repo), '--recon smoke_recon_out.y4m --output smoke_recon.hevc', '--output smoke_recon.hevc'),
        'missing Recon smoke value for --recon',
    )
    fail_case(
        lambda repo: replace_text(runtime_suite(repo), "grep -Fq 'Incorrect system-id, aborting' smoke_vst_oversized.log", "grep -Fq 'system-id' smoke_vst_oversized.log"),
        'Video-signal-type-preset oversized smoke must require invalid system-id log',
    )
    fail_case(
        lambda repo: replace_text(runtime_suite(repo), 'test "$(wc -l < smoke_gop_data_files.txt)" -eq 2', '# test "$(wc -l < smoke_gop_data_files.txt)" -eq 2'),
        'GOP smoke must require exactly two gop-data sidecars',
    )
    fail_case(
        lambda repo: replace_text(runtime_suite(repo), "awk -F= '/^extradata_size=/{ if (($2+0) > 0) found=1 } END { if (!found) exit 1 }' smoke_gop_mux_stream.txt", "# awk -F= '/^extradata_size=/{ if (($2+0) > 0) found=1 } END { if (!found) exit 1 }' smoke_gop_mux_stream.txt"),
        'GOP smoke must require positive extradata_size in muxed MP4 stream',
    )

    fail_case(
        lambda repo: replace_text(mp4_suite(repo), '--no-open-gop --output smoke.mp4', '--open-gop --output smoke.mp4'),
        'missing MP4 smoke argument: --no-open-gop',
    )
    fail_case(
        lambda repo: replace_text(mp4_suite(repo), "assert_mp4_markers smoke_open.mp4 iso6 sgpd sbgp 'rap '", 'assert_mp4_markers smoke_open.mp4 iso6 hvc1 hvcC'),
        'MP4 open-GOP smoke must require sample-group markers',
    )
    fail_case(
        lambda repo: replace_text(mp4_suite(repo), '--cra-nal --output smoke_cra.mp4', '--output smoke_cra.mp4'),
        'missing MP4 CRA smoke argument: --cra-nal',
    )
    fail_case(
        lambda repo: replace_text(mp4_suite(repo), 'make_y4m smoke_single.y4m 24 1 yuv420p', 'make_y4m smoke_single.y4m 24 2 yuv420p'),
        'MP4 single-frame smoke must generate 1-frame yuv420p input',
    )
    fail_case(
        lambda repo: replace_text(mp4_suite(repo), 'assert_single_frame_mp4 smoke_single_frac 0.06 0.03 0.06', 'assert_single_frame_mp4 smoke_single_frac 0.04 0.01 0.04'),
        'MP4 single-frame 24000/1001 smoke must require single-frame timing window',
    )
    fail_case(
        lambda repo: replace_text(mp4_suite(repo), '--frames 0 --bframes 0 --keyint 1 --min-keyint 1 --output smoke_zero.mp4', '--frames 1 --bframes 0 --keyint 1 --min-keyint 1 --output smoke_zero.mp4'),
        'MP4 frames=0 smoke --frames must be 0, got 1',
    )
    fail_case(
        lambda repo: replace_text(mp4_suite(repo), '--sar 4:3 --range limited --colorprim bt709 --transfer bt709 --colormatrix bt709 --output smoke_vui.mp4', '--sar 1:1 --range limited --colorprim bt709 --transfer bt709 --colormatrix bt709 --output smoke_vui.mp4'),
        'MP4 VUI smoke --sar must be 4:3, got 1:1',
    )
    fail_case(
        lambda repo: replace_text(mp4_suite(repo), '--strict-cbr --hrd --output smoke_strict_cbr.mp4', '--strict-cbr --output smoke_strict_cbr.mp4'),
        'missing MP4 strict-CBR smoke argument: --hrd',
    )
    fail_case(
        lambda repo: replace_text(mp4_suite(repo), "awk -F, '$3 ~ /K/ { kf++; if (kf == 2 && NR != 13) exit 1 } END { if (kf < 2) exit 1 }' smoke_frac_packets.csv", "awk -F, '$3 ~ /K/ { kf++; if (kf == 2 && NR != 9) exit 1 } END { if (kf < 2) exit 1 }' smoke_frac_packets.csv"),
        'MP4 24000/1001 smoke must require second key packet at packet 13',
    )
    fail_case(
        lambda repo: replace_text(mp4_suite(repo), '--bframes 4 --b-pyramid --keyint 8', '--bframes 4 --keyint 8'),
        'missing MP4 B-pyramid smoke argument: --b-pyramid',
    )
    fail_case(
        lambda repo: replace_text(mp4_suite(repo), '--aud --output smoke_aud.mp4', '--output smoke_aud.mp4'),
        'missing MP4 AUD smoke argument: --aud',
    )
    fail_case(
        lambda repo: replace_text(mp4_suite(repo), '--eos --eob --output smoke_eos.mp4', '--eos --output smoke_eos.mp4'),
        'missing MP4 EOS/EOB smoke argument: --eob',
    )
    fail_case(
        lambda repo: replace_text(mp4_suite(repo), '--no-open-gop --idr-recovery-sei --output smoke_recovery.mp4', '--no-open-gop --output smoke_recovery.mp4'),
        'missing MP4 IDR recovery smoke argument: --idr-recovery-sei',
    )

    print('CI guard script guardrails validated')


if __name__ == '__main__':
    main()
