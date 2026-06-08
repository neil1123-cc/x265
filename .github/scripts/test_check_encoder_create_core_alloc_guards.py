#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_encoder_create_core_alloc_guards.py')

# Coverage probes used by the scan for encoder core allocation guardrails.
NORMALIZED_PROBES = (
    'Encoder::create must reject Lookahead, DPB, RateControl, and zone counter allocation failures before use',
    'missing encoder create core alloc guardrail: ',
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
        'm_lookahead = new (std::nothrow) Lookahead(m_param, lookAheadThreadPool);',
        'if (!m_lookahead)',
        '{',
        '    x265_log(m_param, X265_LOG_ERROR, "Unable to allocate lookahead instance, aborting\\n");',
        '    m_aborted = true;',
        '    return;',
        '}',
        'm_dpb = new (std::nothrow) DPB(m_param);',
        'if (!m_dpb)',
        '{',
        '    x265_log(m_param, X265_LOG_ERROR, "Unable to allocate DPB instance, aborting\\n");',
        '    m_aborted = true;',
        '    return;',
        '}',
        'm_rateControl = new (std::nothrow) RateControl(*m_param, this);',
        'if (!m_rateControl)',
        '{',
        '    x265_log(m_param, X265_LOG_ERROR, "Unable to allocate rate-control instance, aborting\\n");',
        '    m_aborted = true;',
        '    return;',
        '}',
        'zoneReadCount = new (std::nothrow) ThreadSafeInteger[m_param->rc.zonefileCount];',
        'if (!zoneReadCount)',
        '{',
        '    x265_log(m_param, X265_LOG_ERROR, "Unable to allocate zone-read counters, aborting\\n");',
        '    m_aborted = true;',
        '    return;',
        '}',
        'zoneWriteCount = new (std::nothrow) ThreadSafeInteger[m_param->rc.zonefileCount];',
        'if (!zoneWriteCount)',
        '{',
        '    x265_log(m_param, X265_LOG_ERROR, "Unable to allocate zone-write counters, aborting\\n");',
        '    m_aborted = true;',
        '    return;',
        '}',
    )) + '\n'


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/encoder/encoder.cpp': valid_text()})
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/encoder/encoder.cpp': valid_text().replace('m_lookahead = new (std::nothrow) Lookahead(m_param, lookAheadThreadPool);\n', 'm_lookahead = new Lookahead(m_param, lookAheadThreadPool);\n', 1)})
        expect_fail(run_checker(root), 'forbidden encoder create core alloc regression: m_lookahead = new Lookahead(m_param, lookAheadThreadPool);')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/encoder/encoder.cpp': valid_text().replace('m_dpb = new (std::nothrow) DPB(m_param);\n', 'm_dpb = new DPB(m_param);\n', 1)})
        expect_fail(run_checker(root), 'forbidden encoder create core alloc regression: m_dpb = new DPB(m_param);')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/encoder/encoder.cpp': valid_text().replace('zoneWriteCount = new (std::nothrow) ThreadSafeInteger[m_param->rc.zonefileCount];\n', 'zoneWriteCount = new ThreadSafeInteger[m_param->rc.zonefileCount];\n', 1)})
        expect_fail(run_checker(root), 'forbidden encoder create core alloc regression: zoneWriteCount = new ThreadSafeInteger[m_param->rc.zonefileCount];')

    print('Encoder::create core allocation guard tests passed')


if __name__ == '__main__':
    main()
