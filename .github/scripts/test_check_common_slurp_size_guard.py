#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_common_slurp_size_guard.py')


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
        'char* x265_slurp_file(const char *filename)',
        '{',
        '    size_t fSize = 0;',
        '    long fileSize = 0;',
        '    bError |= std::fseek(fh, 0, SEEK_END) < 0;',
        '    fileSize = std::ftell(fh);',
        '    bError |= fileSize <= 0;',
        '    if (!bError)',
        '    {',
        '        bError |= (uint64_t)fileSize > (uint64_t)SIZE_MAX - 2;',
        '        if (!bError)',
        '            fSize = (size_t)fileSize;',
        '    }',
        '    bError |= std::fseek(fh, 0, SEEK_SET) < 0;',
        '    buf = X265_MALLOC(char, fSize + 2);',
        '    size_t readBytes = std::fread(buf, 1, fSize, fh);',
        '    bError |= readBytes != fSize;',
        "    if (!bError && buf[fSize - 1] != '\\n')",
        '        buf[fSize++] = \'\\n\';',
        '    if (!bError)',
        '        buf[fSize] = 0;',
        '}',
    )) + '\n'


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/common/common.cpp': valid_text()})
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/common.cpp': valid_text().replace(
                    '    fileSize = std::ftell(fh);\n'
                    '    bError |= fileSize <= 0;\n'
                    '    if (!bError)\n'
                    '    {\n'
                    '        bError |= (uint64_t)fileSize > (uint64_t)SIZE_MAX - 2;\n'
                    '        if (!bError)\n'
                    '            fSize = (size_t)fileSize;\n'
                    '    }\n',
                    '    bError |= (fSize = std::ftell(fh)) <= 0;\n',
                    1,
                ),
            },
        )
        expect_fail(run_checker(root), 'forbidden common slurp size regression: bError |= (fSize = std::ftell(fh)) <= 0;')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/common.cpp': valid_text().replace(
                    '        bError |= (uint64_t)fileSize > (uint64_t)SIZE_MAX - 2;\n',
                    '',
                    1,
                ),
            },
        )
        expect_fail(run_checker(root), 'missing common slurp size guardrail: bError |= (uint64_t)fileSize > (uint64_t)SIZE_MAX - 2;')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/common.cpp': valid_text().replace(
                    '    size_t readBytes = std::fread(buf, 1, fSize, fh);\n'
                    '    bError |= readBytes != fSize;\n'
                    "    if (!bError && buf[fSize - 1] != '\\n')\n"
                    "        buf[fSize++] = '\\n';\n"
                    '    if (!bError)\n'
                    '        buf[fSize] = 0;\n',
                    "    bError |= std::fread(buf, 1, fSize, fh) != fSize;\n"
                    "    if (buf[fSize - 1] != '\\n')\n"
                    "        buf[fSize++] = '\\n';\n"
                    '    buf[fSize] = 0;\n',
                    1,
                ),
            },
        )
        expect_fail(run_checker(root), 'forbidden common slurp size regression: bError |= std::fread(buf, 1, fSize, fh) != fSize;')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/common.cpp': valid_text().replace(
                    '    size_t readBytes = std::fread(buf, 1, fSize, fh);\n'
                    '    bError |= readBytes != fSize;\n'
                    "    if (!bError && buf[fSize - 1] != '\\n')\n"
                    "        buf[fSize++] = '\\n';\n"
                    '    if (!bError)\n'
                    '        buf[fSize] = 0;\n',
                    '    size_t readBytes = std::fread(buf, 1, fSize, fh);\n'
                    '    if (!bError)\n'
                    '        buf[fSize] = 0;\n'
                    '    bError |= readBytes != fSize;\n'
                    "    if (!bError && buf[fSize - 1] != '\\n')\n"
                    "        buf[fSize++] = '\\n';\n",
                    1,
                ),
            },
        )
        expect_fail(run_checker(root), 'x265_slurp_file must validate read length before inspecting or terminating the slurped buffer')

    print('Common slurp size guard tests passed')


if __name__ == '__main__':
    main()
