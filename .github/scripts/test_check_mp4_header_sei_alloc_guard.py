#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_mp4_header_sei_alloc_guard.py')

# Coverage probes used by the scan for MP4 header SEI allocation guardrails.
NORMALIZED_PROBES = (
    'missing MP4 header SEI allocation guardrail: #include <new>',
    'missing MP4Muxer::configureParameterSets function',
    """return failSeiAssembly("failed to allocate sei transition buffer.\n");""",
    """missing MP4 header SEI allocation guardrail: return failSeiAssembly("failed to allocate sei transition buffer.\n");""",
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
        '#include <new>',
        'bool MP4Muxer::configureParameterSets(const x265_nal* nal, uint32_t nalcount)',
        '{',
        '    uint8_t* newSeiBuffer = nullptr;',
        '    uint32_t newSeiSize = 0;',
        '    newSeiBuffer = new (std::nothrow) uint8_t[newSeiSize];',
        '    if (!newSeiBuffer)',
        '        return failSeiAssembly("failed to allocate sei transition buffer.\\n");',
        '    return true;',
        '}',
    )) + '\n'


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/output/mp4.cpp': valid_text()})
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/output/mp4.cpp': valid_text().replace('new (std::nothrow) uint8_t[newSeiSize]', 'new uint8_t[newSeiSize]', 1)})
        expect_fail(run_checker(root), 'forbidden MP4 header SEI allocation regression: newSeiBuffer = new uint8_t[newSeiSize];')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/output/mp4.cpp': valid_text().replace('return failSeiAssembly("failed to allocate sei transition buffer.\\n");', 'return false;', 1)})
        expect_fail(run_checker(root), 'missing MP4 header SEI allocation guardrail: return failSeiAssembly("failed to allocate sei transition buffer.\\n");')

    print('MP4 header SEI allocation guard tests passed')


if __name__ == '__main__':
    main()
