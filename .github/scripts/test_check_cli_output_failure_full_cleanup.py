#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_cli_output_failure_full_cleanup.py')


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
    'x265_log_file(param, X265_LOG_ERROR, "failed to open output file <%s> for writing\\n", outputfn);',
    'if (this->output)',
    '{',
    '    this->output->release();',
    '    this->output = nullptr;',
    '}',
    'closeVmafInputFile(param, vmafData->reference_file, "reference", "after output open failure");',
    'closeVmafInputFile(param, vmafData->distorted_file, "distorted", "after output open failure");',
    'for (int releaseIdx = 0; releaseIdx < viewCount; releaseIdx++)',
    '{',
    '    if (this->input[releaseIdx])',
    '    {',
    '        this->input[releaseIdx]->release();',
    '        this->input[releaseIdx] = nullptr;',
    '    }',
    '}',
    'for (int releaseIdx = 0; releaseIdx < param->numLayers; releaseIdx++)',
    '{',
    '    if (this->recon[releaseIdx])',
    '    {',
    '        this->recon[releaseIdx]->release();',
    '        this->recon[releaseIdx] = nullptr;',
    '    }',
    '}',
    'return true;',
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
                    'x265_log_file(param, X265_LOG_ERROR, "failed to open output file <%s> for writing\\n", outputfn);',
                    'return true;',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'missing CLI output failure cleanup guardrail: closeVmafInputFile(param, vmafData->reference_file, "reference", "after output open failure");')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/x265cli.cpp': '\n'.join((
                    'x265_log_file(param, X265_LOG_ERROR, "failed to open output file <%s> for writing\\n", outputfn);',
                    'closeVmafInputFile(param, vmafData->reference_file, "reference", "after output open failure");',
                    'closeVmafInputFile(param, vmafData->distorted_file, "distorted", "after output open failure");',
                    'if (this->output)',
                    '{',
                    '    this->output->release();',
                    '    this->output = nullptr;',
                    '}',
                    'for (int releaseIdx = 0; releaseIdx < viewCount; releaseIdx++)',
                    '{',
                    '    if (this->input[releaseIdx])',
                    '    {',
                    '        this->input[releaseIdx]->release();',
                    '        this->input[releaseIdx] = nullptr;',
                    '    }',
                    '}',
                    'for (int releaseIdx = 0; releaseIdx < param->numLayers; releaseIdx++)',
                    '{',
                    '    if (this->recon[releaseIdx])',
                    '    {',
                    '        this->recon[releaseIdx]->release();',
                    '        this->recon[releaseIdx] = nullptr;',
                    '    }',
                    '}',
                    'return true;',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'CLI output-open failure must release output, VMAF files, started inputs, and recon handles before returning')

    print('CLI output failure cleanup tests passed')


if __name__ == '__main__':
    main()
