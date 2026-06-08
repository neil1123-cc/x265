#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_scalinglist_close_state.py')

# Coverage probes used by the scan for scaling-list close-state guardrails.
NORMALIZED_PROBES = (
    'expected six guarded scaling-list close paths',
    'expected six guarded scaling-list fclose calls',
    'forbidden scaling list short-circuit close regression: ',
    'missing scaling list close guardrail: ',
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
                    'closeFailed = std::ferror(fp) != 0;',
                    'if (std::fclose(fp))',
                    '    closeFailed = true;',
                    'x265_log_file(nullptr, X265_LOG_WARNING, "can\'t close scaling list file %s after open failure\\n", filename);',
                    'x265_log_file(nullptr, X265_LOG_ERROR, "can\'t open scaling list file %s\\n", filename);',
                    'closeFailed = std::ferror(fp) != 0;',
                    'if (std::fclose(fp))',
                    '    closeFailed = true;',
                    'x265_log_file(nullptr, X265_LOG_WARNING, "can\'t close scaling list file %s after matrix read failure\\n", filename);',
                    'return true;',
                    'closeFailed = std::ferror(fp) != 0;',
                    'if (std::fclose(fp))',
                    '    closeFailed = true;',
                    'x265_log_file(nullptr, X265_LOG_WARNING, "can\'t close scaling list file %s after matrix parse failure\\n", filename);',
                    'return true;',
                    'closeFailed = std::ferror(fp) != 0;',
                    'if (std::fclose(fp))',
                    '    closeFailed = true;',
                    'x265_log_file(nullptr, X265_LOG_WARNING, "can\'t close scaling list file %s after DC read failure\\n", filename);',
                    'return true;',
                    'closeFailed = std::ferror(fp) != 0;',
                    'if (std::fclose(fp))',
                    '    closeFailed = true;',
                    'x265_log_file(nullptr, X265_LOG_WARNING, "can\'t close scaling list file %s after DC parse failure\\n", filename);',
                    'return true;',
                    'closeFailed = std::ferror(fp) != 0;',
                    'if (std::fclose(fp))',
                    '    closeFailed = true;',
                    'x265_log_file(nullptr, X265_LOG_WARNING, "can\'t finalize scaling list file %s\\n", filename);',
                    'm_bEnabled = true;',
                    'm_bDataPresent = true;',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/common/scalinglist.cpp': 'std::fclose(fp);\n'})
        expect_fail(run_checker(root), 'missing scaling list close guardrail')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/scalinglist.cpp': '\n'.join((
                    'closeFailed = std::ferror(fp) != 0;',
                    'if (std::fclose(fp))',
                    '    closeFailed = true;',
                    'x265_log_file(nullptr, X265_LOG_WARNING, "can\'t close scaling list file %s after open failure\\n", filename);',
                    'x265_log_file(nullptr, X265_LOG_ERROR, "can\'t open scaling list file %s\\n", filename);',
                    'closeFailed = std::ferror(fp) != 0;',
                    'if (std::fclose(fp))',
                    '    closeFailed = true;',
                    'x265_log_file(nullptr, X265_LOG_WARNING, "can\'t close scaling list file %s after matrix read failure\\n", filename);',
                    'return true;',
                    'closeFailed = std::ferror(fp) != 0;',
                    'if (std::fclose(fp))',
                    '    closeFailed = true;',
                    'x265_log_file(nullptr, X265_LOG_WARNING, "can\'t close scaling list file %s after matrix parse failure\\n", filename);',
                    'return true;',
                    'closeFailed = std::ferror(fp) != 0;',
                    'if (std::fclose(fp))',
                    '    closeFailed = true;',
                    'x265_log_file(nullptr, X265_LOG_WARNING, "can\'t close scaling list file %s after DC read failure\\n", filename);',
                    'return true;',
                    'closeFailed = std::ferror(fp) != 0;',
                    'if (std::fclose(fp))',
                    '    closeFailed = true;',
                    'x265_log_file(nullptr, X265_LOG_WARNING, "can\'t close scaling list file %s after DC parse failure\\n", filename);',
                    'return true;',
                    'closeFailed = std::ferror(fp) != 0;',
                    'if (std::fclose(fp))',
                    '    closeFailed = true;',
                    'x265_log_file(nullptr, X265_LOG_WARNING, "can\'t finalize scaling list file %s\\n", filename);',
                    'm_bEnabled = true;',
                    'm_bDataPresent = true;',
                    'if (std::ferror(fp) || std::fclose(fp))',
                    '    return true;',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden scaling list short-circuit close regression')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/scalinglist.cpp': '\n'.join((
                    'closeFailed = std::ferror(fp) != 0;',
                    'if (std::fclose(fp))',
                    '    closeFailed = true;',
                    'x265_log_file(nullptr, X265_LOG_WARNING, "can\'t close scaling list file %s after open failure\\n", filename);',
                    'x265_log_file(nullptr, X265_LOG_ERROR, "can\'t open scaling list file %s\\n", filename);',
                    'closeFailed = std::ferror(fp) != 0;',
                    'if (std::fclose(fp))',
                    '    closeFailed = true;',
                    'x265_log_file(nullptr, X265_LOG_WARNING, "can\'t close scaling list file %s after matrix read failure\\n", filename);',
                    'return true;',
                    'closeFailed = std::ferror(fp) != 0;',
                    'if (std::fclose(fp))',
                    '    closeFailed = true;',
                    'x265_log_file(nullptr, X265_LOG_WARNING, "can\'t close scaling list file %s after matrix parse failure\\n", filename);',
                    'return true;',
                    'closeFailed = std::ferror(fp) != 0;',
                    'if (std::fclose(fp))',
                    '    closeFailed = true;',
                    'x265_log_file(nullptr, X265_LOG_WARNING, "can\'t close scaling list file %s after DC read failure\\n", filename);',
                    'return true;',
                    'closeFailed = std::ferror(fp) != 0;',
                    'if (std::fclose(fp))',
                    '    closeFailed = true;',
                    'x265_log_file(nullptr, X265_LOG_WARNING, "can\'t close scaling list file %s after DC parse failure\\n", filename);',
                    'return true;',
                    'closeFailed = std::ferror(fp) != 0;',
                    'if (std::fclose(fp))',
                    '    closeFailed = true;',
                    'm_bEnabled = true;',
                    'x265_log_file(nullptr, X265_LOG_WARNING, "can\'t finalize scaling list file %s\\n", filename);',
                    'm_bDataPresent = true;',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'scaling list close guards must preserve open-failure, parse-failure, and finalize ordering before enabling the scaling list')

    print('Scaling list close guard tests passed')


if __name__ == '__main__':
    main()
