#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGETS = {
    Path('source/input/y4m.cpp'): (
        'int64_t cur = ftello(ifs);',
        'if (fseeko(ifs, 0, SEEK_END) == 0)',
        'int64_t size = ftello(ifs);',
        'if (fseeko(ifs, cur, SEEK_SET) < 0)',
        'x265_log(nullptr, X265_LOG_ERROR, "y4m: unable to restore input position after frame count estimate\\n");',
        'clearerr(ifs);',
    ),
    Path('source/input/yuv.cpp'): (
        'int64_t cur = ftello(ifs);',
        'if (fseeko(ifs, 0, SEEK_END) == 0)',
        'int64_t size = ftello(ifs);',
        'if (fseeko(ifs, cur, SEEK_SET) < 0)',
        'x265_log(nullptr, X265_LOG_ERROR, "yuv: unable to restore input position after frame count estimate\\n");',
        'clearerr(ifs);',
    ),
}


def check_repo(repo_root):
    repo_root = Path(repo_root)
    failures = []

    for target, snippets in TARGETS.items():
        path = repo_root / target
        if not path.is_file():
            failures.append((target.as_posix(), 0, 'missing file'))
            continue

        text = path.read_text(encoding='utf-8', errors='ignore')
        for snippet in snippets:
            if snippet not in text:
                failures.append((target.as_posix(), 0, f'missing input framecount seek guardrail: {snippet}'))

    y4m_text = (repo_root / Path('source/input/y4m.cpp')).read_text(encoding='utf-8', errors='ignore')
    y4m_cur_pos = y4m_text.find('int64_t cur = ftello(ifs);')
    y4m_seek_end_pos = y4m_text.find('if (fseeko(ifs, 0, SEEK_END) == 0)', y4m_cur_pos if y4m_cur_pos != -1 else 0)
    y4m_size_pos = y4m_text.find('int64_t size = ftello(ifs);', y4m_seek_end_pos if y4m_seek_end_pos != -1 else 0)
    y4m_restore_pos = y4m_text.find('if (fseeko(ifs, cur, SEEK_SET) < 0)', y4m_size_pos if y4m_size_pos != -1 else 0)
    y4m_log_pos = y4m_text.find('x265_log(nullptr, X265_LOG_ERROR, "y4m: unable to restore input position after frame count estimate\\n");', y4m_restore_pos if y4m_restore_pos != -1 else 0)
    y4m_fail_pos = y4m_text.find('failed.store(true);', y4m_log_pos if y4m_log_pos != -1 else 0)
    y4m_clear_pos = y4m_text.find('threadActive.store(false);', y4m_fail_pos if y4m_fail_pos != -1 else 0)
    y4m_return_pos = y4m_text.find('return;', y4m_clear_pos if y4m_clear_pos != -1 else 0)
    y4m_skip_pos = y4m_text.find('if (info.skipFrames)', y4m_return_pos if y4m_return_pos != -1 else 0)
    if -1 in (
        y4m_cur_pos,
        y4m_seek_end_pos,
        y4m_size_pos,
        y4m_restore_pos,
        y4m_log_pos,
        y4m_fail_pos,
        y4m_clear_pos,
        y4m_return_pos,
        y4m_skip_pos,
    ) or not (
        y4m_cur_pos < y4m_seek_end_pos < y4m_size_pos < y4m_restore_pos < y4m_log_pos <
        y4m_fail_pos < y4m_clear_pos < y4m_return_pos < y4m_skip_pos
    ):
        failures.append(('source/input/y4m.cpp', 0, 'Y4MInput must fail fast before skip-frame handling when frame count probing cannot restore the input position'))

    yuv_text = (repo_root / Path('source/input/yuv.cpp')).read_text(encoding='utf-8', errors='ignore')
    yuv_cur_pos = yuv_text.find('int64_t cur = ftello(ifs);')
    yuv_seek_end_pos = yuv_text.find('if (fseeko(ifs, 0, SEEK_END) == 0)', yuv_cur_pos if yuv_cur_pos != -1 else 0)
    yuv_size_pos = yuv_text.find('int64_t size = ftello(ifs);', yuv_seek_end_pos if yuv_seek_end_pos != -1 else 0)
    yuv_restore_pos = yuv_text.find('if (fseeko(ifs, cur, SEEK_SET) < 0)', yuv_size_pos if yuv_size_pos != -1 else 0)
    yuv_log_pos = yuv_text.find('x265_log(nullptr, X265_LOG_ERROR, "yuv: unable to restore input position after frame count estimate\\n");', yuv_restore_pos if yuv_restore_pos != -1 else 0)
    yuv_fail_pos = yuv_text.find('failed.store(true);', yuv_log_pos if yuv_log_pos != -1 else 0)
    yuv_clear_pos = yuv_text.find('threadActive.store(false);', yuv_fail_pos if yuv_fail_pos != -1 else 0)
    yuv_return_pos = yuv_text.find('return;', yuv_clear_pos if yuv_clear_pos != -1 else 0)
    yuv_skip_pos = yuv_text.find('if (info.skipFrames)', yuv_return_pos if yuv_return_pos != -1 else 0)
    if -1 in (
        yuv_cur_pos,
        yuv_seek_end_pos,
        yuv_size_pos,
        yuv_restore_pos,
        yuv_log_pos,
        yuv_fail_pos,
        yuv_clear_pos,
        yuv_return_pos,
        yuv_skip_pos,
    ) or not (
        yuv_cur_pos < yuv_seek_end_pos < yuv_size_pos < yuv_restore_pos < yuv_log_pos <
        yuv_fail_pos < yuv_clear_pos < yuv_return_pos < yuv_skip_pos
    ):
        failures.append(('source/input/yuv.cpp', 0, 'YUVInput must fail fast before skip-frame handling when frame count probing cannot restore the input position'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check input framecount seek restore guardrails')
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

    print('Input framecount seek guard validated')


if __name__ == '__main__':
    main()
