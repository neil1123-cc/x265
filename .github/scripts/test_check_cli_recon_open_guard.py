#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_cli_recon_open_guard.py')


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
    'this->recon[i] = ReconFile::open(reconfn[i], param->sourceWidth, param->sourceHeight, reconFileBitDepth,',
    '    param->fpsNum, param->fpsDenom, param->internalCsp, param->sourceBitDepth);',
    'if (!this->recon[i] || this->recon[i]->isFail())',
    '{',
    '    if (this->recon[i])',
    '    {',
    '        this->recon[i]->release();',
    '        this->recon[i] = 0;',
    '    }',
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
                    'this->recon[i] = ReconFile::open(reconfn[i], param->sourceWidth, param->sourceHeight, reconFileBitDepth,',
                    '    param->fpsNum, param->fpsDenom, param->internalCsp, param->sourceBitDepth);',
                    'if (this->recon[i]->isFail())',
                    '{',
                    '    this->recon[i]->release();',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'missing CLI recon open guardrail: if (!this->recon[i] || this->recon[i]->isFail())')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/x265cli.cpp': '\n'.join((
                    'if (!this->recon[i] || this->recon[i]->isFail())',
                    '{',
                    '    if (this->recon[i])',
                    '    {',
                    '        this->recon[i]->release();',
                    '        this->recon[i] = 0;',
                    '    }',
                    '}',
                    'this->recon[i] = ReconFile::open(reconfn[i], param->sourceWidth, param->sourceHeight, reconFileBitDepth,',
                    '    param->fpsNum, param->fpsDenom, param->internalCsp, param->sourceBitDepth);',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'Recon open result must be null-checked before isFail()')

    print('CLI recon open guard tests passed')


if __name__ == '__main__':
    main()
