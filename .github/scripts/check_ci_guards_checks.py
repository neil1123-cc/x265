#!/usr/bin/env python3
import shlex

from check_ci_guards_helpers import (
    action_steps,
    fail,
    load_yaml,
    named_step,
    read_text,
    require_active_run_text,
    required_run,
    shell_active_logical_lines,
    workflow_steps,
)


def smoke_suite_active_lines(repo_root, relative_path, missing_message):
    path = repo_root / relative_path
    if not path.is_file():
        fail(missing_message, path)
    return shell_active_logical_lines(read_text(path))


def smoke_suite_function_lines(repo_root, relative_path, function_name, missing_message):
    path = repo_root / relative_path
    if not path.is_file():
        fail(missing_message, path)
    lines = read_text(path).splitlines()
    start = None
    header = f'{function_name}() {{'
    for index, line in enumerate(lines):
        if line == header:
            start = index + 1
            break
    if start is None:
        fail(f'missing function {function_name} in {relative_path.as_posix()}', path)
    end = None
    for index in range(start, len(lines)):
        if lines[index] == '}':
            end = index
            break
    if end is None:
        fail(f'missing closing brace for {function_name} in {relative_path.as_posix()}', path)
    return shell_active_logical_lines('\n'.join(lines[start:end]))


def require_active_line_contains(active_lines, required, path, message):
    if not any(required in line for line in active_lines):
        fail(message, path)


def require_active_command_prefix(active_lines, expected_tokens, path, message):
    for line in active_lines:
        try:
            tokens = shlex.split(line)
        except ValueError:
            continue
        if tuple(tokens[:len(expected_tokens)]) == expected_tokens:
            return
    fail(message, path)


def option_value(args, option, expected, build, context):
    try:
        actual = args[args.index(option) + 1]
    except (ValueError, IndexError):
        fail(f'missing {context} value for {option}', build)
    if actual != expected:
        fail(f'{context} {option} must be {expected}, got {actual}', build)


def runtime_smoke_active_lines(repo_root, runtime_smoke_suite, function_name):
    return smoke_suite_function_lines(repo_root, runtime_smoke_suite, function_name, 'missing runtime smoke suite')


def workflow_step(parsed, path, job_name, step_name, required_items=()):
    return named_step(workflow_steps(parsed, path, job_name), step_name, path, required_items, job_name)


def workflow_step_run(parsed, path, job_name, step_name, required_items=()):
    return required_run(workflow_step(parsed, path, job_name, step_name, required_items), path, step_name)


def action_step(parsed, path, step_name, required_items=()):
    return named_step(action_steps(parsed, path), step_name, path, required_items)


def action_step_run(parsed, path, step_name, required_items=()):
    return required_run(action_step(parsed, path, step_name, required_items), path, step_name)


def validate_required_workflow_steps(repo_root, relative_path, context, requirements):
    path = repo_root / relative_path
    parsed = load_yaml(repo_root, relative_path)
    for job_name, step_name, required_items in requirements:
        script = workflow_step_run(parsed, path, job_name, step_name, required_items)
        for required in required_items:
            require_active_run_text(script, required, path, context)
    return parsed


def validate_required_action_steps(repo_root, relative_path, context, requirements):
    path = repo_root / relative_path
    parsed = load_yaml(repo_root, relative_path)
    for step_name, required_items in requirements:
        script = action_step_run(parsed, path, step_name, required_items)
        for required in required_items:
            require_active_run_text(script, required, path, context)


def single_x265_args(active_lines, build, context, marker):
    command_lines = [line for line in active_lines if 'x265.exe' in line and marker in line]
    if len(command_lines) != 1:
        fail(f'expected exactly one {context} x265 command, found {len(command_lines)}', build)
    try:
        return shlex.split(command_lines[0])
    except ValueError as exc:
        fail(f'could not parse {context} command: {exc}', build)


def require_x265_command(active_lines, build, context, marker, expected_binary, expected_options):
    args = single_x265_args(active_lines, build, context, marker)
    if not args or args[0] != expected_binary:
        actual = args[0] if args else '<empty>'
        fail(f'{context} must run {expected_binary}, got {actual}', build)
    for option, expected in expected_options:
        option_value(args, option, expected, build, context)
    return args


def piped_x265_command(active_lines, build, context, marker):
    command_lines = [line for line in active_lines if 'x265.exe' in line and marker in line]
    if len(command_lines) != 1:
        fail(f'expected exactly one {context} x265 command, found {len(command_lines)}', build)
    command = command_lines[0]
    before_pipe = command.split('|', 1)[0].strip()
    try:
        tokens = shlex.split(before_pipe)
    except ValueError as exc:
        fail(f'could not parse {context} command: {exc}', build)
    args = [token for token in tokens if token not in ('2>&1',)]
    return command, args


def shell_if_command_args(command, build, context):
    before_pipe = command.split('|', 1)[0].strip()
    if before_pipe.startswith('if '):
        before_pipe = before_pipe[3:].strip()
        before_pipe = before_pipe.split('; then', 1)[0].strip()
    try:
        return shlex.split(before_pipe)
    except ValueError as exc:
        fail(f'could not parse {context} command: {exc}', build)


def validate_mp4_smoke_step(build, repo_root, mp4_smoke_suite, context, _step_name, function_name, _target, input_prefix, output, _probe_fields, generator_fps, generator_frames, generator_pix_fmt, required_flags, required_options, required_lines):
    active_lines = smoke_suite_function_lines(repo_root, mp4_smoke_suite, function_name, 'missing MP4 smoke suite')
    generator_line = f'make_y4m {input_prefix}.y4m {generator_fps} {generator_frames} {generator_pix_fmt}'
    if generator_line not in active_lines:
        fail(f'{context} must generate {generator_frames}-frame {generator_pix_fmt} input', build)

    command_lines = [line for line in active_lines if 'build/all/x265.exe' in line and output in line]
    if len(command_lines) != 1:
        fail(f'expected exactly one {context} x265 command, found {len(command_lines)}', build)
    args = shell_if_command_args(command_lines[0], build, context)
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
