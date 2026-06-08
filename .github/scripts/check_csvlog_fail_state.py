#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/encoder/api.cpp')


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    failures = []

    required = (
        'static bool closeCsvLogAfterWriteFailure(x265_param* param, FILE*& csvfp, const char* context)',
        'if (!std::fflush(csvfp) && !std::ferror(csvfp))',
        'x265_log(param, X265_LOG_ERROR, "CSV log write failed during %s\\n", context);',
        'if (std::fclose(csvfp))',
        'csvfp = nullptr;',
        'x265_log(param, X265_LOG_WARNING, "Unable to close CSV log file <%s> after %s failure\\n", param->csvfn, context);',
        'if (closeCsvLogAfterWriteFailure((x265_param*)param, csvfp, "CSV header write"))',
        'x265_param* mutableParam = (x265_param*)param;',
        'if (closeCsvLogAfterWriteFailure(mutableParam, mutableParam->csvfpt, "CSV frame logging"))',
        'x265_param* mutableParam = (x265_param*)p;',
        'closeCsvLogAfterWriteFailure(mutableParam, mutableParam->csvfpt, "CSV summary logging");',
    )
    for snippet in required:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing CSV fail-state guardrail: {snippet}'))

    helper_pos = text.find('static bool closeCsvLogAfterWriteFailure(x265_param* param, FILE*& csvfp, const char* context)')
    fflush_pos = text.find('if (!std::fflush(csvfp) && !std::ferror(csvfp))', helper_pos)
    log_pos = text.find('x265_log(param, X265_LOG_ERROR, "CSV log write failed during %s\\n", context);', fflush_pos)
    fclose_pos = text.find('if (std::fclose(csvfp))', log_pos)
    null_pos = text.find('csvfp = nullptr;', fclose_pos)
    if -1 in (helper_pos, fflush_pos, log_pos, fclose_pos, null_pos) or not (helper_pos < fflush_pos < log_pos < fclose_pos < null_pos):
        failures.append((TARGET.as_posix(), 0, 'CSV fail-state helper must flush/detect failure, then close, then clear the stream pointer'))

    header_pos = text.find('if (closeCsvLogAfterWriteFailure((x265_param*)param, csvfp, "CSV header write"))')
    header_return_pos = text.find('return nullptr;', header_pos)
    if -1 in (header_pos, header_return_pos) or not (header_pos < header_return_pos):
        failures.append((TARGET.as_posix(), 0, 'CSV header initialization must return nullptr after retiring a failed CSV stream'))

    frame_newline_pos = text.find('fprintf(param->csvfpt, "\\n");')
    frame_close_pos = text.find('if (closeCsvLogAfterWriteFailure(mutableParam, mutableParam->csvfpt, "CSV frame logging"))', frame_newline_pos)
    frame_return_pos = text.find('return;', frame_close_pos)
    if -1 in (frame_newline_pos, frame_close_pos, frame_return_pos) or not (frame_newline_pos < frame_close_pos < frame_return_pos):
        failures.append((TARGET.as_posix(), 0, 'CSV frame logging must retire the stream immediately after a failed frame write'))

    summary_tail_pos = text.find('fprintf(p->csvfpt, " %s\\n", api->version_str);')
    summary_close_pos = text.find('closeCsvLogAfterWriteFailure(mutableParam, mutableParam->csvfpt, "CSV summary logging");', summary_tail_pos)
    if -1 in (summary_tail_pos, summary_close_pos) or not (summary_tail_pos < summary_close_pos):
        failures.append((TARGET.as_posix(), 0, 'CSV summary logging must retire the stream after the summary write block'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check CSV log fail-state handling')
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

    print('CSV log fail-state guard validated')


if __name__ == '__main__':
    main()
