#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_cli_input_validation_cleanup.py')


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
    'if (info[i].depth < 8 || info[i].depth > 16)',
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
    'x265_log(param, X265_LOG_ERROR, "Multiview input file <%s> does not match the first view\\n", inputfn[i]);',
    'for (int releaseIdx = 0; releaseIdx < viewCount; releaseIdx++)',
    '{',
    '    if (this->input[releaseIdx])',
    '    {',
    '        this->input[releaseIdx]->release();',
    '        this->input[releaseIdx] = nullptr;',
    '    }',
    '}',
    'return true;',
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
                    'if (info[i].depth < 8 || info[i].depth > 16)',
                    '{',
                    '    return true;',
                    '}',
                    'x265_log(param, X265_LOG_ERROR, "Multiview input file <%s> does not match the first view\\n", inputfn[i]);',
                    'return true;',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'missing CLI input validation cleanup guardrail: for (int releaseIdx = 0; releaseIdx <= i; releaseIdx++)')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/x265cli.cpp': '\n'.join((
                    'x265_log(param, X265_LOG_ERROR, "Multiview input file <%s> does not match the first view\\n", inputfn[i]);',
                    'for (int releaseIdx = 0; releaseIdx < viewCount; releaseIdx++)',
                    '{',
                    '    if (this->input[releaseIdx])',
                    '    {',
                    '        this->input[releaseIdx]->release();',
                    '        this->input[releaseIdx] = nullptr;',
                    '    }',
                    '}',
                    'return true;',
                    'if (info[i].depth < 8 || info[i].depth > 16)',
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
        expect_fail(run_checker(root), 'CLI input bit-depth validation must release opened inputs before returning')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/x265cli.cpp': '\n'.join((
                    'if (info[i].depth < 8 || info[i].depth > 16)',
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
                    'x265_log(param, X265_LOG_ERROR, "Multiview input file <%s> does not match the first view\\n", inputfn[i]);',
                    'if (this->input[releaseIdx])',
                    '{',
                    '    this->input[releaseIdx]->release();',
                    '    this->input[releaseIdx] = nullptr;',
                    '}',
                    'for (int releaseIdx = 0; releaseIdx < viewCount; releaseIdx++)',
                    '{',
                    '}',
                    'return true;',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'CLI multiview validation must release opened inputs before returning')

    print('CLI input validation cleanup tests passed')


if __name__ == '__main__':
    main()
