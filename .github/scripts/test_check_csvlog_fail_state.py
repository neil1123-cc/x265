#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_csvlog_fail_state.py')


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
    'static bool closeCsvLogAfterWriteFailure(x265_param* param, FILE*& csvfp, const char* context)',
    '{',
    '    if (!std::fflush(csvfp) && !std::ferror(csvfp))',
    '        return false;',
    '    x265_log(param, X265_LOG_ERROR, "CSV log write failed during %s\\n", context);',
    '    if (std::fclose(csvfp))',
    '        closeFailed = true;',
    '    csvfp = nullptr;',
    '    x265_log(param, X265_LOG_WARNING, "Unable to close CSV log file <%s> after %s failure\\n", param->csvfn, context);',
    '}',
    'if (closeCsvLogAfterWriteFailure((x265_param*)param, csvfp, "CSV header write"))',
    '    return nullptr;',
    'x265_param* mutableParam = (x265_param*)param;',
    'fprintf(param->csvfpt, "\\n");',
    'if (closeCsvLogAfterWriteFailure(mutableParam, mutableParam->csvfpt, "CSV frame logging"))',
    '    return;',
    'x265_param* mutableParam = (x265_param*)p;',
    'fprintf(p->csvfpt, " %s\\n", api->version_str);',
    'closeCsvLogAfterWriteFailure(mutableParam, mutableParam->csvfpt, "CSV summary logging");',
)) + '\n'


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/encoder/api.cpp': PASS_SOURCE})
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/encoder/api.cpp': 'fprintf(param->csvfpt, "\\n");\n'})
        expect_fail(run_checker(root), 'missing CSV fail-state guardrail: static bool closeCsvLogAfterWriteFailure(x265_param* param, FILE*& csvfp, const char* context)')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/api.cpp': '\n'.join((
                    'static bool closeCsvLogAfterWriteFailure(x265_param* param, FILE*& csvfp, const char* context)',
                    '{',
                    '    if (!std::fflush(csvfp) && !std::ferror(csvfp))',
                    '        return false;',
                    '    x265_log(param, X265_LOG_ERROR, "CSV log write failed during %s\\n", context);',
                    '    csvfp = nullptr;',
                    '    if (std::fclose(csvfp))',
                    '        closeFailed = true;',
                    '}',
                    'if (closeCsvLogAfterWriteFailure((x265_param*)param, csvfp, "CSV header write"))',
                    '    return nullptr;',
                    'x265_param* mutableParam = (x265_param*)param;',
                    'fprintf(param->csvfpt, "\\n");',
                    'if (closeCsvLogAfterWriteFailure(mutableParam, mutableParam->csvfpt, "CSV frame logging"))',
                    '    return;',
                    'x265_param* mutableParam = (x265_param*)p;',
                    'fprintf(p->csvfpt, " %s\\n", api->version_str);',
                    'closeCsvLogAfterWriteFailure(mutableParam, mutableParam->csvfpt, "CSV summary logging");',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'CSV fail-state helper must flush/detect failure, then close, then clear the stream pointer')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/api.cpp': PASS_SOURCE.replace(
                    '    return nullptr;\n',
                    '',
                    1,
                ),
            },
        )
        expect_fail(run_checker(root), 'CSV header initialization must return nullptr after retiring a failed CSV stream')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/api.cpp': PASS_SOURCE.replace(
                    '    return;\n',
                    '',
                    1,
                ),
            },
        )
        expect_fail(run_checker(root), 'CSV frame logging must retire the stream immediately after a failed frame write')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/api.cpp': PASS_SOURCE.replace(
                    'fprintf(p->csvfpt, " %s\\n", api->version_str);\n'
                    'closeCsvLogAfterWriteFailure(mutableParam, mutableParam->csvfpt, "CSV summary logging");',
                    'closeCsvLogAfterWriteFailure(mutableParam, mutableParam->csvfpt, "CSV summary logging");\n'
                    'fprintf(p->csvfpt, " %s\\n", api->version_str);',
                    1,
                ),
            },
        )
        expect_fail(run_checker(root), 'CSV summary logging must retire the stream after the summary write block')

    print('CSV log fail-state guard tests passed')


if __name__ == '__main__':
    main()
