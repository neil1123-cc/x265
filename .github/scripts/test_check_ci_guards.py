#!/usr/bin/env python3
import io
import sys
import tempfile
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from types import SimpleNamespace

import check_ci_guards as checker_module
from test_check_ci_guards_fixture import case, replace_text, write_repo

BASELINE_CHECKS = (
    'yaml-text',
    'yaml-parse',
    'run-blocks',
    'scan-helper',
    'mp4-smoke-helper',
    'runtime-smoke-suite',
    'mp4-smoke-suite',
    'required-snippets',
    'pgo-consume-helper',
    'raw-smoke',
    'mp4-smokes',
    'zimg-smoke',
    'warning-scan-runtime-smokes',
)
TARGETED_CHECKS = (
    'scan-helper',
    'required-snippets',
    'gnu20-diagnostic-steps',
    'warning-scan-dependencies',
    'linux-gcc-smoke',
    'build-pr-fast-gate',
    'dependency-update-anchors',
    'job-timeouts',
    'update-deps-concurrency',
    'pgo-consume-helper',
    'profiling-smoke-helper',
    'verify-ci-archive-helper',
    'source-test-vector-scripts',
    'threaded-me-smoke',
    'threaded-me-stress-smoke',
    'cli-long-input-smoke',
    'mkv-smoke',
    'lavf-smoke',
    'qpfile-smoke',
    'zonefile-smoke',
    'zonefile-oversized-smoke',
    'recon-smoke',
    'video-signal-type-preset-oversized-smoke',
    'gop-output-smoke',
    'dependency-suffixes',
)


def preferred_bash():
    try:
        return checker_module.bash_path(None)
    except checker_module.GuardFailure:
        return None


def run_checker(repo, checks=None):
    command = ['check_ci_guards.py', '--repo-root', str(repo)]
    bash = preferred_bash()
    if bash:
        command.extend(['--bash', bash])
    for check in checks or ():
        command.extend(['--only', check])

    stdout = io.StringIO()
    stderr = io.StringIO()
    argv = sys.argv
    exit_code = 0
    try:
        sys.argv = command
        with redirect_stdout(stdout), redirect_stderr(stderr):
            checker_module.main()
    except SystemExit as exc:
        code = exc.code
        if isinstance(code, int):
            exit_code = code
        elif code is None:
            exit_code = 0
        else:
            exit_code = 1
            print(code, file=stderr)
    finally:
        sys.argv = argv

    output = stdout.getvalue() + stderr.getvalue()
    return SimpleNamespace(returncode=exit_code, stdout=output)


def expect_pass(result):
    if result.returncode != 0:
        raise AssertionError(result.stdout)


def expect_fail(result, expected):
    if result.returncode == 0:
        raise AssertionError(f'expected failure containing {expected!r}')
    if expected not in result.stdout:
        raise AssertionError(result.stdout)


def assert_validator_coverage():
    covered = set(BASELINE_CHECKS) | set(TARGETED_CHECKS)
    missing = sorted(set(checker_module.VALIDATOR_NAMES) - covered)
    if missing:
        raise AssertionError(f'uncovered validators: {", ".join(missing)}')
    unexpected = sorted(covered - set(checker_module.VALIDATOR_NAMES))
    if unexpected:
        raise AssertionError(f'unknown covered validators: {", ".join(unexpected)}')


