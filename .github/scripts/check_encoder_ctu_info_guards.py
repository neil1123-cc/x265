#!/usr/bin/env python3
import argparse
from pathlib import Path


FRAME_H = Path('source/common/frame.h')
FRAME_CPP = Path('source/common/frame.cpp')
DPB_CPP = Path('source/encoder/dpb.cpp')
ANALYSIS_CPP = Path('source/encoder/analysis.cpp')
ENCODER_H = Path('source/encoder/encoder.h')
ENCODER_CPP = Path('source/encoder/encoder.cpp')
API_CPP = Path('source/encoder/api.cpp')


def extract_braced_block(text, signature):
    start = text.find(signature)
    if start == -1:
        return ''
    brace_start = text.find('{', start)
    if brace_start == -1:
        return text[start:]
    depth = 0
    for idx in range(brace_start, len(text)):
        char = text[idx]
        if char == '{':
            depth += 1
        elif char == '}':
            depth -= 1
            if depth == 0:
                return text[start:idx + 1]
    return text[start:]


def read_file(repo_root, relative):
    path = repo_root / relative
    if not path.is_file():
        return None, [(relative.as_posix(), 0, 'missing file')]
    return path.read_text(encoding='utf-8', errors='ignore'), []


def require_snippets(text, relative, snippets, label):
    failures = []
    for snippet in snippets:
        if snippet not in text:
            failures.append((relative.as_posix(), 0, f'missing {label}: {snippet}'))
    return failures


def forbid_snippets(text, relative, snippets, label):
    failures = []
    for snippet in snippets:
        if snippet in text:
            failures.append((relative.as_posix(), 0, f'forbidden {label}: {snippet}'))
    return failures


