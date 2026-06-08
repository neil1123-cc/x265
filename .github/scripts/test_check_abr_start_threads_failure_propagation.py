#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_abr_start_threads_failure_propagation.py')

# Coverage probes used by the scan for ABR startThreads failure propagation guardrails.
NORMALIZED_PROBES = (
    'AbrEncoder ctor must zero active encode count and return immediately after allocBuffers() failure',
    'AbrEncoder ctor must guard missing/failed dependency passes before starting later ABR threads',
    'PassEncoder::startThreads must handle pass, reader, and scaler start failures in order',
    'missing ABR startThreads failure propagation guardrail: ',
    'missing file',
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
                    'if (!allocBuffers())',
                    '{',
                    '    m_numActiveEncodes.set(0);',
                    '    ret = 4;',
                    '    return;',
                    '}',
                    'if (!m_passEnc[pass])',
                    '    continue;',
                    'if (m_passEnc[pass]->m_ret)',
                    '    continue;',
                    'if (usesAbrScalerMode(m_passEnc[pass]->m_cliopt, pass))',
                    '{',
                    '    PassEncoder *srcPass = m_passEnc[pass - 1];',
                    '    if (!srcPass || srcPass->m_ret)',
                    '    {',
                    '        m_numActiveEncodes.decr();',
                    '        continue;',
                    '    }',
                    '}',
                    'if (!m_passEnc[pass]->m_ret && !m_passEnc[pass]->startThreads() && !ret)',
                    '    ret = 4;',
                    'auto handleInputWorkerStartFailure = [&](const char* threadName, std::atomic<bool>& workerActive)',
                    '{',
                    '    workerActive.store(false);',
                    '    m_inputOver.store(true);',
                    '    m_parent->m_picWriteCnt[m_id].poke();',
                    '    return false;',
                    '};',
                    'if (!start())',
                    '{',
                    '    m_inputOver.store(true);',
                    '    m_parent->m_numActiveEncodes.decr();',
                    '    return false;',
                    '}',
                    'if (!m_reader->start())',
                    '    return handleInputWorkerStartFailure("reader", m_reader->m_threadActive);',
                    'if (!m_scaler->start())',
                    '    return handleInputWorkerStartFailure("scaler", m_scaler->m_threadActive);',
                )) + '\n',
                'source/abrEncApp.h': 'bool startThreads();\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/abrEncApp.cpp': 'if (!start())\n{\n    return false;\n}\n',
                'source/abrEncApp.h': 'void startThreads();\n',
            },
        )
        expect_fail(run_checker(root), 'missing ABR startThreads declaration guardrail: bool startThreads();')

    print('ABR startThreads failure propagation tests passed')


if __name__ == '__main__':
    main()
