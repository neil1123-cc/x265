#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_cli_input_open_cleanup.py')


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
    'if (!this->input[i] || this->input[i]->isFail())',
    '{',
    '    for (int releaseIdx = 0; releaseIdx <= i; releaseIdx++)',
    '    {',
    '        if (this->input[releaseIdx])',
    '        {',
    '            this->input[releaseIdx]->release();',
    '            this->input[releaseIdx] = nullptr;',
    '        }',
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
                    'if (!this->input[i] || this->input[i]->isFail())',
                    '{',
                    '    return true;',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'missing CLI input open cleanup guardrail: for (int releaseIdx = 0; releaseIdx <= i; releaseIdx++)')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/x265cli.cpp': '\n'.join((
                    'if (!this->input[i] || this->input[i]->isFail())',
                    '{',
                    '    if (this->input[releaseIdx])',
                    '    {',
                    '        this->input[releaseIdx]->release();',
                    '        this->input[releaseIdx] = nullptr;',
                    '    }',
                    '    for (int releaseIdx = 0; releaseIdx <= i; releaseIdx++)',
                    '    {',
                    '    }',
                    '    return true;',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'CLI input open failure must release already-opened inputs before returning')

    print('CLI input open cleanup tests passed')


if __name__ == '__main__':
    main()
