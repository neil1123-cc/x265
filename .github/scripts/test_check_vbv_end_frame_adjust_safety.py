#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_vbv_end_frame_adjust_safety.py')

# Coverage probes used by the scan for vbv-end-fr-adj guardrails.
NORMALIZED_PROBES = (
    'forbidden vbv-end-fr-adj regression: ',
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
                'source/common/param.cpp': '\n'.join((
                    'OPT("vbv-end-fr-adj") bError |= !parseOptionDoubleToken(value, std::strlen(value), p->vbvEndFrameAdjust);',
                    'OPT("copy-pic")',
                    'CHECK(param->vbvEndFrameAdjust < 0 || param->vbvEndFrameAdjust > 1,',
                    '    "Valid vbv-end-fr-adj must be a fraction 0 - 1");',
                    'CHECK(param->vbvBufferEnd > 0 && param->vbvEndFrameAdjust == 0,',
                    '    "vbv-end-fr-adj must be greater than 0 when vbv-end is enabled");',
                    'if ((param->rc.vbvBufferSize > 0 || param->rc.vbvMaxBitrate > 0) && param->bThreadedME)',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': '\n'.join((
                    'OPT("vbv-end-fr-adj") bError |= !parseOptionDoubleToken(value, std::strlen(value), p->vbvEndFrameAdjust);',
                    'CHECK(param->vbvEndFrameAdjust < 0,',
                    '    "Valid vbv-end-fr-adj must be a fraction 0 - 1");',
                    'CHECK(param->vbvBufferEnd > 0 && param->vbvEndFrameAdjust == 0,',
                    '    "vbv-end-fr-adj must be greater than 0 when vbv-end is enabled");',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden vbv-end-fr-adj regression')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': '\n'.join((
                    'OPT("vbv-end-fr-adj") bError |= !parseOptionDoubleToken(value, std::strlen(value), p->vbvEndFrameAdjust);',
                    'CHECK(param->vbvEndFrameAdjust < 0 || param->vbvEndFrameAdjust > 1,',
                    '    "Valid vbv-end-fr-adj must be a fraction 0 - 1");',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'missing vbv-end-fr-adj guardrail: CHECK(param->vbvBufferEnd > 0 && param->vbvEndFrameAdjust == 0,')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': '\n'.join(((
                    'OPT("vbv-end-fr-adj") bError |= !parseOptionDoubleToken(value, std::strlen(value), p->vbvEndFrameAdjust);',
                    'OPT("copy-pic")',
                    'CHECK(param->vbvBufferEnd > 0 && param->vbvEndFrameAdjust == 0,',
                    '    "vbv-end-fr-adj must be greater than 0 when vbv-end is enabled");',
                    'CHECK(param->vbvEndFrameAdjust < 0 || param->vbvEndFrameAdjust > 1,',
                    '    "Valid vbv-end-fr-adj must be a fraction 0 - 1");',
                    'if ((param->rc.vbvBufferSize > 0 || param->rc.vbvMaxBitrate > 0) && param->bThreadedME)',
                ))) + '\n',
            },
        )
        expect_fail(run_checker(root), 'vbv-end-fr-adj validation must keep the reviewed range check ahead of the vbv-end dependency check')

    print('VBV end frame adjust safety tests passed')


if __name__ == '__main__':
    main()
