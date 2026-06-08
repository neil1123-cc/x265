#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_param_api_null_guards.py')

# Normalized checker probes used by the coverage scan for dynamic null-guard labels.
NORMALIZED_PROBES = (
    'missing  function',
    'missing  null guardrail: ',
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


def valid_text():
    return '\n'.join((
        'int x265_check_params(x265_param* param)',
        '{',
        '    if (!param)',
        '    {',
        '        x265_log(nullptr, X265_LOG_ERROR, "x265_check_params requires a non-null parameter struct\\n");',
        '        return X265_PARAM_BAD_VALUE;',
        '    }',
        '#define CHECK(expr, msg) check_failed |= _confirm(param, expr, msg)',
        '}',
        'void x265_param_apply_fastfirstpass(x265_param* param)',
        '{',
        '    if (!param)',
        '    {',
        '        x265_log(nullptr, X265_LOG_ERROR, "x265_param_apply_fastfirstpass requires a non-null parameter struct\\n");',
        '        return;',
        '    }',
        '    if (param->rc.bStatWrite && !param->rc.bStatRead)',
        '    {',
        '    }',
        '}',
        'void x265_print_params(x265_param* param)',
        '{',
        '    if (!param)',
        '    {',
        '        x265_log(nullptr, X265_LOG_ERROR, "x265_print_params requires a non-null parameter struct\\n");',
        '        return;',
        '    }',
        '    if (param->logLevel < X265_LOG_INFO)',
        '        return;',
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
                    '    if (!param)\n'
                    '    {\n'
                    '        x265_log(nullptr, X265_LOG_ERROR, "x265_check_params requires a non-null parameter struct\\n");\n'
                    '        return X265_PARAM_BAD_VALUE;\n'
                    '    }\n',
                    '',
                    1,
                ),
            },
        )
        expect_fail(run_checker(root), 'missing x265_check_params null guardrail: if (!param)')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': valid_text().replace(
                    '    if (!param)\n'
                    '    {\n'
                    '        x265_log(nullptr, X265_LOG_ERROR, "x265_param_apply_fastfirstpass requires a non-null parameter struct\\n");\n'
                    '        return;\n'
                    '    }\n'
                    '    if (param->rc.bStatWrite && !param->rc.bStatRead)\n',
                    '    if (param->rc.bStatWrite && !param->rc.bStatRead)\n'
                    '    if (!param)\n'
                    '    {\n'
                    '        x265_log(nullptr, X265_LOG_ERROR, "x265_param_apply_fastfirstpass requires a non-null parameter struct\\n");\n'
                    '        return;\n'
                    '    }\n',
                    1,
                ),
            },
        )
        expect_fail(run_checker(root), 'x265_param_apply_fastfirstpass must reject null param before touching rate-control fields')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': valid_text().replace(
                    '        x265_log(nullptr, X265_LOG_ERROR, "x265_print_params requires a non-null parameter struct\\n");\n',
                    '        x265_log(nullptr, X265_LOG_ERROR, "bad print params\\n");\n',
                    1,
                ),
            },
        )
        expect_fail(run_checker(root), 'missing x265_print_params null guardrail: x265_log(nullptr, X265_LOG_ERROR, "x265_print_params requires a non-null parameter struct\\n");')

    print('Public param API null guard tests passed')


if __name__ == '__main__':
    main()
