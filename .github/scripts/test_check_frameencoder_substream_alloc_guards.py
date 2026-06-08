#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_frameencoder_substream_alloc_guards.py')

# Coverage probes used by the scan for frameencoder substream allocation guardrails.
NORMALIZED_PROBES = (
    'FrameEncoder substream buffers must be staged and fully allocated before assignment to member state',
    'missing frameencoder substream allocation guardrail: ',
    'forbidden frameencoder substream allocation regression: ',
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
        'if (!m_outStreams)',
        '{',
        '    Bitstream* stagedOutStreams = new (std::nothrow) Bitstream[numSubstreams];',
        '    if (!stagedOutStreams)',
        '    {',
        '        x265_log(m_param, X265_LOG_ERROR, "Unable to allocate frame encoder substream bitstreams\\n");',
        '        m_top->m_aborted = true;',
        '        return;',
        '    }',
        '    Bitstream* stagedBackupStreams = nullptr;',
        '    stagedBackupStreams = new (std::nothrow) Bitstream[numSubstreams];',
        '    if (!stagedBackupStreams)',
        '    {',
        '        delete[] stagedOutStreams;',
        '        x265_log(m_param, X265_LOG_ERROR, "Unable to allocate frame encoder backup substream bitstreams\\n");',
        '        m_top->m_aborted = true;',
        '        return;',
        '    }',
        '    uint32_t* stagedSubstreamSizes = X265_MALLOC(uint32_t, numSubstreams);',
        '    if (!stagedSubstreamSizes)',
        '    {',
        '        delete[] stagedOutStreams;',
        '        delete[] stagedBackupStreams;',
        '        x265_log(m_param, X265_LOG_ERROR, "Unable to allocate frame encoder substream size table\\n");',
        '        m_top->m_aborted = true;',
        '        return;',
        '    }',
        '    m_outStreams = stagedOutStreams;',
        '    m_backupStreams = stagedBackupStreams;',
        '    m_substreamSizes = stagedSubstreamSizes;',
        '}',
    )) + '\n'


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/encoder/frameencoder.cpp': valid_text()})
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/frameencoder.cpp': valid_text().replace(
                    '    Bitstream* stagedOutStreams = new (std::nothrow) Bitstream[numSubstreams];\n',
                    '    m_outStreams = new Bitstream[numSubstreams];\n',
                    1,
                ),
            },
        )
        expect_fail(run_checker(root), 'forbidden frameencoder substream allocation regression')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/frameencoder.cpp': valid_text().replace(
                    '    uint32_t* stagedSubstreamSizes = X265_MALLOC(uint32_t, numSubstreams);\n',
                    '    m_substreamSizes = X265_MALLOC(uint32_t, numSubstreams);\n',
                    1,
                ),
            },
        )
        expect_fail(run_checker(root), 'forbidden frameencoder substream allocation regression')

    print('FrameEncoder substream allocation guard tests passed')


if __name__ == '__main__':
    main()
