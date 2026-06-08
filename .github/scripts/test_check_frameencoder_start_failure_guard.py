#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_frameencoder_start_failure_guard.py')

# Coverage probes used by the scan for frame-encoder startup failure guardrails.
NORMALIZED_PROBES = (
    'Encoder::create must abort and break out of frame encoder startup before waiting on m_done',
    'Encoder::create must abort after thread initialization failures before continuing encoder startup',
    'FrameEncoder::threadMain must guard thread-local allocation, initSearch, and analysis.create before signaling startup completion',
    'missing frame encoder thread init guardrail: ',
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
                'source/encoder/encoder.cpp': '\n'.join((
                    'if (!m_frameEncoder[i]->start())',
                    '{',
                    '    x265_log(m_param, X265_LOG_ERROR, "Unable to start frame encoder thread %d, aborting\\n", i);',
                    '    m_frameEncoder[i]->m_threadActive.store(false);',
                    '    m_aborted = true;',
                    '    break;',
                    '}',
                    'm_frameEncoder[i]->m_done.wait(); /* wait for thread to initialize */',
                    'if (!m_frameEncoder[i]->m_threadActive.load())',
                    '{',
                    '    x265_log(m_param, X265_LOG_ERROR, "Unable to initialize frame encoder thread %d, aborting\\n", i);',
                    '    m_aborted = true;',
                    '    break;',
                    '}',
                    'if (m_aborted)',
                    '    return;',
                )) + '\n',
                'source/encoder/frameencoder.cpp': '\n'.join((
                    'void FrameEncoder::threadMain()',
                    '{',
                    '    auto failThreadInit = [&](const char* message)',
                    '    {',
                    '        m_threadActive.store(false);',
                    '        m_done.trigger();',
                    '    };',
                    '    m_tld = new (std::nothrow) ThreadLocalData[numTLD];',
                    '    if (!m_tld)',
                    '    {',
                    '        failThreadInit("Unable to allocate frame encoder thread-local state\\n");',
                    '        return;',
                    '    }',
                    '    if (!m_tld[i].analysis.initSearch(*m_param, m_top->m_scalingList))',
                    '    {',
                    '        failThreadInit("Unable to allocate frame encoder search state\\n");',
                    '        return;',
                    '    }',
                    '    if (!m_tld[i].analysis.create(m_tld))',
                    '    {',
                    '        failThreadInit("Unable to allocate frame encoder analysis state\\n");',
                    '        return;',
                    '    }',
                    '    m_tld = new (std::nothrow) ThreadLocalData;',
                    '    if (!m_tld->analysis.initSearch(*m_param, m_top->m_scalingList))',
                    '    {',
                    '        failThreadInit("Unable to allocate frame encoder search state\\n");',
                    '        return;',
                    '    }',
                    '    if (!m_tld->analysis.create(nullptr))',
                    '    {',
                    '        failThreadInit("Unable to allocate frame encoder analysis state\\n");',
                    '        return;',
                    '    }',
                    '    m_done.trigger();     /* signal that thread is initialized */',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/encoder.cpp': 'm_frameEncoder[i]->start();\nm_frameEncoder[i]->m_done.wait(); /* wait for thread to initialize */\n',
                'source/encoder/frameencoder.cpp': 'void FrameEncoder::threadMain()\n{\n    m_done.trigger();     /* signal that thread is initialized */\n}\n',
            },
        )
        expect_fail(run_checker(root), 'missing frame encoder start failure guardrail: if (!m_frameEncoder[i]->start())')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/encoder.cpp': '\n'.join((
                    'if (!m_frameEncoder[i]->start())',
                    '{',
                    '    x265_log(m_param, X265_LOG_ERROR, "Unable to start frame encoder thread %d, aborting\\n", i);',
                    '    m_frameEncoder[i]->m_threadActive.store(false);',
                    '    m_aborted = true;',
                    '    break;',
                    '}',
                    'm_frameEncoder[i]->m_done.wait(); /* wait for thread to initialize */',
                    'if (!m_frameEncoder[i]->m_threadActive.load())',
                    '{',
                    '    x265_log(m_param, X265_LOG_ERROR, "Unable to initialize frame encoder thread %d, aborting\\n", i);',
                    '    m_aborted = true;',
                    '    break;',
                    '}',
                )) + '\n',
                'source/encoder/frameencoder.cpp': '\n'.join((
                    'void FrameEncoder::threadMain()',
                    '{',
                    '    auto failThreadInit = [&](const char* message)',
                    '    {',
                    '        m_threadActive.store(false);',
                    '        m_done.trigger();',
                    '    };',
                    '    m_tld = new (std::nothrow) ThreadLocalData[numTLD];',
                    '    if (!m_tld)',
                    '    {',
                    '        failThreadInit("Unable to allocate frame encoder thread-local state\\n");',
                    '        return;',
                    '    }',
                    '    if (!m_tld[i].analysis.initSearch(*m_param, m_top->m_scalingList))',
                    '    {',
                    '        failThreadInit("Unable to allocate frame encoder search state\\n");',
                    '        return;',
                    '    }',
                    '    if (!m_tld[i].analysis.create(m_tld))',
                    '    {',
                    '        failThreadInit("Unable to allocate frame encoder analysis state\\n");',
                    '        return;',
                    '    }',
                    '    m_tld = new (std::nothrow) ThreadLocalData;',
                    '    if (!m_tld->analysis.initSearch(*m_param, m_top->m_scalingList))',
                    '    {',
                    '        failThreadInit("Unable to allocate frame encoder search state\\n");',
                    '        return;',
                    '    }',
                    '    if (!m_tld->analysis.create(nullptr))',
                    '    {',
                    '        failThreadInit("Unable to allocate frame encoder analysis state\\n");',
                    '        return;',
                    '    }',
                    '    m_done.trigger();     /* signal that thread is initialized */',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'missing frame encoder start failure guardrail: if (m_aborted)')

    print('Frame encoder start failure guard tests passed')


if __name__ == '__main__':
    main()
