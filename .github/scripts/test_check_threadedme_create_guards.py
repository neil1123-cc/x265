#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_threadedme_create_guards.py')

# Coverage probes used by the scan for ThreadedME create guardrails.
NORMALIZED_PROBES = (
    'ThreadedME::create must reject allocation/init failures and roll back partial thread-local state',
    'missing threadedME create cleanup guardrail: if (!m_threadedME->create())',
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


def valid_threadedme_text():
    return '\n'.join((
        'bool ThreadedME::create()',
        '{',
        '    m_tld = new (std::nothrow) ThreadLocalData[m_tldCount];',
        '    if (!m_tld)',
        '        return false;',
        '    if (!m_tld[i].analysis.initSearch(*m_param, m_enc.m_scalingList))',
        '    {',
        '        for (int j = 0; j <= i; j++)',
        '            m_tld[j].destroy();',
        '        delete[] m_tld;',
        '        m_tld = nullptr;',
        '        m_tldCount = 0;',
        '        return false;',
        '    }',
        '    if (!m_tld[i].analysis.create(m_tld))',
        '    {',
        '        for (int j = 0; j <= i; j++)',
            '            m_tld[j].destroy();',
        '        delete[] m_tld;',
        '        m_tld = nullptr;',
        '        m_tldCount = 0;',
        '        return false;',
        '    }',
        '}',
    )) + '\n'


def valid_encoder_text():
    return '\n'.join((
        'if (!m_threadedME->create())',
        '{',
        '    delete m_threadedME;',
        '    m_threadedME = nullptr;',
        '}',
    )) + '\n'


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/threadedme.cpp': valid_threadedme_text(),
                'source/encoder/encoder.cpp': valid_encoder_text(),
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/threadedme.cpp': valid_threadedme_text().replace(
                    '    m_tld = new (std::nothrow) ThreadLocalData[m_tldCount];\n',
                    '    m_tld = new ThreadLocalData[m_tldCount];\n',
                    1,
                ),
                'source/encoder/encoder.cpp': valid_encoder_text(),
            },
        )
        expect_fail(run_checker(root), 'missing ThreadedME create guardrail: m_tld = new (std::nothrow) ThreadLocalData[m_tldCount];')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/threadedme.cpp': valid_threadedme_text().replace(
                    '    if (!m_tld[i].analysis.initSearch(*m_param, m_enc.m_scalingList))\n'
                    '    {\n'
                    '        for (int j = 0; j <= i; j++)\n'
                    '            m_tld[j].destroy();\n'
                    '        delete[] m_tld;\n'
                    '        m_tld = nullptr;\n'
                    '        m_tldCount = 0;\n'
                    '        return false;\n'
                    '    }\n',
                    '    m_tld[i].analysis.initSearch(*m_param, m_enc.m_scalingList);\n',
                    1,
                ),
                'source/encoder/encoder.cpp': valid_encoder_text(),
            },
        )
        expect_fail(run_checker(root), 'missing ThreadedME create guardrail: if (!m_tld[i].analysis.initSearch(*m_param, m_enc.m_scalingList))')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/threadedme.cpp': valid_threadedme_text(),
                'source/encoder/encoder.cpp': valid_encoder_text().replace(
                    '    delete m_threadedME;\n',
                    '    X265_FREE(m_threadedME);\n',
                    1,
                ),
            },
        )
        expect_fail(run_checker(root), 'Encoder::create must delete failed ThreadedME instances with delete, not X265_FREE')

    print('ThreadedME create guard tests passed')


if __name__ == '__main__':
    main()
