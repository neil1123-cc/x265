#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_no_reset_zone_prefill_guard.py')

# Coverage probes used by the scan for no-reset zone prefill guardrails.
NORMALIZED_PROBES = (
    'missing no-reset zone prefill guardrail: ',
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
                'source/encoder/slicetype.h': 'class Lookahead {\npublic:\n    Frame*  peekDecidedPicture();\n};\n',
                'source/encoder/slicetype.cpp': '\n'.join((
                    'Frame* Lookahead::peekDecidedPicture()',
                    '{',
                    '    m_outputLock.acquire();',
                    '    Frame* out = m_outputQueue.first();',
                    '    m_outputLock.release();',
                    '    if (out)',
                    '        return out;',
                    '    findJob(-1); /* run slicetypeDecide() if necessary */',
                    '    m_inputLock.acquire();',
                    '    bool wait = m_outputSignalRequired = m_sliceTypeBusy;',
                    '    m_inputLock.release();',
                    '    if (wait)',
                    '        m_outputSignal.wait();',
                    '    m_outputLock.acquire();',
                    '    out = m_outputQueue.first();',
                    '    m_outputLock.release();',
                    '    return out;',
                    '}',
                )) + '\n',
                'source/encoder/encoder.cpp': '\n'.join((
                    'if (!pass)',
                    '{',
                    '    if (!m_param->bResetZoneConfig && m_param->reconfigWindowSize && m_param->rc.zonefileCount &&',
                    '        (m_encodedFrameNum % m_param->reconfigWindowSize == 0))',
                    '    {',
                    '        Frame* nextFrame = m_lookahead->peekDecidedPicture();',
                    '        int zoneIndex = (m_encodedFrameNum / m_param->reconfigWindowSize) % m_param->rc.zonefileCount;',
                    '        if (!zoneReadCount || !zoneWriteCount || !zone || !zone->zoneParam ||',
                    '            (m_param->reconfigWindowSize && !zone->relativeComplexity))',
                    '        {',
                    '            x265_log(m_param, X265_LOG_ERROR,',
                    '                     "Zone reconfiguration state is incomplete before encode order %d (POC %d)\\n",',
                    '                     m_encodedFrameNum, nextFrame->m_poc);',
                    '            m_aborted = true;',
                    '            return -1;',
                    '        }',
                    '        if (zoneWrite <= zoneRead)',
                    '        {',
                    '            x265_log(m_param, X265_LOG_ERROR,',
                    '                     "Zone reconfiguration window at encode order %d (POC %d) was not prefilled before encoding reached it\\n",',
                    '                     m_encodedFrameNum, nextFrame->m_poc);',
                    '            m_aborted = true;',
                    '            return -1;',
                    '        }',
                    '        if (zone->startFrame != m_encodedFrameNum)',
                    '        {',
                    '            x265_log(m_param, X265_LOG_ERROR,',
                    '                     "Zone reconfiguration window at encode order %d (POC %d) is staged for startFrame %d instead of the current reconfig window\\n",',
                    '                     m_encodedFrameNum, nextFrame->m_poc, zone->startFrame);',
                    '            m_aborted = true;',
                    '            return -1;',
                    '        }',
                    '    }',
                    '    frameEnc[0] = m_lookahead->getDecidedPicture();',
                    '}',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/slicetype.h': 'class Lookahead {\npublic:\n    Frame*  peekDecidedPicture();\n};\n',
                'source/encoder/slicetype.cpp': '\n'.join((
                    'Frame* Lookahead::peekDecidedPicture()',
                    '{',
                    '    Frame* out = m_outputQueue.popFront();',
                    '    return out;',
                    '}',
                )) + '\n',
                'source/encoder/encoder.cpp': 'frameEnc[0] = m_lookahead->getDecidedPicture();\n',
            },
        )
        expect_fail(run_checker(root), 'peekDecidedPicture must inspect the output queue without consuming it')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/slicetype.h': 'class Lookahead {\npublic:\n    Frame*  peekDecidedPicture();\n};\n',
                'source/encoder/slicetype.cpp': '\n'.join((
                    'Frame* Lookahead::peekDecidedPicture()',
                    '{',
                    '    Frame* out = m_outputQueue.first();',
                    '    out = m_outputQueue.first();',
                    '    findJob(-1); /* run slicetypeDecide() if necessary */',
                    '    m_outputSignal.wait();',
                    '    return out;',
                    '}',
                )) + '\n',
                'source/encoder/encoder.cpp': '\n'.join((
                    'if (!pass)',
                    '{',
                    '    frameEnc[0] = m_lookahead->getDecidedPicture();',
                    '    Frame* nextFrame = m_lookahead->peekDecidedPicture();',
                    '    if (zoneWrite <= zoneRead)',
                    '    {',
                    '    }',
                    '    if (zone->startFrame != m_encodedFrameNum)',
                    '    {',
                    '    }',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'Encoder::encode must preflight the no-reset zone window before consuming the next decided picture')

    print('No-reset zone prefill guard tests passed')


if __name__ == '__main__':
    main()
