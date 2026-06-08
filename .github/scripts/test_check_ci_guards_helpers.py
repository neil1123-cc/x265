#!/usr/bin/env python3
import io
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

import check_ci_guards_helpers as helpers


def expect_guard_failure(callback, expected_message, expected_path=None, expected_line=None):
    try:
        callback()
    except helpers.GuardFailure as exc:
        if expected_message not in exc.message:
            raise AssertionError(exc.message)
        if expected_path is not None and Path(exc.path) != Path(expected_path):
            raise AssertionError(f'unexpected failure path: {exc.path!r}')
        if expected_line is not None and exc.line != expected_line:
            raise AssertionError(f'unexpected failure line: {exc.line!r}')
        return exc
    raise AssertionError(f'expected GuardFailure containing {expected_message!r}')


def expect_system_exit(callback, expected_message, expected_stdout):
    stdout = io.StringIO()
    try:
        with redirect_stdout(stdout):
            callback()
    except SystemExit as exc:
        if expected_message not in str(exc):
            raise AssertionError(f'unexpected SystemExit: {exc!r}')
    else:
        raise AssertionError('expected SystemExit')
    output = stdout.getvalue()
    if expected_stdout not in output:
        raise AssertionError(output)


def test_strip_shell_comment():
    assert helpers.strip_shell_comment('echo hello # trailing') == 'echo hello'
    assert helpers.strip_shell_comment("echo '# keep this' # remove this") == "echo '# keep this'"
    assert helpers.strip_shell_comment('echo "# keep this" # remove this') == 'echo "# keep this"'
    assert helpers.strip_shell_comment(r'printf "%s" "a\#b" # remove this') == r'printf "%s" "a\#b"'
    assert helpers.strip_shell_comment('   # full comment   ') == ''


def test_annotation_path_and_require_run_text():
    assert helpers.annotation_path(Path('dir\\workflow.yml')) == 'dir/workflow.yml'
    helpers.require_run_text('echo hello\npython tool.py', 'python tool.py', Path('workflow.yml'), 'shell guard')
    expect_guard_failure(
        lambda: helpers.require_run_text('echo hello', 'python tool.py', Path('workflow.yml'), 'shell guard'),
        'missing required shell guard snippet: python tool.py',
        Path('workflow.yml'),
    )


def test_shell_active_lines_and_logical_lines():
    script = '\n'.join((
        '',
        '  # comment-only line',
        'echo alpha # trailing comment',
        'echo beta \\',
        '  --flag',
        "printf '# not a comment' # actual comment",
        '',
    ))
    assert helpers.shell_active_lines(script) == [
        'echo alpha',
        'echo beta \\',
        '--flag',
        "printf '# not a comment'",
    ]
    assert helpers.shell_active_logical_lines(script) == [
        'echo alpha',
        'echo beta --flag',
        "printf '# not a comment'",
    ]


def test_block_scalar_and_collect_run_blocks():
    lines = [
        '      run: |',
        '        echo first',
        '          echo second',
        '      uses: actions/checkout@v4',
    ]
    script, next_index = helpers.block_scalar(lines, 0, 6)
    assert script == 'echo first\n  echo second'
    assert next_index == 3

    helpers.clear_runtime_caches()
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'workflow.yml'
        path.write_text(
            '\n'.join((
                'jobs:',
                '  build:',
                '    steps:',
                '      - name: Inline',
                '        run: echo inline',
                '      - name: Block',
                '        run: |',
                '          echo from block',
                '          echo ${{ matrix.os }}',
                '      - name: Folded',
                '        run: >',
                '          printf "folded"',
                '          && echo done',
            )) + '\n',
            encoding='utf-8',
        )
        blocks = helpers.collect_run_blocks(path)
    assert blocks == [
        (path, 5, 'echo inline'),
        (path, 7, 'echo from block\necho ${{ matrix.os }}'),
        (path, 11, 'printf "folded"\n&& echo done'),
    ]


def test_require_active_run_text_and_sanitize_github_expressions():
    script = '\n'.join((
        'echo prefix \\',
        '  --flag',
        '# echo missing-token',
        'echo ${{ matrix.os }} ${{ github.ref_name }}',
    ))
    helpers.require_active_run_text(script, 'echo prefix --flag', Path('workflow.yml'), 'shell guard')
    expect_guard_failure(
        lambda: helpers.require_active_run_text(script, 'missing-token', Path('workflow.yml'), 'shell guard'),
        'missing required shell guard snippet: missing-token',
        Path('workflow.yml'),
    )
    sanitized = helpers.sanitize_github_expressions(script)
    assert '${{' not in sanitized
    assert sanitized.count('github_expr') == 2


