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
    BUILD_PROFILING_WORKFLOW,
    BUILD_WORKFLOW,
    DEPENDENCY_SUFFIX_CHECK,
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
    REQUIRED_BUILD_PROFILING_ACTION_SNIPPETS,
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
    pgo_step_requirements,
    profiling_step_requirements,
)
from check_ci_guards_helpers import (
    GuardFailure,
    bash_path,
    clear_runtime_caches,
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
    require_active_line_contains,
    require_x265_command,
    runtime_smoke_active_lines,
    smoke_suite_function_lines,
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
        ),
        required_message='missing profiling compile_commands guard',
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


def validate_verify_ci_archive_helper(repo_root, bash):
    validate_bash_file(
        repo_root,
        bash,
        VERIFY_CI_ARCHIVE_HELPER,
        'missing archive verification helper',
        required_text=(
            'isolated_windows_path()',
            'run_with_isolated_path()',
            'verify_x265_release()',
            'verify_x265_profiling()',
            'verify_llvm_profdata()',
            'run_with_isolated_path "$extract_dir/llvm-profdata.exe" --version >/dev/null',
            'case "$mode" in',
        ),
        required_message='archive verification helper missing function',
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
            'smoke_zonefile()',
            'smoke_zonefile_oversized()',
            'smoke_recon()',
            'smoke_video_signal_type_preset_oversized()',
            'smoke_gop_output()',
            'run_runtime_smoke_target()',
            'run_runtime_smoke_targets()',
            'run_runtime_smoke_targets raw cli-long-input mkv lavf threaded-me threaded-me-stress qpfile zonefile zonefile-oversized recon video-signal-type-preset-oversized gop-output',
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


def validate_dependency_update_anchors(repo_root):
    action = repo_root / WINDOWS_DEPS_ACTION
    text = read_text(action)
    for anchor in UPDATE_DEPS_ANCHORS:
        if f'{anchor}:' not in text:
            fail(f'missing dependency update anchor: {anchor}:', action)
    print('Dependency update anchors validated')


def validate_pgo_consume_helper(repo_root):
    build = repo_root / BUILD_WORKFLOW
    blocks = [block for path, line, block in collect_run_blocks(build) if 'check_pgo_consume_commands()' in block]
    if len(blocks) != 1:
        fail(f'expected exactly one PGO consume helper run block, found {len(blocks)}', build)
    active_lines = shell_active_lines(blocks[0])
    required = 'check_cxx20_commands_pgo_consume "$build_dir" --min-cpp-commands="$min_cpp_commands"'
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

    for required, message in {
        "cat > smoke_qpfile.txt <<'EOF'": 'QPFile smoke must create smoke_qpfile.txt via heredoc',
        '0 I 22': 'QPFile smoke must require frame 0 I 22 entry',
        '3 P 24': 'QPFile smoke must require frame 3 P 24 entry',
        '6 B 26': 'QPFile smoke must require frame 6 B 26 entry',
        '9 K 20': 'QPFile smoke must require frame 9 K 20 entry',
        'EOF': 'QPFile smoke must close heredoc',
        'make_runtime_y4m smoke_qpfile.y4m 160 90 24 12 yuv420p': 'QPFile smoke must generate 12-frame yuv420p input',
        'test -s smoke_qpfile.hevc': 'QPFile smoke must require non-empty HEVC output',
        'ffprobe -v error -count_frames -select_streams v:0 -show_entries stream=nb_read_frames -of default=noprint_wrappers=1 smoke_qpfile.hevc > smoke_qpfile_count.txt': 'QPFile smoke must count decoded frames',
        'grep -q "nb_read_frames=12" smoke_qpfile_count.txt': 'QPFile smoke must require 12 decoded frames',
    }.items():
        if required not in active_lines:
            fail(message, build)

    require_x265_command(active_lines, build, 'QPFile smoke', 'smoke_qpfile', 'build/all/x265.exe', (
        ('--input', 'smoke_qpfile.y4m'),
        ('--input-res', '160x90'),
        ('--fps', '24'),
        ('--frames', '12'),
        ('--qpfile', 'smoke_qpfile.txt'),
        ('--output', 'smoke_qpfile.hevc'),
    ))
    print('QPFile smoke guard validated')


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


def validate_video_signal_type_preset_oversized_smoke(repo_root):
    build = repo_root / BUILD_WORKFLOW
    active_lines = smoke_suite_function_lines(repo_root, RUNTIME_SMOKE_SUITE, 'smoke_video_signal_type_preset_oversized', 'missing runtime smoke suite')

    for required, message in {
        'make_runtime_y4m smoke_recon.y4m 160 90 24 1 yuv420p': 'Video-signal-type-preset oversized smoke must generate 1-frame yuv420p input',
        'long_vst="$(python -c "print(\'A\' * 200 + \':P3D65x1000n0005\')")"': 'Video-signal-type-preset oversized smoke must synthesize oversized preset',
        'if build/all/x265.exe --input smoke_recon.y4m --input-res 160x90 --fps 24 --frames 1 --video-signal-type-preset "$long_vst" --output smoke_vst_oversized.hevc > smoke_vst_oversized.log 2>&1; then': 'Video-signal-type-preset oversized smoke must actively require failure',
        'echo "Video-signal-type-preset oversized smoke unexpectedly succeeded"': 'Video-signal-type-preset oversized smoke must report unexpected success',
        "grep -Fq 'Incorrect system-id, aborting' smoke_vst_oversized.log": 'Video-signal-type-preset oversized smoke must require invalid system-id log',
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
        "grep -Fq 'zimg [info]: Resize: 64x64' build/cxx20-warning-scan/smoke_zimg.log",
        'build/cxx20-warning-scan/smoke_zimg.log',
        'ZIMG smoke',
    )
    validate_zimg_command(
        bypass_command,
        (
            ('--input', 'build/cxx20-warning-scan/smoke_zimg.yuv'),
            ('--input-res', '96x96'),
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
        'if build/cxx20-warning-scan/x265.exe --input build/cxx20-warning-scan/smoke_zimg.yuv --input-res 96x96 --fps 1 --frames 1 --vf "$long_zimg_vf" --output build/cxx20-warning-scan/smoke_zimg_longparam.hevc > build/cxx20-warning-scan/smoke_zimg_longparam.log 2>&1; then': 'ZIMG smoke must actively require long-parameter failure',
        'echo "ZIMG long-parameter smoke unexpectedly succeeded"': 'ZIMG smoke must report unexpected long-parameter success',
        'grep -Fq \'Filter parameters exceeds supported length\' build/cxx20-warning-scan/smoke_zimg_longparam.log': 'ZIMG smoke must require long-parameter error log',
        'long_filter_name_vf="$(python -c "print(\'a\' * 1100 + \':x\')")"': 'ZIMG smoke must synthesize long filter-name vf input',
        'if build/cxx20-warning-scan/x265.exe --input build/cxx20-warning-scan/smoke_zimg.yuv --input-res 96x96 --fps 1 --frames 1 --vf "$long_filter_name_vf" --output build/cxx20-warning-scan/smoke_filter_longname.hevc > build/cxx20-warning-scan/smoke_filter_longname.log 2>&1; then': 'ZIMG smoke must actively require long filter-name failure',
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


def validate_gnu20_diagnostic_steps(repo_root):
    build = repo_root / BUILD_WORKFLOW
    parsed = load_yaml(repo_root, BUILD_WORKFLOW)
    requirements = (
        (
            'cxx20-warning-scan',
            'Check GNU++20 downgrade guardrail',
            (
                ('configure_cxx20_scan x265/source build/cxx20-downgrade-guard', 'GNU++20 downgrade guard must actively configure downgrade build'),
                ('-DCMAKE_CXX_STANDARD=17', 'GNU++20 downgrade guard must request C++17 override'),
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
                ('for target_cpu in haswell arrowlake znver5; do', 'CPU warning scan must actively cover haswell/arrowlake/znver5 loop'),
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
                ('ninja -C build/cxx20-gcc-compile-commands-12bit x265-static', 'Windows GCC diagnostics must actively build 12-bit static target'),
                ('check_cxx20_commands_gcc build/cxx20-gcc-compile-commands-8bit-lib', 'Windows GCC diagnostics must actively check 8-bit lib compile commands'),
                ('--required-file-flag=source/common/winxp.cpp=-D_WIN32_WINNT=_WIN32_WINNT_WIN7', 'Windows GCC diagnostics must actively require Win7 winxp.cpp macro'),
                ('--forbidden-file-flag=source/common/winxp.cpp=-D_WIN32_WINNT=_WIN32_WINNT_WINXP', 'Windows GCC diagnostics must actively reject WinXP winxp.cpp macro'),
                ('ninja -C build/cxx20-gcc-compile-commands-8bit-lib x265-static', 'Windows GCC diagnostics must actively build 8-bit lib static target'),
                ('check_cxx20_commands_gcc build/cxx20-gcc-compile-commands-all', 'Windows GCC diagnostics must actively check all-bit-depth compile commands'),
                ('--required-file-flag=source/common/version.cpp=-DLINKED_8BIT=1', 'Windows GCC diagnostics must actively require linked 8-bit version macro'),
                ('--required-file-flag=source/common/version.cpp=-DLINKED_12BIT=1', 'Windows GCC diagnostics must actively require linked 12-bit version macro'),
                ('ninja -C build/cxx20-gcc-compile-commands-all cli', 'Windows GCC diagnostics must actively build all-bit-depth CLI'),
            ),
        ),
        (
            'cxx20-linux-gcc-compile-commands',
            'Run Linux GCC C++20 compile command diagnostics',
            (
                ('check_cxx20_commands_gcc build/cxx20-linux-gcc-compile-commands ', 'Linux GCC diagnostics must actively check compile commands'),
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
                ('--vf "zimg:lanczos(64,64)"', 'C++20 warning scan must actively run ZIMG filter smoke'),
                ("grep -Fq 'zimg [info]: Resize: 64x64' build/cxx20-warning-scan/smoke_zimg.log", 'C++20 warning scan must actively require ZIMG resize smoke log'),
                ("grep -Fq 'encoded 1 frames' build/cxx20-warning-scan/smoke_zimg.log", 'C++20 warning scan must actively require ZIMG encoded-frame smoke log'),
                ('configure_cxx20_scan x265/source build/cxx20-warning-scan-12bit', 'C++20 warning scan must actively configure 12-bit CLI'),
                ('check_cxx20_commands_clang build/cxx20-warning-scan-12bit', 'C++20 warning scan must actively check 12-bit CLI'),
                ('--required-depth-define=-DX265_DEPTH=12', 'C++20 warning scan must actively require 12-bit depth'),
                ('configure_cxx20_scan x265/source build/cxx20-warning-scan-unity', 'C++20 warning scan must actively configure unity build'),
                ('-DENABLE_UNITY_BUILD=ON', 'C++20 warning scan must actively enable unity build'),
                ('configure_cxx20_scan x265/source build/cxx20-warning-scan-shared-deps', 'C++20 warning scan must actively configure shared deps build'),
                ('--required-file-flag=source/input/lavf.cpp=-DENABLE_LAVF', 'C++20 warning scan must actively require LAVF macro'),
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
                (('check_cxx20_commands_gcc', 'build/cxx20-gcc-compile-commands-all'), 'Windows GCC diagnostics must actively check all-bit-depth compile commands'),
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


def validate_required_snippets(repo_root):
    validate_required_workflow_steps(repo_root, BUILD_WORKFLOW, 'Build workflow guard', build_step_requirements())
    build_profiling = validate_required_workflow_steps(repo_root, BUILD_PROFILING_WORKFLOW, 'Build Profiling workflow guard', profiling_step_requirements())
    build_pgo = validate_required_workflow_steps(repo_root, BUILD_PGO_WORKFLOW, 'Build PGO workflow guard', pgo_step_requirements())
    validate_required_workflow_steps(repo_root, UPDATE_DEPS_WORKFLOW, 'update-deps guard', (
        ('update-deps', 'Check CI guardrails', REQUIRED_UPDATE_DEPS_SNIPPETS[:3]),
        ('update-deps', 'Update Dependency Refs', REQUIRED_UPDATE_DEPS_SNIPPETS[3:8]),
        ('update-deps', 'Validate Dependency Ref Diff', REQUIRED_UPDATE_DEPS_SNIPPETS[8:]),
    ))

    build_profiling_path = repo_root / BUILD_PROFILING_WORKFLOW
    jobs = workflow_jobs(build_profiling, build_profiling_path)
    if jobs.get('build', {}).get('needs') != 'validate-guardrails':
        fail('Build Profiling build job must need validate-guardrails', build_profiling_path)
    if jobs.get('publish-release', {}).get('needs') != ['build', 'validate-guardrails']:
        fail('Build Profiling publish-release job must need build and validate-guardrails', build_profiling_path)

    build_pgo_path = repo_root / BUILD_PGO_WORKFLOW
    pgo_jobs = workflow_jobs(build_pgo, build_pgo_path)
    if pgo_jobs.get('generate', {}).get('needs') != 'validate-guardrails':
        fail('Build PGO generate job must need validate-guardrails', build_pgo_path)
    build_pgo_step = workflow_step(build_pgo, build_pgo_path, 'generate', 'Build Profiling Binaries')
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

    validate_required_action_steps(repo_root, BUILD_PROFILING_ACTION, 'Build Profiling action guard', (
        ('Build 8b-lib profiling CLI', REQUIRED_BUILD_PROFILING_ACTION_SNIPPETS[:3] + REQUIRED_BUILD_PROFILING_ACTION_SNIPPETS[5:]),
        ('Build 12b-lib profiling CLI', REQUIRED_BUILD_PROFILING_ACTION_SNIPPETS[:2] + REQUIRED_BUILD_PROFILING_ACTION_SNIPPETS[3:4]),
        ('Build all profiling CLI', REQUIRED_BUILD_PROFILING_ACTION_SNIPPETS[:2] + REQUIRED_BUILD_PROFILING_ACTION_SNIPPETS[4:5]),
    ))
    validate_required_action_steps(repo_root, WINDOWS_DEPS_ACTION, 'setup-windows-deps guard', (
        ('Verify MSYS2 Toolchain', REQUIRED_WINDOWS_DEPS_ACTION_SNIPPETS[:5]),
        ('Compile L-SMASH', REQUIRED_WINDOWS_DEPS_ACTION_SNIPPETS[5:9]),
        ('Compile GOP muxer', REQUIRED_WINDOWS_DEPS_ACTION_SNIPPETS[9:]),
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
    for job_name in PR_SKIPPED_BUILD_JOBS:
        job = jobs.get(job_name)
        if not isinstance(job, dict):
            fail(f'missing workflow job: {job_name}', build_path)
        if job.get('if') != "github.event_name != 'pull_request'":
            fail(f'Build workflow job {job_name} must be skipped for pull_request fast gate', build_path)

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
    if 'linux-clang-sanitizers' in needs:
        fail('publish-release must not depend on PR fast-gate sanitizer job', build_path)
    for required in ('cxx20-warning-scan', 'cxx20-gcc-compile-commands', 'cxx20-linux-gcc-compile-commands', 'build'):
        if required not in needs:
            fail(f'publish-release must depend on full-gate job: {required}', build_path)
    print('Build PR fast-gate structure validated')


def validate_warning_scan_dependencies(repo_root):
    build_path = repo_root / BUILD_WORKFLOW
    parsed = load_yaml(repo_root, BUILD_WORKFLOW)
    step = workflow_step(parsed, build_path, 'cxx20-warning-scan', 'Setup Shared Dependencies')
    with_values = step.get('with')
    if not isinstance(with_values, dict):
        fail('C++20 warning scan dependency setup is missing with inputs', build_path)
    packages = with_values.get('extra-msys2-packages')
    if not isinstance(packages, str) or 'mingw-w64-clang-x86_64-zimg' not in packages.split():
        fail('C++20 warning scan dependency setup must install mingw-w64-clang-x86_64-zimg', build_path)
    print('C++20 warning scan dependency setup validated')


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


def build_validators(repo_root, args, bash):
    return {
        'yaml-text': lambda: validate_yaml_text(repo_root, WORKFLOW_DIR, ACTION_DIR),
        'yaml-parse': lambda: validate_yaml_parse(repo_root, WORKFLOW_DIR, ACTION_DIR),
        'run-blocks': lambda: validate_run_blocks(repo_root, WORKFLOW_DIR, ACTION_DIR, bash),
        'scan-helper': lambda: validate_scan_helper(repo_root, bash),
        'mp4-smoke-helper': lambda: validate_mp4_smoke_helper(repo_root, bash),
        'profiling-smoke-helper': lambda: validate_profiling_smoke_helper(repo_root, bash),
        'verify-ci-archive-helper': lambda: validate_verify_ci_archive_helper(repo_root, bash),
        'runtime-smoke-suite': lambda: validate_runtime_smoke_suite(repo_root, bash),
        'mp4-smoke-suite': lambda: validate_mp4_smoke_suite(repo_root, bash),
        'source-test-vector-scripts': lambda: validate_source_test_vector_scripts(repo_root),
        'dependency-update-anchors': lambda: validate_dependency_update_anchors(repo_root),
        'required-snippets': lambda: validate_required_snippets(repo_root),
        'build-pr-fast-gate': lambda: validate_build_pr_fast_gate(repo_root),
        'warning-scan-dependencies': lambda: validate_warning_scan_dependencies(repo_root),
        'job-timeouts': lambda: validate_job_timeouts(repo_root),
        'update-deps-concurrency': lambda: validate_update_deps_concurrency(repo_root),
        'pgo-consume-helper': lambda: validate_pgo_consume_helper(repo_root),
        'raw-smoke': lambda: validate_raw_smoke(repo_root),
        'threaded-me-smoke': lambda: validate_threaded_me_smoke(repo_root),
        'threaded-me-stress-smoke': lambda: validate_threaded_me_stress_smoke(repo_root),
        'cli-long-input-smoke': lambda: validate_cli_long_input_smoke(repo_root),
        'mkv-smoke': lambda: validate_mkv_smoke(repo_root),
        'lavf-smoke': lambda: validate_lavf_smoke(repo_root),
        'qpfile-smoke': lambda: validate_qpfile_smoke(repo_root),
        'zonefile-smoke': lambda: validate_zonefile_smoke(repo_root),
        'zonefile-oversized-smoke': lambda: validate_zonefile_oversized_smoke(repo_root),
        'recon-smoke': lambda: validate_recon_smoke(repo_root),
        'video-signal-type-preset-oversized-smoke': lambda: validate_video_signal_type_preset_oversized_smoke(repo_root),
        'gop-output-smoke': lambda: validate_gop_output_smoke(repo_root),
        'mp4-smokes': lambda: validate_mp4_smokes(repo_root),
        'zimg-smoke': lambda: validate_zimg_smoke(repo_root),
        'linux-gcc-smoke': lambda: validate_linux_gcc_smoke(repo_root),
        'warning-scan-runtime-smokes': lambda: validate_warning_scan_runtime_smokes(repo_root),
        'gnu20-diagnostic-steps': lambda: validate_gnu20_diagnostic_steps(repo_root),
        'dependency-suffixes': lambda: validate_dependency_suffixes(repo_root, args.before, args.after),
    }


VALIDATOR_BASH_REQUIREMENTS = {
    'yaml-text': False,
    'yaml-parse': False,
    'run-blocks': True,
    'scan-helper': True,
    'mp4-smoke-helper': True,
    'profiling-smoke-helper': True,
    'verify-ci-archive-helper': True,
    'runtime-smoke-suite': True,
    'mp4-smoke-suite': True,
    'source-test-vector-scripts': False,
    'dependency-update-anchors': False,
    'required-snippets': False,
    'build-pr-fast-gate': False,
    'warning-scan-dependencies': False,
    'job-timeouts': False,
    'update-deps-concurrency': False,
    'pgo-consume-helper': False,
    'raw-smoke': False,
    'threaded-me-smoke': False,
    'threaded-me-stress-smoke': False,
    'cli-long-input-smoke': False,
    'mkv-smoke': False,
    'lavf-smoke': False,
    'qpfile-smoke': False,
    'zonefile-smoke': False,
    'zonefile-oversized-smoke': False,
    'recon-smoke': False,
    'video-signal-type-preset-oversized-smoke': False,
    'gop-output-smoke': False,
    'mp4-smokes': False,
    'zimg-smoke': False,
    'linux-gcc-smoke': False,
    'warning-scan-runtime-smokes': False,
    'gnu20-diagnostic-steps': False,
    'dependency-suffixes': False,
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

    clear_runtime_caches()
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
