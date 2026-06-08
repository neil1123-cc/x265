#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_encoder_ctu_info_guards.py')

# Coverage probes used by the scan for encoder CTU info guardrails.
NORMALIZED_PROBES = (
    'missing Analysis::compressCTU function',
    'missing Encoder::copyCtuInfo function',
    'missing x265_encoder_ctu_info function',
    'missing : ',
    'forbidden : ',
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


def valid_files():
    return {
        'source/common/frame.h': 'x265_ctu_info_t*       m_ctuInfo;\n',
        'source/common/frame.cpp': '\n'.join((
            'if (m_ctuInfo)',
            '{',
            '    X265_FREE(m_ctuInfo[i].ctuInfo);',
            '    m_ctuInfo[i].ctuInfo = nullptr;',
            '    X265_FREE(m_ctuInfo);',
            '}',
            'if (m_addOnDepth || m_addOnCtuInfo || m_addOnPrevChange)',
            '{',
            '    X265_FREE(m_addOnDepth[i]);',
            '    X265_FREE(m_addOnCtuInfo[i]);',
            '    X265_FREE(m_addOnPrevChange[i]);',
            '}',
        )) + '\n',
        'source/encoder/dpb.cpp': '\n'.join((
            'if (curFrame->m_ctuInfo != nullptr)',
            '{',
            '    X265_FREE(curFrame->m_ctuInfo[i].ctuInfo);',
            '    curFrame->m_ctuInfo[i].ctuInfo = nullptr;',
            '    X265_FREE(curFrame->m_ctuInfo);',
            '}',
        )) + '\n',
        'source/encoder/analysis.cpp': '\n'.join((
            'Mode& Analysis::compressCTU(CUData& ctu, Frame& frame, const CUGeom& cuGeom, const Entropy& initialContext)',
            '{',
            '    if (m_param->bCTUInfo && m_frame->m_ctuInfo && m_frame->m_ctuInfo[ctu.m_cuAddr].ctuInfo)',
            '    {',
            '        x265_ctu_info_t* ctuTemp = m_frame->m_ctuInfo + ctu.m_cuAddr;',
            '        int32_t depthIdx = 0;',
            '        uint32_t maxNum8x8Partitions = 64;',
            '        do',
            '        {',
            '            depthIdx++;',
            '        } while (depthIdx < (int32_t)maxNum8x8Partitions && ctuTemp->ctuPartitions[depthIdx] != 0);',
            '    }',
            '}',
        )) + '\n',
        'source/encoder/encoder.h': 'bool copyCtuInfo(x265_ctu_info_t *const* frameCtuInfo, int poc);\n',
        'source/encoder/encoder.cpp': '\n'.join((
            'bool Encoder::copyCtuInfo(x265_ctu_info_t *const* frameCtuInfo, int poc)',
            '{',
            '    if (curFrame->m_ctuInfo || curFrame->m_prevCtuInfoChange)',
            '        return curFrame->m_ctuInfo && curFrame->m_prevCtuInfoChange;',
            '    CHECKED_MALLOC_ZERO(stagedCtuInfo, x265_ctu_info_t, numCUsInFrame);',
            '    CHECKED_MALLOC_ZERO(stagedPrevCtuInfoChange, int, numCUsInFrame * maxNum8x8Partitions);',
            '    if (!frameCtuInfo[i] || !frameCtuInfo[i]->ctuInfo)',
            '    {',
            '        x265_log(m_param, X265_LOG_ERROR, "CTU info input requires non-null per-CTU records and payloads\\n");',
            '        goto fail;',
            '    }',
            '    ctuTemp = stagedCtuInfo + i;',
            '    if (prevFrame && prevFrame->m_ctuInfo && prevFrame->m_prevCtuInfoChange && curFrame->m_poc > 1)',
            '        prevCtuTemp = prevFrame->m_ctuInfo + i;',
            '    curFrame->m_ctuInfo = stagedCtuInfo;',
            '    curFrame->m_prevCtuInfoChange = stagedPrevCtuInfoChange;',
            '    curFrame->m_copied.trigger();',
            '    return true;',
            'fail:',
            '    X265_FREE(stagedCtuInfo[i].ctuInfo);',
            '    X265_FREE(stagedPrevCtuInfoChange);',
            '    return false;',
            '}',
        )) + '\n',
        'source/encoder/api.cpp': '\n'.join((
            'int x265_encoder_ctu_info(x265_encoder *enc, int poc, x265_ctu_info_t** ctu)',
            '{',
            '    if (!enc || !ctu)',
            '        return -1;',
            '    Encoder* encoder = static_cast<Encoder*>(enc);',
            '    if (!encoder->m_param->bCTUInfo)',
            '        return -1;',
            '    return encoder->copyCtuInfo(ctu, poc) ? 0 : -1;',
            '}',
        )) + '\n',
    }


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, valid_files())
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        files = valid_files()
        files['source/common/frame.h'] = 'x265_ctu_info_t**      m_ctuInfo;\n'
        write_targets(root, files)
        expect_fail(run_checker(root), 'forbidden Frame CTU-info storage regression: x265_ctu_info_t**      m_ctuInfo;')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        files = valid_files()
        files['source/encoder/analysis.cpp'] = files['source/encoder/analysis.cpp'].replace(
            '        x265_ctu_info_t* ctuTemp = m_frame->m_ctuInfo + ctu.m_cuAddr;\n',
            '        x265_ctu_info_t* ctuTemp = m_frame->m_ctuInfo[ctu.m_cuAddr];\n',
            1,
        )
        write_targets(root, files)
        expect_fail(run_checker(root), 'forbidden analysis CTU-info regression: x265_ctu_info_t* ctuTemp = m_frame->m_ctuInfo[ctu.m_cuAddr];')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        files = valid_files()
        files['source/encoder/encoder.cpp'] = files['source/encoder/encoder.cpp'].replace(
            '    CHECKED_MALLOC_ZERO(stagedCtuInfo, x265_ctu_info_t, numCUsInFrame);\n',
            '    CHECKED_MALLOC(curFrame->m_ctuInfo, x265_ctu_info_t*, 1);\n',
            1,
        )
        write_targets(root, files)
        expect_fail(run_checker(root), 'forbidden Encoder::copyCtuInfo regression: CHECKED_MALLOC(curFrame->m_ctuInfo, x265_ctu_info_t*, 1);')

    print('Encoder CTU-info guard tests passed')


if __name__ == '__main__':
    main()
