#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_temporalfilter_refpic_state_init.py')

# Coverage probes used by the scan for temporalfilter refpic state-init guardrails.
NORMALIZED_PROBES = (
    'missing file',
    'Frame::Frame must initialize the MCSTF refpic array before MCSTF teardown can observe partially created entries',
    'resetRefPicInfoState() must restore all non-owned refpic state fields before rollback or destroy paths run',
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


def valid_repo():
    return {
        'source/common/frame.cpp': 'Frame::Frame()\n{\n    // mcstf\n    std::fill_n(m_mcstfRefList, MAX_MCSTF_TEMPORAL_WINDOW_LENGTH, TemporalFilterRefPicInfo());\n}\n',
        'source/common/temporalfilter.cpp': '\n'.join((
            'void resetRefPicInfoState(TemporalFilterRefPicInfo* refFrame)',
            '{',
            '    refFrame->picBuffer = nullptr;',
            '    refFrame->picBufferSubSampled2 = nullptr;',
            '    refFrame->picBufferSubSampled4 = nullptr;',
            '    refFrame->poc = 0;',
            '    refFrame->lowres = nullptr;',
            '    refFrame->lowerRes = nullptr;',
            '    refFrame->origOffset = 0;',
            '    refFrame->isFilteredFrame = false;',
            '    refFrame->isSubsampled = nullptr;',
            '    refFrame->slicetype = X265_TYPE_AUTO;',
            '}',
        )) + '\n',
    }


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, valid_repo())
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        repo = valid_repo()
        repo['source/common/frame.cpp'] = repo['source/common/frame.cpp'].replace('std::fill_n(m_mcstfRefList, MAX_MCSTF_TEMPORAL_WINDOW_LENGTH, TemporalFilterRefPicInfo());', '', 1)
        write_targets(root, repo)
        expect_fail(run_checker(root), 'missing temporalfilter refpic state-init guardrail: std::fill_n(m_mcstfRefList, MAX_MCSTF_TEMPORAL_WINDOW_LENGTH, TemporalFilterRefPicInfo());')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        repo = valid_repo()
        repo['source/common/temporalfilter.cpp'] = repo['source/common/temporalfilter.cpp'].replace('    refFrame->isSubsampled = nullptr;\n', '', 1)
        write_targets(root, repo)
        expect_fail(run_checker(root), 'missing temporalfilter refpic state-init guardrail: refFrame->isSubsampled = nullptr;')

    print('Temporalfilter refpic state-init tests passed')


if __name__ == '__main__':
    main()
