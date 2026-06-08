#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_vmaf_api_null_guards.py')

# Normalized checker probes used by the coverage scan for label-formatted failures.
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
        'void x265_vmaf_encoder_log(x265_encoder* enc, int argc, char **argv, x265_param *param, x265_vmaf_data *vmafdata)',
        '{',
        '    if (!enc || !param || !vmafdata)',
        '    {',
        '        x265_log(nullptr, X265_LOG_ERROR, "x265_vmaf_encoder_log requires non-null encoder, param, and VMAF data\\n");',
        '        return;',
        '    }',
        '    Encoder *encoder = static_cast<Encoder*>(enc);',
        '}',
        'double x265_calculate_vmafscore(x265_param *param, x265_vmaf_data *data)',
        '{',
        '    if (!param || !data)',
        '    {',
        '        x265_log(nullptr, X265_LOG_ERROR, "x265_calculate_vmafscore requires non-null param and VMAF data\\n");',
        '        return 0.0;',
        '    }',
        '    if (!data->reference_file || !data->distorted_file)',
        '    {',
        '        x265_log(nullptr, X265_LOG_ERROR, "x265_calculate_vmafscore requires non-null VMAF input files\\n");',
        '        return 0.0;',
        '    }',
        '    data->width = param->sourceWidth;',
        '}',
        'double x265_calculate_vmaf_framelevelscore(x265_param *param, x265_vmaf_framedata *vmafframedata)',
        '{',
        '    if (!param || !vmafframedata)',
        '    {',
        '        x265_log(nullptr, X265_LOG_ERROR, "x265_calculate_vmaf_framelevelscore requires non-null param and frame data\\n");',
        '        return 0.0;',
        '    }',
        '    if (!vmafframedata->reference_frame || !vmafframedata->distorted_frame)',
        '    {',
        '        x265_log(nullptr, X265_LOG_ERROR, "x265_calculate_vmaf_framelevelscore requires non-null reference and distorted frames\\n");',
        '        return 0.0;',
        '    }',
        '    if (param->internalCsp == X265_CSP_I420)',
        '        return 0.0;',
        '}',
    )) + '\n'


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/encoder/api.cpp': ''})
        expect_fail(run_checker(root), 'missing x265_vmaf_encoder_log function')

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
                    '    if (!enc || !param || !vmafdata)\n'
                    '    {\n'
                    '        x265_log(nullptr, X265_LOG_ERROR, "x265_vmaf_encoder_log requires non-null encoder, param, and VMAF data\\n");\n'
                    '        return;\n'
                    '    }\n',
                    '',
                    1,
                ),
            },
        )
        expect_fail(run_checker(root), 'missing x265_vmaf_encoder_log null guardrail: if (!enc || !param || !vmafdata)')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/api.cpp': valid_text().replace(
                    '    if (!data->reference_file || !data->distorted_file)\n',
                    '    if (data->reference_file)\n',
                    1,
                ),
            },
        )
        expect_fail(run_checker(root), 'missing x265_calculate_vmafscore null guardrail: if (!data->reference_file || !data->distorted_file)')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/api.cpp': valid_text().replace(
                    '    if (!vmafframedata->reference_frame || !vmafframedata->distorted_frame)\n',
                    '    if (vmafframedata->reference_frame)\n',
                    1,
                ),
            },
        )
        expect_fail(run_checker(root), 'missing x265_calculate_vmaf_framelevelscore null guardrail: if (!vmafframedata->reference_frame || !vmafframedata->distorted_frame)')

    print('VMAF API null guard tests passed')


if __name__ == '__main__':
    main()
