#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_analysis_data_api_null_guards.py')

# Normalized checker probes used by the coverage scan for dynamic analysis API null-guard labels.
NORMALIZED_PROBES = (
    'missing  function',
    ' must guard null param/analysis before dereferencing analysis state',
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
        'void x265_alloc_analysis_data(x265_param *param, x265_analysis_data* analysis)',
        '{',
        '    if (!param || !analysis)',
        '    {',
        '        x265_log(nullptr, X265_LOG_ERROR, "x265_alloc_analysis_data requires non-null param and analysis data\\n");',
        '        return;',
        '    }',
        '    x265_analysis_inter_data *interData = analysis->interData = nullptr;',
        '}',
        'void x265_free_analysis_data(x265_param *param, x265_analysis_data* analysis)',
        '{',
        '    if (!param || !analysis)',
        '    {',
        '        x265_log(nullptr, X265_LOG_ERROR, "x265_free_analysis_data requires non-null param and analysis data\\n");',
        '        return;',
        '    }',
        '    int maxReuseLevel = X265_MAX(param->analysisSaveReuseLevel, param->analysisLoadReuseLevel);',
        '}',
    )) + '\n'


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/encoder/api.cpp': valid_text()})
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/api.cpp': valid_text().replace(
                    '    if (!param || !analysis)\n'
                    '    {\n'
                    '        x265_log(nullptr, X265_LOG_ERROR, "x265_alloc_analysis_data requires non-null param and analysis data\\n");\n'
                    '        return;\n'
                    '    }\n',
                    '',
                    1,
                ),
            },
        )
        expect_fail(run_checker(root), 'missing x265_alloc_analysis_data null guardrail: if (!param || !analysis)')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/api.cpp': valid_text().replace(
                    '    if (!param || !analysis)\n'
                    '    {\n'
                    '        x265_log(nullptr, X265_LOG_ERROR, "x265_free_analysis_data requires non-null param and analysis data\\n");\n'
                    '        return;\n'
                    '    }\n',
                    '',
                    1,
                ),
            },
        )
        expect_fail(run_checker(root), 'missing x265_free_analysis_data null guardrail: if (!param || !analysis)')

    print('x265 analysis data API null guard tests passed')


if __name__ == '__main__':
    main()
