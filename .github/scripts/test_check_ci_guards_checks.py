#!/usr/bin/env python3
import tempfile
from pathlib import Path

import check_ci_guards_checks as checks
import check_ci_guards_helpers as helpers


def write_file(root, relative_path, text):
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')
    helpers.clear_runtime_caches()
    return path


def expect_guard_failure(callback, expected_message, expected_path=None):
    try:
        callback()
    except helpers.GuardFailure as exc:
        if expected_message not in exc.message:
            raise AssertionError(f'expected {expected_message!r} in {exc.message!r}')
        if expected_path is not None and Path(exc.path) != Path(expected_path):
            raise AssertionError(f'expected failure path {expected_path}, got {exc.path}')
        return exc
    raise AssertionError(f'expected GuardFailure containing {expected_message!r}')


def test_smoke_suite_function_lines():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        relative = Path('runtime_smoke_suite.sh')
        path = write_file(
            root,
            relative,
            '\n'.join((
                '#!/usr/bin/env bash',
                'other_suite() {',
                '  echo ignored',
                '}',
                'smoke_demo() {',
                '  # leading comment should be ignored',
                '  build/all/x265.exe \\',
                '    --input "smoke input.y4m" \\',
                '    --frames 2 \\',
                '    --output smoke.hevc # trailing comment should be ignored',
                '  grep -Fq "encoded ok" smoke.log',
                '}',
            )) + '\n',
        )

        active_lines = checks.smoke_suite_function_lines(root, relative, 'smoke_demo', 'missing smoke suite')
        expected = [
            'build/all/x265.exe --input "smoke input.y4m" --frames 2 --output smoke.hevc',
            'grep -Fq "encoded ok" smoke.log',
        ]
        if active_lines != expected:
            raise AssertionError(f'unexpected active lines: {active_lines!r}')

        expect_guard_failure(
            lambda: checks.smoke_suite_function_lines(root, relative, 'missing_demo', 'missing smoke suite'),
            'missing function missing_demo in runtime_smoke_suite.sh',
            path,
        )


def test_smoke_suite_active_lines_and_runtime_alias():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        relative = Path('runtime_smoke_suite.sh')
        write_file(
            root,
            relative,
            '\n'.join((
                '#!/usr/bin/env bash',
                'runtime_smoke() {',
                '  echo runtime \\',
                '    --flag',
                '  # comment',
                '}',
            )) + '\n',
        )

        active_lines = checks.smoke_suite_active_lines(root, relative, 'missing runtime suite')
        if active_lines != ['runtime_smoke() {', 'echo runtime --flag', '}']:
            raise AssertionError(f'unexpected smoke-suite active lines: {active_lines!r}')

        function_lines = checks.runtime_smoke_active_lines(root, relative, 'runtime_smoke')
        if function_lines != ['echo runtime --flag']:
            raise AssertionError(f'unexpected runtime alias lines: {function_lines!r}')


def test_require_active_command_matchers():
    active_lines = [
        'echo "unterminated',
        'python -c "print(1)"',
        'build/all/x265.exe --input smoke.y4m --frames 2',
        'build/all/x265.exe --input smoke.y4m --frames 2 --output smoke.hevc',
    ]
    path = Path('build.sh')

    checks.require_active_command_prefix(
        active_lines,
        ('build/all/x265.exe', '--input', 'smoke.y4m'),
        path,
        'missing x265 prefix',
    )
    checks.require_active_exact_command(
        active_lines,
        ('python', '-c', 'print(1)'),
        path,
        'missing python exact command',
    )

    expect_guard_failure(
        lambda: checks.require_active_command_prefix(
            active_lines,
            ('build/all/x265.exe', '--preset', 'slow'),
            path,
            'missing preset command',
        ),
        'missing preset command',
        path,
    )
    expect_guard_failure(
        lambda: checks.require_active_exact_command(
            active_lines,
            ('build/all/x265.exe', '--input', 'smoke.y4m'),
            path,
            'missing exact x265 command',
        ),
        'missing exact x265 command',
        path,
    )


