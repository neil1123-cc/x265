#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/encoder/encoder.cpp')
REQUIRED_SNIPPETS = (
    'USER_SEI_LINE_ERROR,',
    'if (std::ferror(file))',
    'x265_log(param, X265_LOG_ERROR, "Unable to read user SEI file\\n");',
    'return USER_SEI_LINE_ERROR;',
    'auto disableNaluFileParsing = [this](const char* closeContext)',
    'm_enableNal = 0;',
    'bool closeFailed = std::ferror(m_naluFile) != 0;',
    'if (std::fclose(m_naluFile))',
    'm_naluFile = nullptr;',
    'disableNaluFileParsing("after file-position failure");',
    'if (lineState == USER_SEI_LINE_ERROR)',
    'disableNaluFileParsing("after read failure");',
    'disableNaluFileParsing("after rewind failure");',
)


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    failures = []
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing nalu-file error-state guardrail: {snippet}'))

    fgets_pos = text.find('if (!std::fgets(line, (int)lineCapacity, file))')
    ferror_pos = text.find('if (std::ferror(file))', fgets_pos)
    error_return_pos = text.find('return USER_SEI_LINE_ERROR;', ferror_pos)
    eof_return_pos = text.find('return USER_SEI_LINE_EOF;', ferror_pos)
    if -1 not in (fgets_pos, ferror_pos, error_return_pos, eof_return_pos) and not (fgets_pos < ferror_pos < error_return_pos < eof_return_pos):
        failures.append((TARGET.as_posix(), 0, 'nalu-file reads must distinguish ferror() from clean EOF'))

    helper_pos = text.find('auto disableNaluFileParsing = [this](const char* closeContext)')
    fclose_pos = text.find('if (std::fclose(m_naluFile))', helper_pos)
    null_pos = text.find('m_naluFile = nullptr;', fclose_pos)
    if -1 not in (helper_pos, fclose_pos, null_pos) and not (helper_pos < fclose_pos < null_pos):
        failures.append((TARGET.as_posix(), 0, 'nalu-file cleanup helper must close the stream before clearing the member pointer'))

    filepos_log_pos = text.find('Unable to record user SEI file position; disabling nalu-file parsing')
    filepos_disable_pos = text.find('disableNaluFileParsing("after file-position failure");', filepos_log_pos)
    if -1 not in (filepos_log_pos, filepos_disable_pos) and not (filepos_log_pos < filepos_disable_pos):
        failures.append((TARGET.as_posix(), 0, 'nalu-file file-position failures must disable parsing via the cleanup helper'))

    line_error_pos = text.find('if (lineState == USER_SEI_LINE_ERROR)')
    read_disable_pos = text.find('disableNaluFileParsing("after read failure");', line_error_pos)
    if -1 not in (line_error_pos, read_disable_pos) and not (line_error_pos < read_disable_pos):
        failures.append((TARGET.as_posix(), 0, 'nalu-file read failures must disable parsing via the cleanup helper'))

    rewind_log_pos = text.find('Unable to rewind user SEI file for frame %d; disabling nalu-file parsing')
    rewind_disable_pos = text.find('disableNaluFileParsing("after rewind failure");', rewind_log_pos)
    if -1 not in (rewind_log_pos, rewind_disable_pos) and not (rewind_log_pos < rewind_disable_pos):
        failures.append((TARGET.as_posix(), 0, 'nalu-file rewind failures must disable parsing via the cleanup helper'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check nalu-file error state handling')
    parser.add_argument('repo_root', nargs='?', default='.')
    args = parser.parse_args()

    failures = check_repo(args.repo_root)
    if failures:
        for path, line, message in failures:
            if line:
                print(f'::error file={path},line={line}::{message}')
            else:
                print(f'::error file={path}::{message}')
        raise SystemExit(1)

    print('Nalu-file error-state guard validated')


if __name__ == '__main__':
    main()
