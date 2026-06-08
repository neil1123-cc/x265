#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_encoder_destroy_close_state.py')

# Coverage probes used by the scan for encoder destroy-close guardrails.
NORMALIZED_PROBES = (
    'forbidden encoder destroy short-circuit close regression: ',
    'missing encoder destroy close guardrail: ',
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
                'source/encoder/encoder.cpp': '\n'.join((
                    'bool closeFailed = std::ferror(m_analysisFileIn) != 0;',
                    'if (std::fclose(m_analysisFileIn))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '    x265_log_file(m_param, X265_LOG_WARNING, "failed to close analysis input file \\"%s\\"\\n", name);',
                    'bool closeFailed = std::ferror(m_analysisFileOut) != 0;',
                    'if (std::fclose(m_analysisFileOut))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '    x265_log_file(m_param, X265_LOG_ERROR, "failed to finalize analysis stats file \\"%s\\"\\n", name);',
                    'char* temp = strcatFilename(name, ".temp");',
                    'x265_unlink(name);',
                    'bError = x265_rename(temp, name);',
                    'x265_log_file(m_param, X265_LOG_ERROR, "failed to rename analysis stats file to \\"%s\\"\\n", name);',
                    'X265_FREE(temp);',
                    'bool closeFailed = std::ferror(m_naluFile) != 0;',
                    'if (std::fclose(m_naluFile))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '    x265_log_file(m_param, X265_LOG_WARNING, "failed to close user SEI file \\"%s\\"\\n", m_param->naluFile);',
                    'bool closeFailed = std::ferror(m_param->csvfpt) != 0;',
                    'if (std::fclose(m_param->csvfpt))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '    x265_log_file(m_param, X265_LOG_WARNING, "failed to close CSV log file \\"%s\\"\\n", m_param->csvfn);',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/encoder/encoder.cpp': 'std::fclose(m_analysisFileOut);\n'})
        expect_fail(run_checker(root), 'missing encoder destroy close guardrail')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/encoder.cpp': '\n'.join((
                    'bool closeFailed = std::ferror(m_analysisFileIn) != 0;',
                    'if (std::fclose(m_analysisFileIn))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '    x265_log_file(m_param, X265_LOG_WARNING, "failed to close analysis input file \\"%s\\"\\n", name);',
                    'bool closeFailed = std::ferror(m_analysisFileOut) != 0;',
                    'if (std::fclose(m_analysisFileOut))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '    x265_log_file(m_param, X265_LOG_ERROR, "failed to finalize analysis stats file \\"%s\\"\\n", name);',
                    'char* temp = strcatFilename(name, ".temp");',
                    'x265_unlink(name);',
                    'bError = x265_rename(temp, name);',
                    'x265_log_file(m_param, X265_LOG_ERROR, "failed to rename analysis stats file to \\"%s\\"\\n", name);',
                    'X265_FREE(temp);',
                    'bool closeFailed = std::ferror(m_naluFile) != 0;',
                    'if (std::fclose(m_naluFile))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '    x265_log_file(m_param, X265_LOG_WARNING, "failed to close user SEI file \\"%s\\"\\n", m_param->naluFile);',
                    'bool closeFailed = std::ferror(m_param->csvfpt) != 0;',
                    'if (std::fclose(m_param->csvfpt))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '    x265_log_file(m_param, X265_LOG_WARNING, "failed to close CSV log file \\"%s\\"\\n", m_param->csvfn);',
                    'if (std::ferror(m_analysisFileOut) || std::fclose(m_analysisFileOut))',
                    '    return;',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden encoder destroy short-circuit close regression')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/encoder.cpp': '\n'.join((
                    'bool closeFailed = std::ferror(m_analysisFileIn) != 0;',
                    'if (std::fclose(m_analysisFileIn))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '    x265_log_file(m_param, X265_LOG_WARNING, "failed to close analysis input file \\"%s\\"\\n", name);',
                    'char* temp = strcatFilename(name, ".temp");',
                    'x265_unlink(name);',
                    'bError = x265_rename(temp, name);',
                    'bool closeFailed = std::ferror(m_analysisFileOut) != 0;',
                    'if (std::fclose(m_analysisFileOut))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '    x265_log_file(m_param, X265_LOG_ERROR, "failed to finalize analysis stats file \\"%s\\"\\n", name);',
                    'x265_log_file(m_param, X265_LOG_ERROR, "failed to rename analysis stats file to \\"%s\\"\\n", name);',
                    'X265_FREE(temp);',
                    'bool closeFailed = std::ferror(m_naluFile) != 0;',
                    'if (std::fclose(m_naluFile))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '    x265_log_file(m_param, X265_LOG_WARNING, "failed to close user SEI file \\"%s\\"\\n", m_param->naluFile);',
                    'bool closeFailed = std::ferror(m_param->csvfpt) != 0;',
                    'if (std::fclose(m_param->csvfpt))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '    x265_log_file(m_param, X265_LOG_WARNING, "failed to close CSV log file \\"%s\\"\\n", m_param->csvfn);',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'encoder destroy must finalize and rename analysis stats before closing user SEI and CSV files')

    print('Encoder destroy close guard tests passed')


if __name__ == '__main__':
    main()
