#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_frame_edge_aq_alloc_guards.py')

# Coverage probe used by the scan for edge-AQ staging guardrails.
NORMALIZED_PROBES = (
    'Frame::create must stage edge-AQ picture buffers, roll back partial allocations on failure, and only publish members after all three allocations succeed',
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
        'pixel* stagedEdgePic = X265_MALLOC(pixel, m_stride * (maxHeight + (m_lumaMarginY * 2)));',
        'pixel* stagedGaussianPic = X265_MALLOC(pixel, m_stride * (maxHeight + (m_lumaMarginY * 2)));',
        'pixel* stagedThetaPic = X265_MALLOC(pixel, m_stride * (maxHeight + (m_lumaMarginY * 2)));',
        'if (!stagedEdgePic || !stagedGaussianPic || !stagedThetaPic)',
        '{',
        '    X265_FREE(stagedEdgePic);',
        '    X265_FREE(stagedGaussianPic);',
        '    X265_FREE(stagedThetaPic);',
        '    return false;',
        '}',
        'm_edgePic = stagedEdgePic;',
        'm_gaussianPic = stagedGaussianPic;',
        'm_thetaPic = stagedThetaPic;',
    )) + '\n'


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/common/frame.cpp': valid_text()})
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/common/frame.cpp': valid_text().replace('if (!stagedEdgePic || !stagedGaussianPic || !stagedThetaPic)', 'if (!stagedEdgePic)', 1)})
        expect_fail(run_checker(root), 'missing frame edge-AQ allocation guardrail: if (!stagedEdgePic || !stagedGaussianPic || !stagedThetaPic)')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/common/frame.cpp': valid_text().replace('m_edgePic = stagedEdgePic;', 'm_edgePic = X265_MALLOC(pixel, m_stride * (maxHeight + (m_lumaMarginY * 2)));', 1)})
        expect_fail(run_checker(root), 'forbidden frame edge-AQ allocation regression: m_edgePic = X265_MALLOC(pixel, m_stride * (maxHeight + (m_lumaMarginY * 2)));')

    print('Frame edge-AQ allocation guard tests passed')


if __name__ == '__main__':
    main()
