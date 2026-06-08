#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_zonefile_parse_no_exit.py')


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


PASS_SOURCE = '\n'.join((
    'if (cliopt.parseZoneParam(argCount, args, &stagedParam, i))',
    '{',
    '    x265_zone_free(&stagedParam);',
    '    cliopt.destroy();',
    '    return false;',
    '}',
)) + '\n'


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/x265cli.cpp': PASS_SOURCE})
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/x265cli.cpp': '\n'.join((
                    'if (cliopt.parseZoneParam(argCount, args, &stagedParam, i))',
                    '{',
                    '    x265_zone_free(&stagedParam);',
                    '    cliopt.destroy();',
                    '    if (cliopt.api)',
                    '        cliopt.api->param_free(cliopt.param);',
                    '    return false;',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden zonefile no-exit regression: parseZoneFile must not terminate the process on zone parse failure')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/x265cli.cpp': '\n'.join((
                    'if (cliopt.parseZoneParam(argCount, args, &stagedParam, i))',
                    '{',
                    '    x265_zone_free(&stagedParam);',
                    '    cliopt.destroy();',
                    '    if (cliopt.api)',
                    '        cliopt.api->param_free(cliopt.param);',
                    '    std::exit(1);',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'missing zonefile no-exit guardrail: return false;')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/x265cli.cpp': PASS_SOURCE.replace(
                    '    x265_zone_free(&stagedParam);\n'
                    '    cliopt.destroy();\n'
                    '    return false;\n',
                    '    return false;\n'
                    '    x265_zone_free(&stagedParam);\n'
                    '    cliopt.destroy();\n',
                    1,
                ),
            },
        )
        expect_fail(run_checker(root), 'parseZoneFile must clean up and return false on zone parse failure')

    print('Zonefile no-exit guard tests passed')


if __name__ == '__main__':
    main()
