#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_nal_takecontents_realloc_safety.py')

# Coverage probes used by the scan for NAL takeContents reallocation guardrails.
NORMALIZED_PROBES = (
    'NALList::takeContents must reset the source list to a zero-capacity safe state before rebuilding its buffer',
    'forbidden NAL takeContents realloc regression: ',
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
        'void NALList::takeContents(NALList& other)',
        '{',
        '    const uint32_t otherAllocSize = other.m_allocSize;',
        '    X265_FREE(m_buffer);',
        '    m_buffer = other.m_buffer;',
        '    m_allocSize = otherAllocSize;',
        '    m_occupancy = other.m_occupancy;',
        '    m_numNal = other.m_numNal;',
        '    std::memcpy(m_nal, other.m_nal, sizeof(x265_nal) * m_numNal);',
        '    other.m_numNal = 0;',
        '    other.m_occupancy = 0;',
        '    other.m_buffer = nullptr;',
        '    other.m_allocSize = 0;',
        '    if (otherAllocSize)',
        '    {',
        '        uint8_t* newBuffer = X265_MALLOC(uint8_t, otherAllocSize);',
        '        if (newBuffer)',
        '        {',
        '            other.m_buffer = newBuffer;',
        '            other.m_allocSize = otherAllocSize;',
        '        }',
        '        else',
        '            x265_log(nullptr, X265_LOG_ERROR, "Unable to realloc access unit buffer\\n");',
        '    }',
        '}',
    )) + '\n'


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/encoder/nal.cpp': valid_text()})
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/nal.cpp': valid_text().replace('    other.m_allocSize = 0;\n', '', 1),
            },
        )
        expect_fail(run_checker(root), 'missing NAL takeContents realloc guardrail: other.m_allocSize = 0;')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/nal.cpp': '\n'.join((
                    'void NALList::takeContents(NALList& other)',
                    '{',
                    '    other.m_buffer = X265_MALLOC(uint8_t, m_allocSize);',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden NAL takeContents realloc regression')

    print('NAL takeContents realloc safety tests passed')


if __name__ == '__main__':
    main()
