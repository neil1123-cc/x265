#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_gop_lookahead_usage_safety.py')

# Coverage probes used by the scan for gop-lookahead usage guardrails.
NORMALIZED_PROBES = (
    'forbidden gop-lookahead usage regression: ',
    'missing gop-lookahead usage guardrail: ',
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
                'source/encoder/slicetype.cpp': '\n'.join((
                    'int keyFrameLimit = keylimit + m_lastKeyframe - frames[0]->frameNum - 1;',
                    'if (m_param->gopLookahead > 0 && keyFrameLimit <= m_param->bframes + 1)',
                    'keyintLimit = X265_MAX(0, keyintLimit);',
                    'if (m_param->gopLookahead > 0 && (keyFrameLimit >= 0) && (keyFrameLimit <= m_param->bframes + 1))',
                    'if (m_param->gopLookahead > 0 && (keyFrameLimit >= 0) && (keyFrameLimit <= m_param->bframes + 1) && !m_extendGopBoundary)',
                    'if (!m_param->bIntraRefresh)',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/slicetype.cpp': 'if (m_param->gopLookahead && keyFrameLimit <= m_param->bframes + 1)\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden gop-lookahead usage regression')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/slicetype.cpp': '\n'.join((
                    'int keyFrameLimit = keylimit + m_lastKeyframe - frames[0]->frameNum - 1;',
                    'if (m_param->gopLookahead > 0 && (keyFrameLimit >= 0) && (keyFrameLimit <= m_param->bframes + 1) && !m_extendGopBoundary)',
                    'keyintLimit = X265_MAX(0, keyintLimit);',
                    'if (m_param->gopLookahead > 0 && keyFrameLimit <= m_param->bframes + 1)',
                    'if (m_param->gopLookahead > 0 && (keyFrameLimit >= 0) && (keyFrameLimit <= m_param->bframes + 1))',
                    'if (!m_param->bIntraRefresh)',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'GOP lookahead usage must preserve the reviewed keyFrameLimit gating order around keyintLimit extension and boundary reset')

    print('GOP lookahead usage safety tests passed')


if __name__ == '__main__':
    main()
