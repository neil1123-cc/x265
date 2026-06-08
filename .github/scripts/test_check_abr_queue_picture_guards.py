#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_abr_queue_picture_guards.py')


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
                'source/abrEncApp.cpp': '\n'.join((
                    'void Scaler::threadMain()',
                    '{',
                    'x265_picture *srcPic = m_parentEnc->m_parent->m_inputPicBuffer[srcId][scaledWritten % QDepth];',
                    'x265_picture* destPic = m_parentEnc->m_parent->m_inputPicBuffer[m_id][scaledWriteIdx];',
                    'if (!srcPic || !destPic)',
                    '{',
                    '    x265_log(m_parentEnc->m_param, X265_LOG_ERROR, "Missing scaler queue picture at src %u dst %d\\n", scaledWritten % QDepth, scaledWriteIdx);',
                    '}',
                    'if (!scalePic(destPic, srcPic))',
                    '{',
                    '    x265_log(nullptr, X265_LOG_ERROR, "Unable to copy scaled input picture to input queue \\n");',
                    '    m_parentEnc->m_ret = 4;',
                    '    m_threadActive.store(false);',
                    '    m_parentEnc->m_inputOver.store(true);',
                    '    m_parentEnc->m_parent->m_picWriteCnt[srcId].poke();',
                    '    m_parentEnc->m_parent->m_picWriteCnt[m_id].poke();',
                    '    break;',
                    '}',
                    'm_parentEnc->m_parent->m_picWriteCnt[m_id].incr();',
                    'm_scaledWriteCnt.incr();',
                    'm_parentEnc->m_parent->m_picIdxReadCnt[srcId][scaledWriteIdx].incr();',
                    '}',
                    'void Reader::threadMain()',
                    '{',
                    'x265_picture* dest = m_parentEnc->m_parent->m_inputPicBuffer[m_id][writeIdx];',
                    'if (m_parentEnc->m_param->numViews > 1)',
                    '    dest = m_parentEnc->m_parent->m_inputPicBuffer[view][writeIdx];',
                    'if (!dest)',
                    '{',
                    '    x265_log(m_parentEnc->m_param, X265_LOG_ERROR, "Missing reader queue picture at view %d index %u\\n", view, writeIdx);',
                    '}',
                    'if (m_input[view]->readPicture(*src))',
                    '{',
                    '}',
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
                'source/abrEncApp.cpp': 'if (!scalePic(destPic, srcPic))\n{\n}\n',
            },
        )
        expect_fail(run_checker(root), 'missing ABR queue picture guardrail: if (!srcPic || !destPic)')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/abrEncApp.cpp': '\n'.join((
                    'void Scaler::threadMain()',
                    '{',
                    'x265_picture *srcPic = m_parentEnc->m_parent->m_inputPicBuffer[srcId][scaledWritten % QDepth];',
                    'x265_picture* destPic = m_parentEnc->m_parent->m_inputPicBuffer[m_id][scaledWriteIdx];',
                    'if (!scalePic(destPic, srcPic))',
                    '{',
                    '    x265_log(nullptr, X265_LOG_ERROR, "Unable to copy scaled input picture to input queue \\n");',
                    '    m_scaledWriteCnt.incr();',
                    '}',
                    'm_parentEnc->m_parent->m_picWriteCnt[m_id].incr();',
                    'm_parentEnc->m_parent->m_picIdxReadCnt[srcId][scaledWriteIdx].incr();',
                    'if (!srcPic || !destPic)',
                    '{',
                    '    x265_log(m_parentEnc->m_param, X265_LOG_ERROR, "Missing scaler queue picture at src %u dst %d\\n", scaledWritten % QDepth, scaledWriteIdx);',
                    '}',
                    '}',
                    'void Reader::threadMain()',
                    '{',
                    'x265_picture* dest = m_parentEnc->m_parent->m_inputPicBuffer[m_id][writeIdx];',
                    'if (m_parentEnc->m_param->numViews > 1)',
                    '    dest = m_parentEnc->m_parent->m_inputPicBuffer[view][writeIdx];',
                    'if (!dest)',
                    '{',
                    '    x265_log(m_parentEnc->m_param, X265_LOG_ERROR, "Missing reader queue picture at view %d index %u\\n", view, writeIdx);',
                    '}',
                    'if (m_input[view]->readPicture(*src))',
                    '{',
                    '}',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'Scaler::threadMain must guard srcPic/destPic before scalePic()')
        expect_fail(run_checker(root), 'Scaler::threadMain must stop and surface scalePic() failures before advancing queue state')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/abrEncApp.cpp': '\n'.join((
                    'void Scaler::threadMain()',
                    '{',
                    'x265_picture *srcPic = m_parentEnc->m_parent->m_inputPicBuffer[srcId][scaledWritten % QDepth];',
                    'x265_picture* destPic = m_parentEnc->m_parent->m_inputPicBuffer[m_id][scaledWriteIdx];',
                    'if (!srcPic || !destPic)',
                    '{',
                    '    x265_log(m_parentEnc->m_param, X265_LOG_ERROR, "Missing scaler queue picture at src %u dst %d\\n", scaledWritten % QDepth, scaledWriteIdx);',
                    '}',
                    'if (!scalePic(destPic, srcPic))',
                    '{',
                    '}',
                    '}',
                    'x265_picture* dest = m_parentEnc->m_parent->m_inputPicBuffer[m_id][writeIdx];',
                    'if (m_parentEnc->m_param->numViews > 1)',
                    '    dest = m_parentEnc->m_parent->m_inputPicBuffer[view][writeIdx];',
                    'if (!dest)',
                    '{',
                    '    x265_log(m_parentEnc->m_param, X265_LOG_ERROR, "Missing reader queue picture at view %d index %u\\n", view, writeIdx);',
                    '}',
                    'if (m_input[view]->readPicture(*src))',
                    '{',
                    '}',
                    'void Reader::threadMain()',
                    '{',
                    '    something_else();',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'Reader::threadMain must select and guard dest before readPicture(*src)')

    print('ABR queue picture guard tests passed')


if __name__ == '__main__':
    main()
