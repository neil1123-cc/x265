#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/encoder/encoder.cpp')


def extract_block(text, start_marker, end_marker):
    start = text.find(start_marker)
    if start == -1:
        return ''
    end = text.find(end_marker, start + len(start_marker))
    if end == -1:
        return text[start:]
    return text[start:end]


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    failures = []

    write_block = extract_block(
        text,
        'void Encoder::writeAnalysisFile(x265_analysis_data* analysis, FrameData &curEncData)',
        'void Encoder::writeAnalysisFileRefine(x265_analysis_data* analysis, FrameData &curEncData)',
    )
    refine_block = extract_block(
        text,
        'void Encoder::writeAnalysisFileRefine(x265_analysis_data* analysis, FrameData &curEncData)',
        'void Encoder::printReconfigureParams()',
    )
    if not write_block:
        failures.append((TARGET.as_posix(), 0, 'missing analysis output fail-state guardrail: writeAnalysisFile block'))
        return failures
    if not refine_block:
        failures.append((TARGET.as_posix(), 0, 'missing analysis output fail-state guardrail: writeAnalysisFileRefine block'))
        return failures

    write_required = (
        'auto failAnalysisWrite = [this]()',
        'x265_log(nullptr, X265_LOG_ERROR, "Error writing analysis data\\n");',
        'if (m_analysisFileOut)',
        'if (std::fclose(m_analysisFileOut))',
        'x265_log_file(m_param, X265_LOG_WARNING, "failed to close analysis output file \\"%s\\" after write failure\\n", m_param->analysisSave);',
        'm_analysisFileOut = nullptr;',
        'm_aborted = true;',
        'if (m_aborted)',
        'if (!m_analysisFileOut)',
    )
    refine_required = (
        'auto failAnalysisWrite = [this]()',
        'x265_log(nullptr, X265_LOG_ERROR, "Error writing analysis 2 pass data\\n");',
        'if (m_analysisFileOut)',
        'if (std::fclose(m_analysisFileOut))',
        'x265_log_file(m_param, X265_LOG_WARNING, "failed to close analysis output file \\"%s\\" after refine write failure\\n", m_param->analysisSave);',
        'm_analysisFileOut = nullptr;',
        'm_aborted = true;',
        'if (m_aborted)',
        'if (!m_analysisFileOut)',
    )
    for snippet in write_required:
        if snippet not in write_block:
            failures.append((TARGET.as_posix(), 0, f'missing analysis output fail-state guardrail in writeAnalysisFile: {snippet}'))
    for snippet in refine_required:
        if snippet not in refine_block:
            failures.append((TARGET.as_posix(), 0, f'missing analysis output fail-state guardrail in writeAnalysisFileRefine: {snippet}'))

    forbidden = 'x265_free_analysis_data(m_param, analysis);'
    if forbidden in write_block:
        failures.append((TARGET.as_posix(), 0, 'writeAnalysisFile must leave analysis-data cleanup to the caller after write failure'))
    if forbidden in refine_block:
        failures.append((TARGET.as_posix(), 0, 'writeAnalysisFileRefine must leave analysis-data cleanup to the caller after write failure'))

    write_fail_pos = write_block.find('auto failAnalysisWrite = [this]()')
    write_close_pos = write_block.find('if (std::fclose(m_analysisFileOut))', write_fail_pos)
    write_null_pos = write_block.find('m_analysisFileOut = nullptr;', write_close_pos)
    write_abort_guard_pos = write_block.find('if (m_aborted)', write_null_pos)
    write_handle_guard_pos = write_block.find('if (!m_analysisFileOut)', write_abort_guard_pos)
    if -1 in (write_fail_pos, write_close_pos, write_null_pos, write_abort_guard_pos, write_handle_guard_pos) or not (
        write_fail_pos < write_close_pos < write_null_pos < write_abort_guard_pos < write_handle_guard_pos
    ):
        failures.append((TARGET.as_posix(), 0, 'writeAnalysisFile must retire the failed stream before later aborted/null stream guards'))

    refine_fail_pos = refine_block.find('auto failAnalysisWrite = [this]()')
    refine_close_pos = refine_block.find('if (std::fclose(m_analysisFileOut))', refine_fail_pos)
    refine_null_pos = refine_block.find('m_analysisFileOut = nullptr;', refine_close_pos)
    refine_abort_guard_pos = refine_block.find('if (m_aborted)', refine_null_pos)
    refine_handle_guard_pos = refine_block.find('if (!m_analysisFileOut)', refine_abort_guard_pos)
    if -1 in (refine_fail_pos, refine_close_pos, refine_null_pos, refine_abort_guard_pos, refine_handle_guard_pos) or not (
        refine_fail_pos < refine_close_pos < refine_null_pos < refine_abort_guard_pos < refine_handle_guard_pos
    ):
        failures.append((TARGET.as_posix(), 0, 'writeAnalysisFileRefine must retire the failed stream before later aborted/null stream guards'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check analysis output fail-state handling')
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

    print('Analysis output fail-state guard validated')


if __name__ == '__main__':
    main()
