#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_abr_thread_queue_state_guards.py')

# Coverage probe used by the scan for the reviewed ABR input queue state guard.
NORMALIZED_PROBES = (
    'Reader::threadMain must guard m_input[view] before readPicture(*src)',
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
                'source/abrEncApp.cpp': '\n'.join((
                    'void Scaler::threadMain()',
                    '{',
                    'if (!m_parentEnc || !m_parentEnc->m_parent || !m_parentEnc->m_parent->m_picWriteCnt ||',
                    '    !m_parentEnc->m_parent->m_picIdxReadCnt || !m_parentEnc->m_parent->m_picIdxReadCnt[m_id] ||',
                    '    !m_parentEnc->m_parent->m_picIdxReadCnt[srcId] ||',
                    '    !m_parentEnc->m_parent->m_inputPicBuffer || !m_parentEnc->m_parent->m_inputPicBuffer[m_id] ||',
                    '    !m_parentEnc->m_parent->m_inputPicBuffer[srcId])',
                    '{',
                    '    x265_log(m_parentEnc ? m_parentEnc->m_param : nullptr, X265_LOG_ERROR, "Missing scaler queue state for layer %d\\n", m_id);',
                    '}',
                    'int QDepth = m_parentEnc->m_parent->m_queueSize;',
                    '}',
                    'void Reader::threadMain()',
                    '{',
                    'if (!m_parentEnc || !m_parentEnc->m_parent || !m_parentEnc->m_parent->m_picWriteCnt ||',
                    '    !m_parentEnc->m_parent->m_picIdxReadCnt || !m_parentEnc->m_parent->m_picIdxReadCnt[m_id] ||',
                    '    !m_parentEnc->m_parent->m_inputPicBuffer)',
                    '{',
                    'x265_log(m_parentEnc ? m_parentEnc->m_param : nullptr, X265_LOG_ERROR, "Missing reader queue state for layer %d\\n", m_id);',
                    '}',
                    'int QDepth = m_parentEnc->m_parent->m_queueSize;',
                    'if (!m_input[view])',
                    '{',
                    '    x265_log(m_parentEnc->m_param, X265_LOG_ERROR, "Missing reader input state for view %d\\n", view);',
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
        write_targets(root, {'source/abrEncApp.cpp': 'if (m_input[view]->readPicture(*src))\n{\n}\n'})
        expect_fail(run_checker(root), 'missing ABR thread queue-state guardrail: if (!m_parentEnc || !m_parentEnc->m_parent || !m_parentEnc->m_parent->m_picWriteCnt ||')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/abrEncApp.cpp': '\n'.join((
                    'void helper()',
                    '{',
                    'if (!m_parentEnc || !m_parentEnc->m_parent || !m_parentEnc->m_parent->m_picWriteCnt ||',
                    '    !m_parentEnc->m_parent->m_picIdxReadCnt || !m_parentEnc->m_parent->m_picIdxReadCnt[m_id] ||',
                    '    !m_parentEnc->m_parent->m_picIdxReadCnt[srcId] ||',
                    '    !m_parentEnc->m_parent->m_inputPicBuffer || !m_parentEnc->m_parent->m_inputPicBuffer[m_id] ||',
                    '    !m_parentEnc->m_parent->m_inputPicBuffer[srcId])',
                    '{',
                    '    x265_log(m_parentEnc ? m_parentEnc->m_param : nullptr, X265_LOG_ERROR, "Missing scaler queue state for layer %d\\n", m_id);',
                    '}',
                    '}',
                    'void Scaler::threadMain()',
                    '{',
                    'int QDepth = m_parentEnc->m_parent->m_queueSize;',
                    '}',
                    'void Reader::threadMain()',
                    '{',
                    'if (!m_parentEnc || !m_parentEnc->m_parent || !m_parentEnc->m_parent->m_picWriteCnt ||',
                    '    !m_parentEnc->m_parent->m_picIdxReadCnt || !m_parentEnc->m_parent->m_picIdxReadCnt[m_id] ||',
                    '    !m_parentEnc->m_parent->m_inputPicBuffer)',
                    '{',
                    '    x265_log(m_parentEnc ? m_parentEnc->m_param : nullptr, X265_LOG_ERROR, "Missing reader queue state for layer %d\\n", m_id);',
                    '}',
                    'int QDepth = m_parentEnc->m_parent->m_queueSize;',
                    'if (!m_input[view])',
                    '{',
                    '    x265_log(m_parentEnc->m_param, X265_LOG_ERROR, "Missing reader input state for view %d\\n", view);',
                    '}',
                    'if (m_input[view]->readPicture(*src))',
                    '{',
                    '}',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'Scaler::threadMain must guard queue state before reading QDepth')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/abrEncApp.cpp': '\n'.join((
                    'void Scaler::threadMain()',
                    '{',
                    'if (!m_parentEnc || !m_parentEnc->m_parent || !m_parentEnc->m_parent->m_picWriteCnt ||',
                    '    !m_parentEnc->m_parent->m_picIdxReadCnt || !m_parentEnc->m_parent->m_picIdxReadCnt[m_id] ||',
                    '    !m_parentEnc->m_parent->m_picIdxReadCnt[srcId] ||',
                    '    !m_parentEnc->m_parent->m_inputPicBuffer || !m_parentEnc->m_parent->m_inputPicBuffer[m_id] ||',
                    '    !m_parentEnc->m_parent->m_inputPicBuffer[srcId])',
                    '{',
                    '    x265_log(m_parentEnc ? m_parentEnc->m_param : nullptr, X265_LOG_ERROR, "Missing scaler queue state for layer %d\\n", m_id);',
                    '}',
                    'int QDepth = m_parentEnc->m_parent->m_queueSize;',
                    '}',
                    'if (!m_parentEnc || !m_parentEnc->m_parent || !m_parentEnc->m_parent->m_picWriteCnt ||',
                    '    !m_parentEnc->m_parent->m_picIdxReadCnt || !m_parentEnc->m_parent->m_picIdxReadCnt[m_id] ||',
                    '    !m_parentEnc->m_parent->m_inputPicBuffer)',
                    '{',
                    '    x265_log(m_parentEnc ? m_parentEnc->m_param : nullptr, X265_LOG_ERROR, "Missing reader queue state for layer %d\\n", m_id);',
                    '}',
                    'void Reader::threadMain()',
                    '{',
                    'int QDepth = m_parentEnc->m_parent->m_queueSize;',
                    'if (!m_input[view])',
                    '{',
                    '    x265_log(m_parentEnc->m_param, X265_LOG_ERROR, "Missing reader input state for view %d\\n", view);',
                    '}',
                    'if (m_input[view]->readPicture(*src))',
                    '{',
                    '}',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'Reader::threadMain must guard queue state before reading QDepth')

    print('ABR thread queue-state guard tests passed')


if __name__ == '__main__':
    main()
