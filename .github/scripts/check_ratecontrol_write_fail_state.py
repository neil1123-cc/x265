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
        'auto failStatsWrite = [this](FILE*& file, const char* logName)',
        'if (file)',
        'bool closeFailed = ferror(file) != 0;',
        'if (fclose(file))',
        'x265_log_file(m_param, X265_LOG_WARNING, "failed to close %s after write failure\\n", logName);',
        'file = nullptr;',
        'if (!m_statFileOut || (m_param->rc.cuTree && IS_REFERENCED(curFrame) && !m_param->rc.bStatRead && X265_SHARE_MODE_FILE == m_param->rc.dataShareMode && !m_cutreeStatFileOut))',
        'failStatsWrite(m_statFileOut, "output stats file");',
        'failStatsWrite(m_cutreeStatFileOut, "cutree output stats file");',
    )
    for snippet in required:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing ratecontrol write fail-state guardrail: {snippet}'))

    helper_pos = text.find('auto failStatsWrite = [this](FILE*& file, const char* logName)')
    fclose_pos = text.find('if (fclose(file))', helper_pos)
    null_pos = text.find('file = nullptr;', fclose_pos)
    if -1 in (helper_pos, fclose_pos, null_pos) or not (helper_pos < fclose_pos < null_pos):
        failures.append((TARGET.as_posix(), 0, 'ratecontrol write fail-state helper must close the stream before clearing the member pointer'))

    entry_guard_pos = text.find('if (!m_statFileOut || (m_param->rc.cuTree && IS_REFERENCED(curFrame) && !m_param->rc.bStatRead && X265_SHARE_MODE_FILE == m_param->rc.dataShareMode && !m_cutreeStatFileOut))')
    write_failure_label_pos = text.find('writeFailure:')
    fail_stats_close_pos = text.find('failStatsWrite(m_statFileOut, "output stats file");', write_failure_label_pos)
    fail_cutree_close_pos = text.find('failStatsWrite(m_cutreeStatFileOut, "cutree output stats file");', fail_stats_close_pos)
    if -1 in (entry_guard_pos, write_failure_label_pos, fail_stats_close_pos, fail_cutree_close_pos) or not (
        entry_guard_pos < write_failure_label_pos < fail_stats_close_pos < fail_cutree_close_pos
    ):
        failures.append((TARGET.as_posix(), 0, 'ratecontrol stats writes must guard entry state and retire both output streams on write failure'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check ratecontrol write fail-state handling')
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

    print('Ratecontrol write fail-state guard validated')


if __name__ == '__main__':
    main()
