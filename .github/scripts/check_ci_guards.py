#!/usr/bin/env python3
import argparse
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

WORKFLOW_DIR = Path('.github/workflows')
ACTION_DIR = Path('.github/actions')
SCAN_HELPER = Path('.github/scripts/cxx20_scan_helpers.sh')
DEPENDENCY_SUFFIX_CHECK = Path('.github/scripts/check_dependency_patch_suffixes.py')
WINDOWS_DEPS_ACTION = Path('.github/actions/setup-windows-deps/action.yml')
UPDATE_DEPS_WORKFLOW = Path('.github/workflows/update-deps.yml')
BUILD_WORKFLOW = Path('.github/workflows/build.yml')
BUILD_PROFILING_WORKFLOW = Path('.github/workflows/build-profiling.yml')
BUILD_PROFILING_ACTION = Path('.github/actions/build-x265-profiling/action.yml')

UPDATE_DEPS_ANCHORS = (
    'ffmpeg-ref',
    'mimalloc-ref',
    'obuparse-ref',
    'lsmash-ref',
    'lsmash-cache-suffix',
    'gop-muxer-ref',
    'gop-muxer-cache-suffix',
)
REQUIRED_BUILD_SNIPPETS = (
    'python .github/scripts/check_ci_guards.py',
    'python .github/scripts/test_check_ci_guards.py',
    'python .github/scripts/check_cmake_cxx20_contract.py source',
    'python .github/scripts/test_check_cmake_cxx20_contract.py',
    'python .github/scripts/test_check_compile_commands.py',
    'python .github/scripts/check_dependency_patch_suffixes.py --before "$before" --after "$after"',
    'python .github/scripts/test_check_dependency_patch_suffixes.py',
    'python .github/scripts/check_release_needs.py',
    'python .github/scripts/test_check_pgo_consume_chain.py',
    'No numeric version tag found; using $version as CI fallback',
    'check_cxx20_commands_pgo_consume "$build_dir" --min-cpp-commands="$min_cpp_commands"',
    'check_pgo_consume_commands build/8b-lib "$PGO_8B_LIB_FLAG" 50',
    'check_pgo_consume_commands build/12b-lib "$PGO_12B_LIB_FLAG" 50',
    'check_pgo_consume_commands build/all-8b-lib "$PGO_ALL_FLAG" 50',
    'check_pgo_consume_commands build/all-12b-lib "$PGO_ALL_FLAG" 50',
    'check_pgo_consume_commands build/all "$PGO_ALL_FLAG" 60',
    '--required-file-flag=source/common/version.cpp=-DLINKED_8BIT=1',
    '--required-file-flag=source/common/version.cpp=-DLINKED_12BIT=1',
    '--required-file-flag=source/encoder/api.cpp=-DLINKED_8BIT=1',
    '--required-file-flag=source/encoder/api.cpp=-DLINKED_12BIT=1',
    '--forbidden-file-flag=source/encoder/api.cpp=-DEXPORT_C_API=1',
    '--input-res 160x90 --fps 24 --frames 16 --preset medium --threaded-me --pools 32 --frame-threads 1 --no-wpp --no-progress',
    'ffmpeg -hide_banner -loglevel error -f lavfi -i testsrc2=size=160x90:rate=24 -frames:v 16 -pix_fmt yuv420p smoke_threaded_me.y4m',
    'ffprobe -v error -count_frames -select_streams v:0 -show_entries stream=nb_read_frames -of default=noprint_wrappers=1 smoke_threaded_me.hevc > smoke_threaded_me_count.txt',
    'frame threads / pool features       : 1 / threaded-me',
    "! grep -Fq 'disabling --threaded-me'",
    'test -s smoke_threaded_me.hevc',
    "grep -q 'nb_read_frames=16' smoke_threaded_me_count.txt",
    'test -s smoke_gop.gop',
    'test -s smoke_gop.options',
    'test -s smoke_gop.headers',
    'test -s smoke_gop-000000.hevc-gop-data',
    'test -s smoke_gop-000008.hevc-gop-data',
    "grep -Fxq 'smoke_gop-000000.hevc-gop-data' smoke_gop_data_files.txt",
    "grep -Fxq 'smoke_gop-000008.hevc-gop-data' smoke_gop_data_files.txt",
    "grep -q 'format_name=mov,mp4,m4a,3gp,3g2,mj2' smoke_gop_mux_format.txt",
    'gop_muxer.exe smoke_gop.gop',
    'test -s smoke_gop.mp4',
    "grep -q 'nb_read_frames=16' smoke_gop_mux_count.txt",
    'encoded 1 frames',
    '--required-file-substring=source/output/reconplay.cpp',
    '--required-file-substring=source/common/winxp.cpp',
    '--required-file-flag=source/common/winxp.cpp=-D_WIN32_WINNT=_WIN32_WINNT_WIN7',
    '--forbidden-file-flag=source/common/winxp.cpp=-D_WIN32_WINNT=_WIN32_WINNT_WINXP',
    '--forbidden-file-substring=source/common/winxp.cpp',
    'check_cxx20_commands_gcc build/cxx20-linux-gcc-compile-commands',
    'ninja -C build/cxx20-linux-gcc-compile-commands cli',
    'build/cxx20-linux-gcc-compile-commands/x265 --input',
    'build/cxx20-linux-gcc-compile-commands/smoke_linux_gcc.log',
    'test -s build/cxx20-linux-gcc-compile-commands/smoke_linux_gcc.log',
    'test -s build/cxx20-linux-gcc-compile-commands/smoke_linux_gcc.hevc',
    'smoke_linux_gcc.hevc',
    'configure_cxx20_scan x265/source build/cxx20-warning-scan-all-12b-lib',
    '-DENABLE_ZIMG=ON',
    '--required-file-substring=source/filters/zimgfilter.cpp',
    '--required-file-flag=source/filters/zimgfilter.cpp=-DENABLE_ZIMG',
    '--vf "zimg:lanczos(64,64)"',
    "grep -Fq 'zimg [info]: Resize: 64x64' build/cxx20-warning-scan/smoke_zimg.log",
    "grep -Fq 'encoded 1 frames' build/cxx20-warning-scan/smoke_zimg.log",
    'check_cxx20_commands_gcc build/cxx20-gcc-compile-commands-12bit',
    'ninja -C build/cxx20-gcc-compile-commands-12bit x265-static',
    'check_cxx20_commands_gcc build/cxx20-gcc-compile-commands-all',
    'ninja -C build/cxx20-gcc-compile-commands-all cli',
)
REQUIRED_BUILD_PROFILING_SNIPPETS = (
    'validate-guardrails:',
    'needs: validate-guardrails',
    'needs: [build, validate-guardrails]',
    'python .github/scripts/check_ci_guards.py',
    'python .github/scripts/test_check_ci_guards.py',
    'No numeric version tag found; using $version as CI fallback',
    'version="${{ steps.tag.outputs.version }}-g${head_hash}"',
    'test -s "$LLVM_PROFILE_FILE"',
    'test -s profile-smoke-8b.profdata',
    'test -s profile-smoke-12b.profdata',
    'case "$llvm_profdata" in',
    '/clang64/bin/*) ;;',
    'test -s profile-smoke-all.profdata',
    'test -s smoke_profile_8b.mp4',
    'test -s smoke_profile_roundtrip_8b.y4m',
    'echo "8b-lib roundtrip FRAME tokens: ${frame_count:-missing}"',
    'test -s smoke_profile_12b.mp4',
    'test -s smoke_profile_roundtrip_12b.y4m',
    'echo "12b-lib roundtrip FRAME tokens: ${frame_count:-missing}"',
    'test -s smoke_profile_all.mp4',
    'test -s smoke_profile_roundtrip_all.y4m',
    'echo "all roundtrip FRAME tokens: ${frame_count:-missing}"',
    'test "$frame_count" = "12"',
    'mp4_roundtrip_frames',
    'enable-lsmash: \'ON\'',
    './profdata-dist/llvm-profdata.exe show profile-smoke-8b.profdata >/dev/null',
    './profdata-dist/llvm-profdata.exe show profile-smoke-12b.profdata >/dev/null',
    './profdata-dist/llvm-profdata.exe show profile-smoke-all.profdata >/dev/null',
    'echo "- standard: gnu++20"',
)
REQUIRED_BUILD_PROFILING_ACTION_SNIPPETS = (
    'CXX20_CHECK_SCRIPT="${{ github.action_path }}/../../scripts/check_compile_commands.py"',
    '-DCMAKE_EXPORT_COMPILE_COMMANDS=ON',
    'check_cxx20_commands_profiling build/8b',
    'check_cxx20_commands_profiling build/12b',
    'check_cxx20_commands_profiling .',
    'enable-lsmash',
    "if [ \"${{ inputs.enable-lsmash }}\" = 'true' ] || [ \"${{ inputs.enable-lsmash }}\" = 'ON' ]; then",
    'lsmash_args=(-DENABLE_LSMASH=ON)',
)
REQUIRED_UPDATE_DEPS_SNIPPETS = (
    'python .github/scripts/check_ci_guards.py',
    'python .github/scripts/test_check_ci_guards.py',
    'python .github/scripts/check_dependency_patch_suffixes.py',
    'for anchor in ffmpeg-ref mimalloc-ref obuparse-ref lsmash-ref lsmash-cache-suffix gop-muxer-ref gop-muxer-cache-suffix; do',
    'lsmash_suffix=$(sed -n',
    'gop_muxer_suffix=$(sed -n',
    'Current L-SMASH cache suffix: ${lsmash_suffix}',
    'Current GOP muxer cache suffix: ${gop_muxer_suffix}',
    'Unexpected dependency update diff paths:',
)
REQUIRED_WINDOWS_DEPS_ACTION_SNIPPETS = (
    'case "${MSYSTEM:-}" in',
    'CLANG64) ;;',
    '/clang64/bin/*|/usr/bin/*) ;;',
    'lsmash=${{ inputs.lsmash-repository }}@${{ inputs.lsmash-ref }} suffix=${{ inputs.lsmash-cache-suffix }} patch=${{ inputs.lsmash-patch-path }}',
    'gop_muxer=${{ inputs.gop-muxer-repository }}@${{ inputs.gop-muxer-ref }} suffix=${{ inputs.gop-muxer-cache-suffix }} patch=${{ inputs.gop-muxer-patch-path }}',
    'git apply --ignore-whitespace --check ${{ inputs.lsmash-patch-path }}',
    "grep -Fq \"LSMASH_4CC( 'h', 'v', 'c', 'C' )\" codecs/hevc.c",
    "grep -Fq 'lsmash_isom_box_type_value' core/box.c",
    'git -c core.autocrlf=false reset --hard HEAD',
    'git apply ${{ inputs.gop-muxer-patch-path }}',
    'c++ -O2 --std=gnu++20 -I/usr/local/include -c gop_muxer.cpp -o gop_muxer.o',
)
TME_SMOKE_FLAGS = (
    '--threaded-me',
    '--no-wpp',
    '--no-progress',
)
TME_SMOKE_OPTIONS = (
    ('--input', 'smoke_threaded_me.y4m'),
    ('--input-res', '160x90'),
    ('--fps', '24'),
    ('--frames', '16'),
    ('--preset', 'medium'),
    ('--pools', '32'),
    ('--frame-threads', '1'),
    ('--output', 'smoke_threaded_me.hevc'),
)
TME_GENERATOR_OPTIONS = (
    ('-i', 'testsrc2=size=160x90:rate=24'),
    ('-frames:v', '16'),
    ('-pix_fmt', 'yuv420p'),
)
MKV_SMOKE_OPTIONS = (
    ('--input', 'smoke_mkv.y4m'),
    ('--input-res', '160x90'),
    ('--fps', '24'),
    ('--frames', '12'),
    ('--output', 'smoke_mkv.mkv'),
)
MKV_GENERATOR_OPTIONS = (
    ('-i', 'testsrc2=size=160x90:rate=24'),
    ('-frames:v', '12'),
    ('-pix_fmt', 'yuv420p'),
)
LAVF_SMOKE_OPTIONS = (
    ('--input', 'smoke_lavf_input.mkv'),
    ('--frames', '12'),
    ('--output', 'smoke_lavf_output.hevc'),
)
LAVF_GENERATOR_OPTIONS = (
    ('-f', 'lavfi'),
    ('-i', 'testsrc2=size=160x90:rate=24'),
    ('-frames:v', '12'),
    ('-pix_fmt', 'yuv420p'),
    ('-c:v', 'ffv1'),
)
GOP_SMOKE_FLAGS = (
    '--no-open-gop',
)
GOP_SMOKE_OPTIONS = (
    ('--input', 'smoke_gop.y4m'),
    ('--input-res', '128x72'),
    ('--fps', '24'),
    ('--frames', '16'),
    ('--bframes', '0'),
    ('--keyint', '8'),
    ('--min-keyint', '8'),
    ('--output', 'smoke_gop.gop'),
)
GOP_GENERATOR_OPTIONS = (
    ('-f', 'lavfi'),
    ('-i', 'testsrc2=size=128x72:rate=24'),
    ('-frames:v', '16'),
    ('-pix_fmt', 'yuv420p'),
)
MP4_SMOKE_FLAGS = (
    '--no-open-gop',
)
MP4_SMOKE_OPTIONS = (
    ('--input', 'smoke.y4m'),
    ('--input-res', '128x72'),
    ('--fps', '24'),
    ('--frames', '16'),
    ('--bframes', '4'),
    ('--keyint', '8'),
    ('--min-keyint', '8'),
    ('--output', 'smoke.mp4'),
)
MP4_OPEN_GOP_SMOKE_FLAGS = (
    '--open-gop',
)
MP4_OPEN_GOP_SMOKE_OPTIONS = (
    ('--input', 'smoke_open.y4m'),
    ('--input-res', '128x72'),
    ('--fps', '24'),
    ('--frames', '16'),
    ('--bframes', '4'),
    ('--keyint', '8'),
    ('--min-keyint', '8'),
    ('--output', 'smoke_open.mp4'),
)
MP4_CRA_SMOKE_FLAGS = (
    '--cra-nal',
)
MP4_CRA_SMOKE_OPTIONS = (
    ('--input', 'smoke_cra.y4m'),
    ('--input-res', '128x72'),
    ('--fps', '24'),
    ('--frames', '16'),
    ('--bframes', '0'),
    ('--keyint', '1'),
    ('--min-keyint', '1'),
    ('--output', 'smoke_cra.mp4'),
)
MP4_SINGLE_FRAME_SMOKE_OPTIONS = (
    ('--input', 'smoke_single.y4m'),
    ('--input-res', '128x72'),
    ('--fps', '24'),
    ('--frames', '1'),
    ('--bframes', '0'),
    ('--keyint', '1'),
    ('--min-keyint', '1'),
    ('--output', 'smoke_single.mp4'),
)
MP4_ZERO_FRAMES_SMOKE_OPTIONS = (
    ('--input', 'smoke_zero.y4m'),
    ('--input-res', '128x72'),
    ('--fps', '24'),
    ('--frames', '0'),
    ('--bframes', '0'),
    ('--keyint', '1'),
    ('--min-keyint', '1'),
    ('--output', 'smoke_zero.mp4'),
)
MP4_VUI_SMOKE_OPTIONS = (
    ('--input', 'smoke_vui.y4m'),
    ('--input-res', '128x72'),
    ('--fps', '24'),
    ('--frames', '4'),
    ('--bframes', '0'),
    ('--keyint', '4'),
    ('--min-keyint', '4'),
    ('--sar', '4:3'),
    ('--range', 'limited'),
    ('--colorprim', 'bt709'),
    ('--transfer', 'bt709'),
    ('--colormatrix', 'bt709'),
    ('--output', 'smoke_vui.mp4'),
)
MP4_FRAC_SMOKE_FLAGS = (
    '--no-open-gop',
)
MP4_FRAC_SMOKE_OPTIONS = (
    ('--input', 'smoke_frac.y4m'),
    ('--input-res', '128x72'),
    ('--fps', '24000/1001'),
    ('--frames', '24'),
    ('--bframes', '4'),
    ('--keyint', '12'),
    ('--min-keyint', '12'),
    ('--output', 'smoke_frac.mp4'),
)
MP4_BPYRAMID_SMOKE_FLAGS = (
    '--b-pyramid',
    '--no-open-gop',
)
MP4_BPYRAMID_SMOKE_OPTIONS = (
    ('--input', 'smoke_bpyramid.y4m'),
    ('--input-res', '128x72'),
    ('--fps', '24'),
    ('--frames', '16'),
    ('--bframes', '4'),
    ('--keyint', '8'),
    ('--min-keyint', '8'),
    ('--output', 'smoke_bpyramid.mp4'),
)
ZIMG_SMOKE_OPTIONS = (
    ('--input', 'build/cxx20-warning-scan/smoke_zimg.yuv'),
    ('--input-res', '96x96'),
    ('--fps', '1'),
    ('--frames', '1'),
    ('--vf', 'zimg:lanczos(64,64)'),
    ('--output', 'build/cxx20-warning-scan/smoke_zimg.hevc'),
)
LINUX_GCC_SMOKE_OPTIONS = (
    ('--input', 'build/cxx20-linux-gcc-compile-commands/smoke_linux_gcc.yuv'),
    ('--input-res', '64x64'),
    ('--fps', '1'),
    ('--frames', '1'),
    ('--output', 'build/cxx20-linux-gcc-compile-commands/smoke_linux_gcc.hevc'),
)
WARNING_SCAN_SMOKES = (
    (
        '12-bit warning-scan smoke',
        'build/cxx20-warning-scan-12bit/x265.exe',
        (
            ('--input', 'build/cxx20-warning-scan-12bit/smoke_12bit.yuv'),
            ('--input-res', '64x64'),
            ('--input-depth', '12'),
            ('--output-depth', '12'),
            ('--fps', '1'),
            ('--frames', '1'),
            ('--output', 'build/cxx20-warning-scan-12bit/smoke_12bit.hevc'),
        ),
        'test -s build/cxx20-warning-scan-12bit/smoke_12bit.hevc',
    ),
    (
        'shared-library warning-scan smoke',
        'build/cxx20-warning-scan-shared-library/x265.exe',
        (
            ('--input', 'build/cxx20-warning-scan-shared-library/smoke_shared.yuv'),
            ('--input-res', '64x64'),
            ('--fps', '1'),
            ('--frames', '1'),
            ('--output', 'build/cxx20-warning-scan-shared-library/smoke_shared.hevc'),
        ),
        'test -s build/cxx20-warning-scan-shared-library/smoke_shared.hevc',
    ),
    (
        'all-bit-depth warning-scan smoke',
        'build/cxx20-warning-scan-all/x265.exe',
        (
            ('--input', 'build/cxx20-warning-scan-all/smoke_all.yuv'),
            ('--input-res', '64x64'),
            ('--input-depth', '10'),
            ('--output-depth', '10'),
            ('--fps', '1'),
            ('--frames', '1'),
            ('--output', 'build/cxx20-warning-scan-all/smoke_all.hevc'),
        ),
        'test -s build/cxx20-warning-scan-all/smoke_all.hevc',
    ),
)
GITHUB_EXPR = re.compile(r'\$\{\{.*?\}\}', re.DOTALL)
RUN_LINE = re.compile(r'^(?P<indent>\s*)run:\s*(?P<value>.*)$')


