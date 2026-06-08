#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/encoder/ratecontrol.cpp')
FORBIDDEN_SNIPPETS = (
    'ferror(m_statFileOut) || fclose(m_statFileOut)',
    'ferror(m_cutreeStatFileOut) || fclose(m_cutreeStatFileOut)',
    'ferror(m_cutreeStatFileIn) || fclose(m_cutreeStatFileIn)',
)
REQUIRED_SNIPPETS = (
    'bool closeFailed = ferror(m_statFileOut) != 0;',
    'if (fclose(m_statFileOut))',
    'closeFailed = true;',
    'if (closeFailed)',
    'x265_log_file(m_param, X265_LOG_ERROR, "failed to finalize output stats file \\"%s\\"\\n", fileName);',
    'char *tmpFileName = strcatFilename(fileName, ".temp");',
    'x265_unlink(fileName);',
    'bError = x265_rename(tmpFileName, fileName);',
    'X265_FREE(tmpFileName);',
    'bool closeFailed = ferror(m_cutreeStatFileOut) != 0;',
    'if (fclose(m_cutreeStatFileOut))',
    'closeFailed = true;',
    'if (closeFailed)',
    'x265_log_file(m_param, X265_LOG_ERROR, "failed to finalize cutree output stats file \\"%s\\"\\n", newFileName ? newFileName : fileName);',
    'char *tmpFileName = strcatFilename(fileName, ".cutree.temp");',
    'char *newFileName = strcatFilename(fileName, ".cutree");',
    'x265_unlink(newFileName);',
    'bError = x265_rename(tmpFileName, newFileName);',
    'X265_FREE(newFileName);',
    'bool closeFailed = ferror(m_cutreeStatFileIn) != 0;',
    'if (fclose(m_cutreeStatFileIn))',
    'closeFailed = true;',
    'if (closeFailed)',
    'x265_log_file(m_param, X265_LOG_WARNING, "failed to close cutree input stats file \\"%s\\"\\n", cutreeFileName ? cutreeFileName : fileName);',
    'char *cutreeFileName = strcatFilename(fileName, ".cutree");',
    'X265_FREE(cutreeFileName);',
    'm_cutreeShrMem->release();',
    'delete m_cutreeShrMem;',
    'm_cutreeShrMem = nullptr;',
)


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    region_start = text.find('void RateControl::destroy()')
    region_end = text.find('bool RateControl::splitdeltaPOC', region_start)
    region = text[region_start:region_end] if -1 not in (region_start, region_end) else text
    failures = []
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in region:
            failures.append((TARGET.as_posix(), 0, f'forbidden ratecontrol destroy short-circuit close regression: {snippet}'))
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in region:
            failures.append((TARGET.as_posix(), 0, f'missing ratecontrol destroy close guardrail: {snippet}'))

    stat_close = region.find('bool closeFailed = ferror(m_statFileOut) != 0;')
    stat_tmp = region.find('char *tmpFileName = strcatFilename(fileName, ".temp");')
    stat_rename = region.find('bError = x265_rename(tmpFileName, fileName);')
    stat_free = region.find('X265_FREE(tmpFileName);')
    cutree_tmp = region.find('char *tmpFileName = strcatFilename(fileName, ".cutree.temp");')
    cutree_new = region.find('char *newFileName = strcatFilename(fileName, ".cutree");')
    cutree_out_close = region.find('bool closeFailed = ferror(m_cutreeStatFileOut) != 0;')
    cutree_rename = region.find('bError = x265_rename(tmpFileName, newFileName);')
    cutree_tmp_free = region.find('X265_FREE(tmpFileName);', stat_free + 1)
    cutree_new_free = region.find('X265_FREE(newFileName);')
    if -1 not in (stat_close, stat_tmp, stat_rename, stat_free, cutree_tmp, cutree_new, cutree_out_close, cutree_rename, cutree_tmp_free, cutree_new_free):
        if not (stat_close < stat_tmp < stat_rename < stat_free):
            failures.append((TARGET.as_posix(), 0, 'ratecontrol destroy must only rename stats files after a successful close'))
        if not (cutree_tmp < cutree_new < cutree_out_close < cutree_rename < cutree_tmp_free < cutree_new_free):
            failures.append((TARGET.as_posix(), 0, 'ratecontrol destroy must only rename cutree stats files after a successful close'))

    cutree_in_name = region.find('char *cutreeFileName = strcatFilename(fileName, ".cutree");')
    cutree_in_close = region.find('bool closeFailed = ferror(m_cutreeStatFileIn) != 0;')
    cutree_in_free = region.find('X265_FREE(cutreeFileName);')
    shm_release = region.find('m_cutreeShrMem->release();')
    shm_delete = region.find('delete m_cutreeShrMem;')
    shm_null = region.find('m_cutreeShrMem = nullptr;')
    if -1 not in (cutree_in_name, cutree_in_close, cutree_in_free, shm_release, shm_delete, shm_null):
        if not (cutree_in_name < cutree_in_close < cutree_in_free < shm_release < shm_delete < shm_null):
            failures.append((TARGET.as_posix(), 0, 'ratecontrol destroy must close cutree input stats before freeing names and shared memory'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check ratecontrol destroy close state')
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

    print('Ratecontrol destroy close guard validated')


if __name__ == '__main__':
    main()
