#!/usr/bin/env python3
import argparse
import re
import shlex
import sys
from pathlib import Path

from check_ci_guards_data import (
    ACTION_DIR,
    BUILD_PGO_WORKFLOW,
    BUILD_PROFILING_ACTION,
    BUILD_PROFILING_HELPER,
    CI_VERSION_HELPER,
    BUILD_PROFILING_WORKFLOW,
    BUILD_WORKFLOW,
    CI_7Z_HELPER,
    DEPENDENCY_SUFFIX_CHECK,
    ENSURE_CMAKE4_HELPER,
    ENSURE_LINUX_SANITIZER_TOOLCHAIN_HELPER,
    GOP_SMOKE_FLAGS,
    GOP_SMOKE_OPTIONS,
    LAVF_GENERATOR_OPTIONS,
    LAVF_SMOKE_OPTIONS,
    LINUX_GCC_SMOKE_OPTIONS,
    MKV_SMOKE_OPTIONS,
    MP4_AUD_SMOKE_FLAGS,
    MP4_AUD_SMOKE_OPTIONS,
    MP4_BPYRAMID_SMOKE_FLAGS,
    MP4_BPYRAMID_SMOKE_OPTIONS,
    MP4_CRA_SMOKE_FLAGS,
    MP4_CRA_SMOKE_OPTIONS,
    MP4_EOS_SMOKE_FLAGS,
    MP4_EOS_SMOKE_OPTIONS,
    MP4_FRAC_SMOKE_FLAGS,
    MP4_FRAC_SMOKE_OPTIONS,
    MP4_OPEN_GOP_SMOKE_FLAGS,
    MP4_OPEN_GOP_SMOKE_OPTIONS,
    MP4_RECOVERY_SMOKE_FLAGS,
    MP4_RECOVERY_SMOKE_OPTIONS,
    MP4_SINGLE_FRAME_SMOKE_OPTIONS,
    MP4_SMOKE_FLAGS,
    MP4_SMOKE_HELPER,
    MP4_SMOKE_OPTIONS,
    MP4_SMOKE_SUITE,
    MP4_VUI_SMOKE_OPTIONS,
    MP4_ZERO_FRAMES_SMOKE_OPTIONS,
    PR_SKIPPED_BUILD_JOBS,
    PR_TRIGGER_PATHS,
    PROFILING_SMOKE_HELPER,
    PYTHON_CI_GUARD_BUNDLE,
    RELEASE_ASSET_VALIDATOR,
    REQUIRED_BUILD_PROFILING_ACTION_SNIPPETS,
    REQUIRED_BUILD_PROFILING_HELPER_SNIPPETS,
    REQUIRED_CI_VERSION_HELPER_SNIPPETS,
    REQUIRED_RELEASE_ASSET_VALIDATOR_SNIPPETS,
    REQUIRED_UPDATE_DEPS_SNIPPETS,
    REQUIRED_WINDOWS_DEPS_ACTION_SNIPPETS,
    RUNTIME_SMOKE_SUITE,
    SCAN_HELPER,
    SOURCE_TEST_VECTOR_CHECK,
    SOURCE_TEST_VECTOR_TEST,
    TME_SMOKE_FLAGS,
    TME_SMOKE_OPTIONS,
    TME_STRESS_FLAGS,
    TME_STRESS_OPTIONS,
    UPDATE_DEPS_ANCHORS,
    UPDATE_DEPS_WORKFLOW,
    VERIFY_CI_ARCHIVE_HELPER,
    WARNING_SCAN_SMOKES,
    WINDOWS_DEPS_ACTION,
    WORKFLOW_DIR,
    ZIMG_SMOKE_OPTIONS,
    build_step_requirements,
    build_workflow_step_requirements,
    pgo_step_requirements,
    profiling_step_requirements,
)
from check_ci_guards_helpers import (
    GuardFailure,
    bash_path,
    collect_run_blocks,
    fail,
    load_yaml,
    read_text,
    report_failure,
    run_guard,
    shell_active_lines,
    shell_active_logical_lines,
    validate_bash_file,
    validate_python_file,
    validate_run_blocks,
    validate_yaml_parse,
    validate_yaml_text,
    workflow_jobs,
    workflow_on,
)
from check_ci_guards_checks import (
    option_value,
    piped_x265_command,
    require_active_command_prefix,
    require_active_exact_command,
    require_active_line_contains,
    require_x265_command,
    runtime_smoke_active_lines,
    smoke_suite_function_lines,
    action_step_run,
    validate_mp4_smoke_step,
    validate_required_action_steps,
    validate_required_workflow_steps,
    workflow_step,
    workflow_step_run,
)


def validate_scan_helper(repo_root, bash):
    validate_bash_file(
        repo_root,
        bash,
        SCAN_HELPER,
        'missing C++20 warning scan helper',
        required_tokens=(
            '--forbidden-flag=-fprofile-instr-use',
            '--forbidden-flag-substring=-fprofile-instr-use=',
            '--required-flag=$pgo_flag',
        ),
        required_message='missing profiling compile_commands guard',
    )
    profiling_lines = smoke_suite_function_lines(repo_root, SCAN_HELPER, 'check_cxx20_commands_profiling', 'missing C++20 warning scan helper')
    for required in ('"${cxx20_common_check_args[@]}"', '"${cxx20_clang_check_args[@]}"'):
        require_active_line_contains(
            profiling_lines,
            required,
            repo_root / SCAN_HELPER,
            f'missing profiling compile_commands guard: {required}',
        )


def validate_ensure_cmake4_helper(repo_root, bash):
    validate_bash_file(
        repo_root,
        bash,
        ENSURE_CMAKE4_HELPER,
        'missing CMake 4 helper',
        required_text=(
            'find_preinstalled_cmake4() {',
            'ensure_cmake4() {',
            '${ANDROID_SDK_ROOT:-}/cmake',
            '/usr/bin/cmake',
            'python -m venv "$RUNNER_TEMP/cmake-venv"',
            '"$RUNNER_TEMP/cmake-venv/bin/python" -m pip install \'cmake>=4.0,<5\'',
            'Using preinstalled CMake:',
            'Installed fallback CMake into $RUNNER_TEMP/cmake-venv',
        ),
        required_message='CMake 4 helper missing detail',
    )


def validate_ensure_linux_sanitizer_toolchain_helper(repo_root, bash):
    validate_bash_file(
        repo_root,
        bash,
        ENSURE_LINUX_SANITIZER_TOOLCHAIN_HELPER,
        'missing Linux sanitizer toolchain helper',
        required_text=(
            'ensure_linux_sanitizer_toolchain() {',
            'for tool in clang++ ld.lld ninja; do',
            'Using preinstalled Linux sanitizer toolchain',
            'sudo apt-get update',
            'sudo apt-get install -y clang lld ninja-build',
            'Installed fallback Linux sanitizer toolchain:',
        ),
        required_message='Linux sanitizer toolchain helper missing detail',
    )


def validate_mp4_smoke_helper(repo_root, bash):
    validate_bash_file(
        repo_root,
        bash,
        MP4_SMOKE_HELPER,
        'missing MP4 smoke helper',
        required_text=(
            'make_y4m()',
            'probe_mp4()',
            'assert_common_mp4()',
            'dump_mp4_diagnostics()',
            'assert_mp4_markers()',
            'assert_duration_window()',
            'assert_single_frame_mp4()',
        ),
        required_message='MP4 smoke helper missing function',
    )


def validate_profiling_smoke_helper(repo_root, bash):
    validate_bash_file(
        repo_root,
        bash,
        PROFILING_SMOKE_HELPER,
        'missing profiling smoke helper',
        required_text=(
            'profile_class="${1:-}"',
            'case "$profile_class" in',
            'runtime_smoke_enabled=1',
            'summary_title=',
            'profile_smoke_output=',
            'dist_exe=',
            './profdata-dist/llvm-profdata.exe merge -o "$profdata" "$LLVM_PROFILE_FILE"',
            './profdata-dist/llvm-profdata.exe show "$profdata" >/dev/null',
            'cp "${build_dir}/x265-profiling.exe" "$dist_exe"',
        ),
        required_message='profiling smoke helper missing detail',
    )


def validate_build_profiling_helper(repo_root, bash):
    validate_bash_file(
        repo_root,
        bash,
        BUILD_PROFILING_HELPER,
        'missing build profiling helper',
        required_text=REQUIRED_BUILD_PROFILING_HELPER_SNIPPETS,
        required_message='build profiling helper missing detail',
    )


def validate_verify_ci_archive_helper(repo_root, bash):
    validate_bash_file(
        repo_root,
        bash,
        VERIFY_CI_ARCHIVE_HELPER,
        'missing archive verification helper',
        required_text=(
            'isolated_windows_path()',
            'run_with_isolated_path()',
            'script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"',
            'source "$script_dir/ci_7z.sh"',
            'ci_7z t "$archive"',
            'ci_7z x -o"$extract_dir" "$archive"',
            'verify_x265_release()',
            'verify_x265_profiling()',
            'verify_llvm_profdata()',
            'test -s "$extract_dir/llvm-profdata.exe"',
            'run_with_isolated_path "$extract_dir/llvm-profdata.exe" --version >/dev/null',
            "dll_count=$(find \"$extract_dir\" -maxdepth 1 -type f -iname '*.dll' | wc -l)",
            'test "$dll_count" -gt 0',
            'case "$mode" in',
        ),
        required_message='archive verification helper missing function',
    )
    path = repo_root / VERIFY_CI_ARCHIVE_HELPER
    release_lines = smoke_suite_function_lines(repo_root, VERIFY_CI_ARCHIVE_HELPER, 'verify_x265_release', 'missing archive verification helper')
    for required in (
        'run_with_isolated_path "$all_exe" --version >/dev/null',
        'run_with_isolated_path "$exe" --version >/dev/null',
    ):
        require_active_line_contains(release_lines, required, path, f'archive verification helper missing release isolation: {required}')
    profiling_lines = smoke_suite_function_lines(repo_root, VERIFY_CI_ARCHIVE_HELPER, 'verify_x265_profiling', 'missing archive verification helper')
    require_active_line_contains(
        profiling_lines,
        'run_with_isolated_path "$exe" --version >/dev/null',
        path,
        'archive verification helper missing profiling isolation: run_with_isolated_path "$exe" --version >/dev/null',
    )
    print('CI archive verification helper validated')


def validate_ci_version_helper(repo_root, bash):
    if bash is None:
        path = repo_root / CI_VERSION_HELPER
        if not path.is_file():
            fail('missing CI version helper', path)
        text = read_text(path)
        for required in REQUIRED_CI_VERSION_HELPER_SNIPPETS:
            if required not in text:
                fail(f'CI version helper missing detail: {required}', path)
        return
    validate_bash_file(
        repo_root,
        bash,
        CI_VERSION_HELPER,
        'missing CI version helper',
        required_text=REQUIRED_CI_VERSION_HELPER_SNIPPETS,
        required_message='CI version helper missing detail',
    )


def validate_release_asset_validator(repo_root, bash):
    if bash is None:
        path = repo_root / RELEASE_ASSET_VALIDATOR
        if not path.is_file():
            fail('missing release asset validator', path)
        text = read_text(path)
        for required in REQUIRED_RELEASE_ASSET_VALIDATOR_SNIPPETS:
            if required not in text:
                fail(f'release asset validator missing detail: {required}', path)
        return
    validate_bash_file(
        repo_root,
        bash,
        RELEASE_ASSET_VALIDATOR,
        'missing release asset validator',
        required_text=REQUIRED_RELEASE_ASSET_VALIDATOR_SNIPPETS,
        required_message='release asset validator missing detail',
    )


def validate_runtime_smoke_suite(repo_root, bash):
    validate_bash_file(
        repo_root,
        bash,
        RUNTIME_SMOKE_SUITE,
        'missing runtime smoke suite',
        required_text=(
            'make_runtime_y4m()',
            'smoke_raw()',
            'smoke_cli_long_input()',
            'smoke_mkv()',
            'smoke_lavf()',
            'smoke_threaded_me()',
            'smoke_threaded_me_stress()',
            'smoke_qpfile()',
            'smoke_nalu_file()',
            'smoke_output_depth_invalid()',
            'smoke_chunk_negative()',
            'smoke_qpfile_oversized()',
            'smoke_zonefile()',
            'smoke_zonefile_oversized()',
            'smoke_recon()',
            'smoke_analysis_save_load()',
            'smoke_2pass_stats()',
            'smoke_abr_ladder()',
            'smoke_video_signal_type_preset_oversized()',
            'smoke_gop_output()',
            'run_runtime_smoke_target()',
            'run_runtime_smoke_targets()',
            'run_runtime_smoke_targets raw cli-long-input mkv lavf threaded-me threaded-me-stress qpfile nalu-file output-depth-invalid chunk-negative qpfile-oversized zonefile zonefile-oversized recon analysis-save-load 2pass-stats abr-ladder video-signal-type-preset-oversized gop-output',
            'case "${1:-}" in',
        ),
        required_message='Runtime smoke suite missing function or dispatch',
    )


def validate_mp4_smoke_suite(repo_root, bash):
    validate_bash_file(
        repo_root,
        bash,
        MP4_SMOKE_SUITE,
        'missing MP4 smoke suite',
        required_text=(
            'source "${script_dir}/mp4_smoke_helpers.sh"',
            'smoke_mp4()',
            'smoke_mp4_open_gop()',
            'smoke_mp4_cra()',
            'smoke_mp4_single_frame()',
            'smoke_mp4_frames_zero()',
            'smoke_mp4_single_frame_frac()',
            'smoke_mp4_vui()',
            'smoke_mp4_strict_cbr_fails()',
            'smoke_mp4_frac()',
            'smoke_mp4_b_pyramid()',
            'smoke_mp4_aud()',
            'smoke_mp4_eos_eob()',
            'smoke_mp4_idr_recovery()',
            'run_mp4_smoke_target()',
            'run_mp4_smoke_targets()',
            'run_mp4_smoke_targets smoke open-gop cra single-frame frames-zero single-frame-24000-1001 vui strict-cbr-fails frac-24000-1001 b-pyramid aud eos-eob idr-recovery',
            'case "${1:-}" in',
        ),
        required_message='MP4 smoke suite missing function or dispatch',
    )


def validate_source_test_vector_scripts(repo_root):
    validate_python_file(
        repo_root,
        SOURCE_TEST_VECTOR_CHECK,
        'missing source test vector checker',
        required_text=(
            'HARNESS_LISTS = {',
            'PLAIN_TEXT_LISTS = {',
            'validate_harness_list(path)',
            'validate_plain_text(path)',
            'unknown source test text file; classify it in HARNESS_LISTS or PLAIN_TEXT_LISTS',
        ),
        required_message='source test vector checker missing detail',
    )
    validate_python_file(
        repo_root,
        SOURCE_TEST_VECTOR_TEST,
        'missing source test vector guard test',
        required_text=(
            "CHECKER = Path(__file__).with_name('check_source_test_vectors.py')",
            'expect_pass(run_checker(test_dir))',
            'future-tests.txt',
            'unknown source test text file; classify it in HARNESS_LISTS or PLAIN_TEXT_LISTS',
        ),
        required_message='source test vector guard test missing detail',
    )


def validate_dependency_suffixes(repo_root, before, after):
    script = repo_root / DEPENDENCY_SUFFIX_CHECK
    if not script.is_file():
        fail('missing dependency patch suffix checker', script)
    command = [sys.executable, str(script)]
    if before or after:
        if not before or not after:
            fail('--before and --after must be provided together')
        command.extend(['--before', before, '--after', after])
    run_guard(repo_root, *command)


def validate_release_needs(repo_root):
    script = repo_root / Path('.github/scripts/check_release_needs.py')
    if not script.is_file():
        fail('missing release needs checker', script)
    run_guard(repo_root, sys.executable, str(script))


def validate_compile_commands(repo_root):
    script = repo_root / Path('.github/scripts/check_compile_commands.py')
    test_script = repo_root / Path('.github/scripts/test_check_compile_commands.py')
    if not script.is_file():
        fail('missing compile commands checker', script)
    if not test_script.is_file():
        fail('missing compile commands test', test_script)
    run_guard(repo_root, sys.executable, str(test_script))


def validate_gnu20_legacy_guard_bundle(repo_root):
    script = repo_root / Path('.github/scripts/check_gnu20_legacy_guard_bundle.py')
    if not script.is_file():
        fail('missing GNU++20 legacy guard bundle checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_cli_nullptr_usage(repo_root):
    script = repo_root / Path('.github/scripts/check_cli_nullptr_usage.py')
    if not script.is_file():
        fail('missing CLI nullptr checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_cli_volatile_usage(repo_root):
    script = repo_root / Path('.github/scripts/check_cli_volatile_usage.py')
    if not script.is_file():
        fail('missing CLI volatile checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_json11_noexcept_usage(repo_root):
    script = repo_root / Path('.github/scripts/check_json11_noexcept_usage.py')
    if not script.is_file():
        fail('missing json11 noexcept checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_json11_number_boundary_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_json11_number_boundary_safety.py')
    if not script.is_file():
        fail('missing json11 number boundary checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_json11_unicode_escape_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_json11_unicode_escape_parse_safety.py')
    if not script.is_file():
        fail('missing json11 unicode escape checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_json11_short_int_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_json11_short_int_parse_safety.py')
    if not script.is_file():
        fail('missing json11 short-int checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_json11_slow_float_token_bounds(repo_root):
    script = repo_root / Path('.github/scripts/check_json11_slow_float_token_bounds.py')
    if not script.is_file():
        fail('missing json11 slow-float checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_source_null_exception_usage(repo_root):
    script = repo_root / Path('.github/scripts/check_source_null_exception_usage.py')
    if not script.is_file():
        fail('missing source NULL exception checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_remaining_null_boundaries(repo_root):
    script = repo_root / Path('.github/scripts/check_remaining_null_boundaries.py')
    if not script.is_file():
        fail('missing remaining NULL boundaries checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_fps_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_fps_parse_safety.py')
    if not script.is_file():
        fail('missing fps parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_frame_threads_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_frame_threads_parse_safety.py')
    if not script.is_file():
        fail('missing frame-threads parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_total_frames_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_total_frames_parse_safety.py')
    if not script.is_file():
        fail('missing total-frames parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_level_idc_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_level_idc_parse_safety.py')
    if not script.is_file():
        fail('missing level-idc parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_log_level_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_log_level_parse_safety.py')
    if not script.is_file():
        fail('missing log-level parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_qpstep_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_qpstep_parse_safety.py')
    if not script.is_file():
        fail('missing qpstep parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_qscale_mode_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_qscale_mode_parse_safety.py')
    if not script.is_file():
        fail('missing qscale-mode parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_subme_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_subme_parse_safety.py')
    if not script.is_file():
        fail('missing subme parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_cli_input_open_cleanup(repo_root):
    script = repo_root / Path('.github/scripts/check_cli_input_open_cleanup.py')
    if not script.is_file():
        fail('missing CLI input open cleanup checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_cli_input_validation_cleanup(repo_root):
    script = repo_root / Path('.github/scripts/check_cli_input_validation_cleanup.py')
    if not script.is_file():
        fail('missing CLI input validation cleanup checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_cli_output_open_cleanup(repo_root):
    script = repo_root / Path('.github/scripts/check_cli_output_open_cleanup.py')
    if not script.is_file():
        fail('missing CLI output open cleanup checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_cli_profile_apply_cleanup(repo_root):
    script = repo_root / Path('.github/scripts/check_cli_profile_apply_cleanup.py')
    if not script.is_file():
        fail('missing CLI profile apply cleanup checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_cli_deprecated_parallel_log_args(repo_root):
    script = repo_root / Path('.github/scripts/check_cli_deprecated_parallel_log_args.py')
    if not script.is_file():
        fail('missing CLI deprecated parallel log checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_scenecut_trailing_arg_diagnostics(repo_root):
    script = repo_root / Path('.github/scripts/check_scenecut_trailing_arg_diagnostics.py')
    if not script.is_file():
        fail('missing scenecut trailing-arg diagnostic checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_cli_recon_basename_cleanup(repo_root):
    script = repo_root / Path('.github/scripts/check_cli_recon_basename_cleanup.py')
    if not script.is_file():
        fail('missing CLI recon basename cleanup checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_cli_vmaf_input_open_cleanup(repo_root):
    script = repo_root / Path('.github/scripts/check_cli_vmaf_input_open_cleanup.py')
    if not script.is_file():
        fail('missing CLI VMAF input open cleanup checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_cli_vmaf_recon_preconditions_cleanup(repo_root):
    script = repo_root / Path('.github/scripts/check_cli_vmaf_recon_preconditions_cleanup.py')
    if not script.is_file():
        fail('missing CLI VMAF recon precondition cleanup checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_cli_recon_open_guard(repo_root):
    script = repo_root / Path('.github/scripts/check_cli_recon_open_guard.py')
    if not script.is_file():
        fail('missing CLI recon open checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_svt_app_context_staging(repo_root):
    script = repo_root / Path('.github/scripts/check_svt_app_context_staging.py')
    if not script.is_file():
        fail('missing SVT app-context staging checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_svt_param_storage_replace_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_svt_param_storage_replace_safety.py')
    if not script.is_file():
        fail('missing SVT param storage checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_svt_nal_buffer_replace_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_svt_nal_buffer_replace_safety.py')
    if not script.is_file():
        fail('missing SVT NAL buffer checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_nal_takecontents_realloc_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_nal_takecontents_realloc_safety.py')
    if not script.is_file():
        fail('missing NAL takeContents realloc checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_svt_rpu_payload_replace_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_svt_rpu_payload_replace_safety.py')
    if not script.is_file():
        fail('missing SVT RPU payload checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_configure_zone_svt_staging(repo_root):
    script = repo_root / Path('.github/scripts/check_configure_zone_svt_staging.py')
    if not script.is_file():
        fail('missing configureZone SVT staging checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_svt_pools_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_svt_pools_parse_safety.py')
    if not script.is_file():
        fail('missing SVT pools parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_svt_deblock_parse_usage(repo_root):
    script = repo_root / Path('.github/scripts/check_svt_deblock_parse_usage.py')
    if not script.is_file():
        fail('missing SVT deblock parse checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_svt_frame_threads_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_svt_frame_threads_parse_safety.py')
    if not script.is_file():
        fail('missing SVT frame-threads parse checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_profdata_metadata(repo_root):
    script = repo_root / Path('.github/scripts/check_profdata_metadata.py')
    test_script = repo_root / Path('.github/scripts/test_check_profdata_metadata.py')
    if not script.is_file():
        fail('missing profdata metadata checker', script)
    if not test_script.is_file():
        fail('missing profdata metadata test', test_script)
    run_guard(repo_root, sys.executable, str(test_script))


def validate_pgo_consume_chain(repo_root):
    script = repo_root / Path('.github/scripts/check_pgo_consume_chain.py')
    metadata_script = repo_root / Path('.github/scripts/check_profdata_metadata.py')
    compile_commands_script = repo_root / Path('.github/scripts/check_compile_commands.py')
    test_script = repo_root / Path('.github/scripts/test_check_pgo_consume_chain.py')
    if not script.is_file():
        fail('missing pgo consume chain checker', script)
    if not metadata_script.is_file():
        fail('missing profdata metadata checker', metadata_script)
    if not compile_commands_script.is_file():
        fail('missing compile commands checker', compile_commands_script)
    if not test_script.is_file():
        fail('missing pgo consume chain test', test_script)
    run_guard(repo_root, sys.executable, str(test_script))


def validate_source_test_vectors(repo_root):
    script = repo_root / Path('.github/scripts/check_source_test_vectors.py')
    if not script.is_file():
        fail('missing source test vector checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root / 'source/test'))


def validate_source_legacy_patterns(repo_root):
    script = repo_root / Path('.github/scripts/check_source_legacy_patterns.py')
    if not script.is_file():
        fail('missing source legacy pattern checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_all_source_legacy_patterns(repo_root):
    script = repo_root / Path('.github/scripts/check_all_source_legacy_patterns.py')
    if not script.is_file():
        fail('missing all source legacy pattern checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_csvlog_reopen_state(repo_root):
    script = repo_root / Path('.github/scripts/check_csvlog_reopen_state.py')
    if not script.is_file():
        fail('missing csvlog reopen checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_csvlog_open_state(repo_root):
    script = repo_root / Path('.github/scripts/check_csvlog_open_state.py')
    if not script.is_file():
        fail('missing csvlog open checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_reconplay_start_failure_guard(repo_root):
    script = repo_root / Path('.github/scripts/check_reconplay_start_failure_guard.py')
    if not script.is_file():
        fail('missing reconplay start failure checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_threadpool_create_rollback(repo_root):
    script = repo_root / Path('.github/scripts/check_threadpool_create_rollback.py')
    if not script.is_file():
        fail('missing threadpool create rollback checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_threadpool_start_rollback(repo_root):
    script = repo_root / Path('.github/scripts/check_threadpool_start_rollback.py')
    if not script.is_file():
        fail('missing threadpool start rollback checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_frameencoder_start_failure_guard(repo_root):
    script = repo_root / Path('.github/scripts/check_frameencoder_start_failure_guard.py')
    if not script.is_file():
        fail('missing frame encoder start failure checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_threadedme_start_failure_guard(repo_root):
    script = repo_root / Path('.github/scripts/check_threadedme_start_failure_guard.py')
    if not script.is_file():
        fail('missing threadedME start failure checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_input_reader_start_failure_guard(repo_root):
    script = repo_root / Path('.github/scripts/check_input_reader_start_failure_guard.py')
    if not script.is_file():
        fail('missing input reader start failure checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_input_framecount_seek_guard(repo_root):
    script = repo_root / Path('.github/scripts/check_input_framecount_seek_guard.py')
    if not script.is_file():
        fail('missing input framecount seek checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_encoder_threadpool_start_failure_guard(repo_root):
    script = repo_root / Path('.github/scripts/check_encoder_threadpool_start_failure_guard.py')
    if not script.is_file():
        fail('missing encoder threadpool start failure checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_encoder_open_fail_cleanup(repo_root):
    script = repo_root / Path('.github/scripts/check_encoder_open_fail_cleanup.py')
    if not script.is_file():
        fail('missing encoder-open fail cleanup checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_lookahead_alloc_guards(repo_root):
    script = repo_root / Path('.github/scripts/check_lookahead_alloc_guards.py')
    if not script.is_file():
        fail('missing lookahead alloc guards checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_frameencoder_init_alloc_guards(repo_root):
    script = repo_root / Path('.github/scripts/check_frameencoder_init_alloc_guards.py')
    if not script.is_file():
        fail('missing frameencoder init alloc guards checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_bitcost_alloc_guards(repo_root):
    script = repo_root / Path('.github/scripts/check_bitcost_alloc_guards.py')
    if not script.is_file():
        fail('missing BitCost alloc guards checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_scaler_chroma_dims_guard(repo_root):
    script = repo_root / Path('.github/scripts/check_scaler_chroma_dims_guard.py')
    if not script.is_file():
        fail('missing scaler chroma-dimension guard checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_tonemap_payload_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_tonemap_payload_safety.py')
    if not script.is_file():
        fail('missing tone-map payload safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_temporalfilter_alloc_counts(repo_root):
    script = repo_root / Path('.github/scripts/check_temporalfilter_alloc_counts.py')
    if not script.is_file():
        fail('missing temporalfilter allocation-count checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_frameencoder_substream_alloc_guards(repo_root):
    script = repo_root / Path('.github/scripts/check_frameencoder_substream_alloc_guards.py')
    if not script.is_file():
        fail('missing FrameEncoder substream allocation checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_frameencoder_initialize_geoms_staging(repo_root):
    script = repo_root / Path('.github/scripts/check_frameencoder_initialize_geoms_staging.py')
    if not script.is_file():
        fail('missing FrameEncoder initializeGeoms staging checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_frame_create_subsample_staging(repo_root):
    script = repo_root / Path('.github/scripts/check_frame_create_subsample_staging.py')
    if not script.is_file():
        fail('missing Frame::createSubSample staging checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_frame_create_rowstate_alloc_guards(repo_root):
    script = repo_root / Path('.github/scripts/check_frame_create_rowstate_alloc_guards.py')
    if not script.is_file():
        fail('missing Frame::create row-state allocation checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_frame_create_mcstf_refpic_guards(repo_root):
    script = repo_root / Path('.github/scripts/check_frame_create_mcstf_refpic_guards.py')
    if not script.is_file():
        fail('missing Frame::create MCSTF refpic checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_frame_create_mcstffencpic_guards(repo_root):
    script = repo_root / Path('.github/scripts/check_frame_create_mcstffencpic_guards.py')
    if not script.is_file():
        fail('missing Frame::create MCSTF fenc PicYuv checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_frame_create_top_alloc_guards(repo_root):
    script = repo_root / Path('.github/scripts/check_frame_create_top_alloc_guards.py')
    if not script.is_file():
        fail('missing Frame::create top allocation checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_frame_alloc_encode_data_guards(repo_root):
    script = repo_root / Path('.github/scripts/check_frame_alloc_encode_data_guards.py')
    if not script.is_file():
        fail('missing Frame::allocEncodeData checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_x265_picture_init_null_guard(repo_root):
    script = repo_root / Path('.github/scripts/check_x265_picture_init_null_guard.py')
    if not script.is_file():
        fail('missing x265_picture_init null guard checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_x265_param_default_null_guard(repo_root):
    script = repo_root / Path('.github/scripts/check_x265_param_default_null_guard.py')
    if not script.is_file():
        fail('missing x265_param_default null guard checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_x265_param_default_preset_null_guard(repo_root):
    script = repo_root / Path('.github/scripts/check_x265_param_default_preset_null_guard.py')
    if not script.is_file():
        fail('missing x265_param_default_preset null guard checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_x265_param_parse_null_guard(repo_root):
    script = repo_root / Path('.github/scripts/check_x265_param_parse_null_guard.py')
    if not script.is_file():
        fail('missing x265_param_parse null guard checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_x265_param_apply_profile_null_guard(repo_root):
    script = repo_root / Path('.github/scripts/check_x265_param_apply_profile_null_guard.py')
    if not script.is_file():
        fail('missing x265_param_apply_profile null guard checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_param_api_null_guards(repo_root):
    script = repo_root / Path('.github/scripts/check_param_api_null_guards.py')
    if not script.is_file():
        fail('missing public param API null guard checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_zone_and_scenecut_param_parse_null_guards(repo_root):
    script = repo_root / Path('.github/scripts/check_zone_and_scenecut_param_parse_null_guards.py')
    if not script.is_file():
        fail('missing zone/scenecut param parse null guard checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_analysis_data_api_null_guards(repo_root):
    script = repo_root / Path('.github/scripts/check_analysis_data_api_null_guards.py')
    if not script.is_file():
        fail('missing analysis data API null guard checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_query_api_output_null_guards(repo_root):
    script = repo_root / Path('.github/scripts/check_query_api_output_null_guards.py')
    if not script.is_file():
        fail('missing query API output null guard checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_x265_dither_image_null_guards(repo_root):
    script = repo_root / Path('.github/scripts/check_x265_dither_image_null_guards.py')
    if not script.is_file():
        fail('missing x265_dither_image null guard checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_csvlog_api_null_guards(repo_root):
    script = repo_root / Path('.github/scripts/check_csvlog_api_null_guards.py')
    if not script.is_file():
        fail('missing CSV log API null guard checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_csvlog_fail_state(repo_root):
    script = repo_root / Path('.github/scripts/check_csvlog_fail_state.py')
    if not script.is_file():
        fail('missing CSV log fail-state checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_vmaf_api_null_guards(repo_root):
    script = repo_root / Path('.github/scripts/check_vmaf_api_null_guards.py')
    if not script.is_file():
        fail('missing VMAF API null guard checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_threadedme_create_guards(repo_root):
    script = repo_root / Path('.github/scripts/check_threadedme_create_guards.py')
    if not script.is_file():
        fail('missing ThreadedME create guard checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_threadpool_windows_numa_affinity_guard(repo_root):
    script = repo_root / Path('.github/scripts/check_threadpool_windows_numa_affinity_guard.py')
    if not script.is_file():
        fail('missing threadpool Windows NUMA affinity guard checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_encoder_ctu_info_guards(repo_root):
    script = repo_root / Path('.github/scripts/check_encoder_ctu_info_guards.py')
    if not script.is_file():
        fail('missing encoder CTU-info guard checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_encoder_open_alloc_guard(repo_root):
    script = repo_root / Path('.github/scripts/check_encoder_open_alloc_guard.py')
    if not script.is_file():
        fail('missing encoder-open allocation guard checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_encoder_create_object_alloc_guards(repo_root):
    script = repo_root / Path('.github/scripts/check_encoder_create_object_alloc_guards.py')
    if not script.is_file():
        fail('missing Encoder::create object allocation checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_encoder_create_core_alloc_guards(repo_root):
    script = repo_root / Path('.github/scripts/check_encoder_create_core_alloc_guards.py')
    if not script.is_file():
        fail('missing Encoder::create core allocation checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_encoder_encode_frame_alloc_guards(repo_root):
    script = repo_root / Path('.github/scripts/check_encoder_encode_frame_alloc_guards.py')
    if not script.is_file():
        fail('missing Encoder::encode frame allocation checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_encoder_encode_setup_rollback(repo_root):
    script = repo_root / Path('.github/scripts/check_encoder_encode_setup_rollback.py')
    if not script.is_file():
        fail('missing Encoder::encode setup rollback checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_lowres_aqlayer_alloc_guards(repo_root):
    script = repo_root / Path('.github/scripts/check_lowres_aqlayer_alloc_guards.py')
    if not script.is_file():
        fail('missing lowres AQ-layer allocation checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_lowres_histogram_alloc_guards(repo_root):
    script = repo_root / Path('.github/scripts/check_lowres_histogram_alloc_guards.py')
    if not script.is_file():
        fail('missing lowres histogram allocation checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_frame_edge_aq_alloc_guards(repo_root):
    script = repo_root / Path('.github/scripts/check_frame_edge_aq_alloc_guards.py')
    if not script.is_file():
        fail('missing Frame edge-AQ allocation checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_cutree_sharedmem_alloc_guards(repo_root):
    script = repo_root / Path('.github/scripts/check_cutree_sharedmem_alloc_guards.py')
    if not script.is_file():
        fail('missing CUTree shared-memory allocation checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_scaler_helper_alloc_guards(repo_root):
    script = repo_root / Path('.github/scripts/check_scaler_helper_alloc_guards.py')
    if not script.is_file():
        fail('missing scaler helper allocation checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_lookahead_create_rollback(repo_root):
    script = repo_root / Path('.github/scripts/check_lookahead_create_rollback.py')
    if not script.is_file():
        fail('missing Lookahead create rollback checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_sea_integral_buffer_lifecycle(repo_root):
    script = repo_root / Path('.github/scripts/check_sea_integral_buffer_lifecycle.py')
    if not script.is_file():
        fail('missing SEA integral buffer lifecycle checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_lookahead_tld_yuv_guards(repo_root):
    script = repo_root / Path('.github/scripts/check_lookahead_tld_yuv_guards.py')
    if not script.is_file():
        fail('missing Lookahead TLD YUV guard checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_vmaf_temp_buffer_cleanup(repo_root):
    script = repo_root / Path('.github/scripts/check_vmaf_temp_buffer_cleanup.py')
    if not script.is_file():
        fail('missing VMAF temp-buffer cleanup checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_encoder_rps_list_alloc_guard(repo_root):
    script = repo_root / Path('.github/scripts/check_encoder_rps_list_alloc_guard.py')
    if not script.is_file():
        fail('missing encoder RPS-list allocation checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_encoder_headers_arg_guard(repo_root):
    script = repo_root / Path('.github/scripts/check_encoder_headers_arg_guard.py')
    if not script.is_file():
        fail('missing encoder-headers argument guard checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_wavefront_init_rollback(repo_root):
    script = repo_root / Path('.github/scripts/check_wavefront_init_rollback.py')
    if not script.is_file():
        fail('missing WaveFront init rollback checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_framedata_create_rollback(repo_root):
    script = repo_root / Path('.github/scripts/check_framedata_create_rollback.py')
    if not script.is_file():
        fail('missing FrameData create rollback checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_scaler_init_rollback(repo_root):
    script = repo_root / Path('.github/scripts/check_scaler_init_rollback.py')
    if not script.is_file():
        fail('missing scaler init rollback checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_reconfig_save_zone_rollback(repo_root):
    script = repo_root / Path('.github/scripts/check_reconfig_save_zone_rollback.py')
    if not script.is_file():
        fail('missing reconfig save zone rollback checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_cli_config_file_parse_usage(repo_root):
    script = repo_root / Path('.github/scripts/check_cli_config_file_parse_usage.py')
    if not script.is_file():
        fail('missing cli config file parse checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_lambda_file_parse_usage(repo_root):
    script = repo_root / Path('.github/scripts/check_lambda_file_parse_usage.py')
    if not script.is_file():
        fail('missing lambda-file parse checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_lambda_file_error_state(repo_root):
    script = repo_root / Path('.github/scripts/check_lambda_file_error_state.py')
    if not script.is_file():
        fail('missing lambda-file error-state checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_param_checked_parse_usage(repo_root):
    script = repo_root / Path('.github/scripts/check_param_checked_parse_usage.py')
    if not script.is_file():
        fail('missing param checked parse checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_scenecut_qp_macro_cleanup(repo_root):
    script = repo_root / Path('.github/scripts/check_scenecut_qp_macro_cleanup.py')
    if not script.is_file():
        fail('missing scenecut-aware QP macro cleanup checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_zone_param_macro_cleanup(repo_root):
    script = repo_root / Path('.github/scripts/check_zone_param_macro_cleanup.py')
    if not script.is_file():
        fail('missing zone param macro cleanup checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_param_parse_macro_cleanup(repo_root):
    script = repo_root / Path('.github/scripts/check_param_parse_macro_cleanup.py')
    if not script.is_file():
        fail('missing param parse macro cleanup checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_qpfile_parse_usage(repo_root):
    script = repo_root / Path('.github/scripts/check_qpfile_parse_usage.py')
    if not script.is_file():
        fail('missing qpfile parse checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_qpfile_error_state(repo_root):
    script = repo_root / Path('.github/scripts/check_qpfile_error_state.py')
    if not script.is_file():
        fail('missing qpfile error-state checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_strict_scan_parsing_usage(repo_root):
    script = repo_root / Path('.github/scripts/check_strict_scan_parsing_usage.py')
    if not script.is_file():
        fail('missing strict-scan parsing checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_zonefile_parse_usage(repo_root):
    script = repo_root / Path('.github/scripts/check_zonefile_parse_usage.py')
    if not script.is_file():
        fail('missing zonefile parse checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_external_input_atoi_usage(repo_root):
    script = repo_root / Path('.github/scripts/check_external_input_atoi_usage.py')
    if not script.is_file():
        fail('missing external input atoi checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_dolby_vision_rpu_parse_usage(repo_root):
    script = repo_root / Path('.github/scripts/check_dolby_vision_rpu_parse_usage.py')
    if not script.is_file():
        fail('missing Dolby Vision RPU parse checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_cmake_cxx20_contract(repo_root):
    script = repo_root / Path('.github/scripts/check_cmake_cxx20_contract.py')
    if not script.is_file():
        fail('missing CMake GNU++20 contract checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root / 'source'))


def validate_nalu_file_parse_usage(repo_root):
    script = repo_root / Path('.github/scripts/check_nalu_file_parse_usage.py')
    if not script.is_file():
        fail('missing nalu-file parse checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_nalu_file_error_state(repo_root):
    script = repo_root / Path('.github/scripts/check_nalu_file_error_state.py')
    if not script.is_file():
        fail('missing nalu-file error-state checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_analysis_reuse_refine_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_analysis_reuse_refine_parse_safety.py')
    if not script.is_file():
        fail('missing analysis/reuse/refine parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_analysis_output_fail_state(repo_root):
    script = repo_root / Path('.github/scripts/check_analysis_output_fail_state.py')
    if not script.is_file():
        fail('missing analysis output fail-state checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_scalinglist_parse_usage(repo_root):
    script = repo_root / Path('.github/scripts/check_scalinglist_parse_usage.py')
    if not script.is_file():
        fail('missing scalinglist parse checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_checked_parse_helper_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_checked_parse_helper_safety.py')
    if not script.is_file():
        fail('missing checked-parse helper checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_param_uint_token_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_param_uint_token_safety.py')
    if not script.is_file():
        fail('missing param uint token checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_mkv_header_cleanup_state(repo_root):
    script = repo_root / Path('.github/scripts/check_mkv_header_cleanup_state.py')
    if not script.is_file():
        fail('missing MKV header cleanup-state checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_vmaf_file_cleanup_state(repo_root):
    script = repo_root / Path('.github/scripts/check_vmaf_file_cleanup_state.py')
    if not script.is_file():
        fail('missing VMAF file cleanup-state checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_vmaf_frame_read_state(repo_root):
    script = repo_root / Path('.github/scripts/check_vmaf_frame_read_state.py')
    if not script.is_file():
        fail('missing VMAF frame read-state checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_vmaf_picture_read_failure(repo_root):
    script = repo_root / Path('.github/scripts/check_vmaf_picture_read_failure.py')
    if not script.is_file():
        fail('missing VMAF picture-read failure checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_vmaf_score_failure_propagation(repo_root):
    script = repo_root / Path('.github/scripts/check_vmaf_score_failure_propagation.py')
    if not script.is_file():
        fail('missing VMAF score failure propagation checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_vmaf_data_cleanup_state(repo_root):
    script = repo_root / Path('.github/scripts/check_vmaf_data_cleanup_state.py')
    if not script.is_file():
        fail('missing VMAF data cleanup-state checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_param_double_token_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_param_double_token_safety.py')
    if not script.is_file():
        fail('missing param double token checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_param_pair_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_param_pair_parse_safety.py')
    if not script.is_file():
        fail('missing param pair parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_parse_name_assignment_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_parse_name_assignment_safety.py')
    if not script.is_file():
        fail('missing parseName assignment safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_ratecontrol_first_pass_parse_usage(repo_root):
    script = repo_root / Path('.github/scripts/check_ratecontrol_first_pass_parse_usage.py')
    if not script.is_file():
        fail('missing ratecontrol first-pass parse checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_preset_index_parse_usage(repo_root):
    script = repo_root / Path('.github/scripts/check_preset_index_parse_usage.py')
    if not script.is_file():
        fail('missing preset-index parse checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_cpu_list_parse_usage(repo_root):
    script = repo_root / Path('.github/scripts/check_cpu_list_parse_usage.py')
    if not script.is_file():
        fail('missing CPU-list parse checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_interlace_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_interlace_parse_safety.py')
    if not script.is_file():
        fail('missing interlace parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_rdoq_level_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_rdoq_level_parse_safety.py')
    if not script.is_file():
        fail('missing rdoq-level parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_ratecontrol_numeric_helper_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_ratecontrol_numeric_helper_safety.py')
    if not script.is_file():
        fail('missing ratecontrol numeric helper safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_ratecontrol_stats_parse_usage(repo_root):
    script = repo_root / Path('.github/scripts/check_ratecontrol_stats_parse_usage.py')
    if not script.is_file():
        fail('missing ratecontrol stats parse checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_ratecontrol_stats_line_parse_usage(repo_root):
    script = repo_root / Path('.github/scripts/check_ratecontrol_stats_line_parse_usage.py')
    if not script.is_file():
        fail('missing ratecontrol stats-line parse checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_ratecontrol_stats_prefix_parse_usage(repo_root):
    script = repo_root / Path('.github/scripts/check_ratecontrol_stats_prefix_parse_usage.py')
    if not script.is_file():
        fail('missing ratecontrol stats-prefix parse checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_param_bool_numeric_int_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_param_bool_numeric_int_safety.py')
    if not script.is_file():
        fail('missing param bool-or-numeric-int safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_bitrate_mode_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_bitrate_mode_parse_safety.py')
    if not script.is_file():
        fail('missing bitrate mode parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_qp_mode_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_qp_mode_parse_safety.py')
    if not script.is_file():
        fail('missing qp mode parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_strict_cbr_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_strict_cbr_parse_safety.py')
    if not script.is_file():
        fail('missing strict-cbr parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_sao_create_rollback(repo_root):
    script = repo_root / Path('.github/scripts/check_sao_create_rollback.py')
    if not script.is_file():
        fail('missing SAO create rollback checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_svt_bitrate_mode_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_svt_bitrate_mode_parse_safety.py')
    if not script.is_file():
        fail('missing SVT bitrate mode parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_api_zone_open_staging(repo_root):
    script = repo_root / Path('.github/scripts/check_api_zone_open_staging.py')
    if not script.is_file():
        fail('missing zone open staging checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_copy_params_zone_replace_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_copy_params_zone_replace_safety.py')
    if not script.is_file():
        fail('missing copy_params zone replacement safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_encoder_parameters_output_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_encoder_parameters_output_safety.py')
    if not script.is_file():
        fail('missing encoder parameters output safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_encoder_get_stats_size_guard(repo_root):
    script = repo_root / Path('.github/scripts/check_encoder_get_stats_size_guard.py')
    if not script.is_file():
        fail('missing encoder_get_stats size checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_cli_output_failure_full_cleanup(repo_root):
    script = repo_root / Path('.github/scripts/check_cli_output_failure_full_cleanup.py')
    if not script.is_file():
        fail('missing CLI output failure cleanup checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_lavf_openfile_cleanup(repo_root):
    script = repo_root / Path('.github/scripts/check_lavf_openfile_cleanup.py')
    if not script.is_file():
        fail('missing Lavf openfile cleanup checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_svt_qp_mode_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_svt_qp_mode_parse_safety.py')
    if not script.is_file():
        fail('missing SVT qp mode parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_reader_thread_alloc_guards(repo_root):
    script = repo_root / Path('.github/scripts/check_reader_thread_alloc_guards.py')
    if not script.is_file():
        fail('missing Reader::threadMain allocation guard checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_scaler_thread_alloc_guards(repo_root):
    script = repo_root / Path('.github/scripts/check_scaler_thread_alloc_guards.py')
    if not script.is_file():
        fail('missing Scaler::threadMain allocation guard checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_hdr10_json_metadata_ownership(repo_root):
    script = repo_root / Path('.github/scripts/check_hdr10_json_metadata_ownership.py')
    if not script.is_file():
        fail('missing HDR10 JSON metadata ownership checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_temporalfilter_refpic_rollback(repo_root):
    script = repo_root / Path('.github/scripts/check_temporalfilter_refpic_rollback.py')
    if not script.is_file():
        fail('missing temporalfilter refpic rollback checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_temporalfilter_refpic_state_init(repo_root):
    script = repo_root / Path('.github/scripts/check_temporalfilter_refpic_state_init.py')
    if not script.is_file():
        fail('missing temporalfilter refpic state-init checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_temporalfilter_metld_yuv_guards(repo_root):
    script = repo_root / Path('.github/scripts/check_temporalfilter_metld_yuv_guards.py')
    if not script.is_file():
        fail('missing temporalfilter MotionEstimatorTLD YUV checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_param_string_replace_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_param_string_replace_safety.py')
    if not script.is_file():
        fail('missing param string replacement safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_zones_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_zones_parse_safety.py')
    if not script.is_file():
        fail('missing zones parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_raw_output_fail_state(repo_root):
    script = repo_root / Path('.github/scripts/check_raw_output_fail_state.py')
    if not script.is_file():
        fail('missing RAW output fail-state checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_cli_progress_file_state(repo_root):
    script = repo_root / Path('.github/scripts/check_cli_progress_file_state.py')
    if not script.is_file():
        fail('missing CLI progress-file checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_raw_output_write_guard(repo_root):
    script = repo_root / Path('.github/scripts/check_raw_output_write_guard.py')
    if not script.is_file():
        fail('missing RAW output write checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_raw_stdout_flush_state(repo_root):
    script = repo_root / Path('.github/scripts/check_raw_stdout_flush_state.py')
    if not script.is_file():
        fail('missing RAW stdout flush checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_mkv_output_fail_state(repo_root):
    script = repo_root / Path('.github/scripts/check_mkv_output_fail_state.py')
    if not script.is_file():
        fail('missing MKV output fail-state checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_mkv_close_fail_state(repo_root):
    script = repo_root / Path('.github/scripts/check_mkv_close_fail_state.py')
    if not script.is_file():
        fail('missing MKV close fail-state checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_recon_output_write_guard(repo_root):
    script = repo_root / Path('.github/scripts/check_recon_output_write_guard.py')
    if not script.is_file():
        fail('missing recon output write checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_recon_output_stream_state(repo_root):
    script = repo_root / Path('.github/scripts/check_recon_output_stream_state.py')
    if not script.is_file():
        fail('missing recon output stream checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_y4m_recon_seek_guard(repo_root):
    script = repo_root / Path('.github/scripts/check_y4m_recon_seek_guard.py')
    if not script.is_file():
        fail('missing Y4M recon seek checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_recon_finalize_state(repo_root):
    script = repo_root / Path('.github/scripts/check_recon_finalize_state.py')
    if not script.is_file():
        fail('missing recon finalize checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_gop_options_fail_state(repo_root):
    script = repo_root / Path('.github/scripts/check_gop_options_fail_state.py')
    if not script.is_file():
        fail('missing GOP options fail-state checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_gop_output_fail_state(repo_root):
    script = repo_root / Path('.github/scripts/check_gop_output_fail_state.py')
    if not script.is_file():
        fail('missing GOP output fail-state checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_vmaf_recon_state_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_vmaf_recon_state_safety.py')
    if not script.is_file():
        fail('missing VMAF/recon state safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_reconplay_pipe_fail_state(repo_root):
    script = repo_root / Path('.github/scripts/check_reconplay_pipe_fail_state.py')
    if not script.is_file():
        fail('missing ReconPlay pipe fail-state checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_lambda_file_failfast(repo_root):
    script = repo_root / Path('.github/scripts/check_lambda_file_failfast.py')
    if not script.is_file():
        fail('missing lambda file fail-fast checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_lavf_buffer_replace_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_lavf_buffer_replace_safety.py')
    if not script.is_file():
        fail('missing LAVF buffer replace safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_svt_pools_parse_usage(repo_root):
    script = repo_root / Path('.github/scripts/check_svt_pools_parse_usage.py')
    if not script.is_file():
        fail('missing SVT pools parse checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_threadpool_cpu_frequency_parse_usage(repo_root):
    script = repo_root / Path('.github/scripts/check_threadpool_cpu_frequency_parse_usage.py')
    if not script.is_file():
        fail('missing threadpool CPU frequency parse checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_threadpool_cpu_frequency_tail_guard(repo_root):
    script = repo_root / Path('.github/scripts/check_threadpool_cpu_frequency_tail_guard.py')
    if not script.is_file():
        fail('missing threadpool CPU frequency tail checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_lavf_framecount_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_lavf_framecount_parse_safety.py')
    if not script.is_file():
        fail('missing lavf framecount parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_gop_close_fail_state(repo_root):
    script = repo_root / Path('.github/scripts/check_gop_close_fail_state.py')
    if not script.is_file():
        fail('missing GOP close fail-state checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_gop_smart_fwrite_retry_guard(repo_root):
    script = repo_root / Path('.github/scripts/check_gop_smart_fwrite_retry_guard.py')
    if not script.is_file():
        fail('missing gop smart_fwrite retry checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_y4m_yuv_row_buffer_alloc_guard(repo_root):
    script = repo_root / Path('.github/scripts/check_y4m_yuv_row_buffer_alloc_guard.py')
    if not script.is_file():
        fail('missing Y4M/YUV row-buffer allocation checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_output_open_alloc_guards(repo_root):
    script = repo_root / Path('.github/scripts/check_output_open_alloc_guards.py')
    if not script.is_file():
        fail('missing output open allocation checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_param_bool_numeric_double_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_param_bool_numeric_double_safety.py')
    if not script.is_file():
        fail('missing param bool-or-numeric-double safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_csv_log_level_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_csv_log_level_parse_safety.py')
    if not script.is_file():
        fail('missing csv-log-level parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_bool_int_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_bool_int_parse_safety.py')
    if not script.is_file():
        fail('missing bool-int parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_aq_mode_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_aq_mode_parse_safety.py')
    if not script.is_file():
        fail('missing aq-mode parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_multiview_scc_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_multiview_scc_parse_safety.py')
    if not script.is_file():
        fail('missing multiview-scc parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_view_layer_limit_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_view_layer_limit_safety.py')
    if not script.is_file():
        fail('missing view/layer limit safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_bframes_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_bframes_parse_safety.py')
    if not script.is_file():
        fail('missing bframes parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_bframe_bias_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_bframe_bias_parse_safety.py')
    if not script.is_file():
        fail('missing bframe-bias parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_keyint_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_keyint_parse_safety.py')
    if not script.is_file():
        fail('missing keyint parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_min_keyint_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_min_keyint_parse_safety.py')
    if not script.is_file():
        fail('missing min-keyint parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_ip_pb_ratio_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_ip_pb_ratio_parse_safety.py')
    if not script.is_file():
        fail('missing ip/pb ratio parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_vbv_end_frame_adjust_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_vbv_end_frame_adjust_safety.py')
    if not script.is_file():
        fail('missing vbv-end-fr-adj safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_zone_alloc_size_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_zone_alloc_size_safety.py')
    if not script.is_file():
        fail('missing zone alloc size safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_ref_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_ref_parse_safety.py')
    if not script.is_file():
        fail('missing ref parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_radl_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_radl_parse_safety.py')
    if not script.is_file():
        fail('missing radl parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_cbqpoffs_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_cbqpoffs_parse_safety.py')
    if not script.is_file():
        fail('missing cbqpoffs parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_crqpoffs_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_crqpoffs_parse_safety.py')
    if not script.is_file():
        fail('missing crqpoffs parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_pass_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_pass_parse_safety.py')
    if not script.is_file():
        fail('missing pass parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_qg_size_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_qg_size_parse_safety.py')
    if not script.is_file():
        fail('missing qg-size parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_qpmin_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_qpmin_parse_safety.py')
    if not script.is_file():
        fail('missing qpmin parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_qpmax_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_qpmax_parse_safety.py')
    if not script.is_file():
        fail('missing qpmax parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_chromaloc_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_chromaloc_parse_safety.py')
    if not script.is_file():
        fail('missing chromaloc parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_vbv_maxrate_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_vbv_maxrate_parse_safety.py')
    if not script.is_file():
        fail('missing vbv-maxrate parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_vbv_bufsize_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_vbv_bufsize_parse_safety.py')
    if not script.is_file():
        fail('missing vbv-bufsize parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_log2_max_poc_lsb_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_log2_max_poc_lsb_parse_safety.py')
    if not script.is_file():
        fail('missing log2-max-poc-lsb parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_nr_intra_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_nr_intra_parse_safety.py')
    if not script.is_file():
        fail('missing nr-intra parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_nr_inter_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_nr_inter_parse_safety.py')
    if not script.is_file():
        fail('missing nr-inter parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_rc_lookahead_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_rc_lookahead_parse_safety.py')
    if not script.is_file():
        fail('missing rc-lookahead parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_slices_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_slices_parse_safety.py')
    if not script.is_file():
        fail('missing slices parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_limit_tu_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_limit_tu_parse_safety.py')
    if not script.is_file():
        fail('missing limit-tu parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_lookahead_threads_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_lookahead_threads_parse_safety.py')
    if not script.is_file():
        fail('missing lookahead-threads parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_vbv_fullness_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_vbv_fullness_parse_safety.py')
    if not script.is_file():
        fail('missing vbv-fullness parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_rdpenalty_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_rdpenalty_parse_safety.py')
    if not script.is_file():
        fail('missing rdpenalty parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_gop_lookahead_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_gop_lookahead_parse_safety.py')
    if not script.is_file():
        fail('missing gop-lookahead parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_gop_lookahead_usage_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_gop_lookahead_usage_safety.py')
    if not script.is_file():
        fail('missing gop-lookahead usage safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_zonefile_startframe_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_zonefile_startframe_safety.py')
    if not script.is_file():
        fail('missing zonefile startFrame safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_reconfig_window_size_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_reconfig_window_size_safety.py')
    if not script.is_file():
        fail('missing reconfig window size safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_no_reset_zone_prefill_guard(repo_root):
    script = repo_root / Path('.github/scripts/check_no_reset_zone_prefill_guard.py')
    if not script.is_file():
        fail('missing no-reset zone prefill checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_common_logfile_open_state(repo_root):
    script = repo_root / Path('.github/scripts/check_common_logfile_open_state.py')
    if not script.is_file():
        fail('missing common logfile open checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_common_logfile_close_state(repo_root):
    script = repo_root / Path('.github/scripts/check_common_logfile_close_state.py')
    if not script.is_file():
        fail('missing common logfile close checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_common_slurp_open_state(repo_root):
    script = repo_root / Path('.github/scripts/check_common_slurp_open_state.py')
    if not script.is_file():
        fail('missing common slurp open checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_common_slurp_close_state(repo_root):
    script = repo_root / Path('.github/scripts/check_common_slurp_close_state.py')
    if not script.is_file():
        fail('missing common slurp close checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_common_slurp_size_guard(repo_root):
    script = repo_root / Path('.github/scripts/check_common_slurp_size_guard.py')
    if not script.is_file():
        fail('missing common slurp size checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_cutree_sharedmem_name_guard(repo_root):
    script = repo_root / Path('.github/scripts/check_cutree_sharedmem_name_guard.py')
    if not script.is_file():
        fail('missing cutree shared-memory name checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_mkv_writer_open_state(repo_root):
    script = repo_root / Path('.github/scripts/check_mkv_writer_open_state.py')
    if not script.is_file():
        fail('missing mkv writer open checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_mkv_writer_close_state(repo_root):
    script = repo_root / Path('.github/scripts/check_mkv_writer_close_state.py')
    if not script.is_file():
        fail('missing mkv writer close checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_riscv_cpuinfo_open_state(repo_root):
    script = repo_root / Path('.github/scripts/check_riscv_cpuinfo_open_state.py')
    if not script.is_file():
        fail('missing riscv cpuinfo open checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_riscv_cpuinfo_close_state(repo_root):
    script = repo_root / Path('.github/scripts/check_riscv_cpuinfo_close_state.py')
    if not script.is_file():
        fail('missing riscv cpuinfo close checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_cli_destroy_close_state(repo_root):
    script = repo_root / Path('.github/scripts/check_cli_destroy_close_state.py')
    if not script.is_file():
        fail('missing cli destroy close checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_encoder_destroy_close_state(repo_root):
    script = repo_root / Path('.github/scripts/check_encoder_destroy_close_state.py')
    if not script.is_file():
        fail('missing encoder destroy close checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_analysis_intra_alloc_guards(repo_root):
    script = repo_root / Path('.github/scripts/check_analysis_intra_alloc_guards.py')
    if not script.is_file():
        fail('missing intra analysis allocation checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_analysis_inter_alloc_guards(repo_root):
    script = repo_root / Path('.github/scripts/check_analysis_inter_alloc_guards.py')
    if not script.is_file():
        fail('missing inter analysis allocation checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_analysis_inter_motion_alloc_guards(repo_root):
    script = repo_root / Path('.github/scripts/check_analysis_inter_motion_alloc_guards.py')
    if not script.is_file():
        fail('missing inter motion allocation checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_analysis_inter_temp_luma_alloc_guard(repo_root):
    script = repo_root / Path('.github/scripts/check_analysis_inter_temp_luma_alloc_guard.py')
    if not script.is_file():
        fail('missing inter tempLuma allocation checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_analysis_inter_depth_run_guard(repo_root):
    script = repo_root / Path('.github/scripts/check_analysis_inter_depth_run_guard.py')
    if not script.is_file():
        fail('missing inter depth-run checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_analysis_cache_cost_guards(repo_root):
    script = repo_root / Path('.github/scripts/check_analysis_cache_cost_guards.py')
    if not script.is_file():
        fail('missing analysis cacheCost guard checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_scaled_analysis_load_alloc_guards(repo_root):
    script = repo_root / Path('.github/scripts/check_scaled_analysis_load_alloc_guards.py')
    if not script.is_file():
        fail('missing scaled analysis-load alloc guard checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_analysis_2pass_load_cleanup(repo_root):
    script = repo_root / Path('.github/scripts/check_analysis_2pass_load_cleanup.py')
    if not script.is_file():
        fail('missing 2-pass analysis-load cleanup checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_picyuv_offset_rollback(repo_root):
    script = repo_root / Path('.github/scripts/check_picyuv_offset_rollback.py')
    if not script.is_file():
        fail('missing PicYuv offset rollback checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_motion_reference_init_guards(repo_root):
    script = repo_root / Path('.github/scripts/check_motion_reference_init_guards.py')
    if not script.is_file():
        fail('missing MotionReference init checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_motionestimate_init_guard(repo_root):
    script = repo_root / Path('.github/scripts/check_motionestimate_init_guard.py')
    if not script.is_file():
        fail('missing MotionEstimate init checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_motion_sea_scratch_guard(repo_root):
    script = repo_root / Path('.github/scripts/check_motion_sea_scratch_guard.py')
    if not script.is_file():
        fail('missing SEA motion scratch checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_scaler_slice_linebuf_init(repo_root):
    script = repo_root / Path('.github/scripts/check_scaler_slice_linebuf_init.py')
    if not script.is_file():
        fail('missing ScalerSlice lineBuf init checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_analysis_load_staging_cleanup(repo_root):
    script = repo_root / Path('.github/scripts/check_analysis_load_staging_cleanup.py')
    if not script.is_file():
        fail('missing analysis-load staging cleanup checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_atc_sei_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_atc_sei_parse_safety.py')
    if not script.is_file():
        fail('missing ATC-SEI parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_chunk_start_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_chunk_start_parse_safety.py')
    if not script.is_file():
        fail('missing chunk-start parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_chunk_end_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_chunk_end_parse_safety.py')
    if not script.is_file():
        fail('missing chunk-end parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_deblock_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_deblock_parse_safety.py')
    if not script.is_file():
        fail('missing deblock parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_hash_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_hash_parse_safety.py')
    if not script.is_file():
        fail('missing hash parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_hme_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_hme_parse_safety.py')
    if not script.is_file():
        fail('missing HME parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_lookahead_slices_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_lookahead_slices_parse_safety.py')
    if not script.is_file():
        fail('missing lookahead-slices parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_merange_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_merange_parse_safety.py')
    if not script.is_file():
        fail('missing merange parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_misc_control_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_misc_control_parse_safety.py')
    if not script.is_file():
        fail('missing misc-control parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_pic_struct_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_pic_struct_parse_safety.py')
    if not script.is_file():
        fail('missing pic-struct parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_psy_scale_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_psy_scale_parse_safety.py')
    if not script.is_file():
        fail('missing psy-scale parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_rskip_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_rskip_parse_safety.py')
    if not script.is_file():
        fail('missing rskip parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_rskip_edge_threshold_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_rskip_edge_threshold_parse_safety.py')
    if not script.is_file():
        fail('missing rskip-edge-threshold parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_sar_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_sar_parse_safety.py')
    if not script.is_file():
        fail('missing SAR parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_selective_sao_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_selective_sao_parse_safety.py')
    if not script.is_file():
        fail('missing selective-sao parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_ssim_rd_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_ssim_rd_parse_safety.py')
    if not script.is_file():
        fail('missing ssim-rd parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_temporal_layers_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_temporal_layers_parse_safety.py')
    if not script.is_file():
        fail('missing temporal-layers parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_uint32_token_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_uint32_token_parse_safety.py')
    if not script.is_file():
        fail('missing uint32 token parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_cli_inputfn_alloc_guard(repo_root):
    script = repo_root / Path('.github/scripts/check_cli_inputfn_alloc_guard.py')
    if not script.is_file():
        fail('missing CLI input filename allocation checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_cli_vmaf_format_cleanup(repo_root):
    script = repo_root / Path('.github/scripts/check_cli_vmaf_format_cleanup.py')
    if not script.is_file():
        fail('missing CLI VMAF format cleanup checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_input_filename_copy_usage(repo_root):
    script = repo_root / Path('.github/scripts/check_input_filename_copy_usage.py')
    if not script.is_file():
        fail('missing input filename copy checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_print_status_progress_guard(repo_root):
    script = repo_root / Path('.github/scripts/check_print_status_progress_guard.py')
    if not script.is_file():
        fail('missing printStatus progress checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_recon_basename_parse_usage(repo_root):
    script = repo_root / Path('.github/scripts/check_recon_basename_parse_usage.py')
    if not script.is_file():
        fail('missing recon basename parse checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_zonefile_parse_no_exit(repo_root):
    script = repo_root / Path('.github/scripts/check_zonefile_parse_no_exit.py')
    if not script.is_file():
        fail('missing zonefile no-exit checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_svt_aud_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_svt_aud_parse_safety.py')
    if not script.is_file():
        fail('missing SVT aud parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_svt_base_layer_switch_mode_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_svt_base_layer_switch_mode_parse_safety.py')
    if not script.is_file():
        fail('missing SVT base-layer-switch-mode parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_svt_compressed_ten_bit_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_svt_compressed_ten_bit_parse_safety.py')
    if not script.is_file():
        fail('missing SVT compressed-ten-bit parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_svt_constrained_intra_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_svt_constrained_intra_parse_safety.py')
    if not script.is_file():
        fail('missing SVT constrained-intra parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_svt_fps_in_vps_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_svt_fps_in_vps_parse_safety.py')
    if not script.is_file():
        fail('missing SVT fps-in-vps parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_svt_frames_to_be_encoded_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_svt_frames_to_be_encoded_parse_safety.py')
    if not script.is_file():
        fail('missing SVT frames-to-be-encoded parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_svt_hdr_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_svt_hdr_parse_safety.py')
    if not script.is_file():
        fail('missing SVT hdr parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_svt_hierarchical_level_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_svt_hierarchical_level_parse_safety.py')
    if not script.is_file():
        fail('missing SVT hierarchical-level parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_svt_high_tier_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_svt_high_tier_parse_safety.py')
    if not script.is_file():
        fail('missing SVT high-tier parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_svt_hrd_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_svt_hrd_parse_safety.py')
    if not script.is_file():
        fail('missing SVT hrd parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_svt_input_depth_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_svt_input_depth_parse_safety.py')
    if not script.is_file():
        fail('missing SVT input-depth parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_svt_keyint_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_svt_keyint_parse_safety.py')
    if not script.is_file():
        fail('missing SVT keyint parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_svt_master_display_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_svt_master_display_parse_safety.py')
    if not script.is_file():
        fail('missing SVT master-display parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_svt_nalu_file_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_svt_nalu_file_parse_safety.py')
    if not script.is_file():
        fail('missing SVT nalu-file parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_svt_pred_struct_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_svt_pred_struct_parse_safety.py')
    if not script.is_file():
        fail('missing SVT pred-struct parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_svt_qpmax_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_svt_qpmax_parse_safety.py')
    if not script.is_file():
        fail('missing SVT qpmax parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_svt_qpmin_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_svt_qpmin_parse_safety.py')
    if not script.is_file():
        fail('missing SVT qpmin parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_svt_rc_lookahead_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_svt_rc_lookahead_parse_safety.py')
    if not script.is_file():
        fail('missing SVT rc-lookahead parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_svt_sao_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_svt_sao_parse_safety.py')
    if not script.is_file():
        fail('missing SVT SAO parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_svt_scenecut_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_svt_scenecut_parse_safety.py')
    if not script.is_file():
        fail('missing SVT scenecut parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_svt_search_height_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_svt_search_height_parse_safety.py')
    if not script.is_file():
        fail('missing SVT search-height parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_svt_search_width_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_svt_search_width_parse_safety.py')
    if not script.is_file():
        fail('missing SVT search-width parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_svt_speed_control_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_svt_speed_control_parse_safety.py')
    if not script.is_file():
        fail('missing SVT speed-control parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_svt_vbv_bufsize_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_svt_vbv_bufsize_parse_safety.py')
    if not script.is_file():
        fail('missing SVT vbv-bufsize parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_svt_vbv_init_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_svt_vbv_init_parse_safety.py')
    if not script.is_file():
        fail('missing SVT vbv-init parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_svt_vbv_maxrate_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_svt_vbv_maxrate_parse_safety.py')
    if not script.is_file():
        fail('missing SVT vbv-maxrate parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_svt_vui_timing_info_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_svt_vui_timing_info_parse_safety.py')
    if not script.is_file():
        fail('missing SVT vui-timing-info parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_svt_hme_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_svt_hme_parse_safety.py')
    if not script.is_file():
        fail('missing SVT hme parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_svt_interlace_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_svt_interlace_parse_safety.py')
    if not script.is_file():
        fail('missing SVT interlace parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_svt_open_gop_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_svt_open_gop_parse_safety.py')
    if not script.is_file():
        fail('missing SVT open-gop parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_svt_pools_exclude_both_sockets_guard(repo_root):
    script = repo_root / Path('.github/scripts/check_svt_pools_exclude_both_sockets_guard.py')
    if not script.is_file():
        fail('missing SVT pools exclude-both-sockets checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_encoder_rpu_replace_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_encoder_rpu_replace_safety.py')
    if not script.is_file():
        fail('missing encoder rpu replace safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_copy_user_sei_staging(repo_root):
    script = repo_root / Path('.github/scripts/check_copy_user_sei_staging.py')
    if not script.is_file():
        fail('missing copy user sei staging checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_dup_side_data_staging(repo_root):
    script = repo_root / Path('.github/scripts/check_dup_side_data_staging.py')
    if not script.is_file():
        fail('missing dup side data staging checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_read_user_sei_staging(repo_root):
    script = repo_root / Path('.github/scripts/check_read_user_sei_staging.py')
    if not script.is_file():
        fail('missing read user sei staging checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_copy_picture_staging(repo_root):
    script = repo_root / Path('.github/scripts/check_copy_picture_staging.py')
    if not script.is_file():
        fail('missing copy picture staging checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_dup_create_alloc_guards(repo_root):
    script = repo_root / Path('.github/scripts/check_dup_create_alloc_guards.py')
    if not script.is_file():
        fail('missing dup create alloc guards checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_encode_quant_offsets_staging(repo_root):
    script = repo_root / Path('.github/scripts/check_encode_quant_offsets_staging.py')
    if not script.is_file():
        fail('missing encode quant offsets staging checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_read_user_sei_cleanup(repo_root):
    script = repo_root / Path('.github/scripts/check_read_user_sei_cleanup.py')
    if not script.is_file():
        fail('missing read user sei cleanup checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_log_progress_file_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_log_progress_file_parse_safety.py')
    if not script.is_file():
        fail('missing log progress file parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_negated_bool_alias_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_negated_bool_alias_parse_safety.py')
    if not script.is_file():
        fail('missing negated bool alias parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_rd_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_rd_parse_safety.py')
    if not script.is_file():
        fail('missing rd parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_limit_refs_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_limit_refs_parse_safety.py')
    if not script.is_file():
        fail('missing limit-refs parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_dup_threshold_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_dup_threshold_parse_safety.py')
    if not script.is_file():
        fail('missing dup-threshold parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_vmaf_flush_cleanup(repo_root):
    script = repo_root / Path('.github/scripts/check_vmaf_flush_cleanup.py')
    if not script.is_file():
        fail('missing VMAF flush cleanup checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_avs_buffer_replace_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_avs_buffer_replace_safety.py')
    if not script.is_file():
        fail('missing avs buffer replace safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_vpy_buffer_replace_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_vpy_buffer_replace_safety.py')
    if not script.is_file():
        fail('missing vpy buffer replace safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_zimg_token_parse_usage(repo_root):
    script = repo_root / Path('.github/scripts/check_zimg_token_parse_usage.py')
    if not script.is_file():
        fail('missing zimg token parse usage checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_zimg_init_rollback(repo_root):
    script = repo_root / Path('.github/scripts/check_zimg_init_rollback.py')
    if not script.is_file():
        fail('missing zimg init rollback checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_dynamic_hdr10_legacy_patterns(repo_root):
    script = repo_root / Path('.github/scripts/check_dynamic_hdr10_legacy_patterns.py')
    if not script.is_file():
        fail('missing dynamic hdr10 legacy patterns checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_sei_unsigned_token_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_sei_unsigned_token_safety.py')
    if not script.is_file():
        fail('missing sei unsigned token safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_video_signal_type_preset_parse(repo_root):
    script = repo_root / Path('.github/scripts/check_video_signal_type_preset_parse.py')
    if not script.is_file():
        fail('missing video signal type preset parse checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_sei_mastering_display_parse(repo_root):
    script = repo_root / Path('.github/scripts/check_sei_mastering_display_parse.py')
    if not script.is_file():
        fail('missing sei mastering display parse checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_sao_param_staging(repo_root):
    script = repo_root / Path('.github/scripts/check_sao_param_staging.py')
    if not script.is_file():
        fail('missing sao param staging checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_zone_parse_replace_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_zone_parse_replace_safety.py')
    if not script.is_file():
        fail('missing zone parse replace safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_cpu_name_strdup_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_cpu_name_strdup_safety.py')
    if not script.is_file():
        fail('missing cpu name strdup safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_x265_fclose_macro_state(repo_root):
    script = repo_root / Path('.github/scripts/check_x265_fclose_macro_state.py')
    if not script.is_file():
        fail('missing x265 fclose macro state checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_hme_param_sscanf_usage(repo_root):
    script = repo_root / Path('.github/scripts/check_hme_param_sscanf_usage.py')
    if not script.is_file():
        fail('missing hme param sscanf usage checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_masking_strength_scan_usage(repo_root):
    script = repo_root / Path('.github/scripts/check_masking_strength_scan_usage.py')
    if not script.is_file():
        fail('missing masking strength scan usage checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_reviewed_string_copy_usage(repo_root):
    script = repo_root / Path('.github/scripts/check_reviewed_string_copy_usage.py')
    if not script.is_file():
        fail('missing reviewed string copy usage checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_analysis_open_state(repo_root):
    script = repo_root / Path('.github/scripts/check_analysis_open_state.py')
    if not script.is_file():
        fail('missing analysis open checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_analysis_load_open_state(repo_root):
    script = repo_root / Path('.github/scripts/check_analysis_load_open_state.py')
    if not script.is_file():
        fail('missing analysis load open checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_cli_config_open_state(repo_root):
    script = repo_root / Path('.github/scripts/check_cli_config_open_state.py')
    if not script.is_file():
        fail('missing cli config open checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_cli_help_exit_cleanup(repo_root):
    script = repo_root / Path('.github/scripts/check_cli_help_exit_cleanup.py')
    if not script.is_file():
        fail('missing CLI help exit cleanup checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_abr_ladder_open_state(repo_root):
    script = repo_root / Path('.github/scripts/check_abr_ladder_open_state.py')
    if not script.is_file():
        fail('missing abr ladder open checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_abr_help_exit_precedence(repo_root):
    script = repo_root / Path('.github/scripts/check_abr_help_exit_precedence.py')
    if not script.is_file():
        fail('missing abr/help precedence checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_lambda_file_open_state(repo_root):
    script = repo_root / Path('.github/scripts/check_lambda_file_open_state.py')
    if not script.is_file():
        fail('missing lambda file open checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_lambda_file_close_state(repo_root):
    script = repo_root / Path('.github/scripts/check_lambda_file_close_state.py')
    if not script.is_file():
        fail('missing lambda file close checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_vmaf_input_open_state(repo_root):
    script = repo_root / Path('.github/scripts/check_vmaf_input_open_state.py')
    if not script.is_file():
        fail('missing vmaf input open checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_nalu_file_open_state(repo_root):
    script = repo_root / Path('.github/scripts/check_nalu_file_open_state.py')
    if not script.is_file():
        fail('missing nalu file open checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_tonemap_file_open_state(repo_root):
    script = repo_root / Path('.github/scripts/check_tonemap_file_open_state.py')
    if not script.is_file():
        fail('missing tonemap file open checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_scalinglist_open_state(repo_root):
    script = repo_root / Path('.github/scripts/check_scalinglist_open_state.py')
    if not script.is_file():
        fail('missing scalinglist open checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_gop_open_state(repo_root):
    script = repo_root / Path('.github/scripts/check_gop_open_state.py')
    if not script.is_file():
        fail('missing gop open checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_film_grain_open_state(repo_root):
    script = repo_root / Path('.github/scripts/check_film_grain_open_state.py')
    if not script.is_file():
        fail('missing film grain open checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_film_grain_close_state(repo_root):
    script = repo_root / Path('.github/scripts/check_film_grain_close_state.py')
    if not script.is_file():
        fail('missing film grain close checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_gop_cleanup_close_state(repo_root):
    script = repo_root / Path('.github/scripts/check_gop_cleanup_close_state.py')
    if not script.is_file():
        fail('missing gop cleanup close checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_mp4_preflight_close_state(repo_root):
    script = repo_root / Path('.github/scripts/check_mp4_preflight_close_state.py')
    if not script.is_file():
        fail('missing mp4 preflight close checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_gop_early_close_state(repo_root):
    script = repo_root / Path('.github/scripts/check_gop_early_close_state.py')
    if not script.is_file():
        fail('missing gop early close checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_gop_intermediate_close_state(repo_root):
    script = repo_root / Path('.github/scripts/check_gop_intermediate_close_state.py')
    if not script.is_file():
        fail('missing gop intermediate close checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_ratecontrol_destroy_close_state(repo_root):
    script = repo_root / Path('.github/scripts/check_ratecontrol_destroy_close_state.py')
    if not script.is_file():
        fail('missing ratecontrol destroy close checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_ratecontrol_write_fail_state(repo_root):
    script = repo_root / Path('.github/scripts/check_ratecontrol_write_fail_state.py')
    if not script.is_file():
        fail('missing ratecontrol write fail-state checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_ratecontrol_cutree_read_fail_state(repo_root):
    script = repo_root / Path('.github/scripts/check_ratecontrol_cutree_read_fail_state.py')
    if not script.is_file():
        fail('missing ratecontrol cutree read fail-state checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_mp4_handle_close_state(repo_root):
    script = repo_root / Path('.github/scripts/check_mp4_handle_close_state.py')
    if not script.is_file():
        fail('missing mp4 handle close checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_mp4_header_sei_alloc_guard(repo_root):
    script = repo_root / Path('.github/scripts/check_mp4_header_sei_alloc_guard.py')
    if not script.is_file():
        fail('missing mp4 header SEI allocation checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_ratecontrol_stats_open_state(repo_root):
    script = repo_root / Path('.github/scripts/check_ratecontrol_stats_open_state.py')
    if not script.is_file():
        fail('missing ratecontrol stats open checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_raw_close_state(repo_root):
    script = repo_root / Path('.github/scripts/check_raw_close_state.py')
    if not script.is_file():
        fail('missing raw close checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_raw_open_cleanup_state(repo_root):
    script = repo_root / Path('.github/scripts/check_raw_open_cleanup_state.py')
    if not script.is_file():
        fail('missing raw open cleanup checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_x265_check_macro_open_state(repo_root):
    script = repo_root / Path('.github/scripts/check_x265_check_macro_open_state.py')
    if not script.is_file():
        fail('missing x265 check macro open checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_x265_check_macro_close_state(repo_root):
    script = repo_root / Path('.github/scripts/check_x265_check_macro_close_state.py')
    if not script.is_file():
        fail('missing x265 check macro close checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_vmaf_encoder_log_close_state(repo_root):
    script = repo_root / Path('.github/scripts/check_vmaf_encoder_log_close_state.py')
    if not script.is_file():
        fail('missing vmaf encoder log close checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_scalinglist_close_state(repo_root):
    script = repo_root / Path('.github/scripts/check_scalinglist_close_state.py')
    if not script.is_file():
        fail('missing scalinglist close checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_y4m_input_close_state(repo_root):
    script = repo_root / Path('.github/scripts/check_y4m_input_close_state.py')
    if not script.is_file():
        fail('missing y4m input close checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_yuv_input_close_state(repo_root):
    script = repo_root / Path('.github/scripts/check_yuv_input_close_state.py')
    if not script.is_file():
        fail('missing yuv input close checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_reconplay_pclose_state(repo_root):
    script = repo_root / Path('.github/scripts/check_reconplay_pclose_state.py')
    if not script.is_file():
        fail('missing reconplay pclose checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_multiview_parse_close_state(repo_root):
    script = repo_root / Path('.github/scripts/check_multiview_parse_close_state.py')
    if not script.is_file():
        fail('missing multiview parse close checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_multiview_config_parse_usage(repo_root):
    script = repo_root / Path('.github/scripts/check_multiview_config_parse_usage.py')
    if not script.is_file():
        fail('missing multiview config parse usage checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_scenecut_aware_qp_config_parse_usage(repo_root):
    script = repo_root / Path('.github/scripts/check_scenecut_aware_qp_config_parse_usage.py')
    if not script.is_file():
        fail('missing scenecut-aware qp config parse usage checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_scenecut_aware_qp_parse_safety(repo_root):
    script = repo_root / Path('.github/scripts/check_scenecut_aware_qp_parse_safety.py')
    if not script.is_file():
        fail('missing scenecut-aware qp parse safety checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_abr_parse_cleanup_state(repo_root):
    script = repo_root / Path('.github/scripts/check_abr_parse_cleanup_state.py')
    if not script.is_file():
        fail('missing abr parse cleanup checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_scenecut_qp_cleanup_state(repo_root):
    script = repo_root / Path('.github/scripts/check_scenecut_qp_cleanup_state.py')
    if not script.is_file():
        fail('missing scenecut qp cleanup checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_x265_main_cleanup_state(repo_root):
    script = repo_root / Path('.github/scripts/check_x265_main_cleanup_state.py')
    if not script.is_file():
        fail('missing x265 main cleanup checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_abr_config_parse_usage(repo_root):
    script = repo_root / Path('.github/scripts/check_abr_config_parse_usage.py')
    if not script.is_file():
        fail('missing abr config parse usage checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_abr_init_result_propagation(repo_root):
    script = repo_root / Path('.github/scripts/check_abr_init_result_propagation.py')
    if not script.is_file():
        fail('missing abr init result propagation checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_abr_init_helper_cleanup(repo_root):
    script = repo_root / Path('.github/scripts/check_abr_init_helper_cleanup.py')
    if not script.is_file():
        fail('missing abr init helper cleanup checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_abr_init_reader_rollback(repo_root):
    script = repo_root / Path('.github/scripts/check_abr_init_reader_rollback.py')
    if not script.is_file():
        fail('missing abr init reader rollback checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_abr_init_api_null_guard(repo_root):
    script = repo_root / Path('.github/scripts/check_abr_init_api_null_guard.py')
    if not script.is_file():
        fail('missing abr init api null checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_abr_init_output_null_guard(repo_root):
    script = repo_root / Path('.github/scripts/check_abr_init_output_null_guard.py')
    if not script.is_file():
        fail('missing abr init output null checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_abr_init_filter_null_guard(repo_root):
    script = repo_root / Path('.github/scripts/check_abr_init_filter_null_guard.py')
    if not script.is_file():
        fail('missing abr init filter null checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_abr_init_reader_alloc_guard(repo_root):
    script = repo_root / Path('.github/scripts/check_abr_init_reader_alloc_guard.py')
    if not script.is_file():
        fail('missing abr init reader alloc checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_abr_start_threads_failure_propagation(repo_root):
    script = repo_root / Path('.github/scripts/check_abr_start_threads_failure_propagation.py')
    if not script.is_file():
        fail('missing abr startThreads failure propagation checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_abr_primary_param_guards(repo_root):
    script = repo_root / Path('.github/scripts/check_abr_primary_param_guards.py')
    if not script.is_file():
        fail('missing abr primary param guards checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_abr_ctor_top_guards(repo_root):
    script = repo_root / Path('.github/scripts/check_abr_ctor_top_guards.py')
    if not script.is_file():
        fail('missing abr ctor top guards checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_abr_queue_picture_guards(repo_root):
    script = repo_root / Path('.github/scripts/check_abr_queue_picture_guards.py')
    if not script.is_file():
        fail('missing abr queue picture guards checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_abr_thread_queue_state_guards(repo_root):
    script = repo_root / Path('.github/scripts/check_abr_thread_queue_state_guards.py')
    if not script.is_file():
        fail('missing abr thread queue state guards checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_abr_counter_state_guards(repo_root):
    script = repo_root / Path('.github/scripts/check_abr_counter_state_guards.py')
    if not script.is_file():
        fail('missing abr counter state guards checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_abr_picture_state_guards(repo_root):
    script = repo_root / Path('.github/scripts/check_abr_picture_state_guards.py')
    if not script.is_file():
        fail('missing abr picture state guards checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_abr_thread_multiview_field_guard(repo_root):
    script = repo_root / Path('.github/scripts/check_abr_thread_multiview_field_guard.py')
    if not script.is_file():
        fail('missing abr thread multiview field checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_abr_thread_multiview_input_guard(repo_root):
    script = repo_root / Path('.github/scripts/check_abr_thread_multiview_input_guard.py')
    if not script.is_file():
        fail('missing abr thread multiview input checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_abr_thread_reconplay_alloc_guard(repo_root):
    script = repo_root / Path('.github/scripts/check_abr_thread_reconplay_alloc_guard.py')
    if not script.is_file():
        fail('missing abr thread reconplay alloc checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_abr_thread_pic_in_reset_guard(repo_root):
    script = repo_root / Path('.github/scripts/check_abr_thread_pic_in_reset_guard.py')
    if not script.is_file():
        fail('missing abr thread pic_in reset checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_abr_thread_dolby_rpu_eof_guard(repo_root):
    script = repo_root / Path('.github/scripts/check_abr_thread_dolby_rpu_eof_guard.py')
    if not script.is_file():
        fail('missing abr thread dolby rpu eof checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_abr_thread_output_null_guard(repo_root):
    script = repo_root / Path('.github/scripts/check_abr_thread_output_null_guard.py')
    if not script.is_file():
        fail('missing abr thread output null checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_abr_thread_fail_output_guard(repo_root):
    script = repo_root / Path('.github/scripts/check_abr_thread_fail_output_guard.py')
    if not script.is_file():
        fail('missing abr thread fail output checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_abr_thread_fail_encoder_guard(repo_root):
    script = repo_root / Path('.github/scripts/check_abr_thread_fail_encoder_guard.py')
    if not script.is_file():
        fail('missing abr thread fail encoder checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_abr_thread_output_picture_guard(repo_root):
    script = repo_root / Path('.github/scripts/check_abr_thread_output_picture_guard.py')
    if not script.is_file():
        fail('missing abr thread output picture checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_abr_thread_layered_recon_guard(repo_root):
    script = repo_root / Path('.github/scripts/check_abr_thread_layered_recon_guard.py')
    if not script.is_file():
        fail('missing abr thread layered recon checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_abr_thread_api_null_guard(repo_root):
    script = repo_root / Path('.github/scripts/check_abr_thread_api_null_guard.py')
    if not script.is_file():
        fail('missing abr thread api null checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_abr_thread_dither_input_guard(repo_root):
    script = repo_root / Path('.github/scripts/check_abr_thread_dither_input_guard.py')
    if not script.is_file():
        fail('missing abr thread dither input checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_abr_thread_field_buffer_guard(repo_root):
    script = repo_root / Path('.github/scripts/check_abr_thread_field_buffer_guard.py')
    if not script.is_file():
        fail('missing abr thread field buffer checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_abr_thread_field_buffer_state_guard(repo_root):
    script = repo_root / Path('.github/scripts/check_abr_thread_field_buffer_state_guard.py')
    if not script.is_file():
        fail('missing abr thread field buffer state checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_abr_thread_field_view_usage(repo_root):
    script = repo_root / Path('.github/scripts/check_abr_thread_field_view_usage.py')
    if not script.is_file():
        fail('missing abr thread field view usage checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_abr_thread_field_layout_guard(repo_root):
    script = repo_root / Path('.github/scripts/check_abr_thread_field_layout_guard.py')
    if not script.is_file():
        fail('missing abr thread field layout checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_abr_thread_field_plane_guard(repo_root):
    script = repo_root / Path('.github/scripts/check_abr_thread_field_plane_guard.py')
    if not script.is_file():
        fail('missing abr thread field plane checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_abr_thread_field_reuse_guard(repo_root):
    script = repo_root / Path('.github/scripts/check_abr_thread_field_reuse_guard.py')
    if not script.is_file():
        fail('missing abr thread field reuse checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_abr_thread_pts_queue_alloc_guard(repo_root):
    script = repo_root / Path('.github/scripts/check_abr_thread_pts_queue_alloc_guard.py')
    if not script.is_file():
        fail('missing abr thread pts queue alloc checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_abr_thread_recon_state_guard(repo_root):
    script = repo_root / Path('.github/scripts/check_abr_thread_recon_state_guard.py')
    if not script.is_file():
        fail('missing abr thread recon state checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_abr_thread_recon_write_guard(repo_root):
    script = repo_root / Path('.github/scripts/check_abr_thread_recon_write_guard.py')
    if not script.is_file():
        fail('missing abr thread recon write checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_abr_copyinfo_inter_arrays_guard(repo_root):
    script = repo_root / Path('.github/scripts/check_abr_copyinfo_inter_arrays_guard.py')
    if not script.is_file():
        fail('missing abr copyinfo inter arrays checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_abr_copyinfo_intra_arrays_guard(repo_root):
    script = repo_root / Path('.github/scripts/check_abr_copyinfo_intra_arrays_guard.py')
    if not script.is_file():
        fail('missing abr copyinfo intra arrays checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_abr_copyinfo_src_guard(repo_root):
    script = repo_root / Path('.github/scripts/check_abr_copyinfo_src_guard.py')
    if not script.is_file():
        fail('missing abr copyinfo src checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_abr_copyinfo_analysis_buffer_guard(repo_root):
    script = repo_root / Path('.github/scripts/check_abr_copyinfo_analysis_buffer_guard.py')
    if not script.is_file():
        fail('missing abr copyinfo analysis buffer checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_abr_analysis_slot_wait_guard(repo_root):
    script = repo_root / Path('.github/scripts/check_abr_analysis_slot_wait_guard.py')
    if not script.is_file():
        fail('missing abr analysis slot wait checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_abr_copyinfo_vbv_lookahead_guard(repo_root):
    script = repo_root / Path('.github/scripts/check_abr_copyinfo_vbv_lookahead_guard.py')
    if not script.is_file():
        fail('missing abr copyinfo vbv lookahead checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_abr_allocbuffers_top_guards(repo_root):
    script = repo_root / Path('.github/scripts/check_abr_allocbuffers_top_guards.py')
    if not script.is_file():
        fail('missing abr allocbuffers top guards checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_abr_allocbuffers_partial_cleanup(repo_root):
    script = repo_root / Path('.github/scripts/check_abr_allocbuffers_partial_cleanup.py')
    if not script.is_file():
        fail('missing abr allocbuffers partial cleanup checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_abr_allocbuffers_queue_guards(repo_root):
    script = repo_root / Path('.github/scripts/check_abr_allocbuffers_queue_guards.py')
    if not script.is_file():
        fail('missing abr allocbuffers queue guards checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_abr_setreuselevel_ref_guard(repo_root):
    script = repo_root / Path('.github/scripts/check_abr_setreuselevel_ref_guard.py')
    if not script.is_file():
        fail('missing abr setreuselevel ref checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_abr_allocbuffers_analysisread_guard(repo_root):
    script = repo_root / Path('.github/scripts/check_abr_allocbuffers_analysisread_guard.py')
    if not script.is_file():
        fail('missing abr allocbuffers analysisread checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_abr_allocbuffers_analysiswrite_guard(repo_root):
    script = repo_root / Path('.github/scripts/check_abr_allocbuffers_analysiswrite_guard.py')
    if not script.is_file():
        fail('missing abr allocbuffers analysiswrite checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_abr_allocbuffers_picidx_guard(repo_root):
    script = repo_root / Path('.github/scripts/check_abr_allocbuffers_picidx_guard.py')
    if not script.is_file():
        fail('missing abr allocbuffers picidx checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_abr_allocbuffers_readflag_guard(repo_root):
    script = repo_root / Path('.github/scripts/check_abr_allocbuffers_readflag_guard.py')
    if not script.is_file():
        fail('missing abr allocbuffers readflag checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_abr_readpicture_srcpic_guard(repo_root):
    script = repo_root / Path('.github/scripts/check_abr_readpicture_srcpic_guard.py')
    if not script.is_file():
        fail('missing abr readpicture srcpic checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_abr_readpicture_analysis_guard(repo_root):
    script = repo_root / Path('.github/scripts/check_abr_readpicture_analysis_guard.py')
    if not script.is_file():
        fail('missing abr readpicture analysis checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_abr_thread_readpicture_failure_guard(repo_root):
    script = repo_root / Path('.github/scripts/check_abr_thread_readpicture_failure_guard.py')
    if not script.is_file():
        fail('missing abr thread readPicture failure checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_abr_readpicture_analysis_queue_guard(repo_root):
    script = repo_root / Path('.github/scripts/check_abr_readpicture_analysis_queue_guard.py')
    if not script.is_file():
        fail('missing abr readpicture analysis queue checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_abr_scaler_videodesc_alloc_guard(repo_root):
    script = repo_root / Path('.github/scripts/check_abr_scaler_videodesc_alloc_guard.py')
    if not script.is_file():
        fail('missing abr scaler videodesc alloc checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_abr_scaler_videodesc_ownership(repo_root):
    script = repo_root / Path('.github/scripts/check_abr_scaler_videodesc_ownership.py')
    if not script.is_file():
        fail('missing abr scaler videodesc ownership checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_abr_scaler_init_failure_handling(repo_root):
    script = repo_root / Path('.github/scripts/check_abr_scaler_init_failure_handling.py')
    if not script.is_file():
        fail('missing abr scaler init failure handling checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_abr_thread_analysis_read_guard(repo_root):
    script = repo_root / Path('.github/scripts/check_abr_thread_analysis_read_guard.py')
    if not script.is_file():
        fail('missing abr thread analysis read checker', script)
    run_guard(repo_root, sys.executable, str(script), str(repo_root))


def validate_dependency_update_anchors(repo_root):
    action = repo_root / WINDOWS_DEPS_ACTION
    text = read_text(action)
    for anchor in UPDATE_DEPS_ANCHORS:
        if f'{anchor}:' not in text:
            fail(f'missing dependency update anchor: {anchor}:', action)
    print('Dependency update anchors validated')


def validate_windows_deps_checkout_scope(repo_root):
    action_path = repo_root / WINDOWS_DEPS_ACTION
    parsed = load_yaml(repo_root, WINDOWS_DEPS_ACTION)
    inputs = parsed.get('inputs')
    if not isinstance(inputs, dict):
        fail('setup-windows-deps action must define inputs', action_path)
    for input_name, default_value in (
        ('use-ffmpeg', 'true'),
        ('use-obuparse', 'true'),
        ('use-lsmash', 'true'),
    ):
        input_data = inputs.get(input_name)
        if not isinstance(input_data, dict):
            fail(f'setup-windows-deps action must define input: {input_name}', action_path)
        if input_data.get('default') != default_value:
            fail(f'setup-windows-deps input {input_name} must default to {default_value}', action_path)

    runs = parsed.get('runs')
    if not isinstance(runs, dict):
        fail('setup-windows-deps action must define runs', action_path)
    steps = runs.get('steps')
    if not isinstance(steps, list):
        fail('setup-windows-deps action must define runs.steps', action_path)

    def step_by_name(name):
        for step in steps:
            if isinstance(step, dict) and step.get('name') == name:
                return step
        fail(f'setup-windows-deps missing step: {name}', action_path)

    for name in ('Checkout FFmpeg', 'Checkout mimalloc', 'Checkout Obuparse', 'Checkout L-SMASH', 'Checkout GOP muxer'):
        step = step_by_name(name)
        with_values = step.get('with')
        if not isinstance(with_values, dict):
            fail(f'{name} must declare with inputs', action_path)
        if with_values.get('fetch-depth') != 1:
            fail(f'{name} must use fetch-depth: 1', action_path)

    obuparse_step = step_by_name('Checkout Obuparse')
    obuparse_with = obuparse_step.get('with')
    if obuparse_with.get('sparse-checkout') != 'Makefile\nobuparse.c\nobuparse.h\n':
        fail('Checkout Obuparse must sparse-checkout only the static library build inputs', action_path)
    if obuparse_with.get('sparse-checkout-cone-mode') is not False:
        fail('Checkout Obuparse must disable sparse-checkout cone mode for file-list checkout', action_path)

    lsmash_step = step_by_name('Checkout L-SMASH')
    lsmash_with = lsmash_step.get('with')
    expected_lsmash_sparse = 'Makefile\nconfigure\nlsmash.h\nliblsmash.v\ncli\ncodecs\ncommon\ncore\nimporter\n'
    if lsmash_with.get('sparse-checkout') != expected_lsmash_sparse:
        fail('Checkout L-SMASH must sparse-checkout only configure and static-library source inputs', action_path)
    if lsmash_with.get('sparse-checkout-cone-mode') is not False:
        fail('Checkout L-SMASH must disable sparse-checkout cone mode for mixed file/directory checkout', action_path)

    gop_step = step_by_name('Checkout GOP muxer')
    gop_with = gop_step.get('with')
    if gop_with.get('sparse-checkout') != 'gop_muxer.cpp':
        fail('Checkout GOP muxer must sparse-checkout only gop_muxer.cpp', action_path)
    if gop_with.get('sparse-checkout-cone-mode') is not False:
        fail('Checkout GOP muxer must disable sparse-checkout cone mode for single-file checkout', action_path)

    setup_step = step_by_name('Setup MSYS2')
    setup_with = setup_step.get('with')
    if not isinstance(setup_with, dict):
        fail('Setup MSYS2 must declare with inputs', action_path)
    install_packages = setup_with.get('install')
    if not isinstance(install_packages, str):
        fail('Setup MSYS2 install package list missing', action_path)
    if 'mingw-w64-clang-x86_64-python' not in install_packages.split():
        fail('Setup Windows dependencies must install CLANG64 Python for C++20 guard helpers', action_path)
    if 'p7zip' in install_packages.split():
        fail('Setup Windows dependencies must not install p7zip globally; package steps install it on demand', action_path)
    print('Windows dependency checkout scope validated')


def validate_pgo_consume_helper(repo_root):
    build = repo_root / BUILD_WORKFLOW
    blocks = [block for path, line, block in collect_run_blocks(build) if 'check_pgo_consume_commands()' in block]
    if len(blocks) != 1:
        fail(f'expected exactly one PGO consume helper run block, found {len(blocks)}', build)
    active_lines = shell_active_lines(blocks[0])
    required = 'check_cxx20_commands_pgo_consume "$build_dir" "$pgo_flag" --min-cpp-commands="$min_cpp_commands"'
    if required not in active_lines:
        fail(f'PGO consume helper must actively run: {required}', build)
    print('PGO consume helper guard validated')


def validate_raw_smoke(repo_root):
    build = repo_root / BUILD_WORKFLOW
    active_lines = runtime_smoke_active_lines(repo_root, RUNTIME_SMOKE_SUITE, 'smoke_raw')
    if 'make_runtime_y4m smoke_raw.y4m 160 90 24 12 yuv420p' not in active_lines:
        fail('RAW smoke must generate 12-frame yuv420p input', build)

    require_x265_command(active_lines, build, 'RAW smoke', 'smoke_raw', 'build/all/x265.exe', (
        ('--input', 'smoke_raw.y4m'),
        ('--input-res', '160x90'),
        ('--fps', '24'),
        ('--frames', '12'),
        ('--output', 'smoke_raw.hevc'),
    ))
    for required, message in {
        'test -s smoke_raw.hevc': 'RAW smoke must require non-empty HEVC output',
        'ffprobe -v error -show_entries stream=codec_name,codec_type,width,height -select_streams v:0 -of default=noprint_wrappers=1 smoke_raw.hevc > smoke_raw_probe.txt': 'RAW smoke must capture HEVC probe output',
        'grep -q "codec_name=hevc" smoke_raw_probe.txt': 'RAW smoke must require HEVC codec',
        'grep -q "codec_type=video" smoke_raw_probe.txt': 'RAW smoke must require video stream',
        'grep -q "width=160" smoke_raw_probe.txt': 'RAW smoke must require width 160',
        'grep -q "height=90" smoke_raw_probe.txt': 'RAW smoke must require height 90',
    }.items():
        if required not in active_lines:
            fail(message, build)
    print('RAW smoke guard validated')


def validate_threaded_me_smoke(repo_root):
    build = repo_root / BUILD_WORKFLOW
    active_lines = runtime_smoke_active_lines(repo_root, RUNTIME_SMOKE_SUITE, 'smoke_threaded_me')
    generator_line = 'make_runtime_y4m smoke_threaded_me.y4m 160 90 24 16 yuv420p'
    if generator_line not in active_lines:
        fail('Threaded ME smoke must generate 16-frame yuv420p input', build)

    command, args = piped_x265_command(active_lines, build, 'Threaded ME smoke', 'smoke_threaded_me')
    if not args or args[0] != 'build/all/x265.exe':
        actual = args[0] if args else '<empty>'
        fail(f'Threaded ME smoke must run build/all/x265.exe, got {actual}', build)
    for expected in TME_SMOKE_FLAGS:
        if expected not in args:
            fail(f'missing Threaded ME smoke argument: {expected}', build)
    for option, expected in TME_SMOKE_OPTIONS:
        option_value(args, option, expected, build, 'Threaded ME smoke')

    active_required = {
        "grep -Fq 'frame threads / pool features       : 1 / threaded-me' smoke_threaded_me_log.txt": 'Threaded ME smoke must require enabled threaded-me log',
        "! grep -Fq 'disabling --threaded-me' smoke_threaded_me_log.txt": 'Threaded ME smoke must reject disabled threaded-me log',
        "grep -q 'nb_read_frames=16' smoke_threaded_me_count.txt": 'Threaded ME smoke must require 16 decoded frames',
    }
    for required, message in active_required.items():
        if required not in active_lines:
            fail(message, build)
    if 'tee smoke_threaded_me_log.txt' not in command:
        fail('Threaded ME smoke must capture x265 log to smoke_threaded_me_log.txt', build)
    ffprobe_lines = [line for line in active_lines if 'ffprobe ' in line and 'smoke_threaded_me.hevc > smoke_threaded_me_count.txt' in line]
    if len(ffprobe_lines) != 1 or ' -count_frames ' not in f' {ffprobe_lines[0]} ':
        fail('Threaded ME smoke must count frames from smoke_threaded_me.hevc', build)
    print('Threaded ME smoke guard validated')


def validate_threaded_me_stress_smoke(repo_root):
    build = repo_root / BUILD_WORKFLOW
    active_lines = runtime_smoke_active_lines(repo_root, RUNTIME_SMOKE_SUITE, 'smoke_threaded_me_stress')
    generator_line = 'make_runtime_y4m smoke_threaded_me_stress.y4m 160 90 24 2 yuv420p'
    if generator_line not in active_lines:
        fail('Threaded ME stress smoke must generate 2-frame yuv420p input', build)

    required_active = {
        'for iteration in $(seq 1 12); do': 'Threaded ME stress smoke must run a 12-iteration loop',
        'output="smoke_threaded_me_stress_${iteration}.hevc"': 'Threaded ME stress smoke must derive per-iteration output path',
        'log="smoke_threaded_me_stress_${iteration}.log"': 'Threaded ME stress smoke must derive per-iteration log path',
        'count="smoke_threaded_me_stress_${iteration}_count.txt"': 'Threaded ME stress smoke must derive per-iteration frame-count path',
        'test -s "$output"': 'Threaded ME stress smoke must require non-empty per-iteration HEVC output',
        'grep -Fq \'frame threads / pool features       : 1 / threaded-me\' "$log"': 'Threaded ME stress smoke must require enabled threaded-me log each iteration',
        '! grep -Fq \'disabling --threaded-me\' "$log"': 'Threaded ME stress smoke must reject disabled threaded-me log each iteration',
        'grep -q \'nb_read_frames=2\' "$count"': 'Threaded ME stress smoke must require 2 decoded frames each iteration',
        'done': 'Threaded ME stress smoke must close the iteration loop',
    }
    for required, message in required_active.items():
        if required not in active_lines:
            fail(message, build)

    command, args = piped_x265_command(active_lines, build, 'Threaded ME stress smoke', 'smoke_threaded_me_stress.y4m')
    if not args or args[0] != 'build/all/x265.exe':
        actual = args[0] if args else '<empty>'
        fail(f'Threaded ME stress smoke must run build/all/x265.exe, got {actual}', build)
    for expected in TME_STRESS_FLAGS:
        if expected not in args:
            fail(f'missing Threaded ME stress smoke argument: {expected}', build)
    for option, expected in TME_STRESS_OPTIONS:
        option_value(args, option, expected, build, 'Threaded ME stress smoke')
    if '--output' not in args or args[args.index('--output') + 1] != '$output':
        fail('Threaded ME stress smoke --output must target $output', build)
    if 'tee "$log"' not in command:
        fail('Threaded ME stress smoke must capture x265 log to $log', build)

    ffprobe_lines = [line for line in active_lines if 'ffprobe ' in line and '"$output" > "$count"' in line]
    if len(ffprobe_lines) != 1 or ' -count_frames ' not in f' {ffprobe_lines[0]} ':
        fail('Threaded ME stress smoke must count frames from $output into $count', build)
    print('Threaded ME stress smoke guard validated')


def validate_mkv_smoke(repo_root):
    build = repo_root / BUILD_WORKFLOW
    active_lines = runtime_smoke_active_lines(repo_root, RUNTIME_SMOKE_SUITE, 'smoke_mkv')
    if 'make_runtime_y4m smoke_mkv.y4m 160 90 24 12 yuv420p' not in active_lines:
        fail('MKV smoke must generate 12-frame yuv420p input', build)

    require_x265_command(active_lines, build, 'MKV smoke', 'smoke_mkv', 'build/all/x265.exe', MKV_SMOKE_OPTIONS)

    active_required = {
        'test -s smoke_mkv.mkv': 'MKV smoke must require non-empty MKV output',
        'ffprobe -v error -show_entries format=format_name,duration -of default=noprint_wrappers=1 smoke_mkv.mkv > smoke_mkv_format.txt': 'MKV smoke must capture format probe output',
        'ffprobe -v error -show_entries stream=codec_name,codec_type,width,height -select_streams v:0 -of default=noprint_wrappers=1 smoke_mkv.mkv > smoke_mkv_stream.txt': 'MKV smoke must capture video stream probe output',
        'ffprobe -v error -count_frames -select_streams v:0 -show_entries stream=nb_read_frames -of default=noprint_wrappers=1 smoke_mkv.mkv > smoke_mkv_count.txt': 'MKV smoke must count decoded frames',
        'grep -q "format_name=matroska,webm" smoke_mkv_format.txt': 'MKV smoke must require Matroska format',
        'grep -q "codec_name=hevc" smoke_mkv_stream.txt': 'MKV smoke must require HEVC codec',
        'grep -q "codec_type=video" smoke_mkv_stream.txt': 'MKV smoke must require video stream',
        'grep -q "width=160" smoke_mkv_stream.txt': 'MKV smoke must require width 160',
        'grep -q "height=90" smoke_mkv_stream.txt': 'MKV smoke must require height 90',
        'grep -q "nb_read_frames=12" smoke_mkv_count.txt': 'MKV smoke must require 12 decoded frames',
    }
    for required, message in active_required.items():
        if required not in active_lines:
            fail(message, build)
    print('MKV smoke guard validated')


def validate_cli_long_input_smoke(repo_root):
    build = repo_root / BUILD_WORKFLOW
    active_lines = smoke_suite_function_lines(repo_root, RUNTIME_SMOKE_SUITE, 'smoke_cli_long_input', 'missing runtime smoke suite')

    required_active = {
        'long_input="$(python -c "print(\'a\' * 1100)")"': 'CLI long-input smoke must synthesize oversized input path',
        'if build/all/x265.exe --input "$long_input" --input-res 96x96 --fps 1 --frames 1 --output smoke_cli_long_input.hevc > smoke_cli_long_input.log 2>&1; then': 'CLI long-input smoke must actively require oversized --input failure',
        'echo "CLI long --input smoke unexpectedly succeeded"': 'CLI long-input smoke must report unexpected --input success',
        'grep -Fq \'Input filename exceeds supported length\' smoke_cli_long_input.log': 'CLI long-input smoke must require oversized --input error log',
        'if build/all/x265.exe "$long_input" -o smoke_cli_long_positional.hevc --input-res 96x96 --fps 1 --frames 1 > smoke_cli_long_positional.log 2>&1; then': 'CLI long-input smoke must actively require oversized positional-input failure',
        'echo "CLI long positional-input smoke unexpectedly succeeded"': 'CLI long-input smoke must report unexpected positional-input success',
        'grep -Fq \'Input filename exceeds supported length\' smoke_cli_long_positional.log': 'CLI long-input smoke must require oversized positional-input error log',
    }
    for required, message in required_active.items():
        if required not in active_lines:
            fail(message, build)
    print('CLI long-input smoke guard validated')


def validate_lavf_smoke(repo_root):
    build = repo_root / BUILD_WORKFLOW
    active_lines = runtime_smoke_active_lines(repo_root, RUNTIME_SMOKE_SUITE, 'smoke_lavf')

    generator_lines = [line for line in active_lines if 'ffmpeg ' in line and 'smoke_lavf_input.mkv' in line]
    if len(generator_lines) != 1:
        fail(f'expected exactly one LAVF input generator command, found {len(generator_lines)}', build)
    try:
        generator_args = shlex.split(generator_lines[0])
    except ValueError as exc:
        fail(f'could not parse LAVF input generator command: {exc}', build)
    for option, expected in LAVF_GENERATOR_OPTIONS:
        option_value(generator_args, option, expected, build, 'LAVF input generator')
    if generator_args[-1] != 'smoke_lavf_input.mkv':
        fail(f'LAVF input generator must write smoke_lavf_input.mkv, got {generator_args[-1]}', build)

    command, args = piped_x265_command(active_lines, build, 'LAVF smoke', 'smoke_lavf')
    if not args or args[0] != 'build/all/x265.exe':
        actual = args[0] if args else '<empty>'
        fail(f'LAVF smoke must run build/all/x265.exe, got {actual}', build)
    for option, expected in LAVF_SMOKE_OPTIONS:
        option_value(args, option, expected, build, 'LAVF smoke')

    active_required = {
        'test -s smoke_lavf_output.hevc': 'LAVF smoke must require non-empty HEVC output',
        'grep -Fq "lavf" smoke_lavf_log.txt': 'LAVF smoke must require lavf runtime log',
        'ffprobe -v error -show_entries stream=codec_name,codec_type,width,height -select_streams v:0 -of default=noprint_wrappers=1 smoke_lavf_output.hevc > smoke_lavf_probe.txt': 'LAVF smoke must capture video stream probe output',
        'ffprobe -v error -count_frames -select_streams v:0 -show_entries stream=nb_read_frames -of default=noprint_wrappers=1 smoke_lavf_output.hevc > smoke_lavf_count.txt': 'LAVF smoke must count decoded frames',
        'grep -q "codec_name=hevc" smoke_lavf_probe.txt': 'LAVF smoke must require HEVC codec',
        'grep -q "codec_type=video" smoke_lavf_probe.txt': 'LAVF smoke must require video stream',
        'grep -q "width=160" smoke_lavf_probe.txt': 'LAVF smoke must require width 160',
        'grep -q "height=90" smoke_lavf_probe.txt': 'LAVF smoke must require height 90',
        'grep -q "nb_read_frames=12" smoke_lavf_count.txt': 'LAVF smoke must require 12 decoded frames',
    }
    for required, message in active_required.items():
        if required not in active_lines:
            fail(message, build)
    if 'tee smoke_lavf_log.txt' not in command:
        fail('LAVF smoke must capture x265 log to smoke_lavf_log.txt', build)
    print('LAVF smoke guard validated')


def validate_qpfile_smoke(repo_root):
    build = repo_root / BUILD_WORKFLOW
    active_lines = runtime_smoke_active_lines(repo_root, RUNTIME_SMOKE_SUITE, 'smoke_qpfile')

    if '# keep qpfile parser moving across ignored lines' not in read_text(repo_root / RUNTIME_SMOKE_SUITE):
        fail('QPFile smoke must exercise ignored qpfile comment lines', build)

    for required, message in {
        "cat > smoke_qpfile.txt <<'EOF'": 'QPFile smoke must create smoke_qpfile.txt via heredoc',
        '0 I 60': 'QPFile smoke must require frame 0 I 60 entry',
        '3 P 24': 'QPFile smoke must require frame 3 P 24 entry',
        '6 B 26': 'QPFile smoke must require frame 6 B 26 entry',
        '9 K 20': 'QPFile smoke must require frame 9 K 20 entry',
        'EOF': 'QPFile smoke must close heredoc',
        'make_runtime_y4m smoke_qpfile.y4m 160 90 24 12 yuv420p': 'QPFile smoke must generate 12-frame yuv420p input',
        'test -s smoke_qpfile.hevc': 'QPFile smoke must require non-empty HEVC output',
        'ffprobe -v error -count_frames -select_streams v:0 -show_entries stream=nb_read_frames -of default=noprint_wrappers=1 smoke_qpfile.hevc > smoke_qpfile_count.txt': 'QPFile smoke must count decoded frames',
        'grep -q "nb_read_frames=12" smoke_qpfile_count.txt': 'QPFile smoke must require 12 decoded frames',
        'ffprobe -v error -select_streams v:0 -show_entries frame=pict_type -of default=noprint_wrappers=1:nokey=1 smoke_qpfile.hevc > smoke_qpfile_types.txt': 'QPFile smoke must dump frame types for qpfile overrides',
        'test "$(grep -c \'^I$\' smoke_qpfile_types.txt)" -eq 2': 'QPFile smoke must require a second qpfile-forced I frame after ignored lines',
    }.items():
        if required not in active_lines:
            fail(message, build)

    require_active_line_contains(active_lines, '--no-scenecut', build, 'QPFile smoke must disable scenecut for deterministic qpfile frame typing')
    require_x265_command(active_lines, build, 'QPFile smoke', 'smoke_qpfile', 'build/all/x265.exe', (
        ('--input', 'smoke_qpfile.y4m'),
        ('--input-res', '160x90'),
        ('--fps', '24'),
        ('--frames', '12'),
        ('--qpmax', '69'),
        ('--keyint', '250'),
        ('--min-keyint', '250'),
        ('--qpfile', 'smoke_qpfile.txt'),
        ('--output', 'smoke_qpfile.hevc'),
    ))
    print('QPFile smoke guard validated')


def validate_qpfile_oversized_smoke(repo_root):
    build = repo_root / BUILD_WORKFLOW
    active_lines = smoke_suite_function_lines(repo_root, RUNTIME_SMOKE_SUITE, 'smoke_qpfile_oversized', 'missing runtime smoke suite')

    for required, message in {
        'make_runtime_y4m smoke_qpfile.y4m 160 90 24 12 yuv420p': 'QPFile oversized smoke must generate 12-frame yuv420p input',
        "Path('smoke_qpfile_longline.txt').write_text('0 I 60\\n1 P ' + ('2' * 5000) + '\\n', encoding='utf-8')": 'QPFile oversized smoke must write an oversized single-line qpfile entry',
        'if build/all/x265.exe --input smoke_qpfile.y4m --input-res 160x90 --fps 24 --frames 2 --qpmax 69 --no-scenecut --keyint 250 --min-keyint 250 --qpfile smoke_qpfile_longline.txt --output smoke_qpfile_longline.hevc > smoke_qpfile_longline.log 2>&1; then': 'QPFile oversized smoke must actively require oversized-line failure',
        'echo "QPFile oversized-line smoke unexpectedly succeeded"': 'QPFile oversized smoke must report unexpected oversized-line success',
        "grep -Fq 'QP file contains a line exceeding supported length' smoke_qpfile_longline.log": 'QPFile oversized smoke must require oversized-line parse error log',
        "grep -Fq \"can't parse qpfile for frame 1 in x265\" smoke_qpfile_longline.log": 'QPFile oversized smoke must require qpfile parse failure propagation log',
    }.items():
        if required not in active_lines:
            fail(message, build)
    print('QPFile oversized-line smoke guard validated')


def validate_nalu_file_smoke(repo_root):
    build = repo_root / BUILD_WORKFLOW
    active_lines = smoke_suite_function_lines(repo_root, RUNTIME_SMOKE_SUITE, 'smoke_nalu_file', 'missing runtime smoke suite')

    for required, message in {
        'make_runtime_y4m smoke_nalu.y4m 96 64 24 3 yuv420p': 'Nalu-file smoke must generate 3-frame yuv420p input',
        'build/all/x265.exe --input smoke_nalu.y4m --input-res 96x64 --fps 24 --frames 2 --no-info --hash 0 --output smoke_nalu_base.hevc > smoke_nalu_base.log 2>&1': 'Nalu-file smoke must encode a baseline bitstream without external SEI input',
        "Path('smoke_nalu_future.txt').write_text('1 PREFIX 39/5 ' + ('A' * 800) + '\\n', encoding='utf-8')": 'Nalu-file smoke must synthesize a future-POC user SEI entry',
        'build/all/x265.exe --input smoke_nalu.y4m --input-res 96x64 --fps 24 --frames 2 --no-info --hash 0 --nalu-file smoke_nalu_future.txt --output smoke_nalu_future.hevc > smoke_nalu_future.log 2>&1': 'Nalu-file smoke must exercise future-POC user SEI rewinding',
        'test "$(wc -c < smoke_nalu_future.hevc)" -gt "$(wc -c < smoke_nalu_base.hevc)"': 'Nalu-file smoke must require the future-POC SEI payload to survive until its frame is encoded',
        "Path('smoke_nalu_long.txt').write_text('0 PREFIX 39/5 ' + ('A' * 5000) + '\\n', encoding='utf-8')": 'Nalu-file smoke must synthesize an oversized user SEI line',
        'build/all/x265.exe --input smoke_nalu.y4m --input-res 96x64 --fps 24 --frames 2 --no-info --hash 0 --nalu-file smoke_nalu_long.txt --output smoke_nalu_long.hevc > smoke_nalu_long.log 2>&1': 'Nalu-file smoke must encode with an oversized user SEI line to verify it is skipped safely',
        "grep -Fq 'User SEI file contains a line exceeding supported length; skipping' smoke_nalu_long.log": 'Nalu-file smoke must require the oversized-line warning log',
        'test "$(wc -c < smoke_nalu_long.hevc)" -eq "$(wc -c < smoke_nalu_base.hevc)"': 'Nalu-file smoke must require oversized user SEI lines to be skipped without injecting truncated payload bytes',
    }.items():
        if required not in active_lines:
            fail(message, build)
    print('Nalu-file smoke guard validated')


def validate_output_depth_invalid_smoke(repo_root):
    build = repo_root / BUILD_WORKFLOW
    active_lines = smoke_suite_function_lines(repo_root, RUNTIME_SMOKE_SUITE, 'smoke_output_depth_invalid', 'missing runtime smoke suite')

    for required, message in {
        'if build/all/x265.exe --output-depth 9 --help > smoke_output_depth_invalid.log 2>&1; then': 'Output-depth invalid smoke must actively require failure',
        'echo "Output-depth invalid smoke unexpectedly succeeded"': 'Output-depth invalid smoke must report unexpected success',
        "grep -Fq 'invalid argument: output-depth = 9' smoke_output_depth_invalid.log": 'Output-depth invalid smoke must require the invalid-argument log',
        "! grep -Fq 'falling back to default bit-depth' smoke_output_depth_invalid.log": 'Output-depth invalid smoke must reject fallback-to-default warnings',
    }.items():
        if required not in active_lines:
            fail(message, build)
    print('Output-depth invalid smoke guard validated')


def validate_chunk_negative_smoke(repo_root):
    build = repo_root / BUILD_WORKFLOW
    active_lines = smoke_suite_function_lines(repo_root, RUNTIME_SMOKE_SUITE, 'smoke_chunk_negative', 'missing runtime smoke suite')

    for required, message in {
        'if build/all/x265.exe --chunk-start -1 --help > smoke_chunk_start_negative.log 2>&1; then': 'Chunk-negative smoke must actively require chunk-start failure',
        'echo "Chunk-start negative smoke unexpectedly succeeded"': 'Chunk-negative smoke must report unexpected chunk-start success',
        "grep -Fq 'invalid argument: chunk-start = -1' smoke_chunk_start_negative.log": 'Chunk-negative smoke must require the chunk-start invalid-argument log',
        'if build/all/x265.exe --chunk-end -1 --help > smoke_chunk_end_negative.log 2>&1; then': 'Chunk-negative smoke must actively require chunk-end failure',
        'echo "Chunk-end negative smoke unexpectedly succeeded"': 'Chunk-negative smoke must report unexpected chunk-end success',
        "grep -Fq 'invalid argument: chunk-end = -1' smoke_chunk_end_negative.log": 'Chunk-negative smoke must require the chunk-end invalid-argument log',
    }.items():
        if required not in active_lines:
            fail(message, build)
    print('Chunk-negative smoke guard validated')


def validate_zonefile_smoke(repo_root):
    build = repo_root / BUILD_WORKFLOW
    active_lines = runtime_smoke_active_lines(repo_root, RUNTIME_SMOKE_SUITE, 'smoke_zonefile')

    for required, message in {
        "cat > smoke_zonefile.txt <<'EOF'": 'Zonefile smoke must create smoke_zonefile.txt via heredoc',
        '0 --bitrate 350': 'Zonefile smoke must require frame 0 bitrate override',
        '6 --bitrate 500': 'Zonefile smoke must require frame 6 bitrate override',
        'EOF': 'Zonefile smoke must close heredoc',
        'make_runtime_y4m smoke_zonefile.y4m 160 90 24 12 yuv420p': 'Zonefile smoke must generate 12-frame yuv420p input',
        'test -s smoke_zonefile.hevc': 'Zonefile smoke must require non-empty HEVC output',
        'ffprobe -v error -count_frames -select_streams v:0 -show_entries stream=nb_read_frames -of default=noprint_wrappers=1 smoke_zonefile.hevc > smoke_zonefile_count.txt': 'Zonefile smoke must count decoded frames',
        'grep -q "nb_read_frames=12" smoke_zonefile_count.txt': 'Zonefile smoke must require 12 decoded frames',
    }.items():
        if required not in active_lines:
            fail(message, build)

    require_x265_command(active_lines, build, 'Zonefile smoke', 'smoke_zonefile', 'build/all/x265.exe', (
        ('--input', 'smoke_zonefile.y4m'),
        ('--input-res', '160x90'),
        ('--fps', '24'),
        ('--frames', '12'),
        ('--bitrate', '400'),
        ('--zonefile', 'smoke_zonefile.txt'),
        ('--output', 'smoke_zonefile.hevc'),
    ))
    print('Zonefile smoke guard validated')


def validate_zonefile_oversized_smoke(repo_root):
    build = repo_root / BUILD_WORKFLOW
    active_lines = smoke_suite_function_lines(repo_root, RUNTIME_SMOKE_SUITE, 'smoke_zonefile_oversized', 'missing runtime smoke suite')

    for required, message in {
        'make_runtime_y4m smoke_zonefile.y4m 160 90 24 12 yuv420p': 'Zonefile oversized smoke must generate 12-frame yuv420p input',
        "tokens = ' '.join(f'--bitrate {100 + i}' for i in range(260))": 'Zonefile oversized smoke must synthesize excessive zone arguments',
        "Path('smoke_zonefile_oversized.txt').write_text('0 ' + tokens + '\\n', encoding='utf-8')": 'Zonefile oversized smoke must write oversized zonefile config',
        'if build/all/x265.exe --input smoke_zonefile.y4m --input-res 160x90 --fps 24 --frames 12 --bitrate 400 --zonefile smoke_zonefile_oversized.txt --output smoke_zonefile_oversized.hevc > smoke_zonefile_oversized.log 2>&1; then': 'Zonefile oversized smoke must actively require failure',
        'echo "Zonefile oversized-argument smoke unexpectedly succeeded"': 'Zonefile oversized smoke must report unexpected success',
        "grep -Fq 'Zone file entry exceeds supported argument count' smoke_zonefile_oversized.log": 'Zonefile oversized smoke must require argument-count error log',
        "Path('smoke_zonefile_longline.txt').write_text('0 --bitrate 100 ' + ('A' * 5000) + '\\n', encoding='utf-8')": 'Zonefile oversized smoke must write oversized single-line zonefile config',
        'if build/all/x265.exe --input smoke_zonefile.y4m --input-res 160x90 --fps 24 --frames 12 --bitrate 400 --zonefile smoke_zonefile_longline.txt --output smoke_zonefile_longline.hevc > smoke_zonefile_longline.log 2>&1; then': 'Zonefile oversized smoke must actively require long-line failure',
        'echo "Zonefile oversized-line smoke unexpectedly succeeded"': 'Zonefile oversized smoke must report unexpected long-line success',
        "grep -Fq 'Zone file line 1 exceeds supported length' smoke_zonefile_longline.log": 'Zonefile oversized smoke must require long-line error log',
    }.items():
        if required not in active_lines:
            fail(message, build)
    print('Zonefile oversized-argument smoke guard validated')


def validate_recon_smoke(repo_root):
    build = repo_root / BUILD_WORKFLOW
    active_lines = runtime_smoke_active_lines(repo_root, RUNTIME_SMOKE_SUITE, 'smoke_recon')
    if 'make_runtime_y4m smoke_recon.y4m 160 90 24 12 yuv420p' not in active_lines:
        fail('Recon smoke must generate 12-frame yuv420p input', build)

    require_x265_command(active_lines, build, 'Recon smoke', 'smoke_recon', 'build/all/x265.exe', (
        ('--input', 'smoke_recon.y4m'),
        ('--input-res', '160x90'),
        ('--fps', '24'),
        ('--frames', '12'),
        ('--recon', 'smoke_recon_out.y4m'),
        ('--output', 'smoke_recon.hevc'),
    ))
    for required, message in {
        'test -s smoke_recon.hevc': 'Recon smoke must require non-empty HEVC output',
        'test -s smoke_recon_out.y4m': 'Recon smoke must require non-empty recon output',
        "grep -q '^YUV4MPEG2 ' smoke_recon_out.y4m": 'Recon smoke must require YUV4MPEG2 header in recon output',
    }.items():
        if required not in active_lines:
            fail(message, build)
    print('Recon smoke guard validated')


def validate_analysis_save_load_smoke(repo_root):
    build = repo_root / BUILD_WORKFLOW
    active_lines = runtime_smoke_active_lines(repo_root, RUNTIME_SMOKE_SUITE, 'smoke_analysis_save_load')
    if 'make_runtime_y4m smoke_analysis.y4m 128 72 24 4 yuv420p' not in active_lines:
        fail('Analysis save/load smoke must generate 4-frame yuv420p input', build)

    save_command, save_args = piped_x265_command(active_lines, build, 'Analysis save/load save smoke', 'smoke_analysis_save.hevc')
    if not save_args or save_args[0] != 'build/all/x265.exe':
        actual = save_args[0] if save_args else '<empty>'
        fail(f'Analysis save/load save smoke must run build/all/x265.exe, got {actual}', build)
    for option, expected in (
        ('--input', 'smoke_analysis.y4m'),
        ('--input-res', '128x72'),
        ('--fps', '24'),
        ('--frames', '4'),
        ('--preset', 'medium'),
        ('--analysis-save', 'smoke_analysis.dat'),
        ('--analysis-save-reuse-level', '10'),
        ('--bitrate', '800'),
        ('--output', 'smoke_analysis_save.hevc'),
    ):
        option_value(save_args, option, expected, build, 'Analysis save/load save smoke')
    if '--no-progress' not in save_args:
        fail('Analysis save/load save smoke must disable progress output', build)
    if 'tee smoke_analysis_save.log' not in save_command:
        fail('Analysis save/load save smoke must capture x265 log to smoke_analysis_save.log', build)

    load_command, load_args = piped_x265_command(active_lines, build, 'Analysis save/load load smoke', 'smoke_analysis_load.hevc')
    if not load_args or load_args[0] != 'build/all/x265.exe':
        actual = load_args[0] if load_args else '<empty>'
        fail(f'Analysis save/load load smoke must run build/all/x265.exe, got {actual}', build)
    for option, expected in (
        ('--input', 'smoke_analysis.y4m'),
        ('--input-res', '128x72'),
        ('--fps', '24'),
        ('--frames', '4'),
        ('--preset', 'medium'),
        ('--analysis-load', 'smoke_analysis.dat'),
        ('--analysis-load-reuse-level', '10'),
        ('--bitrate', '800'),
        ('--output', 'smoke_analysis_load.hevc'),
    ):
        option_value(load_args, option, expected, build, 'Analysis save/load load smoke')
    if '--no-progress' not in load_args:
        fail('Analysis save/load load smoke must disable progress output', build)
    if 'tee smoke_analysis_load.log' not in load_command:
        fail('Analysis save/load load smoke must capture x265 log to smoke_analysis_load.log', build)

    for required, message in {
        'test -s smoke_analysis.dat': 'Analysis save/load smoke must require non-empty analysis file',
        'test -s smoke_analysis_save.hevc': 'Analysis save/load smoke must require non-empty save HEVC output',
        'test -s smoke_analysis_load.hevc': 'Analysis save/load smoke must require non-empty load HEVC output',
        "grep -Fq 'encoded 4 frames' smoke_analysis_save.log": 'Analysis save/load smoke must require save encoded-frame log',
        "grep -Fq 'encoded 4 frames' smoke_analysis_load.log": 'Analysis save/load smoke must require load encoded-frame log',
        'ffprobe -v error -count_frames -select_streams v:0 -show_entries stream=nb_read_frames -of default=noprint_wrappers=1 smoke_analysis_save.hevc > smoke_analysis_save_count.txt': 'Analysis save/load smoke must count decoded save frames',
        'ffprobe -v error -count_frames -select_streams v:0 -show_entries stream=nb_read_frames -of default=noprint_wrappers=1 smoke_analysis_load.hevc > smoke_analysis_load_count.txt': 'Analysis save/load smoke must count decoded load frames',
        "grep -q 'nb_read_frames=4' smoke_analysis_save_count.txt": 'Analysis save/load smoke must require 4 decoded save frames',
        "grep -q 'nb_read_frames=4' smoke_analysis_load_count.txt": 'Analysis save/load smoke must require 4 decoded load frames',
    }.items():
        if required not in active_lines:
            fail(message, build)
    print('Analysis save/load smoke guard validated')


def validate_2pass_stats_smoke(repo_root):
    build = repo_root / BUILD_WORKFLOW
    active_lines = runtime_smoke_active_lines(repo_root, RUNTIME_SMOKE_SUITE, 'smoke_2pass_stats')
    for required, message in {
        'make_runtime_y4m smoke_2pass_stats.y4m 160 90 24 8 yuv420p': '2pass stats smoke must generate 8-frame 160x90 input',
        'make_runtime_y4m smoke_2pass_stats_mismatch.y4m 128 72 24 8 yuv420p': '2pass stats smoke must generate 8-frame mismatched 128x72 input',
        'test -s smoke_2pass_stats.stats': '2pass stats smoke must require non-empty stats output',
        'test -s smoke_2pass_stats_pass1.hevc': '2pass stats smoke must require non-empty pass1 HEVC output',
        'test -s smoke_2pass_stats_pass2.hevc': '2pass stats smoke must require non-empty pass2 HEVC output',
        "grep -Fq ' input-res=160x90' smoke_2pass_stats.stats": '2pass stats smoke must require input-res in stats header',
        "grep -Fq ' conformance-window-offsets right=0 bottom=0' smoke_2pass_stats.stats": '2pass stats smoke must require spaced conformance-window offsets in stats header',
        "grep -Fq 'encoded 8 frames' smoke_2pass_stats_pass1.log": '2pass stats smoke must require pass1 encoded-frame log',
        "grep -Fq 'encoded 8 frames' smoke_2pass_stats_pass2.log": '2pass stats smoke must require pass2 encoded-frame log',
        'ffprobe -v error -count_frames -select_streams v:0 -show_entries stream=nb_read_frames -of default=noprint_wrappers=1 smoke_2pass_stats_pass2.hevc > smoke_2pass_stats_pass2_count.txt': '2pass stats smoke must count decoded pass2 frames',
        "grep -q 'nb_read_frames=8' smoke_2pass_stats_pass2_count.txt": '2pass stats smoke must require 8 decoded pass2 frames',
        'if build/all/x265.exe --input smoke_2pass_stats_mismatch.y4m --input-res 128x72 --fps 24 --frames 8 --bitrate 500 --pass 2 --stats smoke_2pass_stats.stats --no-progress --output smoke_2pass_stats_mismatch.hevc > smoke_2pass_stats_mismatch.log 2>&1; then': '2pass stats smoke must actively require mismatched pass2 failure',
        'echo "2pass stats mismatch smoke unexpectedly succeeded"': '2pass stats smoke must report unexpected mismatched pass2 success',
        "grep -Fq 'input-res mismatch with 1st pass (128 x 72 vs 160 x 90)' smoke_2pass_stats_mismatch.log": '2pass stats smoke must require mismatched input-res error log',
    }.items():
        if required not in active_lines:
            fail(message, build)

    pass1_command, pass1_args = piped_x265_command(active_lines, build, '2pass stats pass1 smoke', 'smoke_2pass_stats_pass1.hevc')
    if not pass1_args or pass1_args[0] != 'build/all/x265.exe':
        actual = pass1_args[0] if pass1_args else '<empty>'
        fail(f'2pass stats pass1 smoke must run build/all/x265.exe, got {actual}', build)
    for option, expected in (
        ('--input', 'smoke_2pass_stats.y4m'),
        ('--input-res', '160x90'),
        ('--fps', '24'),
        ('--frames', '8'),
        ('--bitrate', '500'),
        ('--pass', '1'),
        ('--stats', 'smoke_2pass_stats.stats'),
        ('--output', 'smoke_2pass_stats_pass1.hevc'),
    ):
        option_value(pass1_args, option, expected, build, '2pass stats pass1 smoke')
    if '--no-progress' not in pass1_args:
        fail('2pass stats pass1 smoke must disable progress output', build)
    if 'tee smoke_2pass_stats_pass1.log' not in pass1_command:
        fail('2pass stats pass1 smoke must capture x265 log to smoke_2pass_stats_pass1.log', build)

    pass2_command, pass2_args = piped_x265_command(active_lines, build, '2pass stats pass2 smoke', 'smoke_2pass_stats_pass2.hevc')
    if not pass2_args or pass2_args[0] != 'build/all/x265.exe':
        actual = pass2_args[0] if pass2_args else '<empty>'
        fail(f'2pass stats pass2 smoke must run build/all/x265.exe, got {actual}', build)
    for option, expected in (
        ('--input', 'smoke_2pass_stats.y4m'),
        ('--input-res', '160x90'),
        ('--fps', '24'),
        ('--frames', '8'),
        ('--bitrate', '500'),
        ('--pass', '2'),
        ('--stats', 'smoke_2pass_stats.stats'),
        ('--output', 'smoke_2pass_stats_pass2.hevc'),
    ):
        option_value(pass2_args, option, expected, build, '2pass stats pass2 smoke')
    if '--no-progress' not in pass2_args:
        fail('2pass stats pass2 smoke must disable progress output', build)
    if 'tee smoke_2pass_stats_pass2.log' not in pass2_command:
        fail('2pass stats pass2 smoke must capture x265 log to smoke_2pass_stats_pass2.log', build)
    print('2pass stats smoke guard validated')


def validate_abr_ladder_smoke(repo_root):
    build = repo_root / BUILD_WORKFLOW
    active_lines = runtime_smoke_active_lines(repo_root, RUNTIME_SMOKE_SUITE, 'smoke_abr_ladder')
    for required, message in {
        'ffmpeg -hide_banner -loglevel error -y -f lavfi -i "testsrc2=size=64x36:rate=24" -frames:v 4 -pix_fmt yuv420p10le -f rawvideo smoke_abr_ladder.yuv': 'ABR ladder smoke must generate 4-frame raw yuv420p10 input',
        "cat > smoke_abr_ladder.txt <<'EOF'": 'ABR ladder smoke must create smoke_abr_ladder.txt via heredoc',
        '[base:0:nil] --input smoke_abr_ladder.yuv --input-res 64x36 --fps 24 --frames 4 --input-csp i420 --input-depth 10 --ctu 16 --preset medium --bitrate 400 --no-progress -o smoke_abr_base.hevc': 'ABR ladder smoke must require base ladder config entry',
        '[scaled:10:base] --input smoke_abr_ladder.yuv --input-res 128x72 --fps 24 --frames 4 --input-csp i420 --input-depth 10 --ctu 16 --preset medium --bitrate 700 --no-progress -o smoke_abr_scaled.hevc': 'ABR ladder smoke must require scaled ladder config entry',
        'EOF': 'ABR ladder smoke must close heredoc',
        'test -s smoke_abr_base.hevc': 'ABR ladder smoke must require non-empty base HEVC output',
        'test -s smoke_abr_scaled.hevc': 'ABR ladder smoke must require non-empty scaled HEVC output',
        'test "$(grep -Fc \'encoded 4 frames\' smoke_abr_ladder.log)" -eq 2': 'ABR ladder smoke must require two encoded-frame log entries',
        'ffprobe -v error -count_frames -select_streams v:0 -show_entries stream=nb_read_frames -of default=noprint_wrappers=1 smoke_abr_base.hevc > smoke_abr_base_count.txt': 'ABR ladder smoke must count decoded base frames',
        'ffprobe -v error -count_frames -select_streams v:0 -show_entries stream=nb_read_frames -of default=noprint_wrappers=1 smoke_abr_scaled.hevc > smoke_abr_scaled_count.txt': 'ABR ladder smoke must count decoded scaled frames',
        'ffprobe -v error -show_entries stream=width,height -select_streams v:0 -of default=noprint_wrappers=1 smoke_abr_base.hevc > smoke_abr_base_probe.txt': 'ABR ladder smoke must probe base output dimensions',
        'ffprobe -v error -show_entries stream=width,height -select_streams v:0 -of default=noprint_wrappers=1 smoke_abr_scaled.hevc > smoke_abr_scaled_probe.txt': 'ABR ladder smoke must probe scaled output dimensions',
        "grep -q 'nb_read_frames=4' smoke_abr_base_count.txt": 'ABR ladder smoke must require 4 decoded base frames',
        "grep -q 'nb_read_frames=4' smoke_abr_scaled_count.txt": 'ABR ladder smoke must require 4 decoded scaled frames',
        "grep -q 'width=64' smoke_abr_base_probe.txt": 'ABR ladder smoke must require 64-pixel base width',
        "grep -q 'height=36' smoke_abr_base_probe.txt": 'ABR ladder smoke must require 36-pixel base height',
        "grep -q 'width=128' smoke_abr_scaled_probe.txt": 'ABR ladder smoke must require 128-pixel scaled width',
        "grep -q 'height=72' smoke_abr_scaled_probe.txt": 'ABR ladder smoke must require 72-pixel scaled height',
    }.items():
        if required not in active_lines:
            fail(message, build)

    command, args = piped_x265_command(active_lines, build, 'ABR ladder smoke', 'smoke_abr_ladder.txt')
    if not args or args[0] != 'build/all/x265.exe':
        actual = args[0] if args else '<empty>'
        fail(f'ABR ladder smoke must run build/all/x265.exe, got {actual}', build)
    option_value(args, '--abr-ladder', 'smoke_abr_ladder.txt', build, 'ABR ladder smoke')
    if 'tee smoke_abr_ladder.log' not in command:
        fail('ABR ladder smoke must capture x265 log to smoke_abr_ladder.log', build)
    print('ABR ladder smoke guard validated')


def validate_video_signal_type_preset_oversized_smoke(repo_root):
    build = repo_root / BUILD_WORKFLOW
    active_lines = smoke_suite_function_lines(repo_root, RUNTIME_SMOKE_SUITE, 'smoke_video_signal_type_preset_oversized', 'missing runtime smoke suite')

    for required, message in {
        'make_runtime_y4m smoke_recon.y4m 160 90 24 1 yuv420p': 'Video-signal-type-preset oversized smoke must generate 1-frame yuv420p input',
        'long_vst="$(python -c "print(\'A\' * 200 + \':P3D65x1000n0005\')")"': 'Video-signal-type-preset oversized smoke must synthesize oversized preset',
        'if build/all/x265.exe --input smoke_recon.y4m --input-res 160x90 --fps 24 --frames 1 --video-signal-type-preset "$long_vst" --output smoke_vst_oversized.hevc > smoke_vst_oversized.log 2>&1; then': 'Video-signal-type-preset oversized smoke must actively require failure',
        'echo "Video-signal-type-preset oversized smoke unexpectedly succeeded"': 'Video-signal-type-preset oversized smoke must report unexpected success',
        "grep -Fq 'Incorrect video-signal-type-preset, aborting' smoke_vst_oversized.log": 'Video-signal-type-preset oversized smoke must require malformed preset log',
    }.items():
        if required not in active_lines:
            fail(message, build)
    print('Video-signal-type-preset oversized smoke guard validated')


def validate_gop_output_smoke(repo_root):
    build = repo_root / BUILD_WORKFLOW
    active_lines = runtime_smoke_active_lines(repo_root, RUNTIME_SMOKE_SUITE, 'smoke_gop_output')
    if 'make_runtime_y4m smoke_gop.y4m 128 72 24 16 yuv420p' not in active_lines:
        fail('GOP smoke must generate 16-frame yuv420p input', build)

    args = require_x265_command(active_lines, build, 'GOP smoke', 'smoke_gop', 'build/all/x265.exe', GOP_SMOKE_OPTIONS)
    for expected in GOP_SMOKE_FLAGS:
        if expected not in args:
            fail(f'missing GOP smoke argument: {expected}', build)

    mux_lines = [line for line in active_lines if line == 'gop_muxer.exe smoke_gop.gop']
    if len(mux_lines) != 1:
        fail(f'expected exactly one GOP muxer command, found {len(mux_lines)}', build)

    active_required = {
        'test -s smoke_gop.gop': 'GOP smoke must require non-empty .gop output',
        'test -s smoke_gop.options': 'GOP smoke must require non-empty .options output',
        'test -s smoke_gop.headers': 'GOP smoke must require non-empty .headers output',
        'test -s smoke_gop-000000.hevc-gop-data': 'GOP smoke must require first gop-data sidecar',
        'test -s smoke_gop-000008.hevc-gop-data': 'GOP smoke must require second gop-data sidecar',
        "printf '%s\\n' smoke_gop-*.hevc-gop-data > smoke_gop_data_files.txt": 'GOP smoke must list gop-data sidecars',
        "grep -Fxq 'smoke_gop-000000.hevc-gop-data' smoke_gop_data_files.txt": 'GOP smoke must list first gop-data sidecar',
        "grep -Fxq 'smoke_gop-000008.hevc-gop-data' smoke_gop_data_files.txt": 'GOP smoke must list second gop-data sidecar',
        'test "$(wc -l < smoke_gop_data_files.txt)" -eq 2': 'GOP smoke must require exactly two gop-data sidecars',
        "grep -Fxq '#options smoke_gop.options' smoke_gop.gop": 'GOP smoke must require options reference in .gop',
        "test \"$(grep -Fxc '#options smoke_gop.options' smoke_gop.gop)\" -eq 1": 'GOP smoke must require exactly one options reference',
        "grep -Fxq '#headers smoke_gop.headers' smoke_gop.gop": 'GOP smoke must require headers reference in .gop',
        "grep -Fxq 'smoke_gop-000000.hevc-gop-data' smoke_gop.gop": 'GOP smoke must require first sidecar reference in .gop',
        "grep -Fxq 'smoke_gop-000008.hevc-gop-data' smoke_gop.gop": 'GOP smoke must require second sidecar reference in .gop',
        "grep -Fxq 'b-frames 0' smoke_gop.options": 'GOP smoke must require b-frames 0 option',
        "grep -Fxq 'b-pyramid 0' smoke_gop.options": 'GOP smoke must require b-pyramid 0 option',
        "grep -Fxq 'output-fps-num 24000' smoke_gop.options": 'GOP smoke must require output-fps-num 24000',
        "grep -Fxq 'output-fps-den 1000' smoke_gop.options": 'GOP smoke must require output-fps-den 1000',
        "grep -Fxq 'source-width 128' smoke_gop.options": 'GOP smoke must require source-width 128',
        "grep -Fxq 'source-height 72' smoke_gop.options": 'GOP smoke must require source-height 72',
        "grep -Fxq 'sar-width 1' smoke_gop.options": 'GOP smoke must require sar-width 1',
        "grep -Fxq 'sar-height 1' smoke_gop.options": 'GOP smoke must require sar-height 1',
        'test -s smoke_gop.mp4': 'GOP smoke must require non-empty muxed MP4',
        'ffprobe -v error -show_entries format=format_name,duration -of default=noprint_wrappers=1 smoke_gop.mp4 > smoke_gop_mux_format.txt': 'GOP smoke must capture muxed MP4 format probe output',
        'ffprobe -v error -show_streams -select_streams v:0 smoke_gop.mp4 > smoke_gop_mux_stream.txt': 'GOP smoke must capture muxed MP4 stream probe output',
        'ffprobe -v error -count_frames -select_streams v:0 -show_entries stream=nb_read_frames -of default=noprint_wrappers=1 smoke_gop.mp4 > smoke_gop_mux_count.txt': 'GOP smoke must count muxed MP4 frames',
        "grep -q 'format_name=mov,mp4,m4a,3gp,3g2,mj2' smoke_gop_mux_format.txt": 'GOP smoke must require muxed MP4 format',
        "grep -q 'codec_name=hevc' smoke_gop_mux_stream.txt": 'GOP smoke must require muxed HEVC codec',
        "grep -q 'codec_type=video' smoke_gop_mux_stream.txt": 'GOP smoke must require muxed video stream',
        "grep -q 'width=128' smoke_gop_mux_stream.txt": 'GOP smoke must require muxed width=128',
        "grep -q 'height=72' smoke_gop_mux_stream.txt": 'GOP smoke must require muxed height=72',
        "awk -F= '/^extradata_size=/{ if (($2+0) > 0) found=1 } END { if (!found) exit 1 }' smoke_gop_mux_stream.txt": 'GOP smoke must require positive extradata_size in muxed MP4 stream',
        "grep -q 'nb_read_frames=16' smoke_gop_mux_count.txt": 'GOP smoke must require 16 muxed decoded frames',
    }
    for required, message in active_required.items():
        if required not in active_lines:
            fail(message, build)
    print('GOP output smoke guard validated')


def validate_mp4_smokes(repo_root):
    build = repo_root / BUILD_WORKFLOW
    smoke_steps = (
        (
            'MP4 smoke',
            'MP4 Smoke (All CLI)',
            'smoke_mp4',
            'smoke',
            'smoke',
            'smoke.mp4',
            'flags',
            '24',
            '16',
            'yuv420p',
            MP4_SMOKE_FLAGS,
            MP4_SMOKE_OPTIONS,
            {
                'probe_mp4 smoke smoke.mp4 flags': 'MP4 smoke must probe packet flags',
                'assert_common_mp4 smoke 128 72 yuv420p 24/1 16 1/24000': 'MP4 smoke must require common MP4 stream properties',
                'assert_duration_window smoke 0.60 0.75': 'MP4 smoke must require bounded duration',
                "awk -F, '$1 == 1 { kf++; if (kf == 2 && NR != 9) exit 1 } END { if (kf < 2) exit 1 }' smoke_frames.csv": 'MP4 smoke must require second keyframe at frame 9',
            },
        ),
        (
            'MP4 open-GOP smoke',
            'MP4 Smoke (All CLI Open GOP)',
            'smoke_mp4_open_gop',
            'open-gop',
            'smoke_open',
            'smoke_open.mp4',
            'pts_time,dts_time,flags',
            '24',
            '16',
            'yuv420p',
            MP4_OPEN_GOP_SMOKE_FLAGS,
            MP4_OPEN_GOP_SMOKE_OPTIONS,
            {
                'probe_mp4 smoke_open smoke_open.mp4 pts_time,dts_time,flags': 'MP4 open-GOP smoke must probe timing and flags',
                'assert_common_mp4 smoke_open 128 72 yuv420p 24/1 16 1/24000': 'MP4 open-GOP smoke must require common MP4 stream properties',
                "assert_mp4_markers smoke_open.mp4 iso6 sgpd sbgp 'rap '": 'MP4 open-GOP smoke must require sample-group markers',
                'assert_duration_window smoke_open 0.60 0.75': 'MP4 open-GOP smoke must require bounded duration',
                "awk -F, '$3 ~ /K/ { kf++; if (kf == 2) { if ($1 == \"N/A\") exit 1; if (($1+0) < 0.30 || ($1+0) > 0.38) exit 1 } } END { if (kf < 2) exit 1 }' smoke_open_packets.csv": 'MP4 open-GOP smoke must require second key packet timing window',
            },
        ),
        (
            'MP4 CRA smoke',
            'MP4 Smoke (All CLI CRA)',
            'smoke_mp4_cra',
            'cra',
            'smoke_cra',
            'smoke_cra.mp4',
            'flags',
            '24',
            '16',
            'yuv420p',
            MP4_CRA_SMOKE_FLAGS,
            MP4_CRA_SMOKE_OPTIONS,
            {
                'probe_mp4 smoke_cra smoke_cra.mp4 flags': 'MP4 CRA smoke must probe packet flags',
                'assert_common_mp4 smoke_cra 128 72 yuv420p 24/1 16 1/24000': 'MP4 CRA smoke must require common MP4 stream properties',
                'assert_mp4_markers smoke_cra.mp4 iso6 hvc1 hvcC': 'MP4 CRA smoke must require MP4 HEVC markers',
                "awk -F, '$1 == 1 { kf++ } END { if (kf != 16) exit 1 }' smoke_cra_frames.csv": 'MP4 CRA smoke must require every frame keyframe-marked',
                'assert_duration_window smoke_cra 0.60 0.75': 'MP4 CRA smoke must require bounded duration',
            },
        ),
        (
            'MP4 single-frame smoke',
            'MP4 Smoke (All CLI Single Frame)',
            'smoke_mp4_single_frame',
            'single-frame',
            'smoke_single',
            'smoke_single.mp4',
            'flags',
            '24',
            '1',
            'yuv420p',
            (),
            MP4_SINGLE_FRAME_SMOKE_OPTIONS,
            {
                'probe_mp4 smoke_single smoke_single.mp4 flags': 'MP4 single-frame smoke must probe packet flags',
                'assert_common_mp4 smoke_single 128 72 yuv420p 24/1 1 1/24000': 'MP4 single-frame smoke must require common MP4 stream properties',
                'assert_mp4_markers smoke_single.mp4 iso6 hvc1 hvcC': 'MP4 single-frame smoke must require MP4 HEVC markers',
                'assert_single_frame_mp4 smoke_single 0.05 0.02 0.08': 'MP4 single-frame smoke must require single-frame timing window',
            },
        ),
        (
            'MP4 frames=0 smoke',
            'MP4 Smoke (All CLI Frames=0 Means Encode Available Input)',
            'smoke_mp4_frames_zero',
            'frames-zero',
            'smoke_zero',
            'smoke_zero.mp4',
            'flags',
            '24',
            '1',
            'yuv420p',
            (),
            MP4_ZERO_FRAMES_SMOKE_OPTIONS,
            {
                'probe_mp4 smoke_zero smoke_zero.mp4 flags': 'MP4 frames=0 smoke must probe packet flags',
                'assert_common_mp4 smoke_zero 128 72 yuv420p 24/1 1 1/24000': 'MP4 frames=0 smoke must require common MP4 stream properties',
                'assert_mp4_markers smoke_zero.mp4 iso6 hvc1 hvcC': 'MP4 frames=0 smoke must require MP4 HEVC markers',
                'assert_single_frame_mp4 smoke_zero 0.05 0.02 0.08': 'MP4 frames=0 smoke must require single-frame timing window',
            },
        ),
        (
            'MP4 VUI smoke',
            'MP4 Smoke (All CLI VUI Metadata)',
            'smoke_mp4_vui',
            'vui',
            'smoke_vui',
            'smoke_vui.mp4',
            'flags',
            '24',
            '4',
            'yuv420p',
            (),
            MP4_VUI_SMOKE_OPTIONS,
            {
                'probe_mp4 smoke_vui smoke_vui.mp4 flags': 'MP4 VUI smoke must probe packet flags',
                'assert_common_mp4 smoke_vui 128 72 yuv420p 24/1 4 1/24000': 'MP4 VUI smoke must require common MP4 stream properties',
                'grep -q "sample_aspect_ratio=4:3" smoke_vui_stream.txt': 'MP4 VUI smoke must require SAR metadata',
                'grep -q "display_aspect_ratio=64:27" smoke_vui_stream.txt': 'MP4 VUI smoke must require DAR metadata',
                'grep -q "color_range=tv" smoke_vui_stream.txt': 'MP4 VUI smoke must require limited range metadata',
                'grep -q "color_space=bt709" smoke_vui_stream.txt': 'MP4 VUI smoke must require bt709 matrix metadata',
                'grep -q "color_transfer=bt709" smoke_vui_stream.txt': 'MP4 VUI smoke must require bt709 transfer metadata',
                'grep -q "color_primaries=bt709" smoke_vui_stream.txt': 'MP4 VUI smoke must require bt709 primaries metadata',
                'assert_mp4_markers smoke_vui.mp4 iso6 colr': 'MP4 VUI smoke must require color box marker',
            },
        ),
        (
            'MP4 single-frame 24000/1001 smoke',
            'MP4 Smoke (All CLI Single Frame 24000/1001)',
            'smoke_mp4_single_frame_frac',
            'single-frame-24000-1001',
            'smoke_single_frac',
            'smoke_single_frac.mp4',
            'flags',
            '24000/1001',
            '1',
            'yuv420p',
            (),
            (
                ('--input', 'smoke_single_frac.y4m'),
                ('--input-res', '128x72'),
                ('--fps', '24000/1001'),
                ('--frames', '1'),
                ('--bframes', '0'),
                ('--keyint', '1'),
                ('--min-keyint', '1'),
                ('--output', 'smoke_single_frac.mp4'),
            ),
            {
                'probe_mp4 smoke_single_frac smoke_single_frac.mp4 flags': 'MP4 single-frame 24000/1001 smoke must probe packet flags',
                'assert_common_mp4 smoke_single_frac 128 72 yuv420p 24000/1001 1 1/24000': 'MP4 single-frame 24000/1001 smoke must require common MP4 stream properties',
                'assert_mp4_markers smoke_single_frac.mp4 iso6 hvc1 hvcC': 'MP4 single-frame 24000/1001 smoke must require MP4 HEVC markers',
                'assert_single_frame_mp4 smoke_single_frac 0.06 0.03 0.06': 'MP4 single-frame 24000/1001 smoke must require single-frame timing window',
            },
        ),
        (
            'MP4 24000/1001 smoke',
            'MP4 Smoke (All CLI 24000/1001)',
            'smoke_mp4_frac',
            'frac-24000-1001',
            'smoke_frac',
            'smoke_frac.mp4',
            'pts_time,dts_time,flags',
            '24000/1001',
            '24',
            'yuv420p',
            MP4_FRAC_SMOKE_FLAGS,
            MP4_FRAC_SMOKE_OPTIONS,
            {
                'probe_mp4 smoke_frac smoke_frac.mp4 pts_time,dts_time,flags': 'MP4 24000/1001 smoke must probe timing and flags',
                'assert_common_mp4 smoke_frac 128 72 yuv420p 24000/1001 24 1/24000': 'MP4 24000/1001 smoke must require common MP4 stream properties',
                'assert_mp4_markers smoke_frac.mp4 iso6 hvc1 hvcC': 'MP4 24000/1001 smoke must require MP4 HEVC markers',
                "awk -F, '$3 ~ /K/ { kf++; if (kf == 2 && NR != 13) exit 1 } END { if (kf < 2) exit 1 }' smoke_frac_packets.csv": 'MP4 24000/1001 smoke must require second key packet at packet 13',
                'assert_duration_window smoke_frac 0.95 1.10': 'MP4 24000/1001 smoke must require bounded duration',
            },
        ),
        (
            'MP4 B-pyramid smoke',
            'MP4 Smoke (All CLI B-Pyramid)',
            'smoke_mp4_b_pyramid',
            'b-pyramid',
            'smoke_bpyramid',
            'smoke_bpyramid.mp4',
            'pts_time,dts_time,flags',
            '24',
            '16',
            'yuv420p',
            MP4_BPYRAMID_SMOKE_FLAGS,
            MP4_BPYRAMID_SMOKE_OPTIONS,
            {
                'probe_mp4 smoke_bpyramid smoke_bpyramid.mp4 pts_time,dts_time,flags': 'MP4 B-pyramid smoke must probe timing and flags',
                'assert_common_mp4 smoke_bpyramid 128 72 yuv420p 24/1 16 1/24000': 'MP4 B-pyramid smoke must require common MP4 stream properties',
                "awk -F, '$3 ~ /K/ { kf++; if (kf == 2 && NR != 9) exit 1 } END { if (kf < 2) exit 1 }' smoke_bpyramid_packets.csv": 'MP4 B-pyramid smoke must require second key packet at packet 9',
                'assert_duration_window smoke_bpyramid 0.60 0.75': 'MP4 B-pyramid smoke must require bounded duration',
            },
        ),
        (
            'MP4 AUD smoke',
            'MP4 Smoke (All CLI AUD Request Stays Valid)',
            'smoke_mp4_aud',
            'aud',
            'smoke_aud',
            'smoke_aud.mp4',
            'pts_time,dts_time,flags',
            '24',
            '16',
            'yuv420p',
            MP4_AUD_SMOKE_FLAGS,
            MP4_AUD_SMOKE_OPTIONS,
            {
                'probe_mp4 smoke_aud smoke_aud.mp4 pts_time,dts_time,flags': 'MP4 AUD smoke must probe timing and flags',
                'assert_common_mp4 smoke_aud 128 72 yuv420p 24/1 16 1/24000': 'MP4 AUD smoke must require common MP4 stream properties',
                "awk -F, '$3 ~ /K/ { kf++; if (kf == 2) { if ($1 == \"N/A\") exit 1; if (($1+0) < 0.30 || ($1+0) > 0.38) exit 1 } } END { if (kf < 2) exit 1 }' smoke_aud_packets.csv": 'MP4 AUD smoke must require second key packet timing window',
                'assert_duration_window smoke_aud 0.60 0.75': 'MP4 AUD smoke must require bounded duration',
            },
        ),
        (
            'MP4 EOS/EOB smoke',
            'MP4 Smoke (All CLI EOS/EOB Request Stays Valid)',
            'smoke_mp4_eos_eob',
            'eos-eob',
            'smoke_eos',
            'smoke_eos.mp4',
            'pts_time,dts_time,flags',
            '24',
            '16',
            'yuv420p',
            MP4_EOS_SMOKE_FLAGS,
            MP4_EOS_SMOKE_OPTIONS,
            {
                'probe_mp4 smoke_eos smoke_eos.mp4 pts_time,dts_time,flags': 'MP4 EOS/EOB smoke must probe timing and flags',
                'assert_common_mp4 smoke_eos 128 72 yuv420p 24/1 16 1/24000': 'MP4 EOS/EOB smoke must require common MP4 stream properties',
                "awk -F, '$3 ~ /K/ { kf++; if (kf == 2) { if ($1 == \"N/A\") exit 1; if (($1+0) < 0.30 || ($1+0) > 0.38) exit 1 } } END { if (kf < 2) exit 1 }' smoke_eos_packets.csv": 'MP4 EOS/EOB smoke must require second key packet timing window',
                'assert_duration_window smoke_eos 0.60 0.75': 'MP4 EOS/EOB smoke must require bounded duration',
            },
        ),
        (
            'MP4 IDR recovery smoke',
            'MP4 Smoke (All CLI IDR Recovery SEI)',
            'smoke_mp4_idr_recovery',
            'idr-recovery',
            'smoke_recovery',
            'smoke_recovery.mp4',
            'pts_time,dts_time,flags',
            '24',
            '16',
            'yuv420p',
            MP4_RECOVERY_SMOKE_FLAGS,
            MP4_RECOVERY_SMOKE_OPTIONS,
            {
                'probe_mp4 smoke_recovery smoke_recovery.mp4 pts_time,dts_time,flags': 'MP4 IDR recovery smoke must probe timing and flags',
                'assert_common_mp4 smoke_recovery 128 72 yuv420p 24/1 16 1/24000': 'MP4 IDR recovery smoke must require common MP4 stream properties',
                'assert_mp4_markers smoke_recovery.mp4 iso6 hvc1 hvcC': 'MP4 IDR recovery smoke must require MP4 HEVC markers',
                "awk -F, '$3 ~ /K/ { kf++; if (kf == 2) { if ($1 == \"N/A\") exit 1; if (($1+0) < 0.30 || ($1+0) > 0.38) exit 1 } } END { if (kf < 2) exit 1 }' smoke_recovery_packets.csv": 'MP4 IDR recovery smoke must require second key packet timing window',
                'assert_duration_window smoke_recovery 0.60 0.75': 'MP4 IDR recovery smoke must require bounded duration',
            },
        ),
    )

    for smoke_step in smoke_steps:
        validate_mp4_smoke_step(build, repo_root, MP4_SMOKE_SUITE, *smoke_step)

    active_lines = smoke_suite_function_lines(repo_root, MP4_SMOKE_SUITE, 'smoke_mp4_strict_cbr_fails', 'missing MP4 smoke suite')
    generator_line = 'ffmpeg -hide_banner -loglevel error -f lavfi -i testsrc2=size=128x72:rate=24 -frames:v 16 -pix_fmt yuv420p smoke_strict_cbr.y4m'
    if generator_line not in active_lines:
        fail('MP4 strict-CBR smoke must generate 16-frame yuv420p input', build)
    command_lines = [line for line in active_lines if 'build/all/x265.exe' in line and 'smoke_strict_cbr.mp4' in line]
    if len(command_lines) != 1:
        fail(f'expected exactly one MP4 strict-CBR smoke x265 command, found {len(command_lines)}', build)
    before_then = command_lines[0]
    if before_then.startswith('if '):
        before_then = before_then[3:].strip()
    if before_then.endswith('; then'):
        before_then = before_then[:-6].strip()
    try:
        args = shlex.split(before_then)
    except ValueError as exc:
        fail(f'could not parse MP4 strict-CBR smoke command: {exc}', build)
    if not args or args[0] != 'build/all/x265.exe':
        actual = args[0] if args else '<empty>'
        fail(f'MP4 strict-CBR smoke must run build/all/x265.exe, got {actual}', build)
    for option, expected in (
        ('--input', 'smoke_strict_cbr.y4m'),
        ('--input-res', '128x72'),
        ('--fps', '24'),
        ('--frames', '16'),
        ('--bitrate', '300'),
        ('--vbv-bufsize', '300'),
        ('--output', 'smoke_strict_cbr.mp4'),
    ):
        option_value(args, option, expected, build, 'MP4 strict-CBR smoke')
    for expected in ('--strict-cbr', '--hrd'):
        if expected not in args:
            fail(f'missing MP4 strict-CBR smoke argument: {expected}', build)
    for required, message in {
        'echo "strict-cbr MP4 encode unexpectedly succeeded"': 'MP4 strict-CBR smoke must fail if strict-CBR MP4 encode unexpectedly succeeds',
        'if [ -f smoke_strict_cbr.mp4 ] && [ -s smoke_strict_cbr.mp4 ]; then': 'MP4 strict-CBR smoke must conditionally inspect unexpected MP4 output',
        'ffprobe -v error smoke_strict_cbr.mp4 >/dev/null 2>&1 && {': 'MP4 strict-CBR smoke must reject valid playable MP4 output',
        'echo "strict-cbr MP4 output should not be a valid playable file"': 'MP4 strict-CBR smoke must explain unexpected valid MP4 output',
    }.items():
        if required not in active_lines:
            fail(message, build)
    print('MP4 smoke guards validated')


def validate_zimg_smoke(repo_root):
    build = repo_root / BUILD_WORKFLOW
    blocks = [block for path, line, block in collect_run_blocks(build) if 'smoke_zimg' in block]
    if len(blocks) != 1:
        fail(f'expected exactly one ZIMG smoke run block, found {len(blocks)}', build)

    script = blocks[0]
    active_lines = shell_active_lines(script)
    command_lines = [
        line for line in active_lines
        if 'build/cxx20-warning-scan/x265.exe' in line
        and (
            'smoke_zimg.hevc' in line
            or 'smoke_zimg_bypass.hevc' in line
        )
    ]
    if len(command_lines) != 2:
        fail(f'expected exactly two ZIMG x265 commands, found {len(command_lines)}', build)

    def validate_zimg_command(command, expected_options, output_check, log_check, log_path, context):
        before_pipe = command.split('|', 1)[0].strip()
        try:
            tokens = shlex.split(before_pipe)
        except ValueError as exc:
            fail(f'could not parse {context}: {exc}', build)

        args = [token for token in tokens if token not in ('2>&1',)]
        if not args or args[0] != 'build/cxx20-warning-scan/x265.exe':
            actual = args[0] if args else '<empty>'
            fail(f'{context} must run build/cxx20-warning-scan/x265.exe, got {actual}', build)
        for option, expected in expected_options:
            option_value(args, option, expected, build, context)
        if output_check not in active_lines:
            fail(f'{context} must require non-empty HEVC output', build)
        if log_check not in active_lines:
            fail(f'{context} must require expected log line', build)
        if f'tee {log_path}' not in command:
            fail(f'{context} must capture x265 log to {log_path}', build)

    resize_command = next((line for line in command_lines if 'smoke_zimg.hevc' in line), None)
    bypass_command = next((line for line in command_lines if 'smoke_zimg_bypass.hevc' in line), None)
    if resize_command is None:
        fail('missing ZIMG resize smoke command', build)
    if bypass_command is None:
        fail('missing ZIMG bypass smoke command', build)

    validate_zimg_command(
        resize_command,
        ZIMG_SMOKE_OPTIONS,
        'test -s build/cxx20-warning-scan/smoke_zimg.hevc',
        "grep -Fq 'zimg [info]: Resize: 96x96' build/cxx20-warning-scan/smoke_zimg.log",
        'build/cxx20-warning-scan/smoke_zimg.log',
        'ZIMG smoke',
    )
    validate_zimg_command(
        bypass_command,
        (
            ('--input', 'build/cxx20-warning-scan/smoke_zimg.yuv'),
            ('--input-res', '128x128'),
            ('--fps', '1'),
            ('--frames', '1'),
            ('--vf', 'zimg:crop(0,0,-0,-0)'),
            ('--output', 'build/cxx20-warning-scan/smoke_zimg_bypass.hevc'),
        ),
        'test -s build/cxx20-warning-scan/smoke_zimg_bypass.hevc',
        "grep -Fq 'zimg [info]: Nothing to do. Bypassing' build/cxx20-warning-scan/smoke_zimg_bypass.log",
        'build/cxx20-warning-scan/smoke_zimg_bypass.log',
        'ZIMG bypass smoke',
    )

    for required, message in {
        'long_zimg_vf="$(python -c "print(\'zimg:lanczos(\' + \'1\' * 1100 + \')\')")"': 'ZIMG smoke must synthesize long-parameter vf input',
        'if build/cxx20-warning-scan/x265.exe --input build/cxx20-warning-scan/smoke_zimg.yuv --input-res 128x128 --fps 1 --frames 1 --vf "$long_zimg_vf" --output build/cxx20-warning-scan/smoke_zimg_longparam.hevc > build/cxx20-warning-scan/smoke_zimg_longparam.log 2>&1; then': 'ZIMG smoke must actively require long-parameter failure',
        'echo "ZIMG long-parameter smoke unexpectedly succeeded"': 'ZIMG smoke must report unexpected long-parameter success',
        'grep -Fq \'Filter parameters exceeds supported length\' build/cxx20-warning-scan/smoke_zimg_longparam.log': 'ZIMG smoke must require long-parameter error log',
        'long_filter_name_vf="$(python -c "print(\'a\' * 1100 + \':x\')")"': 'ZIMG smoke must synthesize long filter-name vf input',
        'if build/cxx20-warning-scan/x265.exe --input build/cxx20-warning-scan/smoke_zimg.yuv --input-res 128x128 --fps 1 --frames 1 --vf "$long_filter_name_vf" --output build/cxx20-warning-scan/smoke_filter_longname.hevc > build/cxx20-warning-scan/smoke_filter_longname.log 2>&1; then': 'ZIMG smoke must actively require long filter-name failure',
        'echo "Filter long-name smoke unexpectedly succeeded"': 'ZIMG smoke must report unexpected long-name success',
        'grep -Fq \'Filter name exceeds supported length\' build/cxx20-warning-scan/smoke_filter_longname.log': 'ZIMG smoke must require long-name error log',
    }.items():
        if required not in active_lines:
            fail(message, build)
    print('ZIMG smoke guard validated')


def validate_linux_gcc_smoke(repo_root):
    build = repo_root / BUILD_WORKFLOW
    parsed = load_yaml(repo_root, BUILD_WORKFLOW)
    active_lines = shell_active_logical_lines(workflow_step_run(
        parsed,
        build,
        'cxx20-linux-gcc-compile-commands',
        'Run Linux GCC C++20 compile command diagnostics',
    ))
    command_lines = [line for line in active_lines if 'build/cxx20-linux-gcc-compile-commands/x265 ' in line]
    if len(command_lines) != 1:
        fail(f'expected exactly one Linux GCC x265 smoke command, found {len(command_lines)}', build)

    command = command_lines[0]
    before_pipe = command.split('|', 1)[0].strip()
    try:
        tokens = shlex.split(before_pipe)
    except ValueError as exc:
        fail(f'could not parse Linux GCC smoke command: {exc}', build)

    args = [token for token in tokens if token not in ('2>&1',)]
    if not args or args[0] != 'build/cxx20-linux-gcc-compile-commands/x265':
        actual = args[0] if args else '<empty>'
        fail(f'Linux GCC smoke must run build/cxx20-linux-gcc-compile-commands/x265, got {actual}', build)
    for option, expected in LINUX_GCC_SMOKE_OPTIONS:
        option_value(args, option, expected, build, 'Linux GCC smoke')

    active_required = {
        'test -s build/cxx20-linux-gcc-compile-commands/smoke_linux_gcc.log': 'Linux GCC smoke must require non-empty smoke log',
        'test -s build/cxx20-linux-gcc-compile-commands/smoke_linux_gcc.hevc': 'Linux GCC smoke must require non-empty HEVC output',
        "grep -Fq 'encoded 1 frames' build/cxx20-linux-gcc-compile-commands/smoke_linux_gcc.log": 'Linux GCC smoke must require encoded-frame log',
    }
    for required, message in active_required.items():
        if required not in active_lines:
            fail(message, build)
    if 'tee build/cxx20-linux-gcc-compile-commands/smoke_linux_gcc.log' not in command:
        fail('Linux GCC smoke must capture x265 log to build/cxx20-linux-gcc-compile-commands/smoke_linux_gcc.log', build)
    print('Linux GCC smoke guard validated')


def validate_linux_cmake_setup(repo_root):
    build_path = repo_root / BUILD_WORKFLOW
    parsed = load_yaml(repo_root, BUILD_WORKFLOW)
    requirements = (
        ('cxx20-linux-gcc-compile-commands', 'Run Linux GCC C++20 compile command diagnostics'),
        ('linux-clang-sanitizers', 'Build and smoke-test with ASan and UBSan'),
    )
    for job_name, step_name in requirements:
        active_lines = shell_active_logical_lines(workflow_step_run(parsed, build_path, job_name, step_name))
        require_active_line_contains(
            active_lines,
            'source x265/.github/scripts/ensure_cmake4.sh',
            build_path,
            f'{job_name} must source ensure_cmake4 helper',
        )
        require_active_line_contains(
            active_lines,
            'ensure_cmake4',
            build_path,
            f'{job_name} must call ensure_cmake4 before cmake use',
        )
        if any('python -m venv "$RUNNER_TEMP/cmake-venv"' in line for line in active_lines):
            fail(f'{job_name} must not inline duplicate CMake venv bootstrap logic', build_path)
    print('Linux CMake setup validated')


def validate_linux_sanitizer_toolchain_setup(repo_root):
    build_path = repo_root / BUILD_WORKFLOW
    parsed = load_yaml(repo_root, BUILD_WORKFLOW)
    active_lines = shell_active_logical_lines(workflow_step_run(
        parsed,
        build_path,
        'linux-clang-sanitizers',
        'Build and smoke-test with ASan and UBSan',
    ))
    require_active_line_contains(
        active_lines,
        'source x265/.github/scripts/ensure_linux_sanitizer_toolchain.sh',
        build_path,
        'linux-clang-sanitizers must source Linux sanitizer toolchain helper',
    )
    require_active_line_contains(
        active_lines,
        'ensure_linux_sanitizer_toolchain',
        build_path,
        'linux-clang-sanitizers must call Linux sanitizer toolchain helper before compiler use',
    )
    for forbidden in (
        'sudo apt-get update',
        'sudo apt-get install -y clang lld ninja-build',
    ):
        if forbidden in active_lines:
            fail(f'linux-clang-sanitizers must not inline duplicate sanitizer toolchain apt bootstrap: {forbidden}', build_path)
    print('Linux sanitizer toolchain setup validated')


def validate_warning_scan_runtime_smokes(repo_root):
    build = repo_root / BUILD_WORKFLOW
    blocks = [
        block for path, line, block in collect_run_blocks(build)
        if 'smoke_12bit' in block or 'smoke_shared' in block or 'smoke_all' in block
    ]
    if not blocks:
        print('warning-scan runtime smoke guards skipped: no runtime smoke commands in fixture')
        return
    active_lines = []
    for block in blocks:
        active_lines.extend(shell_active_logical_lines(block))

    for context, executable, options, output_check in WARNING_SCAN_SMOKES:
        command_lines = [line for line in active_lines if executable in line]
        if len(command_lines) != 1:
            fail(f'expected exactly one {context} command, found {len(command_lines)}', build)
        try:
            tokens = shlex.split(command_lines[0])
        except ValueError as exc:
            fail(f'could not parse {context} command: {exc}', build)
        args = [token for token in tokens if token not in ('2>&1',)]
        if not args or args[0] != executable:
            actual = args[0] if args else '<empty>'
            fail(f'{context} must run {executable}, got {actual}', build)
        for option, expected in options:
            option_value(args, option, expected, build, context)
        if output_check not in active_lines:
            fail(f'{context} must require non-empty HEVC output', build)
    print('warning-scan runtime smoke guards validated')


FULL_EVENT_ENV_VALUE = "${{ (github.event_name == 'workflow_dispatch' || startsWith(github.ref, 'refs/tags/')) && 'true' || 'false' }}"
FULL_WARNING_SCAN_SHELL_CONDITION = '[ "${CI_FULL_EVENT}" = \'true\' ]'
FULL_WARNING_SCAN_STEP_IF = "env.CI_FULL_EVENT == 'true'"


def line_indexes_containing(active_lines, required):
    return [index for index, line in enumerate(active_lines) if required in line]


def require_single_line_index(active_lines, required, path, message):
    indexes = line_indexes_containing(active_lines, required)
    if len(indexes) != 1:
        fail(message, path)
    return indexes[0]


def command_prefix_indexes(active_lines, expected_tokens):
    indexes = []
    for index, line in enumerate(active_lines):
        try:
            tokens = shlex.split(line)
        except ValueError:
            continue
        if tuple(tokens[:len(expected_tokens)]) == expected_tokens:
            indexes.append(index)
    return indexes


def require_single_command_prefix_index(active_lines, expected_tokens, path, message):
    indexes = command_prefix_indexes(active_lines, expected_tokens)
    if len(indexes) != 1:
        fail(message, path)
    return indexes[0]


def require_warning_scan_gate_function(active_lines, path, context):
    function_index = require_single_line_index(
        active_lines,
        'is_full_warning_scan() {',
        path,
        f'{context} must define full warning scan gate helper',
    )
    condition_index = function_index + 1
    if condition_index >= len(active_lines) or active_lines[condition_index] != FULL_WARNING_SCAN_SHELL_CONDITION:
        fail(f'{context} full gate must be limited to workflow_dispatch or tags', path)
    close_index = condition_index + 1
    if close_index >= len(active_lines) or active_lines[close_index] != '}':
        fail(f'{context} full gate helper must close immediately after the event/ref condition', path)


def matching_fi_index(active_lines, if_index, path, message):
    depth = 0
    for index in range(if_index, len(active_lines)):
        line = active_lines[index]
        if line.startswith('if ') and line.endswith('; then'):
            depth += 1
        elif line == 'fi':
            depth -= 1
            if depth == 0:
                return index
    fail(message, path)


def require_single_line_in_scope(active_lines, required, start_index, end_index, path, message):
    index = require_single_line_index(active_lines, required, path, message)
    if not start_index < index < end_index:
        fail(message, path)
    return index


def require_line_containing_in_scope(active_lines, required, start_index, end_index, path, message):
    indexes = [index for index in range(start_index + 1, end_index) if required in active_lines[index]]
    if len(indexes) != 1:
        fail(message, path)
    return indexes[0]


def require_single_command_prefix_in_scope(active_lines, expected_tokens, start_index, end_index, path, message):
    index = require_single_command_prefix_index(active_lines, expected_tokens, path, message)
    if not start_index < index < end_index:
        fail(message, path)
    return index


def validate_warning_scan_full_gate(repo_root):
    build = repo_root / BUILD_WORKFLOW
    parsed = load_yaml(repo_root, BUILD_WORKFLOW)

    cli_lines = shell_active_logical_lines(workflow_step_run(
        parsed,
        build,
        'cxx20-warning-scan',
        'Run C++20 CLI and dependency warning scans',
    ))
    require_warning_scan_gate_function(cli_lines, build, 'C++20 CLI/dependency warning scan')
    cli_gate_indexes = [index for index, line in enumerate(cli_lines) if line == 'if is_full_warning_scan; then']
    if len(cli_gate_indexes) != 2:
        fail('C++20 warning scan full-only dependency scans must be gated behind is_full_warning_scan', build)
    dependency_gate_start = cli_gate_indexes[0]
    dependency_gate_end = matching_fi_index(
        cli_lines,
        dependency_gate_start,
        build,
        'C++20 warning scan full-only dependency scans must close their is_full_warning_scan gate',
    )
    for expected_tokens in (
        ('configure_cxx20_scan', 'x265/source', 'build/cxx20-warning-scan-unity'),
        ('configure_cxx20_scan', 'x265/source', 'build/cxx20-warning-scan-shared-deps'),
        ('configure_cxx20_scan', 'x265/source', 'build/cxx20-warning-scan-shared-deps-asm'),
    ):
        require_single_command_prefix_in_scope(
            cli_lines,
            expected_tokens,
            dependency_gate_start,
            dependency_gate_end,
            build,
            f'C++20 warning scan full-only dependency scan must be inside is_full_warning_scan gate: {" ".join(expected_tokens)}',
        )
    require_single_line_in_scope(
        cli_lines,
        'ninja -C build/cxx20-warning-scan-shared-deps-asm cli',
        dependency_gate_start,
        dependency_gate_end,
        build,
        'C++20 warning scan full-only dependency asm build must stay inside is_full_warning_scan gate',
    )

    wait_gate_start = cli_gate_indexes[1]
    wait_gate_end = matching_fi_index(
        cli_lines,
        wait_gate_start,
        build,
        'C++20 warning scan full-only dependency wait must close its is_full_warning_scan gate',
    )
    require_single_line_in_scope(
        cli_lines,
        'wait_for_jobs "$warning_scan_unity_pid" "$warning_scan_shared_deps_pid" "$warning_scan_shared_deps_asm_pid"',
        wait_gate_start,
        wait_gate_end,
        build,
        'C++20 warning scan full-only dependency wait must be inside is_full_warning_scan gate',
    )
    require_single_line_in_scope(
        cli_lines,
        'test -x /clang64/bin/ffmpeg',
        wait_gate_start,
        wait_gate_end,
        build,
        'C++20 warning scan seed MP4 must verify CI-installed /clang64/bin/ffmpeg',
    )
    require_single_line_in_scope(
        cli_lines,
        '/clang64/bin/ffmpeg -hide_banner -loglevel error -y -f lavfi -i testsrc2=size=128x72:rate=24 -frames:v 4 -pix_fmt yuv420p build/cxx20-warning-scan-shared-deps-asm/smoke_shared_deps_seed.mp4',
        wait_gate_start,
        wait_gate_end,
        build,
        'C++20 warning scan seed MP4 must be generated with CI-installed /clang64/bin/ffmpeg',
    )
    require_single_line_in_scope(
        cli_lines,
        'build/cxx20-warning-scan-shared-deps-asm/x265.exe build/cxx20-warning-scan-shared-deps-asm/smoke_shared_deps_seed.mp4 --frames 4 --bframes 0 --keyint 1 --min-keyint 1 --no-progress -o build/cxx20-warning-scan-shared-deps-asm/smoke_shared_deps_out.mkv',
        wait_gate_start,
        wait_gate_end,
        build,
        'C++20 warning scan shared-deps ASM smoke must exercise LAVF input through MKV output',
    )
    require_single_line_in_scope(
        cli_lines,
        'test -s build/cxx20-warning-scan-shared-deps-asm/smoke_shared_deps_out.mkv',
        wait_gate_start,
        wait_gate_end,
        build,
        'C++20 warning scan shared-deps ASM smoke must require non-empty MKV output',
    )
    for index in range(wait_gate_start + 1, wait_gate_end):
        if 'smoke_shared_deps_out.mp4' in cli_lines[index]:
            fail('C++20 warning scan shared-deps ASM smoke must leave MP4 muxer runtime coverage to MP4 smoke suite', build)

    shared_step = workflow_step(parsed, build, 'cxx20-warning-scan', 'Run C++20 shared and all-bit-depth warning scans')
    if shared_step.get('if') != FULL_WARNING_SCAN_STEP_IF:
        fail('C++20 shared/all-bit-depth warning scan step must run only for workflow_dispatch or tags', build)

    cpu_lines = shell_active_logical_lines(workflow_step_run(
        parsed,
        build,
        'cxx20-warning-scan',
        'Run C++20 CPU and ASM warning scans',
    ))
    require_warning_scan_gate_function(cpu_lines, build, 'C++20 CPU/ASM warning scan')
    haswell_index = require_single_line_index(
        cpu_lines,
        'cpu_targets=(haswell)',
        build,
        'CPU warning scan push mode must keep haswell as the representative CPU target',
    )
    cpu_gate_indexes = [index for index, line in enumerate(cpu_lines) if line == 'if is_full_warning_scan; then']
    if len(cpu_gate_indexes) != 1:
        fail('CPU warning scan full-only CPU targets must be gated behind is_full_warning_scan', build)
    cpu_gate_start = cpu_gate_indexes[0]
    cpu_gate_end = matching_fi_index(
        cpu_lines,
        cpu_gate_start,
        build,
        'CPU warning scan full-only CPU target gate must close',
    )
    full_cpu_index = require_single_line_in_scope(
        cpu_lines,
        'cpu_targets+=(arrowlake znver5)',
        cpu_gate_start,
        cpu_gate_end,
        build,
        'CPU warning scan full mode must add arrowlake/znver5 targets behind is_full_warning_scan',
    )
    loop_index = require_single_line_index(
        cpu_lines,
        'for target_cpu in "${cpu_targets[@]}"; do',
        build,
        'CPU warning scan must loop over the gated CPU target list',
    )
    if not haswell_index < cpu_gate_start < full_cpu_index < cpu_gate_end < loop_index:
        fail('CPU warning scan must build push and full CPU target lists before the loop', build)
    print('C++20 warning scan full gate validated')


def validate_gnu20_diagnostic_steps(repo_root):
    build = repo_root / BUILD_WORKFLOW
    parsed = load_yaml(repo_root, BUILD_WORKFLOW)
    requirements = (
        (
            'cxx20-warning-scan',
            'Check GNU++20 downgrade guardrail',
            (
                ('configure_cxx20_scan x265/source build/cxx20-downgrade-guard', 'GNU++20 downgrade guard must actively configure downgrade build'),
                ('-DCMAKE_CXX_' 'STANDARD=17', 'GNU++20 downgrade guard must request C++17 override'),
                ('-DENABLE_CLI=OFF', 'GNU++20 downgrade guard must keep CLI disabled'),
                ('-DENABLE_ASSEMBLY=OFF', 'GNU++20 downgrade guard must keep assembly disabled'),
                ('check_cxx20_commands_clang build/cxx20-downgrade-guard', 'GNU++20 downgrade guard must actively check compile commands'),
                ('--min-cpp-commands=50', 'GNU++20 downgrade guard must keep broad compile command coverage'),
                ('--forbidden-flag-substring=-std=gnu++17', 'GNU++20 downgrade guard must reject GNU++17 flags'),
                ('--forbidden-flag-substring=-std=c++17', 'GNU++20 downgrade guard must reject C++17 flags'),
            ),
        ),
        (
            'cxx20-warning-scan',
            'Run C++20 CPU and ASM warning scans',
            (
                ('cpu_targets=(haswell)', 'CPU warning scan must keep haswell representative push coverage'),
                ('cpu_targets+=(arrowlake znver5)', 'CPU warning scan must keep arrowlake/znver5 full coverage'),
                ('for target_cpu in "${cpu_targets[@]}"; do', 'CPU warning scan must loop over the gated CPU target list'),
                ('--target-cpu="${target_cpu}"', 'CPU warning scan must pass target_cpu to configure helper'),
                ('--required-file-substring=source/common/cpu.cpp', 'CPU warning scan must actively require cpu.cpp'),
                ('--forbidden-file-substring=source/output/', 'CPU warning scan must actively reject output sources'),
                ('configure_cxx20_scan x265/source build/cxx20-warning-scan-asm', 'ASM warning scan must actively configure asm build'),
                ('-DENABLE_ASSEMBLY=ON', 'ASM warning scan must enable assembly'),
                ('-DENABLE_TESTS=ON', 'ASM warning scan must enable tests'),
                ('-DCMAKE_ASM_NASM_FLAGS=-w-macro-params-legacy', 'ASM warning scan must preserve NASM legacy macro warning flag'),
                ('--required-file-substring=source/test/', 'ASM warning scan must actively require test sources'),
                ('ninja -C build/cxx20-warning-scan-asm TestBench', 'ASM warning scan must actively build TestBench'),
            ),
        ),
        (
            'cxx20-gcc-compile-commands',
            'Run GCC C++20 compile command diagnostics',
            (
                ('check_cxx20_commands_gcc build/cxx20-gcc-compile-commands ', 'Windows GCC diagnostics must actively check base compile commands'),
                ('ninja -C build/cxx20-gcc-compile-commands cli', 'Windows GCC diagnostics must actively build base CLI'),
                ('check_cxx20_commands_gcc build/cxx20-gcc-compile-commands-12bit', 'Windows GCC diagnostics must actively check 12-bit compile commands'),
                ('--required-file-substring=source/output/mkv.cpp', 'Windows GCC diagnostics must actively require mkv.cpp coverage'),
                ('--required-file-flag=source/output/mkv.cpp=-DENABLE_MKV', 'Windows GCC diagnostics must actively require MKV macro'),
                ('--forbidden-file-flag=source/common/common.cpp=-DENABLE_LAVF', 'Windows GCC diagnostics must actively reject LAVF macro on common.cpp'),
                ('--forbidden-file-flag=source/common/common.cpp=-DENABLE_MKV', 'Windows GCC diagnostics must actively reject MKV macro on common.cpp'),
                ('--forbidden-file-flag=source/common/common.cpp=-DENABLE_LSMASH', 'Windows GCC diagnostics must actively reject L-SMASH macro on common.cpp'),
                ('--forbidden-file-flag=source/encoder/encoder.cpp=-DENABLE_LAVF', 'Windows GCC diagnostics must actively reject LAVF macro on encoder.cpp'),
                ('--forbidden-file-flag=source/encoder/encoder.cpp=-DENABLE_MKV', 'Windows GCC diagnostics must actively reject MKV macro on encoder.cpp'),
                ('--forbidden-file-flag=source/encoder/encoder.cpp=-DENABLE_LSMASH', 'Windows GCC diagnostics must actively reject L-SMASH macro on encoder.cpp'),
                ('--required-file-substring=source/common/winxp.cpp', 'Windows GCC diagnostics must actively require winxp.cpp coverage'),
                ('--required-file-flag=source/common/winxp.cpp=-D_WIN32_WINNT=_WIN32_WINNT_WIN7', 'Windows GCC diagnostics must actively require Win7 winxp.cpp macro'),
                ('--forbidden-file-flag=source/common/winxp.cpp=-D_WIN32_WINNT=_WIN32_WINNT_WINXP', 'Windows GCC diagnostics must actively reject WinXP winxp.cpp macro'),
            ),
        ),
        (
            'cxx20-linux-gcc-compile-commands',
            'Run Linux GCC C++20 compile command diagnostics',
            (
                ('check_cxx20_commands_gcc build/cxx20-linux-gcc-compile-commands ', 'Linux GCC diagnostics must actively check compile commands'),
                ('--required-file-substring=source/output/mkv.cpp', 'Linux GCC diagnostics must actively require mkv.cpp coverage'),
                ('--required-file-flag=source/output/mkv.cpp=-DENABLE_MKV', 'Linux GCC diagnostics must actively require MKV macro'),
                ('--forbidden-file-flag=source/common/common.cpp=-DENABLE_LAVF', 'Linux GCC diagnostics must actively reject LAVF macro on common.cpp'),
                ('--forbidden-file-flag=source/common/common.cpp=-DENABLE_MKV', 'Linux GCC diagnostics must actively reject MKV macro on common.cpp'),
                ('--forbidden-file-flag=source/common/common.cpp=-DENABLE_LSMASH', 'Linux GCC diagnostics must actively reject L-SMASH macro on common.cpp'),
                ('--forbidden-file-flag=source/encoder/encoder.cpp=-DENABLE_LAVF', 'Linux GCC diagnostics must actively reject LAVF macro on encoder.cpp'),
                ('--forbidden-file-flag=source/encoder/encoder.cpp=-DENABLE_MKV', 'Linux GCC diagnostics must actively reject MKV macro on encoder.cpp'),
                ('--forbidden-file-flag=source/encoder/encoder.cpp=-DENABLE_LSMASH', 'Linux GCC diagnostics must actively reject L-SMASH macro on encoder.cpp'),
                ('--required-file-substring=source/output/reconplay.cpp', 'Linux GCC diagnostics must actively require reconplay.cpp'),
                ('--forbidden-file-substring=source/common/winxp.cpp', 'Linux GCC diagnostics must actively reject winxp.cpp'),
                ('ninja -C build/cxx20-linux-gcc-compile-commands cli', 'Linux GCC diagnostics must actively build CLI'),
                ('build/cxx20-linux-gcc-compile-commands/x265 --input', 'Linux GCC diagnostics must actively run x265 smoke'),
                ("grep -Fq 'encoded 1 frames' build/cxx20-linux-gcc-compile-commands/smoke_linux_gcc.log", 'Linux GCC diagnostics must actively require encoded-frame smoke log'),
                ('configure_cxx20_scan x265/source build/cxx20-linux-gcc-compile-commands-12bit', 'Linux GCC diagnostics must actively configure 12-bit static target'),
                ('check_cxx20_commands_gcc build/cxx20-linux-gcc-compile-commands-12bit', 'Linux GCC diagnostics must actively check 12-bit compile commands'),
                ('--required-depth-define=-DX265_DEPTH=12', 'Linux GCC diagnostics must actively require 12-bit depth'),
                ('--forbidden-file-flag=source/encoder/api.cpp=-DEXPORT_C_API=1', 'Linux GCC diagnostics must actively reject exported API macro'),
                ('ninja -C build/cxx20-linux-gcc-compile-commands-12bit x265-static', 'Linux GCC diagnostics must actively build 12-bit static target'),
            ),
        ),
        (
            'cxx20-warning-scan',
            'Run C++20 CLI and dependency warning scans',
            (
                ('-DENABLE_ZIMG=ON', 'C++20 warning scan must actively enable ZIMG'),
                ('--required-file-substring=source/filters/zimgfilter.cpp', 'C++20 warning scan must actively require zimgfilter.cpp'),
                ('--required-file-flag=source/filters/zimgfilter.cpp=-DENABLE_ZIMG', 'C++20 warning scan must actively require ENABLE_ZIMG on zimgfilter.cpp'),
                ('--vf "zimg:lanczos(96,96)"', 'C++20 warning scan must actively run ZIMG filter smoke'),
                ("grep -Fq 'zimg [info]: Resize: 96x96' build/cxx20-warning-scan/smoke_zimg.log", 'C++20 warning scan must actively require ZIMG resize smoke log'),
                ("grep -Fq 'encoded 1 frames' build/cxx20-warning-scan/smoke_zimg.log", 'C++20 warning scan must actively require ZIMG encoded-frame smoke log'),
                ('configure_cxx20_scan x265/source build/cxx20-warning-scan-12bit', 'C++20 warning scan must actively configure 12-bit CLI'),
                ('check_cxx20_commands_clang build/cxx20-warning-scan-12bit', 'C++20 warning scan must actively check 12-bit CLI'),
                ('--required-depth-define=-DX265_DEPTH=12', 'C++20 warning scan must actively require 12-bit depth'),
                ('configure_cxx20_scan x265/source build/cxx20-warning-scan-unity', 'C++20 warning scan must actively configure unity build'),
                ('-DENABLE_UNITY_BUILD=ON', 'C++20 warning scan must actively enable unity build'),
                ('configure_cxx20_scan x265/source build/cxx20-warning-scan-shared-deps', 'C++20 warning scan must actively configure shared deps build'),
                ('--required-file-flag=source/input/lavf.cpp=-DENABLE_LAVF', 'C++20 warning scan must actively require LAVF macro'),
                ('--required-file-flag=source/output/mkv.cpp=-DENABLE_MKV', 'C++20 warning scan must actively require MKV macro'),
                ('--required-file-flag=source/output/mp4.cpp=-DENABLE_LSMASH', 'C++20 warning scan must actively require L-SMASH macro'),
                ('configure_cxx20_scan x265/source build/cxx20-warning-scan-shared-deps-asm', 'C++20 warning scan must actively configure shared deps asm build'),
            ),
        ),
        (
            'cxx20-warning-scan',
            'Run C++20 shared and all-bit-depth warning scans',
            (
                ('check_cxx20_commands_clang build/cxx20-warning-scan-shared-library', 'C++20 warning scan must actively check shared-library compile commands'),
                ('ninja -C build/cxx20-warning-scan-shared-library cli x265-shared', 'C++20 warning scan must actively build shared-library CLI and DLL'),
                ('--required-file-flag=source/encoder/api.cpp=-DEXPORT_C_API=1', 'C++20 warning scan must actively require exported API macro for shared-library builds'),
                ('check_cxx20_commands_clang build/cxx20-warning-scan-all-8b-lib', 'C++20 warning scan must actively check all 8-bit lib compile commands'),
                ('ninja -C build/cxx20-warning-scan-all-8b-lib x265-static', 'C++20 warning scan must actively build all 8-bit static target'),
                ('configure_cxx20_scan x265/source build/cxx20-warning-scan-all-12b-lib', 'C++20 warning scan must actively configure all 12-bit lib'),
                ('ninja -C build/cxx20-warning-scan-all-12b-lib x265-static', 'C++20 warning scan must actively build all 12-bit static target'),
                ('--required-file-flag=source/common/version.cpp=-DLINKED_8BIT=1', 'C++20 warning scan must actively require linked 8-bit version macro'),
                ('--required-file-flag=source/common/version.cpp=-DLINKED_12BIT=1', 'C++20 warning scan must actively require linked 12-bit version macro'),
                ('--required-file-flag=source/encoder/api.cpp=-DLINKED_8BIT=1', 'C++20 warning scan must actively require linked 8-bit API macro'),
                ('--required-file-flag=source/encoder/api.cpp=-DLINKED_12BIT=1', 'C++20 warning scan must actively require linked 12-bit API macro'),
                ('--forbidden-file-flag=source/encoder/api.cpp=-DEXPORT_C_API=1', 'C++20 warning scan must actively reject exported API macro'),
            ),
        ),
    )
    exact_command_requirements = (
        (
            'cxx20-warning-scan',
            'Check GNU++20 downgrade guardrail',
            (
                (('configure_cxx20_scan', 'x265/source', 'build/cxx20-downgrade-guard'), 'GNU++20 downgrade guard must actively configure downgrade build'),
                (('check_cxx20_commands_clang', 'build/cxx20-downgrade-guard'), 'GNU++20 downgrade guard must actively check compile commands'),
            ),
        ),
        (
            'cxx20-warning-scan',
            'Run C++20 CLI and dependency warning scans',
            (
                (('configure_cxx20_scan', 'x265/source', 'build/cxx20-warning-scan'), 'C++20 warning scan must actively configure base warning-scan target'),
                (('check_cxx20_commands_clang', 'build/cxx20-warning-scan'), 'C++20 warning scan must actively check base warning-scan compile commands target'),
                (('configure_cxx20_scan', 'x265/source', 'build/cxx20-warning-scan-12bit'), 'C++20 warning scan must actively configure 12-bit warning-scan target'),
                (('check_cxx20_commands_clang', 'build/cxx20-warning-scan-12bit'), 'C++20 warning scan must actively check 12-bit warning-scan compile commands target'),
                (('configure_cxx20_scan', 'x265/source', 'build/cxx20-warning-scan-shared-deps'), 'C++20 warning scan must actively configure shared-deps warning-scan target'),
                (('check_cxx20_commands_clang', 'build/cxx20-warning-scan-shared-deps'), 'C++20 warning scan must actively check shared-deps warning-scan compile commands target'),
                (('configure_cxx20_scan', 'x265/source', 'build/cxx20-warning-scan-shared-deps-asm'), 'C++20 warning scan must actively configure shared-deps-asm warning-scan target'),
            ),
        ),
        (
            'cxx20-warning-scan',
            'Run C++20 shared and all-bit-depth warning scans',
            (
                (('configure_cxx20_scan', 'x265/source', 'build/cxx20-warning-scan-all-12b-lib'), 'C++20 warning scan must actively configure all 12-bit lib'),
                (('check_cxx20_commands_clang', 'build/cxx20-warning-scan-all'), 'C++20 warning scan must actively check all-bit-depth warning-scan compile commands target'),
            ),
        ),
        (
            'cxx20-warning-scan',
            'Run C++20 CPU and ASM warning scans',
            (
                (('check_cxx20_commands_clang', 'build/cxx20-warning-scan-asm'), 'ASM warning scan must actively check asm compile commands target'),
            ),
        ),
        (
            'cxx20-gcc-compile-commands',
            'Run GCC C++20 compile command diagnostics',
            (
                (('check_cxx20_commands_gcc', 'build/cxx20-gcc-compile-commands-12bit'), 'Windows GCC diagnostics must actively check 12-bit compile commands'),
            ),
        ),
        (
            'cxx20-linux-gcc-compile-commands',
            'Run Linux GCC C++20 compile command diagnostics',
            (
                (('check_cxx20_commands_gcc', 'build/cxx20-linux-gcc-compile-commands-12bit'), 'Linux GCC diagnostics must actively check 12-bit compile commands'),
            ),
        ),
    )
    for job_name, step_name, required_items in requirements:
        active_lines = shell_active_logical_lines(workflow_step_run(parsed, build, job_name, step_name))
        for required, message in required_items:
            require_active_line_contains(active_lines, required, build, message)
    for job_name, step_name, required_commands in exact_command_requirements:
        active_lines = shell_active_logical_lines(workflow_step_run(parsed, build, job_name, step_name))
        for expected_tokens, message in required_commands:
            require_active_command_prefix(active_lines, expected_tokens, build, message)
    print('GNU++20 diagnostic step active commands validated')


def validate_required_snippets(repo_root, bash):
    build = validate_required_workflow_steps(repo_root, BUILD_WORKFLOW, 'Build workflow guard', build_workflow_step_requirements())
    validate_python_file(
        repo_root,
        PYTHON_CI_GUARD_BUNDLE,
        'missing Python CI guard bundle runner',
        required_text=(
            "CHECK_CI_GUARDS_COMMAND = ('python', '.github/scripts/check_ci_guards.py')",
            "NON_EXECUTED_TESTS = {'test_check_ci_guards_fixture.py'}",
            'WORKFLOW_GUARD_SUITE = (',
            'PROFDATA_GUARD_SUITE = WORKFLOW_GUARD_SUITE + (',
            "('python', '.github/scripts/check_dependency_patch_suffixes.py', '--allow-missing-cache'),",
            "('python', '.github/scripts/check_profdata_metadata.py', '--self-test'),",
            "('python', '.github/scripts/test_check_pgo_consume_chain.py'),",
            'from concurrent.futures import ThreadPoolExecutor, as_completed',
            'def run_commands_parallel(repo_root, commands, jobs):',
            '    run_commands_parallel(repo_root, commands, jobs)',
            "script_dir.glob('test_check_*.py')",
            'run_command(repo_root, CHECK_CI_GUARDS_COMMAND)',
            'for test_script in guard_test_scripts(repo_root):',
            "parser.add_argument('--suite', choices=tuple(SUITE_COMMANDS), default='default')",
            "parser.add_argument('--jobs', type=int, default=default_jobs())",
            'for command in SUITE_COMMANDS[suite]:',
        ),
        required_message='Python CI guard bundle runner missing detail',
    )
    build_profiling = validate_required_workflow_steps(repo_root, BUILD_PROFILING_WORKFLOW, 'Build Profiling workflow guard', profiling_step_requirements())
    build_pgo = validate_required_workflow_steps(repo_root, BUILD_PGO_WORKFLOW, 'Build PGO workflow guard', pgo_step_requirements())
    validate_required_workflow_steps(repo_root, UPDATE_DEPS_WORKFLOW, 'update-deps guard', (
        ('update-deps', 'Check CI guardrails', REQUIRED_UPDATE_DEPS_SNIPPETS[:1]),
        ('update-deps', 'Update Dependency Refs', REQUIRED_UPDATE_DEPS_SNIPPETS[1:6]),
        ('update-deps', 'Validate Dependency Ref Diff', REQUIRED_UPDATE_DEPS_SNIPPETS[6:]),
    ))
    update_deps_path = repo_root / UPDATE_DEPS_WORKFLOW
    update_deps = load_yaml(repo_root, UPDATE_DEPS_WORKFLOW)
    update_guard_step = workflow_step(update_deps, update_deps_path, 'update-deps', 'Check CI guardrails')
    if 'if' in update_guard_step:
        fail('update-deps Check CI guardrails must not be step-gated', update_deps_path)
    update_guard_lines = shell_active_logical_lines(
        workflow_step_run(update_deps, update_deps_path, 'update-deps', 'Check CI guardrails')
    )
    require_active_exact_command(
        update_guard_lines,
        ('python', '.github/scripts/run_python_ci_guard_bundle.py', '--suite', 'update-deps'),
        update_deps_path,
        'update-deps guard bundle must run the exact Python CI guard bundle runner with --suite update-deps without softening wrappers or extra flags',
    )

    build_path = repo_root / BUILD_WORKFLOW
    build_guard_step = workflow_step(build, build_path, 'validate-ci-guardrails', 'Run Python CI guard bundle')
    if 'if' in build_guard_step:
        fail('Build workflow Run Python CI guard bundle must not be step-gated', build_path)
    build_guard_lines = shell_active_logical_lines(
        workflow_step_run(build, build_path, 'validate-ci-guardrails', 'Run Python CI guard bundle')
    )
    require_active_exact_command(
        build_guard_lines,
        ('python', '.github/scripts/run_python_ci_guard_bundle.py'),
        build_path,
        'Build workflow guard bundle must run the exact Python CI guard bundle runner without softening wrappers or extra flags',
    )
    dependency_diff_step = workflow_step(build, build_path, 'validate-deps-cache-suffix', 'Check dependency patch cache suffixes')
    if 'if' in dependency_diff_step:
        fail('Build workflow Check dependency patch cache suffixes must not be step-gated', build_path)

    build_profiling_path = repo_root / BUILD_PROFILING_WORKFLOW
    jobs = workflow_jobs(build_profiling, build_profiling_path)
    if jobs.get('build', {}).get('needs') != 'validate-guardrails':
        fail('Build Profiling build job must need validate-guardrails', build_profiling_path)
    profiling_publish = jobs.get('publish-release', {})
    if profiling_publish.get('needs') != ['build', 'validate-guardrails']:
        fail('Build Profiling publish-release job must need build and validate-guardrails', build_profiling_path)
    if profiling_publish.get('if') != "startsWith(github.ref, 'refs/tags/')":
        fail('Build Profiling publish-release must only run for tag refs', build_profiling_path)
    profiling_guard_lines = shell_active_logical_lines(
        workflow_step_run(build_profiling, build_profiling_path, 'validate-guardrails', 'Check CI guardrails')
    )
    profiling_guard_step = workflow_step(build_profiling, build_profiling_path, 'validate-guardrails', 'Check CI guardrails')
    if 'if' in profiling_guard_step:
        fail('Build Profiling Check CI guardrails must not be step-gated', build_profiling_path)
    require_active_exact_command(
        profiling_guard_lines,
        ('python', '.github/scripts/run_python_ci_guard_bundle.py', '--suite', 'profdata'),
        build_profiling_path,
        'Build Profiling workflow guard bundle must run the exact Python CI guard bundle runner with --suite profdata without softening wrappers or extra flags',
    )

    build_profiling_job = jobs.get('build')
    if not isinstance(build_profiling_job, dict):
        fail('missing workflow job: build', build_profiling_path)
    for job_name in ('build', 'publish-release'):
        checkout_step = workflow_step(build_profiling, build_profiling_path, job_name, 'Checkout X265')
        checkout_with = checkout_step.get('with')
        if not isinstance(checkout_with, dict):
            fail(f'Build Profiling {job_name} Checkout X265 step must declare with inputs', build_profiling_path)
        for key, value in {
            'path': 'x265',
            'fetch-depth': 0,
            'fetch-tags': True,
        }.items():
            if checkout_with.get(key) != value:
                fail(f'Build Profiling {job_name} Checkout X265 must set {key}={value}', build_profiling_path)
    build_profiling_strategy = build_profiling_job.get('strategy')
    if not isinstance(build_profiling_strategy, dict):
        fail('Build Profiling build job must define a strategy', build_profiling_path)
    if build_profiling_strategy.get('fail-fast') is not False:
        fail('Build Profiling build job must set strategy.fail-fast to false so one profiling CPU failure cannot cancel remaining legs', build_profiling_path)
    build_profiling_matrix = build_profiling_strategy.get('matrix')
    if not isinstance(build_profiling_matrix, dict):
        fail('Build Profiling build job must define a matrix', build_profiling_path)
    expected_profiling_matrix = ['x86-64', 'haswell', 'skylake', 'alderlake', 'raptorlake', 'arrowlake', 'znver2', 'znver3', 'znver4', 'znver5']
    if build_profiling_matrix.get('target_cpu') != expected_profiling_matrix:
        fail('Build Profiling build job must use the full profiling CPU matrix', build_profiling_path)
    profiling_setup_step = workflow_step(build_profiling, build_profiling_path, 'build', 'Setup Shared Dependencies')
    if profiling_setup_step.get('uses') != './x265/.github/actions/setup-windows-deps':
        fail('Build Profiling Setup Shared Dependencies must use the setup-windows-deps action', build_profiling_path)
    profiling_setup_with = profiling_setup_step.get('with')
    if not isinstance(profiling_setup_with, dict):
        fail('Build Profiling Setup Shared Dependencies step must declare with inputs', build_profiling_path)
    if profiling_setup_with.get('ffmpeg-cache-suffix') != 'profiling-v1-clang':
        fail('Build Profiling Setup Shared Dependencies must pin ffmpeg-cache-suffix=profiling-v1-clang', build_profiling_path)
    ffmpeg_configure = profiling_setup_with.get('ffmpeg-configure')
    if not isinstance(ffmpeg_configure, str):
        fail('Build Profiling Setup Shared Dependencies must provide ffmpeg-configure', build_profiling_path)
    for required in (
        '--enable-avdevice',
        '--enable-avfilter',
        '--enable-ffmpeg',
        '--enable-indev=lavfi',
        'for f in testsrc testsrc2 smptebars smptehdbars nullsrc geq gradients format scale noise; do',
        '--enable-demuxer=mpegts,mov,matroska,h264,hevc,rawvideo,yuv4mpegpipe',
        '--enable-decoder=h264,hevc,ffv1,ffvhuff,huffyuv,rawvideo,wrapped_avframe,aac,ac3,mp3',
        '--enable-encoder=rawvideo,aac,ac3,mp2,pcm_s16le,pcm_s24le,pcm_s32le',
        '--enable-muxer=yuv4mpegpipe',
        '--enable-protocol=file,pipe',
    ):
        if required not in ffmpeg_configure:
            fail(f'Build Profiling FFmpeg config must enable dependency: {required}', build_profiling_path)
    if profiling_setup_with.get('use-mimalloc') != 'true':
        fail('Build Profiling Setup Shared Dependencies must keep mimalloc enabled', build_profiling_path)
    for step_name in ('Compress LLVM Profdata', 'Verify LLVM Profdata Artifact', 'Upload LLVM Profdata Artifact'):
        step = workflow_step(build_profiling, build_profiling_path, 'build', step_name)
        if step.get('if') != "matrix.target_cpu == 'x86-64'":
            fail(f'Build Profiling step {step_name} must run only for the x86-64 representative build', build_profiling_path)
    for step_name, profile_class in (
        ('Build 8b-lib Profiling Binaries', '8b-lib'),
        ('Build 12b-lib Profiling Binaries', '12b-lib'),
        ('Build All Profiling Binaries', 'all'),
    ):
        step = workflow_step(build_profiling, build_profiling_path, 'build', step_name)
        if step.get('uses') != './x265/.github/actions/build-x265-profiling':
            fail(f'Build Profiling step {step_name} must use the build-x265-profiling action', build_profiling_path)
        with_values = step.get('with')
        if not isinstance(with_values, dict):
            fail(f'Build Profiling step {step_name} must declare with inputs', build_profiling_path)
        for key, value in {
            'target-cpu': '${{ matrix.target_cpu }}',
            'profile-class': profile_class,
            'use-mimalloc': 'ON',
            'enable-lsmash': 'ON',
        }.items():
            if with_values.get(key) != value:
                fail(f'Build Profiling step {step_name} must set {key}={value}', build_profiling_path)

    latest_tag_lines = shell_active_logical_lines(
        workflow_step_run(build_profiling, build_profiling_path, 'build', 'Get Latest Tag')
    )
    for required, message in (
        ('source .github/scripts/ci_version_helpers.sh', 'Build Profiling Get Latest Tag must source the CI version helper'),
        ('version=$(x265_latest_numeric_tag)', 'Build Profiling Get Latest Tag must call x265_latest_numeric_tag'),
        ('echo "version=$version" >> "$GITHUB_OUTPUT"', 'Build Profiling Get Latest Tag must publish the selected version output'),
    ):
        require_active_line_contains(latest_tag_lines, required, build_profiling_path, message)

    ci_version_lines = shell_active_logical_lines(
        workflow_step_run(build_profiling, build_profiling_path, 'build', 'Get CI Version')
    )
    for required, message in (
        ('source .github/scripts/ci_version_helpers.sh', 'Build Profiling Get CI Version must source the CI version helper'),
        ('version=$(x265_ci_version_from_latest_tag "${{ steps.tag.outputs.version }}")', 'Build Profiling Get CI Version must call x265_ci_version_from_latest_tag with the latest tag output'),
        ('echo "version=$version" >> "$GITHUB_OUTPUT"', 'Build Profiling Get CI Version must publish the selected version output'),
    ):
        require_active_line_contains(ci_version_lines, required, build_profiling_path, message)

    package_version_lines = shell_active_logical_lines(
        workflow_step_run(build_profiling, build_profiling_path, 'build', 'Set Package Version')
    )
    for required, message in (
        ('source x265/.github/scripts/ci_version_helpers.sh', 'Build Profiling Set Package Version must source the CI version helper'),
        ('version=$(x265_package_version_for_event "${{ steps.tag.outputs.version }}" "${{ steps.ci_version.outputs.version }}")', 'Build Profiling Set Package Version must use x265_package_version_for_event with the tag and CI version outputs'),
        ('echo "version=$version" >> "$GITHUB_OUTPUT"', 'Build Profiling Set Package Version must publish the chosen version'),
    ):
        require_active_line_contains(package_version_lines, required, build_profiling_path, message)

    build_pgo_path = repo_root / BUILD_PGO_WORKFLOW
    pgo_guard_step = workflow_step(build_pgo, build_pgo_path, 'validate-guardrails', 'Check CI guardrails')
    if 'if' in pgo_guard_step:
        fail('Build PGO Check CI guardrails must not be step-gated', build_pgo_path)
    pgo_guard_lines = shell_active_logical_lines(
        workflow_step_run(build_pgo, build_pgo_path, 'validate-guardrails', 'Check CI guardrails')
    )
    require_active_exact_command(
        pgo_guard_lines,
        ('python', '.github/scripts/run_python_ci_guard_bundle.py', '--suite', 'pgo'),
        build_pgo_path,
        'Build PGO workflow guard bundle must run the exact Python CI guard bundle runner with --suite pgo without softening wrappers or extra flags',
    )
    pgo_publish_lines = shell_active_logical_lines(
        workflow_step_run(build_pgo, build_pgo_path, 'generate', 'Push Profdata to Branch')
    )
    require_active_exact_command(
        pgo_publish_lines,
        (
            'python',
            'x265/.github/scripts/check_profdata_metadata.py',
            '$profdata_push_dir/metadata.json',
            '--expected-cpu=$target_cpu',
            '--expected-target=$profile_target',
            '--expected-branch=$profdata_branch',
            '--expected-toolchain=$profdata_toolchain',
            '--current-commit=$source_commit',
            '--required-ffmpeg-cache-suffix=pgo-v1-clang',
            '--required-obuparse-cache-suffix=$obuparse_cache_suffix',
            '--required-lsmash-cache-suffix=$lsmash_cache_suffix',
            '--required-gop-muxer-cache-suffix=$gop_muxer_cache_suffix',
            '--require-target-cpu',
            '--require-dependency-fields',
            '--require-fresh-slot',
        ),
        build_pgo_path,
        'Build PGO profdata publish must run the exact metadata validation command without softening wrappers or extra flags',
    )

    release_step = workflow_step(build_profiling, build_profiling_path, 'publish-release', 'Release Profiling Artifacts')
    profiling_release_asset_lines = shell_active_logical_lines(
        workflow_step_run(build_profiling, build_profiling_path, 'publish-release', 'Validate Profiling Release Assets')
    )
    require_active_exact_command(
        profiling_release_asset_lines,
        ('bash', 'x265/.github/scripts/validate_release_assets.sh', 'profiling', 'release-assets', '${GITHUB_REF_NAME}'),
        build_profiling_path,
        'Build Profiling Validate Profiling Release Assets must run the shared profiling release asset validator without softening wrappers or extra flags',
    )
    release_with = release_step.get('with')
    if not isinstance(release_with, dict):
        fail('Build Profiling Release Profiling Artifacts step must declare with inputs', build_profiling_path)
    for key, value in {
        'tag_name': '${{ github.ref_name }}',
        'files': 'release-assets/**/*.7z',
        'fail_on_unmatched_files': True,
        'generate_release_notes': False,
        'prerelease': True,
    }.items():
        if release_with.get(key) != value:
            fail(f'Build Profiling Release Profiling Artifacts step must set {key}={value}', build_profiling_path)

    build_pgo_path = repo_root / BUILD_PGO_WORKFLOW
    pgo_jobs = workflow_jobs(build_pgo, build_pgo_path)
    if pgo_jobs.get('generate', {}).get('needs') != 'validate-guardrails':
        fail('Build PGO generate job must need validate-guardrails', build_pgo_path)

    pgo_on = workflow_on(build_pgo, build_pgo_path)
    workflow_dispatch = pgo_on.get('workflow_dispatch')
    if not isinstance(workflow_dispatch, dict):
        fail('Build PGO workflow must define workflow_dispatch inputs', build_pgo_path)
    inputs = workflow_dispatch.get('inputs')
    if not isinstance(inputs, dict):
        fail('Build PGO workflow_dispatch must define inputs', build_pgo_path)
    if 'target_cpu' in inputs:
        fail('Build PGO workflow_dispatch must not expose target_cpu input; generated PGO profdata is x86-64 baseline only', build_pgo_path)
    profile_target = inputs.get('profile_target')
    if not isinstance(profile_target, dict):
        fail('Build PGO workflow_dispatch must define profile_target input', build_pgo_path)
    if profile_target.get('default') != 'all':
        fail('Build PGO profile_target input must default to all', build_pgo_path)
    if profile_target.get('type') != 'choice':
        fail('Build PGO profile_target input must be a choice', build_pgo_path)
    if profile_target.get('options') != ['8b-lib', '12b-lib', 'all']:
        fail('Build PGO profile_target input must offer 8b-lib, 12b-lib, and all in order', build_pgo_path)

    pgo_concurrency = build_pgo.get('concurrency')
    if not isinstance(pgo_concurrency, dict):
        fail('Build PGO workflow must declare concurrency', build_pgo_path)
    if pgo_concurrency.get('group') != "${{ github.workflow }}-${{ github.ref }}-x86-64-${{ inputs.profile_target || 'all' }}":
        fail('Build PGO concurrency group must serialize by ref, x86-64 baseline, and profile_target', build_pgo_path)
    if pgo_concurrency.get('cancel-in-progress') is not False:
        fail('Build PGO concurrency must not cancel in-progress profdata publications', build_pgo_path)

    for job_name, expected_values in (
        ('validate-guardrails', {
            'fetch-depth': 0,
            'fetch-tags': True,
        }),
        ('generate', {
            'path': 'x265',
            'fetch-depth': 0,
            'fetch-tags': True,
        }),
    ):
        checkout_step = workflow_step(build_pgo, build_pgo_path, job_name, 'Checkout X265')
        if checkout_step.get('uses') != 'actions/checkout@v6':
            fail(f'Build PGO {job_name} Checkout X265 must use actions/checkout@v6', build_pgo_path)
        checkout_with = checkout_step.get('with')
        if not isinstance(checkout_with, dict):
            fail(f'Build PGO {job_name} Checkout X265 step must declare with inputs', build_pgo_path)
        for key, value in expected_values.items():
            if checkout_with.get(key) != value:
                fail(f'Build PGO {job_name} Checkout X265 must set {key}={value}', build_pgo_path)

    pgo_setup_step = workflow_step(build_pgo, build_pgo_path, 'generate', 'Setup Shared Dependencies')
    if pgo_setup_step.get('uses') != './x265/.github/actions/setup-windows-deps':
        fail('Build PGO Setup Shared Dependencies must use the setup-windows-deps action', build_pgo_path)
    pgo_setup_with = pgo_setup_step.get('with')
    if not isinstance(pgo_setup_with, dict):
        fail('Build PGO Setup Shared Dependencies step must declare with inputs', build_pgo_path)
    if pgo_setup_with.get('ffmpeg-cache-suffix') != 'pgo-v1-clang':
        fail('Build PGO Setup Shared Dependencies must pin ffmpeg-cache-suffix=pgo-v1-clang', build_pgo_path)
    ffmpeg_configure = pgo_setup_with.get('ffmpeg-configure')
    if not isinstance(ffmpeg_configure, str):
        fail('Build PGO Setup Shared Dependencies must provide ffmpeg-configure', build_pgo_path)
    for required in (
        '--enable-avdevice',
        '--enable-avfilter',
        '--enable-ffmpeg',
        '--enable-indev=lavfi',
        'for f in testsrc testsrc2 smptebars smptehdbars nullsrc mandelbrot life cellauto haldclutsrc; do',
        'for f in geq gradients format scale noise zoompan hue fps setpts drawbox overlay crop rotate transpose hflip vflip concat select; do',
        '--enable-demuxer=mpegts,mov,matroska,h264,hevc,rawvideo,yuv4mpegpipe',
        '--enable-decoder=h264,hevc,ffv1,ffvhuff,huffyuv,rawvideo,wrapped_avframe,aac,ac3,mp3',
        '--enable-encoder=rawvideo,aac,ac3,mp2,pcm_s16le,pcm_s24le,pcm_s32le',
        '--enable-muxer=yuv4mpegpipe',
        '--enable-protocol=file,pipe',
    ):
        if required not in ffmpeg_configure:
            fail(f'Build PGO FFmpeg config must enable dependency: {required}', build_pgo_path)
    if pgo_setup_with.get('use-mimalloc') != 'true':
        fail('Build PGO Setup Shared Dependencies must keep mimalloc enabled', build_pgo_path)

    build_pgo_step = workflow_step(build_pgo, build_pgo_path, 'generate', 'Build Profiling Binaries')
    if build_pgo_step.get('uses') != './x265/.github/actions/build-x265-profiling':
        fail('Build PGO Build Profiling Binaries must use the build-x265-profiling action', build_pgo_path)
    with_values = build_pgo_step.get('with')
    if not isinstance(with_values, dict):
        fail('Build PGO profiling action step is missing with inputs', build_pgo_path)
    for key, value in {
        'target-cpu': 'x86-64',
        'profile-class': "${{ inputs.profile_target || 'all' }}",
        'output-name': "x265-profiling-win64-x86-64-${{ inputs.profile_target || 'all' }}.exe",
        'use-mimalloc': 'ON',
        'enable-lsmash': 'ON',
        }.items():
        if with_values.get(key) != value:
            fail(f'Build PGO profiling action must set {key}={value}', build_pgo_path)

    pgo_publish_lines = shell_active_logical_lines(
        workflow_step_run(build_pgo, build_pgo_path, 'generate', 'Push Profdata to Branch')
    )
    for required, message in (
        ('llvm_profdata_version=$(llvm-profdata --version | sed -nE \'s/.*LLVM version ([0-9]+\\.[0-9]+).*/\\1/p\' | head -1)', 'Build PGO profdata publish must derive llvm_profdata_version from llvm-profdata --version'),
        ('test -n "$llvm_profdata_version"', 'Build PGO profdata publish must require a parsed llvm-profdata version before deriving the toolchain id'),
        ('profdata_toolchain="llvm-${llvm_profdata_version//[^A-Za-z0-9_.-]/_}"', 'Build PGO profdata publish must derive the profdata metadata toolchain id'),
        ('target_cpu=x86-64', 'Build PGO profdata publish must hard-code target_cpu=x86-64 because this workflow generates baseline profdata only'),
        ('profdata_branch="profdata-x86-64-${profile_target}"', 'Build PGO profdata publish must publish to x86-64 baseline profdata branches'),
        ('remote_url="https://x-access-token:${{ secrets.GITHUB_TOKEN }}@github.com/${{ github.repository }}.git"', 'Build PGO profdata publish must target the current repository with the GITHUB_TOKEN remote'),
        ('echo "Publishing profdata for CPU: $target_cpu"', 'Build PGO profdata publish must announce the target CPU'),
        ('copy_if_exists "profiles/0.profdata" "$profiles_dir/1.profdata"', 'Build PGO profdata publish must rotate previous fresh profile into slot 1'),
        ('copy_if_exists "profiles/1.profdata" "$profiles_dir/2.profdata"', 'Build PGO profdata publish must rotate profile slot 1 into slot 2'),
        ('copy_if_exists "profiles/2.profdata" "$profiles_dir/3.profdata"', 'Build PGO profdata publish must rotate profile slot 2 into slot 3'),
        ('fresh_profdata="$GITHUB_WORKSPACE/build/x265.profdata"', 'Build PGO profdata publish must source the fresh profdata from the workload output at $GITHUB_WORKSPACE/build/x265.profdata'),
        ('test -f "$fresh_profdata"', 'Build PGO profdata publish must require the fresh profdata artifact before rotating slots'),
        ('cp "$fresh_profdata" "$profiles_dir/0.profdata"', 'Build PGO profdata publish must place fresh profile data in slot 0'),
        ('for slot in 0 1 2 3; do', 'Build PGO profdata publish must keep a four-slot profile window'),
        ('merge_args+=("--weighted-input=$((4 - slot)),profiles/${slot}.profdata")', 'Build PGO profdata publish must weight newer profile slots more heavily'),
        ('ffmpeg_cache_suffix="pgo-v1-clang"', 'Build PGO profdata metadata must record the workflow-specific FFmpeg cache suffix'),
        ('test -n "$obuparse_cache_suffix"', 'Build PGO profdata publish must validate the workflow-specific obuparse cache suffix input'),
        ('test -n "$lsmash_cache_suffix"', 'Build PGO profdata publish must validate the workflow-specific L-SMASH cache suffix input'),
        ('test -n "$gop_muxer_cache_suffix"', 'Build PGO profdata publish must validate the workflow-specific GOP muxer cache suffix input'),
        ('source_commit=$(git -C "$GITHUB_WORKSPACE/x265" rev-parse HEAD)', 'Build PGO profdata publish must derive metadata source_commit from the checked-out x265 workspace'),
        ('source_ref=$(git -C "$GITHUB_WORKSPACE/x265" rev-parse --abbrev-ref HEAD || true)', 'Build PGO profdata publish must derive metadata source_ref from the checked-out x265 workspace'),
        ('if [ "$source_ref" = "HEAD" ]; then', 'Build PGO profdata publish must normalize detached HEAD source_ref values'),
        ('source_ref="${GITHUB_REF_NAME}"', 'Build PGO profdata publish must fall back to GITHUB_REF_NAME for detached HEAD source_ref values'),
        ('generated_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)', 'Build PGO profdata publish must timestamp metadata in UTC ISO-8601 form'),
        ('cat > "$profdata_push_dir/metadata.json" <<EOF', 'Build PGO profdata publish must write metadata.json into the publish directory'),
        ('"schema_version": 1,', 'Build PGO profdata metadata must declare schema_version 1'),
        ('"generated_at": "${generated_at}",', 'Build PGO profdata metadata must record the generated_at timestamp'),
        ('"repository": "${GITHUB_REPOSITORY}",', 'Build PGO profdata metadata must record the source repository'),
        ('"workflow": "${GITHUB_WORKFLOW}",', 'Build PGO profdata metadata must record the publishing workflow name'),
        ('"run_id": "${GITHUB_RUN_ID}",', 'Build PGO profdata metadata must record the publishing run_id'),
        ('"run_attempt": "${GITHUB_RUN_ATTEMPT}",', 'Build PGO profdata metadata must record the publishing run_attempt'),
        ('"source_ref": "${source_ref}",', 'Build PGO profdata metadata must record the normalized source_ref'),
        ('"source_commit": "${source_commit}",', 'Build PGO profdata metadata must record the publishing source_commit'),
        ('"target_cpu": "${target_cpu}",', 'Build PGO profdata metadata must record the target CPU'),
        ('"layout": "per-target-bounded-window",', 'Build PGO profdata metadata must declare the bounded per-target layout'),
        ('"weights_newest_to_oldest": [4, 3, 2, 1]', 'Build PGO profdata metadata must record the weighted merge policy'),
        ('python x265/.github/scripts/check_profdata_metadata.py "$profdata_push_dir/metadata.json"', 'Build PGO profdata publish must validate generated metadata with the profdata checker'),
        ('--expected-cpu="$target_cpu"', 'Build PGO profdata publish must validate metadata against the selected target CPU'),
        ('--expected-target="$profile_target"', 'Build PGO profdata publish must validate metadata against the selected profile target'),
        ('--current-commit="$source_commit"', 'Build PGO profdata publish must validate metadata against the published source commit'),
        ('--required-ffmpeg-cache-suffix=pgo-v1-clang', 'Build PGO profdata publish must validate the workflow-specific FFmpeg cache suffix'),
        ('--required-obuparse-cache-suffix="$obuparse_cache_suffix"', 'Build PGO profdata publish must validate the workflow-specific obuparse cache suffix'),
        ('--required-lsmash-cache-suffix="$lsmash_cache_suffix"', 'Build PGO profdata publish must validate the workflow-specific L-SMASH cache suffix'),
        ('--required-gop-muxer-cache-suffix="$gop_muxer_cache_suffix"', 'Build PGO profdata publish must validate the workflow-specific GOP muxer cache suffix'),
        ('--expected-branch="$profdata_branch"', 'Build PGO profdata publish must validate metadata against the computed branch'),
        ('--expected-toolchain="$profdata_toolchain"', 'Build PGO profdata publish must validate metadata against the computed LLVM toolchain'),
        ('--require-target-cpu', 'Build PGO profdata publish must require target CPU metadata fields'),
        ('--require-dependency-fields', 'Build PGO profdata publish must require dependency metadata fields'),
        ('--require-fresh-slot', 'Build PGO profdata publish must require the fresh profdata slot in metadata validation'),
        ('cp "$scratch_dir/x265.profdata" "$profdata_push_dir/x265.profdata"', 'Build PGO profdata publish must publish the merged bounded-window profdata artifact'),
        ('add_paths=(x265.profdata profiles metadata.json)', 'Build PGO profdata publish must stage exactly x265.profdata, profiles, and metadata.json'),
        ('git -C "$profdata_push_dir" add "${add_paths[@]}"', 'Build PGO profdata publish must add only the explicit profdata publish set'),
        ('if git -C "$profdata_push_dir" diff --cached --quiet; then', 'Build PGO profdata publish must skip branch updates when staged profdata is unchanged'),
        ('echo "No profdata changes to publish for $profile_target"', 'Build PGO profdata publish must announce unchanged profdata before exiting'),
        ('git -C "$profdata_push_dir" commit -m "Update PGO profdata ($profile_target) - $(date +%Y%m%d-%H%M)"', 'Build PGO profdata publish must create a profdata publication commit'),
        ('if [ "$latest_remote_tip" != "$remote_tip" ]; then', 'Build PGO profdata publish must detect remote branch advancement before pushing'),
        ('Remote profdata branch advanced while this run was publishing: $remote_tip -> $latest_remote_tip', 'Build PGO profdata publish must fail when the remote branch advanced mid-publication'),
        ('elif git -C "$profdata_push_dir" ls-remote --exit-code --heads origin "$profdata_branch" >/dev/null 2>&1; then', 'Build PGO profdata publish must detect a remote profdata branch that appears mid-publication'),
        ('Remote profdata branch appeared while this run was publishing: $profdata_branch', 'Build PGO profdata publish must fail when the remote profdata branch appears mid-publication'),
    ):
        require_active_line_contains(pgo_publish_lines, required, build_pgo_path, message)
    for required, message in (
        ('profdata_push_dir=$(mktemp -d)', 'Build PGO profdata publish must allocate an isolated temporary publish directory'),
        ('trap \'rm -rf "$profdata_push_dir"\' EXIT', 'Build PGO profdata publish must clean up the isolated temporary publish directory on exit'),
        ('git init "$profdata_push_dir"', 'Build PGO profdata publish must initialize an isolated publish repository'),
        ('git -C "$profdata_push_dir" config user.name "github-actions[bot]"', 'Build PGO profdata publish must set the isolated publish repository user.name to github-actions[bot]'),
        ('git -C "$profdata_push_dir" config user.email "github-actions[bot]@users.noreply.github.com"', 'Build PGO profdata publish must set the isolated publish repository user.email to github-actions[bot]@users.noreply.github.com'),
        ('git -C "$profdata_push_dir" remote add origin "$remote_url"', 'Build PGO profdata publish must bind the isolated publish repository to the computed remote'),
        ('remote_tip=$(git -C "$profdata_push_dir" rev-parse FETCH_HEAD)', 'Build PGO profdata publish must snapshot the pre-publication remote tip'),
        ('latest_remote_tip=$(git -C "$profdata_push_dir" rev-parse FETCH_HEAD)', 'Build PGO profdata publish must re-read the remote tip immediately before pushing'),
        ('if git -C "$profdata_push_dir" fetch origin "$profdata_branch" --depth=1; then', 'Build PGO profdata publish must fetch the computed profdata branch before deciding whether it exists'),
        ('git -C "$profdata_push_dir" checkout -B "$profdata_branch" FETCH_HEAD', 'Build PGO profdata publish must reuse the fetched profdata branch tip when it exists'),
        ('git -C "$profdata_push_dir" checkout --orphan "$profdata_branch"', 'Build PGO profdata publish must create a clean orphan profdata branch when none exists'),
        ('git -C "$profdata_push_dir" rm -rf . >/dev/null 2>&1 || true', 'Build PGO profdata publish must remove tracked files from an existing profdata branch before repopulating it'),
        ('scratch_dir="$profdata_push_dir/.window"', 'Build PGO profdata publish must stage bounded-window scratch state under the isolated publish directory'),
        ('profiles_dir="$scratch_dir/profiles"', 'Build PGO profdata publish must derive the bounded-window profiles directory from scratch_dir'),
        ('mkdir -p "$profiles_dir"', 'Build PGO profdata publish must create the bounded-window scratch profiles directory before rotation'),
        ('cd "$scratch_dir"', 'Build PGO profdata publish must merge profdata from the bounded-window scratch directory'),
        ('merge_args=()', 'Build PGO profdata publish must build the bounded-window merge input list from scratch'),
        ('test "${#merge_args[@]}" -gt 0', 'Build PGO profdata publish must require at least one profdata input before merging'),
        ('llvm-profdata merge -o x265.profdata "${merge_args[@]}"', 'Build PGO profdata publish must merge the bounded-window profdata inputs into x265.profdata'),
        ('llvm-profdata show x265.profdata >/dev/null', 'Build PGO profdata publish must validate the merged profdata artifact before publication'),
        ('setup_deps_action="$GITHUB_WORKSPACE/x265/.github/actions/setup-windows-deps/action.yml"', 'Build PGO profdata publish must load dependency defaults from the checked-out setup-windows-deps action'),
        ('git -C "$profdata_push_dir" fetch origin "$profdata_branch" --depth=1', 'Build PGO profdata publish must refetch the computed profdata branch immediately before the remote advancement check'),
    ):
        matches = [index for index, line in enumerate(pgo_publish_lines) if line == required]
        if len(matches) != 1:
            fail(message, build_pgo_path)
    action_default_indexes = [index for index, line in enumerate(pgo_publish_lines) if line == 'action_default() {']
    if len(action_default_indexes) != 1:
        fail('Build PGO profdata publish must define a single action_default helper', build_pgo_path)
    for required, message in (
        ('ffmpeg_ref=$(action_default "$setup_deps_action" ffmpeg-ref)', 'Build PGO profdata publish must source ffmpeg_ref from the setup-windows-deps action defaults'),
        ('mimalloc_ref=$(action_default "$setup_deps_action" mimalloc-ref)', 'Build PGO profdata publish must source mimalloc_ref from the setup-windows-deps action defaults'),
        ('obuparse_ref=$(action_default "$setup_deps_action" obuparse-ref)', 'Build PGO profdata publish must source obuparse_ref from the setup-windows-deps action defaults'),
        ('obuparse_cache_suffix=$(action_default "$setup_deps_action" obuparse-cache-suffix)', 'Build PGO profdata publish must source obuparse_cache_suffix from the setup-windows-deps action defaults'),
        ('lsmash_repository=$(action_default "$setup_deps_action" lsmash-repository)', 'Build PGO profdata publish must source lsmash_repository from the setup-windows-deps action defaults'),
        ('lsmash_ref=$(action_default "$setup_deps_action" lsmash-ref)', 'Build PGO profdata publish must source lsmash_ref from the setup-windows-deps action defaults'),
        ('lsmash_cache_suffix=$(action_default "$setup_deps_action" lsmash-cache-suffix)', 'Build PGO profdata publish must source lsmash_cache_suffix from the setup-windows-deps action defaults'),
        ('gop_muxer_repository=$(action_default "$setup_deps_action" gop-muxer-repository)', 'Build PGO profdata publish must source gop_muxer_repository from the setup-windows-deps action defaults'),
        ('gop_muxer_ref=$(action_default "$setup_deps_action" gop-muxer-ref)', 'Build PGO profdata publish must source gop_muxer_ref from the setup-windows-deps action defaults'),
        ('gop_muxer_cache_suffix=$(action_default "$setup_deps_action" gop-muxer-cache-suffix)', 'Build PGO profdata publish must source gop_muxer_cache_suffix from the setup-windows-deps action defaults'),
    ):
        matches = [index for index, line in enumerate(pgo_publish_lines) if line == required]
        if len(matches) != 1:
            fail(message, build_pgo_path)
    for required, message in (
        ('copy_if_exists() {', 'Build PGO profdata publish must define a single copy_if_exists helper'),
        ('local source_path="$1"', 'Build PGO profdata publish copy_if_exists helper must bind the source path argument'),
        ('local destination_path="$2"', 'Build PGO profdata publish copy_if_exists helper must bind the destination path argument'),
        ('if [ -f "$profdata_push_dir/$source_path" ]; then', 'Build PGO profdata publish copy_if_exists helper must read only from the isolated publish directory'),
        ('mkdir -p "$(dirname "$destination_path")"', 'Build PGO profdata publish copy_if_exists helper must create parent directories for rotated profiles'),
        ('cp "$profdata_push_dir/$source_path" "$destination_path"', 'Build PGO profdata publish copy_if_exists helper must copy rotated profiles from the isolated publish directory'),
        ('local action_file="$1"', 'Build PGO profdata publish action_default helper must bind the action file argument'),
        ('local input_name="$2"', 'Build PGO profdata publish action_default helper must bind the input name argument'),
        ('awk -v input="  ${input_name}:" \'', 'Build PGO profdata publish action_default helper must anchor parsing on the requested input name'),
        ('$0 == input { in_input = 1; next }', 'Build PGO profdata publish action_default helper must begin parsing only at the requested input entry'),
        ('in_input && /^  [^[:space:]].*:$/ { exit }', 'Build PGO profdata publish action_default helper must stop parsing at the next top-level input entry'),
        ('in_input && /^[[:space:]]+default:/ { print $2; exit }', 'Build PGO profdata publish action_default helper must emit the default value token for the requested input'),
        ('\' "$action_file"', 'Build PGO profdata publish action_default helper must parse the requested action file'),
    ):
        matches = [index for index, line in enumerate(pgo_publish_lines) if line == required]
        if len(matches) != 1:
            fail(message, build_pgo_path)
    cleanup_line = 'find "$profdata_push_dir" -mindepth 1 -maxdepth 1 ! -name .git ! -name .window -exec rm -rf {} +'
    cleanup_matches = [index for index, line in enumerate(pgo_publish_lines) if line == cleanup_line]
    if len(cleanup_matches) != 2:
        fail('Build PGO profdata publish must clear non-git branch contents on both existing and new branch paths', build_pgo_path)
    slot_loop_line = 'for slot in 0 1 2 3; do'
    slot_loop_matches = [index for index, line in enumerate(pgo_publish_lines) if line == slot_loop_line]
    if len(slot_loop_matches) != 2:
        fail('Build PGO profdata publish must keep four-slot loops for both merge inputs and published profile copies', build_pgo_path)
    for required, message in (
        ('mkdir -p "$profdata_push_dir/profiles"', 'Build PGO profdata publish must create the published profiles directory before copying profile slots'),
        ('if [ -f "$profiles_dir/${slot}.profdata" ]; then', 'Build PGO profdata publish must only republish bounded-window slots that exist after rotation'),
        ('cp "$profiles_dir/${slot}.profdata" "$profdata_push_dir/profiles/${slot}.profdata"', 'Build PGO profdata publish must republish rotated profile slots from the bounded-window scratch directory'),
    ):
        matches = [index for index, line in enumerate(pgo_publish_lines) if line == required]
        if len(matches) != 1:
            fail(message, build_pgo_path)
    require_active_exact_command(
        pgo_publish_lines,
        (
            'git',
            '-C',
            '$profdata_push_dir',
            'push',
            'origin',
            'HEAD:$profdata_branch',
        ),
        build_pgo_path,
        'Build PGO profdata publish must run the exact push command to the computed profdata branch without force or extra flags',
    )

    profiling_action_path = repo_root / BUILD_PROFILING_ACTION
    profiling_action = load_yaml(repo_root, BUILD_PROFILING_ACTION)
    action_inputs = profiling_action.get('inputs')
    if not isinstance(action_inputs, dict):
        fail('Build Profiling action must define inputs', profiling_action_path)

    def action_input_default(input_name):
        input_data = action_inputs.get(input_name)
        if not isinstance(input_data, dict):
            fail(f'Build Profiling action must define input: {input_name}', profiling_action_path)
        default = input_data.get('default')
        if not isinstance(default, str):
            fail(f'Build Profiling action input {input_name} must define a string default', profiling_action_path)
        try:
            return shlex.split(default)
        except ValueError as exc:
            fail(f'Build Profiling action input {input_name} default is not shell-parseable: {exc}', profiling_action_path)

    profiling_flags = action_input_default('profiling-cxx-flags')
    for required in ('-fprofile-instr-generate', '-fprofile-update=atomic'):
        if required not in profiling_flags:
            fail(f'Build Profiling action profiling-cxx-flags default must include {required}', profiling_action_path)
    if any(flag == '-fprofile-instr-use' or flag.startswith('-fprofile-instr-use=') for flag in profiling_flags):
        fail('Build Profiling action profiling-cxx-flags default must not include PGO consume flags', profiling_action_path)

    common_flags = action_input_default('common-cxx-flags')
    if any(
        flag in ('-fprofile-instr-generate', '-fprofile-update=atomic', '-fprofile-instr-use')
        or flag.startswith('-fprofile-instr-use=')
        for flag in common_flags
    ):
        fail('Build Profiling action common-cxx-flags default must not include profiling instrumentation or consume flags', profiling_action_path)

    validate_required_action_steps(repo_root, BUILD_PROFILING_ACTION, 'Build Profiling action guard', (
        ('Build 8b-lib profiling CLI', REQUIRED_BUILD_PROFILING_ACTION_SNIPPETS + ('8b-lib',)),
        ('Build 12b-lib profiling CLI', REQUIRED_BUILD_PROFILING_ACTION_SNIPPETS + ('12b-lib',)),
        ('Build all profiling CLI', REQUIRED_BUILD_PROFILING_ACTION_SNIPPETS + ('all',)),
    ))
    validate_build_profiling_helper(repo_root, bash)
    validate_ci_version_helper(repo_root, bash)
    validate_release_asset_validator(repo_root, bash)
    validate_required_action_steps(repo_root, WINDOWS_DEPS_ACTION, 'setup-windows-deps guard', (
        ('Verify MSYS2 Toolchain', (
            REQUIRED_WINDOWS_DEPS_ACTION_SNIPPETS[0],
            REQUIRED_WINDOWS_DEPS_ACTION_SNIPPETS[1],
            REQUIRED_WINDOWS_DEPS_ACTION_SNIPPETS[2],
            REQUIRED_WINDOWS_DEPS_ACTION_SNIPPETS[3],
            REQUIRED_WINDOWS_DEPS_ACTION_SNIPPETS[7],
            REQUIRED_WINDOWS_DEPS_ACTION_SNIPPETS[8],
        )),
        ('Install Cached FFmpeg', REQUIRED_WINDOWS_DEPS_ACTION_SNIPPETS[4:6]),
        ('Verify FFmpeg Install', REQUIRED_WINDOWS_DEPS_ACTION_SNIPPETS[6:7]),
        ('Compile L-SMASH', REQUIRED_WINDOWS_DEPS_ACTION_SNIPPETS[9:13]),
        ('Compile GOP muxer', REQUIRED_WINDOWS_DEPS_ACTION_SNIPPETS[13:16]),
        ('Compile mimalloc', REQUIRED_WINDOWS_DEPS_ACTION_SNIPPETS[16:18]),
        ('Verify mimalloc Install', REQUIRED_WINDOWS_DEPS_ACTION_SNIPPETS[18:]),
    ))
    print('Required CI guard steps validated')


def validate_build_pr_fast_gate(repo_root):
    build_path = repo_root / BUILD_WORKFLOW
    parsed = load_yaml(repo_root, BUILD_WORKFLOW)
    on_block = workflow_on(parsed, build_path)
    pull_request = on_block.get('pull_request')
    if not isinstance(pull_request, dict):
        fail('Build workflow must define pull_request trigger for pre-merge CI', build_path)
    branches = pull_request.get('branches')
    if branches != ['**']:
        fail('Build workflow pull_request trigger must cover all target branches', build_path)
    paths = pull_request.get('paths')
    if not isinstance(paths, list):
        fail('Build workflow pull_request trigger must use paths filtering', build_path)
    missing_paths = [path for path in PR_TRIGGER_PATHS if path not in paths]
    if missing_paths:
        fail(f'Build workflow pull_request paths missing: {", ".join(missing_paths)}', build_path)

    jobs = workflow_jobs(parsed, build_path)
    build_metadata = jobs.get('build-metadata')
    if not isinstance(build_metadata, dict):
        fail('Build workflow must include build-metadata job', build_path)

    for job_name in PR_SKIPPED_BUILD_JOBS:
        job = jobs.get(job_name)
        if not isinstance(job, dict):
            fail(f'missing workflow job: {job_name}', build_path)
        if job.get('if') != "github.event_name != 'pull_request'":
            fail(f'Build workflow job {job_name} must be skipped for pull_request fast gate', build_path)

    linux_gcc = jobs.get('cxx20-linux-gcc-compile-commands')
    if not isinstance(linux_gcc, dict):
        fail('missing workflow job: cxx20-linux-gcc-compile-commands', build_path)
    if linux_gcc.get('if') is not None:
        fail('Build workflow job cxx20-linux-gcc-compile-commands must run for pull_request fast gate', build_path)

    windows_gcc = jobs.get('cxx20-gcc-compile-commands')
    if not isinstance(windows_gcc, dict):
        fail('missing workflow job: cxx20-gcc-compile-commands', build_path)
    if windows_gcc.get('if') is not None:
        fail('Build workflow job cxx20-gcc-compile-commands must run for pull_request fast gate', build_path)

    if build_metadata.get('runs-on') != 'ubuntu-latest':
        fail('build-metadata must run on ubuntu-latest', build_path)

    metadata_outputs = build_metadata.get('outputs')
    if not isinstance(metadata_outputs, dict):
        fail('build-metadata must expose outputs', build_path)
    if metadata_outputs.get('latest_tag') != '${{ steps.tag.outputs.version }}':
        fail('build-metadata must expose latest_tag from Get Latest Tag output', build_path)
    if metadata_outputs.get('ci_version') != '${{ steps.ci_version.outputs.version }}':
        fail('build-metadata must expose ci_version from Get CI Version output', build_path)

    ci_guardrails = jobs.get('validate-ci-guardrails')
    if not isinstance(ci_guardrails, dict):
        fail('missing workflow job: validate-ci-guardrails', build_path)
    if ci_guardrails.get('needs') is not None:
        fail('validate-ci-guardrails must run independently of build gates', build_path)
    if ci_guardrails.get('runs-on') != 'ubuntu-latest':
        fail('validate-ci-guardrails must run on ubuntu-latest', build_path)

    build_job = jobs.get('build')
    if not isinstance(build_job, dict):
        fail('missing workflow job: build', build_path)
    build_needs = build_job.get('needs')
    if build_needs != ['validate-deps-cache-suffix', 'build-metadata']:
        fail('Build workflow job build must need validate-deps-cache-suffix and build-metadata', build_path)

    sanitizer = jobs.get('linux-clang-sanitizers')
    if not isinstance(sanitizer, dict):
        fail('Build workflow must include linux-clang-sanitizers PR fast gate job', build_path)
    if sanitizer.get('if') is not None:
        fail('linux-clang-sanitizers must run for pull_request and non-PR events', build_path)
    if sanitizer.get('needs') != 'validate-deps-cache-suffix':
        fail('linux-clang-sanitizers must need validate-deps-cache-suffix', build_path)
    if sanitizer.get('runs-on') != 'ubuntu-latest':
        fail('linux-clang-sanitizers must run on ubuntu-latest', build_path)

    active_lines = shell_active_logical_lines(workflow_step_run(
        parsed,
        build_path,
        'linux-clang-sanitizers',
        'Build and smoke-test with ASan and UBSan',
    ))
    for required, message in {
        'if [ "${{ github.event_name }}" = "pull_request" ]; then': 'sanitizer job must branch on pull_request for fast gate mode',
        'min_cpp_commands=50': 'sanitizer PR fast gate must use reduced compile-command threshold',
        'enable_hdr10_plus=OFF': 'sanitizer PR fast gate must disable HDR10+ for speed',
        'build_dir=build/linux-clang-sanitizers-pr': 'sanitizer PR fast gate must use separate build directory',
        'min_cpp_commands=60': 'sanitizer non-PR mode must keep full compile-command threshold',
        'enable_hdr10_plus=ON': 'sanitizer non-PR mode must keep HDR10+ coverage',
        '-DFSANITIZE=address,undefined': 'sanitizer job must enable ASan and UBSan',
        'ninja -C "$build_dir" cli': 'sanitizer job must build the CLI target',
        'grep -Fq \'encoded 1 frames\' "$build_dir"/"$smoke_prefix".log': 'sanitizer job must require encoded-frame smoke log',
        'runtime error:|ERROR: AddressSanitizer|SUMMARY: AddressSanitizer': 'sanitizer job must fail on ASan/UBSan reports',
    }.items():
        if not any(required in line for line in active_lines):
            fail(message, build_path)

    publish = jobs.get('publish-release')
    if not isinstance(publish, dict):
        fail('missing workflow job: publish-release', build_path)
    needs = publish.get('needs')
    if not isinstance(needs, list):
        fail('publish-release job must have an explicit needs list', build_path)
    if publish.get('if') != "startsWith(github.ref, 'refs/tags/')":
        fail('publish-release must only run for tag refs', build_path)
    validate_release_tag_lines = shell_active_logical_lines(workflow_step_run(parsed, build_path, 'publish-release', 'Validate Release Tag'))
    for required in (
        'refs/tags/[0-9].[0-9]*) ;;',
        'Release artifacts require a numeric version tag',
    ):
        require_active_line_contains(validate_release_tag_lines, required, build_path, f'publish-release Validate Release Tag must include: {required}')
    if 'linux-clang-sanitizers' in needs:
        fail('publish-release must not depend on PR fast-gate sanitizer job', build_path)
    for required in ('validate-ci-guardrails', 'cxx20-warning-scan', 'cxx20-gcc-compile-commands', 'cxx20-linux-gcc-compile-commands', 'build-metadata', 'build'):
        if required not in needs:
            fail(f'publish-release must depend on full-gate job: {required}', build_path)
    print('Build PR fast-gate structure validated')


def validate_warning_scan_dependencies(repo_root):
    build_path = repo_root / BUILD_WORKFLOW
    parsed = load_yaml(repo_root, BUILD_WORKFLOW)
    setup_step = workflow_step(parsed, build_path, 'cxx20-warning-scan', 'Setup Shared Dependencies')
    with_values = setup_step.get('with')
    if not isinstance(with_values, dict):
        fail('C++20 warning scan dependency setup is missing with inputs', build_path)
    if with_values.get('extra-msys2-packages') != '':
        fail('C++20 warning scan dependency setup must keep extra-msys2-packages empty for shared CLANG64 cache reuse', build_path)
    if with_values.get('ffmpeg-cache-suffix') != 'lavf-v4-clang':
        fail('C++20 warning scan dependency setup must pin ffmpeg-cache-suffix=lavf-v4-clang', build_path)
    full_scan_toggle = '${{ env.CI_FULL_EVENT }}'
    if with_values.get('use-ffmpeg') != full_scan_toggle:
        fail('C++20 warning scan dependency setup must enable FFmpeg only for manual/tag full scans', build_path)
    if with_values.get('use-obuparse') != full_scan_toggle:
        fail('C++20 warning scan dependency setup must enable obuparse only for manual/tag full scans', build_path)
    if with_values.get('use-lsmash') != full_scan_toggle:
        fail('C++20 warning scan dependency setup must enable L-SMASH only for manual/tag full scans', build_path)
    ffmpeg_configure = with_values.get('ffmpeg-configure')
    if not isinstance(ffmpeg_configure, str):
        fail('C++20 warning scan dependency setup must provide ffmpeg-configure', build_path)
    for required in (
        '--enable-avformat',
        '--enable-avcodec',
        '--enable-avutil',
        '--enable-swscale',
        '--enable-demuxer=mov,matroska,mpegts,avi,mpegvideo,m4v,mpeg,ogg,asf',
        '--enable-decoder=h264,hevc,ffv1,ffvhuff,huffyuv,rawvideo,wrapped_avframe,aac,ac3,mp3',
        '--enable-protocol=file',
    ):
        if required not in ffmpeg_configure:
            fail(f'C++20 warning scan FFmpeg config must enable compile dependency: {required}', build_path)
    for forbidden in (
        '--enable-ffmpeg',
        '--enable-ffprobe',
        '--enable-avdevice',
        '--enable-avfilter',
        '--enable-indev=lavfi',
        '--enable-filter=testsrc2',
        '--enable-parser=h264,hevc',
        '--enable-encoder=wrapped_avframe,ffv1,rawvideo',
        '--enable-muxer=matroska,rawvideo,yuv4mpegpipe',
        '--enable-demuxer=mov,matroska,mpegts,avi,mpegvideo,m4v,mpeg,ogg,asf,yuv4mpegpipe,hevc',
    ):
        if forbidden in ffmpeg_configure:
            fail(f'C++20 warning scan FFmpeg config must stay lightweight and omit: {forbidden}', build_path)

    install_lines = shell_active_logical_lines(workflow_step_run(
        parsed,
        build_path,
        'cxx20-warning-scan',
        'Install ZIMG for warning scan',
    ))
    require_active_line_contains(
        install_lines,
        'pacman -S --needed --noconfirm mingw-w64-clang-x86_64-zimg',
        build_path,
        'C++20 warning scan must install mingw-w64-clang-x86_64-zimg in a dedicated warning-scan step',
    )
    require_active_line_contains(
        install_lines,
        'mingw-w64-clang-x86_64-ffmpeg',
        build_path,
        'C++20 warning scan must install MSYS2 FFmpeg CLI for full-scan seed MP4 generation',
    )
    print('C++20 warning scan dependency setup validated')


def validate_windows_gcc_diagnostics_setup(repo_root):
    build_path = repo_root / BUILD_WORKFLOW
    parsed = load_yaml(repo_root, BUILD_WORKFLOW)
    step = workflow_step(parsed, build_path, 'cxx20-gcc-compile-commands', 'Setup GCC diagnostics')
    with_values = step.get('with')
    if not isinstance(with_values, dict):
        fail('Windows GCC diagnostics setup is missing with inputs', build_path)
    if with_values.get('msystem') != 'MINGW64':
        fail('Windows GCC diagnostics setup must run under MINGW64', build_path)
    packages = with_values.get('install')
    if not isinstance(packages, str):
        fail('Windows GCC diagnostics setup must declare an MSYS2 install package list', build_path)
    package_set = set(packages.split())
    for required in (
        'git',
        'mingw-w64-x86_64-cmake',
        'mingw-w64-x86_64-gcc',
        'mingw-w64-x86_64-ninja',
        'mingw-w64-x86_64-python',
    ):
        if required not in package_set:
            fail(f'Windows GCC diagnostics setup must install {required}', build_path)
    for forbidden in ('make', 'nasm', 'pkgconf'):
        if forbidden in package_set:
            fail(f'Windows GCC diagnostics setup must not install unused MSYS2 package {forbidden}', build_path)
    print('Windows GCC diagnostics setup validated')


def validate_job_timeouts(repo_root):
    for relative_path in (BUILD_WORKFLOW, BUILD_PROFILING_WORKFLOW, BUILD_PGO_WORKFLOW, UPDATE_DEPS_WORKFLOW):
        path = repo_root / relative_path
        jobs = workflow_jobs(load_yaml(repo_root, relative_path), path)
        for job_name, job in jobs.items():
            if not isinstance(job, dict):
                fail(f'workflow job {job_name} must map to a job definition', path)
            timeout = job.get('timeout-minutes')
            if not isinstance(timeout, int) or timeout <= 0:
                fail(f'{path.name} job {job_name} must declare a positive timeout-minutes', path)
    print('Workflow job timeouts validated')


def validate_update_deps_concurrency(repo_root):
    path = repo_root / UPDATE_DEPS_WORKFLOW
    parsed = load_yaml(repo_root, UPDATE_DEPS_WORKFLOW)
    concurrency = parsed.get('concurrency')
    if not isinstance(concurrency, dict):
        fail('Update-deps workflow must declare concurrency', path)
    if concurrency.get('group') != '${{ github.workflow }}-${{ github.ref }}':
        fail('Update-deps workflow concurrency group must serialize by workflow/ref', path)
    if concurrency.get('cancel-in-progress') is not False:
        fail('Update-deps workflow concurrency must not cancel in-progress runs', path)
    print('Update-deps concurrency validated')


def validate_build_workflow_concurrency(repo_root):
    path = repo_root / BUILD_WORKFLOW
    parsed = load_yaml(repo_root, BUILD_WORKFLOW)
    concurrency = parsed.get('concurrency')
    if not isinstance(concurrency, dict):
        fail('Build workflow must declare concurrency', path)
    if concurrency.get('group') != '${{ github.workflow }}-${{ github.ref }}':
        fail('Build workflow concurrency group must serialize by workflow/ref', path)
    expected_cancel = "${{ github.event_name == 'push' && !startsWith(github.ref, 'refs/tags/') }}"
    if concurrency.get('cancel-in-progress') != expected_cancel:
        fail('Build workflow concurrency must cancel in-progress runs only for non-tag push events', path)
    workflow_env = parsed.get('env')
    if not isinstance(workflow_env, dict):
        fail('Build workflow must declare top-level env', path)
    if workflow_env.get('CI_FULL_EVENT') != FULL_EVENT_ENV_VALUE:
        fail('Build workflow env must define CI_FULL_EVENT for workflow_dispatch/tag full builds', path)
    print('Build workflow concurrency validated')


def validate_build_matrix_scope(repo_root):
    path = repo_root / BUILD_WORKFLOW
    parsed = load_yaml(repo_root, BUILD_WORKFLOW)
    jobs = workflow_jobs(parsed, path)
    build_job = jobs.get('build')
    if not isinstance(build_job, dict):
        fail('missing workflow job: build', path)

    strategy = build_job.get('strategy')
    if not isinstance(strategy, dict):
        fail('Build workflow job build must define a strategy matrix', path)
    if strategy.get('fail-fast') is not False:
        fail('Build workflow job build must set strategy.fail-fast to false so one CPU failure cannot cancel remaining dependency-coverage legs', path)
    matrix = strategy.get('matrix')
    if not isinstance(matrix, dict):
        fail('Build workflow job build must define a strategy.matrix mapping', path)

    target_cpu = matrix.get('target_cpu')
    expected = "${{ fromJSON((github.event_name == 'workflow_dispatch' || startsWith(github.ref, 'refs/tags/')) && '[\"x86-64\",\"haswell\",\"skylake\",\"alderlake\",\"raptorlake\",\"arrowlake\",\"znver2\",\"znver3\",\"znver4\",\"znver5\"]' || '[\"x86-64\",\"haswell\",\"alderlake\",\"znver4\"]') }}"
    if target_cpu != expected:
        fail('Build workflow job build must use representative push CPU matrix and full tag/workflow_dispatch matrix', path)
    print('Build matrix scope validated')


def validate_checkout_scope(repo_root):
    path = repo_root / BUILD_WORKFLOW
    parsed = load_yaml(repo_root, BUILD_WORKFLOW)
    jobs = workflow_jobs(parsed, path)

    def expect_sparse(job_name, expected):
        step = workflow_step(parsed, path, job_name, 'Checkout X265')
        with_values = step.get('with')
        if not isinstance(with_values, dict):
            fail(f'{job_name} Checkout X265 step is missing with inputs', path)
        if with_values.get('fetch-depth') != 1:
            fail(f'{job_name} Checkout X265 must use fetch-depth: 1', path)
        if with_values.get('sparse-checkout') != expected:
            fail(f'{job_name} Checkout X265 must use sparse-checkout {expected!r}', path)

    common_sparse = '.\n.github\nsource\n'
    expect_sparse('validate-ci-guardrails', common_sparse)
    expect_sparse('validate-deps-cache-suffix', '.github\n')
    expect_sparse('cxx20-warning-scan', common_sparse)
    expect_sparse('cxx20-gcc-compile-commands', common_sparse)
    expect_sparse('cxx20-linux-gcc-compile-commands', common_sparse)
    expect_sparse('linux-clang-sanitizers', common_sparse)
    expect_sparse('build', common_sparse)
    expect_sparse('build-metadata', '.\n.github\n')

    metadata_step = workflow_step(parsed, path, 'build-metadata', 'Checkout X265')
    metadata_with = metadata_step.get('with')
    if metadata_with.get('fetch-tags') is not True:
        fail('build-metadata Checkout X265 must enable fetch-tags', path)
    print('Checkout scope validated')


def validate_metadata_history_scope(repo_root, bash):
    path = repo_root / BUILD_WORKFLOW
    parsed = load_yaml(repo_root, BUILD_WORKFLOW)
    validate_ci_version_helper(repo_root, bash)

    diff_lines = shell_active_logical_lines(workflow_step_run(parsed, path, 'validate-deps-cache-suffix', 'Check dependency patch cache suffixes'))
    for required in (
        'if [ "${{ github.event_name }}" != "push" ] || [[ "$before" =~ ^0+$ ]]; then',
        'echo "No push diff to validate"',
        'echo "Before commit unavailable locally; fetching before commit"',
        'git fetch --no-tags --depth=1 origin "$before"',
        'echo "Before commit fetch failed; skipping patch suffix diff validation"',
        'echo "Before commit still unavailable after fetch; skipping patch suffix diff validation"',
        'python .github/scripts/check_dependency_patch_suffixes.py --before "$before" --after "$after"',
    ):
        require_active_line_contains(diff_lines, required, path, f'validate-deps-cache-suffix diff fallback must include: {required}')
    if diff_lines.count('if ! git cat-file -e "$before^{commit}" 2>/dev/null; then') != 2:
        fail('validate-deps-cache-suffix diff fallback must check before commit availability before and after fetch', path)
    require_active_exact_command(
        diff_lines,
        ('python', '.github/scripts/check_dependency_patch_suffixes.py', '--before', '$before', '--after', '$after'),
        path,
        'validate-deps-cache-suffix diff fallback must run the exact before/after dependency suffix command without permissive extra flags',
    )

    latest_tag_lines = shell_active_logical_lines(workflow_step_run(parsed, path, 'build-metadata', 'Get Latest Tag'))
    for required in (
        'source .github/scripts/ci_version_helpers.sh',
        'version=$(x265_latest_numeric_tag)',
        'echo "version=$version" >> "$GITHUB_OUTPUT"',
    ):
        require_active_line_contains(latest_tag_lines, required, path, f'build-metadata Get Latest Tag must include: {required}')

    ci_version_lines = shell_active_logical_lines(workflow_step_run(parsed, path, 'build-metadata', 'Get CI Version'))
    for required in (
        'source .github/scripts/ci_version_helpers.sh',
        'version=$(x265_ci_version_from_latest_tag "${{ steps.tag.outputs.version }}")',
        'echo "version=$version" >> "$GITHUB_OUTPUT"',
    ):
        require_active_line_contains(ci_version_lines, required, path, f'build-metadata Get CI Version must include: {required}')
    print('Metadata history scope validated')


def validate_pgo_fetch_scope(repo_root):
    path = repo_root / BUILD_WORKFLOW
    parsed = load_yaml(repo_root, BUILD_WORKFLOW)
    active_lines = shell_active_logical_lines(workflow_step_run(parsed, path, 'build', 'Fetch PGO Profdata'))
    required_lines = (
        'if [ "${CI_FULL_EVENT}" = \'true\' ]; then',
        'current_toolchain="llvm-${llvm_profdata_version//[^A-Za-z0-9_.-]/_}"',
        'fetch_output=$(timeout 180s git -c http.lowSpeedLimit=1024 -c http.lowSpeedTime=30 fetch --quiet origin "$branch" --depth=1 2>&1)',
        'echo "::warning::PGO profdata fetch timed out: target=${target} branch=${branch} after 180s"',
        'echo "PGO profdata fetch timed out: target=${target} branch=${branch} after 180s"',
        'echo "::warning::PGO profdata fetch failed: target=${target} branch=${branch} status=${fetch_status}"',
        'echo "PGO profdata fetch failed: target=${target} branch=${branch} status=${fetch_status}"',
        'summary_note="fetch failed with status ${fetch_status}"',
        'echo "::warning::PGO profdata unavailable: target=${target} branch=${branch}"',
        'echo "PGO profdata unavailable: target=${target} branch=${branch}"',
        'if ! metadata_check_output=$(python .github/scripts/check_profdata_metadata.py "$metadata_path" "${metadata_check_args[@]}" 2>&1); then',
        'printf \'%s\\n\' "$metadata_check_output" | sed \'s/^::warning::/PGO fallback probe warning: /\'',
        'if [ "$report_unavailable" = true ] && [ -n "${GITHUB_STEP_SUMMARY:-}" ]; then',
        '--expected-cpu="$expected_cpu"',
        '--expected-target="$target"',
        '--expected-branch="$branch"',
        '--current-commit="${{ github.sha }}"',
        'local is_cpu_specific_profdata=false',
        'is_cpu_specific_profdata=true',
        'local required_ffmpeg_cache_suffix=pgo-v1-clang',
        'required_ffmpeg_cache_suffix=profiling-v1-clang',
        '--required-ffmpeg-cache-suffix="$required_ffmpeg_cache_suffix"',
        'test -n "$obuparse_cache_suffix"',
        'test -n "$lsmash_cache_suffix"',
        'test -n "$gop_muxer_cache_suffix"',
        '--required-obuparse-cache-suffix="$obuparse_cache_suffix"',
        '--required-lsmash-cache-suffix="$lsmash_cache_suffix"',
        '--required-gop-muxer-cache-suffix="$gop_muxer_cache_suffix"',
        '--require-dependency-fields',
        '--require-fresh-slot',
        'if [ "$is_cpu_specific_profdata" = true ]; then',
        'metadata_check_args+=(--require-target-cpu)',
        'metadata_check_args+=(--current-toolchain="$current_toolchain")',
        'echo "::warning::PGO profdata metadata missing: target=${target} branch=${branch}"',
        'summary_note="metadata missing"',
        'rm -f "$metadata_path"',
        'rm -rf ../build/profiles',
        'profdata_branch_for() {',
        'printf \'profdata-%s-%s\\n\' "$target_cpu" "$profile_target"',
        'fetch_profdata_with_fallback() {',
        'local target_cpu="${{ matrix.target_cpu }}"',
        'target_branch=$(profdata_branch_for "$target_cpu" "$target")',
        'baseline_branch=$(profdata_branch_for x86-64 "$target")',
        'if [ "$target_branch" = "$baseline_branch" ]; then',
        'fetch_profdata "$target" "$target_cpu" "$target_branch" "$source_path"',
        'if fetch_profdata "$target" "$target_cpu" "$target_branch" "$source_path" false; then',
        'echo "Falling back to x86-64 PGO profdata: target=${target} branch=${baseline_branch}"',
        'fetch_profdata "$target" x86-64 "$baseline_branch" "$source_path"',
        'fetch_profdata_with_fallback 8b-lib x265.profdata || true',
        'fetch_profdata_with_fallback 12b-lib x265.profdata || true',
        'append_pgo_status 8b-lib skipped push "push path only consumes all-target profdata"',
        'append_pgo_status 12b-lib skipped push "push path only consumes all-target profdata"',
        'fetch_profdata_with_fallback all x265.profdata || true',
    )
    for required in required_lines:
        require_active_line_contains(active_lines, required, path, f'Build workflow Fetch PGO Profdata must include: {required}')
    for index, line in enumerate(active_lines):
        if 'summary_note="metadata missing"' in line:
            tail = active_lines[index + 1:index + 10]
            if not any(line == 'append_pgo_status "$target" unavailable "$branch" "$summary_note"' for line in tail):
                fail('Build workflow Fetch PGO Profdata must record missing metadata before returning', path)
            if not any(line == 'return 1' for line in tail):
                fail('Build workflow Fetch PGO Profdata must skip branches with missing metadata before copying profdata', path)
            break
    else:
        fail('Build workflow Fetch PGO Profdata must record missing metadata before skipping the branch', path)
    if any('git ls-remote --exit-code --heads origin "$branch"' in line for line in active_lines):
        fail('Build workflow Fetch PGO Profdata must not preflight branches with git ls-remote before git fetch', path)
    print('PGO fetch scope validated')


def validate_build_compile_cpu_flags(repo_root):
    path = repo_root / BUILD_WORKFLOW
    parsed = load_yaml(repo_root, BUILD_WORKFLOW)
    active_lines = shell_active_logical_lines(workflow_step_run(parsed, path, 'build', 'Compile X265'))
    for required in (
        'resolve_cpu_march_flag() {',
        'x86-64)',
        'haswell|skylake|alderlake|raptorlake|arrowlake|znver2|znver3|znver4|znver5)',
        'printf -- \'-march=%s\\n\' "$1"',
        'CPU_CXX_FLAG=$(resolve_cpu_march_flag "$CPU")',
        'BASE_CXX_FLAGS="${BASE_CXX_FLAGS} ${CPU_CXX_FLAG}"',
    ):
        require_active_line_contains(active_lines, required, path, f'Build workflow Compile X265 must include CPU-specific CXX flags: {required}')


def validate_windows_dependency_smoke_scope(repo_root):
    build_path = repo_root / BUILD_WORKFLOW
    parsed = load_yaml(repo_root, BUILD_WORKFLOW)

    warning_scan_setup_step = workflow_step(parsed, build_path, 'cxx20-warning-scan', 'Setup Shared Dependencies')
    warning_scan_with_values = warning_scan_setup_step.get('with')
    if not isinstance(warning_scan_with_values, dict):
        fail('C++20 warning scan Setup Shared Dependencies step is missing with inputs', build_path)

    runtime_setup_step = workflow_step(parsed, build_path, 'build', 'Setup Shared Dependencies (Runtime Smokes)')
    runtime_with_values = runtime_setup_step.get('with')
    if not isinstance(runtime_with_values, dict):
        fail('Build workflow Setup Shared Dependencies (Runtime Smokes) step is missing with inputs', build_path)
    if runtime_with_values.get('ffmpeg-cache-suffix') == warning_scan_with_values.get('ffmpeg-cache-suffix'):
        fail('Build workflow runtime-smoke FFmpeg cache suffix must differ from warning-scan library-only cache suffix', build_path)
    if runtime_with_values.get('ffmpeg-cache-suffix') != 'lavf-cli-v5-clang':
        fail('Build workflow Setup Shared Dependencies (Runtime Smokes) must pin ffmpeg-cache-suffix=lavf-cli-v5-clang', build_path)
    ffmpeg_configure = runtime_with_values.get('ffmpeg-configure')
    if not isinstance(ffmpeg_configure, str):
        fail('Build workflow Setup Shared Dependencies (Runtime Smokes) must provide ffmpeg-configure', build_path)
    for required in (
        '--enable-ffmpeg',
        '--enable-ffprobe',
        '--enable-avdevice',
        '--enable-avfilter',
        '--enable-indev=lavfi',
        '--enable-filter=testsrc2,scale',
        '--enable-demuxer=mov,matroska,mpegts,avi,mpegvideo,m4v,mpeg,ogg,asf,yuv4mpegpipe,hevc',
        '--enable-parser=h264,hevc',
        '--enable-encoder=wrapped_avframe,ffv1,rawvideo',
        '--enable-muxer=matroska,rawvideo,yuv4mpegpipe',
    ):
        if required not in ffmpeg_configure:
            fail(f'Build workflow runtime-smoke FFmpeg config must enable dependency: {required}', build_path)
    if runtime_with_values.get('use-gop-muxer') != 'true':
        fail('Build workflow Setup Shared Dependencies (Runtime Smokes) must enable GOP muxer', build_path)
    if runtime_with_values.get('use-mimalloc') != 'true':
        fail('Build workflow Setup Shared Dependencies (Runtime Smokes) must keep mimalloc enabled', build_path)
    if runtime_with_values.get('use-obuparse') != 'true':
        fail('Build workflow Setup Shared Dependencies (Runtime Smokes) must keep obuparse enabled', build_path)
    if runtime_with_values.get('use-lsmash') != 'true':
        fail('Build workflow Setup Shared Dependencies (Runtime Smokes) must keep L-SMASH enabled', build_path)
    expected_packages = ''
    if runtime_with_values.get('extra-msys2-packages') != expected_packages:
        fail('Build workflow Setup Shared Dependencies (Runtime Smokes) must not preinstall extra MSYS2 packages', build_path)

    build_only_setup_step = workflow_step(parsed, build_path, 'build', 'Setup Shared Dependencies (Build Only)')
    build_only_with_values = build_only_setup_step.get('with')
    if not isinstance(build_only_with_values, dict):
        fail('Build workflow Setup Shared Dependencies (Build Only) step is missing with inputs', build_path)
    if build_only_with_values.get('ffmpeg-cache-suffix') != warning_scan_with_values.get('ffmpeg-cache-suffix'):
        fail('Build workflow build-only FFmpeg cache suffix must reuse warning-scan library-only cache suffix', build_path)
    if build_only_with_values.get('ffmpeg-cache-suffix') != 'lavf-v4-clang':
        fail('Build workflow Setup Shared Dependencies (Build Only) must pin ffmpeg-cache-suffix=lavf-v4-clang', build_path)
    build_only_ffmpeg_configure = build_only_with_values.get('ffmpeg-configure')
    if not isinstance(build_only_ffmpeg_configure, str):
        fail('Build workflow Setup Shared Dependencies (Build Only) must provide ffmpeg-configure', build_path)
    for required in (
        '--enable-avformat',
        '--enable-avcodec',
        '--enable-avutil',
        '--enable-swscale',
        '--enable-demuxer=mov,matroska,mpegts,avi,mpegvideo,m4v,mpeg,ogg,asf',
        '--enable-protocol=file',
    ):
        if required not in build_only_ffmpeg_configure:
            fail(f'Build workflow build-only FFmpeg config must enable compile dependency: {required}', build_path)
    for forbidden in (
        '--enable-ffmpeg',
        '--enable-ffprobe',
        '--enable-avdevice',
        '--enable-avfilter',
        '--enable-indev=lavfi',
        '--enable-filter=testsrc2',
        '--enable-parser=h264,hevc',
        '--enable-encoder=wrapped_avframe,ffv1,rawvideo',
        '--enable-muxer=matroska,yuv4mpegpipe',
        '--enable-demuxer=mov,matroska,mpegts,avi,mpegvideo,m4v,mpeg,ogg,asf,yuv4mpegpipe,hevc',
    ):
        if forbidden in build_only_ffmpeg_configure:
            fail(f'Build workflow build-only FFmpeg config must stay lightweight and omit: {forbidden}', build_path)
    if build_only_with_values.get('use-gop-muxer') != 'false':
        fail('Build workflow Setup Shared Dependencies (Build Only) must disable GOP muxer', build_path)
    full_deps_toggle = '${{ env.CI_FULL_EVENT }}'
    if build_only_with_values.get('use-mimalloc') != full_deps_toggle:
        fail('Build workflow Setup Shared Dependencies (Build Only) must enable mimalloc only for workflow_dispatch/tag full builds', build_path)
    if build_only_with_values.get('use-obuparse') != full_deps_toggle:
        fail('Build workflow Setup Shared Dependencies (Build Only) must enable obuparse only for workflow_dispatch/tag full builds', build_path)
    if build_only_with_values.get('use-lsmash') != full_deps_toggle:
        fail('Build workflow Setup Shared Dependencies (Build Only) must enable L-SMASH only for workflow_dispatch/tag full builds', build_path)
    expected_packages = ''
    if build_only_with_values.get('extra-msys2-packages') != expected_packages:
        fail('Build workflow Setup Shared Dependencies (Build Only) must not preinstall extra MSYS2 packages', build_path)

    smoke_step = workflow_step(parsed, build_path, 'build', 'Smoke Test L-SMASH')
    if smoke_step.get('if') != "matrix.target_cpu == 'x86-64'":
        fail('Build workflow Smoke Test L-SMASH must run only for the x86-64 representative build', build_path)

    active_lines = shell_active_logical_lines(workflow_step_run(parsed, build_path, 'build', 'Smoke Test L-SMASH'))
    for required in (
        'nm /usr/local/lib/liblsmash.a 2>/dev/null | grep -E "lsmash_create_root|lsmash_destroy_root" | head -5',
        '/tmp/lsmash_smoke.exe',
        'if ! /tmp/mp4_smoke.exe; then',
        'pacman -S --needed --noconfirm mingw-w64-clang-x86_64-lldb',
        'lldb -b -s /tmp/mp4_smoke_lldb.cmd /tmp/mp4_smoke.exe || true',
        'exit 1',
        'test -s smoke.mp4',
    ):
        require_active_line_contains(active_lines, required, build_path, f'Build workflow Smoke Test L-SMASH must include: {required}')
    print('Windows dependency smoke scope validated')


def validate_build_log_scope(repo_root):
    build_path = repo_root / BUILD_WORKFLOW
    parsed = load_yaml(repo_root, BUILD_WORKFLOW)
    active_lines = shell_active_logical_lines(workflow_step_run(parsed, build_path, 'build', 'Compile X265'))
    required_lines = (
        'run_ninja_retry_verbose() {',
        'ninja "${ninja_args[@]}"',
        'mkdir -p build/logs',
        'echo "=== Ninja failed, rerunning verbose diagnostics: $dir -> $log ==="',
        'ninja "${ninja_args[@]}" -v 2>&1 | tee "$log"',
    )
    for required in required_lines:
        require_active_line_contains(active_lines, required, build_path, f'Build workflow Compile X265 must include: {required}')
    forbidden_lines = (
        'run_ninja_logged() {',
        'mkdir -p build/logs',
        'echo "=== Verbose ninja: $dir -> $log ==="',
    )
    if active_lines.count('mkdir -p build/logs') > 1:
        fail('Build workflow Compile X265 must not precreate build/logs for successful builds', build_path)
    for forbidden in forbidden_lines:
        if forbidden in active_lines and forbidden != 'mkdir -p build/logs':
            fail(f'Build workflow Compile X265 must not include: {forbidden}', build_path)
    print('Build log scope validated')


def validate_build_compile_scope(repo_root):
    build_path = repo_root / BUILD_WORKFLOW
    parsed = load_yaml(repo_root, BUILD_WORKFLOW)
    active_lines = shell_active_logical_lines(workflow_step_run(parsed, build_path, 'build', 'Compile X265'))
    for required in (
        'FULL_COMPILE=false',
        'FULL_COMPILE=true',
        'if [ "${CI_FULL_EVENT}" = \'true\' ]; then',
        'echo "Building representative compile smoke only"',
        'ENABLE_LSMASH=OFF',
        'USE_MIMALLOC=OFF',
        'ALL_BUILD_EXTRA_ARGS=()',
        'if [ "$CPU" = "x86-64" ] || [ "${CI_FULL_EVENT}" = \'true\' ]; then',
        'ENABLE_LSMASH=ON',
        'USE_MIMALLOC=ON',
        'ALL_BUILD_EXTRA_ARGS=(-DOBUPARSE_LIBRARY=/usr/local/lib/libobuparse.a)',
        'echo "Disabling Windows dependency features not installed in build-only push path"',
        '-DENABLE_LSMASH="${ENABLE_LSMASH}"',
        '-DUSE_MIMALLOC="${USE_MIMALLOC}"',
        'build_representative_compile_smoke() {',
        'run_ninja_retry_verbose 10b build/10b "$NPROC"',
        'cp build/10b/x265.exe build/all/x265.exe',
        'build_full_compile_matrix() {',
        'run_ninja_retry_verbose 8b build/8b "$NINJA_JOBS_TRIPLE" &',
        'run_ninja_retry_verbose 10b build/10b "$NINJA_JOBS_TRIPLE" &',
        'run_ninja_retry_verbose 12b build/12b "$NINJA_JOBS_TRIPLE" &',
        'run_ninja_retry_verbose 8b-lib build/8b-lib "$NINJA_JOBS_PAIR" &',
        'run_ninja_retry_verbose 12b-lib build/12b-lib "$NINJA_JOBS_PAIR" &',
        'run_ninja_retry_verbose all-8b-lib build/all-8b-lib "$NINJA_JOBS_PAIR" &',
        'run_ninja_retry_verbose all-12b-lib build/all-12b-lib "$NINJA_JOBS_PAIR" &',
        '"${ALL_BUILD_EXTRA_ARGS[@]}"',
        'run_ninja_retry_verbose all build/all',
        'build_representative_compile_smoke',
        'if [ "$FULL_COMPILE" = true ]; then',
        'require_pgo_flag 8b-lib "$PGO_8B_LIB_FLAG"',
        'require_pgo_flag 12b-lib "$PGO_12B_LIB_FLAG"',
        'require_pgo_flag all "$PGO_ALL_FLAG"',
        'build_full_compile_matrix',
        'require_pgo_flag() {',
        'echo "::error::Missing required PGO profdata for $label" >&2',
        ):
        require_active_line_contains(active_lines, required, build_path, f'Build workflow Compile X265 must include: {required}')

    full_gate_index = require_single_line_index(
        active_lines,
        'if [ "$FULL_COMPILE" = true ]; then',
        build_path,
        'Build workflow Compile X265 full matrix must be gated by FULL_COMPILE',
    )
    full_gate_end = matching_fi_index(
        active_lines,
        full_gate_index,
        build_path,
        'Build workflow Compile X265 full matrix gate must close',
    )
    full_call_indexes = [index for index, line in enumerate(active_lines) if line == 'build_full_compile_matrix']
    if len(full_call_indexes) != 1:
        fail('Build workflow Compile X265 full matrix must be called exactly once', build_path)
    full_call_index = full_call_indexes[0]
    if not full_gate_index < full_call_index < full_gate_end:
        fail('Build workflow Compile X265 full matrix call must be inside FULL_COMPILE gate', build_path)
    for required in (
        'require_pgo_flag 8b-lib "$PGO_8B_LIB_FLAG"',
        'require_pgo_flag 12b-lib "$PGO_12B_LIB_FLAG"',
        'require_pgo_flag all "$PGO_ALL_FLAG"',
    ):
        matches = [index for index, line in enumerate(active_lines) if line == required]
        if len(matches) != 1 or not full_gate_index < matches[0] < full_call_index:
            fail(f'Build workflow Compile X265 must require PGO before full matrix: {required}', build_path)

    representative_call_indexes = [index for index, line in enumerate(active_lines) if line == 'build_representative_compile_smoke']
    if len(representative_call_indexes) != 1:
        fail('Build workflow Compile X265 must always run representative compile smoke', build_path)
    representative_call_index = representative_call_indexes[0]
    if not representative_call_index < full_gate_index < full_call_index < full_gate_end:
        fail('Build workflow Compile X265 must run representative compile smoke before gated full matrix', build_path)
    representative_function_index = require_single_line_index(
        active_lines,
        'build_representative_compile_smoke() {',
        build_path,
        'Build workflow Compile X265 must define representative compile smoke',
    )
    full_function_index = require_single_line_index(
        active_lines,
        'build_full_compile_matrix() {',
        build_path,
        'Build workflow Compile X265 must define full compile matrix',
    )
    for required in (
        '-DCMAKE_CXX_FLAGS="$CXX_FLAGS_ALL"',
        'check_pgo_consume_commands build/10b "$PGO_ALL_FLAG" 60',
    ):
        require_line_containing_in_scope(
            active_lines,
            required,
            representative_function_index,
            full_function_index,
            build_path,
            f'Build workflow Compile X265 representative smoke must include: {required}',
        )
    print('Build compile scope validated')


def validate_package_scope(repo_root, bash):
    build_path = repo_root / BUILD_WORKFLOW
    parsed = load_yaml(repo_root, BUILD_WORKFLOW)
    validate_ci_version_helper(repo_root, bash)
    validate_release_asset_validator(repo_root, bash)
    expected_if = "env.CI_FULL_EVENT == 'true' || matrix.target_cpu == 'x86-64'"
    for step_name in (
        'Package',
        'Set Package Version',
        'Compress Package',
        'Verify Package Artifact',
        'Upload Artifact',
    ):
        step = workflow_step(parsed, build_path, 'build', step_name)
        if step.get('if') != expected_if:
            fail(f'Build workflow step {step_name} must package push artifacts only for the x86-64 representative build', build_path)

    active_lines = shell_active_logical_lines(workflow_step_run(parsed, build_path, 'build', 'Set Package Version'))
    require_active_line_contains(
        active_lines,
        'source x265/.github/scripts/ci_version_helpers.sh',
        build_path,
        'Build workflow Set Package Version must source the CI version helper',
    )
    require_active_line_contains(
        active_lines,
        'version=$(x265_package_version_for_event "${{ needs.build-metadata.outputs.latest_tag }}" "${{ needs.build-metadata.outputs.ci_version }}")',
        build_path,
        'Build workflow Set Package Version must use x265_package_version_for_event with the build-metadata outputs',
    )

    profiling_path = repo_root / BUILD_PROFILING_WORKFLOW
    profiling = load_yaml(repo_root, BUILD_PROFILING_WORKFLOW)
    for workflow_path, workflow_parsed, workflow_name in (
        (build_path, parsed, 'Build workflow'),
        (profiling_path, profiling, 'Build Profiling workflow'),
    ):
        for job in workflow_jobs(workflow_parsed, workflow_path).values():
            if not isinstance(job, dict):
                continue
            for step in job.get('steps', []):
                if not isinstance(step, dict):
                    continue
                run = step.get('run')
                if isinstance(run, str) and 'pacman -S --needed --noconfirm p7zip' in run:
                    fail(f'{workflow_name} must use runner-provided 7z instead of installing p7zip', workflow_path)

    active_lines = shell_active_logical_lines(workflow_step_run(parsed, build_path, 'build', 'Compress Package'))
    require_active_line_contains(
        active_lines,
        'bash ../x265/.github/scripts/ci_7z.sh a -t7z -mx=9 ../x265-win64-${{matrix.target_cpu}}-clang.${{ steps.package_version.outputs.version }}.7z ./*.exe',
        build_path,
        'Build workflow Compress Package must use the runner-provided 7z executable',
    )
    verify_lines = shell_active_logical_lines(workflow_step_run(parsed, build_path, 'build', 'Verify Package Artifact'))
    for required, message in (
        ('bash x265/.github/scripts/verify_ci_archive.sh x265-release "x265-win64-${{ matrix.target_cpu }}-clang.${{ steps.package_version.outputs.version }}.7z" artifact-check "${{ matrix.target_cpu }}" "$expected_count"', 'Build workflow Verify Package Artifact must validate the packaged release archive'),
        ('expected_count=1', 'Build workflow Verify Package Artifact must default representative push verification to one packaged executable'),
        ('if [ "${CI_FULL_EVENT}" = \'true\' ]; then', 'Build workflow Verify Package Artifact must expand verification for workflow_dispatch and tagged releases'),
        ('expected_count=4', 'Build workflow Verify Package Artifact must verify four packaged executables for workflow_dispatch and tagged releases'),
    ):
        require_active_line_contains(verify_lines, required, build_path, message)

    upload_step = workflow_step(parsed, build_path, 'build', 'Upload Artifact')
    if upload_step.get('uses') != 'actions/upload-artifact@v7':
        fail('Build workflow Upload Artifact step must use actions/upload-artifact@v7', build_path)
    upload_with = upload_step.get('with')
    if not isinstance(upload_with, dict):
        fail('Build workflow Upload Artifact step must declare with inputs', build_path)
    for key, value in {
        'name': 'x265-win64-${{matrix.target_cpu}}-clang.${{ steps.package_version.outputs.version }}',
        'path': 'x265-win64-${{matrix.target_cpu}}-clang.${{ steps.package_version.outputs.version }}.7z',
        'compression-level': 0,
    }.items():
        if upload_with.get(key) != value:
            fail(f'Build workflow Upload Artifact step must set {key}={value}', build_path)

    download_step = workflow_step(parsed, build_path, 'publish-release', 'Download Release Artifacts')
    if download_step.get('uses') != 'actions/download-artifact@v7':
        fail('Build workflow Download Release Artifacts step must use actions/download-artifact@v7', build_path)
    download_with = download_step.get('with')
    if not isinstance(download_with, dict):
        fail('Build workflow Download Release Artifacts step must declare with inputs', build_path)
    if download_with.get('path') != 'release-assets':
        fail('Build workflow Download Release Artifacts step must set path=release-assets', build_path)

    release_step = workflow_step(parsed, build_path, 'publish-release', 'Release Artifacts')
    if release_step.get('uses') != 'softprops/action-gh-release@v3':
        fail('Build workflow Release Artifacts step must use softprops/action-gh-release@v3', build_path)
    release_with = release_step.get('with')
    if not isinstance(release_with, dict):
        fail('Build workflow Release Artifacts step must declare with inputs', build_path)
    for key, value in {
        'tag_name': '${{ github.ref_name }}',
        'files': 'release-assets/**/*.7z',
        'fail_on_unmatched_files': True,
        'generate_release_notes': False,
        'prerelease': True,
    }.items():
        if release_with.get(key) != value:
            fail(f'Build workflow Release Artifacts step must set {key}={value}', build_path)

    active_lines = shell_active_logical_lines(workflow_step_run(
        profiling,
        profiling_path,
        'build',
        'Package LLVM Profdata Tool',
    ))
    for required, message in (
        ('llvm_profdata=$(command -v llvm-profdata.exe || command -v llvm-profdata)', 'Build Profiling workflow Package LLVM Profdata Tool must resolve llvm-profdata from PATH'),
        ('test -n "$llvm_profdata"', 'Build Profiling workflow Package LLVM Profdata Tool must require a resolved llvm-profdata path'),
        ('[ -f "$llvm_profdata" ] || llvm_profdata="${llvm_profdata}.exe"', 'Build Profiling workflow Package LLVM Profdata Tool must normalize bare llvm-profdata paths to the .exe sibling when needed'),
        ('test -f "$llvm_profdata"', 'Build Profiling workflow Package LLVM Profdata Tool must require the resolved llvm-profdata executable to exist'),
        ('case "$llvm_profdata" in', 'Build Profiling workflow Package LLVM Profdata Tool must constrain llvm-profdata to the expected toolchain location'),
        ('/clang64/bin/*) ;;', 'Build Profiling workflow Package LLVM Profdata Tool must allow only the clang64 llvm-profdata path prefix'),
        ('*) echo "Unexpected llvm-profdata path: $llvm_profdata" >&2; exit 1 ;;', 'Build Profiling workflow Package LLVM Profdata Tool must fail on unexpected llvm-profdata locations'),
        ('version=$("$llvm_profdata" --version | sed -nE \'s/.*LLVM version ([0-9]+(\\.[0-9]+)+).*/\\1/p\' | head -1)', 'Build Profiling workflow Package LLVM Profdata Tool must derive the package version from llvm-profdata --version'),
        ('test -n "$version"', 'Build Profiling workflow Package LLVM Profdata Tool must require a parsed llvm-profdata version before packaging'),
        ('echo "version=$version" >> "$GITHUB_OUTPUT"', 'Build Profiling workflow Package LLVM Profdata Tool must publish the parsed llvm-profdata version'),
        ('cp "$llvm_profdata" profdata-dist/', 'Build Profiling workflow Package LLVM Profdata Tool must copy llvm-profdata.exe into profdata-dist before dependency staging'),
        ('declare -A seen', 'Build Profiling workflow Package LLVM Profdata Tool must track visited DLL dependencies'),
        ('declare -a queue', 'Build Profiling workflow Package LLVM Profdata Tool must maintain a DLL traversal queue'),
        ('declare -a missing_dlls', 'Build Profiling workflow Package LLVM Profdata Tool must collect unresolved DLL dependencies'),
        ('queue=("$llvm_profdata")', 'Build Profiling workflow Package LLVM Profdata Tool must seed DLL dependency traversal with llvm-profdata'),
        ('current="${queue[0]}"', 'Build Profiling workflow Package LLVM Profdata Tool must process queued DLL dependencies in order'),
        ('queue=("${queue[@]:1}")', 'Build Profiling workflow Package LLVM Profdata Tool must pop processed DLL dependencies from the queue'),
        ('dll_key=$(printf \'%s\' "$dll_name" | tr \'[:upper:]\' \'[:lower:]\')', 'Build Profiling workflow Package LLVM Profdata Tool must normalize DLL dependency names before deduping and whitelisting'),
        ('[ -z "${seen[$dll_key]:-}" ] || continue', 'Build Profiling workflow Package LLVM Profdata Tool must skip DLL dependencies already seen in the traversal'),
        ('for base in /clang64/bin /usr/bin; do', 'Build Profiling workflow Package LLVM Profdata Tool must search DLL dependencies in clang64 and system bin directories'),
        ('if [ -f "$base/$dll_name" ]; then', 'Build Profiling workflow Package LLVM Profdata Tool must resolve DLL dependencies by checking candidate directories'),
        ('dll_path="$base/$dll_name"', 'Build Profiling workflow Package LLVM Profdata Tool must bind resolved DLL dependency paths from the candidate directory'),
        ('advapi32.dll|bcrypt.dll|kernel32.dll|msvcrt.dll|ntdll.dll|ole32.dll|shell32.dll|user32.dll|ws2_32.dll) ;;', 'Build Profiling workflow Package LLVM Profdata Tool must tolerate the expected Windows system DLL set without packaging them'),
        ('seen[$dll_key]=missing', 'Build Profiling workflow Package LLVM Profdata Tool must mark unresolved non-system DLL dependencies as missing'),
        ('missing_dlls+=("$dll_name")', 'Build Profiling workflow Package LLVM Profdata Tool must record unresolved non-system DLL dependency names'),
        ('seen[$dll_key]="$dll_path"', 'Build Profiling workflow Package LLVM Profdata Tool must record resolved DLL dependency paths to avoid duplicate staging'),
        ('cp "$dll_path" profdata-dist/', 'Build Profiling workflow Package LLVM Profdata Tool must copy resolved DLL dependencies into profdata-dist'),
        ('queue+=("$dll_path")', 'Build Profiling workflow Package LLVM Profdata Tool must recursively collect DLL dependencies'),
        ('done < <(objdump -p "$current" | awk -F\': \' \'/DLL Name:/ { sub(/\\r$/, "", $2); print $2 }\')', 'Build Profiling workflow Package LLVM Profdata Tool must extract DLL dependency names from objdump output'),
        ('printf \'Missing DLL dependency for llvm-profdata package: %s\\n\' "${missing_dlls[@]}" >&2', 'Build Profiling workflow Package LLVM Profdata Tool must fail on missing DLL dependencies'),
        ('strip -s profdata-dist/llvm-profdata.exe', 'Build Profiling workflow Package LLVM Profdata Tool must strip llvm-profdata.exe'),
        ('shopt -s nullglob', 'Build Profiling workflow Package LLVM Profdata Tool must enable nullglob before iterating packaged DLLs'),
        ('for dll in profdata-dist/*.dll; do', 'Build Profiling workflow Package LLVM Profdata Tool must iterate packaged DLLs from profdata-dist'),
        ('strip -s "$dll"', 'Build Profiling workflow Package LLVM Profdata Tool must strip packaged DLL dependencies'),
        ('packaged_dll_count=$((packaged_dll_count + 1))', 'Build Profiling workflow Package LLVM Profdata Tool must count packaged DLLs'),
        ('if [ -n "${GITHUB_STEP_SUMMARY:-}" ]; then', 'Build Profiling workflow Package LLVM Profdata Tool must write a package summary only when GITHUB_STEP_SUMMARY is available'),
        ('echo "### LLVM profdata package"', 'Build Profiling workflow Package LLVM Profdata Tool must title the step summary for llvm-profdata packaging'),
        ('echo "| tool | version | packaged_dlls |"', 'Build Profiling workflow Package LLVM Profdata Tool must write the package summary table header'),
        ('echo "| $llvm_profdata | $version | $packaged_dll_count |"', 'Build Profiling workflow Package LLVM Profdata Tool must record tool path, version, and packaged DLL count in the step summary'),
    ):
        require_active_line_contains(active_lines, required, profiling_path, message)

    active_lines = shell_active_logical_lines(workflow_step_run(
        profiling,
        profiling_path,
        'build',
        'Compress Profiling Build',
    ))
    require_active_line_contains(
        active_lines,
        'bash ../x265/.github/scripts/ci_7z.sh a -t7z -mx=9 ../x265-profiling-win64-${{ matrix.target_cpu }}-clang.${{ steps.package_version.outputs.version }}.7z ./*.exe',
        profiling_path,
        'Build Profiling workflow Compress Profiling Build must use the runner-provided 7z executable',
    )
    active_lines = shell_active_logical_lines(workflow_step_run(
        profiling,
        profiling_path,
        'build',
        'Compress LLVM Profdata',
    ))
    require_active_line_contains(
        active_lines,
        'bash ../x265/.github/scripts/ci_7z.sh a -t7z -mx=9 ../llvm-profdata-win64-clang.${{ steps.llvm_profdata.outputs.version }}.7z ./*',
        profiling_path,
        'Build Profiling workflow Compress LLVM Profdata must use the runner-provided 7z executable',
    )
    verify_lines = shell_active_logical_lines(workflow_step_run(
        profiling,
        profiling_path,
        'build',
        'Verify Profiling Artifact',
    ))
    require_active_line_contains(
        verify_lines,
        'bash x265/.github/scripts/verify_ci_archive.sh x265-profiling "x265-profiling-win64-${{ matrix.target_cpu }}-clang.${{ steps.package_version.outputs.version }}.7z" artifact-check-profiling "${{ matrix.target_cpu }}"',
        profiling_path,
        'Build Profiling workflow Verify Profiling Artifact must validate the packaged profiling archive',
    )
    verify_lines = shell_active_logical_lines(workflow_step_run(
        profiling,
        profiling_path,
        'build',
        'Verify LLVM Profdata Artifact',
    ))
    require_active_line_contains(
        verify_lines,
        'bash x265/.github/scripts/verify_ci_archive.sh llvm-profdata "llvm-profdata-win64-clang.${{ steps.llvm_profdata.outputs.version }}.7z" artifact-check-profdata',
        profiling_path,
        'Build Profiling workflow Verify LLVM Profdata Artifact must validate the packaged profdata archive',
    )
    combined_upload_step = workflow_step(
        profiling,
        profiling_path,
        'build',
        'Upload Combined Profiling Artifact',
    )
    if combined_upload_step.get('uses') != 'actions/upload-artifact@v7':
        fail('Build Profiling Upload Combined Profiling Artifact step must use actions/upload-artifact@v7', profiling_path)
    combined_upload_with = combined_upload_step.get('with')
    if not isinstance(combined_upload_with, dict):
        fail('Build Profiling Upload Combined Profiling Artifact step must declare with inputs', profiling_path)
    for key, value in {
        'name': 'x265-profiling-win64-${{ matrix.target_cpu }}-clang.${{ steps.package_version.outputs.version }}',
        'path': 'x265-profiling-win64-${{ matrix.target_cpu }}-clang.${{ steps.package_version.outputs.version }}.7z',
        'compression-level': 0,
        'retention-days': 7,
    }.items():
        if combined_upload_with.get(key) != value:
            fail(f'Build Profiling Upload Combined Profiling Artifact step must set {key}={value}', profiling_path)

    llvm_upload_step = workflow_step(
        profiling,
        profiling_path,
        'build',
        'Upload LLVM Profdata Artifact',
    )
    if llvm_upload_step.get('uses') != 'actions/upload-artifact@v7':
        fail('Build Profiling Upload LLVM Profdata Artifact step must use actions/upload-artifact@v7', profiling_path)
    llvm_upload_with = llvm_upload_step.get('with')
    if not isinstance(llvm_upload_with, dict):
        fail('Build Profiling Upload LLVM Profdata Artifact step must declare with inputs', profiling_path)
    for key, value in {
        'name': 'llvm-profdata-win64-clang.${{ steps.llvm_profdata.outputs.version }}',
        'path': 'llvm-profdata-win64-clang.${{ steps.llvm_profdata.outputs.version }}.7z',
        'compression-level': 0,
        'retention-days': 7,
    }.items():
        if llvm_upload_with.get(key) != value:
            fail(f'Build Profiling Upload LLVM Profdata Artifact step must set {key}={value}', profiling_path)

    download_step = workflow_step(
        profiling,
        profiling_path,
        'publish-release',
        'Download Profiling Artifacts',
    )
    if download_step.get('uses') != 'actions/download-artifact@v7':
        fail('Build Profiling Download Profiling Artifacts step must use actions/download-artifact@v7', profiling_path)
    download_with = download_step.get('with')
    if not isinstance(download_with, dict):
        fail('Build Profiling Download Profiling Artifacts step must declare with inputs', profiling_path)
    if download_with.get('path') != 'release-assets':
        fail('Build Profiling Download Profiling Artifacts step must set path=release-assets', profiling_path)

    release_step = workflow_step(profiling, profiling_path, 'publish-release', 'Release Profiling Artifacts')
    if release_step.get('uses') != 'softprops/action-gh-release@v3':
        fail('Build Profiling Release Profiling Artifacts step must use softprops/action-gh-release@v3', profiling_path)

    build_release_asset_lines = shell_active_logical_lines(
        workflow_step_run(parsed, build_path, 'publish-release', 'Validate Release Assets')
    )
    require_active_exact_command(
        build_release_asset_lines,
        ('bash', 'x265/.github/scripts/validate_release_assets.sh', 'release', 'release-assets', '${GITHUB_REF_NAME}'),
        build_path,
        'Build workflow Validate Release Assets must run the shared release asset validator without softening wrappers or extra flags',
    )
    profiling_release_asset_lines = shell_active_logical_lines(
        workflow_step_run(profiling, profiling_path, 'publish-release', 'Validate Profiling Release Assets')
    )
    require_active_exact_command(
        profiling_release_asset_lines,
        ('bash', 'x265/.github/scripts/validate_release_assets.sh', 'profiling', 'release-assets', '${GITHUB_REF_NAME}'),
        profiling_path,
        'Build Profiling Validate Profiling Release Assets must run the shared profiling release asset validator without softening wrappers or extra flags',
    )
    print('Package scope validated')


def validate_ci_7z_helper(repo_root, bash):
    validate_bash_file(
        repo_root,
        bash,
        CI_7Z_HELPER,
        'missing CI 7z helper',
        required_text=(
            'find_ci_7z() {',
            'for candidate in 7z 7za 7z.exe; do',
            '"/c/Program Files/7-Zip/7z.exe"',
            'ci_7z() {',
        ),
        required_message='CI 7z helper missing detail',
    )
    print('CI 7z helper validated')


def build_validators(repo_root, args, bash):
    return {
        'yaml-text': lambda: validate_yaml_text(repo_root, WORKFLOW_DIR, ACTION_DIR),
        'yaml-parse': lambda: validate_yaml_parse(repo_root, WORKFLOW_DIR, ACTION_DIR),
        'run-blocks': lambda: validate_run_blocks(repo_root, WORKFLOW_DIR, ACTION_DIR, bash),
        'scan-helper': lambda: validate_scan_helper(repo_root, bash),
        'ensure-cmake4-helper': lambda: validate_ensure_cmake4_helper(repo_root, bash),
        'ensure-linux-sanitizer-toolchain-helper': lambda: validate_ensure_linux_sanitizer_toolchain_helper(repo_root, bash),
        'mp4-smoke-helper': lambda: validate_mp4_smoke_helper(repo_root, bash),
        'profiling-smoke-helper': lambda: validate_profiling_smoke_helper(repo_root, bash),
        'verify-ci-archive-helper': lambda: validate_verify_ci_archive_helper(repo_root, bash),
        'ci-7z-helper': lambda: validate_ci_7z_helper(repo_root, bash),
        'runtime-smoke-suite': lambda: validate_runtime_smoke_suite(repo_root, bash),
        'mp4-smoke-suite': lambda: validate_mp4_smoke_suite(repo_root, bash),
        'source-test-vector-scripts': lambda: validate_source_test_vector_scripts(repo_root),
        'dependency-update-anchors': lambda: validate_dependency_update_anchors(repo_root),
        'windows-deps-checkout-scope': lambda: validate_windows_deps_checkout_scope(repo_root),
        'required-snippets': lambda: validate_required_snippets(repo_root, bash),
        'build-pr-fast-gate': lambda: validate_build_pr_fast_gate(repo_root),
        'warning-scan-dependencies': lambda: validate_warning_scan_dependencies(repo_root),
        'windows-gcc-diagnostics-setup': lambda: validate_windows_gcc_diagnostics_setup(repo_root),
        'job-timeouts': lambda: validate_job_timeouts(repo_root),
        'update-deps-concurrency': lambda: validate_update_deps_concurrency(repo_root),
        'build-workflow-concurrency': lambda: validate_build_workflow_concurrency(repo_root),
        'build-matrix-scope': lambda: validate_build_matrix_scope(repo_root),
        'build-compile-cpu-flags': lambda: validate_build_compile_cpu_flags(repo_root),
        'checkout-scope': lambda: validate_checkout_scope(repo_root),
        'metadata-history-scope': lambda: validate_metadata_history_scope(repo_root, bash),
        'pgo-fetch-scope': lambda: validate_pgo_fetch_scope(repo_root),
        'windows-dependency-smoke-scope': lambda: validate_windows_dependency_smoke_scope(repo_root),
        'build-log-scope': lambda: validate_build_log_scope(repo_root),
        'build-compile-scope': lambda: validate_build_compile_scope(repo_root),
        'package-scope': lambda: validate_package_scope(repo_root, bash),
        'warning-scan-full-gate': lambda: validate_warning_scan_full_gate(repo_root),
        'pgo-consume-helper': lambda: validate_pgo_consume_helper(repo_root),
        'raw-smoke': lambda: validate_raw_smoke(repo_root),
        'threaded-me-smoke': lambda: validate_threaded_me_smoke(repo_root),
        'threaded-me-stress-smoke': lambda: validate_threaded_me_stress_smoke(repo_root),
        'cli-long-input-smoke': lambda: validate_cli_long_input_smoke(repo_root),
        'mkv-smoke': lambda: validate_mkv_smoke(repo_root),
        'lavf-smoke': lambda: validate_lavf_smoke(repo_root),
        'qpfile-smoke': lambda: validate_qpfile_smoke(repo_root),
        'nalu-file-smoke': lambda: validate_nalu_file_smoke(repo_root),
        'output-depth-invalid-smoke': lambda: validate_output_depth_invalid_smoke(repo_root),
        'chunk-negative-smoke': lambda: validate_chunk_negative_smoke(repo_root),
        'qpfile-oversized-smoke': lambda: validate_qpfile_oversized_smoke(repo_root),
        'zonefile-smoke': lambda: validate_zonefile_smoke(repo_root),
        'zonefile-oversized-smoke': lambda: validate_zonefile_oversized_smoke(repo_root),
        'recon-smoke': lambda: validate_recon_smoke(repo_root),
        'analysis-save-load-smoke': lambda: validate_analysis_save_load_smoke(repo_root),
        '2pass-stats-smoke': lambda: validate_2pass_stats_smoke(repo_root),
        'abr-ladder-smoke': lambda: validate_abr_ladder_smoke(repo_root),
        'video-signal-type-preset-oversized-smoke': lambda: validate_video_signal_type_preset_oversized_smoke(repo_root),
        'gop-output-smoke': lambda: validate_gop_output_smoke(repo_root),
        'mp4-smokes': lambda: validate_mp4_smokes(repo_root),
        'zimg-smoke': lambda: validate_zimg_smoke(repo_root),
        'linux-gcc-smoke': lambda: validate_linux_gcc_smoke(repo_root),
        'linux-cmake-setup': lambda: validate_linux_cmake_setup(repo_root),
        'linux-sanitizer-toolchain-setup': lambda: validate_linux_sanitizer_toolchain_setup(repo_root),
        'warning-scan-runtime-smokes': lambda: validate_warning_scan_runtime_smokes(repo_root),
        'gnu20-diagnostic-steps': lambda: validate_gnu20_diagnostic_steps(repo_root),
        'dependency-suffixes': lambda: validate_dependency_suffixes(repo_root, args.before, args.after),
        'release-needs': lambda: validate_release_needs(repo_root),
        'compile-commands': lambda: validate_compile_commands(repo_root),
        'gnu20-legacy-guard-bundle': lambda: validate_gnu20_legacy_guard_bundle(repo_root),
        'profdata-metadata': lambda: validate_profdata_metadata(repo_root),
        'cli-nullptr-usage': lambda: validate_cli_nullptr_usage(repo_root),
        'cli-volatile-usage': lambda: validate_cli_volatile_usage(repo_root),
        'json11-noexcept-usage': lambda: validate_json11_noexcept_usage(repo_root),
        'json11-number-boundary-safety': lambda: validate_json11_number_boundary_safety(repo_root),
        'json11-unicode-escape-parse-safety': lambda: validate_json11_unicode_escape_parse_safety(repo_root),
        'json11-short-int-parse-safety': lambda: validate_json11_short_int_parse_safety(repo_root),
        'json11-slow-float-token-bounds': lambda: validate_json11_slow_float_token_bounds(repo_root),
        'source-null-exception-usage': lambda: validate_source_null_exception_usage(repo_root),
        'remaining-null-boundaries': lambda: validate_remaining_null_boundaries(repo_root),
        'fps-parse-safety': lambda: validate_fps_parse_safety(repo_root),
        'frame-threads-parse-safety': lambda: validate_frame_threads_parse_safety(repo_root),
        'total-frames-parse-safety': lambda: validate_total_frames_parse_safety(repo_root),
        'level-idc-parse-safety': lambda: validate_level_idc_parse_safety(repo_root),
        'log-level-parse-safety': lambda: validate_log_level_parse_safety(repo_root),
        'qpstep-parse-safety': lambda: validate_qpstep_parse_safety(repo_root),
        'qscale-mode-parse-safety': lambda: validate_qscale_mode_parse_safety(repo_root),
        'subme-parse-safety': lambda: validate_subme_parse_safety(repo_root),
        'cli-input-open-cleanup': lambda: validate_cli_input_open_cleanup(repo_root),
        'cli-input-validation-cleanup': lambda: validate_cli_input_validation_cleanup(repo_root),
        'cli-output-open-cleanup': lambda: validate_cli_output_open_cleanup(repo_root),
        'cli-profile-apply-cleanup': lambda: validate_cli_profile_apply_cleanup(repo_root),
        'cli-deprecated-parallel-log-args': lambda: validate_cli_deprecated_parallel_log_args(repo_root),
        'scenecut-trailing-arg-diagnostics': lambda: validate_scenecut_trailing_arg_diagnostics(repo_root),
        'cli-recon-basename-cleanup': lambda: validate_cli_recon_basename_cleanup(repo_root),
        'cli-vmaf-input-open-cleanup': lambda: validate_cli_vmaf_input_open_cleanup(repo_root),
        'cli-vmaf-recon-preconditions-cleanup': lambda: validate_cli_vmaf_recon_preconditions_cleanup(repo_root),
        'cli-recon-open-guard': lambda: validate_cli_recon_open_guard(repo_root),
        'svt-app-context-staging': lambda: validate_svt_app_context_staging(repo_root),
        'svt-param-storage-replace-safety': lambda: validate_svt_param_storage_replace_safety(repo_root),
        'svt-nal-buffer-replace-safety': lambda: validate_svt_nal_buffer_replace_safety(repo_root),
        'nal-takecontents-realloc-safety': lambda: validate_nal_takecontents_realloc_safety(repo_root),
        'svt-rpu-payload-replace-safety': lambda: validate_svt_rpu_payload_replace_safety(repo_root),
        'configure-zone-svt-staging': lambda: validate_configure_zone_svt_staging(repo_root),
        'svt-pools-parse-safety': lambda: validate_svt_pools_parse_safety(repo_root),
        'svt-deblock-parse-usage': lambda: validate_svt_deblock_parse_usage(repo_root),
        'svt-frame-threads-parse-safety': lambda: validate_svt_frame_threads_parse_safety(repo_root),
        'pgo-consume-chain': lambda: validate_pgo_consume_chain(repo_root),
        'source-test-vectors': lambda: validate_source_test_vectors(repo_root),
        'source-legacy-patterns': lambda: validate_source_legacy_patterns(repo_root),
        'all-source-legacy-patterns': lambda: validate_all_source_legacy_patterns(repo_root),
        'csvlog-reopen-state': lambda: validate_csvlog_reopen_state(repo_root),
        'csvlog-open-state': lambda: validate_csvlog_open_state(repo_root),
        'reconplay-start-failure-guard': lambda: validate_reconplay_start_failure_guard(repo_root),
        'threadpool-create-rollback': lambda: validate_threadpool_create_rollback(repo_root),
        'threadpool-start-rollback': lambda: validate_threadpool_start_rollback(repo_root),
        'frameencoder-start-failure-guard': lambda: validate_frameencoder_start_failure_guard(repo_root),
        'threadedme-start-failure-guard': lambda: validate_threadedme_start_failure_guard(repo_root),
        'input-reader-start-failure-guard': lambda: validate_input_reader_start_failure_guard(repo_root),
        'input-framecount-seek-guard': lambda: validate_input_framecount_seek_guard(repo_root),
        'encoder-threadpool-start-failure-guard': lambda: validate_encoder_threadpool_start_failure_guard(repo_root),
        'encoder-open-fail-cleanup': lambda: validate_encoder_open_fail_cleanup(repo_root),
        'lookahead-alloc-guards': lambda: validate_lookahead_alloc_guards(repo_root),
        'frameencoder-init-alloc-guards': lambda: validate_frameencoder_init_alloc_guards(repo_root),
        'bitcost-alloc-guards': lambda: validate_bitcost_alloc_guards(repo_root),
        'scaler-chroma-dims-guard': lambda: validate_scaler_chroma_dims_guard(repo_root),
        'tonemap-payload-safety': lambda: validate_tonemap_payload_safety(repo_root),
        'temporalfilter-alloc-counts': lambda: validate_temporalfilter_alloc_counts(repo_root),
        'frameencoder-substream-alloc-guards': lambda: validate_frameencoder_substream_alloc_guards(repo_root),
        'frameencoder-initialize-geoms-staging': lambda: validate_frameencoder_initialize_geoms_staging(repo_root),
        'frame-create-subsample-staging': lambda: validate_frame_create_subsample_staging(repo_root),
        'frame-create-rowstate-alloc-guards': lambda: validate_frame_create_rowstate_alloc_guards(repo_root),
        'frame-create-mcstf-refpic-guards': lambda: validate_frame_create_mcstf_refpic_guards(repo_root),
        'frame-create-mcstf-fenc-pic-guards': lambda: validate_frame_create_mcstffencpic_guards(repo_root),
        'frame-create-top-alloc-guards': lambda: validate_frame_create_top_alloc_guards(repo_root),
        'frame-alloc-encode-data-guards': lambda: validate_frame_alloc_encode_data_guards(repo_root),
        'x265-picture-init-null-guard': lambda: validate_x265_picture_init_null_guard(repo_root),
        'x265-param-default-null-guard': lambda: validate_x265_param_default_null_guard(repo_root),
        'x265-param-default-preset-null-guard': lambda: validate_x265_param_default_preset_null_guard(repo_root),
        'x265-param-parse-null-guard': lambda: validate_x265_param_parse_null_guard(repo_root),
        'x265-param-apply-profile-null-guard': lambda: validate_x265_param_apply_profile_null_guard(repo_root),
        'param-api-null-guards': lambda: validate_param_api_null_guards(repo_root),
        'zone-scenecut-param-parse-null-guards': lambda: validate_zone_and_scenecut_param_parse_null_guards(repo_root),
        'analysis-data-api-null-guards': lambda: validate_analysis_data_api_null_guards(repo_root),
        'query-api-output-null-guards': lambda: validate_query_api_output_null_guards(repo_root),
        'x265-dither-image-null-guards': lambda: validate_x265_dither_image_null_guards(repo_root),
        'csvlog-api-null-guards': lambda: validate_csvlog_api_null_guards(repo_root),
        'csvlog-fail-state': lambda: validate_csvlog_fail_state(repo_root),
        'vmaf-api-null-guards': lambda: validate_vmaf_api_null_guards(repo_root),
        'threadedme-create-guards': lambda: validate_threadedme_create_guards(repo_root),
        'threadpool-windows-numa-affinity-guard': lambda: validate_threadpool_windows_numa_affinity_guard(repo_root),
        'encoder-ctu-info-guards': lambda: validate_encoder_ctu_info_guards(repo_root),
        'encoder-open-alloc-guard': lambda: validate_encoder_open_alloc_guard(repo_root),
        'encoder-create-object-alloc-guards': lambda: validate_encoder_create_object_alloc_guards(repo_root),
        'encoder-create-core-alloc-guards': lambda: validate_encoder_create_core_alloc_guards(repo_root),
        'encoder-encode-frame-alloc-guards': lambda: validate_encoder_encode_frame_alloc_guards(repo_root),
        'encoder-encode-setup-rollback': lambda: validate_encoder_encode_setup_rollback(repo_root),
        'lowres-aqlayer-alloc-guards': lambda: validate_lowres_aqlayer_alloc_guards(repo_root),
        'lowres-histogram-alloc-guards': lambda: validate_lowres_histogram_alloc_guards(repo_root),
        'frame-edge-aq-alloc-guards': lambda: validate_frame_edge_aq_alloc_guards(repo_root),
        'cutree-sharedmem-alloc-guards': lambda: validate_cutree_sharedmem_alloc_guards(repo_root),
        'scaler-helper-alloc-guards': lambda: validate_scaler_helper_alloc_guards(repo_root),
        'lookahead-create-rollback': lambda: validate_lookahead_create_rollback(repo_root),
        'lookahead-tld-yuv-guards': lambda: validate_lookahead_tld_yuv_guards(repo_root),
        'sea-integral-buffer-lifecycle': lambda: validate_sea_integral_buffer_lifecycle(repo_root),
        'vmaf-temp-buffer-cleanup': lambda: validate_vmaf_temp_buffer_cleanup(repo_root),
        'encoder-rps-list-alloc-guard': lambda: validate_encoder_rps_list_alloc_guard(repo_root),
        'encoder-headers-arg-guard': lambda: validate_encoder_headers_arg_guard(repo_root),
        'wavefront-init-rollback': lambda: validate_wavefront_init_rollback(repo_root),
        'framedata-create-rollback': lambda: validate_framedata_create_rollback(repo_root),
        'scaler-init-rollback': lambda: validate_scaler_init_rollback(repo_root),
        'reconfig-save-zone-rollback': lambda: validate_reconfig_save_zone_rollback(repo_root),
        'cli-config-file-parse-usage': lambda: validate_cli_config_file_parse_usage(repo_root),
        'lambda-file-parse-usage': lambda: validate_lambda_file_parse_usage(repo_root),
        'lambda-file-error-state': lambda: validate_lambda_file_error_state(repo_root),
        'param-checked-parse-usage': lambda: validate_param_checked_parse_usage(repo_root),
        'scenecut-qp-macro-cleanup': lambda: validate_scenecut_qp_macro_cleanup(repo_root),
        'zone-param-macro-cleanup': lambda: validate_zone_param_macro_cleanup(repo_root),
        'param-parse-macro-cleanup': lambda: validate_param_parse_macro_cleanup(repo_root),
        'qpfile-parse-usage': lambda: validate_qpfile_parse_usage(repo_root),
        'qpfile-error-state': lambda: validate_qpfile_error_state(repo_root),
        'strict-scan-parsing-usage': lambda: validate_strict_scan_parsing_usage(repo_root),
        'zonefile-parse-usage': lambda: validate_zonefile_parse_usage(repo_root),
        'external-input-atoi-usage': lambda: validate_external_input_atoi_usage(repo_root),
        'dolby-vision-rpu-parse-usage': lambda: validate_dolby_vision_rpu_parse_usage(repo_root),
        'cmake-cxx20-contract': lambda: validate_cmake_cxx20_contract(repo_root),
        'nalu-file-parse-usage': lambda: validate_nalu_file_parse_usage(repo_root),
        'nalu-file-error-state': lambda: validate_nalu_file_error_state(repo_root),
        'analysis-reuse-refine-parse-safety': lambda: validate_analysis_reuse_refine_parse_safety(repo_root),
        'analysis-output-fail-state': lambda: validate_analysis_output_fail_state(repo_root),
        'scalinglist-parse-usage': lambda: validate_scalinglist_parse_usage(repo_root),
        'checked-parse-helper-safety': lambda: validate_checked_parse_helper_safety(repo_root),
        'param-uint-token-safety': lambda: validate_param_uint_token_safety(repo_root),
        'mkv-header-cleanup-state': lambda: validate_mkv_header_cleanup_state(repo_root),
        'vmaf-file-cleanup-state': lambda: validate_vmaf_file_cleanup_state(repo_root),
        'vmaf-frame-read-state': lambda: validate_vmaf_frame_read_state(repo_root),
        'vmaf-picture-read-failure': lambda: validate_vmaf_picture_read_failure(repo_root),
        'vmaf-score-failure-propagation': lambda: validate_vmaf_score_failure_propagation(repo_root),
        'vmaf-data-cleanup-state': lambda: validate_vmaf_data_cleanup_state(repo_root),
        'param-double-token-safety': lambda: validate_param_double_token_safety(repo_root),
        'param-pair-parse-safety': lambda: validate_param_pair_parse_safety(repo_root),
        'parse-name-assignment-safety': lambda: validate_parse_name_assignment_safety(repo_root),
        'ratecontrol-first-pass-parse-usage': lambda: validate_ratecontrol_first_pass_parse_usage(repo_root),
        'preset-index-parse-usage': lambda: validate_preset_index_parse_usage(repo_root),
        'cpu-list-parse-usage': lambda: validate_cpu_list_parse_usage(repo_root),
        'interlace-parse-safety': lambda: validate_interlace_parse_safety(repo_root),
        'rdoq-level-parse-safety': lambda: validate_rdoq_level_parse_safety(repo_root),
        'ratecontrol-numeric-helper-safety': lambda: validate_ratecontrol_numeric_helper_safety(repo_root),
        'ratecontrol-stats-parse-usage': lambda: validate_ratecontrol_stats_parse_usage(repo_root),
        'ratecontrol-stats-line-parse-usage': lambda: validate_ratecontrol_stats_line_parse_usage(repo_root),
        'ratecontrol-stats-prefix-parse-usage': lambda: validate_ratecontrol_stats_prefix_parse_usage(repo_root),
        'param-bool-numeric-int-safety': lambda: validate_param_bool_numeric_int_safety(repo_root),
        'bitrate-mode-parse-safety': lambda: validate_bitrate_mode_parse_safety(repo_root),
        'qp-mode-parse-safety': lambda: validate_qp_mode_parse_safety(repo_root),
        'strict-cbr-parse-safety': lambda: validate_strict_cbr_parse_safety(repo_root),
        'sao-create-rollback': lambda: validate_sao_create_rollback(repo_root),
        'svt-bitrate-mode-parse-safety': lambda: validate_svt_bitrate_mode_parse_safety(repo_root),
        'api-zone-open-staging': lambda: validate_api_zone_open_staging(repo_root),
        'copy-params-zone-replace-safety': lambda: validate_copy_params_zone_replace_safety(repo_root),
        'encoder-parameters-output-safety': lambda: validate_encoder_parameters_output_safety(repo_root),
        'encoder-get-stats-size-guard': lambda: validate_encoder_get_stats_size_guard(repo_root),
        'cli-output-failure-full-cleanup': lambda: validate_cli_output_failure_full_cleanup(repo_root),
        'lavf-openfile-cleanup': lambda: validate_lavf_openfile_cleanup(repo_root),
        'svt-qp-mode-parse-safety': lambda: validate_svt_qp_mode_parse_safety(repo_root),
        'reader-thread-alloc-guards': lambda: validate_reader_thread_alloc_guards(repo_root),
        'scaler-thread-alloc-guards': lambda: validate_scaler_thread_alloc_guards(repo_root),
        'hdr10-json-metadata-ownership': lambda: validate_hdr10_json_metadata_ownership(repo_root),
        'temporalfilter-refpic-rollback': lambda: validate_temporalfilter_refpic_rollback(repo_root),
        'temporalfilter-refpic-state-init': lambda: validate_temporalfilter_refpic_state_init(repo_root),
        'temporalfilter-metld-yuv-guards': lambda: validate_temporalfilter_metld_yuv_guards(repo_root),
        'param-string-replace-safety': lambda: validate_param_string_replace_safety(repo_root),
        'zones-parse-safety': lambda: validate_zones_parse_safety(repo_root),
        'raw-output-fail-state': lambda: validate_raw_output_fail_state(repo_root),
        'cli-progress-file-state': lambda: validate_cli_progress_file_state(repo_root),
        'raw-output-write-guard': lambda: validate_raw_output_write_guard(repo_root),
        'raw-stdout-flush-state': lambda: validate_raw_stdout_flush_state(repo_root),
        'mkv-output-fail-state': lambda: validate_mkv_output_fail_state(repo_root),
        'mkv-close-fail-state': lambda: validate_mkv_close_fail_state(repo_root),
        'recon-output-write-guard': lambda: validate_recon_output_write_guard(repo_root),
        'recon-output-stream-state': lambda: validate_recon_output_stream_state(repo_root),
        'y4m-recon-seek-guard': lambda: validate_y4m_recon_seek_guard(repo_root),
        'recon-finalize-state': lambda: validate_recon_finalize_state(repo_root),
        'gop-options-fail-state': lambda: validate_gop_options_fail_state(repo_root),
        'gop-output-fail-state': lambda: validate_gop_output_fail_state(repo_root),
        'gop-smart-fwrite-retry-guard': lambda: validate_gop_smart_fwrite_retry_guard(repo_root),
        'y4m-yuv-row-buffer-alloc-guard': lambda: validate_y4m_yuv_row_buffer_alloc_guard(repo_root),
        'output-open-alloc-guards': lambda: validate_output_open_alloc_guards(repo_root),
        'vmaf-recon-state-safety': lambda: validate_vmaf_recon_state_safety(repo_root),
        'reconplay-pipe-fail-state': lambda: validate_reconplay_pipe_fail_state(repo_root),
        'lambda-file-failfast': lambda: validate_lambda_file_failfast(repo_root),
        'lavf-buffer-replace-safety': lambda: validate_lavf_buffer_replace_safety(repo_root),
        'svt-pools-parse-usage': lambda: validate_svt_pools_parse_usage(repo_root),
        'threadpool-cpu-frequency-parse-usage': lambda: validate_threadpool_cpu_frequency_parse_usage(repo_root),
        'threadpool-cpu-frequency-tail-guard': lambda: validate_threadpool_cpu_frequency_tail_guard(repo_root),
        'lavf-framecount-parse-safety': lambda: validate_lavf_framecount_parse_safety(repo_root),
        'gop-close-fail-state': lambda: validate_gop_close_fail_state(repo_root),
        'param-bool-numeric-double-safety': lambda: validate_param_bool_numeric_double_safety(repo_root),
        'csv-log-level-parse-safety': lambda: validate_csv_log_level_parse_safety(repo_root),
        'bool-int-parse-safety': lambda: validate_bool_int_parse_safety(repo_root),
        'aq-mode-parse-safety': lambda: validate_aq_mode_parse_safety(repo_root),
        'multiview-scc-parse-safety': lambda: validate_multiview_scc_parse_safety(repo_root),
        'view-layer-limit-safety': lambda: validate_view_layer_limit_safety(repo_root),
        'bframes-parse-safety': lambda: validate_bframes_parse_safety(repo_root),
        'bframe-bias-parse-safety': lambda: validate_bframe_bias_parse_safety(repo_root),
        'keyint-parse-safety': lambda: validate_keyint_parse_safety(repo_root),
        'min-keyint-parse-safety': lambda: validate_min_keyint_parse_safety(repo_root),
        'ip-pb-ratio-parse-safety': lambda: validate_ip_pb_ratio_parse_safety(repo_root),
        'vbv-end-fr-adj-safety': lambda: validate_vbv_end_frame_adjust_safety(repo_root),
        'zone-alloc-size-safety': lambda: validate_zone_alloc_size_safety(repo_root),
        'ref-parse-safety': lambda: validate_ref_parse_safety(repo_root),
        'radl-parse-safety': lambda: validate_radl_parse_safety(repo_root),
        'cbqpoffs-parse-safety': lambda: validate_cbqpoffs_parse_safety(repo_root),
        'crqpoffs-parse-safety': lambda: validate_crqpoffs_parse_safety(repo_root),
        'pass-parse-safety': lambda: validate_pass_parse_safety(repo_root),
        'qg-size-parse-safety': lambda: validate_qg_size_parse_safety(repo_root),
        'qpmin-parse-safety': lambda: validate_qpmin_parse_safety(repo_root),
        'qpmax-parse-safety': lambda: validate_qpmax_parse_safety(repo_root),
        'chromaloc-parse-safety': lambda: validate_chromaloc_parse_safety(repo_root),
        'vbv-maxrate-parse-safety': lambda: validate_vbv_maxrate_parse_safety(repo_root),
        'vbv-bufsize-parse-safety': lambda: validate_vbv_bufsize_parse_safety(repo_root),
        'log2-max-poc-lsb-parse-safety': lambda: validate_log2_max_poc_lsb_parse_safety(repo_root),
        'nr-intra-parse-safety': lambda: validate_nr_intra_parse_safety(repo_root),
        'nr-inter-parse-safety': lambda: validate_nr_inter_parse_safety(repo_root),
        'rc-lookahead-parse-safety': lambda: validate_rc_lookahead_parse_safety(repo_root),
        'slices-parse-safety': lambda: validate_slices_parse_safety(repo_root),
        'limit-tu-parse-safety': lambda: validate_limit_tu_parse_safety(repo_root),
        'lookahead-threads-parse-safety': lambda: validate_lookahead_threads_parse_safety(repo_root),
        'vbv-fullness-parse-safety': lambda: validate_vbv_fullness_parse_safety(repo_root),
        'rdpenalty-parse-safety': lambda: validate_rdpenalty_parse_safety(repo_root),
        'gop-lookahead-parse-safety': lambda: validate_gop_lookahead_parse_safety(repo_root),
        'gop-lookahead-usage-safety': lambda: validate_gop_lookahead_usage_safety(repo_root),
        'zonefile-startframe-safety': lambda: validate_zonefile_startframe_safety(repo_root),
        'reconfig-window-size-safety': lambda: validate_reconfig_window_size_safety(repo_root),
        'no-reset-zone-prefill-guard': lambda: validate_no_reset_zone_prefill_guard(repo_root),
        'common-logfile-open-state': lambda: validate_common_logfile_open_state(repo_root),
        'common-logfile-close-state': lambda: validate_common_logfile_close_state(repo_root),
        'common-slurp-open-state': lambda: validate_common_slurp_open_state(repo_root),
        'common-slurp-close-state': lambda: validate_common_slurp_close_state(repo_root),
        'common-slurp-size-guard': lambda: validate_common_slurp_size_guard(repo_root),
        'cutree-sharedmem-name-guard': lambda: validate_cutree_sharedmem_name_guard(repo_root),
        'mkv-writer-open-state': lambda: validate_mkv_writer_open_state(repo_root),
        'mkv-writer-close-state': lambda: validate_mkv_writer_close_state(repo_root),
        'riscv-cpuinfo-open-state': lambda: validate_riscv_cpuinfo_open_state(repo_root),
        'riscv-cpuinfo-close-state': lambda: validate_riscv_cpuinfo_close_state(repo_root),
        'cli-destroy-close-state': lambda: validate_cli_destroy_close_state(repo_root),
        'encoder-destroy-close-state': lambda: validate_encoder_destroy_close_state(repo_root),
        'lambda-file-close-state': lambda: validate_lambda_file_close_state(repo_root),
        'film-grain-close-state': lambda: validate_film_grain_close_state(repo_root),
        'gop-cleanup-close-state': lambda: validate_gop_cleanup_close_state(repo_root),
        'mp4-preflight-close-state': lambda: validate_mp4_preflight_close_state(repo_root),
        'gop-early-close-state': lambda: validate_gop_early_close_state(repo_root),
        'gop-intermediate-close-state': lambda: validate_gop_intermediate_close_state(repo_root),
        'ratecontrol-destroy-close-state': lambda: validate_ratecontrol_destroy_close_state(repo_root),
        'ratecontrol-write-fail-state': lambda: validate_ratecontrol_write_fail_state(repo_root),
        'ratecontrol-cutree-read-fail-state': lambda: validate_ratecontrol_cutree_read_fail_state(repo_root),
        'mp4-handle-close-state': lambda: validate_mp4_handle_close_state(repo_root),
        'mp4-header-sei-alloc-guard': lambda: validate_mp4_header_sei_alloc_guard(repo_root),
        'raw-close-state': lambda: validate_raw_close_state(repo_root),
        'raw-open-cleanup-state': lambda: validate_raw_open_cleanup_state(repo_root),
        'x265-check-macro-open-state': lambda: validate_x265_check_macro_open_state(repo_root),
        'x265-check-macro-close-state': lambda: validate_x265_check_macro_close_state(repo_root),
        'scalinglist-close-state': lambda: validate_scalinglist_close_state(repo_root),
        'vmaf-encoder-log-close-state': lambda: validate_vmaf_encoder_log_close_state(repo_root),
        'y4m-input-close-state': lambda: validate_y4m_input_close_state(repo_root),
        'yuv-input-close-state': lambda: validate_yuv_input_close_state(repo_root),
        'reconplay-pclose-state': lambda: validate_reconplay_pclose_state(repo_root),
        'multiview-parse-close-state': lambda: validate_multiview_parse_close_state(repo_root),
        'multiview-config-parse-usage': lambda: validate_multiview_config_parse_usage(repo_root),
        'scenecut-aware-qp-config-parse-usage': lambda: validate_scenecut_aware_qp_config_parse_usage(repo_root),
        'scenecut-aware-qp-parse-safety': lambda: validate_scenecut_aware_qp_parse_safety(repo_root),
        'abr-parse-cleanup-state': lambda: validate_abr_parse_cleanup_state(repo_root),
        'scenecut-qp-cleanup-state': lambda: validate_scenecut_qp_cleanup_state(repo_root),
        'x265-main-cleanup-state': lambda: validate_x265_main_cleanup_state(repo_root),
        'abr-config-parse-usage': lambda: validate_abr_config_parse_usage(repo_root),
        'abr-init-result-propagation': lambda: validate_abr_init_result_propagation(repo_root),
        'abr-init-helper-cleanup': lambda: validate_abr_init_helper_cleanup(repo_root),
        'abr-init-reader-rollback': lambda: validate_abr_init_reader_rollback(repo_root),
        'abr-init-api-null': lambda: validate_abr_init_api_null_guard(repo_root),
        'abr-init-output-null': lambda: validate_abr_init_output_null_guard(repo_root),
        'abr-init-filter-null': lambda: validate_abr_init_filter_null_guard(repo_root),
        'abr-init-reader-alloc': lambda: validate_abr_init_reader_alloc_guard(repo_root),
        'abr-start-threads-failure-propagation': lambda: validate_abr_start_threads_failure_propagation(repo_root),
        'abr-primary-param-guards': lambda: validate_abr_primary_param_guards(repo_root),
        'abr-ctor-top-guards': lambda: validate_abr_ctor_top_guards(repo_root),
        'abr-queue-picture-guards': lambda: validate_abr_queue_picture_guards(repo_root),
        'abr-thread-queue-state-guards': lambda: validate_abr_thread_queue_state_guards(repo_root),
        'abr-counter-state-guards': lambda: validate_abr_counter_state_guards(repo_root),
        'abr-picture-state-guards': lambda: validate_abr_picture_state_guards(repo_root),
        'abr-setreuselevel-ref': lambda: validate_abr_setreuselevel_ref_guard(repo_root),
        'abr-thread-multiview-field-guard': lambda: validate_abr_thread_multiview_field_guard(repo_root),
        'abr-thread-multiview-input-guard': lambda: validate_abr_thread_multiview_input_guard(repo_root),
        'abr-thread-reconplay-alloc-guard': lambda: validate_abr_thread_reconplay_alloc_guard(repo_root),
        'abr-thread-pic-in-reset-guard': lambda: validate_abr_thread_pic_in_reset_guard(repo_root),
        'abr-thread-dolby-rpu-eof-guard': lambda: validate_abr_thread_dolby_rpu_eof_guard(repo_root),
        'abr-thread-output-null-guard': lambda: validate_abr_thread_output_null_guard(repo_root),
        'abr-thread-fail-output': lambda: validate_abr_thread_fail_output_guard(repo_root),
        'abr-thread-fail-encoder': lambda: validate_abr_thread_fail_encoder_guard(repo_root),
        'abr-thread-output-picture': lambda: validate_abr_thread_output_picture_guard(repo_root),
        'abr-thread-layered-recon': lambda: validate_abr_thread_layered_recon_guard(repo_root),
        'abr-thread-api-null': lambda: validate_abr_thread_api_null_guard(repo_root),
        'abr-thread-dither-input': lambda: validate_abr_thread_dither_input_guard(repo_root),
        'abr-thread-field-buffer': lambda: validate_abr_thread_field_buffer_guard(repo_root),
        'abr-thread-field-buffer-state': lambda: validate_abr_thread_field_buffer_state_guard(repo_root),
        'abr-thread-field-view-usage': lambda: validate_abr_thread_field_view_usage(repo_root),
        'abr-thread-field-layout': lambda: validate_abr_thread_field_layout_guard(repo_root),
        'abr-thread-field-plane': lambda: validate_abr_thread_field_plane_guard(repo_root),
        'abr-thread-field-reuse': lambda: validate_abr_thread_field_reuse_guard(repo_root),
        'abr-thread-pts-queue-alloc': lambda: validate_abr_thread_pts_queue_alloc_guard(repo_root),
        'abr-thread-recon-state': lambda: validate_abr_thread_recon_state_guard(repo_root),
        'abr-thread-recon-write': lambda: validate_abr_thread_recon_write_guard(repo_root),
        'abr-copyinfo-inter-arrays': lambda: validate_abr_copyinfo_inter_arrays_guard(repo_root),
        'abr-copyinfo-intra-arrays': lambda: validate_abr_copyinfo_intra_arrays_guard(repo_root),
        'abr-copyinfo-src': lambda: validate_abr_copyinfo_src_guard(repo_root),
        'abr-copyinfo-analysis-buffer': lambda: validate_abr_copyinfo_analysis_buffer_guard(repo_root),
        'abr-analysis-slot-wait': lambda: validate_abr_analysis_slot_wait_guard(repo_root),
        'abr-copyinfo-vbv-lookahead': lambda: validate_abr_copyinfo_vbv_lookahead_guard(repo_root),
        'abr-allocbuffers-top-guards': lambda: validate_abr_allocbuffers_top_guards(repo_root),
        'abr-allocbuffers-partial-cleanup': lambda: validate_abr_allocbuffers_partial_cleanup(repo_root),
        'abr-allocbuffers-queue-guards': lambda: validate_abr_allocbuffers_queue_guards(repo_root),
        'abr-allocbuffers-analysisread': lambda: validate_abr_allocbuffers_analysisread_guard(repo_root),
        'abr-allocbuffers-analysiswrite': lambda: validate_abr_allocbuffers_analysiswrite_guard(repo_root),
        'abr-allocbuffers-picidx': lambda: validate_abr_allocbuffers_picidx_guard(repo_root),
        'abr-allocbuffers-readflag': lambda: validate_abr_allocbuffers_readflag_guard(repo_root),
        'abr-readpicture-srcpic': lambda: validate_abr_readpicture_srcpic_guard(repo_root),
        'abr-readpicture-analysis': lambda: validate_abr_readpicture_analysis_guard(repo_root),
        'abr-thread-readpicture-failure-guard': lambda: validate_abr_thread_readpicture_failure_guard(repo_root),
        'abr-readpicture-analysis-queue': lambda: validate_abr_readpicture_analysis_queue_guard(repo_root),
        'abr-scaler-videodesc-alloc': lambda: validate_abr_scaler_videodesc_alloc_guard(repo_root),
        'abr-scaler-videodesc-ownership': lambda: validate_abr_scaler_videodesc_ownership(repo_root),
        'abr-scaler-init-failure-handling': lambda: validate_abr_scaler_init_failure_handling(repo_root),
        'abr-thread-analysis-read': lambda: validate_abr_thread_analysis_read_guard(repo_root),
        'analysis-intra-alloc-guards': lambda: validate_analysis_intra_alloc_guards(repo_root),
        'analysis-inter-alloc-guards': lambda: validate_analysis_inter_alloc_guards(repo_root),
        'analysis-inter-motion-alloc-guards': lambda: validate_analysis_inter_motion_alloc_guards(repo_root),
        'analysis-inter-temp-luma-alloc-guard': lambda: validate_analysis_inter_temp_luma_alloc_guard(repo_root),
        'analysis-inter-depth-run-guard': lambda: validate_analysis_inter_depth_run_guard(repo_root),
        'analysis-cache-cost-guards': lambda: validate_analysis_cache_cost_guards(repo_root),
        'scaled-analysis-load-alloc-guards': lambda: validate_scaled_analysis_load_alloc_guards(repo_root),
        'analysis-2pass-load-cleanup': lambda: validate_analysis_2pass_load_cleanup(repo_root),
        'picyuv-offset-rollback': lambda: validate_picyuv_offset_rollback(repo_root),
        'motion-reference-init-guards': lambda: validate_motion_reference_init_guards(repo_root),
        'motionestimate-init-guard': lambda: validate_motionestimate_init_guard(repo_root),
        'motion-sea-scratch-guard': lambda: validate_motion_sea_scratch_guard(repo_root),
        'scaler-slice-linebuf-init': lambda: validate_scaler_slice_linebuf_init(repo_root),
        'analysis-load-staging-cleanup': lambda: validate_analysis_load_staging_cleanup(repo_root),
        'atc-sei-parse-safety': lambda: validate_atc_sei_parse_safety(repo_root),
        'chunk-start-parse-safety': lambda: validate_chunk_start_parse_safety(repo_root),
        'chunk-end-parse-safety': lambda: validate_chunk_end_parse_safety(repo_root),
        'deblock-parse-safety': lambda: validate_deblock_parse_safety(repo_root),
        'hash-parse-safety': lambda: validate_hash_parse_safety(repo_root),
        'hme-parse-safety': lambda: validate_hme_parse_safety(repo_root),
        'lookahead-slices-parse-safety': lambda: validate_lookahead_slices_parse_safety(repo_root),
        'merange-parse-safety': lambda: validate_merange_parse_safety(repo_root),
        'misc-control-parse-safety': lambda: validate_misc_control_parse_safety(repo_root),
        'pic-struct-parse-safety': lambda: validate_pic_struct_parse_safety(repo_root),
        'psy-scale-parse-safety': lambda: validate_psy_scale_parse_safety(repo_root),
        'rskip-parse-safety': lambda: validate_rskip_parse_safety(repo_root),
        'rskip-edge-threshold-parse-safety': lambda: validate_rskip_edge_threshold_parse_safety(repo_root),
        'sar-parse-safety': lambda: validate_sar_parse_safety(repo_root),
        'selective-sao-parse-safety': lambda: validate_selective_sao_parse_safety(repo_root),
        'ssim-rd-parse-safety': lambda: validate_ssim_rd_parse_safety(repo_root),
        'temporal-layers-parse-safety': lambda: validate_temporal_layers_parse_safety(repo_root),
        'uint32-token-parse-safety': lambda: validate_uint32_token_parse_safety(repo_root),
        'cli-inputfn-alloc-guard': lambda: validate_cli_inputfn_alloc_guard(repo_root),
        'cli-vmaf-format-cleanup': lambda: validate_cli_vmaf_format_cleanup(repo_root),
        'input-filename-copy-usage': lambda: validate_input_filename_copy_usage(repo_root),
        'print-status-progress-guard': lambda: validate_print_status_progress_guard(repo_root),
        'recon-basename-parse-usage': lambda: validate_recon_basename_parse_usage(repo_root),
        'zonefile-parse-no-exit': lambda: validate_zonefile_parse_no_exit(repo_root),
        'svt-aud-parse-safety': lambda: validate_svt_aud_parse_safety(repo_root),
        'svt-base-layer-switch-mode-parse-safety': lambda: validate_svt_base_layer_switch_mode_parse_safety(repo_root),
        'svt-compressed-ten-bit-parse-safety': lambda: validate_svt_compressed_ten_bit_parse_safety(repo_root),
        'svt-constrained-intra-parse-safety': lambda: validate_svt_constrained_intra_parse_safety(repo_root),
        'svt-fps-in-vps-parse-safety': lambda: validate_svt_fps_in_vps_parse_safety(repo_root),
        'svt-frames-to-be-encoded-parse-safety': lambda: validate_svt_frames_to_be_encoded_parse_safety(repo_root),
        'svt-hdr-parse-safety': lambda: validate_svt_hdr_parse_safety(repo_root),
        'svt-hierarchical-level-parse-safety': lambda: validate_svt_hierarchical_level_parse_safety(repo_root),
        'svt-high-tier-parse-safety': lambda: validate_svt_high_tier_parse_safety(repo_root),
        'svt-hrd-parse-safety': lambda: validate_svt_hrd_parse_safety(repo_root),
        'svt-input-depth-parse-safety': lambda: validate_svt_input_depth_parse_safety(repo_root),
        'svt-keyint-parse-safety': lambda: validate_svt_keyint_parse_safety(repo_root),
        'svt-master-display-parse-safety': lambda: validate_svt_master_display_parse_safety(repo_root),
        'svt-nalu-file-parse-safety': lambda: validate_svt_nalu_file_parse_safety(repo_root),
        'svt-pred-struct-parse-safety': lambda: validate_svt_pred_struct_parse_safety(repo_root),
        'svt-qpmax-parse-safety': lambda: validate_svt_qpmax_parse_safety(repo_root),
        'svt-qpmin-parse-safety': lambda: validate_svt_qpmin_parse_safety(repo_root),
        'svt-rc-lookahead-parse-safety': lambda: validate_svt_rc_lookahead_parse_safety(repo_root),
        'svt-sao-parse-safety': lambda: validate_svt_sao_parse_safety(repo_root),
        'svt-scenecut-parse-safety': lambda: validate_svt_scenecut_parse_safety(repo_root),
        'svt-search-height-parse-safety': lambda: validate_svt_search_height_parse_safety(repo_root),
        'svt-search-width-parse-safety': lambda: validate_svt_search_width_parse_safety(repo_root),
        'svt-speed-control-parse-safety': lambda: validate_svt_speed_control_parse_safety(repo_root),
        'svt-vbv-bufsize-parse-safety': lambda: validate_svt_vbv_bufsize_parse_safety(repo_root),
        'svt-vbv-init-parse-safety': lambda: validate_svt_vbv_init_parse_safety(repo_root),
        'svt-vbv-maxrate-parse-safety': lambda: validate_svt_vbv_maxrate_parse_safety(repo_root),
        'svt-vui-timing-info-parse-safety': lambda: validate_svt_vui_timing_info_parse_safety(repo_root),
        'svt-hme-parse-safety': lambda: validate_svt_hme_parse_safety(repo_root),
        'svt-interlace-parse-safety': lambda: validate_svt_interlace_parse_safety(repo_root),
        'svt-open-gop-parse-safety': lambda: validate_svt_open_gop_parse_safety(repo_root),
        'svt-pools-exclude-both-sockets-guard': lambda: validate_svt_pools_exclude_both_sockets_guard(repo_root),
        'encoder-rpu-replace-safety': lambda: validate_encoder_rpu_replace_safety(repo_root),
        'copy-user-sei-staging': lambda: validate_copy_user_sei_staging(repo_root),
        'dup-side-data-staging': lambda: validate_dup_side_data_staging(repo_root),
        'read-user-sei-staging': lambda: validate_read_user_sei_staging(repo_root),
        'copy-picture-staging': lambda: validate_copy_picture_staging(repo_root),
        'dup-create-alloc-guards': lambda: validate_dup_create_alloc_guards(repo_root),
        'encode-quant-offsets-staging': lambda: validate_encode_quant_offsets_staging(repo_root),
        'read-user-sei-cleanup': lambda: validate_read_user_sei_cleanup(repo_root),
        'log-progress-file-parse-safety': lambda: validate_log_progress_file_parse_safety(repo_root),
        'negated-bool-alias-parse-safety': lambda: validate_negated_bool_alias_parse_safety(repo_root),
        'rd-parse-safety': lambda: validate_rd_parse_safety(repo_root),
        'limit-refs-parse-safety': lambda: validate_limit_refs_parse_safety(repo_root),
        'dup-threshold-parse-safety': lambda: validate_dup_threshold_parse_safety(repo_root),
        'vmaf-flush-cleanup': lambda: validate_vmaf_flush_cleanup(repo_root),
        'avs-buffer-replace-safety': lambda: validate_avs_buffer_replace_safety(repo_root),
        'vpy-buffer-replace-safety': lambda: validate_vpy_buffer_replace_safety(repo_root),
        'zimg-token-parse-usage': lambda: validate_zimg_token_parse_usage(repo_root),
        'zimg-init-rollback': lambda: validate_zimg_init_rollback(repo_root),
        'dynamic-hdr10-legacy-patterns': lambda: validate_dynamic_hdr10_legacy_patterns(repo_root),
        'sei-unsigned-token-safety': lambda: validate_sei_unsigned_token_safety(repo_root),
        'video-signal-type-preset-parse': lambda: validate_video_signal_type_preset_parse(repo_root),
        'sei-mastering-display-parse': lambda: validate_sei_mastering_display_parse(repo_root),
        'sao-param-staging': lambda: validate_sao_param_staging(repo_root),
        'zone-parse-replace-safety': lambda: validate_zone_parse_replace_safety(repo_root),
        'cpu-name-strdup-safety': lambda: validate_cpu_name_strdup_safety(repo_root),
        'x265-fclose-macro-state': lambda: validate_x265_fclose_macro_state(repo_root),
        'hme-param-sscanf-usage': lambda: validate_hme_param_sscanf_usage(repo_root),
        'masking-strength-scan-usage': lambda: validate_masking_strength_scan_usage(repo_root),
        'reviewed-string-copy-usage': lambda: validate_reviewed_string_copy_usage(repo_root),
        'analysis-open-state': lambda: validate_analysis_open_state(repo_root),
        'analysis-load-open-state': lambda: validate_analysis_load_open_state(repo_root),
        'cli-config-open-state': lambda: validate_cli_config_open_state(repo_root),
        'cli-help-exit-cleanup': lambda: validate_cli_help_exit_cleanup(repo_root),
        'abr-ladder-open-state': lambda: validate_abr_ladder_open_state(repo_root),
        'abr-help-exit-precedence': lambda: validate_abr_help_exit_precedence(repo_root),
        'lambda-file-open-state': lambda: validate_lambda_file_open_state(repo_root),
        'vmaf-input-open-state': lambda: validate_vmaf_input_open_state(repo_root),
        'nalu-file-open-state': lambda: validate_nalu_file_open_state(repo_root),
        'tonemap-file-open-state': lambda: validate_tonemap_file_open_state(repo_root),
        'scalinglist-open-state': lambda: validate_scalinglist_open_state(repo_root),
        'gop-open-state': lambda: validate_gop_open_state(repo_root),
        'film-grain-open-state': lambda: validate_film_grain_open_state(repo_root),
        'ratecontrol-stats-open-state': lambda: validate_ratecontrol_stats_open_state(repo_root),
    }


VALIDATOR_BASH_REQUIREMENTS = {
    'yaml-text': False,
    'yaml-parse': False,
    'run-blocks': True,
    'scan-helper': True,
    'ensure-cmake4-helper': True,
    'ensure-linux-sanitizer-toolchain-helper': True,
    'mp4-smoke-helper': True,
    'profiling-smoke-helper': True,
    'verify-ci-archive-helper': True,
    'ci-7z-helper': True,
    'runtime-smoke-suite': True,
    'mp4-smoke-suite': True,
    'source-test-vector-scripts': False,
    'dependency-update-anchors': False,
    'windows-deps-checkout-scope': False,
    'required-snippets': True,
    'build-pr-fast-gate': False,
    'warning-scan-dependencies': False,
    'windows-gcc-diagnostics-setup': False,
    'job-timeouts': False,
    'update-deps-concurrency': False,
    'build-workflow-concurrency': False,
    'build-matrix-scope': False,
    'build-compile-cpu-flags': False,
    'checkout-scope': False,
    'metadata-history-scope': False,
    'pgo-fetch-scope': False,
    'windows-dependency-smoke-scope': False,
    'build-log-scope': False,
    'build-compile-scope': False,
    'package-scope': False,
    'warning-scan-full-gate': False,
    'pgo-consume-helper': False,
    'raw-smoke': False,
    'threaded-me-smoke': False,
    'threaded-me-stress-smoke': False,
    'cli-long-input-smoke': False,
    'mkv-smoke': False,
    'lavf-smoke': False,
    'qpfile-smoke': False,
    'nalu-file-smoke': False,
    'output-depth-invalid-smoke': False,
    'chunk-negative-smoke': False,
    'qpfile-oversized-smoke': False,
    'zonefile-smoke': False,
    'zonefile-oversized-smoke': False,
    'recon-smoke': False,
    'analysis-save-load-smoke': False,
    '2pass-stats-smoke': False,
    'abr-ladder-smoke': False,
    'video-signal-type-preset-oversized-smoke': False,
    'gop-output-smoke': False,
    'mp4-smokes': False,
    'zimg-smoke': False,
    'linux-gcc-smoke': False,
    'linux-cmake-setup': False,
    'linux-sanitizer-toolchain-setup': False,
    'warning-scan-runtime-smokes': False,
    'gnu20-diagnostic-steps': False,
    'dependency-suffixes': False,
    'release-needs': False,
    'compile-commands': False,
    'gnu20-legacy-guard-bundle': False,
    'profdata-metadata': False,
    'cli-nullptr-usage': False,
    'cli-volatile-usage': False,
    'json11-noexcept-usage': False,
    'json11-number-boundary-safety': False,
    'json11-unicode-escape-parse-safety': False,
    'json11-short-int-parse-safety': False,
    'json11-slow-float-token-bounds': False,
    'source-null-exception-usage': False,
    'remaining-null-boundaries': False,
    'fps-parse-safety': False,
    'frame-threads-parse-safety': False,
    'total-frames-parse-safety': False,
    'level-idc-parse-safety': False,
    'log-level-parse-safety': False,
    'qpstep-parse-safety': False,
    'qscale-mode-parse-safety': False,
    'subme-parse-safety': False,
    'cli-input-open-cleanup': False,
    'cli-input-validation-cleanup': False,
    'cli-output-open-cleanup': False,
    'cli-profile-apply-cleanup': False,
    'cli-deprecated-parallel-log-args': False,
    'scenecut-trailing-arg-diagnostics': False,
    'cli-recon-basename-cleanup': False,
    'cli-vmaf-input-open-cleanup': False,
    'cli-vmaf-recon-preconditions-cleanup': False,
    'cli-recon-open-guard': False,
    'svt-app-context-staging': False,
    'svt-param-storage-replace-safety': False,
    'svt-nal-buffer-replace-safety': False,
    'nal-takecontents-realloc-safety': False,
    'svt-rpu-payload-replace-safety': False,
    'configure-zone-svt-staging': False,
    'svt-pools-parse-safety': False,
    'svt-deblock-parse-usage': False,
    'svt-frame-threads-parse-safety': False,
    'pgo-consume-chain': False,
    'source-test-vectors': False,
    'source-legacy-patterns': False,
    'all-source-legacy-patterns': False,
    'csvlog-reopen-state': False,
    'csvlog-open-state': False,
    'reconplay-start-failure-guard': False,
    'threadpool-create-rollback': False,
    'threadpool-start-rollback': False,
    'frameencoder-start-failure-guard': False,
    'threadedme-start-failure-guard': False,
    'input-reader-start-failure-guard': False,
    'input-framecount-seek-guard': False,
    'encoder-threadpool-start-failure-guard': False,
    'encoder-open-fail-cleanup': False,
    'lookahead-alloc-guards': False,
    'frameencoder-init-alloc-guards': False,
    'bitcost-alloc-guards': False,
    'scaler-chroma-dims-guard': False,
    'tonemap-payload-safety': False,
    'temporalfilter-alloc-counts': False,
    'frameencoder-substream-alloc-guards': False,
    'frameencoder-initialize-geoms-staging': False,
    'frame-create-subsample-staging': False,
    'frame-create-rowstate-alloc-guards': False,
    'frame-create-mcstf-refpic-guards': False,
    'frame-create-mcstf-fenc-pic-guards': False,
    'frame-create-top-alloc-guards': False,
    'frame-alloc-encode-data-guards': False,
    'x265-picture-init-null-guard': False,
    'x265-param-default-null-guard': False,
    'x265-param-default-preset-null-guard': False,
    'x265-param-parse-null-guard': False,
    'x265-param-apply-profile-null-guard': False,
    'param-api-null-guards': False,
    'zone-scenecut-param-parse-null-guards': False,
    'analysis-data-api-null-guards': False,
    'query-api-output-null-guards': False,
    'x265-dither-image-null-guards': False,
    'csvlog-api-null-guards': False,
    'csvlog-fail-state': False,
    'vmaf-api-null-guards': False,
    'threadedme-create-guards': False,
    'threadpool-windows-numa-affinity-guard': False,
    'encoder-ctu-info-guards': False,
    'encoder-open-alloc-guard': False,
    'encoder-create-object-alloc-guards': False,
    'encoder-create-core-alloc-guards': False,
    'encoder-encode-frame-alloc-guards': False,
    'encoder-encode-setup-rollback': False,
    'lowres-aqlayer-alloc-guards': False,
    'lowres-histogram-alloc-guards': False,
    'frame-edge-aq-alloc-guards': False,
    'cutree-sharedmem-alloc-guards': False,
    'scaler-helper-alloc-guards': False,
    'lookahead-create-rollback': False,
    'lookahead-tld-yuv-guards': False,
    'sea-integral-buffer-lifecycle': False,
    'vmaf-temp-buffer-cleanup': False,
    'encoder-rps-list-alloc-guard': False,
    'encoder-headers-arg-guard': False,
    'wavefront-init-rollback': False,
    'framedata-create-rollback': False,
    'scaler-init-rollback': False,
    'reconfig-save-zone-rollback': False,
    'cli-config-file-parse-usage': False,
    'lambda-file-parse-usage': False,
    'lambda-file-error-state': False,
    'param-checked-parse-usage': False,
    'scenecut-qp-macro-cleanup': False,
    'zone-param-macro-cleanup': False,
    'param-parse-macro-cleanup': False,
    'qpfile-parse-usage': False,
    'qpfile-error-state': False,
    'strict-scan-parsing-usage': False,
    'zonefile-parse-usage': False,
    'external-input-atoi-usage': False,
    'dolby-vision-rpu-parse-usage': False,
    'cmake-cxx20-contract': False,
    'nalu-file-parse-usage': False,
    'nalu-file-error-state': False,
    'analysis-reuse-refine-parse-safety': False,
    'analysis-output-fail-state': False,
    'scalinglist-parse-usage': False,
    'checked-parse-helper-safety': False,
    'param-uint-token-safety': False,
    'mkv-header-cleanup-state': False,
    'vmaf-file-cleanup-state': False,
    'vmaf-frame-read-state': False,
    'vmaf-picture-read-failure': False,
    'vmaf-score-failure-propagation': False,
    'vmaf-data-cleanup-state': False,
    'param-double-token-safety': False,
    'param-pair-parse-safety': False,
    'parse-name-assignment-safety': False,
    'ratecontrol-first-pass-parse-usage': False,
    'preset-index-parse-usage': False,
    'cpu-list-parse-usage': False,
    'interlace-parse-safety': False,
    'rdoq-level-parse-safety': False,
    'ratecontrol-numeric-helper-safety': False,
    'ratecontrol-stats-parse-usage': False,
    'ratecontrol-stats-line-parse-usage': False,
    'ratecontrol-stats-prefix-parse-usage': False,
    'param-bool-numeric-int-safety': False,
    'bitrate-mode-parse-safety': False,
    'qp-mode-parse-safety': False,
    'strict-cbr-parse-safety': False,
    'sao-create-rollback': False,
    'svt-bitrate-mode-parse-safety': False,
    'api-zone-open-staging': False,
    'copy-params-zone-replace-safety': False,
    'encoder-parameters-output-safety': False,
    'encoder-get-stats-size-guard': False,
    'cli-output-failure-full-cleanup': False,
    'lavf-openfile-cleanup': False,
    'svt-qp-mode-parse-safety': False,
    'reader-thread-alloc-guards': False,
    'scaler-thread-alloc-guards': False,
    'hdr10-json-metadata-ownership': False,
    'temporalfilter-refpic-rollback': False,
    'temporalfilter-refpic-state-init': False,
    'temporalfilter-metld-yuv-guards': False,
    'param-string-replace-safety': False,
    'zones-parse-safety': False,
    'raw-output-fail-state': False,
    'cli-progress-file-state': False,
    'raw-output-write-guard': False,
    'raw-stdout-flush-state': False,
    'mkv-output-fail-state': False,
    'mkv-close-fail-state': False,
    'recon-output-write-guard': False,
    'recon-output-stream-state': False,
    'y4m-recon-seek-guard': False,
    'recon-finalize-state': False,
    'gop-options-fail-state': False,
    'gop-output-fail-state': False,
    'gop-smart-fwrite-retry-guard': False,
    'y4m-yuv-row-buffer-alloc-guard': False,
    'output-open-alloc-guards': False,
    'vmaf-recon-state-safety': False,
    'reconplay-pipe-fail-state': False,
    'lambda-file-failfast': False,
    'lavf-buffer-replace-safety': False,
    'svt-pools-parse-usage': False,
    'threadpool-cpu-frequency-parse-usage': False,
    'threadpool-cpu-frequency-tail-guard': False,
    'lavf-framecount-parse-safety': False,
    'gop-close-fail-state': False,
    'param-bool-numeric-double-safety': False,
    'csv-log-level-parse-safety': False,
    'bool-int-parse-safety': False,
    'aq-mode-parse-safety': False,
    'multiview-scc-parse-safety': False,
    'view-layer-limit-safety': False,
    'bframes-parse-safety': False,
    'bframe-bias-parse-safety': False,
    'keyint-parse-safety': False,
    'min-keyint-parse-safety': False,
    'ip-pb-ratio-parse-safety': False,
    'vbv-end-fr-adj-safety': False,
    'zone-alloc-size-safety': False,
    'ref-parse-safety': False,
    'radl-parse-safety': False,
    'cbqpoffs-parse-safety': False,
    'crqpoffs-parse-safety': False,
    'pass-parse-safety': False,
    'qg-size-parse-safety': False,
    'qpmin-parse-safety': False,
    'qpmax-parse-safety': False,
    'chromaloc-parse-safety': False,
    'vbv-maxrate-parse-safety': False,
    'vbv-bufsize-parse-safety': False,
    'log2-max-poc-lsb-parse-safety': False,
    'nr-intra-parse-safety': False,
    'nr-inter-parse-safety': False,
    'rc-lookahead-parse-safety': False,
    'slices-parse-safety': False,
    'limit-tu-parse-safety': False,
    'lookahead-threads-parse-safety': False,
    'vbv-fullness-parse-safety': False,
    'rdpenalty-parse-safety': False,
    'gop-lookahead-parse-safety': False,
    'gop-lookahead-usage-safety': False,
    'zonefile-startframe-safety': False,
    'reconfig-window-size-safety': False,
    'no-reset-zone-prefill-guard': False,
    'common-logfile-open-state': False,
    'common-logfile-close-state': False,
    'common-slurp-open-state': False,
    'common-slurp-close-state': False,
    'common-slurp-size-guard': False,
    'cutree-sharedmem-name-guard': False,
    'mkv-writer-open-state': False,
    'mkv-writer-close-state': False,
    'riscv-cpuinfo-open-state': False,
    'riscv-cpuinfo-close-state': False,
    'cli-destroy-close-state': False,
    'encoder-destroy-close-state': False,
    'lambda-file-close-state': False,
    'film-grain-close-state': False,
    'gop-cleanup-close-state': False,
    'mp4-preflight-close-state': False,
    'gop-early-close-state': False,
    'gop-intermediate-close-state': False,
    'ratecontrol-destroy-close-state': False,
    'ratecontrol-write-fail-state': False,
    'ratecontrol-cutree-read-fail-state': False,
    'mp4-handle-close-state': False,
    'mp4-header-sei-alloc-guard': False,
    'raw-close-state': False,
    'raw-open-cleanup-state': False,
    'x265-check-macro-open-state': False,
    'x265-check-macro-close-state': False,
    'scalinglist-close-state': False,
    'vmaf-encoder-log-close-state': False,
    'y4m-input-close-state': False,
    'yuv-input-close-state': False,
    'reconplay-pclose-state': False,
    'multiview-parse-close-state': False,
    'multiview-config-parse-usage': False,
    'scenecut-aware-qp-config-parse-usage': False,
    'scenecut-aware-qp-parse-safety': False,
    'abr-parse-cleanup-state': False,
    'scenecut-qp-cleanup-state': False,
    'x265-main-cleanup-state': False,
    'abr-config-parse-usage': False,
    'abr-init-result-propagation': False,
    'abr-init-helper-cleanup': False,
    'abr-init-reader-rollback': False,
    'abr-init-api-null': False,
    'abr-init-output-null': False,
    'abr-init-filter-null': False,
    'abr-init-reader-alloc': False,
    'abr-start-threads-failure-propagation': False,
    'abr-primary-param-guards': False,
    'abr-ctor-top-guards': False,
    'abr-queue-picture-guards': False,
    'abr-thread-queue-state-guards': False,
    'abr-counter-state-guards': False,
    'abr-picture-state-guards': False,
    'abr-setreuselevel-ref': False,
    'abr-thread-multiview-field-guard': False,
    'abr-thread-multiview-input-guard': False,
    'abr-thread-reconplay-alloc-guard': False,
    'abr-thread-pic-in-reset-guard': False,
    'abr-thread-dolby-rpu-eof-guard': False,
    'abr-thread-output-null-guard': False,
    'abr-thread-fail-output': False,
    'abr-thread-fail-encoder': False,
    'abr-thread-output-picture': False,
    'abr-thread-layered-recon': False,
    'abr-thread-api-null': False,
    'abr-thread-dither-input': False,
    'abr-thread-field-buffer': False,
    'abr-thread-field-buffer-state': False,
    'abr-thread-field-view-usage': False,
    'abr-thread-field-layout': False,
    'abr-thread-field-plane': False,
    'abr-thread-field-reuse': False,
    'abr-thread-pts-queue-alloc': False,
    'abr-thread-recon-state': False,
    'abr-thread-recon-write': False,
    'abr-copyinfo-inter-arrays': False,
    'abr-copyinfo-intra-arrays': False,
    'abr-copyinfo-src': False,
    'abr-copyinfo-analysis-buffer': False,
    'abr-analysis-slot-wait': False,
    'abr-copyinfo-vbv-lookahead': False,
    'abr-allocbuffers-top-guards': False,
    'abr-allocbuffers-partial-cleanup': False,
    'abr-allocbuffers-queue-guards': False,
    'abr-allocbuffers-analysisread': False,
    'abr-allocbuffers-analysiswrite': False,
    'abr-allocbuffers-picidx': False,
    'abr-allocbuffers-readflag': False,
    'abr-readpicture-srcpic': False,
    'abr-readpicture-analysis': False,
    'abr-thread-readpicture-failure-guard': False,
    'abr-readpicture-analysis-queue': False,
    'abr-scaler-videodesc-alloc': False,
    'abr-scaler-videodesc-ownership': False,
    'abr-scaler-init-failure-handling': False,
    'abr-thread-analysis-read': False,
    'analysis-intra-alloc-guards': False,
    'analysis-inter-alloc-guards': False,
    'analysis-inter-motion-alloc-guards': False,
    'analysis-inter-temp-luma-alloc-guard': False,
    'analysis-inter-depth-run-guard': False,
    'analysis-cache-cost-guards': False,
    'scaled-analysis-load-alloc-guards': False,
    'analysis-2pass-load-cleanup': False,
    'picyuv-offset-rollback': False,
    'motion-reference-init-guards': False,
    'motionestimate-init-guard': False,
    'motion-sea-scratch-guard': False,
    'scaler-slice-linebuf-init': False,
    'analysis-load-staging-cleanup': False,
    'atc-sei-parse-safety': False,
    'chunk-start-parse-safety': False,
    'chunk-end-parse-safety': False,
    'deblock-parse-safety': False,
    'hash-parse-safety': False,
    'hme-parse-safety': False,
    'lookahead-slices-parse-safety': False,
    'merange-parse-safety': False,
    'misc-control-parse-safety': False,
    'pic-struct-parse-safety': False,
    'psy-scale-parse-safety': False,
    'rskip-parse-safety': False,
    'rskip-edge-threshold-parse-safety': False,
    'sar-parse-safety': False,
    'selective-sao-parse-safety': False,
    'ssim-rd-parse-safety': False,
    'temporal-layers-parse-safety': False,
    'uint32-token-parse-safety': False,
    'cli-inputfn-alloc-guard': False,
    'cli-vmaf-format-cleanup': False,
    'input-filename-copy-usage': False,
    'print-status-progress-guard': False,
    'recon-basename-parse-usage': False,
    'zonefile-parse-no-exit': False,
    'svt-aud-parse-safety': False,
    'svt-base-layer-switch-mode-parse-safety': False,
    'svt-compressed-ten-bit-parse-safety': False,
    'svt-constrained-intra-parse-safety': False,
    'svt-fps-in-vps-parse-safety': False,
    'svt-frames-to-be-encoded-parse-safety': False,
    'svt-hdr-parse-safety': False,
    'svt-hierarchical-level-parse-safety': False,
    'svt-high-tier-parse-safety': False,
    'svt-hrd-parse-safety': False,
    'svt-input-depth-parse-safety': False,
    'svt-keyint-parse-safety': False,
    'svt-master-display-parse-safety': False,
    'svt-nalu-file-parse-safety': False,
    'svt-pred-struct-parse-safety': False,
    'svt-qpmax-parse-safety': False,
    'svt-qpmin-parse-safety': False,
    'svt-rc-lookahead-parse-safety': False,
    'svt-sao-parse-safety': False,
    'svt-scenecut-parse-safety': False,
    'svt-search-height-parse-safety': False,
    'svt-search-width-parse-safety': False,
    'svt-speed-control-parse-safety': False,
    'svt-vbv-bufsize-parse-safety': False,
    'svt-vbv-init-parse-safety': False,
    'svt-vbv-maxrate-parse-safety': False,
    'svt-vui-timing-info-parse-safety': False,
    'svt-hme-parse-safety': False,
    'svt-interlace-parse-safety': False,
    'svt-open-gop-parse-safety': False,
    'svt-pools-exclude-both-sockets-guard': False,
    'encoder-rpu-replace-safety': False,
    'copy-user-sei-staging': False,
    'dup-side-data-staging': False,
    'read-user-sei-staging': False,
    'copy-picture-staging': False,
    'dup-create-alloc-guards': False,
    'encode-quant-offsets-staging': False,
    'read-user-sei-cleanup': False,
    'log-progress-file-parse-safety': False,
    'negated-bool-alias-parse-safety': False,
    'rd-parse-safety': False,
    'limit-refs-parse-safety': False,
    'dup-threshold-parse-safety': False,
    'vmaf-flush-cleanup': False,
    'avs-buffer-replace-safety': False,
    'vpy-buffer-replace-safety': False,
    'zimg-token-parse-usage': False,
    'zimg-init-rollback': False,
    'dynamic-hdr10-legacy-patterns': False,
    'sei-unsigned-token-safety': False,
    'video-signal-type-preset-parse': False,
    'sei-mastering-display-parse': False,
    'sao-param-staging': False,
    'zone-parse-replace-safety': False,
    'cpu-name-strdup-safety': False,
    'x265-fclose-macro-state': False,
    'hme-param-sscanf-usage': False,
    'masking-strength-scan-usage': False,
    'reviewed-string-copy-usage': False,
    'analysis-open-state': False,
    'analysis-load-open-state': False,
    'cli-config-open-state': False,
    'cli-help-exit-cleanup': False,
    'abr-ladder-open-state': False,
    'abr-help-exit-precedence': False,
    'lambda-file-open-state': False,
    'vmaf-input-open-state': False,
    'nalu-file-open-state': False,
    'tonemap-file-open-state': False,
    'scalinglist-open-state': False,
    'gop-open-state': False,
    'film-grain-open-state': False,
    'ratecontrol-stats-open-state': False,
}
VALIDATOR_NAMES = tuple(VALIDATOR_BASH_REQUIREMENTS)
BASH_VALIDATOR_NAMES = {name for name, needs_bash in VALIDATOR_BASH_REQUIREMENTS.items() if needs_bash}


def main():
    parser = argparse.ArgumentParser(description='Check CI workflow guardrails that are easy to miss by hand')
    parser.add_argument('--repo-root', type=Path, default=Path.cwd())
    parser.add_argument('--before')
    parser.add_argument('--after')
    parser.add_argument('--bash', help='bash executable used for syntax checks')
    parser.add_argument(
        '--only',
        action='append',
        default=[],
        metavar='CHECK',
        help='run only the named validation; may be specified multiple times',
    )
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    unknown = [name for name in args.only if name not in VALIDATOR_NAMES]
    if unknown:
        parser.error(f'unknown check(s): {", ".join(unknown)}')

    try:
        requested = set(args.only)
        needs_bash = not requested or bool(BASH_VALIDATOR_NAMES & requested)
        bash = bash_path(args.bash) if needs_bash else None
        validators = build_validators(repo_root, args, bash)
        if set(validators) != set(VALIDATOR_NAMES):
            fail('validator registry drift detected')
        for name in VALIDATOR_NAMES:
            if requested and name not in requested:
                continue
            validators[name]()
    except GuardFailure as exc:
        report_failure(exc)
    print('CI guardrails validated')


if __name__ == '__main__':
    main()
