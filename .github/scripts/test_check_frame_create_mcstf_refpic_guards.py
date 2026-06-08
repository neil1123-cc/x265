#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_frame_create_mcstf_refpic_guards.py')

# Coverage probe used by the scan for MCSTF ref-pic guardrails.
NORMALIZED_PROBES = (
    'Frame::create must check TemporalFilter::createRefPicInfo() inside the MCSTF setup loop',
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
        'bool Frame::create(x265_param *param, float* quantOffsets)',
        '{',
        '    for (int i = 0; i < (m_mcstf->m_range << 1); i++)',
        '    {',
        '        if (!m_mcstf->createRefPicInfo(&m_mcstfRefList[i], m_param))',
        '            return false;',
        '    }',
        '    return true;',
        '}',
    )) + '\n'


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/common/frame.cpp': valid_text()})
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/common/frame.cpp': valid_text().replace('        if (!m_mcstf->createRefPicInfo(&m_mcstfRefList[i], m_param))\n            return false;\n', '        m_mcstf->createRefPicInfo(&m_mcstfRefList[i], m_param);\n', 1)})
        expect_fail(run_checker(root), 'forbidden frame create MCSTF refpic regression: ignored createRefPicInfo() result')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/common/frame.cpp': valid_text().replace('            return false;\n', '', 1)})
        expect_fail(run_checker(root), 'missing frame create MCSTF refpic guardrail: return false;')

    print('Frame::create MCSTF refpic guard tests passed')


if __name__ == '__main__':
    main()
