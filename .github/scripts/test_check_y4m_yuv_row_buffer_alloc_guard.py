#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_y4m_yuv_row_buffer_alloc_guard.py')

# Coverage probes used by the scan for y4m/yuv row-buffer allocation guardrails.
NORMALIZED_PROBES = (
    'missing file',
    'missing constructor: ',
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


def valid_files():
    return {
        'source/output/y4m.cpp': '\n'.join((
            '#include <new>',
            'Y4MOutput::Y4MOutput(const char* filename, int w, int h, uint32_t bitdepth, uint32_t fpsNum, uint32_t fpsDenom, int csp, int inputdepth)',
            '{',
            '    buf = new (std::nothrow) char[width];',
            '    if (!buf)',
            '    {',
            '        x265_log(nullptr, X265_LOG_ERROR, "Unable to allocate Y4M output row buffer\\n");',
            '        failed = true;',
            '        return;',
            '    }',
            '}',
        )) + '\n',
        'source/output/yuv.cpp': '\n'.join((
            '#include <new>',
            'YUVOutput::YUVOutput(const char *filename, int w, int h, uint32_t d, int csp, int inputdepth)',
            '{',
            '    buf = new (std::nothrow) char[width];',
            '    if (!buf)',
            '    {',
            '        x265_log(nullptr, X265_LOG_ERROR, "Unable to allocate YUV output row buffer\\n");',
            '        failed = true;',
            '        return;',
            '    }',
            '}',
        )) + '\n',
    }


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, valid_files())
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        files = valid_files()
        files['source/output/y4m.cpp'] = files['source/output/y4m.cpp'].replace('buf = new (std::nothrow) char[width];', 'buf = new char[width];', 1)
        write_targets(root, files)
        expect_fail(run_checker(root), 'forbidden row-buffer allocation regression: buf = new char[width];')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        files = valid_files()
        files['source/output/yuv.cpp'] = files['source/output/yuv.cpp'].replace('        x265_log(nullptr, X265_LOG_ERROR, "Unable to allocate YUV output row buffer\\n");\n', '', 1)
        write_targets(root, files)
        expect_fail(run_checker(root), 'missing row-buffer allocation guardrail: x265_log(nullptr, X265_LOG_ERROR, "Unable to allocate YUV output row buffer\\n");')

    print('Y4M/YUV row-buffer allocation guard tests passed')


if __name__ == '__main__':
    main()
