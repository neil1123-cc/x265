#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_cli_progress_file_state.py')


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
                'source/x265cli.cpp': '\n'.join((
                    'FILE *progressfp = x265_fopen(param->pgfn, "wb");',
                    'bool wroteProgress = std::fprintf(progressfp,',
                    '    "{\\"frame\\":1}\\n") >= 0;',
                    'bool closeFailed = std::ferror(progressfp) != 0;',
                    'if (std::fclose(progressfp))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '    wroteProgress = false;',
                    'if (wroteProgress)',
                    '    prevUpdateTimeFile = time;',
                    'else',
                    '    x265_log_file(param, X265_LOG_WARNING, "unable to open progress report file \\"%s\\"\\n", param->pgfn);',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/x265cli.cpp': 'FILE *progressfp = x265_fopen(param->pgfn, "wb");\nif (progressfp)\n    std::fprintf(progressfp, "x");\n'})
        expect_fail(run_checker(root), 'missing CLI progress-file guardrail: bool wroteProgress = std::fprintf(progressfp,')

    print('CLI progress-file guard tests passed')


if __name__ == '__main__':
    main()
