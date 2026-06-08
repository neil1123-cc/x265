#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/encoder/encoder.cpp')
FORBIDDEN_SNIPPETS = (
    'std::ferror(m_analysisFileIn) || std::fclose(m_analysisFileIn)',
    'std::ferror(m_analysisFileOut) || std::fclose(m_analysisFileOut)',
    'std::ferror(m_naluFile) || std::fclose(m_naluFile)',
    'std::ferror(m_param->csvfpt) || std::fclose(m_param->csvfpt)',
)
REQUIRED_SNIPPETS = (
    'bool closeFailed = std::ferror(m_analysisFileIn) != 0;',
    'if (std::fclose(m_analysisFileIn))',
    'if (closeFailed)',
    'x265_log_file(m_param, X265_LOG_WARNING, "failed to close analysis input file \\"%s\\"\\n", name);',
    'bool closeFailed = std::ferror(m_analysisFileOut) != 0;',
    'if (std::fclose(m_analysisFileOut))',
    'if (closeFailed)',
    'x265_log_file(m_param, X265_LOG_ERROR, "failed to finalize analysis stats file \\"%s\\"\\n", name);',
    'char* temp = strcatFilename(name, ".temp");',
    'x265_unlink(name);',
    'bError = x265_rename(temp, name);',
    'x265_log_file(m_param, X265_LOG_ERROR, "failed to rename analysis stats file to \\"%s\\"\\n", name);',
    'X265_FREE(temp);',
    'bool closeFailed = std::ferror(m_naluFile) != 0;',
    'if (std::fclose(m_naluFile))',
    'if (closeFailed)',
    'x265_log_file(m_param, X265_LOG_WARNING, "failed to close user SEI file \\"%s\\"\\n", m_param->naluFile);',
    'bool closeFailed = std::ferror(m_param->csvfpt) != 0;',
    'if (std::fclose(m_param->csvfpt))',
    'if (closeFailed)',
    'x265_log_file(m_param, X265_LOG_WARNING, "failed to close CSV log file \\"%s\\"\\n", m_param->csvfn);',
)


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    region_start = text.find('if (m_analysisFileIn)')
    region_end = text.find('// Need not check anymore since all pointer is alias to base[]', region_start)
    region = text[region_start:region_end] if -1 not in (region_start, region_end) else text
    failures = []
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in region:
            failures.append((TARGET.as_posix(), 0, f'forbidden encoder destroy short-circuit close regression: {snippet}'))
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in region:
            failures.append((TARGET.as_posix(), 0, f'missing encoder destroy close guardrail: {snippet}'))

    analysis_in_close = region.find('bool closeFailed = std::ferror(m_analysisFileIn) != 0;')
    analysis_out_close = region.find('bool closeFailed = std::ferror(m_analysisFileOut) != 0;')
    temp_assign = region.find('char* temp = strcatFilename(name, ".temp");')
    rename_call = region.find('bError = x265_rename(temp, name);')
    temp_free = region.find('X265_FREE(temp);')
    nalu_close = region.find('bool closeFailed = std::ferror(m_naluFile) != 0;')
    csv_close = region.find('bool closeFailed = std::ferror(m_param->csvfpt) != 0;')
    if -1 not in (analysis_in_close, analysis_out_close, temp_assign, rename_call, temp_free, nalu_close, csv_close):
        if not (analysis_in_close < analysis_out_close < temp_assign < rename_call < temp_free < nalu_close < csv_close):
            failures.append((TARGET.as_posix(), 0, 'encoder destroy must finalize and rename analysis stats before closing user SEI and CSV files'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check encoder destroy close state')
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

    print('Encoder destroy close guard validated')


if __name__ == '__main__':
    main()
