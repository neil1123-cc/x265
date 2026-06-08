#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_encoder_get_stats_size_guard.py')

# Coverage probes used by the scan for encoder_get_stats size guardrails.
NORMALIZED_PROBES = (
    'forbidden encoder_get_stats size regression: ',
    'missing encoder_get_stats size guardrail: ',
    'fetchStats must not touch stats fields before the sizeof(*stats) guard is checked',
    'fetchStats size-guard block could not be validated',
    'fetchStats must keep every stats field access inside the sizeof(*stats) compatibility guard',
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
                'source/encoder/encoder.cpp': '\n'.join((
                    'void Encoder::fetchStats(x265_stats *stats, size_t statsSizeBytes, int layer)',
                    '{',
                    '    if (statsSizeBytes >= sizeof(*stats))',
                    '    {',
                    '        stats->globalPsnrY = m_analyzeAll[layer].m_psnrSumY;',
                    '        if (stats->encodedPictureCount > 0)',
                    '        {',
                    '        }',
                    '        stats->statsI.numPics = m_analyzeI[layer].m_numPics;',
                    '        if (m_param->csvLogLevel >= 2 || m_param->maxCLL || m_param->maxFALL)',
                    '        {',
                    '        }',
                    '    }',
                    '    /* If new statistics are added to x265_stats, we must check here whether the',
                    '}',
                    'void Encoder::finishFrameStats(Frame* curFrame, FrameEncoder *curEncoder, x265_frame_stats* frameStats, int inPoc, int layer)',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/encoder.cpp': '\n'.join((
                    'void Encoder::fetchStats(x265_stats *stats, size_t statsSizeBytes, int layer)',
                    '{',
                    '    if (statsSizeBytes >= sizeof(stats))',
                    '    {',
                    '        stats->globalPsnrY = m_analyzeAll[layer].m_psnrSumY;',
                    '    }',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden encoder_get_stats size regression')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/encoder.cpp': '\n'.join((
                    'void Encoder::fetchStats(x265_stats *stats, size_t statsSizeBytes, int layer)',
                    '{',
                    '    stats->globalPsnrY = m_analyzeAll[layer].m_psnrSumY;',
                    '    if (statsSizeBytes >= sizeof(*stats))',
                    '    {',
                    '        if (stats->encodedPictureCount > 0)',
                    '        {',
                    '        }',
                    '        stats->statsI.numPics = m_analyzeI[layer].m_numPics;',
                    '        if (m_param->csvLogLevel >= 2 || m_param->maxCLL || m_param->maxFALL)',
                    '        {',
                    '        }',
                    '    }',
                    '    /* If new statistics are added to x265_stats, we must check here whether the',
                    '}',
                    'void Encoder::finishFrameStats(Frame* curFrame, FrameEncoder *curEncoder, x265_frame_stats* frameStats, int inPoc, int layer)',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'fetchStats must guard x265_stats writes with sizeof(*stats) before populating the aggregate and per-slice statistics')

    print('Encoder get stats size guard tests passed')


if __name__ == '__main__':
    main()
