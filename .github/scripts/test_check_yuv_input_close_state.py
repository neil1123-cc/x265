#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_yuv_input_close_state.py')

# Coverage probes used by the scan for yuv input close-state guardrails.
NORMALIZED_PROBES = (
    'expected yuv input close guards to skip stdin in both constructor-failure and destructor paths',
    'expected two guarded yuv input close paths',
    'expected two guarded yuv input fclose calls',
    'forbidden yuv input short-circuit close regression: ',
    'missing yuv input close guardrail: ',
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
                'source/input/yuv.cpp': '\n'.join((
                    'if (ifs && ifs != stdin)',
                    'bool closeFailed = std::ferror(ifs) != 0;',
                    'if (std::fclose(ifs))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '    x265_log(nullptr, X265_LOG_WARNING, "yuv: unable to close input file after open failure\\n");',
                    'ifs = nullptr;',
                    'YUVInput::~YUVInput()',
                    'if (ifs && ifs != stdin)',
                    'bool closeFailed = std::ferror(ifs) != 0;',
                    'if (std::fclose(ifs))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '    x265_log(nullptr, X265_LOG_WARNING, "yuv: unable to finalize input file state\\n");',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/input/yuv.cpp': 'std::fclose(ifs);\n'})
        expect_fail(run_checker(root), 'missing yuv input close guardrail')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/input/yuv.cpp': '\n'.join((
                    'if (ifs && ifs != stdin)',
                    'bool closeFailed = std::ferror(ifs) != 0;',
                    'if (std::fclose(ifs))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '    x265_log(nullptr, X265_LOG_WARNING, "yuv: unable to close input file after open failure\\n");',
                    'ifs = nullptr;',
                    'YUVInput::~YUVInput()',
                    'if (ifs && ifs != stdin)',
                    'bool closeFailed = std::ferror(ifs) != 0;',
                    'if (std::fclose(ifs))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '    x265_log(nullptr, X265_LOG_WARNING, "yuv: unable to finalize input file state\\n");',
                    'if (std::ferror(ifs) || std::fclose(ifs))',
                    '    x265_log(nullptr, X265_LOG_WARNING, "yuv: unable to finalize input file state\\n");',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden yuv input short-circuit close regression')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/input/yuv.cpp': '\n'.join((
                    'YUVInput::~YUVInput()',
                    'if (ifs && ifs != stdin)',
                    'bool closeFailed = std::ferror(ifs) != 0;',
                    'if (std::fclose(ifs))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '    x265_log(nullptr, X265_LOG_WARNING, "yuv: unable to finalize input file state\\n");',
                    'if (ifs && ifs != stdin)',
                    'bool closeFailed = std::ferror(ifs) != 0;',
                    'if (std::fclose(ifs))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '    x265_log(nullptr, X265_LOG_WARNING, "yuv: unable to close input file after open failure\\n");',
                    'ifs = nullptr;',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'yuv input close guards must preserve constructor-failure cleanup before destructor finalization')

    print('YUV input close guard tests passed')


if __name__ == '__main__':
    main()
