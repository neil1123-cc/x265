#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_lambda_file_close_state.py')

# Coverage probes used by the scan for lambda-file close-state guardrails.
NORMALIZED_PROBES = (
    'expected seven guarded lambda-file close paths',
    'expected seven guarded lambda-file fclose calls',
    'expected seven lambda-file error returns',
    'forbidden lambda file short-circuit close regression: ',
    'missing lambda file close guardrail: ',
    'lambda-file close guards must preserve open-failure, parse-failure, and finalize ordering',
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
                    'x265_log_file(param, X265_LOG_ERROR, "unable to read lambda file <%s>\\n", param->rc.lambdaFileName);',
                    'return true;',
                    'bool closeFailed = ferror(lfn) != 0;',
                    'if (fclose(lfn))',
                    '    closeFailed = true;',
                    'x265_log(param, X265_LOG_WARNING, "unable to close lambda file after open failure\\n");',
                    'x265_log_file(param, X265_LOG_ERROR, "unable to read lambda file <%s>\\n", param->rc.lambdaFileName);',
                    'return true;',
                    'bool closeFailed = ferror(lfn) != 0;',
                    'if (fclose(lfn))',
                    '    closeFailed = true;',
                    'x265_log(param, X265_LOG_WARNING, "unable to close lambda file after read failure\\n");',
                    'x265_log_file(param, X265_LOG_ERROR, "unable to read lambda file <%s>\\n", param->rc.lambdaFileName);',
                    'return true;',
                    'bool closeFailed = ferror(lfn) != 0;',
                    'if (fclose(lfn))',
                    '    closeFailed = true;',
                    'x265_log(param, X265_LOG_WARNING, "unable to close lambda file after incomplete parse\\n");',
                    'x265_log(param, X265_LOG_ERROR, "lambda file is incomplete\\n");',
                    'return true;',
                    'bool closeFailed = ferror(lfn) != 0;',
                    'if (fclose(lfn))',
                    '    closeFailed = true;',
                    'x265_log(param, X265_LOG_WARNING, "unable to close lambda file after truncated parse\\n");',
                    'return false;',
                    'x265_log(param, X265_LOG_ERROR, "invalid lambda value: %s\\n", tok);',
                    'bool closeFailed = ferror(lfn) != 0;',
                    'if (fclose(lfn))',
                    '    closeFailed = true;',
                    'x265_log(param, X265_LOG_WARNING, "unable to close lambda file after invalid value\\n");',
                    'return true;',
                    'x265_log(param, X265_LOG_ERROR, "lambda file contains too many values\\n");',
                    'bool closeFailed = ferror(lfn) != 0;',
                    'if (fclose(lfn))',
                    '    closeFailed = true;',
                    'x265_log(param, X265_LOG_WARNING, "unable to close lambda file after oversized table\\n");',
                    'return true;',
                    'bool closeFailed = ferror(lfn) != 0;',
                    'if (fclose(lfn))',
                    '    closeFailed = true;',
                    'x265_log(param, X265_LOG_WARNING, "unable to finalize lambda file state\\n");',
                    'return true;',
                    'return false;',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/common/param.cpp': 'fclose(lfn);\n'})
        expect_fail(run_checker(root), 'missing lambda file close guardrail')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': '\n'.join((
                    'x265_log_file(param, X265_LOG_ERROR, "unable to read lambda file <%s>\\n", param->rc.lambdaFileName);',
                    'return true;',
                    'bool closeFailed = ferror(lfn) != 0;',
                    'if (fclose(lfn))',
                    '    closeFailed = true;',
                    'x265_log(param, X265_LOG_WARNING, "unable to close lambda file after open failure\\n");',
                    'x265_log_file(param, X265_LOG_ERROR, "unable to read lambda file <%s>\\n", param->rc.lambdaFileName);',
                    'return true;',
                    'bool closeFailed = ferror(lfn) != 0;',
                    'if (fclose(lfn))',
                    '    closeFailed = true;',
                    'x265_log(param, X265_LOG_WARNING, "unable to close lambda file after read failure\\n");',
                    'x265_log_file(param, X265_LOG_ERROR, "unable to read lambda file <%s>\\n", param->rc.lambdaFileName);',
                    'return true;',
                    'bool closeFailed = ferror(lfn) != 0;',
                    'if (fclose(lfn))',
                    '    closeFailed = true;',
                    'x265_log(param, X265_LOG_WARNING, "unable to close lambda file after incomplete parse\\n");',
                    'x265_log(param, X265_LOG_ERROR, "lambda file is incomplete\\n");',
                    'return true;',
                    'bool closeFailed = ferror(lfn) != 0;',
                    'if (fclose(lfn))',
                    '    closeFailed = true;',
                    'x265_log(param, X265_LOG_WARNING, "unable to close lambda file after truncated parse\\n");',
                    'return false;',
                    'x265_log(param, X265_LOG_ERROR, "invalid lambda value: %s\\n", tok);',
                    'bool closeFailed = ferror(lfn) != 0;',
                    'if (fclose(lfn))',
                    '    closeFailed = true;',
                    'x265_log(param, X265_LOG_WARNING, "unable to close lambda file after invalid value\\n");',
                    'return true;',
                    'x265_log(param, X265_LOG_ERROR, "lambda file contains too many values\\n");',
                    'bool closeFailed = ferror(lfn) != 0;',
                    'if (fclose(lfn))',
                    '    closeFailed = true;',
                    'x265_log(param, X265_LOG_WARNING, "unable to close lambda file after oversized table\\n");',
                    'return true;',
                    'bool closeFailed = ferror(lfn) != 0;',
                    'if (fclose(lfn))',
                    '    closeFailed = true;',
                    'x265_log(param, X265_LOG_WARNING, "unable to finalize lambda file state\\n");',
                    'return true;',
                    'return false;',
                    'if (ferror(lfn) || fclose(lfn))',
                    '    return true;',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden lambda file short-circuit close regression')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': '\n'.join((
                    'x265_log_file(param, X265_LOG_ERROR, "unable to read lambda file <%s>\\n", param->rc.lambdaFileName);',
                    'return true;',
                    'bool closeFailed = ferror(lfn) != 0;',
                    'if (fclose(lfn))',
                    '    closeFailed = true;',
                    'x265_log(param, X265_LOG_WARNING, "unable to close lambda file after open failure\\n");',
                    'x265_log_file(param, X265_LOG_ERROR, "unable to read lambda file <%s>\\n", param->rc.lambdaFileName);',
                    'return true;',
                    'bool closeFailed = ferror(lfn) != 0;',
                    'if (fclose(lfn))',
                    '    closeFailed = true;',
                    'x265_log(param, X265_LOG_WARNING, "unable to close lambda file after read failure\\n");',
                    'x265_log_file(param, X265_LOG_ERROR, "unable to read lambda file <%s>\\n", param->rc.lambdaFileName);',
                    'return true;',
                    'bool closeFailed = ferror(lfn) != 0;',
                    'if (fclose(lfn))',
                    '    closeFailed = true;',
                    'x265_log(param, X265_LOG_WARNING, "unable to close lambda file after incomplete parse\\n");',
                    'x265_log(param, X265_LOG_ERROR, "lambda file is incomplete\\n");',
                    'return true;',
                    'bool closeFailed = ferror(lfn) != 0;',
                    'if (fclose(lfn))',
                    '    closeFailed = true;',
                    'x265_log(param, X265_LOG_WARNING, "unable to close lambda file after truncated parse\\n");',
                    'return true;',
                    'x265_log(param, X265_LOG_ERROR, "invalid lambda value: %s\\n", tok);',
                    'bool closeFailed = ferror(lfn) != 0;',
                    'if (fclose(lfn))',
                    '    closeFailed = true;',
                    'x265_log(param, X265_LOG_WARNING, "unable to close lambda file after invalid value\\n");',
                    'return true;',
                    'x265_log(param, X265_LOG_ERROR, "lambda file contains too many values\\n");',
                    'bool closeFailed = ferror(lfn) != 0;',
                    'if (fclose(lfn))',
                    '    closeFailed = true;',
                    'x265_log(param, X265_LOG_WARNING, "unable to close lambda file after oversized table\\n");',
                    'return true;',
                    'bool closeFailed = ferror(lfn) != 0;',
                    'if (fclose(lfn))',
                    '    closeFailed = true;',
                    'x265_log(param, X265_LOG_WARNING, "unable to finalize lambda file state\\n");',
                    'return true;',
                    'return false;',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'expected two lambda-file false returns for truncated parse and successful completion')

    print('Lambda file close guard tests passed')


if __name__ == '__main__':
    main()