class GuardFailure(Exception):
    def __init__(self, message, path=None, line=None):
        super().__init__(message)
        self.message = message
        self.path = path
        self.line = line


def annotation_path(path):
    return Path(path).as_posix()


def fail(message, path=None, line=None):
    raise GuardFailure(message, path, line)


def report_failure(exc):
    if exc.path is not None:
        location = f' file={annotation_path(exc.path)}'
        if exc.line is not None:
            location += f',line={exc.line}'
        print(f'::error{location}::{exc.message}')
        raise SystemExit(f'{exc.message}: {annotation_path(exc.path)}')
    print(f'::error::{exc.message}')
    raise SystemExit(exc.message)


def read_text(path):
    return Path(path).read_text(encoding='utf-8')


def yaml_files(repo_root):
    workflow_files = sorted((repo_root / WORKFLOW_DIR).glob('*.yml'))
    action_files = sorted((repo_root / ACTION_DIR).glob('*/action.yml'))
    return workflow_files + action_files


def validate_yaml_parse_with_pyyaml(repo_root):
    import yaml

    for path in yaml_files(repo_root):
        try:
            parsed = yaml.safe_load(read_text(path))
        except yaml.YAMLError as exc:
            line = getattr(getattr(exc, 'problem_mark', None), 'line', None)
            fail(str(exc), path, None if line is None else line + 1)
        if not isinstance(parsed, dict):
            fail('YAML file did not parse to a mapping', path)
        if WORKFLOW_DIR.as_posix() in path.as_posix().replace('\\', '/') and 'jobs' not in parsed:
            fail('workflow YAML is missing a jobs mapping', path)
        if path.name == 'action.yml' and 'runs' not in parsed:
            fail('action YAML is missing a runs mapping', path)


