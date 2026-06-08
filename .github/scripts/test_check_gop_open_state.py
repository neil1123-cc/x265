#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_gop_open_state.py')

# Coverage probes used by the scan for GOP open-state guardrails.
NORMALIZED_PROBES = (
    'GOP file open-state cleanup must happen before retry/bailout',
    'missing GOP open-state guardrail: ',
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
                'source/output/gop.cpp': '\n'.join((
                    'FILE* fp = x265_fopen(fname.c_str(), "wb");',
                    'if(fp != nullptr && !std::ferror(fp))',
                    '    return fp;',
                    'if (fp != nullptr)',
                    '{',
                    '    bool closeFailed = std::ferror(fp) != 0;',
                    '    if (std::fclose(fp))',
                    '        closeFailed = true;',
                    '    if (closeFailed)',
                    '        general_log(nullptr, getName(), X265_LOG_WARNING,',
                    '            "unable to close file %s after open failure.\\n", fname.c_str());',
                    '}',
                    'if(!retry)',
                    '    break;',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/output/gop.cpp': 'FILE* fp = x265_fopen(fname.c_str(), "wb");\nif(fp != nullptr)\n    return fp;\n',
            },
        )
        expect_fail(run_checker(root), 'missing GOP open-state guardrail')

    print('GOP open-state guard tests passed')


if __name__ == '__main__':
    main()
