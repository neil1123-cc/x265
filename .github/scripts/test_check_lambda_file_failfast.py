#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_lambda_file_failfast.py')

# Coverage probes used by the scan for lambda-file fail-fast guardrails.
NORMALIZED_PROBES = (
    'parseLambdaFile must fail fast on invalid lambda tokens',
    'forbidden lambda fail-fast regression: ...',
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


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': '\n'.join((
                    'value = x265_atof(tok, bValueError);',
                    'if (!bValueError)',
                    '    break;',
                    'x265_log(param, X265_LOG_ERROR, "invalid lambda value: %s\\n", tok);',
                    'bool closeFailed = ferror(lfn) != 0;',
                    'if (fclose(lfn))',
                    '    closeFailed = true;',
                    '    x265_log(param, X265_LOG_WARNING, "unable to close lambda file after invalid value\\n");',
                    'return true;',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': '\n'.join((
                    'if (tok)',
                    '{',
                    '    bool bValueError = false;',
                    '    value = x265_atof(tok, bValueError);',
                    '    if (!bValueError)',
                    '        break;',
                    '}',
                    'while (1);',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'missing lambda fail-fast guardrail: x265_log(param, X265_LOG_ERROR, "invalid lambda value: %s\\n", tok);')

    print('Lambda-file fail-fast tests passed')


if __name__ == '__main__':
    main()
