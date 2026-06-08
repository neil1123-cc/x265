#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_abr_copyinfo_intra_arrays_guard.py')

# Coverage probe used by the scan for the reviewed copyInfo array guards.
NORMALIZED_PROBES = (
    'PassEncoder::copyInfo must guard intra/inter analysis arrays before memcpy into them',
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
                    'copyIntraAnalysis(m_analysisInfo, src)',
                    'if (!interDst->depth || !interSrc->depth || !interDst->modes || !interSrc->modes)',
                    '{',
                    '    x265_log(m_param, X265_LOG_ERROR, "Missing inter analysis array buffers for encoder %u\\n", m_id);',
                    '}',
                    'x265_log(m_param, X265_LOG_ERROR, "Missing inter cuTree analysis buffers for encoder %u\\n", m_id);',
                    'x265_log(m_param, X265_LOG_ERROR, "Missing intra-in-inter analysis arrays for encoder %u\\n", m_id);',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/abrEncApp.cpp': '\n'.join((
                    'copyIntraAnalysis(m_analysisInfo, src)',
                    'x265_log(m_param, X265_LOG_ERROR, "Missing inter cuTree analysis buffers for encoder %u\\n", m_id);',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'missing ABR copyInfo intra-array guardrail: if (!interDst->depth || !interSrc->depth || !interDst->modes || !interSrc->modes)')

    print('ABR copyInfo intra-array guard tests passed')


if __name__ == '__main__':
    main()
