#!/usr/bin/env python3
import argparse
from pathlib import Path


WORKFLOW = Path('.github/workflows/build.yml')
RUNNER = Path('.github/scripts/run_python_ci_guard_bundle.py')
WORKFLOW_RUNNER_COMMAND = 'python .github/scripts/run_python_ci_guard_bundle.py'
REQUIRED_RUNNER_SNIPPETS = (
    "CHECK_CI_GUARDS_COMMAND = ('python', '.github/scripts/check_ci_guards.py')",
    "NON_EXECUTED_TESTS = {'test_check_ci_guards_fixture.py'}",
    "script_dir.glob('test_check_*.py')",
    'if path.name not in NON_EXECUTED_TESTS',
    'run_command(repo_root, CHECK_CI_GUARDS_COMMAND)',
    'for test_script in guard_test_scripts(repo_root):',
    "commands.append(('python', test_script.relative_to(repo_root).as_posix()))",
    '    run_commands_parallel(repo_root, commands, jobs)',
    "parser.add_argument('--jobs', type=int, default=default_jobs())",
)


def read_required_file(repo_root, relative, missing_message):
    path = repo_root / relative
    if not path.is_file():
        return None, [(relative.as_posix(), 0, missing_message)]
    return path.read_text(encoding='utf-8', errors='ignore'), []


def check_repo(repo_root):
    repo_root = Path(repo_root)
    failures = []

    workflow_text, workflow_failures = read_required_file(repo_root, WORKFLOW, 'missing build workflow')
    failures.extend(workflow_failures)
    if workflow_text is not None and WORKFLOW_RUNNER_COMMAND not in workflow_text:
        failures.append((
            WORKFLOW.as_posix(),
            0,
            f'missing GNU++20 legacy guard bundle runner: {WORKFLOW_RUNNER_COMMAND}',
        ))

    runner_text, runner_failures = read_required_file(
        repo_root,
        RUNNER,
        'missing Python CI guard bundle runner',
    )
    failures.extend(runner_failures)
    if runner_text is not None:
        for snippet in REQUIRED_RUNNER_SNIPPETS:
            if snippet not in runner_text:
                failures.append((
                    RUNNER.as_posix(),
                    0,
                    f'Python CI guard bundle runner missing detail: {snippet}',
                ))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check GNU++20 legacy guard bundle wiring in CI')
    parser.add_argument('repo_root', nargs='?', default='.')
    args = parser.parse_args()

    failures = check_repo(args.repo_root)
    if failures:
        for path, line, message in failures:
            if line:
                print(f'::error file={path},line={line}::{message}')
            else:
                print(f'::error file={path}::{message}')
        raise SystemExit(1)

    print('GNU++20 legacy guard bundle validated')


if __name__ == '__main__':
    main()
