#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_raw_close_state.py')

# Coverage probes used by the scan for raw close-state guardrails.
NORMALIZED_PROBES = (
    'missing raw close guardrail: ',
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
                'source/output/raw.cpp': '\n'.join((
                    'bool closeFailed = false;',
                    'if (ofs == stdout)',
                    '    closeFailed = std::fflush(ofs) || std::ferror(ofs);',
                    'else',
                    '    closeFailed = std::ferror(ofs) != 0;',
                    '    if (std::fclose(ofs))',
                    '        closeFailed = true;',
                    'if (closeFailed)',
                    '    b_fail = true;',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/output/raw.cpp': 'if (ofs != stdout && std::fclose(ofs))\n    b_fail = true;\n'})
        expect_fail(run_checker(root), 'missing raw close guardrail')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/output/raw.cpp': '\n'.join((
                    'bool closeFailed = false;',
                    'if (ofs != stdout && (std::ferror(ofs) || std::fclose(ofs)))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '    b_fail = true;',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden raw close short-circuit regression')

    print('RAW close guard tests passed')


if __name__ == '__main__':
    main()