def test_named_step_and_required_run():
    steps = [
        {'name': 'Checkout', 'uses': 'actions/checkout@v4'},
        {'name': 'Build', 'run': 'cmake --build .'},
        {'name': 'Fallback', 'run': 'python script.py --token value'},
    ]
    assert helpers.named_step(steps, 'Build', Path('workflow.yml')) is steps[1]
    assert helpers.named_step(
        steps,
        'Missing Name',
        Path('workflow.yml'),
        required_items=('python script.py',),
        job_name='build',
    ) is steps[2]
    expect_guard_failure(
        lambda: helpers.named_step(steps, 'Publish', Path('workflow.yml'), job_name='release'),
        'missing job release step: Publish',
        Path('workflow.yml'),
    )

    assert helpers.required_run(steps[1], Path('workflow.yml'), 'Build') == 'cmake --build .'
    expect_guard_failure(
        lambda: helpers.required_run({'name': 'Empty', 'run': '   '}, Path('workflow.yml'), 'Empty'),
        'step Empty is missing a run block',
        Path('workflow.yml'),
    )


def test_report_failure():
    expect_system_exit(
        lambda: helpers.report_failure(helpers.GuardFailure('broken run block', Path('dir\\workflow.yml'), 7)),
        'broken run block: dir/workflow.yml',
        '::error file=dir/workflow.yml,line=7::broken run block',
    )
    expect_system_exit(
        lambda: helpers.report_failure(helpers.GuardFailure('plain failure')),
        'plain failure',
        '::error::plain failure',
    )


def test_yaml_helpers_and_private_caches():
    helpers.clear_runtime_caches()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        workflow = root / '.github' / 'workflows' / 'build.yml'
        workflow.parent.mkdir(parents=True, exist_ok=True)
        workflow.write_text(
            '\n'.join((
                'name: Build',
                'on:',
                '  push:',
                'jobs:',
                '  build:',
                '    steps:',
                '      - name: Smoke',
                '        run: echo ok',
            )) + '\n',
            encoding='utf-8',
        )
        action = root / '.github' / 'actions' / 'sample' / 'action.yml'
        action.parent.mkdir(parents=True, exist_ok=True)
        action.write_text(
            '\n'.join((
                'name: Sample',
                'runs:',
                '  using: composite',
                '  steps:',
                '    - name: Prepare',
                '      run: echo ready',
            )) + '\n',
            encoding='utf-8',
        )

        helpers.validate_yaml_structure({'jobs': {}}, workflow, root / '.github' / 'workflows')
        helpers.validate_yaml_structure({'runs': {}}, action, root / '.github' / 'workflows')
        expect_guard_failure(
            lambda: helpers.validate_yaml_structure([], workflow, root / '.github' / 'workflows'),
            'YAML file did not parse to a mapping',
            workflow,
        )

        yaml_paths = helpers.yaml_files(root, Path('.github/workflows'), Path('.github/actions'))
        if yaml_paths != [workflow, action]:
            raise AssertionError(f'unexpected yaml file list: {yaml_paths!r}')

        loaded = helpers._load_yaml_cached(str(workflow.resolve()))
        jobs = helpers.workflow_jobs(loaded, workflow)
        if sorted(jobs) != ['build']:
            raise AssertionError(f'unexpected workflow jobs: {jobs!r}')
        if helpers._read_text_cached(str(workflow.resolve())) != workflow.read_text(encoding='utf-8'):
            raise AssertionError('cached text loader returned unexpected content')
        cached_blocks = helpers._collect_run_blocks_cached(str(workflow.resolve()))
        if cached_blocks != ((workflow, 8, 'echo ok'),):
            raise AssertionError(f'unexpected cached run blocks: {cached_blocks!r}')

        helpers.validate_yaml_text(root, Path('.github/workflows'), Path('.github/actions'))

        workflow.write_text('jobs:\n\tbuild:\n', encoding='utf-8')
        helpers.clear_runtime_caches()
        expect_guard_failure(
            lambda: helpers.validate_yaml_text(root, Path('.github/workflows'), Path('.github/actions')),
            'YAML indentation must not contain tab characters',
            workflow,
            2,
        )
    helpers.clear_runtime_caches()


