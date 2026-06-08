#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_gnu20_legacy_guard_bundle.py')

# Coverage probes used by the scan for GNU++20 legacy-guard bundle checks.
NORMALIZED_PROBES = (
    'missing GNU++20 legacy guard bundle runner: ',
    'Python CI guard bundle runner missing detail: ',
)


def write_targets(root, contents):
    for relative, text in contents.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)


def run_checker(repo_root):
    return subprocess.run(
        [sys.executable, str(CHECKER), str(repo_root)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def expect_pass(result):
    if result.returncode != 0:
        raise AssertionError(result.stdout)


def expect_fail(result, expected):
    if result.returncode == 0:
        raise AssertionError(f'expected failure containing {expected!r}')
    if expected not in result.stdout:
        raise AssertionError(result.stdout)


def workflow_text(command='python .github/scripts/run_python_ci_guard_bundle.py'):
    return f'''\
jobs:
  validate-deps-cache-suffix:
    steps:
      - name: Run Python CI guard bundle
        shell: bash
        run: |
          set -euo pipefail
          {command}
'''


def runner_text(**overrides):
    check_command = overrides.get(
        'check_command',
        "CHECK_CI_GUARDS_COMMAND = ('python', '.github/scripts/check_ci_guards.py')",
    )
    excluded_tests = overrides.get(
        'excluded_tests',
        "NON_EXECUTED_TESTS = {'test_check_ci_guards_fixture.py'}",
    )
    glob_expr = overrides.get('glob_expr', "script_dir.glob('test_check_*.py')")
    filter_expr = overrides.get('filter_expr', 'if path.name not in NON_EXECUTED_TESTS')
    jobs_arg = overrides.get(
        'jobs_arg',
        "parser.add_argument('--jobs', type=int, default=default_jobs())",
    )
    parallel_call = overrides.get(
        'parallel_call',
        'run_commands_parallel(repo_root, commands, jobs)',
    )
    return f'''\
#!/usr/bin/env python3
from pathlib import Path

{check_command}
{excluded_tests}


def run_command(repo_root, command):
    pass


def default_jobs():
    return 2


def run_commands_parallel(repo_root, commands, jobs):
    pass


def guard_test_scripts(repo_root):
    script_dir = repo_root / '.github' / 'scripts'
    return tuple(
        sorted(
            path
            for path in {glob_expr}
            {filter_expr}
        )
    )


def main():
    repo_root = Path.cwd()
    parser = argparse.ArgumentParser()
    {jobs_arg}
    jobs = 2
    run_command(repo_root, CHECK_CI_GUARDS_COMMAND)
    commands = []
    for test_script in guard_test_scripts(repo_root):
        commands.append(('python', test_script.relative_to(repo_root).as_posix()))
    {parallel_call}
'''


def repo_files(workflow=None, runner=None):
    return {
        '.github/workflows/build.yml': workflow if workflow is not None else workflow_text(),
        '.github/scripts/run_python_ci_guard_bundle.py': runner if runner is not None else runner_text(),
    }


def run_case(files, expected=None):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, files)
        result = run_checker(root)
        if expected is None:
            expect_pass(result)
        else:
            expect_fail(result, expected)


def main():
    run_case(repo_files())
    run_case(
        repo_files(workflow=workflow_text('python .github/scripts/check_ci_guards.py')),
        'missing GNU++20 legacy guard bundle runner',
    )
    run_case(
        {'.github/workflows/build.yml': workflow_text()},
        'missing Python CI guard bundle runner',
    )
    run_case(
        repo_files(runner=runner_text(
            check_command="CHECK_CI_GUARDS_COMMAND = ('python', '.github/scripts/check_ci_guards.py', '--only', 'required-snippets')",
        )),
        "Python CI guard bundle runner missing detail: CHECK_CI_GUARDS_COMMAND = ('python', '.github/scripts/check_ci_guards.py')",
    )
    run_case(
        repo_files(runner=runner_text(
            excluded_tests="NON_EXECUTED_TESTS = {'test_check_ci_guards_fixture.py', 'test_check_gnu20_legacy_guard_bundle.py'}",
        )),
        "Python CI guard bundle runner missing detail: NON_EXECUTED_TESTS = {'test_check_ci_guards_fixture.py'}",
    )
    run_case(
        repo_files(runner=runner_text(glob_expr="script_dir.glob('test_check_ci_guards.py')")),
        "Python CI guard bundle runner missing detail: script_dir.glob('test_check_*.py')",
    )
    run_case(
        repo_files(runner=runner_text(
            parallel_call="run_command(repo_root, commands[0])",
        )),
        'Python CI guard bundle runner missing detail:     run_commands_parallel(repo_root, commands, jobs)',
    )
    run_case(
        repo_files(runner=runner_text(
            jobs_arg="parser.add_argument('--verbose', action='store_true')",
        )),
        "Python CI guard bundle runner missing detail: parser.add_argument('--jobs', type=int, default=default_jobs())",
    )

    print('GNU++20 legacy guard bundle tests passed')


if __name__ == '__main__':
    main()
