#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_mp4_preflight_close_state.py')

# Coverage probes used by the scan for MP4 preflight close-state guardrails.
NORMALIZED_PROBES = (
    'forbidden MP4 preflight short-circuit close regression: std::ferror(fh) || std::fclose(fh)',
    'missing MP4 preflight close-state guardrail: bool closeFailed = std::ferror(fh) != 0;',
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
                'source/output/mp4.cpp': '\n'.join((
                    'FILE* fh = x265_fopen(fname, "wb");',
                    'bool closeFailed = std::ferror(fh) != 0;',
                    'if (std::fclose(fh))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '{',
                    '    MP4_LOG_ERROR("cannot finalize output file preflight `%s\'.\\n", fname);'.replace("\\'", "'"),
                    '    m_fail = true;',
                    '    return false;',
                    '}',
                    'm_root = lsmash_create_root();',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/output/mp4.cpp': 'std::fclose(fh);\n'})
        expect_fail(run_checker(root), 'missing MP4 preflight close-state guardrail')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/output/mp4.cpp': '\n'.join((
                    'FILE* fh = x265_fopen(fname, "wb");',
                    'bool closeFailed = std::ferror(fh) != 0;',
                    'if (std::fclose(fh))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '{',
                    '    MP4_LOG_ERROR("cannot finalize output file preflight `%s\'.\\n", fname);'.replace("\\'", "'"),
                    '    m_fail = true;',
                    '    return false;',
                    '}',
                    'if (std::ferror(fh) || std::fclose(fh))',
                    '    return false;',
                    'm_root = lsmash_create_root();',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden MP4 preflight short-circuit close regression')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/output/mp4.cpp': '\n'.join((
                    'FILE* fh = x265_fopen(fname, "wb");',
                    'if (std::fclose(fh))',
                    '    closeFailed = true;',
                    'bool closeFailed = std::ferror(fh) != 0;',
                    'if (closeFailed)',
                    '{',
                    '    MP4_LOG_ERROR("cannot finalize output file preflight `%s\'.\\n", fname);'.replace("\\'", "'"),
                    '    m_fail = true;',
                    '    return false;',
                    '}',
                    'm_root = lsmash_create_root();',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'MP4 preflight must record fclose failure before reporting the preflight error and creating the root')

    print('MP4 preflight close-state guard tests passed')


if __name__ == '__main__':
    main()
