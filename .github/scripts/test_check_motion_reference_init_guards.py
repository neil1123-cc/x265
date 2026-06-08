#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_motion_reference_init_guards.py')

# Coverage probes used by the scan for motion reference-init guardrails.
NORMALIZED_PROBES = (
    'missing file',
    'unable to locate motion reference initialization loop',
    'Motion reference init failures must abort frame compression immediately',
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


def reference_text():
    return '\n'.join((
        'int MotionReference::init(PicYuv* recPic, WeightParam *wp, const x265_param& p)',
        '{',
        '    bool allocWeightBuffer[3] = { false, false, false };',
        '    if (!wp)',
        '        return 0;',
        '    numSliceWeightedRows = X265_MALLOC(uint32_t, p.maxSlices);',
        '    if (!numSliceWeightedRows)',
        '        goto fail;',
        '    std::fill_n(numSliceWeightedRows, p.maxSlices, uint32_t(0));',
        '    allocWeightBuffer[c] = true;',
        '    return 0;',
        'fail:',
        '    fpelPlane[0] = recPic->m_picOrg[0];',
        '    fpelPlane[1] = recPic->m_picOrg[1];',
        '    fpelPlane[2] = recPic->m_picOrg[2];',
        '    if (allocWeightBuffer[c])',
        '    {',
        '        X265_FREE(weightBuffer[c]);',
        '        weightBuffer[c] = nullptr;',
        '    }',
        '    X265_FREE(numSliceWeightedRows);',
        '    numSliceWeightedRows = nullptr;',
        '    return -1;',
        '}',
        'void MotionReference::applyWeight(uint32_t finishedRows, uint32_t maxNumRows, uint32_t maxNumRowsInSlice, uint32_t sliceId)',
        '{',
        '}',
    )) + '\n'


def frameencoder_text():
    return '\n'.join((
        'for (int l = 0; l < numPredDir; l++)',
        '{',
        '    if (m_mref[l][ref].init(slice->m_refReconPicList[l][ref], w, *m_param) < 0)',
        '    {',
        '        x265_log(m_param, X265_LOG_ERROR, "Unable to initialize motion reference weights\\n");',
        '        m_top->m_aborted = true;',
        '        return;',
        '    }',
        '}',
        'int numTLD;',
    )) + '\n'


def valid_repo(root):
    write_targets(root, {
        'source/encoder/reference.cpp': reference_text(),
        'source/encoder/frameencoder.cpp': frameencoder_text(),
    })


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        valid_repo(root)
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        valid_repo(root)
        path = root / 'source/encoder/reference.cpp'
        path.write_text(reference_text().replace('if (!wp)', 'if (wp)', 1))
        expect_fail(run_checker(root), 'missing MotionReference init guardrail: if (!wp)')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        valid_repo(root)
        path = root / 'source/encoder/reference.cpp'
        path.write_text(reference_text().replace('X265_FREE(numSliceWeightedRows);', '', 1))
        expect_fail(run_checker(root), 'MotionReference::init must only allocate slice-weight rows for weighted references and must roll back weighted state on failure')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        valid_repo(root)
        path = root / 'source/encoder/frameencoder.cpp'
        path.write_text(frameencoder_text().replace('m_top->m_aborted = true;', 'm_top->m_aborted = false;', 1))
        expect_fail(run_checker(root), 'missing motion reference init failure handling: m_top->m_aborted = true;')

    print('MotionReference init guard tests passed')


if __name__ == '__main__':
    main()
