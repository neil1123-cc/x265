#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_log_progress_file_parse_safety.py')

# Normalized checker probe used by the coverage scan for generic guardrail failures.
NORMALIZED_PROBES = (
    'missing log/progress file guardrail: ',
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
                    'OPT("log-file")',
                    '{',
                    '    char* newLogFile = strdup(value);',
                    '    if (!newLogFile)',
                    '        bError = true;',
                    '    else',
                    '    {',
                    '        free(p->logfn);',
                    '        p->logfn = newLogFile;',
                    '    }',
                    '}',
                    'OPT("progress-file")',
                    '{',
                    '    char* newProgressFile = strdup(value);',
                    '    if (!newProgressFile)',
                    '        bError = true;',
                    '    else',
                    '    {',
                    '        free(p->pgfn);',
                    '        p->pgfn = newProgressFile;',
                    '    }',
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
                    'OPT("log-file")',
                    '{',
                    '    if (p->logfn)',
                    '    {',
                    '        free(p->logfn);',
                    '        p->logfn = nullptr;',
                    '    }',
                    '    p->logfn = strdup(value);',
                    '}',
                    'OPT("log-file-level")',
                    'OPT("progress-file")',
                    '{',
                    '    char* newProgressFile = strdup(value);',
                    '    if (!newProgressFile)',
                    '        bError = true;',
                    '    else',
                    '    {',
                    '        free(p->pgfn);',
                    '        p->pgfn = newProgressFile;',
                    '    }',
                    '}',
                    'OPT("csv-log-level")',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden log/progress file parse regression: if (p->logfn)')

    print('Log/progress file parse safety tests passed')


if __name__ == '__main__':
    main()
