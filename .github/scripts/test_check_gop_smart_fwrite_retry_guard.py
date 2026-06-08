#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_gop_smart_fwrite_retry_guard.py')

# Coverage probes used by the scan for GOP smart_fwrite retry guardrails.
NORMALIZED_PROBES = (
    'missing GOP smart_fwrite retry guardrail: ',
    'missing GOPOutput::smart_fwrite function',
    'GOPOutput::smart_fwrite must only retry after ENOSPC with clearerr() and fseek() success',
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
        'source/output/gop.h': 'bool smart_fwrite(const void* data, std::size_t size, FILE* file);\n',
        'source/output/gop.cpp': '\n'.join((
            'bool GOPOutput::smart_fwrite(const void* data, std::size_t size, FILE* file)',
            '{',
            '    int err = 0;',
            '    err = errno ? errno : EIO;',
            '    if (err == ENOSPC)',
            '    {',
            '        clearerr(file);',
            '        if (std::fseek(file, data_pos, SEEK_SET) == 0)',
            '            return true;',
            '    }',
            '    b_fail = true;',
            '    return false;',
            '}',
            'int GOPOutput::writeHeaders(const x265_nal* p_nal, uint32_t nalcount)',
            '{',
            '    if (!smart_fwrite(p_nal[i].payload, p_nal[i].sizeBytes, hdr_file))',
            '        return -1;',
            '}',
            'int GOPOutput::writeFrame(const x265_nal* p_nalu, uint32_t nalcount, x265_picture& pic)',
            '{',
            '    if (!smart_fwrite(&ts_lenx, 4, data_file) ||',
            '        !smart_fwrite(&pic.pts, sizeof(int64_t), data_file))',
            '        return -1;',
            '    if (!smart_fwrite(p_nalu[i].payload, p_nalu[i].sizeBytes, data_file))',
            '        return -1;',
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
        files['source/output/gop.h'] = 'void smart_fwrite(const void* data, std::size_t size, FILE* file);\n'
        write_targets(root, files)
        expect_fail(run_checker(root), 'forbidden GOP smart_fwrite retry regression: void smart_fwrite(const void* data, std::size_t size, FILE* file);')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        files = valid_files()
        files['source/output/gop.cpp'] = files['source/output/gop.cpp'].replace(
            '        if (std::fseek(file, data_pos, SEEK_SET) == 0)\n',
            '        std::fseek(file, data_pos, SEEK_SET);\n',
            1,
        )
        write_targets(root, files)
        expect_fail(run_checker(root), 'forbidden GOP smart_fwrite retry regression: std::fseek(file, data_pos, SEEK_SET);')

    print('GOP smart_fwrite retry guard tests passed')


if __name__ == '__main__':
    main()