def check_repo(repo_root):
    repo_root = Path(repo_root)
    failures = []

    frame_h, errs = read_file(repo_root, FRAME_H)
    failures.extend(errs)
    frame_cpp, errs = read_file(repo_root, FRAME_CPP)
    failures.extend(errs)
    dpb_cpp, errs = read_file(repo_root, DPB_CPP)
    failures.extend(errs)
    analysis_cpp, errs = read_file(repo_root, ANALYSIS_CPP)
    failures.extend(errs)
    encoder_h, errs = read_file(repo_root, ENCODER_H)
    failures.extend(errs)
    encoder_cpp, errs = read_file(repo_root, ENCODER_CPP)
    failures.extend(errs)
    api_cpp, errs = read_file(repo_root, API_CPP)
    failures.extend(errs)
    if failures:
        return failures

    failures.extend(require_snippets(
        frame_h,
        FRAME_H,
        ('x265_ctu_info_t*       m_ctuInfo;',),
        'Frame CTU-info storage guardrail',
    ))
    failures.extend(forbid_snippets(
        frame_h,
        FRAME_H,
        ('x265_ctu_info_t**      m_ctuInfo;',),
        'Frame CTU-info storage regression',
    ))

    frame_cleanup_required = (
        'X265_FREE(m_ctuInfo[i].ctuInfo);',
        'm_ctuInfo[i].ctuInfo = nullptr;',
        'X265_FREE(m_ctuInfo);',
        'if (m_addOnDepth || m_addOnCtuInfo || m_addOnPrevChange)',
        'X265_FREE(m_addOnDepth[i]);',
        'X265_FREE(m_addOnCtuInfo[i]);',
        'X265_FREE(m_addOnPrevChange[i]);',
    )
    cleanup_forbidden = (
        'X265_FREE((*m_ctuInfo + i)->ctuInfo);',
        'X265_FREE(*m_ctuInfo);',
    )
    failures.extend(require_snippets(frame_cpp, FRAME_CPP, frame_cleanup_required, 'frame CTU-info cleanup guardrail'))
    failures.extend(forbid_snippets(frame_cpp, FRAME_CPP, cleanup_forbidden, 'frame CTU-info cleanup regression'))
    dpb_cleanup_required = (
        'X265_FREE(curFrame->m_ctuInfo[i].ctuInfo);',
        'curFrame->m_ctuInfo[i].ctuInfo = nullptr;',
        'X265_FREE(curFrame->m_ctuInfo);',
    )
    dpb_cleanup_forbidden = (
        'X265_FREE((*curFrame->m_ctuInfo + i)->ctuInfo);',
        'X265_FREE(*curFrame->m_ctuInfo);',
    )
    failures.extend(require_snippets(dpb_cpp, DPB_CPP, dpb_cleanup_required, 'DPB CTU-info cleanup guardrail'))
    failures.extend(forbid_snippets(dpb_cpp, DPB_CPP, dpb_cleanup_forbidden, 'DPB CTU-info cleanup regression'))

    analysis_text = extract_braced_block(analysis_cpp, 'Mode& Analysis::compressCTU(CUData& ctu, Frame& frame, const CUGeom& cuGeom, const Entropy& initialContext)')
    if not analysis_text:
        failures.append((ANALYSIS_CPP.as_posix(), 0, 'missing Analysis::compressCTU function'))
    else:
        failures.extend(require_snippets(
            analysis_text,
            ANALYSIS_CPP,
            (
                'if (m_param->bCTUInfo && m_frame->m_ctuInfo && m_frame->m_ctuInfo[ctu.m_cuAddr].ctuInfo)',
                'x265_ctu_info_t* ctuTemp = m_frame->m_ctuInfo + ctu.m_cuAddr;',
                'depthIdx < (int32_t)maxNum8x8Partitions && ctuTemp->ctuPartitions[depthIdx] != 0',
            ),
            'analysis CTU-info guardrail',
        ))
        failures.extend(forbid_snippets(
            analysis_text,
            ANALYSIS_CPP,
            ('x265_ctu_info_t* ctuTemp = m_frame->m_ctuInfo[ctu.m_cuAddr];',),
            'analysis CTU-info regression',
        ))

    failures.extend(require_snippets(
        encoder_h,
        ENCODER_H,
        ('bool copyCtuInfo(x265_ctu_info_t *const* frameCtuInfo, int poc);',),
        'encoder CTU-info signature guardrail',
    ))
    failures.extend(forbid_snippets(
        encoder_h,
        ENCODER_H,
        ('void copyCtuInfo(x265_ctu_info_t** frameCtuInfo, int poc);',),
        'encoder CTU-info signature regression',
    ))

    encoder_text = extract_braced_block(encoder_cpp, 'bool Encoder::copyCtuInfo(x265_ctu_info_t *const* frameCtuInfo, int poc)')
    if not encoder_text:
        failures.append((ENCODER_CPP.as_posix(), 0, 'missing Encoder::copyCtuInfo function'))
    else:
        failures.extend(require_snippets(
            encoder_text,
            ENCODER_CPP,
            (
                'if (curFrame->m_ctuInfo || curFrame->m_prevCtuInfoChange)',
                'CHECKED_MALLOC_ZERO(stagedCtuInfo, x265_ctu_info_t, numCUsInFrame);',
                'CHECKED_MALLOC_ZERO(stagedPrevCtuInfoChange, int, numCUsInFrame * maxNum8x8Partitions);',
                'if (!frameCtuInfo[i] || !frameCtuInfo[i]->ctuInfo)',
                'x265_log(m_param, X265_LOG_ERROR, "CTU info input requires non-null per-CTU records and payloads\\n");',
                'ctuTemp = stagedCtuInfo + i;',
                'if (prevFrame && prevFrame->m_ctuInfo && prevFrame->m_prevCtuInfoChange && curFrame->m_poc > 1)',
                'prevCtuTemp = prevFrame->m_ctuInfo + i;',
                'curFrame->m_ctuInfo = stagedCtuInfo;',
                'curFrame->m_prevCtuInfoChange = stagedPrevCtuInfoChange;',
                'curFrame->m_copied.trigger();',
                'X265_FREE(stagedCtuInfo[i].ctuInfo);',
                'X265_FREE(stagedPrevCtuInfoChange);',
                'return false;',
            ),
            'Encoder::copyCtuInfo guardrail',
        ))
        failures.extend(forbid_snippets(
            encoder_text,
            ENCODER_CPP,
            (
                'CHECKED_MALLOC(curFrame->m_ctuInfo, x265_ctu_info_t*, 1);',
                'CHECKED_MALLOC(*curFrame->m_ctuInfo, x265_ctu_info_t, numCUsInFrame);',
                'ctuTemp = *curFrame->m_ctuInfo + i;',
                'prevCtuTemp = *prevFrame->m_ctuInfo + i;',
                'X265_FREE((*curFrame->m_ctuInfo + i)->ctuInfo);',
            ),
            'Encoder::copyCtuInfo regression',
        ))

    api_text = extract_braced_block(api_cpp, 'int x265_encoder_ctu_info(x265_encoder *enc, int poc, x265_ctu_info_t** ctu)')
    if not api_text:
        failures.append((API_CPP.as_posix(), 0, 'missing x265_encoder_ctu_info function'))
    else:
        failures.extend(require_snippets(
            api_text,
            API_CPP,
            (
                'if (!enc || !ctu)',
                'if (!encoder->m_param->bCTUInfo)',
                'return encoder->copyCtuInfo(ctu, poc) ? 0 : -1;',
            ),
            'x265_encoder_ctu_info guardrail',
        ))
        failures.extend(forbid_snippets(
            api_text,
            API_CPP,
            ('encoder->copyCtuInfo(ctu, poc);\n    return 0;',),
            'x265_encoder_ctu_info regression',
        ))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check encoder CTU-info guards')
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

    print('Encoder CTU-info guards validated')


if __name__ == '__main__':
    main()
