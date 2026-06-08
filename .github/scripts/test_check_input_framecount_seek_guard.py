#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_input_framecount_seek_guard.py')

# Coverage probes used by the scan for input framecount seek guardrails.
NORMALIZED_PROBES = (
    'missing file',
    'missing input framecount seek guardrail: ',
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
                'source/input/y4m.cpp': '\n'.join((
                    'int64_t cur = ftello(ifs);',
                    'if (fseeko(ifs, 0, SEEK_END) == 0)',
                    'int64_t size = ftello(ifs);',
                    'if (fseeko(ifs, cur, SEEK_SET) < 0)',
                    '{',
                    '    x265_log(nullptr, X265_LOG_ERROR, "y4m: unable to restore input position after frame count estimate\\n");',
                    '    failed.store(true);',
                    '    threadActive.store(false);',
                    '    return;',
                    '}',
                    'clearerr(ifs);',
                    'if (info.skipFrames)',
                )) + '\n',
                'source/input/yuv.cpp': '\n'.join((
                    'int64_t cur = ftello(ifs);',
                    'if (fseeko(ifs, 0, SEEK_END) == 0)',
                    'int64_t size = ftello(ifs);',
                    'if (fseeko(ifs, cur, SEEK_SET) < 0)',
                    '{',
                    '    x265_log(nullptr, X265_LOG_ERROR, "yuv: unable to restore input position after frame count estimate\\n");',
                    '    failed.store(true);',
                    '    threadActive.store(false);',
                    '    return;',
                    '}',
                    'clearerr(ifs);',
                    'if (info.skipFrames)',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/input/y4m.cpp': 'int64_t cur = ftello(ifs);\n',
                'source/input/yuv.cpp': 'int64_t cur = ftello(ifs);\n',
            },
        )
        expect_fail(run_checker(root), 'missing input framecount seek guardrail')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/input/y4m.cpp': '\n'.join((
                    'int64_t cur = ftello(ifs);',
                    'if (fseeko(ifs, 0, SEEK_END) == 0)',
                    'int64_t size = ftello(ifs);',
                    'if (fseeko(ifs, cur, SEEK_SET) < 0)',
                    '{',
                    '    x265_log(nullptr, X265_LOG_ERROR, "y4m: unable to restore input position after frame count estimate\\n");',
                    '    failed.store(true);',
                    '    threadActive.store(false);',
                    '}',
                    'if (info.skipFrames)',
                )) + '\n',
                'source/input/yuv.cpp': '\n'.join((
                    'int64_t cur = ftello(ifs);',
                    'if (fseeko(ifs, 0, SEEK_END) == 0)',
                    'int64_t size = ftello(ifs);',
                    'if (fseeko(ifs, cur, SEEK_SET) < 0)',
                    '{',
                    '    x265_log(nullptr, X265_LOG_ERROR, "yuv: unable to restore input position after frame count estimate\\n");',
                    '    failed.store(true);',
                    '    threadActive.store(false);',
                    '    return;',
                    '}',
                    'clearerr(ifs);',
                    'if (info.skipFrames)',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'Y4MInput must fail fast before skip-frame handling when frame count probing cannot restore the input position')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/input/y4m.cpp': '\n'.join((
                    'int64_t cur = ftello(ifs);',
                    'if (fseeko(ifs, 0, SEEK_END) == 0)',
                    'int64_t size = ftello(ifs);',
                    'if (fseeko(ifs, cur, SEEK_SET) < 0)',
                    '{',
                    '    x265_log(nullptr, X265_LOG_ERROR, "y4m: unable to restore input position after frame count estimate\\n");',
                    '    failed.store(true);',
                    '    threadActive.store(false);',
                    '    return;',
                    '}',
                    'clearerr(ifs);',
                    'if (info.skipFrames)',
                )) + '\n',
                'source/input/yuv.cpp': '\n'.join((
                    'int64_t cur = ftello(ifs);',
                    'if (fseeko(ifs, 0, SEEK_END) == 0)',
                    'int64_t size = ftello(ifs);',
                    'if (fseeko(ifs, cur, SEEK_SET) < 0)',
                    '{',
                    '    x265_log(nullptr, X265_LOG_ERROR, "yuv: unable to restore input position after frame count estimate\\n");',
                    '    failed.store(true);',
                    '    threadActive.store(false);',
                    '}',
                    'if (info.skipFrames)',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'YUVInput must fail fast before skip-frame handling when frame count probing cannot restore the input position')

    print('Input framecount seek guard tests passed')


if __name__ == '__main__':
    main()
