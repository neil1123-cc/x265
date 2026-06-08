#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_encoder_create_object_alloc_guards.py')

# Coverage probe used by the scan for the reviewed encoder object allocation guards.
NORMALIZED_PROBES = (
    'Encoder::create must reject FrameEncoder and ThreadedME allocation failures before using those objects',
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


def valid_text():
    return '\n'.join((
        'for (int i = 0; i < m_param->frameNumThreads; i++)',
        '{',
        '    m_frameEncoder[i] = new (std::nothrow) FrameEncoder;',
        '    if (!m_frameEncoder[i])',
        '    {',
        '        x265_log(m_param, X265_LOG_ERROR, "Unable to allocate frame encoder %d, aborting\\n", i);',
        '        m_aborted = true;',
        '        break;',
        '    }',
        '    m_frameEncoder[i]->m_nalList.m_annexB = m_param->bAnnexB != 0;',
        '}',
        'if (m_aborted)',
        '    return;',
        'if (p->bThreadedME)',
        '{',
        '    m_threadedME = new (std::nothrow) ThreadedME(m_param, *this);',
        '    if (!m_threadedME)',
        '    {',
        '        x265_log(m_param, X265_LOG_ERROR, "Unable to allocate ThreadedME instance, aborting\\n");',
        '        m_aborted = true;',
        '        return;',
        '    }',
        '}',
    )) + '\n'


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/encoder/encoder.cpp': valid_text()})
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/encoder/encoder.cpp': valid_text().replace('    m_frameEncoder[i] = new (std::nothrow) FrameEncoder;\n', '    m_frameEncoder[i] = new FrameEncoder;\n', 1)})
        expect_fail(run_checker(root), 'forbidden encoder create object alloc regression: m_frameEncoder[i] = new FrameEncoder;')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/encoder/encoder.cpp': valid_text().replace('if (m_aborted)\n    return;\n', '', 1)})
        expect_fail(run_checker(root), 'missing encoder create object alloc guardrail: if (m_aborted)')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/encoder/encoder.cpp': valid_text().replace('    m_threadedME = new (std::nothrow) ThreadedME(m_param, *this);\n', '    m_threadedME = new ThreadedME(m_param, *this);\n', 1)})
        expect_fail(run_checker(root), 'forbidden encoder create object alloc regression: m_threadedME = new ThreadedME(m_param, *this);')

    print('Encoder::create object allocation guard tests passed')


if __name__ == '__main__':
    main()
