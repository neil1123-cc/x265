#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/encoder/slicetype.cpp')
REQUIRED_SNIPPETS = (
    '#include <new>',
    'm_metld = nullptr;',
    'm_accHistDiffRunningAvgCb = nullptr;',
    'm_accHistDiffRunningAvgCr = nullptr;',
    'm_accHistDiffRunningAvg = nullptr;',
    'if (m_accHistDiffRunningAvgCb)',
    'if (m_accHistDiffRunningAvgCb[0])',
    'm_accHistDiffRunningAvgCb[w] = m_accHistDiffRunningAvgCb[0] + w * NUMBER_OF_SEGMENTS_IN_HEIGHT;',
    'if (m_accHistDiffRunningAvgCr)',
    'if (m_accHistDiffRunningAvgCr[0])',
    'm_accHistDiffRunningAvgCr[w] = m_accHistDiffRunningAvgCr[0] + w * NUMBER_OF_SEGMENTS_IN_HEIGHT;',
    'if (m_accHistDiffRunningAvg)',
    'if (m_accHistDiffRunningAvg[0])',
    'm_accHistDiffRunningAvg[w] = m_accHistDiffRunningAvg[0] + w * NUMBER_OF_SEGMENTS_IN_HEIGHT;',
    'if (!m_accHistDiffRunningAvgCb || !m_accHistDiffRunningAvgCb[0] ||',
    'x265_log(m_param, X265_LOG_ERROR, "Unable to allocate lookahead histogram buffers\\n");',
    'LookaheadTLD* tld = new (std::nothrow) LookaheadTLD[numTLD];',
    'if (!tld)',
    'x265_log(m_param, X265_LOG_ERROR, "Unable to allocate lookahead thread-local data\\n");',
    'scratch = X265_MALLOC(int, tld[0].widthInCU);',
    'if (!scratch)',
    'x265_log(m_param, X265_LOG_ERROR, "Unable to allocate lookahead scratch buffer\\n");',
    'metld = new (std::nothrow) MotionEstimatorTLD[numTLD];',
    'if (!metld)',
    'x265_log(m_param, X265_LOG_ERROR, "Unable to allocate lookahead motion-estimator buffers\\n");',
    'origPicBuf = new (std::nothrow) OrigPicBuffer();',
    'if (!origPicBuf)',
    'x265_log(m_param, X265_LOG_ERROR, "Unable to allocate lookahead original-picture buffer\\n");',
    'm_tld = tld;',
    'm_scratch = scratch;',
    'm_metld = metld;',
    'm_origPicBuf = origPicBuf;',
    'if (m_accHistDiffRunningAvgCb)',
    'X265_FREE(m_accHistDiffRunningAvgCb[0]);',
    'if (m_accHistDiffRunningAvgCr)',
    'X265_FREE(m_accHistDiffRunningAvgCr[0]);',
    'if (m_accHistDiffRunningAvg)',
    'X265_FREE(m_accHistDiffRunningAvg[0]);',
)


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    failures = []
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing lookahead allocation guardrail: {snippet}'))

    ctor_pos = text.find('Lookahead::Lookahead(x265_param *param, ThreadPool* pool)')
    cb_alloc_pos = text.find('m_accHistDiffRunningAvgCb = X265_MALLOC(uint32_t*, NUMBER_OF_SEGMENTS_IN_WIDTH);', ctor_pos if ctor_pos != -1 else 0)
    cb_guard_pos = text.find('if (m_accHistDiffRunningAvgCb)', cb_alloc_pos if cb_alloc_pos != -1 else 0)
    create_pos = text.find('bool Lookahead::create()')
    hist_guard_pos = text.find('if (!m_accHistDiffRunningAvgCb || !m_accHistDiffRunningAvgCb[0] ||', create_pos if create_pos != -1 else 0)
    tld_alloc_pos = text.find('LookaheadTLD* tld = new (std::nothrow) LookaheadTLD[numTLD];', hist_guard_pos if hist_guard_pos != -1 else 0)
    tld_guard_pos = text.find('if (!tld)', tld_alloc_pos if tld_alloc_pos != -1 else 0)
    scratch_alloc_pos = text.find('scratch = X265_MALLOC(int, tld[0].widthInCU);', tld_guard_pos if tld_guard_pos != -1 else 0)
    scratch_guard_pos = text.find('if (!scratch)', scratch_alloc_pos if scratch_alloc_pos != -1 else 0)
    metld_alloc_pos = text.find('metld = new (std::nothrow) MotionEstimatorTLD[numTLD];', scratch_guard_pos if scratch_guard_pos != -1 else 0)
    metld_guard_pos = text.find('if (!metld)', metld_alloc_pos if metld_alloc_pos != -1 else 0)
    orig_alloc_pos = text.find('origPicBuf = new (std::nothrow) OrigPicBuffer();', metld_guard_pos if metld_guard_pos != -1 else 0)
    orig_guard_pos = text.find('if (!origPicBuf)', orig_alloc_pos if orig_alloc_pos != -1 else 0)
    publish_tld_pos = text.find('m_tld = tld;', orig_guard_pos if orig_guard_pos != -1 else 0)
    publish_scratch_pos = text.find('m_scratch = scratch;', publish_tld_pos if publish_tld_pos != -1 else 0)
    publish_metld_pos = text.find('m_metld = metld;', publish_scratch_pos if publish_scratch_pos != -1 else 0)
    publish_orig_pos = text.find('m_origPicBuf = origPicBuf;', publish_metld_pos if publish_metld_pos != -1 else 0)
    destroy_pos = text.find('void Lookahead::destroy()')
    destroy_cb_guard_pos = text.find('if (m_accHistDiffRunningAvgCb)', destroy_pos if destroy_pos != -1 else 0)
    cb_row_pos = text.find('m_accHistDiffRunningAvgCb[w] = m_accHistDiffRunningAvgCb[0] + w * NUMBER_OF_SEGMENTS_IN_HEIGHT;', cb_guard_pos if cb_guard_pos != -1 else 0)
    cr_alloc_pos = text.find('m_accHistDiffRunningAvgCr = X265_MALLOC(uint32_t*, NUMBER_OF_SEGMENTS_IN_WIDTH);', cb_guard_pos if cb_guard_pos != -1 else 0)
    cr_guard_pos = text.find('if (m_accHistDiffRunningAvgCr)', cr_alloc_pos if cr_alloc_pos != -1 else 0)
    cr_row_pos = text.find('m_accHistDiffRunningAvgCr[w] = m_accHistDiffRunningAvgCr[0] + w * NUMBER_OF_SEGMENTS_IN_HEIGHT;', cr_guard_pos if cr_guard_pos != -1 else 0)
    y_alloc_pos = text.find('m_accHistDiffRunningAvg = X265_MALLOC(uint32_t*, NUMBER_OF_SEGMENTS_IN_WIDTH);', cr_guard_pos if cr_guard_pos != -1 else 0)
    y_guard_pos = text.find('if (m_accHistDiffRunningAvg)', y_alloc_pos if y_alloc_pos != -1 else 0)
    y_row_pos = text.find('m_accHistDiffRunningAvg[w] = m_accHistDiffRunningAvg[0] + w * NUMBER_OF_SEGMENTS_IN_HEIGHT;', y_guard_pos if y_guard_pos != -1 else 0)
    if -1 in (
        ctor_pos, cb_alloc_pos, cb_guard_pos, create_pos, hist_guard_pos,
        tld_alloc_pos, tld_guard_pos, scratch_alloc_pos, scratch_guard_pos,
        metld_alloc_pos, metld_guard_pos, orig_alloc_pos, orig_guard_pos,
        publish_tld_pos, publish_scratch_pos, publish_metld_pos, publish_orig_pos,
        destroy_pos, destroy_cb_guard_pos,
    ) or not (
        ctor_pos < cb_alloc_pos < cb_guard_pos < cb_row_pos < cr_alloc_pos < cr_guard_pos < cr_row_pos < y_alloc_pos < y_guard_pos < y_row_pos and
        create_pos < hist_guard_pos < tld_alloc_pos < tld_guard_pos < scratch_alloc_pos < scratch_guard_pos <
        metld_alloc_pos < metld_guard_pos < orig_alloc_pos < orig_guard_pos <
        publish_tld_pos < publish_scratch_pos < publish_metld_pos < publish_orig_pos and
        destroy_pos < destroy_cb_guard_pos
    ):
        failures.append((TARGET.as_posix(), 0, 'Lookahead constructor/create/destroy must guard histogram allocations, initialize histogram row pointers, and validate worker-buffer allocations before use and cleanup'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check lookahead allocation guardrails')
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

    print('Lookahead allocation guards validated')


if __name__ == '__main__':
    main()
