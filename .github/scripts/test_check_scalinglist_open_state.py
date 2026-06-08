#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_scalinglist_open_state.py')

# Coverage probes used by the scan for scaling-list open-state guardrails.
NORMALIZED_PROBES = (
    'forbidden scaling list open-state regression: ',
    'missing scaling list open-state guardrail: ',
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
                'source/common/scalinglist.cpp': '\n'.join((
                    'FILE *fp = x265_fopen(filename, "r");',
                    'if (!fp)',
                    '{',
                    '    x265_log_file(nullptr, X265_LOG_ERROR, "can\'t open scaling list file %s\\n", filename);',
                    '    return true;',
                    '}',
                    'else if (std::ferror(fp))',
                    '{',
                    'bool closeFailed = std::ferror(fp) != 0;',
                    'if (std::fclose(fp))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '    x265_log_file(nullptr, X265_LOG_WARNING, "can\'t close scaling list file %s after open failure\\n", filename);',
                    'x265_log_file(nullptr, X265_LOG_ERROR, "can\'t open scaling list file %s\\n", filename);',
                    '    return true;',
                    '}',
                    'bool closeFailed = false;',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/scalinglist.cpp': '\n'.join((
                    'FILE *fp = x265_fopen(filename, "r");',
                    'if (!fp)',
                    '{',
                    '    x265_log_file(nullptr, X265_LOG_ERROR, "can\'t open scaling list file %s\\n", filename);',
                    '    return true;',
                    '}',
                    'else if (std::ferror(fp))',
                    '{',
                    'bool closeFailed = std::ferror(fp) != 0;',
                    'if (std::fclose(fp))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '    x265_log_file(nullptr, X265_LOG_WARNING, "can\'t close scaling list file %s after open failure\\n", filename);',
                    'x265_log_file(nullptr, X265_LOG_ERROR, "can\'t open scaling list file %s\\n", filename);',
                    '    return true;',
                    '}',
                    'std::fseek(fp, 0, 0);',
                    'bool closeFailed = false;',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden scaling list open-state regression')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/scalinglist.cpp': 'FILE *fp = x265_fopen(filename, "r");\nif (!fp)\n    return true;\n',
            },
        )
        expect_fail(run_checker(root), 'missing scaling list open-state guardrail')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/scalinglist.cpp': '\n'.join((
                    'FILE *fp = x265_fopen(filename, "r");',
                    'if (!fp)',
                    '{',
                    '    x265_log_file(nullptr, X265_LOG_ERROR, "can\'t open scaling list file %s\\n", filename);',
                    '    return true;',
                    '}',
                    'bool closeFailed = false;',
                    'else if (std::ferror(fp))',
                    '{',
                    '    bool closeFailed = std::ferror(fp) != 0;',
                    '    if (std::fclose(fp))',
                    '        closeFailed = true;',
                    '    if (closeFailed)',
                    '        x265_log_file(nullptr, X265_LOG_WARNING, "can\'t close scaling list file %s after open failure\\n", filename);',
                    '    x265_log_file(nullptr, X265_LOG_ERROR, "can\'t open scaling list file %s\\n", filename);',
                    '    return true;',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'scaling list open failure handling must finalize the preflight handle before reporting the open error and entering parse state')

    print('Scaling list open-state guard tests passed')


if __name__ == '__main__':
    main()
