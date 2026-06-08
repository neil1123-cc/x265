#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_output_open_alloc_guards.py')

# Coverage probes used by the scan for output-open allocation guardrails.
NORMALIZED_PROBES = (
    'missing output open allocation guardrail: #include <new>',
    'missing ReconFile::open function',
    'missing OutputFile::open function',
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
        'ReconFile* ReconFile::open(const char *fname, int width, int height, uint32_t bitdepth, uint32_t fpsNum, uint32_t fpsDenom, int csp, int sourceBitDepth)',
        '{',
        '    ReconFile* output = new (std::nothrow) Y4MOutput(fname, width, height, bitdepth, fpsNum, fpsDenom, csp, sourceBitDepth);',
        '    if (!output)',
        '        x265_log(nullptr, X265_LOG_ERROR, "Unable to allocate Y4M recon output\\n");',
        '    output = new (std::nothrow) YUVOutput(fname, width, height, bitdepth, csp, sourceBitDepth);',
        '    if (!output)',
        '        x265_log(nullptr, X265_LOG_ERROR, "Unable to allocate YUV recon output\\n");',
        '}',
        'OutputFile* OutputFile::open(const char *fname, InputFileInfo& inputInfo)',
        '{',
        '    OutputFile* output = new (std::nothrow) MKVOutput(fname, inputInfo);',
        '    if (!output)',
        '        x265_log(nullptr, X265_LOG_ERROR, "Unable to allocate MKV output\\n");',
        '    output = new (std::nothrow) MP4Output(fname, inputInfo);',
        '    if (!output)',
        '        x265_log(nullptr, X265_LOG_ERROR, "Unable to allocate MP4 output\\n");',
        '    output = new (std::nothrow) GOPOutput(fname, inputInfo);',
        '    if (!output)',
        '        x265_log(nullptr, X265_LOG_ERROR, "Unable to allocate GOP output\\n");',
        '    output = new (std::nothrow) RAWOutput(fname, inputInfo);',
        '    if (!output)',
        '        x265_log(nullptr, X265_LOG_ERROR, "Unable to allocate raw output\\n");',
        '}',
    )) + '\n'


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/output/output.cpp': valid_text()})
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/output/output.cpp': valid_text().replace('new (std::nothrow) Y4MOutput', 'new Y4MOutput', 1)})
        expect_fail(run_checker(root), 'forbidden output open allocation regression: new Y4MOutput(')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/output/output.cpp': valid_text().replace('        x265_log(nullptr, X265_LOG_ERROR, "Unable to allocate raw output\\n");\n', '', 1)})
        expect_fail(run_checker(root), 'missing output open allocation guardrail: x265_log(nullptr, X265_LOG_ERROR, "Unable to allocate raw output\\n");')

    print('Output open allocation guard tests passed')


if __name__ == '__main__':
    main()
