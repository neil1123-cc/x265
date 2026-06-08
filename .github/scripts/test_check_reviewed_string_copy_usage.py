#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_reviewed_string_copy_usage.py')

# Coverage probes used by the scan for reviewed string-copy guardrails.
NORMALIZED_PROBES = (
    'missing file',
    'avoid reviewed legacy string copy helper ',
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
                'source/abrEncApp.cpp': 'std::snprintf(buf, size, "%s", value);\n',
                'source/common/common.h': 'std::memcpy(output, input, 4);\n',
                'source/encoder/encoder.cpp': 'std::snprintf(buf, sizeof(buf), "%s", "none");\n',
                'source/encoder/ratecontrol.cpp': 'std::memcpy(tmpStr, src, length);\ntmpStr[length] = \'\\0\';\n',
                'source/encoder/slicetype.cpp': "paths[idx][len + path] = 'P';\n",
                'source/input/avs.h': 'std::snprintf(real_filename, sizeof(real_filename), "%s", info.filename);\n',
                'source/input/vpy.cpp': 'std::snprintf(libname_buffer, sizeof(libname_buffer), "%s", real_libname);\n',
                'source/x265cli.cpp': 'std::snprintf(buf + p, size - p, " test");\n',
                'source/common/param.cpp': 'snprintf(buf + used, size - used, " %s", toolstr);\n',
                'source/encoder/level.cpp': 'std::snprintf(profbuf, sizeof(profbuf), "%s", value);\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/abrEncApp.cpp': 'int ok = 0;\n',
                'source/common/common.h': 'std::strcpy(output, input);\n',
                'source/encoder/encoder.cpp': 'int ok = 0;\n',
                'source/encoder/ratecontrol.cpp': 'int ok = 0;\n',
                'source/encoder/slicetype.cpp': 'int ok = 0;\n',
                'source/input/avs.h': 'int ok = 0;\n',
                'source/input/vpy.cpp': 'int ok = 0;\n',
                'source/x265cli.cpp': 'int ok = 0;\n',
                'source/common/param.cpp': 'int ok = 0;\n',
                'source/encoder/level.cpp': 'int ok = 0;\n',
            },
        )
        expect_fail(run_checker(root), 'avoid reviewed legacy string copy helper')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/abrEncApp.cpp': 'int ok = 0;\n',
                'source/common/common.h': 'int ok = 0;\n',
                'source/encoder/encoder.cpp': 'int ok = 0;\n',
                'source/encoder/ratecontrol.cpp': 'std::strncpy(tmpStr, src, length);\n',
                'source/encoder/slicetype.cpp': 'int ok = 0;\n',
                'source/input/avs.h': 'int ok = 0;\n',
                'source/input/vpy.cpp': 'int ok = 0;\n',
                'source/x265cli.cpp': 'int ok = 0;\n',
                'source/common/param.cpp': 'int ok = 0;\n',
                'source/encoder/level.cpp': 'int ok = 0;\n',
            },
        )
        expect_fail(run_checker(root), 'avoid reviewed legacy string copy helper')

    print('Reviewed string copy usage tests passed')


if __name__ == '__main__':
    main()