def test_require_active_line_contains_and_action_step_run():
    path = Path('runtime_smoke_suite.sh')
    checks.require_active_line_contains(['echo success', 'test -s smoke.hevc'], 'test -s smoke.hevc', path, 'missing smoke file check')
    expect_guard_failure(
        lambda: checks.require_active_line_contains(['echo success'], 'test -s smoke.hevc', path, 'missing smoke file check'),
        'missing smoke file check',
        path,
    )

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        relative = Path('.github/actions/sample/action.yml')
        action_path = write_file(
            root,
            relative,
            '\n'.join((
                'name: Sample',
                'runs:',
                '  using: composite',
                '  steps:',
                '    - name: Prepare',
                '      shell: bash',
                '      run: |',
                '        echo ready',
                '        python tool.py --check',
            )) + '\n',
        )
        parsed = helpers.load_yaml(root, relative)
        run = checks.action_step_run(parsed, action_path, 'Prepare', ('python tool.py --check',))
        if 'python tool.py --check' not in run:
            raise AssertionError(f'unexpected action step run block: {run!r}')


def test_option_value():
    args = ['build/all/x265.exe', '--input', 'smoke.y4m', '--frames', '2', '--no-progress']
    build = Path('build.sh')

    checks.option_value(args, '--input', 'smoke.y4m', build, 'smoke command')
    checks.option_value(args, '--frames', '2', build, 'smoke command')
    checks.option_value(args, '--no-progress', None, build, 'smoke command')

    expect_guard_failure(
        lambda: checks.option_value(args, '--frames', '3', build, 'smoke command'),
        'smoke command --frames must be 3, got 2',
        build,
    )
    expect_guard_failure(
        lambda: checks.option_value(args, '--output', 'smoke.hevc', build, 'smoke command'),
        'missing smoke command value for --output',
        build,
    )
    expect_guard_failure(
        lambda: checks.option_value(args, '--repeat-headers', None, build, 'smoke command'),
        'missing smoke command flag --repeat-headers',
        build,
    )


def test_x265_command_helpers():
    active_lines = [
        'build/all/x265.exe --input "smoke input.y4m" --frames 2 --output smoke.hevc',
        'build/all/x265.exe --input other.y4m --frames 1 --output other.hevc',
    ]
    build = Path('runtime_smoke_suite.sh')

    args = checks.single_x265_args(active_lines, build, 'smoke suite', 'smoke.hevc')
    expected_args = [
        'build/all/x265.exe',
        '--input',
        'smoke input.y4m',
        '--frames',
        '2',
        '--output',
        'smoke.hevc',
    ]
    if args != expected_args:
        raise AssertionError(f'unexpected x265 args: {args!r}')

    returned_args = checks.require_x265_command(
        active_lines,
        build,
        'smoke suite',
        'smoke.hevc',
        'build/all/x265.exe',
        (('--input', 'smoke input.y4m'), ('--frames', '2')),
    )
    if returned_args != expected_args:
        raise AssertionError(f'unexpected validated args: {returned_args!r}')

    expect_guard_failure(
        lambda: checks.single_x265_args(active_lines, build, 'missing suite', 'absent.hevc'),
        'expected exactly one missing suite x265 command, found 0',
        build,
    )
    expect_guard_failure(
        lambda: checks.require_x265_command(
            active_lines,
            build,
            'smoke suite',
            'smoke.hevc',
            'x265.exe',
            (),
        ),
        'smoke suite must run x265.exe, got build/all/x265.exe',
        build,
    )


def test_piped_and_shell_if_command_args():
    active_lines = [
        'build/all/x265.exe --input smoke.y4m --frames 2 2>&1 | tee smoke.log',
    ]
    build = Path('runtime_smoke_suite.sh')

    command, args = checks.piped_x265_command(active_lines, build, 'piped smoke', 'smoke.log')
    if command != active_lines[0]:
        raise AssertionError(f'unexpected piped command: {command!r}')
    expected_args = ['build/all/x265.exe', '--input', 'smoke.y4m', '--frames', '2']
    if args != expected_args:
        raise AssertionError(f'unexpected piped args: {args!r}')

    if_args = checks.shell_if_command_args(
        'if build/all/x265.exe --input "smoke input.y4m" --frames 2; then echo ok; fi',
        build,
        'if smoke',
    )
    expected_if_args = ['build/all/x265.exe', '--input', 'smoke input.y4m', '--frames', '2']
    if if_args != expected_if_args:
        raise AssertionError(f'unexpected if command args: {if_args!r}')

    expect_guard_failure(
        lambda: checks.piped_x265_command(
            [
                'build/all/x265.exe --output smoke.log',
                'build/all/x265.exe --output smoke.log',
            ],
            build,
            'duplicate smoke',
            'smoke.log',
        ),
        'expected exactly one duplicate smoke x265 command, found 2',
        build,
    )
    expect_guard_failure(
        lambda: checks.shell_if_command_args(
            'if build/all/x265.exe --input "broken; then echo ok; fi',
            build,
            'broken if smoke',
        ),
        'could not parse broken if smoke command',
        build,
    )


