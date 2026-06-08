#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_abr_copyinfo_vbv_lookahead_guard.py')

# Coverage probe used by the scan for the reviewed copyInfo VBV lookahead guards.
NORMALIZED_PROBES = (
    'PassEncoder::copyInfo must guard VBV lookahead buffers before copying them',
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
                    'if (m_param->bDisableLookahead && isVbv)',
                    '{',
                    '    if (!m_analysisInfo->lookahead.intraSatdForVbv || !src->lookahead.intraSatdForVbv ||',
                    '        !m_analysisInfo->lookahead.satdForVbv || !src->lookahead.satdForVbv ||',
                    '        !m_analysisInfo->lookahead.intraVbvCost || !src->lookahead.intraVbvCost ||',
                    '        !m_analysisInfo->lookahead.vbvCost || !src->lookahead.vbvCost)',
                    '    {',
                    '        x265_log(m_param, X265_LOG_ERROR, "Missing VBV lookahead analysis buffers for encoder %u\\n", m_id);',
                    '    }',
                    '    std::memcpy(m_analysisInfo->lookahead.intraSatdForVbv, src->lookahead.intraSatdForVbv, src->numCuInHeight * sizeof(uint32_t));',
                    '    std::memcpy(m_analysisInfo->lookahead.vbvCost, src->lookahead.vbvCost, src->numCUsInFrame * sizeof(uint32_t));',
                    '}',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/abrEncApp.cpp': 'if (m_param->bDisableLookahead && isVbv)\n{\n}\n'})
        expect_fail(run_checker(root), 'missing ABR copyInfo VBV lookahead guardrail: if (!m_analysisInfo->lookahead.intraSatdForVbv || !src->lookahead.intraSatdForVbv ||')

    print('ABR copyInfo VBV lookahead guard tests passed')


if __name__ == '__main__':
    main()
