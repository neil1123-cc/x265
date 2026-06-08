#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_vmaf_encoder_log_close_state.py')


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
                'source/encoder/api.cpp': '\n'.join((
                    'stats.aggregateVmafScore = x265_calculate_vmafscore(param, vmafdata);',
                    'if(vmafdata->reference_file)',
                    'bool closeFailed = ferror(vmafdata->reference_file) != 0;',
                    'if (fclose(vmafdata->reference_file))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '    x265_log(param, X265_LOG_WARNING, "Unable to close VMAF reference file after score calculation\\n");',
                    'if(vmafdata->distorted_file)',
                    'bool closeFailed = ferror(vmafdata->distorted_file) != 0;',
                    'if (fclose(vmafdata->distorted_file))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '    x265_log(param, X265_LOG_WARNING, "Unable to close VMAF distorted file after score calculation\\n");',
                    'x265_free(vmafdata);',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/encoder/api.cpp': 'fclose(vmafdata->reference_file);\n'})
        expect_fail(run_checker(root), 'missing VMAF encoder-log close guardrail: stats.aggregateVmafScore = x265_calculate_vmafscore(param, vmafdata);')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/api.cpp': '\n'.join((
                    'stats.aggregateVmafScore = x265_calculate_vmafscore(param, vmafdata);',
                    'if(vmafdata->reference_file)',
                    'bool closeFailed = ferror(vmafdata->reference_file) != 0;',
                    'if (fclose(vmafdata->reference_file))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '    x265_log(param, X265_LOG_WARNING, "Unable to close VMAF reference file after score calculation\\n");',
                    'if(vmafdata->distorted_file)',
                    'bool closeFailed = ferror(vmafdata->distorted_file) != 0;',
                    'if (fclose(vmafdata->distorted_file))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '    x265_log(param, X265_LOG_WARNING, "Unable to close VMAF distorted file after score calculation\\n");',
                    'x265_free(vmafdata);',
                    'if (ferror(vmafdata->reference_file) || fclose(vmafdata->reference_file))',
                    '    x265_log(param, X265_LOG_WARNING, "Unable to close VMAF reference file after score calculation\\n");',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden VMAF encoder-log close short-circuit regression: if (ferror(vmafdata->reference_file) || fclose(vmafdata->reference_file))')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/api.cpp': '\n'.join((
                    'stats.aggregateVmafScore = x265_calculate_vmafscore(param, vmafdata);',
                    'x265_free(vmafdata);',
                    'if(vmafdata->reference_file)',
                    'bool closeFailed = ferror(vmafdata->reference_file) != 0;',
                    'if (fclose(vmafdata->reference_file))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '    x265_log(param, X265_LOG_WARNING, "Unable to close VMAF reference file after score calculation\\n");',
                    'if(vmafdata->distorted_file)',
                    'bool closeFailed = ferror(vmafdata->distorted_file) != 0;',
                    'if (fclose(vmafdata->distorted_file))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '    x265_log(param, X265_LOG_WARNING, "Unable to close VMAF distorted file after score calculation\\n");',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'VMAF close guards must stay after score calculation and before x265_free(vmafdata)')

    print('VMAF encoder-log close guard tests passed')


if __name__ == '__main__':
    main()
