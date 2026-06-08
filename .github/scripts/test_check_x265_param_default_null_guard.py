#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_x265_param_default_null_guard.py')


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
        'void x265_param_default(x265_param* param)',
        '{',
        '    if (!param)',
        '    {',
        '        x265_log(nullptr, X265_LOG_ERROR, "x265_param_default requires a non-null parameter struct\\n");',
        '        return;',
        '    }',
        '#ifdef SVT_HEVC',
        '    EB_H265_ENC_CONFIGURATION* svtParam = getSvtHevcParamStorage(param);',
        '#endif',
        '    std::fill_n(reinterpret_cast<uint8_t*>(param), sizeof(x265_param), uint8_t(0));',
        '}',
    )) + '\n'


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/common/param.cpp': ''})
        expect_fail(run_checker(root), 'missing x265_param_default declaration')

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
                    '        x265_log(nullptr, X265_LOG_ERROR, "x265_param_default requires a non-null parameter struct\\n");\n'
                    '        return;\n'
                    '    }\n',
                    '',
                    1,
                ),
            },
        )
        expect_fail(run_checker(root), 'missing x265_param_default null guardrail: if (!param)')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': valid_text().replace(
                    '        x265_log(nullptr, X265_LOG_ERROR, "x265_param_default requires a non-null parameter struct\\n");\n',
                    '        x265_log(nullptr, X265_LOG_ERROR, "bad param default\\n");\n',
                    1,
                ),
            },
        )
        expect_fail(run_checker(root), 'missing x265_param_default null guardrail: x265_log(nullptr, X265_LOG_ERROR, "x265_param_default requires a non-null parameter struct\\n");')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': '\n'.join((
                    'void x265_param_default(x265_param* param)',
                    '{',
                    '#ifdef SVT_HEVC',
                    '    EB_H265_ENC_CONFIGURATION* svtParam = getSvtHevcParamStorage(param);',
                    '#endif',
                    '    if (!param)',
                    '    {',
                    '        x265_log(nullptr, X265_LOG_ERROR, "x265_param_default requires a non-null parameter struct\\n");',
                    '        return;',
                    '    }',
                    '    std::fill_n(reinterpret_cast<uint8_t*>(param), sizeof(x265_param), uint8_t(0));',
                    '}',
                    'int x265_param_default_preset(x265_param* param, const char* preset, const char* tune)',
                    '{',
                    '    return 0;',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'x265_param_default must guard null param before SVT state lookup or parameter clearing')

    print('x265_param_default null guard tests passed')


if __name__ == '__main__':
    main()
