#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_abr_thread_field_view_usage.py')

# Coverage probes used by the scan for ABR field-view guardrails.
NORMALIZED_PROBES = (
    'missing ABR thread field-view guardrail: ',
    'forbidden ABR field-view regression: ',
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
                'source/abrEncApp.cpp': '\n'.join((
                    'uint64_t requiredFieldFrameSize = pic_in[view]->stride[0] *',
                    'for (int i = 1; i < x265_cli_csps[pic_in[view]->colorSpace].planes; i++)',
                    'if (requiredFieldFrameSize != fieldFrameSize || requiredFieldFrameSize != picField1.framesize)',
                    'x265_log(m_param, X265_LOG_ERROR, "Field picture layout mismatch for view %d in %s\\n",',
                    'int stride = picField1.stride[0] = picField2.stride[0] = pic_in[view]->stride[0];',
                    'for (int i = 1; i < x265_cli_csps[pic_in[view]->colorSpace].planes; i++)',
                    'assert(framesize == requiredFieldFrameSize);',
                    'fieldBuffersCreated = true;',
                    '{',
                    '}',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/abrEncApp.cpp': '\n'.join((
                    'int stride = picField1.stride[0] = picField2.stride[0] = pic_in[0]->stride[0];',
                    'for (int i = 1; i < x265_cli_csps[pic_in[0]->colorSpace].planes; i++)',
                    '{',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden ABR field-view regression')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/abrEncApp.cpp': '\n'.join((
                    'uint64_t requiredFieldFrameSize = pic_in[view]->stride[0] *',
                    'int stride = picField1.stride[0] = picField2.stride[0] = pic_in[view]->stride[0];',
                    'for (int i = 1; i < x265_cli_csps[pic_in[view]->colorSpace].planes; i++)',
                    'if (requiredFieldFrameSize != fieldFrameSize || requiredFieldFrameSize != picField1.framesize)',
                    'x265_log(m_param, X265_LOG_ERROR, "Field picture layout mismatch for view %d in %s\\n",',
                    'for (int i = 1; i < x265_cli_csps[pic_in[view]->colorSpace].planes; i++)',
                    'assert(framesize == requiredFieldFrameSize);',
                    'fieldBuffersCreated = true;',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'ABR field threading must preserve the reviewed view-indexed frame-size validation before publishing per-view field strides and planes')

    print('ABR thread field-view usage tests passed')


if __name__ == '__main__':
    main()
