#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_cli_deprecated_parallel_log_args.py')


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


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/x265cli.cpp': '\n'.join((
                    'OPT("pme")',
                    '{',
                    '    x265_log_file(param, X265_LOG_ERROR, " pme feature is deprecated from release 4.1 \\n");',
                    '    return true;',
                    '}',
                    'OPT("pmode")',
                    '{',
                    '    x265_log_file(param, X265_LOG_ERROR, " pmode feature is deprecated from release 4.1 \\n");',
                    '    return true;',
                    '}',
                    'OPT("dolby-vision-rpu")',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/x265cli.cpp': '\n'.join((
                    'OPT("pme")',
                    '{',
                    '    return true;',
                    '}',
                    'OPT("pmode")',
                    '{',
                    '    x265_log_file(param, X265_LOG_ERROR, " pmode feature is deprecated from release 4.1 \\n");',
                    '    return true;',
                    '}',
                    'OPT("dolby-vision-rpu")',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'missing deprecated parallel log guardrail: x265_log_file(param, X265_LOG_ERROR, " pme feature is deprecated from release 4.1 \\n");')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/x265cli.cpp': '\n'.join((
                    'OPT("pme")',
                    '{',
                    '    x265_log_file(param, X265_LOG_ERROR, " pme feature is deprecated from release 4.1 \\n", optarg);',
                    '    return true;',
                    '}',
                    'OPT("pmode")',
                    '{',
                    '    x265_log_file(param, X265_LOG_ERROR, " pmode feature is deprecated from release 4.1 \\n", optarg);',
                    '    return true;',
                    '}',
                    'OPT("dolby-vision-rpu")',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden deprecated parallel log regression: x265_log_file(param, X265_LOG_ERROR, " pme feature is deprecated from release 4.1 \\n", optarg);')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/x265cli.cpp': '\n'.join((
                    'OPT("pme")',
                    '{',
                    '    return true;',
                    '    x265_log_file(param, X265_LOG_ERROR, " pme feature is deprecated from release 4.1 \\n");',
                    '}',
                    'OPT("pmode")',
                    '{',
                    '    x265_log_file(param, X265_LOG_ERROR, " pmode feature is deprecated from release 4.1 \\n");',
                    '    return true;',
                    '}',
                    'OPT("dolby-vision-rpu")',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'Deprecated pme/pmode handlers must emit their fixed deprecation messages inside the matching option blocks before returning')

    print('Deprecated parallel option logging tests passed')


if __name__ == '__main__':
    main()
