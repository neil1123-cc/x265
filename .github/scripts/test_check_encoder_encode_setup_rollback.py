#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_encoder_encode_setup_rollback.py')

# Coverage probe used by the scan for the reviewed encode setup rollback guard.
NORMALIZED_PROBES = (
    'Encoder::encode setup failures must roll back pending input frames and staged temporal-filter frames before returning',
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
        'Frame* inFrame[MAX_LAYERS] = {};',
        'bool inFrameFromFreeList[MAX_LAYERS] = {};',
        'bool inFrameRefCounted[MAX_LAYERS] = {};',
        'int stagedOrigPicFreeFrames = 0;',
        'auto rollbackPendingInputFrames = [&](int lastLayer)',
        '{',
        '    pendingFrame->m_countRefEncoders.fetch_sub(1);',
        '    m_dpb->m_freeList.pushBack(*pendingFrame);',
        '}',
        'auto rollbackPendingEncodeSetup = [&](int lastLayer)',
        '{',
        '    Frame* stagedFrame = m_lookahead->m_origPicBuf->m_mcstfOrigPicFreeList.popBackMCSTF();',
        '}',
        'x265_log(m_param, X265_LOG_ERROR, "x265_picture.quantOffsets is unsupported because the public API does not expose a verifiable buffer length\\n");',
        'rollbackPendingEncodeSetup(m_param->numLayers - 1);',
        'x265_log(m_param, X265_LOG_ERROR, "Unable to allocate temporal-filter frame %d, aborting encode\\n", i);',
        'rollbackPendingEncodeSetup(m_param->numLayers - 1);',
        'if (!inFrame[layer])',
        '{',
        '    rollbackPendingEncodeSetup(layer);',
        '}',
        'm_lookahead->m_origPicBuf->addEncPicture(dupFrame);',
        'stagedOrigPicFreeFrames++;',
    )) + '\n'


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/encoder/encoder.cpp': valid_text()})
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/encoder/encoder.cpp': valid_text().replace('rollbackPendingEncodeSetup(layer);', 'return -1;', 1)})
        expect_fail(run_checker(root), 'missing encoder encode setup rollback guardrail: rollbackPendingEncodeSetup(layer);')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/encoder/encoder.cpp': valid_text().replace('Frame* stagedFrame = m_lookahead->m_origPicBuf->m_mcstfOrigPicFreeList.popBackMCSTF();', '', 1)})
        expect_fail(run_checker(root), 'missing encoder encode setup rollback guardrail: Frame* stagedFrame = m_lookahead->m_origPicBuf->m_mcstfOrigPicFreeList.popBackMCSTF();')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/encoder/encoder.cpp': valid_text().replace('stagedOrigPicFreeFrames++;', '', 1)})
        expect_fail(run_checker(root), 'missing encoder encode setup rollback guardrail: stagedOrigPicFreeFrames++;')

    print('Encoder::encode setup rollback guard tests passed')


if __name__ == '__main__':
    main()