def test_validate_required_workflow_steps():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        relative = Path('.github/workflows/build.yml')
        path = write_file(
            root,
            relative,
            '\n'.join((
                'name: Build',
                'on:',
                '  push:',
                'jobs:',
                '  build:',
                '    runs-on: ubuntu-latest',
                '    steps:',
                '      - name: Run Smoke',
                '        run: |',
                '          # comment',
                '          build/all/x265.exe \\',
                '            --input smoke.y4m \\',
                '            --output smoke.hevc',
                '          test -s smoke.hevc',
            )) + '\n',
        )

        parsed = checks.validate_required_workflow_steps(
            root,
            relative,
            'workflow smoke',
            [('build', 'Run Smoke', ('build/all/x265.exe --input smoke.y4m --output smoke.hevc', 'test -s smoke.hevc'))],
        )
        if parsed['jobs']['build']['steps'][0]['name'] != 'Run Smoke':
            raise AssertionError('workflow parser returned unexpected step data')

        expect_guard_failure(
            lambda: checks.validate_required_workflow_steps(
                root,
                relative,
                'workflow smoke',
                [('build', 'Run Smoke', ('grep -Fq success smoke.log',))],
            ),
            'missing required workflow smoke snippet: grep -Fq success smoke.log',
            path,
        )


def test_validate_required_action_steps():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        relative = Path('.github/actions/sample/action.yml')
        path = write_file(
            root,
            relative,
            '\n'.join((
                'name: Sample',
                'runs:',
                '  using: composite',
                '  steps:',
                '    - name: Prepare',
                '      shell: bash',
                '      run: |',
                '        echo ready',
                '        python tool.py --check',
            )) + '\n',
        )

        checks.validate_required_action_steps(
            root,
            relative,
            'action smoke',
            [('Prepare', ('echo ready', 'python tool.py --check'))],
        )

        expect_guard_failure(
            lambda: checks.validate_required_action_steps(
                root,
                relative,
                'action smoke',
                [('Prepare', ('python tool.py --missing',))],
            ),
            'missing required action smoke snippet: python tool.py --missing',
            path,
        )


def test_validate_mp4_smoke_step():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        suite = Path('.github/scripts/mp4_smoke_suite.sh')
        build = write_file(
            root,
            suite,
            '\n'.join((
                '#!/usr/bin/env bash',
                'smoke_mp4() {',
                '  make_y4m smoke_mp4.y4m 24 12 yuv420p',
                '  if build/all/x265.exe --input smoke_mp4.y4m --input-res 160x90 --fps 24 --frames 12 --output smoke_mp4.mp4 --aud; then',
                '    echo encoded',
                '  fi',
                '  grep -Fq "major_brand=isom" smoke_mp4.ffprobe',
                '  grep -Fq "codec_name=hevc" smoke_mp4.ffprobe',
                '}',
            )) + '\n',
        )

        checks.validate_mp4_smoke_step(
            build,
            root,
            suite,
            'MP4 smoke',
            'unused-step',
            'smoke_mp4',
            'unused-target',
            'smoke_mp4',
            'smoke_mp4.mp4',
            ('major_brand=isom', 'codec_name=hevc'),
            '24',
            '12',
            'yuv420p',
            ('--aud',),
            (
                ('--input', 'smoke_mp4.y4m'),
                ('--input-res', '160x90'),
                ('--fps', '24'),
                ('--frames', '12'),
                ('--output', 'smoke_mp4.mp4'),
            ),
            {
                'grep -Fq "major_brand=isom" smoke_mp4.ffprobe': 'missing MP4 ffprobe brand check',
                'grep -Fq "codec_name=hevc" smoke_mp4.ffprobe': 'missing MP4 ffprobe codec check',
            },
        )


def main():
    tests = [
        test_smoke_suite_function_lines,
        test_smoke_suite_active_lines_and_runtime_alias,
        test_require_active_command_matchers,
        test_require_active_line_contains_and_action_step_run,
        test_option_value,
        test_x265_command_helpers,
        test_piped_and_shell_if_command_args,
        test_validate_required_workflow_steps,
        test_validate_required_action_steps,
        test_validate_mp4_smoke_step,
    ]
    for test in tests:
        test()
    print('CI guard helper check tests passed')


if __name__ == '__main__':
    main()
