#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_ratecontrol_destroy_close_state.py')

# Coverage probes used by the scan for ratecontrol destroy-close guardrails.
NORMALIZED_PROBES = (
    'forbidden ratecontrol destroy short-circuit close regression: ',
    'missing ratecontrol destroy close guardrail: ',
    'ratecontrol destroy must only rename cutree stats files after a successful close',
    'ratecontrol destroy must close cutree input stats before freeing names and shared memory',
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
                'source/encoder/ratecontrol.cpp': '\n'.join((
                    'bool closeFailed = ferror(m_statFileOut) != 0;',
                    'if (fclose(m_statFileOut))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '    x265_log_file(m_param, X265_LOG_ERROR, "failed to finalize output stats file \\"%s\\"\\n", fileName);',
                    'char *tmpFileName = strcatFilename(fileName, ".temp");',
                    'x265_unlink(fileName);',
                    'bError = x265_rename(tmpFileName, fileName);',
                    'X265_FREE(tmpFileName);',
                    'char *tmpFileName = strcatFilename(fileName, ".cutree.temp");',
                    'char *newFileName = strcatFilename(fileName, ".cutree");',
                    'bool closeFailed = ferror(m_cutreeStatFileOut) != 0;',
                    'if (fclose(m_cutreeStatFileOut))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '    x265_log_file(m_param, X265_LOG_ERROR, "failed to finalize cutree output stats file \\"%s\\"\\n", newFileName ? newFileName : fileName);',
                    'x265_unlink(newFileName);',
                    'bError = x265_rename(tmpFileName, newFileName);',
                    'X265_FREE(tmpFileName);',
                    'X265_FREE(newFileName);',
                    'char *cutreeFileName = strcatFilename(fileName, ".cutree");',
                    'bool closeFailed = ferror(m_cutreeStatFileIn) != 0;',
                    'if (fclose(m_cutreeStatFileIn))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '    x265_log_file(m_param, X265_LOG_WARNING, "failed to close cutree input stats file \\"%s\\"\\n", cutreeFileName ? cutreeFileName : fileName);',
                    'X265_FREE(cutreeFileName);',
                    'm_cutreeShrMem->release();',
                    'delete m_cutreeShrMem;',
                    'm_cutreeShrMem = nullptr;',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/encoder/ratecontrol.cpp': 'fclose(m_statFileOut);\n'})
        expect_fail(run_checker(root), 'missing ratecontrol destroy close guardrail')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/ratecontrol.cpp': '\n'.join((
                    'bool closeFailed = ferror(m_statFileOut) != 0;',
                    'if (fclose(m_statFileOut))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '    x265_log_file(m_param, X265_LOG_ERROR, "failed to finalize output stats file \\"%s\\"\\n", fileName);',
                    'char *tmpFileName = strcatFilename(fileName, ".temp");',
                    'x265_unlink(fileName);',
                    'bError = x265_rename(tmpFileName, fileName);',
                    'X265_FREE(tmpFileName);',
                    'char *tmpFileName = strcatFilename(fileName, ".cutree.temp");',
                    'char *newFileName = strcatFilename(fileName, ".cutree");',
                    'bool closeFailed = ferror(m_cutreeStatFileOut) != 0;',
                    'if (fclose(m_cutreeStatFileOut))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '    x265_log_file(m_param, X265_LOG_ERROR, "failed to finalize cutree output stats file \\"%s\\"\\n", newFileName ? newFileName : fileName);',
                    'x265_unlink(newFileName);',
                    'bError = x265_rename(tmpFileName, newFileName);',
                    'X265_FREE(tmpFileName);',
                    'X265_FREE(newFileName);',
                    'char *cutreeFileName = strcatFilename(fileName, ".cutree");',
                    'bool closeFailed = ferror(m_cutreeStatFileIn) != 0;',
                    'if (fclose(m_cutreeStatFileIn))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '    x265_log_file(m_param, X265_LOG_WARNING, "failed to close cutree input stats file \\"%s\\"\\n", cutreeFileName ? cutreeFileName : fileName);',
                    'X265_FREE(cutreeFileName);',
                    'm_cutreeShrMem->release();',
                    'delete m_cutreeShrMem;',
                    'm_cutreeShrMem = nullptr;',
                    'if (ferror(m_statFileOut) || fclose(m_statFileOut))',
                    '    return;',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden ratecontrol destroy short-circuit close regression')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/ratecontrol.cpp': '\n'.join((
                    'char *tmpFileName = strcatFilename(fileName, ".temp");',
                    'x265_unlink(fileName);',
                    'bError = x265_rename(tmpFileName, fileName);',
                    'bool closeFailed = ferror(m_statFileOut) != 0;',
                    'if (fclose(m_statFileOut))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '    x265_log_file(m_param, X265_LOG_ERROR, "failed to finalize output stats file \\"%s\\"\\n", fileName);',
                    'X265_FREE(tmpFileName);',
                    'char *tmpFileName = strcatFilename(fileName, ".cutree.temp");',
                    'char *newFileName = strcatFilename(fileName, ".cutree");',
                    'bool closeFailed = ferror(m_cutreeStatFileOut) != 0;',
                    'if (fclose(m_cutreeStatFileOut))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '    x265_log_file(m_param, X265_LOG_ERROR, "failed to finalize cutree output stats file \\"%s\\"\\n", newFileName ? newFileName : fileName);',
                    'x265_unlink(newFileName);',
                    'bError = x265_rename(tmpFileName, newFileName);',
                    'X265_FREE(tmpFileName);',
                    'X265_FREE(newFileName);',
                    'char *cutreeFileName = strcatFilename(fileName, ".cutree");',
                    'bool closeFailed = ferror(m_cutreeStatFileIn) != 0;',
                    'if (fclose(m_cutreeStatFileIn))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '    x265_log_file(m_param, X265_LOG_WARNING, "failed to close cutree input stats file \\"%s\\"\\n", cutreeFileName ? cutreeFileName : fileName);',
                    'X265_FREE(cutreeFileName);',
                    'm_cutreeShrMem->release();',
                    'delete m_cutreeShrMem;',
                    'm_cutreeShrMem = nullptr;',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'ratecontrol destroy must only rename stats files after a successful close')

    print('Ratecontrol destroy close guard tests passed')


if __name__ == '__main__':
    main()
