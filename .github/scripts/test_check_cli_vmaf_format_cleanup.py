#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_cli_vmaf_format_cleanup.py')


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
    'x265_log(param, X265_LOG_ERROR, "VMAF supports YUV file format only.\\n");',
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
    'x265_log(param, X265_LOG_ERROR, "VMAF will support only yuv420p, yu422p, yu444p, yuv420p10le, yuv422p10le, yuv444p10le formats.\\n");',
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
                    'x265_log(param, X265_LOG_ERROR, "VMAF supports YUV file format only.\\n");',
                    'return true;',
                    'x265_log(param, X265_LOG_ERROR, "VMAF will support only yuv420p, yu422p, yu444p, yuv420p10le, yuv422p10le, yuv444p10le formats.\\n");',
                    'return true;',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'missing CLI VMAF format cleanup guardrail: for (int releaseIdx = 0; releaseIdx < viewCount; releaseIdx++)')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/x265cli.cpp': '\n'.join((
                    'x265_log(param, X265_LOG_ERROR, "VMAF will support only yuv420p, yu422p, yu444p, yuv420p10le, yuv422p10le, yuv444p10le formats.\\n");',
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
                    'x265_log(param, X265_LOG_ERROR, "VMAF supports YUV file format only.\\n");',
                    'if (this->input[releaseIdx])',
                    '{',
                    '    this->input[releaseIdx]->release();',
                    '    this->input[releaseIdx] = nullptr;',
                    '}',
                    'for (int releaseIdx = 0; releaseIdx < viewCount; releaseIdx++)',
                    '{',
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
        expect_fail(run_checker(root), 'CLI VMAF Y4M rejection must release started inputs and recon handles before returning')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/x265cli.cpp': '\n'.join((
                    'x265_log(param, X265_LOG_ERROR, "VMAF supports YUV file format only.\\n");',
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
                    'x265_log(param, X265_LOG_ERROR, "VMAF will support only yuv420p, yu422p, yu444p, yuv420p10le, yuv422p10le, yuv444p10le formats.\\n");',
                    'if (this->input[releaseIdx])',
                    '{',
                    '    this->input[releaseIdx]->release();',
                    '    this->input[releaseIdx] = nullptr;',
                    '}',
                    'for (int releaseIdx = 0; releaseIdx < viewCount; releaseIdx++)',
                    '{',
                    '}',
                    'for (int releaseIdx = 0; releaseIdx < param->numLayers; releaseIdx++)',
                    '{',
                    '    if (this->recon[releaseIdx])',
                    '    {',
                    '        this->recon[releaseIdx]->release();',
                    '        this->recon[releaseIdx] = nullptr;',
                    '    }',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'CLI VMAF colorspace rejection must release started inputs and recon handles before returning')

    print('CLI VMAF format cleanup tests passed')


if __name__ == '__main__':
    main()
