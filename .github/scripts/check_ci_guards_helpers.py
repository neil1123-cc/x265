#!/usr/bin/env python3
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from functools import lru_cache
from pathlib import Path


GITHUB_EXPR = re.compile(r'\$\{\{.*?\}\}', re.DOTALL)
RUN_LINE = re.compile(r'^(?P<indent>\s*)run:\s*(?P<value>.*)$')
BASH_CANDIDATES = (
    Path('D:/msys64/usr/bin/bash.exe'),
    Path('C:/msys64/usr/bin/bash.exe'),
)


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
    return _read_text_cached(str(Path(path).resolve()))


@lru_cache(maxsize=None)
def _read_text_cached(path_str):
    return Path(path_str).read_text(encoding='utf-8')


def yaml_files(repo_root, workflow_dir, action_dir):
    workflow_files = sorted((repo_root / workflow_dir).glob('*.yml'))
    action_files = sorted((repo_root / action_dir).glob('*/action.yml'))
    return workflow_files + action_files


@lru_cache(maxsize=1)
def yaml_module():
    import yaml
    return yaml


def parse_yaml_with_ruby(path, ruby):
    result = subprocess.run(
        [ruby, '-e', 'require "yaml"; require "json"; print JSON.dump(YAML.load_file(ARGV[0]))', str(path)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if result.returncode != 0:
        fail(result.stdout.strip() or 'Ruby YAML parser failed', path)
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        fail(f'Ruby YAML parser returned invalid JSON: {exc}', path)


def validate_yaml_parse_with_pyyaml(repo_root, workflow_dir, action_dir):
    yaml = yaml_module()
    for path in yaml_files(repo_root, workflow_dir, action_dir):
        try:
            parsed = yaml.safe_load(read_text(path))
        except yaml.YAMLError as exc:
            line = getattr(getattr(exc, 'problem_mark', None), 'line', None)
            fail(str(exc), path, None if line is None else line + 1)
        if not isinstance(parsed, dict):
            fail('YAML file did not parse to a mapping', path)
        if workflow_dir.as_posix() in path.as_posix().replace('\\', '/') and 'jobs' not in parsed:
            fail('workflow YAML is missing a jobs mapping', path)
        if path.name == 'action.yml' and 'runs' not in parsed:
            fail('action YAML is missing a runs mapping', path)


def validate_yaml_parse_with_ruby(repo_root, workflow_dir, action_dir, ruby):
    for path in yaml_files(repo_root, workflow_dir, action_dir):
        parse_yaml_with_ruby(path, ruby)


def validate_yaml_parse(repo_root, workflow_dir, action_dir):
    try:
        validate_yaml_parse_with_pyyaml(repo_root, workflow_dir, action_dir)
        print('YAML files parsed with PyYAML')
        return
    except ModuleNotFoundError:
        ruby = shutil.which('ruby')
        if not ruby:
            fail('PyYAML is unavailable and ruby was not found for YAML parsing')
        validate_yaml_parse_with_ruby(repo_root, workflow_dir, action_dir, ruby)
        print('YAML files parsed with ruby')


def validate_yaml_text(repo_root, workflow_dir, action_dir):
    for path in yaml_files(repo_root, workflow_dir, action_dir):
        text = read_text(path)
        for index, line in enumerate(text.splitlines(), 1):
            if '\t' in line:
                fail('YAML indentation must not contain tab characters', path, index)
        if path.suffix != '.yml':
            continue
        if path.parent == repo_root / workflow_dir and 'jobs:' not in text:
            fail('workflow text is missing jobs:', path)


def load_yaml(repo_root, relative_path):
    path = repo_root / relative_path
    try:
        yaml = yaml_module()
    except ModuleNotFoundError:
        ruby = shutil.which('ruby')
        if not ruby:
            fail('PyYAML is unavailable and ruby was not found for YAML parsing', path)
        parsed = parse_yaml_with_ruby(path, ruby)
    else:
        try:
            parsed = _load_yaml_cached(str(path.resolve()))
        except yaml.YAMLError as exc:
            line = getattr(getattr(exc, 'problem_mark', None), 'line', None)
            fail(str(exc), path, None if line is None else line + 1)
    if not isinstance(parsed, dict):
        fail('YAML file did not parse to a mapping', path)
    return parsed


@lru_cache(maxsize=None)
def _load_yaml_cached(path_str):
    yaml = yaml_module()
    return yaml.safe_load(_read_text_cached(path_str))


def workflow_jobs(parsed, path):
    jobs = parsed.get('jobs')
    if not isinstance(jobs, dict):
        fail('workflow YAML is missing a jobs mapping', path)
    return jobs


def workflow_on(parsed, path):
    value = parsed.get('on')
    if value is None:
        value = parsed.get(True)
    if not isinstance(value, dict):
        fail('workflow YAML is missing an on mapping', path)
    return value


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


def require_active_run_text(script, required, path, context):
    active_lines = shell_active_logical_lines(script)
    if not any(required in line for line in active_lines):
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
    return list(_collect_run_blocks_cached(str(Path(path).resolve())))


@lru_cache(maxsize=None)
def _collect_run_blocks_cached(path_str):
    path = Path(path_str)
    lines = _read_text_cached(path_str).splitlines()
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
    return tuple(blocks)


def sanitize_github_expressions(script):
    return GITHUB_EXPR.sub('github_expr', script)


def bash_path(args_bash):
    candidate = args_bash or os.environ.get('CI_GUARD_BASH')
    if not candidate:
        for preferred in BASH_CANDIDATES:
            if preferred.exists():
                candidate = str(preferred)
                break
    if not candidate:
        candidate = shutil.which('bash')
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


def validate_run_blocks(repo_root, workflow_dir, action_dir, bash):
    blocks = []
    for path in yaml_files(repo_root, workflow_dir, action_dir):
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


def validate_bash_file(repo_root, bash, relative_path, missing_message, required_text=(), required_tokens=(), required_message='missing required bash detail'):
    path = repo_root / relative_path
    if not path.is_file():
        fail(missing_message, path)
    bash_check(bash, path, path, 1)
    text = read_text(path)
    for required in required_text:
        if required not in text:
            fail(f'{required_message}: {required}', path)
    if required_tokens:
        tokens = shlex.split(sanitize_github_expressions(text))
        for required in required_tokens:
            if required not in tokens:
                fail(f'{required_message}: {required}', path)
    print(f'{relative_path.as_posix()}: bash syntax validated')


def validate_python_file(repo_root, relative_path, missing_message, required_text=(), required_message='missing required python detail'):
    path = repo_root / relative_path
    if not path.is_file():
        fail(missing_message, path)
    result = subprocess.run(
        [sys.executable, '-m', 'py_compile', str(path)],
        cwd=repo_root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if result.returncode != 0:
        fail(f'python syntax check failed: {result.stdout.strip()}', path)
    text = read_text(path)
    for required in required_text:
        if required not in text:
            fail(f'{required_message}: {required}', path)
    print(f'{relative_path.as_posix()}: python syntax validated')


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


def clear_runtime_caches():
    _read_text_cached.cache_clear()
    _load_yaml_cached.cache_clear()
    _collect_run_blocks_cached.cache_clear()
