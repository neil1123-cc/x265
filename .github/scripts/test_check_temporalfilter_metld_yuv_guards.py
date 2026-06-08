#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_temporalfilter_metld_yuv_guards.py')

# Coverage probes used by the scan for temporalfilter metld YUV guardrails.
NORMALIZED_PROBES = (
    'TemporalFilter::init must validate MotionEstimatorTLD YUV buffers before returning success and roll back m_metld on failure',
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
        'inline bool hasMotionEstimatorTLDBuffers(const MotionEstimatorTLD* metld)',
        '{',
        '    return metld && metld->me.fencPUYuv.m_buf[0] && metld->predPUYuv.m_buf[0];',
        '}',
        'bool TemporalFilter::init(const x265_param* param)',
        '{',
        '    m_metld = new (std::nothrow) MotionEstimatorTLD;',
        '    if (!hasMotionEstimatorTLDBuffers(m_metld))',
        '    {',
        '        delete m_metld;',
        '        m_metld = nullptr;',
        '        return false;',
        '    }',
        '    return true;',
        '}',
    )) + '\n'


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/common/temporalfilter.cpp': valid_text()})
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/common/temporalfilter.cpp': valid_text().replace('if (!hasMotionEstimatorTLDBuffers(m_metld))', 'if (!m_metld)', 1)})
        expect_fail(run_checker(root), 'missing temporalfilter metld YUV guardrail: if (!hasMotionEstimatorTLDBuffers(m_metld))')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/common/temporalfilter.cpp': valid_text().replace('return true;', 'return m_metld != nullptr;', 1)})
        expect_fail(run_checker(root), 'forbidden temporalfilter metld YUV regression: return m_metld != nullptr;')

    print('TemporalFilter MotionEstimatorTLD YUV guard tests passed')


if __name__ == '__main__':
    main()