def test_validate_run_blocks_and_script_validators():
    bash = helpers.bash_path(None)
    helpers.clear_runtime_caches()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        workflow = root / '.github' / 'workflows' / 'build.yml'
        workflow.parent.mkdir(parents=True, exist_ok=True)
        workflow.write_text(
            '\n'.join((
                'name: Build',
                'on:',
                '  push:',
                'jobs:',
                '  build:',
                '    steps:',
                '      - name: Smoke',
                '        run: |',
                '          echo workflow',
                '          echo "${{ matrix.os }}"',
            )) + '\n',
            encoding='utf-8',
        )
        action = root / '.github' / 'actions' / 'sample' / 'action.yml'
        action.parent.mkdir(parents=True, exist_ok=True)
        action.write_text(
            '\n'.join((
                'name: Sample',
                'runs:',
                '  using: composite',
                '  steps:',
                '    - name: Prepare',
                '      shell: bash',
                '      run: echo action',
            )) + '\n',
            encoding='utf-8',
        )

        helpers.validate_run_blocks(root, Path('.github/workflows'), Path('.github/actions'), bash)

        bash_script = root / '.github' / 'scripts' / 'sample.sh'
        bash_script.parent.mkdir(parents=True, exist_ok=True)
        bash_script.write_text('#!/usr/bin/env bash\necho token-one token-two\n', encoding='utf-8')
        helpers.bash_check(bash, bash_script, bash_script, 1)
        helpers.validate_bash_file(
            root,
            bash,
            Path('.github/scripts/sample.sh'),
            'missing sample bash script',
            required_text=('token-one',),
            required_tokens=('token-two',),
            required_message='missing bash detail',
        )

        python_script = root / '.github' / 'scripts' / 'sample.py'
        python_script.write_text('print("hello helper test")\n', encoding='utf-8')
        helpers.validate_python_file(
            root,
            Path('.github/scripts/sample.py'),
            'missing sample python script',
            required_text=('hello helper test',),
            required_message='missing python detail',
        )
    helpers.clear_runtime_caches()


def test_run_guard_python_in_process():
    old_argv = list(sys.argv)
    old_cwd = Path.cwd()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        script = root / '.github' / 'scripts' / 'sample_guard.py'
        script.parent.mkdir(parents=True, exist_ok=True)
        script.write_text(
            '\n'.join((
                'import sys',
                'from pathlib import Path',
                'print("argv=" + "|".join(sys.argv[1:]))',
                'print("cwd=" + Path.cwd().name)',
            )) + '\n',
            encoding='utf-8',
        )

        stdout = io.StringIO()
        with redirect_stdout(stdout):
            helpers.run_guard(root, sys.executable, '.github/scripts/sample_guard.py', 'alpha')
        output = stdout.getvalue()
        if 'argv=alpha' not in output or f'cwd={root.name}' not in output:
            raise AssertionError(output)

        failing_script = root / '.github' / 'scripts' / 'failing_guard.py'
        failing_script.write_text('raise RuntimeError("in-process boom")\n', encoding='utf-8')
        try:
            helpers.run_guard(root, sys.executable, str(failing_script))
        except SystemExit as exc:
            failure_output = str(exc)
        else:
            raise AssertionError('expected failing in-process guard to raise SystemExit')
        if 'RuntimeError: in-process boom' not in failure_output:
            raise AssertionError(failure_output)

    if sys.argv != old_argv:
        raise AssertionError('run_guard did not restore sys.argv')
    if Path.cwd() != old_cwd:
        raise AssertionError('run_guard did not restore cwd')


def main():
    test_annotation_path_and_require_run_text()
    test_strip_shell_comment()
    test_shell_active_lines_and_logical_lines()
    test_block_scalar_and_collect_run_blocks()
    test_require_active_run_text_and_sanitize_github_expressions()
    test_named_step_and_required_run()
    test_report_failure()
    test_yaml_helpers_and_private_caches()
    test_validate_run_blocks_and_script_validators()
    test_run_guard_python_in_process()
    print('check_ci_guards_helpers tests passed')


if __name__ == '__main__':
    main()
