#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_lookahead_tld_yuv_guards.py')

# Coverage probes used by the scan for lookahead TLD YUV guardrails.
NORMALIZED_PROBES = (
    'Lookahead::create must validate TLD YUV buffers before publishing members and roll back staged allocations on failure',
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
        'inline bool hasLookaheadTLDYuvBuffers(LookaheadTLD* tld, int numTLD)',
        '{',
        '    if (!tld[i].me.fencPUYuv.m_buf[0])',
        '        return false;',
        '    return true;',
        '}',
        'inline bool hasMotionEstimatorTLDYuvBuffers(MotionEstimatorTLD* metld, int numTLD)',
        '{',
        '    if (!metld[i].me.fencPUYuv.m_buf[0] || !metld[i].predPUYuv.m_buf[0])',
        '        return false;',
        '    return true;',
        '}',
        'LookaheadTLD* tld = new (std::nothrow) LookaheadTLD[numTLD];',
        'int* scratch = nullptr;',
        'MotionEstimatorTLD* metld = nullptr;',
        'OrigPicBuffer* origPicBuf = nullptr;',
        'if (!hasLookaheadTLDYuvBuffers(tld, numTLD))',
        '{',
        '    goto fail;',
        '}',
        'scratch = X265_MALLOC(int, tld[0].widthInCU);',
        'metld = new (std::nothrow) MotionEstimatorTLD[numTLD];',
        'if (!hasMotionEstimatorTLDYuvBuffers(metld, numTLD))',
        '{',
        '    goto fail;',
        '}',
        'm_tld = tld;',
        'm_scratch = scratch;',
        'm_metld = metld;',
        'm_origPicBuf = origPicBuf;',
        'fail:',
        'delete origPicBuf;',
        'delete[] metld;',
        'X265_FREE(scratch);',
        'delete[] tld;',
    )) + '\n'


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/encoder/slicetype.cpp': valid_text()})
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/encoder/slicetype.cpp': valid_text().replace('if (!hasLookaheadTLDYuvBuffers(tld, numTLD))', 'if (!tld)', 1)})
        expect_fail(run_checker(root), 'missing lookahead TLD YUV guardrail: if (!hasLookaheadTLDYuvBuffers(tld, numTLD))')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/encoder/slicetype.cpp': valid_text().replace('m_tld = tld;', 'm_tld = new (std::nothrow) LookaheadTLD[numTLD];', 1)})
        expect_fail(run_checker(root), 'forbidden lookahead TLD YUV regression: m_tld = new (std::nothrow) LookaheadTLD[numTLD];')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/encoder/slicetype.cpp': valid_text().replace('delete[] metld;\n', '', 1)})
        expect_fail(run_checker(root), 'missing lookahead TLD YUV guardrail: delete[] metld;')

    print('Lookahead TLD YUV guard tests passed')


if __name__ == '__main__':
    main()
