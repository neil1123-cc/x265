#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_param_string_replace_safety.py')

# Normalized checker probes used by the coverage scan for param string replacement guardrails.
NORMALIZED_PROBES = (
    'logfn replacement must allocate before dropping the old string',
    'pgfn replacement must allocate before dropping the old string',
    'forbidden param string replacement regression: ',
    'missing param string replacement guardrail: ',
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
                'source/common/param.cpp': '\n'.join((
                    'char* newLogfn = nullptr;',
                    'newLogfn = strdup(src->logfn);',
                    'if (newLogfn)',
                    '{',
                    '    free(dst->logfn);',
                    '    dst->logfn = newLogfn;',
                    '}',
                    'char* newPgfn = nullptr;',
                    'newPgfn = strdup(src->pgfn);',
                    'if (newPgfn)',
                    '{',
                    '    free(dst->pgfn);',
                    '    dst->pgfn = newPgfn;',
                    '}',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': '\n'.join((
                    'if (dst->logfn)',
                    '{',
                    '    free(dst->logfn);',
                    '    dst->logfn = nullptr;',
                    '}',
                    'if (src->logfn)',
                    '{',
                    '    dst->logfn = strdup(src->logfn);',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'missing param string replacement guardrail')

    print('Param string replacement safety tests passed')


if __name__ == '__main__':
    main()
