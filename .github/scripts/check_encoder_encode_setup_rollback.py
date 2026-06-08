#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/encoder/encoder.cpp')


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    failures = []
    required = (
        'Frame* inFrame[MAX_LAYERS] = {};',
        'bool inFrameFromFreeList[MAX_LAYERS] = {};',
        'bool inFrameRefCounted[MAX_LAYERS] = {};',
        'int stagedOrigPicFreeFrames = 0;',
        'auto rollbackPendingInputFrames = [&](int lastLayer)',
        'auto rollbackPendingEncodeSetup = [&](int lastLayer)',
        'pendingFrame->m_countRefEncoders.fetch_sub(1);',
        'm_dpb->m_freeList.pushBack(*pendingFrame);',
        'Frame* stagedFrame = m_lookahead->m_origPicBuf->m_mcstfOrigPicFreeList.popBackMCSTF();',
        'rollbackPendingEncodeSetup(layer);',
        'rollbackPendingEncodeSetup(m_param->numLayers - 1);',
        'stagedOrigPicFreeFrames++;',
    )
    for snippet in required:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing encoder encode setup rollback guardrail: {snippet}'))

    quant_pos = text.find('"x265_picture.quantOffsets is unsupported because the public API does not expose a verifiable buffer length\\n"')
    quant_rollback_pos = text.find('rollbackPendingEncodeSetup(m_param->numLayers - 1);', quant_pos if quant_pos != -1 else 0)
    dup_alloc_log_pos = text.find('x265_log(m_param, X265_LOG_ERROR, "Unable to allocate temporal-filter frame %d, aborting encode\\n", i);')
    dup_alloc_rollback_pos = text.find('rollbackPendingEncodeSetup(m_param->numLayers - 1);', dup_alloc_log_pos if dup_alloc_log_pos != -1 else 0)
    staged_add_pos = text.find('m_lookahead->m_origPicBuf->addEncPicture(dupFrame);')
    staged_count_pos = text.find('stagedOrigPicFreeFrames++;', staged_add_pos if staged_add_pos != -1 else 0)
    if -1 in (quant_pos, quant_rollback_pos, dup_alloc_log_pos, dup_alloc_rollback_pos, staged_add_pos, staged_count_pos) or not (
        quant_pos < quant_rollback_pos and dup_alloc_log_pos < dup_alloc_rollback_pos and staged_add_pos < staged_count_pos
    ):
        failures.append((TARGET.as_posix(), 0, 'Encoder::encode setup failures must roll back pending input frames and staged temporal-filter frames before returning'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check Encoder::encode setup rollback guards')
    parser.add_argument('repo_root', nargs='?', default='.')
    args = parser.parse_args()

    failures = check_repo(args.repo_root)
    if failures:
        for path, line, message in failures:
            if line:
                print(f'::error file={path},line={line}::{message}')
            else:
                print(f'::error file={path}::{message}')
        raise SystemExit(1)

    print('Encoder::encode setup rollback guards validated')


if __name__ == '__main__':
    main()
