#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_abr_picture_state_guards.py')


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
                    'bool PassEncoder::readPicture(x265_picture* dstPic, int view)',
                    '{',
                    'if (!m_parent->m_inputPicBuffer || (m_param->numViews > 1 && !m_parent->m_inputPicBuffer[view]) ||',
                    '    (m_param->numViews <= 1 && !m_parent->m_inputPicBuffer[m_id]))',
                    '{',
                    '    x265_log(m_param, X265_LOG_ERROR, "Missing input queue state for encoder %u view %d\\n", m_id, view);',
                    '}',
                    'x265_picture* srcPic = (m_param->numViews > 1) ? (x265_picture*)(m_parent->m_inputPicBuffer[view][readPos]) : (x265_picture*)(m_parent->m_inputPicBuffer[m_id][readPos]);',
                    'if (!srcPic)',
                    '{',
                    '    x265_log(m_param, X265_LOG_ERROR, "Missing input picture at queue position %d for view %d\\n", readPos, view);',
                    '}',
                    'x265_picture* pic = dstPic;',
                    'copyInputPictureState(pic, srcPic);',
                    '}',
                    'void PassEncoder::threadMain()',
                    '{',
                    'if (!m_parent->m_param)',
                    '{',
                    '    x265_log(m_param, X265_LOG_ERROR, "Missing parent parameter cache for encoder %u\\n", m_id);',
                    '}',
                    'std::memcpy(&m_parent->m_param[m_id], m_param, sizeof(x265_param));',
                    '}',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/abrEncApp.cpp': 'std::memcpy(&m_parent->m_param[m_id], m_param, sizeof(x265_param));\n'})
        expect_fail(run_checker(root), 'missing ABR picture-state guardrail: if (!m_parent->m_inputPicBuffer || (m_param->numViews > 1 && !m_parent->m_inputPicBuffer[view]) ||')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/abrEncApp.cpp': '\n'.join((
                    'bool PassEncoder::readPicture(x265_picture* dstPic, int view)',
                    '{',
                    'if (!m_parent->m_inputPicBuffer || (m_param->numViews > 1 && !m_parent->m_inputPicBuffer[view]) ||',
                    '    (m_param->numViews <= 1 && !m_parent->m_inputPicBuffer[m_id]))',
                    '{',
                    '    x265_log(m_param, X265_LOG_ERROR, "Missing input queue state for encoder %u view %d\\n", m_id, view);',
                    '}',
                    'x265_picture* srcPic = (m_param->numViews > 1) ? (x265_picture*)(m_parent->m_inputPicBuffer[view][readPos]) : (x265_picture*)(m_parent->m_inputPicBuffer[m_id][readPos]);',
                    'if (!srcPic)',
                    '{',
                    '    x265_log(m_param, X265_LOG_ERROR, "Missing input picture at queue position %d for view %d\\n", readPos, view);',
                    '}',
                    'x265_picture* pic = dstPic;',
                    'if (!m_parent->m_param)',
                    '{',
                    '    x265_log(m_param, X265_LOG_ERROR, "Missing parent parameter cache for encoder %u\\n", m_id);',
                    '}',
                    'std::memcpy(&m_parent->m_param[m_id], m_param, sizeof(x265_param));',
                    'copyInputPictureState(pic, srcPic);',
                    '}',
                    'void PassEncoder::threadMain()',
                    '{',
                    '    something_else();',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'PassEncoder::threadMain must guard parent parameter cache before memcpy into shared state')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/abrEncApp.cpp': '\n'.join((
                    'void helper()',
                    '{',
                    'if (!m_parent->m_inputPicBuffer || (m_param->numViews > 1 && !m_parent->m_inputPicBuffer[view]) ||',
                    '    (m_param->numViews <= 1 && !m_parent->m_inputPicBuffer[m_id]))',
                    '{',
                    '    x265_log(m_param, X265_LOG_ERROR, "Missing input queue state for encoder %u view %d\\n", m_id, view);',
                    '}',
                    '}',
                    'bool PassEncoder::readPicture(x265_picture* dstPic, int view)',
                    '{',
                    'x265_picture* srcPic = (m_param->numViews > 1) ? (x265_picture*)(m_parent->m_inputPicBuffer[view][readPos]) : (x265_picture*)(m_parent->m_inputPicBuffer[m_id][readPos]);',
                    'if (!srcPic)',
                    '{',
                    '    x265_log(m_param, X265_LOG_ERROR, "Missing input picture at queue position %d for view %d\\n", readPos, view);',
                    '}',
                    'x265_picture* pic = dstPic;',
                    'copyInputPictureState(pic, srcPic);',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'PassEncoder::readPicture must guard shared input queue state before dereferencing and copying srcPic')

    print('ABR picture-state guard tests passed')


if __name__ == '__main__':
    main()
