#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_y4m_input_close_state.py')

# Coverage probes used by the scan for y4m input close-state guardrails.
NORMALIZED_PROBES = (
    'expected y4m input close guards to skip stdin in both constructor-failure and destructor paths',
    'expected two guarded y4m input close paths',
    'expected two guarded y4m input fclose calls',
    'forbidden y4m input short-circuit close regression: ',
    'missing y4m input close guardrail: ',
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
                    'if (ifs && ifs != stdin)',
                    'bool closeFailed = std::ferror(ifs) != 0;',
                    'if (std::fclose(ifs))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '    x265_log(nullptr, X265_LOG_WARNING, "y4m: unable to close input file after open failure\\n");',
                    'ifs = nullptr;',
                    'Y4MInput::~Y4MInput()',
                    'if (ifs && ifs != stdin)',
                    'bool closeFailed = std::ferror(ifs) != 0;',
                    'if (std::fclose(ifs))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '    x265_log(nullptr, X265_LOG_WARNING, "y4m: unable to finalize input file state\\n");',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/input/y4m.cpp': 'std::fclose(ifs);\n'})
        expect_fail(run_checker(root), 'missing y4m input close guardrail')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/input/y4m.cpp': '\n'.join((
                    'if (ifs && ifs != stdin)',
                    'bool closeFailed = std::ferror(ifs) != 0;',
                    'if (std::fclose(ifs))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '    x265_log(nullptr, X265_LOG_WARNING, "y4m: unable to close input file after open failure\\n");',
                    'ifs = nullptr;',
                    'Y4MInput::~Y4MInput()',
                    'if (ifs && ifs != stdin)',
                    'bool closeFailed = std::ferror(ifs) != 0;',
                    'if (std::fclose(ifs))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '    x265_log(nullptr, X265_LOG_WARNING, "y4m: unable to finalize input file state\\n");',
                    'if (std::ferror(ifs) || std::fclose(ifs))',
                    '    x265_log(nullptr, X265_LOG_WARNING, "y4m: unable to finalize input file state\\n");',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden y4m input short-circuit close regression')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/input/y4m.cpp': '\n'.join((
                    'Y4MInput::~Y4MInput()',
                    'if (ifs && ifs != stdin)',
                    'bool closeFailed = std::ferror(ifs) != 0;',
                    'if (std::fclose(ifs))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '    x265_log(nullptr, X265_LOG_WARNING, "y4m: unable to finalize input file state\\n");',
                    'if (ifs && ifs != stdin)',
                    'bool closeFailed = std::ferror(ifs) != 0;',
                    'if (std::fclose(ifs))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '    x265_log(nullptr, X265_LOG_WARNING, "y4m: unable to close input file after open failure\\n");',
                    'ifs = nullptr;',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'y4m input close guards must preserve constructor-failure cleanup before destructor finalization')

    print('Y4M input close guard tests passed')


if __name__ == '__main__':
    main()
