#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_x265_param_parse_null_guard.py')


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


def valid_text():
    return '\n'.join((
        'int x265_param_parse(x265_param* p, const char* name, const char* value)',
        '{',
        '    if (!name)',
        '        return X265_PARAM_BAD_NAME;',
        '    if (!p)',
        '        return X265_PARAM_BAD_VALUE;',
        '    if (p->bEnableSvtHevc)',
        '    {',
        '    }',
        '    p->cpuid = X265_NS::cpu_detect(true);',
        '}',
    )) + '\n'


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/common/param.cpp': valid_text()})
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': valid_text().replace(
                    '    if (!p)\n        return X265_PARAM_BAD_VALUE;\n',
                    '',
                    1,
                ),
            },
        )
        expect_fail(run_checker(root), 'missing x265_param_parse null guardrail: if (!p)\n        return X265_PARAM_BAD_VALUE;')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': valid_text().replace(
                    '    if (!name)\n        return X265_PARAM_BAD_NAME;\n    if (!p)\n        return X265_PARAM_BAD_VALUE;\n',
                    '    if (!p)\n        return X265_PARAM_BAD_VALUE;\n    if (!name)\n        return X265_PARAM_BAD_NAME;\n',
                    1,
                ),
            },
        )
        expect_fail(run_checker(root), 'x265_param_parse must reject null p after validating name and before dereferencing parser state')

    print('x265_param_parse null guard tests passed')


if __name__ == '__main__':
    main()
