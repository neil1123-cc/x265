#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_abr_thread_analysis_read_guard.py')


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
                    'void PassEncoder::threadMain()',
                    '{',
                    'if (m_cliopt.loadLevel && picInput)',
                    '{',
                    '    if (m_lastIdx < 0 || !m_parent->m_analysisRead || !m_parent->m_analysisRead[m_cliopt.refId] ||',
                    '        !m_parent->m_analysisReadCnt)',
                    '    {',
                    '        x265_log(m_param, X265_LOG_ERROR, "Missing analysis read state for encoder %u\\n", m_id);',
                    '        goto fail;',
                    '    }',
                    '    m_parent->m_analysisReadCnt[m_cliopt.refId].incr();',
                    '    m_parent->m_analysisRead[m_cliopt.refId][m_lastIdx].incr();',
                    '}',
                    '}',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/abrEncApp.cpp': 'm_parent->m_analysisRead[m_cliopt.refId][m_lastIdx].incr();\n'})
        expect_fail(run_checker(root), 'missing ABR thread analysis-read guardrail: if (m_lastIdx < 0 || !m_parent->m_analysisRead || !m_parent->m_analysisRead[m_cliopt.refId] ||')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/abrEncApp.cpp': '\n'.join((
                    'void helper()',
                    '{',
                    'if (m_cliopt.loadLevel && picInput)',
                    '{',
                    '    if (m_lastIdx < 0 || !m_parent->m_analysisRead || !m_parent->m_analysisRead[m_cliopt.refId] ||',
                    '        !m_parent->m_analysisReadCnt)',
                    '    {',
                    '        x265_log(m_param, X265_LOG_ERROR, "Missing analysis read state for encoder %u\\n", m_id);',
                    '        goto fail;',
                    '    }',
                    '}',
                    '}',
                    'void PassEncoder::threadMain()',
                    '{',
                    'if (m_cliopt.loadLevel && picInput)',
                    '{',
                    '    m_parent->m_analysisReadCnt[m_cliopt.refId].incr();',
                    '    m_parent->m_analysisRead[m_cliopt.refId][m_lastIdx].incr();',
                    '}',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'PassEncoder::threadMain must guard analysis-read state before incrementing it')

    print('ABR thread analysis-read guard tests passed')


if __name__ == '__main__':
    main()
