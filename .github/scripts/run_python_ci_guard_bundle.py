#!/usr/bin/env python3
import argparse
import os
import shlex
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


CHECK_CI_GUARDS_COMMAND = ('python', '.github/scripts/check_ci_guards.py')
NON_EXECUTED_TESTS = {'test_check_ci_guards_fixture.py'}
WORKFLOW_GUARD_SUITE = (
    CHECK_CI_GUARDS_COMMAND,
    ('python', '.github/scripts/test_check_ci_guards.py'),
    ('python', '.github/scripts/test_check_ci_guards_helpers.py'),
    ('python', '.github/scripts/test_check_ci_guards_checks.py'),
    ('python', '.github/scripts/test_check_ci_guards_data.py'),
)
PROFDATA_GUARD_SUITE = WORKFLOW_GUARD_SUITE + (
    ('python', '.github/scripts/check_profdata_metadata.py', '--self-test'),
    ('python', '.github/scripts/test_check_profdata_metadata.py'),
)
SUITE_COMMANDS = {
    'default': (),
    'update-deps': WORKFLOW_GUARD_SUITE + (
        ('python', '.github/scripts/check_dependency_patch_suffixes.py', '--allow-missing-cache'),
    ),
    'profdata': PROFDATA_GUARD_SUITE,
    'pgo': PROFDATA_GUARD_SUITE + (
        ('python', '.github/scripts/test_check_pgo_consume_chain.py'),
    ),
}


def normalize_python(command):
    if command and command[0] == 'python':
        return (sys.executable, *command[1:])
    return command


def default_jobs():
    return max(1, min(8, os.cpu_count() or 2))


def command_text(command):
    return ' '.join(shlex.quote(part) for part in command)


def run_command(repo_root, command):
    printable = command_text(command)
    print(f'+ {printable}', flush=True)
    subprocess.run(normalize_python(command), cwd=repo_root, check=True)


def run_command_capture(repo_root, command):
    start = time.monotonic()
    result = subprocess.run(
        normalize_python(command),
        cwd=repo_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding='utf-8',
        errors='replace',
    )
    elapsed = time.monotonic() - start
    return command, result.returncode, result.stdout, elapsed


def run_commands_parallel(repo_root, commands, jobs):
    commands = tuple(commands)
    if not commands:
        return
    if jobs <= 1 or len(commands) == 1:
        for command in commands:
            run_command(repo_root, command)
        return

    worker_count = min(jobs, len(commands))
    print(f'+ running {len(commands)} commands with {worker_count} parallel jobs', flush=True)
    for command in commands:
        print(f'+ {command_text(command)}', flush=True)

    results = [None] * len(commands)
    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        future_indexes = {
            executor.submit(run_command_capture, repo_root, command): index
            for index, command in enumerate(commands)
        }
        for future in as_completed(future_indexes):
            index = future_indexes[future]
            results[index] = future.result()

    failures = []
    for command, returncode, output, elapsed in results:
        if returncode == 0:
            print(f'ok {command_text(command)} ({elapsed:.1f}s)', flush=True)
            continue
        failures.append((command, returncode, output, elapsed))

    if failures:
        for command, returncode, output, elapsed in failures:
            print(f'FAILED {command_text(command)} ({elapsed:.1f}s, exit {returncode})', flush=True)
            if output:
                print(output, end='' if output.endswith('\n') else '\n', flush=True)
        raise SystemExit(f'{len(failures)} parallel command(s) failed')


def guard_test_scripts(repo_root):
    script_dir = repo_root / '.github' / 'scripts'
    return tuple(
        sorted(
            path
            for path in script_dir.glob('test_check_*.py')
            if path.name not in NON_EXECUTED_TESTS
        )
    )


def run_default_suite(repo_root, jobs):
    run_command(repo_root, CHECK_CI_GUARDS_COMMAND)
    commands = []
    for test_script in guard_test_scripts(repo_root):
        commands.append(('python', test_script.relative_to(repo_root).as_posix()))
    run_commands_parallel(repo_root, commands, jobs)


def run_named_suite(repo_root, suite, jobs):
    if suite == 'default':
        run_default_suite(repo_root, jobs)
        return
    commands = []
    for command in SUITE_COMMANDS[suite]:
        commands.append(command)
    if commands and commands[0] == CHECK_CI_GUARDS_COMMAND:
        run_command(repo_root, commands[0])
        commands = commands[1:]
    run_commands_parallel(repo_root, commands, jobs)


def main():
    parser = argparse.ArgumentParser(description='Run the Python CI guard bundle')
    parser.add_argument('--repo-root', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--suite', choices=tuple(SUITE_COMMANDS), default='default')
    parser.add_argument('--jobs', type=int, default=default_jobs())
    args = parser.parse_args()
    if args.jobs < 1:
        raise SystemExit('--jobs must be at least 1')

    repo_root = args.repo_root.resolve()
    run_named_suite(repo_root, args.suite, args.jobs)


if __name__ == '__main__':
    main()
