#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_temporalfilter_alloc_counts.py')

# Coverage probes used by the scan for temporalfilter allocation-count guardrails.
NORMALIZED_PROBES = (
    'TemporalFilter::createRefPicInfo must allocate MV and error buffers using element counts, not byte counts',
    'missing temporalfilter allocation-count guardrail: ',
    'forbidden temporalfilter allocation-count regression: ',
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
        'int TemporalFilter::createRefPicInfo(TemporalFilterRefPicInfo* refFrame, x265_param* param)',
        '{',
        '    CHECKED_MALLOC_ZERO(refFrame->mvs, MV, ((m_sourceWidth ) / 4) * ((m_sourceHeight ) / 4));',
        '    CHECKED_MALLOC_ZERO(refFrame->mvs0, MV, ((m_sourceWidth ) / 16) * ((m_sourceHeight ) / 16));',
        '    CHECKED_MALLOC_ZERO(refFrame->mvs1, MV, ((m_sourceWidth ) / 16) * ((m_sourceHeight ) / 16));',
        '    CHECKED_MALLOC_ZERO(refFrame->mvs2, MV, ((m_sourceWidth ) / 16) * ((m_sourceHeight ) / 16));',
        '    CHECKED_MALLOC_ZERO(refFrame->noise, int, ((m_sourceWidth) / 4) * ((m_sourceHeight) / 4));',
        '    CHECKED_MALLOC_ZERO(refFrame->error, int, ((m_sourceWidth) / 4) * ((m_sourceHeight) / 4));',
        '}',
    )) + '\n'


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/common/temporalfilter.cpp': valid_text()})
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/temporalfilter.cpp': valid_text().replace(
                    'CHECKED_MALLOC_ZERO(refFrame->mvs, MV, ((m_sourceWidth ) / 4) * ((m_sourceHeight ) / 4));',
                    'CHECKED_MALLOC_ZERO(refFrame->mvs, MV, sizeof(MV)* ((m_sourceWidth ) / 4) * ((m_sourceHeight ) / 4));',
                    1,
                ),
            },
        )
        expect_fail(run_checker(root), 'forbidden temporalfilter allocation-count regression')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/temporalfilter.cpp': valid_text().replace(
                    'CHECKED_MALLOC_ZERO(refFrame->noise, int, ((m_sourceWidth) / 4) * ((m_sourceHeight) / 4));',
                    'CHECKED_MALLOC_ZERO(refFrame->noise, int, sizeof(int) * ((m_sourceWidth) / 4) * ((m_sourceHeight) / 4));',
                    1,
                ),
            },
        )
        expect_fail(run_checker(root), 'forbidden temporalfilter allocation-count regression')

    print('Temporalfilter allocation-count tests passed')


if __name__ == '__main__':
    main()
