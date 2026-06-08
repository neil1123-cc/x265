#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_frame_create_subsample_staging.py')

# Coverage probes used by the scan for Frame::createSubSample staging guardrails.
NORMALIZED_PROBES = (
    'missing frame createSubSample staging guardrail: #include <new>',
    'missing Frame::createSubSample function',
    'Frame::createSubSample must fully stage subsampled picture state before assigning member state',
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
        '#include <new>',
        'bool Frame::createSubSample()',
        '{',
        '    PicYuv* stagedFencPicSubsampled2 = new (std::nothrow) PicYuv;',
        '    PicYuv* stagedFencPicSubsampled4 = new (std::nothrow) PicYuv;',
        '    int* stagedIsSubSampled = nullptr;',
        '    if (!stagedFencPicSubsampled2 || !stagedFencPicSubsampled4)',
        '        return false;',
        '    if (!stagedFencPicSubsampled2->createScaledPicYUV(m_param, 2))',
        '        goto fail;',
        '    if (!stagedFencPicSubsampled4->createScaledPicYUV(m_param, 4))',
        '        goto fail;',
        '    CHECKED_MALLOC_ZERO(stagedIsSubSampled, int, 1);',
        '    m_fencPicSubsampled2 = stagedFencPicSubsampled2;',
        '    m_fencPicSubsampled4 = stagedFencPicSubsampled4;',
        '    m_isSubSampled = stagedIsSubSampled;',
        '    return true;',
        'fail:',
        '    stagedFencPicSubsampled2->destroy();',
        '    delete stagedFencPicSubsampled2;',
        '    stagedFencPicSubsampled4->destroy();',
        '    delete stagedFencPicSubsampled4;',
        '    X265_FREE(stagedIsSubSampled);',
        '    return false;',
        '}',
    )) + '\n'


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/common/frame.cpp': valid_text()})
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/common/frame.cpp': valid_text().replace('PicYuv* stagedFencPicSubsampled2 = new (std::nothrow) PicYuv;', 'm_fencPicSubsampled2 = new PicYuv;', 1)})
        expect_fail(run_checker(root), 'forbidden frame createSubSample staging regression: m_fencPicSubsampled2 = new PicYuv;')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/common/frame.cpp': valid_text().replace('    X265_FREE(stagedIsSubSampled);\n', '', 1)})
        expect_fail(run_checker(root), 'missing frame createSubSample staging guardrail: X265_FREE(stagedIsSubSampled);')

    print('Frame::createSubSample staging guard tests passed')


if __name__ == '__main__':
    main()
