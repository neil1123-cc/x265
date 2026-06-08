#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/encoder/ratecontrol.cpp')


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    failures = []

    required = (
        'auto failCutreeRead = [this]()',
        'const char* fileName = m_param->rc.statFileName;',
        'char* cutreeFileName = strcatFilename(fileName, ".cutree");',
        'bool closeFailed = ferror(m_cutreeStatFileIn) != 0;',
        'if (fclose(m_cutreeStatFileIn))',
        'x265_log_file(m_param, X265_LOG_WARNING, "failed to close cutree input stats file \\"%s\\" after read failure\\n", cutreeFileName ? cutreeFileName : fileName);',
        'm_cutreeStatFileIn = nullptr;',
        'if (!m_cutreeStatFileIn)',
        'goto readError;',
        'if (X265_SHARE_MODE_FILE == m_param->rc.dataShareMode && m_cutreeStatFileIn && ferror(m_cutreeStatFileIn))',
        'x265_log(m_param, X265_LOG_ERROR, "CU-tree stats file read failure.\\n");',
        'x265_log(m_param, X265_LOG_ERROR, "Incomplete CU-tree stats file.\\n");',
        'failCutreeRead();',
    )
    for snippet in required:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing ratecontrol cutree read fail-state guardrail: {snippet}'))

    helper_pos = text.find('auto failCutreeRead = [this]()')
    fclose_pos = text.find('if (fclose(m_cutreeStatFileIn))', helper_pos)
    null_pos = text.find('m_cutreeStatFileIn = nullptr;', fclose_pos)
    if -1 in (helper_pos, fclose_pos, null_pos) or not (helper_pos < fclose_pos < null_pos):
        failures.append((TARGET.as_posix(), 0, 'ratecontrol cutree read fail-state helper must close the stream before clearing the member pointer'))

    null_guard_pos = text.find('if (!m_cutreeStatFileIn)')
    read_error_jump_pos = text.find('goto readError;', null_guard_pos)
    read_error_label_pos = text.find('readError:')
    read_error_log_pos = text.find('x265_log(m_param, X265_LOG_ERROR, "CU-tree stats file read failure.\\n");', read_error_label_pos)
    fail_cleanup_pos = text.find('failCutreeRead();', read_error_log_pos)
    if -1 in (null_guard_pos, read_error_jump_pos, read_error_label_pos, read_error_log_pos, fail_cleanup_pos) or not (
        null_guard_pos < read_error_jump_pos < read_error_label_pos < read_error_log_pos < fail_cleanup_pos
    ):
        failures.append((TARGET.as_posix(), 0, 'ratecontrol cutree file reads must guard missing input state and retire the stream on read failure'))

    incomplete_log_pos = text.find('x265_log(m_param, X265_LOG_ERROR, "Incomplete CU-tree stats file.\\n");')
    ferror_guard_pos = text.find('if (X265_SHARE_MODE_FILE == m_param->rc.dataShareMode && m_cutreeStatFileIn && ferror(m_cutreeStatFileIn))')
    if -1 in (ferror_guard_pos, incomplete_log_pos, read_error_label_pos) or not (ferror_guard_pos < incomplete_log_pos < read_error_label_pos):
        failures.append((TARGET.as_posix(), 0, 'ratecontrol cutree file reads must distinguish read errors from incomplete stats data'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check ratecontrol cutree read fail-state handling')
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

    print('Ratecontrol cutree read fail-state guard validated')


if __name__ == '__main__':
    main()
