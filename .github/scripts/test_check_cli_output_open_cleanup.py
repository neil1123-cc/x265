#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_cli_output_open_cleanup.py')


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


PASS_SOURCE = '\n'.join((
    'this->output = OutputFile::open(outputfn, info[0]);',
    'if (!this->output || this->output->isFail())',
    '{',
    '    if (this->output)',
    '    {',
    '        this->output->release();',
    '        this->output = nullptr;',
    '    }',
    '    return true;',
    '}',
)) + '\n'


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/x265cli.cpp': PASS_SOURCE})
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/x265cli.cpp': '\n'.join((
                    'this->output = OutputFile::open(outputfn, info[0]);',
                    'if (this->output->isFail())',
                    '{',
                    '    return true;',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'missing CLI output open cleanup guardrail: if (!this->output || this->output->isFail())')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/x265cli.cpp': '\n'.join((
                    'this->output = OutputFile::open(outputfn, info[0]);',
                    'if (!this->output || this->output->isFail())',
                    '{',
                    '    this->output->release();',
                    '    if (this->output)',
                    '    {',
                    '        this->output = nullptr;',
                    '    }',
                    '    return true;',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'CLI output open failure must null-guard, then release and null output before returning')

    print('CLI output open cleanup tests passed')


if __name__ == '__main__':
    main()
