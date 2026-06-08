#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_temporalfilter_refpic_rollback.py')

# Coverage probes used by the scan for temporalfilter refpic rollback guardrails.
NORMALIZED_PROBES = (
    'forbidden temporalfilter refpic rollback regression: ',
    'missing temporalfilter refpic rollback guardrail: ',
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
                'source/common/temporalfilter.cpp': '\n'.join((
                    'void resetRefPicInfoState(TemporalFilterRefPicInfo* refFrame)',
                    'int TemporalFilter::createRefPicInfo(TemporalFilterRefPicInfo* refFrame, x265_param* param)',
                    '{',
                    'resetRefPicInfoState(refFrame);',
                    'refFrame->compensatedPic = new (std::nothrow) PicYuv;',
                    'if (!refFrame->compensatedPic || !refFrame->compensatedPic->create(param, true))',
                    '    goto fail;',
                    'return 1;',
                    'fail:',
                    'destroyRefPicInfo(refFrame);',
                    'return 0;',
                    '}',
                    'int MotionEstimatorTLD::motionErrorLumaSAD(',
                    '{',
                    '}',
                    'void TemporalFilter::destroyRefPicInfo(TemporalFilterRefPicInfo* curFrame)',
                    '{',
                    'if (curFrame->compensatedPic)',
                    '{',
                    '    curFrame->compensatedPic->destroy();',
                    '    delete curFrame->compensatedPic;',
                    '    curFrame->compensatedPic = nullptr;',
                    '}',
                    'curFrame->compensatedPic = nullptr;',
                    'curFrame->mvs = nullptr;',
                    'curFrame->mvs0 = nullptr;',
                    'curFrame->mvs1 = nullptr;',
                    'curFrame->mvs2 = nullptr;',
                    'curFrame->noise = nullptr;',
                    'curFrame->error = nullptr;',
                    'curFrame->mvsStride = 0;',
                    'curFrame->mvsStride0 = 0;',
                    'curFrame->mvsStride1 = 0;',
                    'curFrame->mvsStride2 = 0;',
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
                'source/common/temporalfilter.cpp': '\n'.join((
                    'refFrame->compensatedPic = new PicYuv;',
                    'refFrame->compensatedPic->create(param, true);',
                    '',
                    'return 1;',
                    'fail:',
                    '    return 0;',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden temporalfilter refpic rollback regression')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/temporalfilter.cpp': '\n'.join((
                    'void resetRefPicInfoState(TemporalFilterRefPicInfo* refFrame)',
                    'int TemporalFilter::createRefPicInfo(TemporalFilterRefPicInfo* refFrame, x265_param* param)',
                    '{',
                    'resetRefPicInfoState(refFrame);',
                    'refFrame->compensatedPic = new (std::nothrow) PicYuv;',
                    'if (!refFrame->compensatedPic || !refFrame->compensatedPic->create(param, true))',
                    '    goto fail;',
                    'fail:',
                    'destroyRefPicInfo(refFrame);',
                    'return 0;',
                    'return 1;',
                    '}',
                    'int MotionEstimatorTLD::motionErrorLumaSAD(',
                    '{',
                    '}',
                    'void TemporalFilter::destroyRefPicInfo(TemporalFilterRefPicInfo* curFrame)',
                    '{',
                    'if (curFrame->compensatedPic)',
                    '{',
                    '    curFrame->compensatedPic->destroy();',
                    '    delete curFrame->compensatedPic;',
                    '    curFrame->compensatedPic = nullptr;',
                    '}',
                    'curFrame->mvs = nullptr;',
                    'curFrame->mvs0 = nullptr;',
                    'curFrame->mvs1 = nullptr;',
                    'curFrame->mvs2 = nullptr;',
                    'curFrame->noise = nullptr;',
                    'curFrame->error = nullptr;',
                    'curFrame->mvsStride = 0;',
                    'curFrame->mvsStride0 = 0;',
                    'curFrame->mvsStride1 = 0;',
                    'curFrame->mvsStride2 = 0;',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'TemporalFilter::createRefPicInfo must route compensatedPic failures through destroyRefPicInfo before returning 0')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/temporalfilter.cpp': '\n'.join((
                    'void resetRefPicInfoState(TemporalFilterRefPicInfo* refFrame)',
                    'int TemporalFilter::createRefPicInfo(TemporalFilterRefPicInfo* refFrame, x265_param* param)',
                    '{',
                    'resetRefPicInfoState(refFrame);',
                    'refFrame->compensatedPic = new (std::nothrow) PicYuv;',
                    'if (!refFrame->compensatedPic || !refFrame->compensatedPic->create(param, true))',
                    '    goto fail;',
                    'return 1;',
                    'fail:',
                    'destroyRefPicInfo(refFrame);',
                    'return 0;',
                    '}',
                    'int MotionEstimatorTLD::motionErrorLumaSAD(',
                    '{',
                    '}',
                    'void TemporalFilter::destroyRefPicInfo(TemporalFilterRefPicInfo* curFrame)',
                    '{',
                    'curFrame->mvs = nullptr;',
                    'if (curFrame->compensatedPic)',
                    '{',
                    '    curFrame->compensatedPic->destroy();',
                    '    delete curFrame->compensatedPic;',
                    '    curFrame->compensatedPic = nullptr;',
                    '}',
                    'curFrame->mvs0 = nullptr;',
                    'curFrame->mvs1 = nullptr;',
                    'curFrame->mvs2 = nullptr;',
                    'curFrame->noise = nullptr;',
                    'curFrame->error = nullptr;',
                    'curFrame->mvsStride = 0;',
                    'curFrame->mvsStride0 = 0;',
                    'curFrame->mvsStride1 = 0;',
                    'curFrame->mvsStride2 = 0;',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'TemporalFilter::destroyRefPicInfo must clear compensatedPic ownership before resetting motion and noise state')

    print('Temporalfilter refpic rollback tests passed')


if __name__ == '__main__':
    main()