def validate_yaml_parse_with_ruby(repo_root, ruby):
    for path in yaml_files(repo_root):
        result = subprocess.run(
            [ruby, '-e', 'require "yaml"; YAML.load_file(ARGV[0])', str(path)],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        if result.returncode != 0:
            fail(result.stdout.strip() or 'Ruby YAML parser failed', path)


def validate_yaml_parse(repo_root):
    try:
        validate_yaml_parse_with_pyyaml(repo_root)
        print('YAML files parsed with PyYAML')
        return
    except ModuleNotFoundError:
        ruby = shutil.which('ruby')
        if not ruby:
            fail('PyYAML is unavailable and ruby was not found for YAML parsing')
        validate_yaml_parse_with_ruby(repo_root, ruby)
        print('YAML files parsed with ruby')


def validate_yaml_text(repo_root):
    for path in yaml_files(repo_root):
        text = read_text(path)
        for index, line in enumerate(text.splitlines(), 1):
            if '\t' in line:
                fail('YAML indentation must not contain tab characters', path, index)
        if path.suffix != '.yml':
            continue
        if path.parent == repo_root / WORKFLOW_DIR and 'jobs:' not in text:
            fail('workflow text is missing jobs:', path)


def load_yaml(repo_root, relative_path):
    import yaml

    path = repo_root / relative_path
    try:
        parsed = yaml.safe_load(read_text(path))
    except yaml.YAMLError as exc:
        line = getattr(getattr(exc, 'problem_mark', None), 'line', None)
        fail(str(exc), path, None if line is None else line + 1)
    if not isinstance(parsed, dict):
        fail('YAML file did not parse to a mapping', path)
    return parsed


def workflow_jobs(parsed, path):
    jobs = parsed.get('jobs')
    if not isinstance(jobs, dict):
        fail('workflow YAML is missing a jobs mapping', path)
    return jobs


def workflow_steps(parsed, path, job_name):
    job = workflow_jobs(parsed, path).get(job_name)
    if not isinstance(job, dict):
        fail(f'missing workflow job: {job_name}', path)
    steps = job.get('steps')
    if not isinstance(steps, list):
        fail(f'workflow job {job_name} is missing a steps list', path)
    return steps


def action_steps(parsed, path):
    runs = parsed.get('runs')
    if not isinstance(runs, dict):
        fail('action YAML is missing a runs mapping', path)
    steps = runs.get('steps')
    if not isinstance(steps, list):
        fail('action YAML is missing a runs.steps list', path)
    return steps


def named_step(steps, step_name, path, required_items=(), job_name=None):
    for step in steps:
        if isinstance(step, dict) and step.get('name') == step_name:
            return step
    for step in steps:
        if not isinstance(step, dict):
            continue
        run = step.get('run')
        if isinstance(run, str) and any(required in run for required in required_items):
            return step
    prefix = f'job {job_name} ' if job_name else ''
    fail(f'missing {prefix}step: {step_name}', path)


def required_run(step, path, step_name):
    run = step.get('run')
    if not isinstance(run, str) or not run.strip():
        fail(f'step {step_name} is missing a run block', path)
    return run


def require_run_text(script, required, path, context):
    if required not in script:
        fail(f'missing required {context} snippet: {required}', path)


def block_scalar(lines, start_index, base_indent):
    collected = []
    index = start_index + 1
    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        indent = len(line) - len(line.lstrip(' '))
        if stripped and indent <= base_indent:
            break
        collected.append(line)
        index += 1

    nonblank_indents = [len(line) - len(line.lstrip(' ')) for line in collected if line.strip()]
    dedent = min(nonblank_indents, default=base_indent + 2)
    script = '\n'.join(line[dedent:] if len(line) >= dedent else '' for line in collected)
    return script, index


def collect_run_blocks(path):
    lines = read_text(path).splitlines()
    blocks = []
    index = 0
    while index < len(lines):
        match = RUN_LINE.match(lines[index])
        if not match:
            index += 1
            continue

        value = match.group('value').strip()
        base_indent = len(match.group('indent'))
        line_number = index + 1
        if value.startswith('|') or value.startswith('>'):
            script, index = block_scalar(lines, index, base_indent)
            if script.strip():
                blocks.append((path, line_number, script))
            continue
        if value:
            blocks.append((path, line_number, value))
        index += 1
    return blocks


def sanitize_github_expressions(script):
    return GITHUB_EXPR.sub('github_expr', script)


def bash_path(args_bash):
    candidate = args_bash or os.environ.get('CI_GUARD_BASH') or shutil.which('bash')
    if not candidate:
        fail('bash executable not found; set CI_GUARD_BASH or pass --bash')
    return candidate


def bash_check(bash, script_path, source_path, line):
    result = subprocess.run(
        [bash, '-n', str(script_path)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if result.returncode != 0:
        message = result.stdout.strip() or 'bash -n failed'
        fail(message, source_path, line)


def validate_run_blocks(repo_root, bash):
    blocks = []
    for path in yaml_files(repo_root):
        blocks.extend(collect_run_blocks(path))
    if not blocks:
        fail('no CI run blocks found')

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_root = Path(temp_dir)
        for number, (path, line, script) in enumerate(blocks, 1):
            script_path = temp_root / f'run-block-{number}.sh'
            script_path.write_text(sanitize_github_expressions(script) + '\n', encoding='utf-8')
            bash_check(bash, script_path, path, line)
    print(f'Validated bash syntax for {len(blocks)} CI run blocks')


def validate_scan_helper(repo_root, bash):
    helper = repo_root / SCAN_HELPER
    if not helper.is_file():
        fail('missing C++20 warning scan helper', helper)
    bash_check(bash, helper, helper, 1)
    text = read_text(helper)
    tokens = shlex.split(sanitize_github_expressions(text))
    for required in ('--forbidden-flag=-fprofile-instr-use', '--forbidden-flag-substring=-fprofile-instr-use='):
        if required not in tokens:
            fail(f'missing profiling compile_commands guard: {required}', helper)
    print(f'{SCAN_HELPER.as_posix()}: bash syntax validated')


def run_guard(repo_root, *command):
    result = subprocess.run(
        command,
        cwd=repo_root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if result.returncode != 0:
        raise SystemExit(result.stdout)
    print(result.stdout, end='')


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


def strip_shell_comment(line):
    stripped = []
    in_single_quote = False
    in_double_quote = False
    escaped = False
    for char in line:
        if escaped:
            stripped.append(char)
            escaped = False
            continue
        if char == '\\' and in_double_quote:
            stripped.append(char)
            escaped = True
            continue
        if char == "'" and not in_double_quote:
            in_single_quote = not in_single_quote
            stripped.append(char)
            continue
        if char == '"' and not in_single_quote:
            in_double_quote = not in_double_quote
            stripped.append(char)
            continue
        if char == '#' and not in_single_quote and not in_double_quote:
            break
        stripped.append(char)
    return ''.join(stripped).strip()


def shell_active_lines(script):
    lines = []
    for line in script.splitlines():
        stripped = strip_shell_comment(line)
        if stripped:
            lines.append(stripped)
    return lines


def shell_active_logical_lines(script):
    logical_lines = []
    current = ''
    for line in shell_active_lines(script):
        if current:
            current += ' ' + line
        else:
            current = line
        if current.endswith('\\'):
            current = current[:-1].rstrip()
            continue
        logical_lines.append(current)
        current = ''
    if current:
        logical_lines.append(current)
    return logical_lines


def require_active_line_contains(active_lines, required, path, message):
    if not any(required in line for line in active_lines):
        fail(message, path)


def option_value(args, option, expected, build, context):
    try:
        actual = args[args.index(option) + 1]
    except (ValueError, IndexError):
        fail(f'missing {context} value for {option}', build)
    if actual != expected:
        fail(f'{context} {option} must be {expected}, got {actual}', build)


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


def validate_threaded_me_smoke(repo_root):
    build = repo_root / BUILD_WORKFLOW
    blocks = [block for path, line, block in collect_run_blocks(build) if 'smoke_threaded_me' in block]
    if len(blocks) != 1:
        fail(f'expected exactly one Threaded ME smoke run block, found {len(blocks)}', build)

    script = blocks[0]
    active_lines = shell_active_lines(script)
    generator_lines = [line for line in active_lines if 'ffmpeg ' in line and 'smoke_threaded_me.y4m' in line]
    if len(generator_lines) != 1:
        fail(f'expected exactly one Threaded ME input generator command, found {len(generator_lines)}', build)
    try:
        generator_args = shlex.split(generator_lines[0])
    except ValueError as exc:
        fail(f'could not parse Threaded ME input generator command: {exc}', build)
    for option, expected in TME_GENERATOR_OPTIONS:
        try:
            actual = generator_args[generator_args.index(option) + 1]
        except (ValueError, IndexError):
            fail(f'missing Threaded ME input generator value for {option}', build)
        if actual != expected:
            fail(f'Threaded ME input generator {option} must be {expected}, got {actual}', build)
    if generator_args[-1] != 'smoke_threaded_me.y4m':
        fail(f'Threaded ME input generator must write smoke_threaded_me.y4m, got {generator_args[-1]}', build)

    command_lines = [line for line in active_lines if 'x265.exe' in line and 'smoke_threaded_me' in line]
    if len(command_lines) != 1:
        fail(f'expected exactly one Threaded ME x265 command, found {len(command_lines)}', build)

    command = command_lines[0]
    before_pipe = command.split('|', 1)[0].strip()
    try:
        tokens = shlex.split(before_pipe)
    except ValueError as exc:
        fail(f'could not parse Threaded ME smoke command: {exc}', build)

    args = [token for token in tokens if token not in ('2>&1',)]
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


def validate_mkv_smoke(repo_root):
    build = repo_root / BUILD_WORKFLOW
    parsed = load_yaml(repo_root, BUILD_WORKFLOW)
    step = named_step(
        workflow_steps(parsed, build, 'build'),
        'MKV Smoke (All CLI)',
        build,
        job_name='build',
    )
    active_lines = shell_active_logical_lines(required_run(step, build, 'MKV Smoke (All CLI)'))

    generator_lines = [line for line in active_lines if 'ffmpeg ' in line and 'smoke_mkv.y4m' in line]
    if len(generator_lines) != 1:
        fail(f'expected exactly one MKV input generator command, found {len(generator_lines)}', build)
    try:
        generator_args = shlex.split(generator_lines[0])
    except ValueError as exc:
        fail(f'could not parse MKV input generator command: {exc}', build)
    for option, expected in MKV_GENERATOR_OPTIONS:
        option_value(generator_args, option, expected, build, 'MKV input generator')
    if generator_args[-1] != 'smoke_mkv.y4m':
        fail(f'MKV input generator must write smoke_mkv.y4m, got {generator_args[-1]}', build)

    command_lines = [line for line in active_lines if 'x265.exe' in line and 'smoke_mkv' in line]
    if len(command_lines) != 1:
        fail(f'expected exactly one MKV x265 command, found {len(command_lines)}', build)
    try:
        args = shlex.split(command_lines[0])
    except ValueError as exc:
        fail(f'could not parse MKV smoke command: {exc}', build)
    if not args or args[0] != 'build/all/x265.exe':
        actual = args[0] if args else '<empty>'
        fail(f'MKV smoke must run build/all/x265.exe, got {actual}', build)
    for option, expected in MKV_SMOKE_OPTIONS:
        option_value(args, option, expected, build, 'MKV smoke')

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


def validate_lavf_smoke(repo_root):
    build = repo_root / BUILD_WORKFLOW
    parsed = load_yaml(repo_root, BUILD_WORKFLOW)
    step = named_step(
        workflow_steps(parsed, build, 'build'),
        'LAVF Input Smoke (All CLI)',
        build,
        job_name='build',
    )
    active_lines = shell_active_logical_lines(required_run(step, build, 'LAVF Input Smoke (All CLI)'))

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

    command_lines = [line for line in active_lines if 'x265.exe' in line and 'smoke_lavf' in line]
    if len(command_lines) != 1:
        fail(f'expected exactly one LAVF x265 command, found {len(command_lines)}', build)
    command = command_lines[0]
    before_pipe = command.split('|', 1)[0].strip()
    try:
        tokens = shlex.split(before_pipe)
    except ValueError as exc:
        fail(f'could not parse LAVF smoke command: {exc}', build)
    args = [token for token in tokens if token not in ('2>&1',)]
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


def validate_gop_output_smoke(repo_root):
    build = repo_root / BUILD_WORKFLOW
    parsed = load_yaml(repo_root, BUILD_WORKFLOW)
    step = named_step(
        workflow_steps(parsed, build, 'build'),
        'GOP Output Smoke (All CLI)',
        build,
        job_name='build',
    )
    active_lines = shell_active_logical_lines(required_run(step, build, 'GOP Output Smoke (All CLI)'))

    generator_lines = [line for line in active_lines if 'ffmpeg ' in line and 'smoke_gop.y4m' in line]
    if len(generator_lines) != 1:
        fail(f'expected exactly one GOP input generator command, found {len(generator_lines)}', build)
    try:
        generator_args = shlex.split(generator_lines[0])
    except ValueError as exc:
        fail(f'could not parse GOP input generator command: {exc}', build)
    for option, expected in GOP_GENERATOR_OPTIONS:
        option_value(generator_args, option, expected, build, 'GOP input generator')
    if generator_args[-1] != 'smoke_gop.y4m':
        fail(f'GOP input generator must write smoke_gop.y4m, got {generator_args[-1]}', build)

    command_lines = [line for line in active_lines if 'x265.exe' in line and 'smoke_gop' in line]
    if len(command_lines) != 1:
        fail(f'expected exactly one GOP x265 command, found {len(command_lines)}', build)
    try:
        args = shlex.split(command_lines[0])
    except ValueError as exc:
        fail(f'could not parse GOP smoke command: {exc}', build)
    if not args or args[0] != 'build/all/x265.exe':
        actual = args[0] if args else '<empty>'
        fail(f'GOP smoke must run build/all/x265.exe, got {actual}', build)
    for expected in GOP_SMOKE_FLAGS:
        if expected not in args:
            fail(f'missing GOP smoke argument: {expected}', build)
    for option, expected in GOP_SMOKE_OPTIONS:
        option_value(args, option, expected, build, 'GOP smoke')

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
    parsed = load_yaml(repo_root, BUILD_WORKFLOW)

    smoke_steps = (
        (
            'MP4 smoke',
            'MP4 Smoke (All CLI)',
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
            'MP4 24000/1001 smoke',
            'MP4 Smoke (All CLI 24000/1001)',
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
    )

    for context, step_name, input_prefix, output, probe_fields, generator_fps, generator_frames, generator_pix_fmt, required_flags, required_options, required_lines in smoke_steps:
        step = named_step(workflow_steps(parsed, build, 'build'), step_name, build, job_name='build')
        active_lines = shell_active_logical_lines(required_run(step, build, step_name))
        generator_line = f'make_y4m {input_prefix}.y4m {generator_fps} {generator_frames} {generator_pix_fmt}'
        if generator_line not in active_lines:
            fail(f'{context} must generate {generator_frames}-frame {generator_pix_fmt} input', build)

        command_lines = [line for line in active_lines if 'build/all/x265.exe' in line and output in line]
        if len(command_lines) != 1:
            fail(f'expected exactly one {context} x265 command, found {len(command_lines)}', build)
        before_pipe = command_lines[0].split('|', 1)[0].strip()
        if before_pipe.startswith('if '):
            before_pipe = before_pipe[3:].strip()
            before_pipe = before_pipe.split('; then', 1)[0].strip()
        try:
            args = shlex.split(before_pipe)
        except ValueError as exc:
            fail(f'could not parse {context} command: {exc}', build)
        if not args or args[0] != 'build/all/x265.exe':
            actual = args[0] if args else '<empty>'
            fail(f'{context} must run build/all/x265.exe, got {actual}', build)
        for expected in required_flags:
            if expected not in args:
                fail(f'missing {context} argument: {expected}', build)
        for option, expected in required_options:
            option_value(args, option, expected, build, context)

        for required, message in required_lines.items():
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
    command_lines = [line for line in active_lines if 'x265.exe' in line and 'smoke_zimg' in line]
    if len(command_lines) != 1:
        fail(f'expected exactly one ZIMG x265 command, found {len(command_lines)}', build)

    command = command_lines[0]
    before_pipe = command.split('|', 1)[0].strip()
    try:
        tokens = shlex.split(before_pipe)
    except ValueError as exc:
        fail(f'could not parse ZIMG smoke command: {exc}', build)

    args = [token for token in tokens if token not in ('2>&1',)]
    if not args or args[0] != 'build/cxx20-warning-scan/x265.exe':
        actual = args[0] if args else '<empty>'
        fail(f'ZIMG smoke must run build/cxx20-warning-scan/x265.exe, got {actual}', build)
    for option, expected in ZIMG_SMOKE_OPTIONS:
        option_value(args, option, expected, build, 'ZIMG smoke')

    active_required = {
        'test -s build/cxx20-warning-scan/smoke_zimg.hevc': 'ZIMG smoke must require non-empty HEVC output',
        "grep -Fq 'zimg [info]: Resize: 64x64' build/cxx20-warning-scan/smoke_zimg.log": 'ZIMG smoke must require resize log',
        "grep -Fq 'encoded 1 frames' build/cxx20-warning-scan/smoke_zimg.log": 'ZIMG smoke must require encoded-frame log',
    }
    for required, message in active_required.items():
        if required not in active_lines:
            fail(message, build)
    if 'tee build/cxx20-warning-scan/smoke_zimg.log' not in command:
        fail('ZIMG smoke must capture x265 log to build/cxx20-warning-scan/smoke_zimg.log', build)
    print('ZIMG smoke guard validated')


def validate_linux_gcc_smoke(repo_root):
    build = repo_root / BUILD_WORKFLOW
    parsed = load_yaml(repo_root, BUILD_WORKFLOW)
    step = named_step(
        workflow_steps(parsed, build, 'cxx20-linux-gcc-compile-commands'),
        'Run Linux GCC C++20 compile command diagnostics',
        build,
        job_name='cxx20-linux-gcc-compile-commands',
    )
    active_lines = shell_active_logical_lines(required_run(step, build, 'Run Linux GCC C++20 compile command diagnostics'))
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
            'cxx20-gcc-compile-commands',
            'Run GCC C++20 compile command diagnostics',
            (
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
                ('check_cxx20_commands_gcc build/cxx20-linux-gcc-compile-commands', 'Linux GCC diagnostics must actively check compile commands'),
                ('--required-file-substring=source/output/reconplay.cpp', 'Linux GCC diagnostics must actively require reconplay.cpp'),
                ('--forbidden-file-substring=source/common/winxp.cpp', 'Linux GCC diagnostics must actively reject winxp.cpp'),
                ('ninja -C build/cxx20-linux-gcc-compile-commands cli', 'Linux GCC diagnostics must actively build CLI'),
                ('build/cxx20-linux-gcc-compile-commands/x265 --input', 'Linux GCC diagnostics must actively run x265 smoke'),
                ("grep -Fq 'encoded 1 frames' build/cxx20-linux-gcc-compile-commands/smoke_linux_gcc.log", 'Linux GCC diagnostics must actively require encoded-frame smoke log'),
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
            ),
        ),
        (
            'cxx20-warning-scan',
            'Run C++20 shared and all-bit-depth warning scans',
            (
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
    for job_name, step_name, required_items in requirements:
        step = named_step(workflow_steps(parsed, build, job_name), step_name, build, job_name=job_name)
        active_lines = shell_active_logical_lines(required_run(step, build, step_name))
        for required, message in required_items:
            require_active_line_contains(active_lines, required, build, message)
    print('GNU++20 diagnostic step active commands validated')


def build_step_requirements():
    return (
        ('validate-deps-cache-suffix', 'Check CI guardrails', REQUIRED_BUILD_SNIPPETS[:2]),
        ('validate-deps-cache-suffix', 'Check CMake C++20 contract', REQUIRED_BUILD_SNIPPETS[2:3]),
        ('validate-deps-cache-suffix', 'Check CMake C++20 contract guardrails', REQUIRED_BUILD_SNIPPETS[3:4]),
        ('validate-deps-cache-suffix', 'Check C++20 compile command guardrails', REQUIRED_BUILD_SNIPPETS[4:5]),
        ('validate-deps-cache-suffix', 'Check dependency patch cache suffixes', REQUIRED_BUILD_SNIPPETS[5:6]),
        ('validate-deps-cache-suffix', 'Check dependency patch suffix guardrails', REQUIRED_BUILD_SNIPPETS[6:7]),
        ('validate-deps-cache-suffix', 'Check release needs guardrails', REQUIRED_BUILD_SNIPPETS[7:8]),
        ('validate-deps-cache-suffix', 'Check PGO metadata/consume guardrails', REQUIRED_BUILD_SNIPPETS[8:9]),
        ('build', 'Get Latest Tag', REQUIRED_BUILD_SNIPPETS[9:10]),
        ('build', 'Compile X265', REQUIRED_BUILD_SNIPPETS[10:16]),
        ('build', 'Threaded ME Smoke (All CLI)', REQUIRED_BUILD_SNIPPETS[21:28]),
        ('build', 'GOP Output Smoke (All CLI)', REQUIRED_BUILD_SNIPPETS[28:39]),
        ('cxx20-linux-gcc-compile-commands', 'Run Linux GCC C++20 compile command diagnostics', REQUIRED_BUILD_SNIPPETS[39:41] + REQUIRED_BUILD_SNIPPETS[44:52]),
        ('cxx20-warning-scan', 'Run C++20 CLI and dependency warning scans', REQUIRED_BUILD_SNIPPETS[85:91]),
        ('cxx20-warning-scan', 'Run C++20 shared and all-bit-depth warning scans', REQUIRED_BUILD_SNIPPETS[16:21] + REQUIRED_BUILD_SNIPPETS[84:85]),
        ('cxx20-gcc-compile-commands', 'Run GCC C++20 compile command diagnostics', REQUIRED_BUILD_SNIPPETS[16:21] + REQUIRED_BUILD_SNIPPETS[41:44] + REQUIRED_BUILD_SNIPPETS[91:]),
    )


def profiling_step_requirements():
    return (
        ('validate-guardrails', 'Check CI guardrails', REQUIRED_BUILD_PROFILING_SNIPPETS[3:5]),
        ('build', 'Get Latest Tag', REQUIRED_BUILD_PROFILING_SNIPPETS[5:6]),
        ('build', 'Get CI Version', REQUIRED_BUILD_PROFILING_SNIPPETS[6:7]),
        ('build', 'Package LLVM Profdata Tool', REQUIRED_BUILD_PROFILING_SNIPPETS[10:12]),
        ('build', 'Smoke, Package, and Verify 8b-lib', REQUIRED_BUILD_PROFILING_SNIPPETS[7:9] + REQUIRED_BUILD_PROFILING_SNIPPETS[13:16] + REQUIRED_BUILD_PROFILING_SNIPPETS[22:23] + REQUIRED_BUILD_PROFILING_SNIPPETS[23:24] + REQUIRED_BUILD_PROFILING_SNIPPETS[25:26] + REQUIRED_BUILD_PROFILING_SNIPPETS[28:29]),
        ('build', 'Smoke, Package, and Verify 12b-lib', REQUIRED_BUILD_PROFILING_SNIPPETS[7:8] + REQUIRED_BUILD_PROFILING_SNIPPETS[9:10] + REQUIRED_BUILD_PROFILING_SNIPPETS[16:19] + REQUIRED_BUILD_PROFILING_SNIPPETS[22:23] + REQUIRED_BUILD_PROFILING_SNIPPETS[23:24] + REQUIRED_BUILD_PROFILING_SNIPPETS[26:27] + REQUIRED_BUILD_PROFILING_SNIPPETS[28:29]),
        ('build', 'Smoke, Package, and Verify All', REQUIRED_BUILD_PROFILING_SNIPPETS[7:8] + REQUIRED_BUILD_PROFILING_SNIPPETS[12:13] + REQUIRED_BUILD_PROFILING_SNIPPETS[19:24] + REQUIRED_BUILD_PROFILING_SNIPPETS[27:]),
    )


def validate_workflow_steps(repo_root, relative_path, context, requirements):
    path = repo_root / relative_path
    parsed = load_yaml(repo_root, relative_path)
    for job_name, step_name, required_items in requirements:
        step = named_step(workflow_steps(parsed, path, job_name), step_name, path, required_items, job_name)
        script = required_run(step, path, step_name)
        for required in required_items:
            require_run_text(script, required, path, context)
    return parsed


def validate_required_snippets(repo_root):
    validate_workflow_steps(repo_root, BUILD_WORKFLOW, 'Build workflow guard', build_step_requirements())
    build_profiling = validate_workflow_steps(repo_root, BUILD_PROFILING_WORKFLOW, 'Build Profiling workflow guard', profiling_step_requirements())
    validate_workflow_steps(repo_root, UPDATE_DEPS_WORKFLOW, 'update-deps guard', (
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
    profiling_action = load_yaml(repo_root, BUILD_PROFILING_ACTION)
    profiling_action_path = repo_root / BUILD_PROFILING_ACTION
    for step_name, required_items in (
        ('Build 8b-lib profiling CLI', REQUIRED_BUILD_PROFILING_ACTION_SNIPPETS[:3] + REQUIRED_BUILD_PROFILING_ACTION_SNIPPETS[5:]),
        ('Build 12b-lib profiling CLI', REQUIRED_BUILD_PROFILING_ACTION_SNIPPETS[:2] + REQUIRED_BUILD_PROFILING_ACTION_SNIPPETS[3:4]),
        ('Build all profiling CLI', REQUIRED_BUILD_PROFILING_ACTION_SNIPPETS[:2] + REQUIRED_BUILD_PROFILING_ACTION_SNIPPETS[4:5]),
    ):
        step = named_step(action_steps(profiling_action, profiling_action_path), step_name, profiling_action_path)
        script = required_run(step, profiling_action_path, step_name)
        for required in required_items:
            require_run_text(script, required, profiling_action_path, 'Build Profiling action guard')

    windows_deps = load_yaml(repo_root, WINDOWS_DEPS_ACTION)
    windows_deps_path = repo_root / WINDOWS_DEPS_ACTION
    for step_name, required_items in (
        ('Verify MSYS2 Toolchain', REQUIRED_WINDOWS_DEPS_ACTION_SNIPPETS[:5]),
        ('Compile L-SMASH', REQUIRED_WINDOWS_DEPS_ACTION_SNIPPETS[5:8]),
        ('Compile GOP muxer', REQUIRED_WINDOWS_DEPS_ACTION_SNIPPETS[8:]),
    ):
        step = named_step(action_steps(windows_deps, windows_deps_path), step_name, windows_deps_path)
        script = required_run(step, windows_deps_path, step_name)
        for required in required_items:
            require_run_text(script, required, windows_deps_path, 'setup-windows-deps guard')
    print('Required CI guard steps validated')


def validate_warning_scan_dependencies(repo_root):
    build_path = repo_root / BUILD_WORKFLOW
    parsed = load_yaml(repo_root, BUILD_WORKFLOW)
    step = named_step(workflow_steps(parsed, build_path, 'cxx20-warning-scan'), 'Setup Shared Dependencies', build_path, job_name='cxx20-warning-scan')
    with_values = step.get('with')
    if not isinstance(with_values, dict):
        fail('C++20 warning scan dependency setup is missing with inputs', build_path)
    packages = with_values.get('extra-msys2-packages')
    if not isinstance(packages, str) or 'mingw-w64-clang-x86_64-zimg' not in packages.split():
        fail('C++20 warning scan dependency setup must install mingw-w64-clang-x86_64-zimg', build_path)
    print('C++20 warning scan dependency setup validated')


def main():
    parser = argparse.ArgumentParser(description='Check CI workflow guardrails that are easy to miss by hand')
    parser.add_argument('--repo-root', type=Path, default=Path.cwd())
    parser.add_argument('--before')
    parser.add_argument('--after')
    parser.add_argument('--bash', help='bash executable used for syntax checks')
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    try:
        validate_yaml_text(repo_root)
        validate_yaml_parse(repo_root)
        bash = bash_path(args.bash)
        validate_run_blocks(repo_root, bash)
        validate_scan_helper(repo_root, bash)
        validate_dependency_update_anchors(repo_root)
        validate_required_snippets(repo_root)
        validate_warning_scan_dependencies(repo_root)
        validate_pgo_consume_helper(repo_root)
        validate_threaded_me_smoke(repo_root)
        validate_mkv_smoke(repo_root)
        validate_lavf_smoke(repo_root)
        validate_gop_output_smoke(repo_root)
        validate_mp4_smokes(repo_root)
        validate_zimg_smoke(repo_root)
        validate_linux_gcc_smoke(repo_root)
        validate_warning_scan_runtime_smokes(repo_root)
        validate_gnu20_diagnostic_steps(repo_root)
        validate_dependency_suffixes(repo_root, args.before, args.after)
    except GuardFailure as exc:
        report_failure(exc)
    print('CI guardrails validated')


if __name__ == '__main__':
    main()
