#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/encoder/encoder.cpp')
FORBIDDEN_SNIPPETS = (
    'std::ferror(m_analysisFileIn) || std::fclose(m_analysisFileIn)',
)
REQUIRED_SNIPPETS = (
    'm_analysisFileIn = x265_fopen(m_param->analysisLoad, "rb");',
    'else if (std::ferror(m_analysisFileIn))',
    'bool closeFailed = std::ferror(m_analysisFileIn) != 0;',
    'if (std::fclose(m_analysisFileIn))',
    'closeFailed = true;',
    'if (closeFailed)',
    'x265_log_file(nullptr, X265_LOG_WARNING, "failed to close analysis load file \\"%s\\" after open failure\\n", m_param->analysisLoad);',
    'm_analysisFileIn = nullptr;',
    'int rightOffset, bottomOffset;',
    'if (fread(&rightOffset, sizeof(int), 1, m_analysisFileIn) != 1)',
)


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    failures = []
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in text:
            failures.append((TARGET.as_posix(), 0, f'forbidden analysis load open-state short-circuit close regression: {snippet}'))
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing analysis load open-state guardrail: {snippet}'))
    region_start = text.find('if (std::strlen(m_param->analysisLoad) && m_param->bUseAnalysisFile)')
    region_end = text.find('return;', region_start)
    region = text[region_start:region_end] if -1 not in (region_start, region_end) else text
    open_line = region.find('m_analysisFileIn = x265_fopen(m_param->analysisLoad, "rb");')
    close_line = region.find('bool closeFailed = std::ferror(m_analysisFileIn) != 0;')
    reset_line = region.find('m_analysisFileIn = nullptr;')
    read_decl = region.find('int rightOffset, bottomOffset;')
    read_line = region.find('if (fread(&rightOffset, sizeof(int), 1, m_analysisFileIn) != 1)')
    if -1 not in (open_line, close_line, reset_line, read_decl, read_line):
        if not (open_line < close_line < reset_line < read_decl < read_line):
            failures.append((TARGET.as_posix(), 0, 'analysis load open-failure close guard must stay before the analysis-read path'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check analysis load open state')
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

    print('Analysis load open-state guard validated')


if __name__ == '__main__':
    main()
