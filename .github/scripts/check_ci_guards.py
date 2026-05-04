#!/usr/bin/env python3
import argparse
import os
import re
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
    'check_pgo_consume_commands build/all "$PGO_ALL_FLAG" 60',
    '--threaded-me --pools 32 --frame-threads 1 --no-wpp --no-progress',
    'frame threads / pool features       : 1 / threaded-me',
    "! grep -Fq 'disabling --threaded-me'",
    'test -s smoke_threaded_me.hevc',
    'nb_read_frames=16',
    'gop_muxer.exe smoke_gop.gop',
    'test -s smoke_gop.mp4',
    "grep -q 'nb_read_frames=16' smoke_gop_mux_count.txt",
    'encoded 1 frames',
    'check_cxx20_commands_gcc build/cxx20-linux-gcc-compile-commands',
    'ninja -C build/cxx20-linux-gcc-compile-commands cli',
    'build/cxx20-linux-gcc-compile-commands/x265 --input',
    'test -s build/cxx20-linux-gcc-compile-commands/smoke_linux_gcc.hevc',
    'smoke_linux_gcc.hevc',
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
    'test -s profile-smoke-all.profdata',
    'test -s smoke_profile_8b.mp4',
    'test -s smoke_profile_12b.mp4',
    'test -s smoke_profile_all.mp4',
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
    'python .github/scripts/check_dependency_patch_suffixes.py',
    'for anchor in ffmpeg-ref mimalloc-ref obuparse-ref lsmash-ref lsmash-cache-suffix gop-muxer-ref gop-muxer-cache-suffix; do',
    'Unexpected dependency update diff paths:',
)
REQUIRED_WINDOWS_DEPS_ACTION_SNIPPETS = (
    'echo "=== Dependency provenance ==="',
    'lsmash=${{ inputs.lsmash-repository }}@${{ inputs.lsmash-ref }} suffix=${{ inputs.lsmash-cache-suffix }} patch=${{ inputs.lsmash-patch-path }}',
    'gop_muxer=${{ inputs.gop-muxer-repository }}@${{ inputs.gop-muxer-ref }} suffix=${{ inputs.gop-muxer-cache-suffix }} patch=${{ inputs.gop-muxer-patch-path }}',
    'git apply --ignore-whitespace --check ${{ inputs.lsmash-patch-path }}',
    'git -c core.autocrlf=false reset --hard HEAD',
    'git apply ${{ inputs.gop-muxer-patch-path }}',
    'c++ -O2 --std=gnu++20 -I/usr/local/include -c gop_muxer.cpp -o gop_muxer.o',
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


def validate_required_snippets(repo_root):
    build_text = read_text(repo_root / BUILD_WORKFLOW)
    for snippet in REQUIRED_BUILD_SNIPPETS:
        if snippet not in build_text:
            fail(f'missing required Build workflow guard snippet: {snippet}', repo_root / BUILD_WORKFLOW)

    build_profiling_text = read_text(repo_root / BUILD_PROFILING_WORKFLOW)
    for snippet in REQUIRED_BUILD_PROFILING_SNIPPETS:
        if snippet not in build_profiling_text:
            fail(f'missing required Build Profiling workflow guard snippet: {snippet}', repo_root / BUILD_PROFILING_WORKFLOW)

    build_profiling_action_text = read_text(repo_root / BUILD_PROFILING_ACTION)
    for snippet in REQUIRED_BUILD_PROFILING_ACTION_SNIPPETS:
        if snippet not in build_profiling_action_text:
            fail(f'missing required Build Profiling action guard snippet: {snippet}', repo_root / BUILD_PROFILING_ACTION)

    update_deps_text = read_text(repo_root / UPDATE_DEPS_WORKFLOW)
    for snippet in REQUIRED_UPDATE_DEPS_SNIPPETS:
        if snippet not in update_deps_text:
            fail(f'missing required update-deps guard snippet: {snippet}', repo_root / UPDATE_DEPS_WORKFLOW)

    windows_deps_text = read_text(repo_root / WINDOWS_DEPS_ACTION)
    for snippet in REQUIRED_WINDOWS_DEPS_ACTION_SNIPPETS:
        if snippet not in windows_deps_text:
            fail(f'missing required setup-windows-deps guard snippet: {snippet}', repo_root / WINDOWS_DEPS_ACTION)
    print('Required CI guard snippets validated')


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
        validate_dependency_suffixes(repo_root, args.before, args.after)
    except GuardFailure as exc:
        report_failure(exc)
    print('CI guardrails validated')


if __name__ == '__main__':
    main()
