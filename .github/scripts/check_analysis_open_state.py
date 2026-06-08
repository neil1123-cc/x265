#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/encoder/encoder.cpp')
FORBIDDEN_SNIPPETS = (
    'std::ferror(m_analysisFileOut) || std::fclose(m_analysisFileOut)',
    'std::ferror(m_analysisFileIn) || std::fclose(m_analysisFileIn)',
)
REQUIRED_SNIPPETS = (
    'if (m_param->analysisMultiPassRefine || m_param->analysisMultiPassDistortion)',
    'm_analysisFileOut = x265_fopen(temp, "wb");',
    'else if (std::ferror(m_analysisFileOut))',
    'bool closeFailed = std::ferror(m_analysisFileOut) != 0;',
    'if (std::fclose(m_analysisFileOut))',
    'closeFailed = true;',
    'if (closeFailed)',
    'x265_log_file(nullptr, X265_LOG_WARNING, "failed to close analysis save file \\"%s.temp\\" after open failure\\n", m_param->analysisSave);',
    'x265_log_file(nullptr, X265_LOG_WARNING, "failed to close analysis 2 pass file \\"%s.temp\\" after open failure\\n", name);',
    'm_analysisFileOut = nullptr;',
    'm_analysisFileIn = x265_fopen(name, "rb");',
    'else if (std::ferror(m_analysisFileIn))',
    'bool closeFailed = std::ferror(m_analysisFileIn) != 0;',
    'if (std::fclose(m_analysisFileIn))',
    'closeFailed = true;',
    'if (closeFailed)',
    'x265_log_file(nullptr, X265_LOG_WARNING, "failed to close analysis input file \\"%s\\" after open failure\\n", name);',
    'm_analysisFileIn = nullptr;',
)


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    region_start = text.find('if (std::strlen(m_param->analysisSave) && m_param->bUseAnalysisFile)')
    region_end = text.find('if (m_param->filmGrain)', region_start)
    region = text[region_start:region_end] if -1 not in (region_start, region_end) else text
    failures = []
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in region:
            failures.append((TARGET.as_posix(), 0, f'forbidden analysis open-state short-circuit close regression: {snippet}'))
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in region:
            failures.append((TARGET.as_posix(), 0, f'missing analysis open-state guardrail: {snippet}'))
    if region.count('m_analysisFileOut = x265_fopen(temp, "wb");') != 2:
        failures.append((TARGET.as_posix(), 0, 'expected both analysis output open-failure paths to be guarded'))
    if region.count('else if (std::ferror(m_analysisFileOut))') != 2:
        failures.append((TARGET.as_posix(), 0, 'expected two guarded analysis output open-failure branches'))
    if region.count('bool closeFailed = std::ferror(m_analysisFileOut) != 0;') != 2:
        failures.append((TARGET.as_posix(), 0, 'expected guarded analysis output close handling for both open-failure paths'))
    if region.count('if (std::fclose(m_analysisFileOut))') != 2:
        failures.append((TARGET.as_posix(), 0, 'expected two guarded analysis output fclose calls'))
    if region.count('m_analysisFileOut = nullptr;') != 2:
        failures.append((TARGET.as_posix(), 0, 'expected analysis output handles to be cleared in both open-failure paths'))

    multipass_block = region.find('if (m_param->analysisMultiPassRefine || m_param->analysisMultiPassDistortion)')
    first_out_open = region.find('m_analysisFileOut = x265_fopen(temp, "wb");')
    second_out_open = region.find('m_analysisFileOut = x265_fopen(temp, "wb");', first_out_open + 1)
    first_out_close = region.find('bool closeFailed = std::ferror(m_analysisFileOut) != 0;')
    second_out_close = region.find('bool closeFailed = std::ferror(m_analysisFileOut) != 0;', first_out_close + 1)
    input_open = region.find('m_analysisFileIn = x265_fopen(name, "rb");')
    input_close = region.find('bool closeFailed = std::ferror(m_analysisFileIn) != 0;')
    if -1 not in (multipass_block, first_out_open, second_out_open, first_out_close, second_out_close, input_open, input_close):
        if not (first_out_open < first_out_close < multipass_block < second_out_open < second_out_close < input_open < input_close):
            failures.append((TARGET.as_posix(), 0, 'analysis open-state guards must preserve the save-output path before the multi-pass output and input paths'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check analysis open state')
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

    print('Analysis open-state guard validated')


if __name__ == '__main__':
    main()
