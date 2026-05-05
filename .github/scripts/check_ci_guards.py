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
    '--required-file-flag=source/common/winxp.cpp=-D_WIN32_WINNT=_WIN32_WINNT_WINXP',
    '--forbidden-file-substring=source/common/winxp.cpp',
    'check_cxx20_commands_gcc build/cxx20-linux-gcc-compile-commands',
    'ninja -C build/cxx20-linux-gcc-compile-commands cli',
    'build/cxx20-linux-gcc-compile-commands/x265 --input',
    'build/cxx20-linux-gcc-compile-commands/smoke_linux_gcc.log',
    'test -s build/cxx20-linux-gcc-compile-commands/smoke_linux_gcc.log',
    'test -s build/cxx20-linux-gcc-compile-commands/smoke_linux_gcc.hevc',
    'smoke_linux_gcc.hevc',
    'configure_cxx20_scan x265/source build/cxx20-warning-scan-all-12b-lib',
    'ninja -C build/cxx20-warning-scan-all-12b-lib x265-static',
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
    ('--input-res', '160x90'),
    ('--fps', '24'),
    ('--frames', '16'),
    ('--preset', 'medium'),
    ('--pools', '32'),
    ('--frame-threads', '1'),
)
TME_SMOKE_REQUIRED_LINES = (
    'test -s smoke_threaded_me.hevc',
    "grep -Fq 'frame threads / pool features       : 1 / threaded-me' smoke_threaded_me_log.txt",
    "! grep -Fq 'disabling --threaded-me' smoke_threaded_me_log.txt",
    "grep -q 'nb_read_frames=16' smoke_threaded_me_count.txt",
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


def validate_threaded_me_smoke(repo_root):
    build = repo_root / BUILD_WORKFLOW
    blocks = [block for path, line, block in collect_run_blocks(build) if 'smoke_threaded_me' in block]
    if len(blocks) != 1:
        fail(f'expected exactly one Threaded ME smoke run block, found {len(blocks)}', build)

    script = blocks[0]
    command_lines = [line.strip() for line in script.splitlines() if 'x265.exe' in line and 'smoke_threaded_me' in line]
    if len(command_lines) != 1:
        fail(f'expected exactly one Threaded ME x265 command, found {len(command_lines)}', build)

    command = command_lines[0]
    before_pipe = command.split('|', 1)[0].strip()
    try:
        tokens = shlex.split(before_pipe)
    except ValueError as exc:
        fail(f'could not parse Threaded ME smoke command: {exc}', build)

    args = [token for token in tokens if token not in ('2>&1',)]
    for expected in TME_SMOKE_FLAGS:
        if expected not in args:
            fail(f'missing Threaded ME smoke argument: {expected}', build)
    for option, expected in TME_SMOKE_OPTIONS:
        try:
            actual = args[args.index(option) + 1]
        except (ValueError, IndexError):
            fail(f'missing Threaded ME smoke value for {option}', build)
        if actual != expected:
            fail(f'Threaded ME smoke {option} must be {expected}, got {actual}', build)

    for required in TME_SMOKE_REQUIRED_LINES:
        if required not in script:
            fail(f'missing Threaded ME smoke check: {required}', build)
    if 'tee smoke_threaded_me_log.txt' not in command:
        fail('Threaded ME smoke must capture x265 log to smoke_threaded_me_log.txt', build)
    if 'ffprobe -v error -count_frames' not in script or 'smoke_threaded_me.hevc > smoke_threaded_me_count.txt' not in script:
        fail('Threaded ME smoke must count frames from smoke_threaded_me.hevc', build)
    print('Threaded ME smoke guard validated')


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
        ('cxx20-linux-gcc-compile-commands', 'Run Linux GCC C++20 compile command diagnostics', REQUIRED_BUILD_SNIPPETS[39:41] + REQUIRED_BUILD_SNIPPETS[43:51]),
        ('cxx20-warning-scan', 'Run C++20 shared and all-bit-depth warning scans', REQUIRED_BUILD_SNIPPETS[16:21] + REQUIRED_BUILD_SNIPPETS[51:53]),
        ('cxx20-gcc-compile-commands', 'Run GCC C++20 compile command diagnostics', REQUIRED_BUILD_SNIPPETS[16:21] + REQUIRED_BUILD_SNIPPETS[41:43] + REQUIRED_BUILD_SNIPPETS[53:]),
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
        validate_threaded_me_smoke(repo_root)
        validate_dependency_suffixes(repo_root, args.before, args.after)
    except GuardFailure as exc:
        report_failure(exc)
    print('CI guardrails validated')


if __name__ == '__main__':
    main()
