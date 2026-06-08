#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_abr_thread_field_layout_guard.py')

# Coverage probe used by the scan for the reviewed ABR field layout guard.
NORMALIZED_PROBES = (
    'threadMain must validate field layout before assigning field plane pointers',
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
                    'char* field2Buf = X265_MALLOC(char, fieldFrameSize);',
                    'uint64_t requiredFieldFrameSize = pic_in[view]->stride[0] *',
                    '    (height >> x265_cli_csps[pic_in[view]->colorSpace].height[0]);',
                    'for (int i = 1; i < x265_cli_csps[pic_in[view]->colorSpace].planes; i++)',
                    '    requiredFieldFrameSize += pic_in[view]->stride[i] *',
                    '        (height >> x265_cli_csps[pic_in[view]->colorSpace].height[i]);',
                    'if (requiredFieldFrameSize != fieldFrameSize || requiredFieldFrameSize != picField1.framesize)',
                    '{',
                    '    X265_FREE(field1Buf);',
                    '    X265_FREE(field2Buf);',
                    '    x265_log(m_param, X265_LOG_ERROR, "Field picture layout mismatch for view %d in %s\\n",',
                    '        view, profileName);',
                    '    m_ret = 4;',
                    '    goto fail;',
                    '}',
                    'picField1.planes[0] = field1Buf;',
                    'assert(framesize == requiredFieldFrameSize);',
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
                    'char* field2Buf = X265_MALLOC(char, fieldFrameSize);',
                    'picField1.planes[0] = field1Buf;',
                    'assert(framesize == picField1.framesize);',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'missing ABR thread field-layout guardrail: uint64_t requiredFieldFrameSize = pic_in[view]->stride[0] *')

    print('ABR thread field-layout guard tests passed')


if __name__ == '__main__':
    main()
