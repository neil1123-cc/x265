#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_x265_param_default_preset_null_guard.py')


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
        'int x265_param_default_preset(x265_param* param, const char* preset, const char* tune)',
        '{',
        '    if (!param)',
        '    {',
        '        x265_log(nullptr, X265_LOG_ERROR, "x265_param_default_preset requires a non-null parameter struct\\n");',
        '        return -1;',
        '    }',
        '#if EXPORT_C_API',
        '    ::x265_param_default(param);',
        '#else',
        '    X265_NS::x265_param_default(param);',
        '#endif',
        '}',
        '#undef atoi',
    )) + '\n'


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/common/param.cpp': ''})
        expect_fail(run_checker(root), 'missing x265_param_default_preset declaration')

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
                    '        x265_log(nullptr, X265_LOG_ERROR, "x265_param_default_preset requires a non-null parameter struct\\n");\n'
                    '        return -1;\n'
                    '    }\n',
                    '',
                    1,
                ),
            },
        )
        expect_fail(run_checker(root), 'missing x265_param_default_preset null guardrail: if (!param)')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': valid_text().replace(
                    '        x265_log(nullptr, X265_LOG_ERROR, "x265_param_default_preset requires a non-null parameter struct\\n");\n',
                    '        x265_log(nullptr, X265_LOG_ERROR, "bad preset default\\n");\n',
                    1,
                ),
            },
        )
        expect_fail(run_checker(root), 'missing x265_param_default_preset null guardrail: x265_log(nullptr, X265_LOG_ERROR, "x265_param_default_preset requires a non-null parameter struct\\n");')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': '\n'.join((
                    'int x265_param_default_preset(x265_param* param, const char* preset, const char* tune)',
                    '{',
                    '#if EXPORT_C_API',
                    '    ::x265_param_default(param);',
                    '#else',
                    '    X265_NS::x265_param_default(param);',
                    '#endif',
                    '    if (!param)',
                    '    {',
                    '        x265_log(nullptr, X265_LOG_ERROR, "x265_param_default_preset requires a non-null parameter struct\\n");',
                    '        return -1;',
                    '    }',
                    '}',
                    '#undef atoi',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'x265_param_default_preset must guard null param before default initialization')

    print('x265_param_default_preset null guard tests passed')


if __name__ == '__main__':
    main()
