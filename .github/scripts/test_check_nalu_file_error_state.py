#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_nalu_file_error_state.py')

# Coverage probes used by the scan for nalu-file error-state guardrails.
NORMALIZED_PROBES = (
    'nalu-file reads must distinguish ferror() from clean EOF',
    'nalu-file cleanup helper must close the stream before clearing the member pointer',
    'nalu-file file-position failures must disable parsing via the cleanup helper',
    'nalu-file read failures must disable parsing via the cleanup helper',
    'nalu-file rewind failures must disable parsing via the cleanup helper',
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
                    'USER_SEI_LINE_ERROR,',
                    'if (!std::fgets(line, (int)lineCapacity, file))',
                    '{',
                    '    if (std::ferror(file))',
                    '    {',
                    '        x265_log(param, X265_LOG_ERROR, "Unable to read user SEI file\\n");',
                    '        return USER_SEI_LINE_ERROR;',
                    '    }',
                    '    return USER_SEI_LINE_EOF;',
                    '}',
                    'auto disableNaluFileParsing = [this](const char* closeContext)',
                    '{',
                    '    m_enableNal = 0;',
                    '    bool closeFailed = std::ferror(m_naluFile) != 0;',
                    '    if (std::fclose(m_naluFile))',
                    '        closeFailed = true;',
                    '    if (closeFailed)',
                    '        x265_log_file(m_param, X265_LOG_WARNING, "failed to close user SEI file \\"%s\\" %s\\n", m_param->naluFile, closeContext);',
                    '    m_naluFile = nullptr;',
                    '}',
                    'x265_log(m_param, X265_LOG_ERROR, "Unable to record user SEI file position; disabling nalu-file parsing\\n");',
                    'disableNaluFileParsing("after file-position failure");',
                    'if (lineState == USER_SEI_LINE_ERROR)',
                    '{',
                    '    disableNaluFileParsing("after read failure");',
                    '}',
                    'x265_log(m_param, X265_LOG_ERROR, "Unable to rewind user SEI file for frame %d; disabling nalu-file parsing\\n", poc);',
                    'disableNaluFileParsing("after rewind failure");',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/encoder.cpp': '\n'.join((
                    'if (!std::fgets(line, (int)lineCapacity, file))',
                    '    return USER_SEI_LINE_EOF;',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'missing nalu-file error-state guardrail: USER_SEI_LINE_ERROR,')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/encoder.cpp': '\n'.join((
                    'USER_SEI_LINE_ERROR,',
                    'if (!std::fgets(line, (int)lineCapacity, file))',
                    '{',
                    '    if (std::ferror(file))',
                    '        return USER_SEI_LINE_EOF;',
                    '}',
                    'auto disableNaluFileParsing = [this](const char* closeContext)',
                    '{',
                    '    if (std::fclose(m_naluFile))',
                    '        closeFailed = true;',
                    '    m_naluFile = nullptr;',
                    '}',
                    'if (lineState == USER_SEI_LINE_ERROR)',
                    '{',
                    '    disableNaluFileParsing("after read failure");',
                    '}',
                    'disableNaluFileParsing("after file-position failure");',
                    'disableNaluFileParsing("after rewind failure");',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'missing nalu-file error-state guardrail: x265_log(param, X265_LOG_ERROR, "Unable to read user SEI file\\n");')

    print('Nalu-file error-state guard tests passed')


if __name__ == '__main__':
    main()