def main():
    if not preferred_bash():
        print('bash is unavailable; skipping CI guard tests')
        return

    assert_validator_coverage()

    def build_workflow(repo):
        return repo / '.github' / 'workflows' / 'build.yml'

    def profiling_workflow(repo):
        return repo / '.github' / 'workflows' / 'build-profiling.yml'

    def build_pgo_workflow(repo):
        return repo / '.github' / 'workflows' / 'build-pgo.yml'

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

    def source_test_vector_checker(repo):
        return repo / '.github' / 'scripts' / 'check_source_test_vectors.py'

    def source_test_vector_guard_test(repo):
        return repo / '.github' / 'scripts' / 'test_check_source_test_vectors.py'

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write_repo(repo, __file__)
        expect_pass(run_checker(repo, checks=BASELINE_CHECKS))

        def fail_case(modifier, expected, check):
            with tempfile.TemporaryDirectory() as tmp:
                repo = Path(tmp)
                write_repo(repo, __file__)
                modifier(repo)
                expect_fail(run_checker(repo, checks=(check,)), expected)
        cases = (
            case(lambda repo: replace_text(scan_helper(repo), '--forbidden-flag=-fprofile-instr-use', '--forbidden-flag=-fprofile-instr-generate'), 'missing profiling compile_commands guard: --forbidden-flag=-fprofile-instr-use', 'scan-helper'),
            case(lambda repo: replace_text(scan_helper(repo), '--forbidden-flag-substring=-fprofile-instr-use=', '--forbidden-flag-substring=-fprofile-instr-generate='), 'missing profiling compile_commands guard: --forbidden-flag-substring=-fprofile-instr-use=', 'scan-helper'),
            case(lambda repo: replace_text(build_workflow(repo), 'check_cxx20_commands_pgo_consume "$build_dir" --min-cpp-commands="$min_cpp_commands"', ': # check_cxx20_commands_pgo_consume "$build_dir" --min-cpp-commands="$min_cpp_commands"'), 'missing required Build workflow guard snippet: check_cxx20_commands_pgo_consume "$build_dir" --min-cpp-commands="$min_cpp_commands"', 'required-snippets'),
            case(lambda repo: replace_text(windows_deps_action(repo), 'c++ -O2 --std=gnu++20 -I/usr/local/include -c gop_muxer.cpp -o gop_muxer.o', 'c++ -O2 --std=gnu++20 --std=gnu++17 -I/usr/local/include -c gop_muxer.cpp -o gop_muxer.o'), 'missing required setup-windows-deps guard snippet: c++ -O2 --std=gnu++20 -I/usr/local/include -c gop_muxer.cpp -o gop_muxer.o', 'required-snippets'),
            case(lambda repo: replace_text(windows_deps_action(repo), 'git -c core.autocrlf=false reset --hard HEAD\n        git apply --ignore-whitespace --check ${{ inputs.lsmash-patch-path }}', 'git apply --ignore-whitespace --check ${{ inputs.lsmash-patch-path }}'), 'missing required setup-windows-deps guard snippet: git -c core.autocrlf=false reset --hard HEAD', 'required-snippets'),
            case(lambda repo: replace_text(build_workflow(repo), '--forbidden-flag-substring=-std=gnu++17', '# --forbidden-flag-substring=-std=gnu++17'), 'GNU++20 downgrade guard must reject GNU++17 flags', 'gnu20-diagnostic-steps'),
            case(lambda repo: replace_text(build_workflow(repo), 'configure_cxx20_scan x265/source build/cxx20-downgrade-guard', 'configure_cxx20_scan x265/source build/cxx20-warning-scan'), 'GNU++20 downgrade guard must actively configure downgrade build', 'gnu20-diagnostic-steps'),
            case(lambda repo: replace_text(build_workflow(repo), 'for target_cpu in haswell arrowlake znver5; do', 'for target_cpu in haswell znver5; do'), 'CPU warning scan must actively cover haswell/arrowlake/znver5 loop', 'gnu20-diagnostic-steps'),
            case(lambda repo: replace_text(build_workflow(repo), 'check_cxx20_commands_clang build/cxx20-warning-scan-asm', 'check_cxx20_commands_clang build/cxx20-warning-scan'), 'ASM warning scan must actively check asm compile commands target', 'gnu20-diagnostic-steps'),
            case(lambda repo: replace_text(build_workflow(repo), '--required-file-substring=source/test/', '--required-file-substring=source/common/'), 'ASM warning scan must actively require test sources', 'gnu20-diagnostic-steps'),
            case(lambda repo: replace_text(build_workflow(repo), '--required-file-flag=source/input/lavf.cpp=-DENABLE_LAVF', '--required-file-substring=source/input/lavf.cpp', count=2), 'C++20 warning scan must actively require LAVF macro', 'gnu20-diagnostic-steps'),
            case(lambda repo: replace_text(build_workflow(repo), 'check_cxx20_commands_gcc build/cxx20-linux-gcc-compile-commands-12bit', 'echo skip-linux-gcc-12bit-shape'), 'Linux GCC diagnostics must actively check 12-bit compile commands', 'gnu20-diagnostic-steps'),
            case(lambda repo: replace_text(build_workflow(repo), 'check_cxx20_commands_gcc build/cxx20-gcc-compile-commands', 'echo skip-windows-gcc-base'), 'Windows GCC diagnostics must actively check base compile commands', 'gnu20-diagnostic-steps'),
            case(lambda repo: replace_text(build_workflow(repo), 'mingw-w64-clang-x86_64-zimg', 'mingw-w64-clang-x86_64-python'), 'C++20 warning scan dependency setup must install mingw-w64-clang-x86_64-zimg', 'warning-scan-dependencies'),
            case(lambda repo: replace_text(build_workflow(repo), 'build/cxx20-linux-gcc-compile-commands/x265 --input build/cxx20-linux-gcc-compile-commands/smoke_linux_gcc.yuv --input-res 64x64', 'build/cxx20-linux-gcc-compile-commands/x265 --input build/cxx20-linux-gcc-compile-commands/smoke_linux_gcc.yuv --input-res 128x128'), 'Linux GCC smoke --input-res must be 64x64, got 128x128', 'linux-gcc-smoke'),
            case(lambda repo: replace_text(build_workflow(repo), '  pull_request:', '  pull_request_disabled:'), 'Build workflow must define pull_request trigger for pre-merge CI', 'build-pr-fast-gate'),
            case(lambda repo: replace_text(build_workflow(repo), "      - '.github/workflows/**'", "      - '.github/workflows/build.yml'"), 'Build workflow pull_request paths missing: .github/workflows/**', 'build-pr-fast-gate'),
            case(lambda repo: replace_text(build_workflow(repo), "      - '.github/patches/**'", "      - '.github/scripts/**'"), 'Build workflow pull_request paths missing: .github/patches/**', 'build-pr-fast-gate'),
            case(lambda repo: replace_text(build_workflow(repo), "    if: github.event_name != 'pull_request'\n    runs-on: windows-latest", "    runs-on: windows-latest", count=1), 'Build workflow job cxx20-warning-scan must be skipped for pull_request fast gate', 'build-pr-fast-gate'),
            case(lambda repo: replace_text(build_workflow(repo), '  linux-clang-sanitizers:', '  linux-clang-sanitizers-disabled:'), 'Build workflow must include linux-clang-sanitizers PR fast gate job', 'build-pr-fast-gate'),
            case(lambda repo: replace_text(build_workflow(repo), '            enable_hdr10_plus=OFF', '            enable_hdr10_plus=ON', count=1), 'sanitizer PR fast gate must disable HDR10+ for speed', 'build-pr-fast-gate'),
            case(lambda repo: replace_text(build_workflow(repo), '      - build\n    if: github.event_name', '      - build\n      - linux-clang-sanitizers\n    if: github.event_name'), 'publish-release must not depend on PR fast-gate sanitizer job', 'build-pr-fast-gate'),
            case(lambda repo: replace_text(build_workflow(repo), 'bash x265/.github/scripts/runtime_smoke_suite.sh all', 'bash x265/.github/scripts/runtime_smoke_suite.sh raw'), 'missing required Build workflow guard snippet: bash x265/.github/scripts/runtime_smoke_suite.sh all', 'required-snippets'),
            case(lambda repo: replace_text(build_workflow(repo), 'bash x265/.github/scripts/mp4_smoke_suite.sh all', 'bash x265/.github/scripts/mp4_smoke_suite.sh smoke'), 'missing required Build workflow guard snippet: bash x265/.github/scripts/mp4_smoke_suite.sh all', 'required-snippets'),
            case(lambda repo: replace_text(update_deps_workflow(repo), 'python .github/scripts/check_ci_guards.py', 'python .github/scripts/check_dependency_patch_suffixes.py'), 'missing required update-deps guard snippet: python .github/scripts/check_ci_guards.py', 'required-snippets'),
            case(lambda repo: replace_text(windows_deps_action(repo), 'gop-muxer-cache-suffix:', 'gop-muxer-cache-label:'), 'missing dependency update anchor: gop-muxer-cache-suffix:', 'dependency-update-anchors'),
            case(lambda repo: replace_text(profiling_workflow(repo), 'needs: validate-guardrails', '# needs removed'), 'Build Profiling build job must need validate-guardrails', 'required-snippets'),
            case(lambda repo: replace_text(build_pgo_workflow(repo), 'python .github/scripts/check_ci_guards.py', 'python .github/scripts/check_pgo_consume_chain.py'), 'missing required Build PGO workflow guard snippet: python .github/scripts/check_ci_guards.py', 'required-snippets'),
            case(lambda repo: replace_text(build_pgo_workflow(repo), 'needs: validate-guardrails', '# needs removed'), 'Build PGO generate job must need validate-guardrails', 'required-snippets'),
            case(lambda repo: replace_text(build_pgo_workflow(repo), '        target-cpu: x86-64', '        target-cpu: haswell'), 'Build PGO profiling action must set target-cpu=x86-64', 'required-snippets'),
            case(lambda repo: replace_text(build_workflow(repo), '    timeout-minutes: 15\n', '', count=1), 'build.yml job validate-deps-cache-suffix must declare a positive timeout-minutes', 'job-timeouts'),
            case(lambda repo: replace_text(update_deps_workflow(repo), "concurrency:\n  group: ${{ github.workflow }}-${{ github.ref }}\n  cancel-in-progress: false\n\n", ''), 'Update-deps workflow must declare concurrency', 'update-deps-concurrency'),
            case(lambda repo: replace_text(build_workflow(repo), 'check_pgo_consume_commands()', 'check_pgo_consume_commands_disabled()'), 'expected exactly one PGO consume helper run block, found 0', 'pgo-consume-helper'),
            case(lambda repo: replace_text(profiling_smoke_helper(repo), './profdata-dist/llvm-profdata.exe show "$profdata" >/dev/null', 'test -s "$profdata"'), 'profiling smoke helper missing detail: ./profdata-dist/llvm-profdata.exe show "$profdata" >/dev/null', 'profiling-smoke-helper'),
            case(lambda repo: replace_text(profiling_action(repo), 'check_cxx20_commands_profiling build/12b', 'echo skip-12b-guard'), 'missing required Build Profiling action guard snippet: check_cxx20_commands_profiling build/12b', 'required-snippets'),
            case(lambda repo: replace_text(archive_verify_helper(repo), 'verify_x265_release()', 'verify_x265_release_disabled()'), 'archive verification helper missing function: verify_x265_release()', 'verify-ci-archive-helper'),
            case(lambda repo: replace_text(archive_verify_helper(repo), 'run_with_isolated_path "$extract_dir/llvm-profdata.exe" --version >/dev/null', '"$extract_dir/llvm-profdata.exe" --version >/dev/null'), 'archive verification helper missing function: run_with_isolated_path "$extract_dir/llvm-profdata.exe" --version >/dev/null', 'verify-ci-archive-helper'),
            case(lambda repo: source_test_vector_checker(repo).unlink(), 'missing source test vector checker', 'source-test-vector-scripts'),
            case(lambda repo: source_test_vector_guard_test(repo).unlink(), 'missing source test vector guard test', 'source-test-vector-scripts'),
            case(lambda repo: replace_text(runtime_suite(repo), 'run_runtime_smoke_targets raw cli-long-input mkv lavf threaded-me threaded-me-stress qpfile zonefile zonefile-oversized recon video-signal-type-preset-oversized gop-output', 'run_runtime_smoke_targets raw cli-long-input mkv lavf threaded-me threaded-me-stress qpfile zonefile zonefile-oversized recon video-signal-type-preset-oversized'), 'Runtime smoke suite missing function or dispatch: run_runtime_smoke_targets raw cli-long-input mkv lavf threaded-me threaded-me-stress qpfile zonefile zonefile-oversized recon video-signal-type-preset-oversized gop-output', 'runtime-smoke-suite'),
            case(lambda repo: replace_text(runtime_suite(repo), 'build/all/x265.exe --input smoke_raw.y4m', 'build/8b/x265.exe --input smoke_raw.y4m'), 'RAW smoke must run build/all/x265.exe, got build/8b/x265.exe', 'raw-smoke'),
            case(lambda repo: replace_text(runtime_suite(repo), "grep -Fq 'frame threads / pool features       : 1 / threaded-me' smoke_threaded_me_log.txt", "grep -Fq 'threaded-me' smoke_threaded_me_log.txt"), 'Threaded ME smoke must require enabled threaded-me log', 'threaded-me-smoke'),
            case(lambda repo: replace_text(runtime_suite(repo), 'for iteration in $(seq 1 12); do', 'for iteration in $(seq 1 1); do'), 'Threaded ME stress smoke must run a 12-iteration loop', 'threaded-me-stress-smoke'),
            case(lambda repo: replace_text(runtime_suite(repo), "grep -Fq 'Input filename exceeds supported length' smoke_cli_long_input.log", "grep -Fq 'supported length' smoke_cli_long_input.log"), 'CLI long-input smoke must require oversized --input error log', 'cli-long-input-smoke'),
            case(lambda repo: replace_text(runtime_suite(repo), '--frames 12 --output smoke_mkv.mkv', '--frames 8 --output smoke_mkv.mkv'), 'MKV smoke --frames must be 12, got 8', 'mkv-smoke'),
            case(lambda repo: replace_text(runtime_suite(repo), '2>&1 | tee smoke_lavf_log.txt', '2>&1'), 'LAVF smoke must capture x265 log to smoke_lavf_log.txt', 'lavf-smoke'),
            case(lambda repo: replace_text(runtime_suite(repo), '9 K 20', '9 K 18'), 'QPFile smoke must require frame 9 K 20 entry', 'qpfile-smoke'),
            case(lambda repo: replace_text(runtime_suite(repo), '--bitrate 400 --zonefile smoke_zonefile.txt --output smoke_zonefile.hevc', '--bitrate 350 --zonefile smoke_zonefile.txt --output smoke_zonefile.hevc'), 'Zonefile smoke --bitrate must be 400, got 350', 'zonefile-smoke'),
            case(lambda repo: replace_text(runtime_suite(repo), "grep -Fq 'Zone file entry exceeds supported argument count' smoke_zonefile_oversized.log", "grep -Fq 'supported argument count' smoke_zonefile_oversized.log"), 'Zonefile oversized smoke must require argument-count error log', 'zonefile-oversized-smoke'),
            case(lambda repo: replace_text(runtime_suite(repo), '--recon smoke_recon_out.y4m --output smoke_recon.hevc', '--output smoke_recon.hevc'), 'missing Recon smoke value for --recon', 'recon-smoke'),
            case(lambda repo: replace_text(runtime_suite(repo), "grep -Fq 'Incorrect system-id, aborting' smoke_vst_oversized.log", "grep -Fq 'system-id' smoke_vst_oversized.log"), 'Video-signal-type-preset oversized smoke must require invalid system-id log', 'video-signal-type-preset-oversized-smoke'),
            case(lambda repo: replace_text(runtime_suite(repo), 'test "$(wc -l < smoke_gop_data_files.txt)" -eq 2', '# test "$(wc -l < smoke_gop_data_files.txt)" -eq 2'), 'GOP smoke must require exactly two gop-data sidecars', 'gop-output-smoke'),
            case(lambda repo: replace_text(runtime_suite(repo), "awk -F= '/^extradata_size=/{ if (($2+0) > 0) found=1 } END { if (!found) exit 1 }' smoke_gop_mux_stream.txt", "# awk -F= '/^extradata_size=/{ if (($2+0) > 0) found=1 } END { if (!found) exit 1 }' smoke_gop_mux_stream.txt"), 'GOP smoke must require positive extradata_size in muxed MP4 stream', 'gop-output-smoke'),
            case(lambda repo: replace_text(mp4_suite(repo), 'run_mp4_smoke_targets smoke open-gop cra single-frame frames-zero single-frame-24000-1001 vui strict-cbr-fails frac-24000-1001 b-pyramid aud eos-eob idr-recovery', 'run_mp4_smoke_targets smoke open-gop cra single-frame frames-zero single-frame-24000-1001 vui strict-cbr-fails frac-24000-1001 b-pyramid aud eos-eob'), 'MP4 smoke suite missing function or dispatch: run_mp4_smoke_targets smoke open-gop cra single-frame frames-zero single-frame-24000-1001 vui strict-cbr-fails frac-24000-1001 b-pyramid aud eos-eob idr-recovery', 'mp4-smoke-suite'),
            case(lambda repo: replace_text(mp4_suite(repo), '--no-open-gop --output smoke.mp4', '--open-gop --output smoke.mp4'), 'missing MP4 smoke argument: --no-open-gop', 'mp4-smokes'),
            case(lambda repo: replace_text(mp4_suite(repo), "assert_mp4_markers smoke_open.mp4 iso6 sgpd sbgp 'rap '", 'assert_mp4_markers smoke_open.mp4 iso6 hvc1 hvcC'), 'MP4 open-GOP smoke must require sample-group markers', 'mp4-smokes'),
            case(lambda repo: replace_text(mp4_suite(repo), '--cra-nal --output smoke_cra.mp4', '--output smoke_cra.mp4'), 'missing MP4 CRA smoke argument: --cra-nal', 'mp4-smokes'),
            case(lambda repo: replace_text(mp4_suite(repo), 'make_y4m smoke_single.y4m 24 1 yuv420p', 'make_y4m smoke_single.y4m 24 2 yuv420p'), 'MP4 single-frame smoke must generate 1-frame yuv420p input', 'mp4-smokes'),
            case(lambda repo: replace_text(mp4_suite(repo), 'assert_single_frame_mp4 smoke_single_frac 0.06 0.03 0.06', 'assert_single_frame_mp4 smoke_single_frac 0.04 0.01 0.04'), 'MP4 single-frame 24000/1001 smoke must require single-frame timing window', 'mp4-smokes'),
            case(lambda repo: replace_text(mp4_suite(repo), '--frames 0 --bframes 0 --keyint 1 --min-keyint 1 --output smoke_zero.mp4', '--frames 1 --bframes 0 --keyint 1 --min-keyint 1 --output smoke_zero.mp4'), 'MP4 frames=0 smoke --frames must be 0, got 1', 'mp4-smokes'),
            case(lambda repo: replace_text(mp4_suite(repo), '--sar 4:3 --range limited --colorprim bt709 --transfer bt709 --colormatrix bt709 --output smoke_vui.mp4', '--sar 1:1 --range limited --colorprim bt709 --transfer bt709 --colormatrix bt709 --output smoke_vui.mp4'), 'MP4 VUI smoke --sar must be 4:3, got 1:1', 'mp4-smokes'),
            case(lambda repo: replace_text(mp4_suite(repo), '--strict-cbr --hrd --output smoke_strict_cbr.mp4', '--strict-cbr --output smoke_strict_cbr.mp4'), 'missing MP4 strict-CBR smoke argument: --hrd', 'mp4-smokes'),
            case(lambda repo: replace_text(mp4_suite(repo), "awk -F, '$3 ~ /K/ { kf++; if (kf == 2 && NR != 13) exit 1 } END { if (kf < 2) exit 1 }' smoke_frac_packets.csv", "awk -F, '$3 ~ /K/ { kf++; if (kf == 2 && NR != 9) exit 1 } END { if (kf < 2) exit 1 }' smoke_frac_packets.csv"), 'MP4 24000/1001 smoke must require second key packet at packet 13', 'mp4-smokes'),
            case(lambda repo: replace_text(mp4_suite(repo), '--bframes 4 --b-pyramid --keyint 8', '--bframes 4 --keyint 8'), 'missing MP4 B-pyramid smoke argument: --b-pyramid', 'mp4-smokes'),
            case(lambda repo: replace_text(mp4_suite(repo), '--aud --output smoke_aud.mp4', '--output smoke_aud.mp4'), 'missing MP4 AUD smoke argument: --aud', 'mp4-smokes'),
            case(lambda repo: replace_text(mp4_suite(repo), '--eos --eob --output smoke_eos.mp4', '--eos --output smoke_eos.mp4'), 'missing MP4 EOS/EOB smoke argument: --eob', 'mp4-smokes'),
            case(lambda repo: replace_text(mp4_suite(repo), '--no-open-gop --idr-recovery-sei --output smoke_recovery.mp4', '--no-open-gop --output smoke_recovery.mp4'), 'missing MP4 IDR recovery smoke argument: --idr-recovery-sei', 'mp4-smokes'),
            case(lambda repo: replace_text(repo / '.github' / 'scripts' / 'check_dependency_patch_suffixes.py', 'def main():', 'def main_disabled():'), "NameError: name 'main' is not defined", 'dependency-suffixes'),
        )

        for item in cases:
            fail_case(item['modifier'], item['expected'], item['check'])

        print('CI guard script guardrails validated')


if __name__ == '__main__':
    main()
